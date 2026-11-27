import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { countTasks, login, openTasksFromNavigation, required, scope } from './ai-helpers'
import { feedbackLogin, feedbackNavigate, feedbackOpen, feedbackScope, feedbackState } from './feedback-helpers'

// Django and PostgreSQL are real. The owned launcher substitutes the outbound
// HTTPS transport with a deterministic response for the selected provider.
const provider = process.env.HT_FRONTEND_AI_PROVIDER ?? 'openai'
if (provider !== 'groq' && provider !== 'openai') throw new Error('Invalid isolated AI provider fixture.')
const providerName = provider === 'groq' ? 'Groq' : 'OpenAI'
const mode = `${provider}_live`
const model = provider === 'groq' ? 'openai/gpt-oss-120b' : 'gpt-5.4-mini'
const viewports = [{ width: 375, height: 812 }, { width: 768, height: 1024 },
  { width: 1440, height: 1000 }, { width: 812, height: 375 }]

async function verifyViewport(page: Page, name: string) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
  expect(result.violations.map((item) => ({ id: item.id, targets: item.nodes.map((node) => node.target) }))).toEqual([])
  const size = page.viewportSize()
  await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `${name}-${size?.width}x${size?.height}.png`), fullPage: true })
}

test(`${providerName} wire flow with fake transport saves the edited estimate for only the chosen flat Task`, async ({ page }) => {
  test.setTimeout(120_000)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await login(page, 'ai_manager')
  await openTasksFromNavigation(page)
  expect(await countTasks(page.request)).toBe(0)
  await page.getByRole('link', { name: 'Tạo công việc bằng AI', exact: true }).click()
  await expect(page.getByText(`Yêu cầu sẽ được gửi đến ${providerName} để tạo bản nháp.`, { exact: false })).toBeVisible()
  const brief = 'Kiểm tra chất lượng phụ đề cho video hướng dẫn tổng hợp.'
  await page.getByLabel('Mô tả yêu cầu (bắt buộc)', { exact: true }).fill(brief)
  await page.getByLabel('Số công việc mong muốn', { exact: true }).fill('2')
  const generated = page.waitForResponse((response) => new URL(response.url()).pathname === scope().apiAi && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'AI tạo đề xuất', exact: true }).click()
  const reply = await generated
  expect(reply.status()).toBe(201)
  expect(reply.request().postDataJSON()).toEqual({ brief, task_count: 2 })
  expect(reply.request().headers()['idempotency-key']).toMatch(/^[\da-f-]{36}$/i)
  const proposal = await reply.json() as { proposal_id: string; mode: string; payload: { tasks: { parent_ref: string | null; proposed_deadline: string | null; estimated_hours: number }[] } }
  expect(proposal).toMatchObject({ mode, provider, model, usage: {
    input_tokens: 150, billable_output_tokens: 75, status: 'provider_reported',
  } })
  await expect(page.getByText(`Đề xuất từ ${providerName} · ${model}.`, { exact: false })).toBeVisible()
  await expect(page.getByText('Chi phí tham chiếu', { exact: false })).toBeVisible()
  expect(proposal.payload.tasks).toHaveLength(2)
  for (const task of proposal.payload.tasks) expect(task).toMatchObject({ parent_ref: null, proposed_deadline: null, estimated_hours: 2 })
  expect(await countTasks(page.request)).toBe(0)
  await expect(page.getByLabel('Tên công việc 1', { exact: true })).toHaveValue('Công việc kiểm thử AI 1')
  await page.getByLabel('Tên công việc 1', { exact: true }).fill('Công việc được duyệt từ bản nháp kiểm thử')
  const hours = page.getByRole('textbox', { name: 'Số giờ ước tính 1', exact: true })
  await expect(hours).toHaveValue(/^2(?:[,.]00)?$/)
  await hours.fill('3,251')
  await page.getByRole('button', { name: 'Kiểm tra và xác nhận', exact: true }).click()
  await expect(hours).toHaveAttribute('aria-invalid', 'true')
  await expect(hours).toHaveValue('3,251')
  await expect(page.getByRole('dialog', { name: 'Xác nhận tạo công việc', exact: true })).toHaveCount(0)
  await page.getByRole('link', { name: 'Nhập từ 0,01 đến 1.000 giờ, tối đa 2 chữ số thập phân.', exact: true }).click()
  await expect(hours).toBeFocused()
  await hours.fill('3,25')
  await page.getByRole('checkbox', { name: 'Lưu công việc 2 khi xác nhận' }).uncheck()
  for (const size of viewports) {
    await page.setViewportSize(size)
    const trigger = page.getByRole('button', { name: 'Kiểm tra và xác nhận', exact: true })
    await trigger.focus()
    await page.keyboard.press('Enter')
    const dialog = page.getByRole('dialog', { name: 'Xác nhận tạo công việc', exact: true })
    await expect(dialog.getByText('Công việc được duyệt từ bản nháp kiểm thử', { exact: true })).toBeVisible()
    await expect(dialog.getByText('Ước tính: 3,25 giờ', { exact: true })).toBeVisible()
    await expect(dialog.getByText('Công việc kiểm thử AI 2', { exact: true })).toHaveCount(0)
    await verifyViewport(page, 'ai-mvp-generator-confirm')
    await page.keyboard.press('Escape')
    await expect(trigger).toBeFocused()
  }
  expect(await countTasks(page.request)).toBe(0)
  await page.getByRole('button', { name: 'Kiểm tra và xác nhận', exact: true }).click()
  const confirmed = page.waitForResponse((response) => new URL(response.url()).pathname === `${scope().apiAi}${proposal.proposal_id}/confirm/` && response.request().method() === 'POST')
  await page.getByRole('dialog', { name: 'Xác nhận tạo công việc', exact: true }).getByRole('button', { name: 'Xác nhận tạo công việc', exact: true }).click()
  const confirmation = await confirmed
  expect(confirmation.status()).toBe(201)
  expect(confirmation.request().postDataJSON()).toMatchObject({
    payload: { tasks: [{ local_ref: 'item_1', estimated_hours: '3.25' }] },
  })
  const result = await confirmation.json() as { created_tasks: Record<string, string> }
  const taskId = result.created_tasks.item_1
  expect(Object.keys(result.created_tasks)).toEqual(['item_1'])
  const detail = await page.request.get(`${scope().apiTasks}${taskId}/`)
  expect(detail.status()).toBe(200)
  expect(await detail.json()).toMatchObject({ status: 'PENDING', parent_id: null, active_assignment: null, deadline: null, estimated_hours: '3.25' })
  const list = await page.request.get(scope().apiTasks)
  expect(list.status()).toBe(200)
  expect(await list.json()).toMatchObject({ count: 1, results: [{ id: taskId, estimated_hours: '3.25' }] })
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Đã tạo công việc', exact: true })).toBeVisible()
  await expect(page.getByText('Đã lưu: 3,25 giờ', { exact: true })).toBeVisible()
  const taskLink = page.getByRole('link', { name: 'Mở công việc item_1', exact: true })
  await expect(taskLink).toHaveAttribute('href', `${scope().tasks}/${taskId}`)
  await taskLink.click()
  await expect(page).toHaveURL(`${scope().tasks}/${taskId}`)
  await page.reload()
  await expect(page.getByText('Số giờ ước tính', { exact: true })).toBeVisible()
  await expect(page.getByText('3,25 giờ', { exact: true })).toBeVisible()
})

test('rejects a generated draft and reloads the terminal state without creating Tasks', async ({ page }) => {
  await login(page, 'ai_manager')
  await openTasksFromNavigation(page)
  const before = await countTasks(page.request)
  await page.getByRole('link', { name: 'Tạo công việc bằng AI', exact: true }).click()
  await page.getByLabel('Mô tả yêu cầu (bắt buộc)', { exact: true }).fill('Kiểm tra phụ đề cho video minh họa giả lập.')
  await page.getByLabel('Số công việc mong muốn', { exact: true }).fill('1')
  const generated = page.waitForResponse((response) => new URL(response.url()).pathname === scope().apiAi && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'AI tạo đề xuất', exact: true }).click()
  const reply = await generated
  expect(reply.status()).toBe(201)
  const proposal = await reply.json() as { proposal_id: string }
  await expect(page.getByLabel('Tên công việc 1', { exact: true })).toBeVisible()
  const trigger = page.getByRole('button', { name: 'Loại bỏ đề xuất', exact: true })
  await trigger.focus()
  await trigger.press('Enter')
  const dialog = page.getByRole('dialog', { name: 'Loại bỏ đề xuất', exact: true })
  await expect(dialog).toBeVisible()
  const rejected = page.waitForResponse((response) => new URL(response.url()).pathname === `${scope().apiAi}${proposal.proposal_id}/reject/` && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Xác nhận loại bỏ', exact: true }).press('Enter')
  const rejection = await rejected
  expect(rejection.status()).toBe(200)
  expect(await rejection.json()).toMatchObject({ status: 'REJECTED', payload: null, mode, provider, model })
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Đề xuất đã bị loại bỏ', exact: true })).toBeVisible()
  expect(await countTasks(page.request)).toBe(before)
})

test(`fake ${providerName} analyzes manual feedback, shows exact evidence and keeps edits out of Review`, async ({ page }) => {
  test.setTimeout(120_000)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await feedbackLogin(page, 'analyzer_manager')
  await feedbackNavigate(page)
  const before = feedbackState() as Record<string, unknown>
  const panel = await feedbackOpen(page)
  await expect(panel.getByText(`được phép chia sẻ với ${providerName}.`, { exact: false })).toBeVisible()
  const feedback = 'Dòng phụ đề đầu tiên chạy quá nhanh.'
  await panel.getByLabel('Nhập phản hồi bổ sung', { exact: true }).fill(feedback)
  const analyze = panel.getByRole('button', { name: 'Phân tích bằng AI', exact: true })
  await expect(analyze).toBeEnabled()
  await analyze.focus()
  await expect(analyze).toBeFocused()
  const analyzed = page.waitForResponse((response) => new URL(response.url()).pathname === feedbackScope().analyze && response.request().method() === 'POST', { timeout: 30_000 })
  await analyze.press('Enter')
  const response = await analyzed
  expect(response.status()).toBe(200)
  expect(response.request().postDataJSON()).toEqual({ sources: [], feedback_text: feedback })
  expect(response.request().headers()['idempotency-key']).toMatch(/^[\da-f-]{36}$/i)
  expect(await response.json()).toMatchObject({ mode, provider, model, usage: {
    input_tokens: 150, billable_output_tokens: 75, status: 'provider_reported',
  } })
  await expect(panel.getByRole('heading', { name: 'Kết quả phân tích phản hồi' })).toBeFocused()
  await expect(panel.getByText('Tóm tắt kiểm thử AI', { exact: true })).toBeVisible()
  await expect(panel.locator('blockquote')).toHaveText(feedback)
  await expect(panel.getByText(`${providerName} · ${model}.`, { exact: false })).toBeVisible()
  const action = panel.getByLabel('Gợi ý 1', { exact: true })
  await action.fill('Điều chỉnh tốc độ phụ đề sau khi xem lại.')
  for (const size of viewports) {
    await page.setViewportSize(size)
    await verifyViewport(page, 'ai-mvp-feedback-result')
  }
  await panel.getByRole('button', { name: 'Bỏ kết quả', exact: true }).click()
  await expect(analyze).toBeFocused()
  const after = feedbackState() as Record<string, unknown>
  for (const key of Object.keys(before).filter((key) => !key.startsWith('ai.'))) expect(after[key]).toEqual(before[key])
})

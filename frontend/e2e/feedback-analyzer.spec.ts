import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { csrf, feedbackExpireSessions, feedbackLogin, feedbackNavigate, feedbackOpen, feedbackScope, feedbackState, required } from './feedback-helpers'

test('real selected Review/Comment → synthetic result/citations, with every isolated model unchanged', async ({ page }) => {
  await feedbackLogin(page, 'analyzer_manager')
  await feedbackNavigate(page)
  const panel = await feedbackOpen(page)
  const before = feedbackState(), unsafe: string[] = []
  page.on('request', (request) => { if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) unsafe.push(new URL(request.url()).pathname) })
  expect(await panel.getByText('DELETED_ANALYZER_CONTENT_MUST_STAY_HIDDEN').count()).toBe(0)
  await panel.getByRole('checkbox', { name: 'Chọn Đánh giá bản nộp 1', exact: true }).check()
  await panel.getByRole('checkbox', { name: 'Chọn Bình luận 1', exact: true }).check()
  const focus = 'Synthetic only: minh họa phụ đề và âm thanh.'
  await panel.getByLabel('Trọng tâm phân tích (không bắt buộc)', { exact: true }).fill(focus)
  const analyzed = page.waitForResponse((response) => new URL(response.url()).pathname === feedbackScope().analyze && response.request().method() === 'POST')
  await panel.getByRole('button', { name: 'Phân tích phản hồi', exact: true }).click()
  const response = await analyzed
  expect(response.status()).toBe(200)
  expect(response.request().headers()['x-csrftoken']).toBeTruthy()
  expect(response.request().headers()['idempotency-key']).toBeUndefined()
  expect(response.request().postDataJSON()).toEqual({ sources: [{ kind: 'review', id: feedbackScope().review }, { kind: 'comment', id: feedbackScope().comment }], focus })
  const result = await response.json() as { mode: string; generated_by_ai: boolean; persisted: boolean; sources: { ref: string }[] }
  expect(result).toMatchObject({ mode: 'fixture_demo', generated_by_ai: false, persisted: false })
  expect(result.sources.map((source) => source.ref)).toEqual(['S1', 'S2'])
  await expect(panel.getByRole('heading', { name: 'Kết quả mô phỏng', exact: true })).toBeVisible()
  await expect(panel.getByText('S1 · Đánh giá bản nộp 1', { exact: true }).first()).toBeVisible()
  expect(JSON.stringify(result)).not.toContain('ANALYZER_SYNTHETIC_REVIEW')
  expect(JSON.stringify(result)).not.toContain(focus)
  expect(feedbackState()).toEqual(before)
  expect(unsafe).toEqual([feedbackScope().analyze])
  await expect(panel.getByRole('button', { name: /Áp dụng|Tạo công việc|Phê duyệt/ })).toHaveCount(0)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Kết quả mô phỏng', exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Phân tích phản hồi', exact: true })).toBeVisible()
})

test('deleted selection returns safe failure and refreshes sources without publishing a stale result', async ({ page }) => {
  await feedbackLogin(page, 'analyzer_manager')
  await feedbackNavigate(page)
  const panel = await feedbackOpen(page)
  await panel.getByRole('checkbox', { name: 'Chọn Bình luận 1', exact: true }).check()
  // API-driven fixture change, separate from the Analyze UI under test.
  expect((await page.request.delete(`${feedbackScope().apiTask}comments/${feedbackScope().comment}/`, { headers: { 'X-CSRFToken': await csrf(page.request) } })).status()).toBe(204)
  const before = feedbackState()
  await panel.getByRole('button', { name: 'Phân tích phản hồi', exact: true }).click()
  await expect(panel.getByRole('heading', { name: 'Kết quả mô phỏng', exact: true })).toHaveCount(0)
  await expect(panel.getByText(/Nguồn.*thay đổi|phản hồi.*thay đổi/).first()).toBeVisible()
  expect(feedbackState()).toEqual(before)
})

test('Viewer/Editor, foreign tenant and invalid CSRF cannot obtain analysis authority', async ({ page }) => {
  for (const actor of ['analyzer_viewer', 'analyzer_editor'] as const) {
    await feedbackLogin(page, actor)
    await feedbackNavigate(page, actor)
    await expect(page.getByRole('region', { name: 'Phân tích phản hồi', exact: true })).toHaveCount(0)
    const denied = await page.request.post(feedbackScope().analyze, { data: { sources: [{ kind: 'review', id: feedbackScope().review }] }, headers: { 'X-CSRFToken': await csrf(page.request) } })
    expect(denied.status()).toBe(403)
    await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
    await expect(page).toHaveURL(/\/login(?:\?|$)/)
  }
  await feedbackLogin(page, 'analyzer_manager')
  const body = { sources: [{ kind: 'review', id: feedbackScope().review }] }
  expect((await page.request.post(feedbackScope().analyze, { data: body })).status()).toBe(403)
  expect((await page.request.post(feedbackScope('analyzer_privacy').analyze, { data: body, headers: { 'X-CSRFToken': await csrf(page.request) } })).status()).toBe(404)
})

test('an in-flight real result cannot cross Task context; session expiry clears a later result', async ({ page }) => {
  test.setTimeout(90_000)
  await feedbackLogin(page, 'analyzer_privacy')
  await feedbackNavigate(page, 'analyzer_privacy')
  const panel = await feedbackOpen(page)
  await panel.getByRole('checkbox', { name: 'Chọn Đánh giá bản nộp 1', exact: true }).check()
  let release: () => void = () => {}, dispatched: () => void = () => {}
  const held = new Promise<void>((resolve) => { release = resolve })
  const sent = new Promise<void>((resolve) => { dispatched = resolve })
  await page.route('**/ai/feedback-analysis/', async (route) => {
    const response = await route.fetch()
    expect(response.status()).toBe(200)
    dispatched(); await held
    try { await route.fulfill({ response }) } catch { /* The old Task request may have been aborted. */ }
  })
  await panel.getByRole('button', { name: 'Phân tích phản hồi', exact: true }).click()
  await sent
  await page.getByRole('link', { name: 'Công việc', exact: true }).click()
  await page.getByRole('link', { name: 'Feedback analyzer_privacy Empty Task', exact: true }).click()
  release()
  await expect(page).toHaveURL(feedbackScope('analyzer_privacy').emptyDetail)
  await expect(page.getByRole('heading', { name: 'Kết quả mô phỏng', exact: true })).toHaveCount(0)
  await page.unroute('**/ai/feedback-analysis/')
  await page.getByRole('region', { name: 'Phân tích phản hồi', exact: true }).getByRole('button', { name: 'Phân tích phản hồi', exact: true }).click()
  await expect(page.getByText('Chưa có phản hồi phù hợp. Hãy dùng bình luận hoặc quy trình Review hiện có trước khi phân tích.', { exact: true })).toBeVisible()
  await page.goto(feedbackScope('analyzer_privacy').detail)
  const again = await feedbackOpen(page)
  await again.getByRole('checkbox', { name: 'Chọn Đánh giá bản nộp 1', exact: true }).check()
  await again.getByRole('button', { name: 'Phân tích phản hồi', exact: true }).click()
  await expect(again.getByRole('heading', { name: 'Kết quả mô phỏng', exact: true })).toBeVisible()
  feedbackExpireSessions()
  await page.evaluate(() => { window.dispatchEvent(new Event('focus')) })
  await expect(page).toHaveURL(/\/login(?:\?|$)/)
  await expect(page.getByRole('heading', { name: 'Kết quả mô phỏng', exact: true })).toHaveCount(0)
})

test('source selection/results are accessible across four viewports and keyboard focus', async ({ page }) => {
  test.setTimeout(90_000)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await feedbackLogin(page, 'analyzer_keyboard')
  await feedbackNavigate(page, 'analyzer_keyboard')
  const panel = await feedbackOpen(page)
  const checkbox = panel.getByRole('checkbox', { name: 'Chọn Đánh giá bản nộp 1', exact: true })
  await checkbox.focus(); await page.keyboard.press('Space')
  await expect(checkbox).toBeChecked()
  await panel.getByRole('button', { name: 'Phân tích phản hồi', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(panel.getByRole('heading', { name: 'Kết quả mô phỏng', exact: true })).toBeFocused()
  for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
    await page.setViewportSize(size)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
    expect(result.violations.map((item) => ({ id: item.id, targets: item.nodes.map((node) => node.target) }))).toEqual([])
    await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `feedback-result-${size.width}.png`), fullPage: true })
  }
})

import { randomUUID } from 'node:crypto'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { countTasks, csrf, fixtureId, generateUI, login, openTasksFromNavigation, required, scope } from './ai-helpers'

test('synthetic brief → real preview/edit → explicit confirmation creates scoped Task/Subtask only once', async ({ page }) => {
  test.setTimeout(120_000)
  const failures: string[] = []
  page.on('pageerror', (error) => failures.push(error.name))
  page.on('response', (response) => { if (response.status() >= 500) failures.push(`HTTP ${response.status()}`) })
  await login(page, 'ai_manager')
  await openTasksFromNavigation(page)
  await expect(page.getByRole('button', { name: 'Tạo công việc', exact: true })).toBeVisible()
  expect(await countTasks(page.request)).toBe(0)
  const proposal = await generateUI(page, 'ai_manager', 'Synthetic demo: prepare a caption review and contrast check.')
  expect(await countTasks(page.request)).toBe(0)
  await page.getByLabel('Tên công việc 1', { exact: true }).fill('Synthetic edited parent Integration')
  await page.getByLabel('Mô tả công việc 1', { exact: true }).fill('Human edited draft, not automatic AI execution.')
  await page.getByLabel('Mức ưu tiên 1', { exact: true }).selectOption('HIGH')
  await page.getByLabel('Thời hạn 1', { exact: true }).fill('2027-02-09T10:30')
  const deadline = await page.evaluate(() => new Date('2027-02-09T10:30').toISOString())
  await page.getByLabel('Tên công việc 2', { exact: true }).fill('Synthetic edited child Integration')
  await page.getByRole('button', { name: 'Kiểm tra và xác nhận', exact: true }).click()
  let dialog = page.getByRole('dialog', { name: 'Xác nhận tạo công việc', exact: true })
  await expect(dialog.getByText('AI ai_manager Workspace', { exact: true })).toBeVisible()
  await expect(dialog.getByText('Synthetic edited parent Integration', { exact: true })).toBeVisible()
  expect(await countTasks(page.request)).toBe(0)
  const confirmed = page.waitForResponse((response) => new URL(response.url()).pathname === `${scope().apiAi}${proposal.proposal_id}/confirm/` && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Xác nhận tạo công việc', exact: true }).click()
  const response = await confirmed
  expect(response.status()).toBe(201)
  const result = await response.json() as { status: string; payload: null; created_tasks: Record<string, string> }
  expect(result.status).toBe('CONFIRMED')
  expect(result.payload).toBeNull()
  await expect(page.getByRole('heading', { name: 'Đã tạo công việc', exact: true })).toBeVisible()
  expect(await countTasks(page.request)).toBe(2)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Đã tạo công việc', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Kiểm tra và xác nhận', exact: true })).toHaveCount(0)
  const root = await (await page.request.get(`${scope().apiTasks}${result.created_tasks.item_1}/`)).json() as { title: string; priority: string; deadline: string; parent_id: string | null; status: string }
  const child = await (await page.request.get(`${scope().apiTasks}${result.created_tasks.item_2}/`)).json() as { title: string; parent_id: string | null; status: string }
  expect(root).toMatchObject({ title: 'Synthetic edited parent Integration', priority: 'HIGH', parent_id: null, status: 'PENDING' })
  expect(Date.parse(root.deadline)).toBe(Date.parse(deadline))
  expect(child).toMatchObject({ title: 'Synthetic edited child Integration', parent_id: result.created_tasks.item_1, status: 'PENDING' })
  await page.getByRole('link', { name: 'Xem danh sách công việc', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Synthetic edited parent Integration', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Synthetic edited child Integration', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
  dialog = page.getByRole('dialog', { name: 'Tạo công việc', exact: true })
  await dialog.getByLabel('Tên công việc', { exact: true }).fill('Manual Task still works Integration')
  await dialog.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
  await expect(dialog).not.toBeVisible()
  expect(await countTasks(page.request)).toBe(3)
  expect(failures).toEqual([])
})

test('lost confirmation response reconciles through real GET; explicit same-key replay creates no duplicate Tasks', async ({ page }) => {
  test.setTimeout(120_000)
  await login(page, 'ai_recovery')
  await openTasksFromNavigation(page, 'ai_recovery')
  const proposal = await generateUI(page, 'ai_recovery', 'Synthetic response-loss rehearsal.')
  expect(await countTasks(page.request, 'ai_recovery')).toBe(0)
  const path = `${scope('ai_recovery').apiAi}${proposal.proposal_id}/confirm/`
  let key = '', body: Record<string, unknown> | null = null, confirms = 0, reads = 0
  page.on('request', (request) => {
    if (new URL(request.url()).pathname === path && request.method() === 'POST') confirms++
    if (new URL(request.url()).pathname === `${scope('ai_recovery').apiAi}${proposal.proposal_id}/` && request.method() === 'GET') reads++
  })
  // Fault injection only: send the actual UI request to Django, commit it, then
  // lose its response. No JSON response or backend state is mocked.
  await page.route('**/ai/task-proposals/*/confirm/', async (route) => {
    key = route.request().headers()['idempotency-key'] || ''
    body = route.request().postDataJSON() as Record<string, unknown>
    const response = await route.fetch()
    expect(response.status()).toBe(201)
    await route.abort('connectionfailed')
  })
  await page.getByRole('button', { name: 'Kiểm tra và xác nhận', exact: true }).click()
  await page.getByRole('dialog', { name: 'Xác nhận tạo công việc', exact: true }).getByRole('button', { name: 'Xác nhận tạo công việc', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Đã tạo công việc', exact: true })).toBeVisible()
  expect(confirms).toBe(1)
  expect(reads).toBeGreaterThan(0)
  expect(await countTasks(page.request, 'ai_recovery')).toBe(2)
  await page.unroute('**/ai/task-proposals/*/confirm/')
  expect(key).toMatch(/^[0-9a-f-]{36}$/i)
  expect(body).not.toBeNull()
  // Supporting API replay probe, distinct from the successful UI mutation above.
  expect((await page.request.post(path, { data: body, headers: { 'X-CSRFToken': await csrf(page.request), 'Idempotency-Key': key } })).status()).toBe(200)
  expect((await page.request.post(path, { data: body, headers: { 'X-CSRFToken': await csrf(page.request), 'Idempotency-Key': randomUUID() } })).status()).toBe(409)
  expect(await countTasks(page.request, 'ai_recovery')).toBe(2)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Đã tạo công việc', exact: true })).toBeVisible()
})

test('current Viewer, another proposal actor and foreign tenant cannot obtain AI authority', async ({ page }) => {
  await login(page, 'ai_viewer')
  await openTasksFromNavigation(page, 'ai_viewer')
  await expect(page.getByRole('link', { name: 'Tạo công việc bằng AI', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Tạo công việc bằng AI', exact: true })).toHaveCount(0)
  expect((await page.request.fetch(scope().apiAi, { method: 'OPTIONS' })).status()).toBe(403)
  expect((await page.request.post(scope().apiAi, { data: { scenario_id: 'task-tree-v1' }, headers: { 'X-CSRFToken': await csrf(page.request), 'Idempotency-Key': randomUUID() } })).status()).toBe(403)
  await page.goto(`${scope().tasks}/generate`)
  await expect(page.getByText('Chức năng đề xuất chỉ dành cho người có quyền quản lý công việc trong không gian đang hoạt động.', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Mô tả yêu cầu giả lập', { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
  await expect(page).toHaveURL(/\/login(?:\?|$)/)
  await login(page, 'ai_peer')
  const foreign = `/api/v1/profiles/${fixtureId('ai_recovery_profile')}/workspaces/${fixtureId('ai_recovery_workspace')}/ai/task-proposals/`
  expect((await page.request.fetch(foreign, { method: 'OPTIONS' })).status()).toBe(404)
  expect((await page.request.get(`${foreign}${randomUUID()}/`)).status()).toBe(404)
  expect((await page.request.post(scope().apiAi, { data: { scenario_id: 'task-tree-v1' } })).status()).toBe(403)
  await page.goto(scope().tasks)
  const before = await countTasks(page.request)
  const peerProposal = await generateUI(page, 'ai_peer', 'Synthetic same-tenant actor-bound proposal.')
  expect(await countTasks(page.request)).toBe(before)
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
  await expect(page).toHaveURL(/\/login(?:\?|$)/)
  await login(page, 'ai_manager')
  const peerPath = `${scope().apiAi}${peerProposal.proposal_id}/`
  expect((await page.request.get(peerPath)).status()).toBe(404)
  expect((await page.request.post(`${peerPath}confirm/`, {
    data: { confirmed: true, proposal_revision: 1, payload: peerProposal.payload },
    headers: { 'X-CSRFToken': await csrf(page.request), 'Idempotency-Key': randomUUID() },
  })).status()).toBe(404)
  await page.goto(`${scope().tasks}/generate?proposal=${peerProposal.proposal_id}`)
  await expect(page.getByLabel('Tên công việc 1', { exact: true })).toHaveCount(0)
  expect(await countTasks(page.request)).toBe(before)
})

test('AI draft/confirmation stay accessible on mobile/tablet/desktop/landscape and cancel leaves zero Tasks', async ({ page }) => {
  test.setTimeout(120_000)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await login(page, 'ai_keyboard')
  await openTasksFromNavigation(page, 'ai_keyboard')
  const proposal = await generateUI(page, 'ai_keyboard', 'Synthetic keyboard and responsive preview.')
  expect(proposal.status).toBe('AVAILABLE')
  for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
    await page.setViewportSize(size)
    const title = page.getByLabel('Tên công việc 1', { exact: true })
    await title.focus()
    await expect(title).toBeFocused()
    await page.getByRole('button', { name: 'Kiểm tra và xác nhận', exact: true }).focus()
    await page.keyboard.press('Enter')
    const dialog = page.getByRole('dialog', { name: 'Xác nhận tạo công việc', exact: true })
    await expect(dialog).toBeVisible()
    expect(await countTasks(page.request, 'ai_keyboard')).toBe(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
    expect(result.violations.map((item) => ({ id: item.id, targets: item.nodes.map((node) => node.target) }))).toEqual([])
    await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `ai-confirm-${size.width}.png`), fullPage: true })
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'Kiểm tra và xác nhận', exact: true })).toBeFocused()
    const preview = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
    expect(preview.violations.map((item) => ({ id: item.id, targets: item.nodes.map((node) => node.target) }))).toEqual([])
    await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `ai-preview-${size.width}.png`), fullPage: true })
  }
  await page.getByRole('link', { name: 'Hủy đề xuất', exact: true }).click()
  const discard = page.getByRole('dialog', { name: 'Rời bản nháp đề xuất', exact: true })
  await expect(discard).toBeVisible()
  await discard.getByRole('button', { name: 'Ở lại chỉnh sửa', exact: true }).click()
  await expect(page.getByLabel('Tên công việc 1', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Hủy đề xuất', exact: true }).click()
  await page.getByRole('dialog', { name: 'Rời bản nháp đề xuất', exact: true }).getByRole('button', { name: 'Rời trang', exact: true }).click()
  await expect(page).toHaveURL(scope('ai_keyboard').tasks)
  expect(await countTasks(page.request, 'ai_keyboard')).toBe(0)
})


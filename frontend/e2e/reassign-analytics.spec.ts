import { createHash } from 'node:crypto'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type BrowserContext, type Locator, type Page } from '@playwright/test'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated reassignment/analytics launcher.')
  return value
}
const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Invalid owned fixture identity.')
function fixtureId(label: string): string {
  const hash = createHash('sha1').update(Buffer.from(runId, 'hex')).update(label, 'utf8').digest()
  hash[6] = (hash.readUInt8(6) & 0x0f) | 0x50
  hash[8] = (hash.readUInt8(8) & 0x3f) | 0x80
  const hex = hash.subarray(0, 16).toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
const profileId = fixtureId('analytics_profile'), workspaceId = fixtureId('analytics_workspace')
const siblingId = fixtureId('analytics_sibling_workspace'), transferId = fixtureId('analytics_transfer_task'), completedId = fixtureId('analytics_completed_task')
const editorAId = fixtureId('analytics_editor_a_membership'), editorBId = fixtureId('analytics_editor_b_membership')
const editorAName = 'Nguyễn Editor A', editorBName = 'analytics_editor_b'
const apiBase = `/api/v1/profiles/${profileId}/workspaces/${workspaceId}/tasks/`
const analyticsBase = `/api/v1/profiles/${profileId}/analytics/`
const taskBase = `/profiles/${profileId}/workspaces/${workspaceId}/tasks/`
const bigTotal = '1000000000009599999'
const formattedBigTotal = '1.000.000.000.009.599.999 ₫'
type Actor = 'manager' | 'editor_a' | 'editor_b' | 'viewer'
type Assignment = { id: string; assigned_at: string; profile_membership_id: string; display_name: string | null }
type TaskRead = { id: string; status: string; active_assignment: Assignment | null; estimated_compensation_vnd: string | null }
type Employee = { id: string; display_name: string | null; active_tasks: number; approved_tasks: number; finance: { active_total_vnd: string | null; approved_total_vnd: string | null; approved_unknown_tasks: number } | null }
type Summary = {
  scope: { mode: 'self' | 'management'; from: string; to: string; workspace_id: string | null }
  kpis: { total_tasks: number; approved_tasks: number; unassigned_tasks: number }
  finance: { estimated_total_vnd: string | null; approved_total_vnd: string | null; approved_unknown_tasks: number } | null
  distribution: { status: string; count: number }[]; approval_trend: { month: string; count: number }[]
}
const viewports = [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]

// All accounts/data below are deterministic fixture setup in the owned database.
// Business mutations under test are performed through the actual React dialogs.
async function login(page: Page, actor: Actor) {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(`analytics_${actor}.${runId}@example.test`)
  try {
    await page.getByLabel('Mật khẩu', { exact: true }).evaluate((element, secret) => {
      if (!(element instanceof HTMLInputElement) || element.type !== 'password') throw new Error('Masked input required.')
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      if (!setter) throw new Error('Native setter unavailable.')
      setter.call(element, secret); element.dispatchEvent(new Event('input', { bubbles: true }))
    }, required('HT_FRONTEND_TEST_PASSWORD'))
  } catch { throw new Error('Isolated masked credential entry failed.') }
  const received = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/login/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await received).status()).toBe(200)
  await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
}
async function readTask(page: Page, id = transferId): Promise<TaskRead> {
  const response = await page.request.get(`${apiBase}${id}/`)
  expect(response.status()).toBe(200)
  return response.json() as Promise<TaskRead>
}
async function token(page: Page) {
  const response = await page.request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  return (await response.json() as { csrf_token: string }).csrf_token
}
async function summary(page: Page, workspace = workspaceId): Promise<Summary> {
  const response = await page.request.get(`${analyticsBase}?workspace_id=${workspace}`)
  expect(response.status()).toBe(200)
  return response.json() as Promise<Summary>
}
async function employees(page: Page): Promise<Employee[]> {
  const response = await page.request.get(`${analyticsBase}employees/?workspace_id=${workspaceId}`)
  expect(response.status()).toBe(200)
  return (await response.json() as { results: Employee[] }).results
}
function factsAssignment(page: Page) {
  return page.locator('.task-detail-grid .workspace-facts dl > div').filter({ has: page.getByText('Phân công', { exact: true }) }).locator('dd')
}
function employeeRow(page: Page, name: string) {
  return page.getByRole('table').getByRole('row').filter({ has: page.getByRole('rowheader', { name: new RegExp(name) }) })
}
async function openAnalytics(page: Page) {
  await page.goto(`/analytics?profile_id=${profileId}&workspace_id=${workspaceId}`)
  await expect(page.getByRole('heading', { name: 'Thống kê', level: 1, exact: true })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Tài chính công việc', exact: true })).toBeVisible()
  await expect(page.getByRole('table')).toBeVisible()
}
async function assertNoOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
}
async function assertAxe(page: Page) {
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
}
async function visibleFocus(locator: Locator) {
  expect(await locator.evaluate((element) => {
    const rect = element.getBoundingClientRect(), style = getComputedStyle(element)
    return element === document.activeElement && rect.bottom > 0 && rect.top < innerHeight && style.outlineStyle !== 'none' && Number.parseFloat(style.outlineWidth) > 0
  })).toBe(true)
}

test.describe('Reassignment and analytics — real UI with isolated PostgreSQL', () => {
  test.describe.configure({ mode: 'serial' })
  test.use({ actionTimeout: 15_000 })
  const contexts: BrowserContext[] = [], failures: string[] = [], externalRequests: string[] = []
  let manager: Page, editorA: Page, editorB: Page, viewer: Page
  function observe(page: Page) {
    page.on('pageerror', (error) => failures.push(error.name))
    page.on('response', (response) => { if (response.status() >= 500) failures.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })
    page.on('request', (request) => {
      const url = new URL(request.url())
      if (['http:', 'https:'].includes(url.protocol) && !['127.0.0.1', 'localhost'].includes(url.hostname)) externalRequests.push(url.hostname)
    })
  }
  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext({ baseURL: test.info().project.use.baseURL, locale: 'en-US', timezoneId: 'Asia/Ho_Chi_Minh', viewport: { width: 1440, height: 1000 } })
    contexts.push(context); manager = await context.newPage(); observe(manager); await login(manager, 'manager')
  })
  test.afterEach(() => { expect(failures).toEqual([]); expect(externalRequests).toEqual([]) })
  test.afterAll(async () => { for (const context of contexts) await context.close() })

  test('management dashboard uses exact cohort/event money and accessible responsive employee charts', async () => {
    test.setTimeout(180_000)
    await manager.goto(`/analytics?profile_id=${profileId}`)
    await expect(manager.getByRole('status').filter({ hasText: 'Thống kê của tôi' })).toBeVisible()
    const changed = manager.waitForResponse((response) => {
      const url = new URL(response.url())
      return url.pathname === analyticsBase && url.searchParams.get('workspace_id') === workspaceId
    })
    await manager.getByRole('combobox', { name: 'Chọn Workspace', exact: true }).selectOption(workspaceId)
    const result = await changed
    expect(result.status()).toBe(200)
    const data = await result.json() as Summary
    expect(data.scope.mode).toBe('management')
    expect(data.kpis.total_tasks).toBe(5); expect(data.kpis.approved_tasks).toBe(1)
    expect(data.kpis.unassigned_tasks).toBe(2)
    expect(data.distribution.reduce((sum, row) => sum + row.count, 0)).toBe(5)
    expect(data.approval_trend.reduce((sum, row) => sum + row.count, 0)).toBe(2)
    expect(data.finance?.estimated_total_vnd).toBe(bigTotal)
    expect(data.finance?.approved_total_vnd).toBe('700000')
    expect(data.finance?.approved_unknown_tasks).toBe(1)
    const nav = manager.getByRole('navigation', { name: 'Điều hướng chính', exact: true })
    await expect(nav.getByRole('link', { name: 'Thống kê', exact: true })).toHaveAttribute('aria-current', 'page')
    const labels = await nav.getByRole('link').allTextContents()
    expect(labels.findIndex((value) => value.includes('Thống kê'))).toBe(labels.findIndex((value) => value.includes('Tổ chức')) + 1)
    expect(labels.findIndex((value) => value.includes('Thông báo'))).toBe(labels.findIndex((value) => value.includes('Thống kê')) + 1)
    await expect(manager.getByRole('region', { name: 'Sáu chỉ số công việc' }).locator('.analytics-kpi')).toHaveCount(6)
    await expect(manager.getByText(formattedBigTotal, { exact: true })).toBeVisible()
    await expect(manager.getByRole('region', { name: 'Tài chính công việc' }).getByText('700.000 ₫', { exact: true })).toBeVisible()
    await expect(manager.getByText(/1 lượt nghiệm thu cũ chưa có snapshot/)).toBeVisible()
    await expect(employeeRow(manager, editorAName).getByRole('cell').nth(0)).toHaveText('2')
    await expect(employeeRow(manager, editorBName).getByRole('cell').nth(0)).toHaveText('0')
    await manager.getByRole('combobox', { name: 'Sắp xếp nhân viên', exact: true }).selectOption('-approved_value')
    await expect(manager.getByRole('table').getByRole('row').nth(1)).toContainText(editorBName)
    await manager.getByLabel('Tìm nhân viên', { exact: true }).fill(editorBName)
    await manager.getByRole('button', { name: 'Tìm kiếm', exact: true }).click()
    await expect(manager.getByRole('table').locator('tbody tr')).toHaveCount(1)
    await manager.getByRole('button', { name: `Xem chi tiết ${editorBName}`, exact: true }).click()
    const detail = manager.locator('.analytics-employee-detail')
    await expect(detail.getByRole('heading', { name: editorBName, exact: true })).toBeFocused()
    await expect(detail.getByRole('link', { name: 'Đã nghiệm thu trong kỳ', exact: true })).toHaveAttribute('href', `${taskBase}${completedId}`)
    await expect(detail.getByText('700.000 ₫', { exact: true })).toBeVisible()
    await manager.getByRole('button', { name: 'Đóng chi tiết', exact: true }).click()
    await manager.getByLabel('Tìm nhân viên', { exact: true }).fill('')
    await manager.getByRole('button', { name: 'Tìm kiếm', exact: true }).click()
    await expect(employeeRow(manager, editorAName)).toBeVisible()
    await manager.emulateMedia({ reducedMotion: 'reduce' })
    for (const size of viewports) {
      await manager.setViewportSize(size)
      await assertNoOverflow(manager)
      const legend = manager.getByRole('list', { name: 'Số lượng và tỷ lệ từng trạng thái' }).getByRole('button').first()
      await legend.focus(); await manager.keyboard.press('Enter'); await visibleFocus(legend)
      await expect(legend).toHaveAttribute('aria-pressed', 'true')
      const month = manager.getByRole('region', { name: 'Số Task nghiệm thu từng tháng' }).getByRole('button').first()
      await month.focus(); await manager.keyboard.press('Enter'); await visibleFocus(month)
      await expect(month).toHaveAttribute('aria-pressed', 'true')
      await assertAxe(manager)
      if (size.width === 375 || size.width === 1440) await manager.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `analytics-${size.width}.png`), fullPage: true })
    }
    await manager.setViewportSize({ width: 1440, height: 1000 })
  })

  test('transfer, unassign and assign again are confirmed through UI and update current analytics without changing historical credit', async () => {
    test.setTimeout(180_000)
    const before = await summary(manager)
    await manager.goto(`${taskBase}${transferId}`)
    await expect(factsAssignment(manager)).toHaveText(editorAName)
    for (const size of viewports) {
      await manager.setViewportSize(size)
      const trigger = manager.getByRole('button', { name: 'Thay đổi phân công', exact: true })
      await trigger.focus(); await manager.keyboard.press('Enter')
      const modal = manager.getByRole('dialog', { name: 'Thay đổi phân công', exact: true })
      await expect(modal).toBeVisible()
      expect(await modal.evaluate((element) => element.contains(document.activeElement))).toBe(true)
      await manager.keyboard.press('Tab')
      expect(await modal.evaluate((element) => element.contains(document.activeElement))).toBe(true)
      await assertNoOverflow(manager); await assertAxe(manager)
      if (size.width === 375 || size.width === 1440) await manager.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `reassignment-dialog-${size.width}.png`), fullPage: true })
      await manager.keyboard.press('Escape')
      await expect(modal).not.toBeVisible(); await expect(trigger).toBeFocused()
    }
    await manager.setViewportSize({ width: 1440, height: 1000 })
    await manager.getByRole('button', { name: 'Thay đổi phân công', exact: true }).click()
    let dialog = manager.getByRole('dialog', { name: 'Thay đổi phân công', exact: true })
    await expect(dialog.getByLabel('Thành viên', { exact: true }).locator(`option[value="${editorAId}"]`)).toHaveCount(0)
    const targetLabel = await dialog.getByLabel('Thành viên', { exact: true }).locator(`option[value="${editorBId}"]`).textContent()
    await dialog.getByLabel('Thành viên', { exact: true }).selectOption(editorBId)
    await dialog.getByLabel('Lý do chuyển giao', { exact: false }).fill('Bàn giao do lịch làm việc thay đổi; dữ liệu kiểm thử cô lập.')
    await dialog.getByRole('button', { name: 'Kiểm tra thay đổi', exact: true }).click()
    await expect(dialog.getByText(`Chuyển Task từ ${editorAName} sang ${targetLabel}?`, { exact: false })).toBeVisible()
    const transferred = manager.waitForResponse((response) => new URL(response.url()).pathname === `${apiBase}${transferId}/assign/` && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Xác nhận chuyển giao', exact: true }).click()
    const transferResponse = await transferred
    expect(transferResponse.status()).toBe(200)
    expect((await transferResponse.json() as TaskRead).active_assignment?.profile_membership_id).toBe(editorBId)
    await expect(factsAssignment(manager)).toHaveText(editorBName)
    await manager.reload()
    await expect(factsAssignment(manager)).toHaveText(editorBName)
    const after = await summary(manager), rows = await employees(manager)
    expect(after.kpis.total_tasks).toBe(before.kpis.total_tasks)
    expect(after.finance).toEqual(before.finance)
    expect(rows.find((row) => row.id === editorAId)?.active_tasks).toBe(1)
    expect(rows.find((row) => row.id === editorBId)?.active_tasks).toBe(1)
    expect(rows.find((row) => row.id === editorAId)?.finance?.active_total_vnd).toBe('100000')
    expect(rows.find((row) => row.id === editorBId)?.finance?.active_total_vnd).toBe('500000')
    expect(rows.find((row) => row.id === editorBId)?.finance?.approved_total_vnd).toBe('700000')
    // Keep the React/query-cache session alive while navigating back to the
    // dashboard after the mutation; no document reload substitutes for this.
    await manager.getByRole('navigation', { name: 'Điều hướng chính', exact: true }).getByRole('link', { name: 'Thống kê', exact: true }).click()
    await manager.getByRole('combobox', { name: 'Chọn Workspace', exact: true }).selectOption(workspaceId)
    await expect(employeeRow(manager, editorAName).getByRole('cell').nth(0)).toHaveText('1')
    await expect(employeeRow(manager, editorBName).getByRole('cell').nth(0)).toHaveText('1')
    await manager.getByRole('button', { name: `Xem chi tiết ${editorBName}`, exact: true }).click()
    await manager.locator('.analytics-employee-detail').getByRole('link', { name: 'Chuyển giao an toàn', exact: true }).click()
    await expect(factsAssignment(manager)).toHaveText(editorBName)
    const assigned = await readTask(manager)
    await manager.getByRole('button', { name: 'Thay đổi phân công', exact: true }).click()
    dialog = manager.getByRole('dialog', { name: 'Thay đổi phân công', exact: true })
    await dialog.getByRole('radio', { name: 'Gỡ phân công', exact: true }).check()
    await dialog.getByLabel('Lý do gỡ phân công', { exact: false }).fill('Tạm thời chờ phân công lại.')
    await dialog.getByRole('button', { name: 'Kiểm tra thay đổi', exact: true }).click()
    await expect(dialog.getByText(`Gỡ ${editorBName} khỏi Task này?`, { exact: false })).toBeVisible()
    const removed = manager.waitForResponse((response) => new URL(response.url()).pathname === `${apiBase}${transferId}/unassign/` && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Xác nhận gỡ phân công', exact: true }).click()
    expect((await removed).status()).toBe(200)
    await expect(factsAssignment(manager)).toHaveText('Chưa phân công')
    const unassigned = await readTask(manager)
    expect(assigned.status).toBe('ASSIGNED')
    expect(unassigned.active_assignment).toBeNull(); expect(unassigned.status).toBe('PENDING')
    expect((await summary(manager)).kpis.unassigned_tasks).toBe(before.kpis.unassigned_tasks + 1)
    await manager.getByRole('button', { name: 'Phân công nhân viên', exact: true }).click()
    dialog = manager.getByRole('dialog', { name: 'Phân công công việc', exact: true })
    await dialog.getByLabel('Thành viên', { exact: true }).selectOption(editorAId)
    const restored = manager.waitForResponse((response) => new URL(response.url()).pathname === `${apiBase}${transferId}/assign/` && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Xác nhận phân công', exact: true }).click()
    expect((await restored).status()).toBe(200)
    await expect(factsAssignment(manager)).toHaveText(editorAName)
    expect((await summary(manager)).finance).toEqual(before.finance)
    // Denied API checks below are intentionally NOT claimed as UI mutations.
    await manager.goto(`${taskBase}${completedId}`)
    await expect(manager.getByRole('heading', { name: 'Đã nghiệm thu trong kỳ', exact: true })).toBeVisible()
    await expect(manager.getByRole('button', { name: 'Thay đổi phân công', exact: true })).toHaveCount(0)
    const completed = await readTask(manager, completedId)
    const denied = await manager.request.post(`${apiBase}${completedId}/assign/`, { headers: { 'X-CSRFToken': await token(manager) }, data: { target_profile_membership_id: editorAId, expected_assignment_id: completed.active_assignment?.id, expected_assigned_at: completed.active_assignment?.assigned_at } })
    expect(denied.status()).toBe(409)
    expect((await readTask(manager, completedId)).active_assignment).toEqual(completed.active_assignment)
    const current = await readTask(manager)
    const csrfDenied = await manager.request.post(`${apiBase}${transferId}/unassign/`, { headers: { 'X-CSRFToken': 'invalid-isolated-csrf' }, data: { expected_assignment_id: current.active_assignment?.id, expected_assigned_at: current.active_assignment?.assigned_at } })
    expect(csrfDenied.status()).toBe(403)
    expect((await readTask(manager)).active_assignment).toEqual(current.active_assignment)
  })

  test('personal views and notification recipients remain isolated; Viewer cannot mutate or receive coworker money', async ({ browser }) => {
    test.setTimeout(150_000)
    for (const actor of ['editor_a', 'editor_b', 'viewer'] as const) {
      const context = await browser.newContext({ baseURL: test.info().project.use.baseURL, locale: 'en-US', timezoneId: 'Asia/Ho_Chi_Minh', viewport: { width: 1440, height: 1000 } })
      contexts.push(context)
      const page = await context.newPage(); observe(page); await login(page, actor)
      if (actor === 'editor_a') editorA = page
      if (actor === 'editor_b') editorB = page
      if (actor === 'viewer') viewer = page
    }
    for (const [page, name] of [[editorA, editorAName], [editorB, editorBName]] as const) {
      await page.goto(`/analytics?profile_id=${profileId}&workspace_id=${workspaceId}`)
      await expect(page.getByRole('status').filter({ hasText: 'Thống kê của tôi' })).toBeVisible()
      await expect(page.getByRole('table').locator('tbody tr')).toHaveCount(1)
      await expect(employeeRow(page, name)).toBeVisible()
      await expect(page.getByText(formattedBigTotal, { exact: true })).toHaveCount(0)
      const notifications = await page.request.get('/api/v1/notifications/?page_size=100')
      expect(notifications.status()).toBe(200)
      const rows = (await notifications.json() as { results: { task_id: string; event_type: string }[] }).results.filter((row) => row.task_id === transferId)
      expect(rows.some((row) => row.event_type === 'TASK_ASSIGNED')).toBe(true)
      expect(rows.some((row) => row.event_type === 'TASK_UNASSIGNED')).toBe(true)
      await page.goto('/notifications')
      await expect(page.getByRole('article', { name: 'Task assignment removed', exact: true })).toBeVisible()
      await expect(page.getByRole('article', { name: 'Task assignment removed', exact: true }).getByRole('link', { name: 'Mở công việc', exact: true })).toHaveAttribute('href', `${taskBase}${transferId}`)
    }
    const personal = await summary(editorB)
    expect(personal.finance?.approved_total_vnd).toBe('700000')
    expect(personal.approval_trend.reduce((sum, row) => sum + row.count, 0)).toBe(1)
    await viewer.goto(`/analytics?profile_id=${profileId}&workspace_id=${workspaceId}`)
    await expect(viewer.getByRole('status').filter({ hasText: 'Thống kê của tôi' })).toBeVisible()
    await expect(viewer.getByRole('region', { name: 'Thù lao dự kiến của tôi', exact: true })).toHaveCount(0)
    await expect(viewer.getByRole('columnheader', { name: 'Giá trị nghiệm thu', exact: true })).toHaveCount(0)
    const viewerSummary = await summary(viewer)
    expect(viewerSummary.finance).toBeNull()
    const viewerRows = await employees(viewer)
    expect(viewerRows.every((row) => row.finance === null && ![editorAId, editorBId].includes(row.id))).toBe(true)
    expect(JSON.stringify(viewerSummary)).not.toContain('700000'); expect(JSON.stringify(viewerSummary)).not.toContain(bigTotal)
    await viewer.goto(`${taskBase}${transferId}`)
    await expect(factsAssignment(viewer)).toHaveText(editorAName)
    await expect(viewer.getByRole('button', { name: 'Thay đổi phân công', exact: true })).toHaveCount(0)
    const projection = await readTask(viewer)
    expect(projection.estimated_compensation_vnd).toBeNull()
    const forbidden = await viewer.request.post(`${apiBase}${transferId}/assign/`, { headers: { 'X-CSRFToken': await token(viewer) }, data: { target_profile_membership_id: editorBId } })
    expect(forbidden.status()).toBe(403)
    const current = await readTask(editorA)
    const memberDenied = await editorA.request.post(`${apiBase}${transferId}/unassign/`, { headers: { 'X-CSRFToken': await token(editorA) }, data: { expected_assignment_id: current.active_assignment?.id, expected_assigned_at: current.active_assignment?.assigned_at } })
    expect(memberDenied.status()).toBe(403)
    const foreign = fixtureId('management_profile')
    expect((await manager.request.get(`/api/v1/profiles/${foreign}/analytics/`)).status()).toBe(404)
    expect((await manager.request.get(`${analyticsBase}?workspace_id=${fixtureId('management_workspace')}`)).status()).toBe(404)
    expect((await viewer.request.get(`${analyticsBase}employees/${editorAId}/?workspace_id=${workspaceId}`)).status()).toBe(404)
    await assertAxe(viewer)
  })

  test('workspace and date controls show honest self/empty scopes and reject reversed dates without fetching', async () => {
    test.setTimeout(90_000)
    await openAnalytics(manager)
    const sibling = manager.waitForResponse((response) => {
      const url = new URL(response.url())
      return url.pathname === analyticsBase && url.searchParams.get('workspace_id') === siblingId
    })
    await manager.getByRole('combobox', { name: 'Chọn Workspace', exact: true }).selectOption(siblingId)
    const siblingData = await (await sibling).json() as Summary
    expect(siblingData.scope.mode).toBe('self'); expect(siblingData.kpis.total_tasks).toBe(0)
    await expect(manager.getByRole('status').filter({ hasText: 'Thống kê của tôi' })).toBeVisible()
    await manager.getByRole('combobox', { name: 'Chọn Workspace', exact: true }).selectOption(workspaceId)
    await expect(manager.getByRole('region', { name: 'Tài chính công việc' })).toBeVisible()
    await manager.getByRole('combobox', { name: 'Chọn thời gian', exact: true }).selectOption('range')
    await manager.getByLabel('Từ ngày', { exact: true }).fill('2027-12-31')
    await manager.getByLabel('Đến ngày', { exact: true }).fill('2027-01-01')
    let invalidRequests = 0
    const watch = (request: { url: () => string }) => { if (new URL(request.url()).pathname === analyticsBase) invalidRequests++ }
    manager.on('request', watch)
    await manager.getByRole('button', { name: 'Áp dụng thời gian', exact: true }).click()
    await expect(manager.getByRole('alert').filter({ hasText: 'Ngày bắt đầu phải trước hoặc bằng ngày kết thúc hợp lệ.' })).toBeVisible()
    expect(invalidRequests).toBe(0); manager.off('request', watch)
    const futureYear = Number((await summary(manager)).scope.from.slice(0, 4)) + 2
    await manager.getByLabel('Từ ngày', { exact: true }).fill(`${futureYear}-01-01`)
    await manager.getByLabel('Đến ngày', { exact: true }).fill(`${futureYear}-01-31`)
    const empty = manager.waitForResponse((response) => {
      const url = new URL(response.url())
      return url.pathname === analyticsBase && url.searchParams.get('from') === `${futureYear}-01-01`
    })
    await manager.getByRole('button', { name: 'Áp dụng thời gian', exact: true }).click()
    const emptyData = await (await empty).json() as Summary
    expect(emptyData.kpis.total_tasks).toBe(0)
    expect(emptyData.finance?.estimated_total_vnd).toBeNull()
    expect(emptyData.finance?.approved_total_vnd).toBeNull()
    await expect(manager.getByText('Chưa có Task tạo trong khoảng thời gian này.', { exact: true })).toBeVisible()
    await assertNoOverflow(manager); await assertAxe(manager)
  })
})

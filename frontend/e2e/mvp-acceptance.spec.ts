import { createHash } from 'node:crypto'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated acceptance launcher.')
  return value
}

const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Invalid isolated run identity.')
function fixtureId(label: string): string {
  const hash = createHash('sha1').update(Buffer.from(runId, 'hex')).update(label, 'utf8').digest()
  hash[6] = (hash.readUInt8(6) & 0x0f) | 0x50
  hash[8] = (hash.readUInt8(8) & 0x3f) | 0x80
  const hex = hash.subarray(0, 16).toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
const profileId = fixtureId('management_profile'), workspaceId = fixtureId('management_workspace')
const apiTasks = `/api/v1/profiles/${profileId}/workspaces/${workspaceId}/tasks/`
const taskBase = `/profiles/${profileId}/workspaces/${workspaceId}/tasks`
const taskTitle = 'MVP acceptance task Integration'
const childTitle = 'MVP acceptance subtask Integration'
type Role = 'manager' | 'editor' | 'viewer'
type Task = { id: string; parent_id: string | null; status: string; priority: string; deadline: string | null; can_start: boolean; can_submit: boolean; active_assignment: { profile_membership_id: string } | null }
type Deliverable = { id: string; revision: number; can_approve: boolean; can_request_changes: boolean }
type Notification = { id: string; task_id: string; event_type: string; is_read: boolean }

async function csrf(request: APIRequestContext): Promise<string> {
  const response = await request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  return (await response.json() as { csrf_token: string }).csrf_token
}
// API helpers are assertions/negative probes, never successful business setup.
async function rejectedPost(request: APIRequestContext, path: string, data: Record<string, unknown>, status: number) {
  expect((await request.post(path, { headers: { 'X-CSRFToken': await csrf(request) }, data })).status()).toBe(status)
}
async function getTask(page: Page, id: string): Promise<Task> {
  const response = await page.request.get(`${apiTasks}${id}/`)
  expect(response.status()).toBe(200)
  return response.json() as Promise<Task>
}
async function signIn(page: Page, role: Role) {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(`${role}.${runId}@example.test`)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(required('HT_FRONTEND_TEST_PASSWORD'))
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  await expect(page.locator('.account__name')).toHaveText({ manager: 'Quản lý Kiểm thử', editor: 'Nhân viên Kiểm thử', viewer: 'Người xem Kiểm thử' }[role])
  // Login may legitimately restore the protected route from the previous
  // logout. Navigate through the real sidebar before the next journey segment.
  await page.getByRole('navigation', { name: 'Điều hướng chính', exact: true }).getByRole('link', { name: 'Tổng quan', exact: true }).click()
  await expect(page).toHaveURL('/dashboard')
}
async function signOut(page: Page) {
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
  await expect(page).toHaveURL(/\/login(?:\?|$)/)
  await expect(page.getByRole('button', { name: 'Mở thông báo', exact: true })).toHaveCount(0)
  await expect(page.getByRole('article')).toHaveCount(0)
  expect((await page.request.get('/api/auth/me/')).status()).toBe(403)
}
async function openWorkspaceThroughNavigation(page: Page) {
  await page.getByRole('link', { name: /Khám phá tổ chức/ }).click()
  await expect(page).toHaveURL('/profiles')
  await page.getByRole('link').filter({ has: page.getByRole('heading', { name: 'Team Management Integration', exact: true }) }).click()
  await expect(page).toHaveURL(`/profiles/${profileId}`)
  await page.getByRole('link').filter({ has: page.getByRole('heading', { name: 'Team Workspace Integration', exact: true }) }).click()
  await expect(page).toHaveURL(`/profiles/${profileId}/workspaces/${workspaceId}`)
  await page.getByRole('link', { name: 'Xem công việc', exact: true }).click()
  await expect(page).toHaveURL(taskBase)
}
async function submitFromUI(page: Page, taskId: string, product: string): Promise<Deliverable> {
  await page.getByRole('button', { name: 'Nộp sản phẩm', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Nộp sản phẩm', exact: true })
  await dialog.getByLabel('Đường dẫn hoặc nội dung sản phẩm', { exact: true }).fill(product)
  const request = page.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${taskId}/deliverables/` && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Nộp sản phẩm', exact: true }).click()
  const response = await request
  expect(response.status()).toBe(201)
  await expect(dialog).not.toBeVisible()
  expect((await getTask(page, taskId)).status).toBe('REVIEW')
  await expect(page.getByRole('button', { name: 'Nộp sản phẩm', exact: true })).toHaveCount(0)
  return response.json() as Promise<Deliverable>
}

test('MVP acceptance: one UI-created Task passes assignment, execution, revision, approval and cross-user cache boundaries', async ({ page }) => {
  test.setTimeout(180_000)
  const failures: string[] = []
  page.on('pageerror', (error) => failures.push(error.name))
  page.on('response', (response) => { if (response.status() >= 500) failures.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })

  // Only identity/membership/Workspace and negative legacy fixtures are seeded.
  // The Task under acceptance and every successful mutation below use React UI.
  await signIn(page, 'manager')
  await openWorkspaceThroughNavigation(page)
  expect((await page.request.post(apiTasks, { data: { title: 'Rejected missing CSRF acceptance' } })).status()).toBe(403)
  await page.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
  let dialog = page.getByRole('dialog', { name: 'Tạo công việc', exact: true })
  await dialog.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
  await expect(dialog.getByRole('alert')).toBeVisible()
  await expect(dialog.getByLabel('Tên công việc', { exact: true })).toHaveAttribute('aria-invalid', 'true')
  await dialog.getByLabel('Tên công việc', { exact: true }).fill(taskTitle)
  await dialog.getByLabel('Mô tả', { exact: true }).fill('Created, assigned and reviewed only through the React MVP.')
  await dialog.getByLabel('Ưu tiên', { exact: true }).selectOption('HIGH')
  await dialog.getByLabel('Thời hạn', { exact: true }).fill('2027-01-25T16:30')
  const createdResponse = page.waitForResponse((response) => new URL(response.url()).pathname === apiTasks && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
  const created = await createdResponse
  expect(created.status()).toBe(201)
  const task = await created.json() as Task
  expect(task.status).toBe('PENDING')
  expect(task.priority).toBe('HIGH')
  expect(task.parent_id).toBeNull()
  await expect(dialog).not.toBeVisible()
  await page.getByRole('link', { name: taskTitle, exact: true }).click()
  await expect(page).toHaveURL(`${taskBase}/${task.id}`)

  await page.getByRole('button', { name: 'Tạo công việc con', exact: true }).click()
  dialog = page.getByRole('dialog', { name: 'Tạo công việc con', exact: true })
  await dialog.getByLabel('Tên công việc', { exact: true }).fill(childTitle)
  const childResponse = page.waitForResponse((response) => new URL(response.url()).pathname === apiTasks && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Tạo công việc con', exact: true }).click()
  const child = await (await childResponse).json() as Task
  expect(child.parent_id).toBe(task.id)
  await expect(dialog).not.toBeVisible()
  await page.getByRole('link', { name: childTitle, exact: true }).click()
  await expect(page.getByRole('navigation', { name: 'Phân cấp công việc' }).getByRole('link', { name: taskTitle, exact: true })).toBeVisible()
  await page.getByRole('navigation', { name: 'Phân cấp công việc' }).getByRole('link', { name: taskTitle, exact: true }).click()
  expect((await getTask(page, task.id)).status).toBe('PENDING')

  await page.getByRole('button', { name: 'Phân công', exact: true }).click()
  dialog = page.getByRole('dialog', { name: 'Phân công công việc', exact: true })
  await dialog.getByLabel('Thành viên', { exact: true }).selectOption(fixtureId('editor_profile_membership'))
  await dialog.getByRole('button', { name: 'Xác nhận phân công', exact: true }).click()
  await expect(dialog).not.toBeVisible()
  expect((await getTask(page, task.id)).active_assignment?.profile_membership_id).toBe(fixtureId('editor_profile_membership'))
  await signOut(page)

  // The same browser context logs out/in, exercising real session/cache cleanup.
  await signIn(page, 'editor')
  await openWorkspaceThroughNavigation(page)
  await page.getByRole('link', { name: taskTitle, exact: true }).click()
  const started = page.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${task.id}/start/` && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Bắt đầu công việc', exact: true }).click()
  expect((await started).status()).toBe(200)
  expect((await getTask(page, task.id)).status).toBe('WORKING')
  await rejectedPost(page.request, `${apiTasks}${task.id}/start/`, {}, 409)
  const first = await submitFromUI(page, task.id, 'https://example.test/mvp-acceptance-v1')
  expect(first.revision).toBe(1)
  await rejectedPost(page.request, `${apiTasks}${task.id}/deliverables/`, { file_url: 'https://example.test/rejected-duplicate' }, 409)
  await expect(page.getByRole('button', { name: /^(Phê duyệt sản phẩm|Yêu cầu chỉnh sửa)$/ })).toHaveCount(0)

  await page.getByLabel('Nội dung bình luận', { exact: true }).fill('MVP acceptance comment before reload')
  await page.getByRole('button', { name: 'Gửi bình luận', exact: true }).click()
  await expect(page.getByText('MVP acceptance comment before reload', { exact: true })).toBeVisible()
  await page.reload()
  const comment = page.getByRole('article').filter({ has: page.getByText('MVP acceptance comment before reload', { exact: true }) })
  await comment.getByRole('button', { name: 'Chỉnh sửa bình luận', exact: true }).click()
  dialog = page.getByRole('dialog', { name: 'Chỉnh sửa bình luận', exact: true })
  await dialog.getByLabel('Nội dung bình luận', { exact: true }).fill('MVP acceptance edited private body')
  await dialog.getByRole('button', { name: 'Lưu bình luận', exact: true }).click()
  await expect(dialog).not.toBeVisible()
  await page.getByRole('article').filter({ has: page.getByText('MVP acceptance edited private body', { exact: true }) }).getByRole('button', { name: 'Xóa bình luận', exact: true }).click()
  dialog = page.getByRole('dialog', { name: 'Xóa bình luận', exact: true })
  await dialog.getByRole('button', { name: 'Xác nhận xóa', exact: true }).click()
  await expect(dialog).not.toBeVisible()
  await expect(page.getByText('Bình luận đã được xóa.', { exact: true })).toBeVisible()
  await expect(page.getByText('MVP acceptance edited private body', { exact: true })).toHaveCount(0)
  await signOut(page)

  await signIn(page, 'manager')
  await openWorkspaceThroughNavigation(page)
  await page.getByRole('link', { name: taskTitle, exact: true }).click()
  await page.getByRole('button', { name: 'Yêu cầu chỉnh sửa', exact: true }).click()
  dialog = page.getByRole('dialog', { name: 'Yêu cầu chỉnh sửa', exact: true })
  await dialog.getByLabel('Nội dung cần chỉnh sửa', { exact: true }).fill('MVP acceptance review feedback')
  const changes = page.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${task.id}/deliverables/${first.id}/request-changes/` && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Gửi yêu cầu chỉnh sửa', exact: true }).click()
  expect((await changes).status()).toBe(200)
  await expect(dialog).not.toBeVisible()
  expect((await getTask(page, task.id)).status).toBe('WORKING')
  await signOut(page)

  await signIn(page, 'editor')
  await openWorkspaceThroughNavigation(page)
  await page.getByRole('link', { name: taskTitle, exact: true }).click()
  await expect(page.getByText('MVP acceptance review feedback', { exact: true })).toBeVisible()
  const second = await submitFromUI(page, task.id, 'https://example.test/mvp-acceptance-v2')
  expect(second.revision).toBe(2)
  await signOut(page)

  await signIn(page, 'manager')
  await openWorkspaceThroughNavigation(page)
  await page.getByRole('link', { name: taskTitle, exact: true }).click()
  const old = page.getByRole('article', { name: 'Phiên bản 1', exact: true })
  await expect(old.getByRole('button', { name: 'Phê duyệt sản phẩm', exact: true })).toHaveCount(0)
  await rejectedPost(page.request, `${apiTasks}${task.id}/deliverables/${first.id}/approve/`, {}, 409)
  await page.getByRole('button', { name: 'Phê duyệt sản phẩm', exact: true }).click()
  dialog = page.getByRole('dialog', { name: 'Phê duyệt sản phẩm', exact: true })
  await dialog.getByLabel('Nhận xét', { exact: false }).fill('MVP acceptance approved')
  const approved = page.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${task.id}/deliverables/${second.id}/approve/` && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Xác nhận phê duyệt', exact: true }).click()
  expect((await approved).status()).toBe(200)
  await expect(dialog).not.toBeVisible()
  expect((await getTask(page, task.id)).status).toBe('COMPLETED')
  expect((await getTask(page, child.id)).status).toBe('PENDING')
  await expect(page.getByText('MVP acceptance approved', { exact: true })).toBeVisible()
  await rejectedPost(page.request, `${apiTasks}${task.id}/deliverables/${second.id}/approve/`, {}, 409)
  await rejectedPost(page.request, `${apiTasks}${task.id}/deliverables/${second.id}/request-changes/`, { comment: 'Rejected post-completion replay' }, 409)

  await page.emulateMedia({ reducedMotion: 'reduce' })
  for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
    await page.setViewportSize(size)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
    expect(a11y.violations.map((item) => ({ id: item.id, targets: item.nodes.map((node) => node.target) }))).toEqual([])
    await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `accepted-task-${size.width}.png`), fullPage: true })
  }
  await page.setViewportSize({ width: 1440, height: 1000 })

  // This separate historical fixture tests self-review denial, not successful
  // submission setup. No current manager has Editor execution authority.
  const selfId = fixtureId('acceptance_self_review_task')
  await page.goto(`${taskBase}/${selfId}`)
  const selfResponse = await page.request.get(`${apiTasks}${selfId}/deliverables/`)
  const ownSubmission = (await selfResponse.json() as { results: Deliverable[] }).results[0]
  if (!ownSubmission) throw new Error('Owned negative fixture missing.')
  expect(ownSubmission.can_approve).toBe(false)
  expect(ownSubmission.can_request_changes).toBe(false)
  await expect(page.getByRole('button', { name: /^(Phê duyệt sản phẩm|Yêu cầu chỉnh sửa)$/ })).toHaveCount(0)
  await rejectedPost(page.request, `${apiTasks}${selfId}/deliverables/${ownSubmission.id}/approve/`, {}, 403)
  await rejectedPost(page.request, `${apiTasks}${selfId}/deliverables/${ownSubmission.id}/request-changes/`, { comment: 'Rejected self-review' }, 403)

  await page.getByRole('navigation', { name: 'Điều hướng chính', exact: true }).getByRole('link', { name: 'Thông báo', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Thông báo', exact: true })).toBeVisible()
  const managerFeed = await page.request.get('/api/v1/notifications/?page=1')
  const managerRows = (await managerFeed.json() as { results: Notification[] }).results
  const notification = managerRows.find((item) => item.task_id === task.id && !item.is_read)
  if (!notification) throw new Error('UI journey notification missing.')
  const before = await page.request.get('/api/v1/notifications/unread-count/')
  const unreadCount = (await before.json() as { unread_count: number }).unread_count
  // The API only asserts identity of the row; mark-read itself is a UI action.
  const markRead = page.waitForResponse((response) => new URL(response.url()).pathname === `/api/v1/notifications/${notification.id}/read/` && response.request().method() === 'POST')
  // Same-title events can repeat. Match the server's validated Task target too.
  const article = page.getByRole('article').filter({ has: page.locator(`a[href="${taskBase}/${task.id}"]`) }).filter({ has: page.getByRole('button', { name: 'Đánh dấu đã đọc', exact: true }) }).first()
  await article.getByRole('button', { name: 'Đánh dấu đã đọc', exact: true }).click()
  // Server and UI retain the same stable order, so this is the first unread
  // event for the selected Task in both the asserted page and the actual UI.
  const readResponse = await markRead
  expect(readResponse.status()).toBe(200)
  await expect.poll(async () => (await (await page.request.get('/api/v1/notifications/unread-count/')).json() as { unread_count: number }).unread_count).toBe(unreadCount - 1)
  await signOut(page)

  await signIn(page, 'viewer')
  await page.getByRole('navigation', { name: 'Điều hướng chính', exact: true }).getByRole('link', { name: 'Thông báo', exact: true }).click()
  await expect(page.getByText('Chưa có thông báo', { exact: true })).toBeVisible()
  await expect(page.getByText('MVP acceptance edited private body', { exact: true })).toHaveCount(0)
  const viewerFeed = await page.request.get('/api/v1/notifications/?page=1')
  const viewerRows = (await viewerFeed.json() as { results: Notification[] }).results
  expect(viewerRows.some((item) => managerRows.some((other) => other.id === item.id))).toBe(false)
  await rejectedPost(page.request, `/api/v1/notifications/${notification.id}/read/`, {}, 404)
  await page.goto(`${taskBase}/${task.id}`)
  await expect(page.getByRole('heading', { name: taskTitle, exact: true })).toBeVisible()
  for (const label of ['Chỉnh sửa công việc', 'Phân công', 'Bắt đầu công việc', 'Nộp sản phẩm', 'Phê duyệt sản phẩm', 'Yêu cầu chỉnh sửa', 'Gửi bình luận', 'Chỉnh sửa bình luận', 'Xóa bình luận']) {
    await expect(page.getByRole('button', { name: label, exact: true })).toHaveCount(0)
  }
  await rejectedPost(page.request, `${apiTasks}${task.id}/comments/`, { content: 'Rejected Viewer acceptance write' }, 403)
  const foreign = `/api/v1/profiles/${fixtureId('other_profile')}/workspaces/${fixtureId('foreign_workspace')}/tasks/${fixtureId('task_foreign')}/`
  expect((await page.request.get(foreign)).status()).toBe(404)
  await signOut(page)
  expect(failures).toEqual([])
})

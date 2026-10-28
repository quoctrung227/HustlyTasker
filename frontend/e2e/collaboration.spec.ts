import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the isolated frontend integration launcher.')
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
const taskBase = `/profiles/${profileId}/workspaces/${workspaceId}/tasks`
const apiTasks = `/api/v1/profiles/${profileId}/workspaces/${workspaceId}/tasks/`
const historyId = fixtureId('collaboration_history_task'), workingId = fixtureId('collaboration_working_task'), commentId = fixtureId('collaboration_comment_task')
type Role = 'owner' | 'manager' | 'editor' | 'viewer'
type Comment = { id: string; content: string | null; is_deleted: boolean }
type Notification = { id: string; task_id: string; is_read: boolean; title: string }
async function csrf(request: APIRequestContext): Promise<string> {
  const response = await request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  return (await response.json() as { csrf_token: string }).csrf_token
}
function email(role: Role) { return role === 'owner' ? required('HT_FRONTEND_TEST_OWNER_EMAIL') : `${role}.${runId}@example.test` }
async function loginUI(page: Page, role: Role) {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(email(role))
  await page.getByLabel('Mật khẩu', { exact: true }).fill(required('HT_FRONTEND_TEST_PASSWORD'))
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  await expect.poll(() => new URL(page.url()).pathname).toBe('/dashboard')
}
async function loginAPI(request: APIRequestContext, role: Role) {
  const token = await csrf(request)
  const response = await request.post('/api/auth/login/', { headers: { 'X-CSRFToken': token }, data: { email: email(role), password: required('HT_FRONTEND_TEST_PASSWORD') } })
  expect(response.status()).toBe(200)
}
async function post(request: APIRequestContext, path: string, data: Record<string, unknown> = {}) {
  return request.post(path, { headers: { 'X-CSRFToken': await csrf(request) }, data })
}
async function comments(request: APIRequestContext): Promise<Comment[]> {
  const response = await request.get(`${apiTasks}${commentId}/comments/?page=2`)
  expect(response.status()).toBe(200)
  return (await response.json() as { results: Comment[] }).results
}

// Verify the actual native mutation dialogs, not an API-created substitute.
async function verifyMutationDialog(page: Page, title: string, surface: string) {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 812, height: 375 }, { width: 1440, height: 1000 }]) {
    await page.setViewportSize(size)
    const trigger = page.getByRole('button', { name: title, exact: true })
    await trigger.focus()
    await page.keyboard.press('Enter')
    const dialog = page.getByRole('dialog', { name: title, exact: true })
    await expect(dialog).toBeVisible()
    expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true)
    await page.keyboard.press('Tab')
    expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true)
    expect(await page.evaluate(() => {
      const focused = document.activeElement
      if (!(focused instanceof HTMLElement)) return false
      const rect = focused.getBoundingClientRect(), style = getComputedStyle(focused)
      return rect.bottom > 0 && rect.top < innerHeight && style.outlineStyle !== 'none' && Number.parseFloat(style.outlineWidth) > 0
    })).toBe(true)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    expect(await dialog.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true)
    const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
    expect(a11y.violations.map((violation) => ({ id: violation.id, targets: violation.nodes.map((node) => node.target) }))).toEqual([])
    await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `${surface}-${size.width}.png`), fullPage: true })
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await expect(trigger).toBeFocused()
  }
}

test.describe('Collaboration UI — real isolated Django/PostgreSQL, no API mocks', () => {
  const failures = new WeakMap<Page, string[]>()
  test.beforeEach(({ page }) => {
    const events: string[] = []
    failures.set(page, events)
    page.on('pageerror', (error) => events.push(error.name))
    page.on('response', (response) => { if (response.status() >= 500) events.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })
  })
  test.afterEach(({ page }) => { expect(failures.get(page)).toEqual([]) })

  test('Viewer reads revision/review history and safe product links without mutation authority', async ({ page }) => {
    await loginUI(page, 'viewer')
    await page.goto(`${taskBase}/${historyId}`)
    await expect(page.getByRole('heading', { name: 'Deliverable & Review', exact: true })).toBeVisible()
    const first = page.getByRole('article', { name: 'Phiên bản 1', exact: true })
    await expect(first.getByText('Improve contrast in the first revision.', { exact: true })).toBeVisible()
    await expect(first.getByRole('link', { name: /Mở sản phẩm bàn giao/ })).toHaveAttribute('href', 'https://example.test/isolated-deliverable-v1')
    const second = page.getByRole('article', { name: 'Phiên bản 2', exact: true })
    await expect(second.getByText('Approved contrast revision.', { exact: true })).toBeVisible()
    await expect(second.getByText('javascript:unsafe-deliverable-text', { exact: true })).toBeVisible()
    await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0)
    await expect(page.getByRole('button', { name: /^(Nộp sản phẩm|Phê duyệt sản phẩm|Yêu cầu chỉnh sửa|Gửi bình luận)$/ })).toHaveCount(0)
    expect((await post(page.request, `${apiTasks}${historyId}/deliverables/`, { file_url: 'https://example.test/rejected-viewer' })).status()).toBe(403)
    expect((await post(page.request, `${apiTasks}${historyId}/comments/`, { content: 'Rejected viewer comment' })).status()).toBe(403)
    expect((await page.request.get(`/api/v1/profiles/${fixtureId('other_profile')}/workspaces/${fixtureId('foreign_workspace')}/tasks/${fixtureId('task_foreign')}/comments/`)).status()).toBe(404)
  })

  test('Editor edits an existing comment after reload/navigation and creates/soft-deletes a new comment', async ({ page }) => {
    await loginUI(page, 'editor')
    await page.goto(`${taskBase}/${commentId}`)
    await expect(page.getByRole('heading', { name: 'Thảo luận', exact: true })).toBeVisible()
    await page.reload()
    const existing = page.getByRole('article').filter({ has: page.getByText('Existing discussion comment 01 Integration', { exact: true }) })
    await existing.getByRole('button', { name: 'Chỉnh sửa bình luận', exact: true }).click()
    let dialog = page.getByRole('dialog', { name: 'Chỉnh sửa bình luận', exact: true })
    await dialog.getByLabel('Nội dung bình luận', { exact: true }).fill('Existing comment edited after reload Integration')
    await dialog.getByRole('button', { name: 'Lưu bình luận', exact: true }).click()
    await expect(dialog).not.toBeVisible()
    await page.goto(`${taskBase}/${historyId}`)
    await page.goto(`${taskBase}/${commentId}`)
    const restored = page.getByRole('article').filter({ has: page.getByText('Existing comment edited after reload Integration', { exact: true }) })
    await expect(restored.getByRole('button', { name: 'Chỉnh sửa bình luận', exact: true })).toBeVisible()
    await expect(restored.getByRole('button', { name: 'Xóa bình luận', exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Trang sau', exact: true }).last().click()
    await expect(page.getByText('Bình luận đã được xóa.', { exact: true })).toBeVisible()
    await expect(page.getByText('Deleted private discussion fixture body', { exact: true })).toHaveCount(0)
    const paginated = page.getByRole('article').filter({ has: page.getByText('Existing discussion comment 21 Integration', { exact: true }) })
    await paginated.getByRole('button', { name: 'Chỉnh sửa bình luận', exact: true }).click()
    dialog = page.getByRole('dialog', { name: 'Chỉnh sửa bình luận', exact: true })
    await dialog.getByLabel('Nội dung bình luận', { exact: true }).fill('Existing paginated comment edited Integration')
    await dialog.getByRole('button', { name: 'Lưu bình luận', exact: true }).click()
    await expect(dialog).not.toBeVisible()
    await expect(page.getByText('Existing paginated comment edited Integration', { exact: true })).toBeVisible()
    expect((await page.request.post(`${apiTasks}${commentId}/comments/`, { data: { content: 'Rejected missing CSRF' } })).status()).toBe(403)
    await page.getByLabel('Nội dung bình luận', { exact: true }).fill('Natural UI comment Integration')
    const createdResponse = page.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${commentId}/comments/` && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Gửi bình luận', exact: true }).click()
    expect((await createdResponse).status()).toBe(201)
    await expect(page.getByText('Natural UI comment Integration', { exact: true })).toBeVisible()
    const article = page.getByRole('article').filter({ has: page.getByText('Natural UI comment Integration', { exact: true }) })
    await article.getByRole('button', { name: 'Chỉnh sửa bình luận', exact: true }).click()
    dialog = page.getByRole('dialog', { name: 'Chỉnh sửa bình luận', exact: true })
    await dialog.getByLabel('Nội dung bình luận', { exact: true }).fill('Edited natural UI comment Integration')
    await dialog.getByRole('button', { name: 'Lưu bình luận', exact: true }).click()
    await expect(dialog).not.toBeVisible()
    const edited = page.getByRole('article').filter({ has: page.getByText('Edited natural UI comment Integration', { exact: true }) })
    await edited.getByRole('button', { name: 'Xóa bình luận', exact: true }).click()
    dialog = page.getByRole('dialog', { name: 'Xóa bình luận', exact: true })
    await dialog.getByRole('button', { name: 'Xác nhận xóa', exact: true }).click()
    await expect(dialog).not.toBeVisible()
    await expect(page.getByText('Edited natural UI comment Integration', { exact: true })).toHaveCount(0)
    expect((await comments(page.request)).some((comment) => comment.content === 'Edited natural UI comment Integration')).toBe(false)
    await page.reload()
    await expect(page.getByRole('article').filter({ has: page.getByText('Existing comment edited after reload Integration', { exact: true }) }).getByRole('button', { name: 'Chỉnh sửa bình luận', exact: true })).toBeVisible()
  })

  test('Manager moderates another author without gaining edit authority', async ({ page }) => {
    await loginUI(page, 'manager')
    await page.goto(`${taskBase}/${commentId}`)
    const article = page.getByRole('article').filter({ has: page.getByText('Existing discussion comment 00 Integration', { exact: true }) })
    await expect(article).toBeVisible()
    await expect(article.getByRole('button', { name: 'Chỉnh sửa bình luận', exact: true })).toHaveCount(0)
    await article.getByRole('button', { name: 'Xóa bình luận', exact: true }).click()
    await page.getByRole('dialog', { name: 'Xóa bình luận', exact: true }).getByRole('button', { name: 'Xác nhận xóa', exact: true }).click()
    await expect(page.getByText('Existing discussion comment 00 Integration', { exact: true })).toHaveCount(0)
    await expect(page.getByText('Bình luận đã được xóa.', { exact: true })).toBeVisible()
  })

  test('React UI submits, requests changes, resubmits and approves; a separate fresh submission is approved', async ({ page, browser }) => {
    test.setTimeout(180_000)
    await loginUI(page, 'editor')
    const reviewerContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' })
    const reviewerPage = await reviewerContext.newPage()
    reviewerPage.on('pageerror', (error) => failures.get(page)?.push(error.name))
    reviewerPage.on('response', (response) => { if (response.status() >= 500) failures.get(page)?.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })
    try {
      await loginUI(reviewerPage, 'manager')
      await page.goto(`${taskBase}/${workingId}`)
      expect((await page.request.post(`${apiTasks}${workingId}/deliverables/`, { data: { file_url: 'https://example.test/rejected-missing-csrf' } })).status()).toBe(403)
      await verifyMutationDialog(page, 'Nộp sản phẩm', 'submit-form')
      const submit = async (taskId: string, url: string) => {
        await page.getByRole('button', { name: 'Nộp sản phẩm', exact: true }).click()
        const dialog = page.getByRole('dialog', { name: 'Nộp sản phẩm', exact: true })
        await dialog.getByLabel('Đường dẫn hoặc nội dung sản phẩm', { exact: true }).fill(url)
        const response = page.waitForResponse((item) => new URL(item.url()).pathname === `${apiTasks}${taskId}/deliverables/` && item.request().method() === 'POST')
        await dialog.getByRole('button', { name: 'Nộp sản phẩm', exact: true }).click()
        const saved = await response
        expect(saved.status()).toBe(201)
        await expect(dialog).not.toBeVisible()
        await expect(page.getByRole('button', { name: 'Nộp sản phẩm', exact: true })).toHaveCount(0)
        expect((await (await page.request.get(`${apiTasks}${taskId}/`)).json() as { status: string }).status).toBe('REVIEW')
        return await saved.json() as { id: string }
      }
      const first = await submit(workingId, 'https://example.test/ui-review-v1')
      await expect(page.getByRole('article', { name: 'Phiên bản 1', exact: true })).toBeVisible()
      await expect(page.getByRole('button', { name: /^(Phê duyệt sản phẩm|Yêu cầu chỉnh sửa)$/ })).toHaveCount(0)
      const reviewerFeed = await reviewerPage.request.get('/api/v1/notifications/?page=1')
      const reviewerNotifications = await reviewerFeed.json() as { results: Notification[] }
      const someoneElsesNotification = reviewerNotifications.results[0]
      if (!someoneElsesNotification) throw new Error('Reviewer event missing.')
      expect((await post(page.request, `/api/v1/notifications/${someoneElsesNotification.id}/read/`)).status()).toBe(404)
      await reviewerPage.goto(`${taskBase}/${workingId}`)
      await verifyMutationDialog(reviewerPage, 'Yêu cầu chỉnh sửa', 'request-changes-form')
      await reviewerPage.getByRole('button', { name: 'Yêu cầu chỉnh sửa', exact: true }).click()
      let dialog = reviewerPage.getByRole('dialog', { name: 'Yêu cầu chỉnh sửa', exact: true })
      await dialog.getByLabel('Nội dung cần chỉnh sửa', { exact: true }).fill('UI change request Integration')
      const changes = reviewerPage.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${workingId}/deliverables/${first.id}/request-changes/` && response.request().method() === 'POST')
      await dialog.getByRole('button', { name: 'Gửi yêu cầu chỉnh sửa', exact: true }).click()
      expect((await changes).status()).toBe(200)
      await expect(dialog).not.toBeVisible()
      expect((await (await reviewerPage.request.get(`${apiTasks}${workingId}/`)).json() as { status: string }).status).toBe('WORKING')
      await page.reload()
      await expect(page.getByText('UI change request Integration', { exact: true })).toBeVisible()
      const second = await submit(workingId, 'https://example.test/ui-review-v2')
      await reviewerPage.reload()
      await expect(reviewerPage.getByRole('article', { name: 'Phiên bản 1', exact: true }).getByRole('button', { name: 'Phê duyệt sản phẩm', exact: true })).toHaveCount(0)
      await verifyMutationDialog(reviewerPage, 'Phê duyệt sản phẩm', 'approve-form')
      const approve = async (taskId: string, deliverableId: string, feedback: string) => {
        await reviewerPage.getByRole('button', { name: 'Phê duyệt sản phẩm', exact: true }).click()
        dialog = reviewerPage.getByRole('dialog', { name: 'Phê duyệt sản phẩm', exact: true })
        await dialog.getByLabel('Nhận xét', { exact: false }).fill(feedback)
        const decision = reviewerPage.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${taskId}/deliverables/${deliverableId}/approve/` && response.request().method() === 'POST')
        await dialog.getByRole('button', { name: 'Xác nhận phê duyệt', exact: true }).click()
        expect((await decision).status()).toBe(200)
        await expect(dialog).not.toBeVisible()
        expect((await (await reviewerPage.request.get(`${apiTasks}${taskId}/`)).json() as { status: string }).status).toBe('COMPLETED')
      }
      await approve(workingId, second.id, 'UI approval after revision Integration')
      await page.reload()
      await expect(page.getByText('UI approval after revision Integration', { exact: true })).toBeVisible()
      const taskResponse = await page.request.get(`${apiTasks}${workingId}/`)
      expect((await taskResponse.json() as { status: string }).status).toBe('COMPLETED')
      expect((await post(reviewerPage.request, `${apiTasks}${workingId}/deliverables/${first.id}/approve/`)).status()).toBe(409)
      await expect(page.getByRole('button', { name: /^(Nộp sản phẩm|Phê duyệt sản phẩm|Yêu cầu chỉnh sửa)$/ })).toHaveCount(0)

      // Independent first-revision approval, using another existing WORKING
      // fixture and the same browser identities; no direct API setup mutation.
      await page.goto(`${taskBase}/${commentId}`)
      const direct = await submit(commentId, 'https://example.test/ui-direct-approval')
      await reviewerPage.goto(`${taskBase}/${commentId}`)
      await approve(commentId, direct.id, 'UI direct approval Integration')
      const taskNotifications = await reviewerPage.request.get('/api/v1/notifications/?page=1')
      expect((await taskNotifications.json() as { results: Notification[] }).results.some((notification) => notification.task_id === commentId)).toBe(true)
    } finally { await reviewerContext.close() }
  })

  test('Own Notification feed/count/mark-read and target navigation use real events', async ({ page }) => {
    await loginUI(page, 'manager')
    await page.goto('/notifications')
    await expect(page.getByRole('heading', { name: 'Thông báo', exact: true })).toBeVisible()
    const feedResponse = await page.request.get('/api/v1/notifications/?page=1')
    const feed = await feedResponse.json() as { results: Notification[] }
    const unread = feed.results.find((notification) => !notification.is_read)
    expect(unread).toBeDefined()
    if (!unread) throw new Error('Owned seeded notification missing.')
    const before = await page.request.get('/api/v1/notifications/unread-count/')
    const beforeCount = (await before.json() as { unread_count: number }).unread_count
    expect((await page.request.post(`/api/v1/notifications/${unread.id}/read/`, { data: {} })).status()).toBe(403)
    await page.getByRole('article').filter({ has: page.getByRole('heading', { name: unread.title, exact: true }) }).filter({ has: page.getByRole('button', { name: 'Đánh dấu đã đọc', exact: true }) }).first().getByRole('button', { name: 'Đánh dấu đã đọc', exact: true }).click()
    await expect.poll(async () => (await (await page.request.get('/api/v1/notifications/unread-count/')).json() as { unread_count: number }).unread_count).toBe(beforeCount - 1)
    await page.getByLabel('Trạng thái thông báo', { exact: true }).selectOption('read')
    await expect(page.getByRole('article')).not.toHaveCount(0)
    const firstRead = page.getByRole('article').first()
    const target = await firstRead.getByRole('link', { name: 'Mở công việc', exact: true }).getAttribute('href')
    expect(target).toMatch(/^\/profiles\/[a-f0-9-]+\/workspaces\/[a-f0-9-]+\/tasks\/[a-f0-9-]+$/)
    await firstRead.getByRole('link', { name: 'Mở công việc', exact: true }).click()
    await expect(page).toHaveURL(target ?? '')
    await expect(page.getByRole('heading', { name: 'Deliverable & Review', exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Mở thông báo', exact: true }).click()
    await expect(page.getByRole('dialog', { name: 'Thông báo của bạn', exact: true })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('button', { name: 'Mở thông báo', exact: true })).toBeFocused()
  })

  test('collaboration and Notification surfaces remain accessible at four viewport sizes', async ({ page }) => {
    test.setTimeout(120_000)
    await loginUI(page, 'owner')
    await page.emulateMedia({ reducedMotion: 'reduce' })
    const verify = async (surface: string, width: number) => {
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
      expect(a11y.violations.map((violation) => ({ id: violation.id, targets: violation.nodes.map((node) => node.target) }))).toEqual([])
      await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `${surface}-${width}.png`), fullPage: true })
    }
    for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 812, height: 375 }, { width: 1440, height: 1000 }]) {
      await page.setViewportSize(size)
      await page.goto(`${taskBase}/${historyId}`)
      await expect(page.getByRole('heading', { name: 'Deliverable & Review', exact: true })).toBeVisible()
      await expect(page.getByLabel('Nội dung bình luận', { exact: true })).toBeVisible()
      await expect(page.getByRole('article', { name: 'Phiên bản 2', exact: true })).toBeVisible()
      await verify('collaboration-task', size.width)
      await page.goto('/notifications')
      await expect(page.getByRole('heading', { name: 'Thông báo', exact: true })).toBeVisible()
      await expect(page.getByRole('article').first()).toBeVisible()
      await verify('notification-feed', size.width)
      await page.getByRole('button', { name: 'Mở thông báo', exact: true }).click()
      await expect(page.getByRole('dialog', { name: 'Thông báo của bạn', exact: true }).getByRole('article').first()).toBeVisible()
      await verify('notification-preview', size.width)
      await page.keyboard.press('Escape')
      await expect(page.getByRole('button', { name: 'Mở thông báo', exact: true })).toBeFocused()
    }
  })

  test('revoked target disappears from feed/count and session expiry removes private collaboration UI', async ({ page, playwright }) => {
    await loginUI(page, 'editor')
    await page.goto('/notifications')
    await expect(page.getByRole('heading', { name: 'Thông báo', exact: true })).toBeVisible()
    await expect(page.getByRole('article').first().getByRole('button', { name: 'Đánh dấu đã đọc', exact: true })).toBeVisible()
    const visible = await page.request.get('/api/v1/notifications/?page=1')
    const feed = await visible.json() as { results: Notification[] }
    expect(feed.results.length).toBeGreaterThan(0)
    const known = feed.results[0]
    if (!known) throw new Error('Owned event missing.')
    const manager = await playwright.request.newContext({ baseURL: 'http://127.0.0.1:5173' })
    try {
      await loginAPI(manager, 'manager')
      const response = await manager.delete(`/api/v1/profiles/${profileId}/workspaces/${workspaceId}/members/${fixtureId('editor_active_membership')}/`, { headers: { 'X-CSRFToken': await csrf(manager) } })
      expect(response.status()).toBe(204)
    } finally { await manager.dispose() }
    const deniedRead = page.waitForResponse((response) => new URL(response.url()).pathname === `/api/v1/notifications/${known.id}/read/` && response.request().method() === 'POST')
    await page.getByRole('article').first().getByRole('button', { name: 'Đánh dấu đã đọc', exact: true }).click()
    expect((await deniedRead).status()).toBe(404)
    await expect(page.getByText('Chưa có thông báo', { exact: true })).toBeVisible()
    const count = await page.request.get('/api/v1/notifications/unread-count/')
    expect((await count.json() as { unread_count: number }).unread_count).toBe(0)
    expect((await page.request.get(`${apiTasks}${known.task_id}/`)).status()).toBe(404)
    const container = required('HT_FRONTEND_TEST_BACKEND_CONTAINER')
    if (container !== `ht-fe-${runId}-backend`) throw new Error('Unexpected test backend identity.')
    const output = execFileSync('docker', ['exec', container, 'python', '/workspace/scripts/frontend_integration.py', 'expire-sessions'], { encoding: 'utf8', timeout: 15_000 })
    expect(output.trim()).toBe('OWNED_ISOLATED_SESSIONS_EXPIRED')
    await page.evaluate(() => window.dispatchEvent(new Event('focus')))
    await expect(page).toHaveURL(/\/login(?:\?|$)/)
    await expect(page.getByRole('button', { name: 'Mở thông báo', exact: true })).toHaveCount(0)
    await expect(page.getByRole('article')).toHaveCount(0)
  })
})

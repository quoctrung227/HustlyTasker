import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type BrowserContext, type Page } from '@playwright/test'
import { csrf, enterSecret, fixtureId, required, runId } from './invitation-v2-helpers'

// This suite requires serve-trash: fresh PostgreSQL, scoped migrations without
// AI0002, synthetic fixtures, locmem mail and purge enabled only in that server.
const profile = fixtureId('trash_profile'), workspace = fixtureId('trash_workspace')
const liveTask = fixtureId('trash_live_task')
const taskRoute = `/profiles/${profile}/workspaces/${workspace}/tasks/${liveTask}`
const taskApi = `/api/v1/profiles/${profile}/workspaces/${workspace}/tasks/${liveTask}/`
const objectPath = (type: string, id: string, action: string) => `/api/v1/trash/${type}/${id}/${action}/`
let ownerContext: BrowserContext, owner: Page

async function login(page: Page, actor: 'owner' | 'viewer' | 'solo_owner') {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(`trash_${actor}.${runId}@example.test`)
  await enterSecret(page, 'Mật khẩu', required('HT_FRONTEND_TEST_PASSWORD'))
  const result = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/login/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await result).status()).toBe(200)
  await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
}
async function openTrash(page: Page, title = '') {
  await page.goto(`/trash${title ? `?search=${encodeURIComponent(title)}` : ''}`)
  await expect(page.getByRole('heading', { name: 'Thùng rác', exact: true })).toBeVisible()
  if (title) await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
  else await expect(page.getByRole('list', { name: 'Các mục trong Thùng rác' })).toBeVisible()
}
function row(page: Page, title: string) { return page.locator('.trash-list > li').filter({ has: page.getByRole('heading', { name: title, exact: true }) }) }
function mutation(page: Page, type: string, id: string, action: string) {
  return page.waitForResponse((response) => new URL(response.url()).pathname === objectPath(type, id, action) && response.request().method() === 'POST')
}
async function restore(page: Page, type: string, id: string, title: string) {
  await openTrash(page, title)
  await row(page, title).getByRole('button', { name: 'Khôi phục', exact: true }).click()
  const result = mutation(page, type, id, 'restore')
  await page.getByRole('dialog', { name: 'Khôi phục dữ liệu' }).getByRole('button', { name: 'Xác nhận khôi phục' }).click()
  expect((await result).status()).toBe(204)
  await expect(page.getByRole('dialog', { name: 'Khôi phục dữ liệu' })).not.toBeVisible()
  await expect(page.getByRole('heading', { name: title, exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Thùng rác', exact: true })).toBeFocused()
}
async function deleteCurrent(page: Page, type: string, id: string, button: string) {
  await page.getByRole('button', { name: button, exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Chuyển vào Thùng rác' })
  await expect(dialog).toBeVisible()
  const result = mutation(page, type, id, 'delete')
  await dialog.getByRole('button', { name: 'Xác nhận chuyển vào Thùng rác' }).click()
  expect((await result).status()).toBe(200)
  await expect(page).toHaveURL(/\/trash$/)
  await expect(page.getByText('Đã chuyển vào Thùng rác. Trạng thái nghiệp vụ và lịch sử được giữ lại.')).toBeVisible()
}
async function purge(page: Page, type: 'task' | 'workspace' | 'profile', id: string, title: string) {
  await openTrash(page, title)
  await row(page, title).getByRole('button', { name: 'Xóa vĩnh viễn', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Xóa vĩnh viễn' })
  const confirm = dialog.getByRole('button', { name: 'Xác nhận xóa vĩnh viễn' })
  await expect(confirm).toBeDisabled()
  if (type !== 'task') {
    await dialog.getByLabel('Nhập chính xác tên để xác nhận').fill('Tên chưa khớp')
    await dialog.getByRole('checkbox').check()
    await expect(confirm).toBeDisabled()
    await dialog.getByLabel('Nhập chính xác tên để xác nhận').fill(title)
  } else await dialog.getByRole('checkbox').check()
  await expect(confirm).toBeEnabled()
  const result = mutation(page, type, id, 'purge')
  await confirm.click()
  expect((await result).status()).toBe(204)
  await expect(page.getByRole('heading', { name: title, exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Thùng rác', exact: true })).toBeFocused()
}

test.describe('Trash V1 real isolated UI', () => {
  test.describe.configure({ mode: 'serial' })
  test.beforeAll(async ({ browser }) => {
    ownerContext = await browser.newContext({ viewport: { width: 1440, height: 900 } })
    owner = await ownerContext.newPage()
    await login(owner, 'owner')
  })
  test.afterAll(async () => { await ownerContext?.close() })

  test('server filters/pagination, native keyboard focus and responsive accessible Trash', async () => {
    await openTrash(owner)
    await expect(owner.getByRole('button', { name: 'Trang sau' })).toBeEnabled()
    const next = owner.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/trash/' && new URL(response.url()).searchParams.get('page') === '2')
    await owner.getByRole('button', { name: 'Trang sau' }).click()
    expect((await next).status()).toBe(200)
    await expect(owner).toHaveURL(/page=2/)
    const filtered = owner.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/trash/' && new URL(response.url()).searchParams.get('object_type') === 'TASK' && new URL(response.url()).searchParams.get('page') === '1')
    await owner.getByRole('button', { name: 'Task', exact: true }).click()
    expect((await filtered).status()).toBe(200)
    await expect(owner.getByRole('button', { name: 'Task', exact: true })).toHaveAttribute('aria-pressed', 'true')
    const missing = owner.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/trash/' && new URL(response.url()).searchParams.get('search') === 'không có mục tương ứng')
    await owner.getByLabel('Tìm trong Thùng rác').fill('không có mục tương ứng')
    expect((await missing).status()).toBe(200)
    await expect(owner.getByRole('heading', { name: 'Không tìm thấy mục phù hợp' })).toBeVisible()
    await owner.getByRole('button', { name: 'Bỏ bộ lọc' }).click()
    await expect(owner.getByRole('list', { name: 'Các mục trong Thùng rác' })).toBeVisible()
    const title = 'Trash recent task Integration'
    await openTrash(owner, title)
    await owner.emulateMedia({ reducedMotion: 'reduce' })
    for (const [width, height] of [[375, 812], [768, 1024], [1440, 900], [812, 375]] as const) {
      await owner.setViewportSize({ width, height })
      await expect(row(owner, title)).toBeVisible()
      expect(await owner.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
      expect((await new AxeBuilder({ page: owner }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
      await owner.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `trash-${width}x${height}.png`), fullPage: true })
    }
    const restoreButton = row(owner, title).getByRole('button', { name: 'Khôi phục', exact: true })
    await restoreButton.focus(); await owner.keyboard.press('Enter')
    const dialog = owner.getByRole('dialog', { name: 'Khôi phục dữ liệu' })
    await expect(dialog).toBeVisible()
    await dialog.getByRole('button', { name: 'Hủy', exact: true }).focus()
    await owner.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await expect(restoreButton).toBeFocused()
    await owner.getByRole('button', { name: 'Mở menu' }).click()
    await owner.getByRole('dialog', { name: 'Điều hướng' }).getByRole('link', { name: 'Thùng rác', exact: true }).click()
    await expect(owner.getByRole('heading', { name: 'Thùng rác', exact: true })).toBeVisible()
  })

  test('Task soft delete and restore through UI preserve business state', async () => {
    await owner.setViewportSize({ width: 1440, height: 900 })
    await owner.goto(taskRoute)
    await expect(owner.getByRole('heading', { name: 'Trash live task Integration', exact: true })).toBeVisible()
    const before = await owner.request.get(taskApi)
    expect(before.status()).toBe(200)
    const original = await before.json() as { status: string; active_assignment: unknown }
    await deleteCurrent(owner, 'task', liveTask, 'Xóa công việc')
    expect((await owner.request.get(taskApi)).status()).toBe(404)
    await restore(owner, 'task', liveTask, 'Trash live task Integration')
    const restored = await owner.request.get(taskApi)
    expect(restored.status()).toBe(200)
    expect(await restored.json()).toMatchObject({ status: original.status, active_assignment: original.active_assignment })
  })

  test('Workspace restore exposes inherited children but preserves separate child deletion', async () => {
    const id = fixtureId('trash_deleted_workspace'), title = 'Trash Deleted Workspace Integration'
    const base = `/api/v1/profiles/${profile}/workspaces/${id}/tasks/`
    await restore(owner, 'workspace', id, title)
    expect((await owner.request.get(`${base}${fixtureId('trash_inherited_task')}/`)).status()).toBe(200)
    expect((await owner.request.get(`${base}${fixtureId('trash_independent_task')}/`)).status()).toBe(404)
    await owner.goto(`/profiles/${profile}/workspaces/${id}`)
    await expect(owner.getByRole('heading', { name: title, exact: true })).toBeVisible()
    await deleteCurrent(owner, 'workspace', id, 'Xóa không gian')
    expect((await owner.request.get(`${base}${fixtureId('trash_inherited_task')}/`)).status()).toBe(404)
    await restore(owner, 'workspace', id, title)
    expect((await owner.request.get(`${base}${fixtureId('trash_independent_task')}/`)).status()).toBe(404)
  })

  test('Profile delete/restore uses the existing detail surface without granting extra rights', async () => {
    const id = fixtureId('trash_deleted_profile'), title = 'Trash Deleted Profile Integration'
    await restore(owner, 'profile', id, title)
    await owner.goto(`/profiles/${id}`)
    await expect(owner.getByRole('heading', { name: title, exact: true })).toBeVisible()
    await deleteCurrent(owner, 'profile', id, 'Xóa tổ chức')
    expect((await owner.request.get(`/api/v1/profiles/${id}/`)).status()).toBe(404)
    await restore(owner, 'profile', id, title)
    expect((await owner.request.get(`/api/v1/profiles/${id}/`)).status()).toBe(200)
  })

  test('30-day and protected-history blocks remain visible; eligible purge requires confirmation', async () => {
    await openTrash(owner, 'Trash recent task Integration')
    await expect(row(owner, 'Trash recent task Integration').getByRole('button', { name: 'Xóa vĩnh viễn', exact: true })).toBeDisabled()
    await openTrash(owner, 'Trash protected history Integration')
    await expect(row(owner, 'Trash protected history Integration').getByRole('button', { name: 'Xóa vĩnh viễn', exact: true })).toBeDisabled()
    await expect(row(owner, 'Trash protected history Integration').getByText('Lịch sử nghiệm thu hoặc tiền công đang được bảo toàn.')).toBeVisible()
    const denied = await owner.request.post(objectPath('task', fixtureId('trash_foreign_task'), 'purge'), { headers: await csrf(owner), data: { confirm: true } })
    expect(denied.status()).toBe(404)
    await purge(owner, 'task', fixtureId('trash_expired_task'), 'Trash expired task Integration')
    await purge(owner, 'workspace', fixtureId('trash_expired_workspace'), 'Trash Expired Workspace Integration')
    await purge(owner, 'profile', fixtureId('trash_expired_profile'), 'Trash Expired Profile Integration')
    expect((await owner.request.get('/api/auth/me/')).status()).toBe(200)
    expect((await owner.request.get(`/api/v1/profiles/${profile}/`)).status()).toBe(200)
  })

  test('Viewer mutation/CSRF denied and switching users discards private Trash content', async () => {
    await openTrash(owner, 'Trash protected history Integration')
    await owner.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
    await expect(owner).toHaveURL(/\/login/)
    await expect(owner.getByRole('heading', { name: 'Trash protected history Integration', exact: true })).toHaveCount(0)
    await login(owner, 'viewer')
    await owner.goto('/trash')
    await expect(owner.getByRole('heading', { name: 'Thùng rác trống' })).toBeVisible()
    await expect(owner.getByRole('heading', { name: 'Trash protected history Integration', exact: true })).toHaveCount(0)
    await owner.goto(taskRoute)
    await expect(owner.getByRole('heading', { name: 'Trash live task Integration', exact: true })).toBeVisible()
    await expect(owner.getByRole('button', { name: 'Xóa công việc' })).toHaveCount(0)
    const withoutCsrf = await owner.request.post(objectPath('task', liveTask, 'delete'), { data: {} })
    expect(withoutCsrf.status()).toBe(403)
    const forbidden = await owner.request.post(objectPath('task', liveTask, 'delete'), { headers: await csrf(owner), data: {} })
    expect(forbidden.status()).toBe(404)
    expect((await owner.request.get(taskApi)).status()).toBe(200)
  })

  test('deleting the last Profile leaves global Trash reachable and restorable', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 375, height: 812 } })
    const page = await context.newPage()
    try {
      await login(page, 'solo_owner')
      const id = fixtureId('trash_solo_profile'), title = 'Trash Solo Profile Integration'
      await page.goto(`/profiles/${id}`)
      await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
      await deleteCurrent(page, 'profile', id, 'Xóa tổ chức')
      const profiles = await page.request.get('/api/v1/profiles/')
      expect(profiles.status()).toBe(200)
      expect((await profiles.json() as { count: number }).count).toBe(0)
      await restore(page, 'profile', id, title)
      expect((await page.request.get(`/api/v1/profiles/${id}/`)).status()).toBe(200)
    } finally { await context.close() }
  })
})

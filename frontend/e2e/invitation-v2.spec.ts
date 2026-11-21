import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type BrowserContext, type Page } from '@playwright/test'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated Invitation V2 launcher.')
  return value
}
const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Unexpected isolated run identity.')
const password = required('HT_FRONTEND_TEST_PASSWORD')
function fixtureId(label: string): string {
  const hash = createHash('sha1').update(Buffer.from(runId, 'hex')).update(label, 'utf8').digest()
  hash[6] = (hash.readUInt8(6) & 0x0f) | 0x50
  hash[8] = (hash.readUInt8(8) & 0x3f) | 0x80
  const hex = hash.subarray(0, 16).toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
const profileId = fixtureId('invitation_v2_profile')
const foreignId = fixtureId('invitation_v2_foreign_profile')
const currentWorkspace = fixtureId('invitation_v2_workspace_current')
const previousWorkspace = fixtureId('invitation_v2_workspace_previous')
const managerPath = `/profiles/${profileId}/members`
const createPath = `/api/v1/profiles/${profileId}/invitations/`
const candidatePath = `/api/v1/profiles/${profileId}/invitation-candidates/`
type Invitation = { id: string; status: string; delivery_status: string; expires_at: string; recipient_email: string | null }

async function enterSecret(page: Page, label: string, value: string) {
  try {
    await page.getByLabel(label, { exact: true }).evaluate((element, secret) => {
      if (!(element instanceof HTMLInputElement) || element.type !== 'password') throw new Error('Masked field required.')
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      if (!setter) throw new Error('Native setter unavailable.')
      setter.call(element, secret)
      element.dispatchEvent(new Event('input', { bubbles: true }))
    }, value)
  } catch { throw new Error('Isolated masked credential entry failed.') }
}
async function login(page: Page, actor: string) {
  await page.goto('/login')
  const email = actor === 'legacy' ? `acceptance.${runId}@example.test` : `invitation_v2_${actor}.${runId}@example.test`
  await page.getByLabel('Email', { exact: true }).fill(email)
  await enterSecret(page, 'Mật khẩu', password)
  const saved = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/login/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await saved).status()).toBe(200)
  await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
}
async function logout(page: Page) {
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
  await expect(page).toHaveURL(/\/login(?:\?|$)/)
  await expect(page.locator('.notification-item')).toHaveCount(0)
}
async function csrf(page: Page) {
  const response = await page.request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  return { 'X-CSRFToken': (await response.json() as { csrf_token: string }).csrf_token }
}
async function openPicker(page: Page) {
  await page.goto(managerPath)
  await page.getByRole('button', { name: 'Thêm thành viên', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Mời thành viên', exact: true })
  await expect(dialog.getByLabel('Tìm tài khoản', { exact: true })).toBeVisible()
  return dialog
}
async function invite(page: Page, actor: string): Promise<Invitation> {
  const dialog = await openPicker(page)
  await dialog.getByLabel('Tìm tài khoản', { exact: true }).fill(`fixture_v2_${actor}`)
  await dialog.getByRole('radio', { name: new RegExp(`fixture_v2_${actor}`) }).check()
  await dialog.getByLabel('Vai trò tổ chức', { exact: true }).selectOption('MEMBER')
  const saved = page.waitForResponse((response) => new URL(response.url()).pathname === createPath && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Gửi lời mời', exact: true }).click()
  const response = await saved
  expect(response.status()).toBe(201)
  expect(response.request().postDataJSON()).toEqual({ recipient_user_id: fixtureId(`invitation_v2_${actor}`), requested_role: 'MEMBER' })
  expect(Boolean(response.request().headers()['x-csrftoken'])).toBe(true)
  const body = await response.json() as Invitation
  expect(body.recipient_email).toBeNull()
  expect(body.status).toBe('PENDING')
  expect(Object.keys(body)).not.toContain('token')
  expect(Object.keys(body)).not.toContain('token_digest')
  await expect(dialog).not.toBeVisible()
  return body
}
async function decide(page: Page, id: string, action: 'accept' | 'decline') {
  const path = `/api/v1/invitations/${id}/${action}/`
  const response = page.waitForResponse((item) => new URL(item.url()).pathname === path && item.request().method() === 'POST')
  await page.getByRole('button', { name: action === 'accept' ? 'Chấp nhận lời mời' : 'Từ chối lời mời', exact: true }).click()
  // Shared inline confirmation also works within the notification menu dialog.
  const confirm = page.getByRole('button', { name: 'Xác nhận từ chối', exact: true })
  if (await confirm.isVisible()) await confirm.click()
  const saved = await response
  expect(saved.status()).toBe(200)
  expect(saved.request().postDataJSON()).toEqual({})
  return saved
}

test.describe('Invitation V2 — real React/Django and owned PostgreSQL, fake mail only', () => {
  test.describe.configure({ mode: 'serial' })
  const pageErrors = new WeakMap<Page, string[]>()
  const ownerErrors: string[] = []
  let ownerContext: BrowserContext
  let owner: Page
  test.beforeAll(async ({ browser }) => {
    ownerContext = await browser.newContext({ baseURL: test.info().project.use.baseURL })
    owner = await ownerContext.newPage()
    owner.on('pageerror', (error) => ownerErrors.push(error.name))
    owner.on('response', (response) => { if (response.status() >= 500) ownerErrors.push(`Unexpected HTTP ${response.status()}`) })
    // Reuse the real Owner session; do not disable or evade login throttling.
    await login(owner, 'owner')
  })
  test.afterAll(async () => { await ownerContext?.close() })
  test.beforeEach(({ page }) => {
    const errors: string[] = []
    pageErrors.set(page, errors)
    page.on('pageerror', (error) => errors.push(error.name))
    page.on('response', (response) => { if (response.status() >= 500) errors.push(`Unexpected HTTP ${response.status()}`) })
  })
  test.afterEach(({ page }) => { expect(pageErrors.get(page)).toEqual([]); expect(ownerErrors).toEqual([]) })

  test('manager searches bounded private account pages; picker supports keyboard, four-size reflow and axe', async () => {
    const page = owner
    test.setTimeout(90_000)
    const dialog = await openPicker(page)
    await dialog.getByLabel('Tìm tài khoản', { exact: true }).fill('V2 Candidate')
    await expect(dialog.getByRole('radio')).toHaveCount(20)
    const data = await page.request.get(`${candidatePath}?search=V2%20Candidate&page=1`)
    expect(data.status()).toBe(200)
    const body = await data.json() as { count: number; results: Record<string, unknown>[] }
    expect(body.count).toBe(25)
    expect(body.results).toHaveLength(20)
    for (const row of body.results) {
      for (const forbidden of ['email', 'phone', 'is_staff', 'email_verified_at', 'memberships']) expect(Object.keys(row)).not.toContain(forbidden)
      expect(JSON.stringify(row)).not.toContain(`.${runId}@example.test`)
    }
    await dialog.getByRole('button', { name: 'Trang sau', exact: true }).click()
    await expect(dialog.getByRole('radio')).toHaveCount(5)
    await dialog.getByLabel('Tìm tài khoản', { exact: true }).fill('no-such-invitation-account')
    await expect(dialog.getByRole('radio')).toHaveCount(0)
    await expect(dialog.getByText('Không có tài khoản phù hợp. Thử tên hoặc username khác.', { exact: true })).toBeVisible()
    await dialog.getByLabel('Tìm tài khoản', { exact: true }).fill('fixture_v2_recipient')
    const choice = dialog.getByRole('radio', { name: /fixture_v2_recipient/ })
    await expect(choice).toBeVisible()
    for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
      await page.setViewportSize(size)
      await expect(dialog.getByRole('button', { name: 'Gửi lời mời', exact: true })).toBeVisible()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
      expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
      if (size.width === 375 || size.width === 1440) await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `invitation-v2-picker-${size.width}.png`), fullPage: true })
    }
    await page.setViewportSize({ width: 1440, height: 1000 })
    await choice.focus()
    await page.keyboard.press('Space')
    await expect(choice).toBeChecked()
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'Thêm thành viên', exact: true })).toBeFocused()
    const emailOnly = await page.request.post(createPath, { headers: await csrf(page), data: { recipient_email: 'synthetic@example.test', requested_role: 'MEMBER' } })
    expect(emailOnly.status()).toBe(400)
  })

  test('zero-Profile recipient sees own Web notification, marks read independently and accepts with current-month access', async ({ page }) => {
    const issued = await invite(owner, 'recipient')
    expect(issued.delivery_status).toBe('SENT')
    const duplicate = await owner.request.post(createPath, { headers: await csrf(owner), data: { recipient_user_id: fixtureId('invitation_v2_recipient'), requested_role: 'MEMBER' } })
    expect(duplicate.status()).toBe(409)
    await login(page, 'member')
    expect((await page.request.get(candidatePath)).status()).toBe(403)
    expect((await page.request.get(`/api/v1/invitations/${issued.id}/`)).status()).toBe(404)
    await logout(page)
    await login(page, 'recipient')
    const before = await page.request.get('/api/v1/profiles/')
    expect((await before.json() as { count: number }).count).toBe(0)
    await page.goto('/notifications')
    const notification = page.getByRole('article').filter({ hasText: 'V2 Invitation Studio' })
    await expect(notification.getByRole('button', { name: 'Chấp nhận lời mời', exact: true })).toBeVisible()
    await notification.getByRole('button', { name: 'Đánh dấu đã đọc', exact: true }).click()
    await expect(notification).toContainText('Đã đọc')
    const stillPending = await page.request.get(`/api/v1/invitations/${issued.id}/`)
    expect((await stillPending.json() as { status: string }).status).toBe('PENDING')
    await decide(page, issued.id, 'accept')
    const workspaces = await page.request.get(`/api/v1/profiles/${profileId}/workspaces/`)
    expect((await workspaces.json() as { results: { id: string }[] }).results.map((row) => row.id)).toEqual([currentWorkspace])
    expect((await page.request.get(`/api/v1/profiles/${profileId}/workspaces/${previousWorkspace}/`)).status()).toBe(404)
    const tasks = await page.request.get(`/api/v1/profiles/${profileId}/workspaces/${currentWorkspace}/tasks/`)
    expect((await tasks.json() as { count: number }).count).toBe(0)
    const replay = await page.request.post(`/api/v1/invitations/${issued.id}/accept/`, { headers: await csrf(page), data: {} })
    expect(replay.status()).toBe(200)
    await page.reload()
    await expect(page.getByRole('button', { name: 'Chấp nhận lời mời', exact: true })).toHaveCount(0)
    await logout(page)
    await login(page, 'decliner')
    await page.goto('/notifications')
    await expect(page.getByRole('article').filter({ hasText: 'V2 Invitation Studio' })).toHaveCount(0)
  })

  test('recipient declines through React without joining; Admin cannot issue ADMIN or access another tenant directory', async ({ page }) => {
    await login(page, 'admin')
    const dialog = await openPicker(page)
    expect(await dialog.getByLabel('Vai trò tổ chức', { exact: true }).locator('option').evaluateAll((options) => options.map((option) => option.getAttribute('value')))).toEqual(['', 'MEMBER'])
    await page.keyboard.press('Escape')
    const denied = await page.request.post(createPath, { headers: await csrf(page), data: { recipient_user_id: fixtureId('invitation_v2_decliner'), requested_role: 'ADMIN' } })
    expect(denied.status()).toBe(403)
    const csrfDenied = await page.request.post(createPath, { data: { recipient_user_id: fixtureId('invitation_v2_decliner'), requested_role: 'MEMBER' } })
    expect(csrfDenied.status()).toBe(403)
    expect((await page.request.get(`/api/v1/profiles/${foreignId}/invitation-candidates/`)).status()).toBe(404)
    const issued = await invite(page, 'decliner')
    await logout(page)
    await login(page, 'decliner')
    await page.goto(`/invitations/${issued.id}`)
    await decide(page, issued.id, 'decline')
    const profiles = await page.request.get('/api/v1/profiles/')
    expect((await profiles.json() as { count: number }).count).toBe(0)
    await page.reload()
    await expect(page.getByRole('button', { name: 'Chấp nhận lời mời', exact: true })).toHaveCount(0)
  })

  test('fake SMTP failure preserves committed Web invitation and permits recipient acceptance', async ({ page }) => {
    const issued = await invite(owner, 'failed')
    expect(issued.delivery_status).toBe('FAILED')
    await owner.reload()
    await expect(owner.getByText('V2 Email lỗi', { exact: true })).toBeVisible()
    await login(page, 'failed')
    await page.goto(`/invitations/${issued.id}`)
    await decide(page, issued.id, 'accept')
    const state = await page.request.get(`/api/v1/invitations/${issued.id}/`)
    expect((await state.json() as { status: string }).status).toBe('ACCEPTED')
  })

  test('explicit mail retry retains Invitation ID/expiry, Web notification and independent read state', async ({ page }) => {
    const issued = await invite(owner, 'retry')
    expect(issued.delivery_status).toBe('FAILED')
    const row = owner.getByRole('list', { name: 'Lời mời tổ chức', exact: true }).getByRole('listitem').filter({ hasText: 'V2 Thử lại email' })
    const saved = owner.waitForResponse((response) => new URL(response.url()).pathname === `${createPath}${issued.id}/resend/` && response.request().method() === 'POST')
    await row.getByRole('button', { name: 'Thử gửi lại email', exact: true }).click()
    const response = await saved
    expect(response.status()).toBe(200)
    const retried = await response.json() as Invitation
    expect(retried).toMatchObject({ id: issued.id, expires_at: issued.expires_at, status: 'PENDING', delivery_status: 'SENT' })
    await login(page, 'retry')
    const notifications = await page.request.get('/api/v1/notifications/')
    const rows = (await notifications.json() as { results: { invitation_id: string; is_read: boolean }[] }).results.filter((item) => item.invitation_id === issued.id)
    expect(rows).toHaveLength(1)
    expect(rows[0]?.is_read).toBe(false)
    await page.goto(`/invitations/${issued.id}`)
    await expect(page.getByRole('button', { name: 'Chấp nhận lời mời', exact: true })).toBeVisible()
  })

  test('an account in another organization accepts the exact target without losing its previous membership or auto-navigation', async ({ page }) => {
    const issued = await invite(owner, 'switcher')
    await login(page, 'switcher')
    await page.goto(`/profiles/${foreignId}`)
    await expect(page.getByRole('heading', { name: 'V2 Other Studio', exact: true })).toBeVisible()
    await page.goto(`/invitations/${issued.id}`)
    await decide(page, issued.id, 'accept')
    await expect(page).toHaveURL(`/invitations/${issued.id}`)
    const profiles = await page.request.get('/api/v1/profiles/')
    const ids = (await profiles.json() as { results: { id: string }[] }).results.map((row) => row.id)
    expect(ids).toContain(profileId)
    expect(ids).toContain(foreignId)
    expect((await page.request.get(`/api/v1/profiles/${foreignId}/`)).status()).toBe(200)
    expect((await page.request.get(`/api/v1/profiles/${profileId}/workspaces/${currentWorkspace}/`)).status()).toBe(200)
  })

  test('pre-cutover legacy token still works through its unpromoted compatibility route', async ({ page }) => {
    await login(page, 'legacy')
    const container = required('HT_FRONTEND_TEST_BACKEND_CONTAINER')
    if (container !== `ht-fe-${runId}-backend`) throw new Error('Unexpected owned backend.')
    let token: string
    try {
      token = execFileSync('docker', ['exec', container, 'python', '/workspace/scripts/frontend_integration.py', 'consume-test-mail', 'registered', 'invitation'], { encoding: 'utf8', timeout: 15_000, stdio: ['ignore', 'pipe', 'pipe'] }).trim()
      if (!/^[A-Za-z0-9_-]{43}$/.test(token)) throw new Error('Unexpected synthetic credential format.')
    } catch { throw new Error('Private isolated legacy mail could not be consumed.') }
    await page.goto('/invitations/respond')
    await enterSecret(page, 'Mã lời mời', token)
    const saved = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/invitations/accept/' && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Chấp nhận lời mời', exact: true }).click()
    expect((await saved).status()).toBe(200)
    await expect(page.getByRole('heading', { name: 'Đã tham gia tổ chức', exact: true })).toBeVisible()
    expect((await page.request.get(`/api/v1/profiles/${profileId}/`)).status()).toBe(200)
  })
})

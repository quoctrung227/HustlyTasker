import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page, type Response } from '@playwright/test'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated members integration launcher.')
  return value
}
const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Invalid isolated fixture run identity.')
const recipient = `acceptance.${runId}@example.test`
const password = required('HT_FRONTEND_TEST_PASSWORD')
function fixtureId(label: string): string {
  const hash = createHash('sha1').update(Buffer.from(runId, 'hex')).update(label, 'utf8').digest()
  hash[6] = (hash.readUInt8(6) & 0x0f) | 0x50
  hash[8] = (hash.readUInt8(8) & 0x3f) | 0x80
  const hex = hash.subarray(0, 16).toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
const managementId = fixtureId('management_profile')
const studioId = fixtureId('profile')
const otherId = fixtureId('other_profile')
const workspaceId = fixtureId('management_workspace')
const apiProfile = (id: string) => `/api/v1/profiles/${id}/`
const apiInvitations = (id: string) => `${apiProfile(id)}invitations/`
const rowFor = (page: Page, status?: string) => {
  const rows = page.getByRole('list', { name: 'Lời mời tổ chức', exact: true }).getByRole('listitem').filter({
    has: page.getByRole('heading', { name: recipient, exact: true }),
  })
  return status ? rows.filter({ hasText: status }) : rows
}

/** No credentials in fill-call diagnostics, CLI argv, URLs or screenshots. */
async function enterSecret(page: Page, label: string, value: string) {
  try {
    await page.getByLabel(label, { exact: true }).evaluate((element, secret) => {
      if (!(element instanceof HTMLInputElement) || element.type !== 'password') throw new Error('Masked input required.')
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      if (!setter) throw new Error('Native setter unavailable.')
      setter.call(element, secret)
      element.dispatchEvent(new Event('input', { bubbles: true }))
    }, value)
  } catch { throw new Error('Isolated masked credential entry failed.') }
}
function consumeInvitation(): string {
  const container = required('HT_FRONTEND_TEST_BACKEND_CONTAINER')
  if (container !== `ht-fe-${runId}-backend`) throw new Error('Unexpected isolated backend identity.')
  try {
    const token = execFileSync('docker', ['exec', container, 'python', '/workspace/scripts/frontend_integration.py', 'consume-test-mail', 'registered', 'invitation'], {
      encoding: 'utf8', timeout: 15_000, stdio: ['ignore', 'pipe', 'pipe'],
    }).trim()
    if (!/^[A-Za-z0-9_-]{43}$/.test(token)) throw new Error('Unexpected credential format.')
    return token
  } catch { throw new Error('Delivered isolated invitation could not be consumed.') }
}
async function login(page: Page, actor: 'owner' | 'recipient' | 'manager', followExistingForm = false) {
  if (!followExistingForm) await page.goto('/login')
  const email = actor === 'owner' ? required('HT_FRONTEND_TEST_OWNER_EMAIL') : actor === 'recipient' ? recipient : `manager.${runId}@example.test`
  await page.getByLabel('Email', { exact: true }).fill(email)
  await enterSecret(page, 'Mật khẩu', password)
  const result = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/login/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await result).status()).toBe(200)
  await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
}
async function logout(page: Page) {
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
  await expect(page).toHaveURL(/\/login(?:\?|$)/)
  await expect(page.getByRole('list', { name: 'Lời mời tổ chức', exact: true })).toHaveCount(0)
}
async function openMembers(page: Page, profileId: string) {
  await page.goto(`/profiles/${profileId}`)
  await page.getByRole('link', { name: 'Thành viên tổ chức', exact: true }).click()
  await expect(page).toHaveURL(`/profiles/${profileId}/members`)
  await expect(page.getByRole('heading', { name: 'Thành viên tổ chức', level: 1 })).toBeVisible()
  await expect(page.getByRole('list', { name: 'Thành viên tổ chức', exact: true })).toBeVisible()
}
async function invite(page: Page, profileId: string) {
  await page.getByRole('button', { name: 'Mời thành viên', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Mời thành viên', exact: true })
  await dialog.getByLabel('Email người nhận', { exact: true }).fill(recipient)
  await dialog.getByLabel('Vai trò tổ chức', { exact: true }).selectOption('MEMBER')
  const result = page.waitForResponse((response) => new URL(response.url()).pathname === apiInvitations(profileId) && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Gửi lời mời', exact: true }).click()
  const response = await result
  expect(response.status()).toBe(201)
  expect(response.request().postDataJSON()).toEqual({ recipient_email: recipient, requested_role: 'MEMBER' })
  expect(Boolean(response.request().headers()['x-csrftoken'])).toBe(true)
  const created = await response.json() as { id: string; status: string; delivery_status: string; profile_id: string }
  expect(created).toMatchObject({ status: 'PENDING', delivery_status: 'SENT', profile_id: profileId })
  await expect(dialog).not.toBeVisible()
  await expect(rowFor(page, 'Đang chờ phản hồi')).toContainText('Hệ thống email đã tiếp nhận')
  return created
}
async function respond(page: Page, token: string, action: 'accept' | 'decline'): Promise<Response> {
  await page.goto('/invitations/respond')
  await expect(page.getByRole('heading', { name: 'Phản hồi lời mời', level: 1 })).toBeVisible()
  await enterSecret(page, 'Mã lời mời', token)
  const result = page.waitForResponse((response) => new URL(response.url()).pathname === `/api/v1/invitations/${action}/` && response.request().method() === 'POST')
  await page.getByRole('button', { name: action === 'accept' ? 'Chấp nhận lời mời' : 'Từ chối lời mời', exact: true }).click()
  if (action === 'decline') {
    await page.getByRole('dialog').getByRole('button', { name: 'Xác nhận từ chối', exact: true }).click()
  }
  const response = await result
  // Never pass the secret into an assertion's expected/actual diagnostic text.
  const body = response.request().postDataJSON() as Record<string, unknown>
  expect(Object.keys(body)).toEqual(['token'])
  expect(body.token === token).toBe(true)
  expect(Boolean(response.request().headers()['x-csrftoken'])).toBe(true)
  expect(page.url().includes(token)).toBe(false)
  return response
}

test.describe('Organization members and invitation — real isolated Django/PostgreSQL', () => {
  // This bounded journey intentionally reuses the one newly registered email;
  // failed setup must not cascade into additional token/login attempts.
  test.describe.configure({ mode: 'serial' })
  const failures = new WeakMap<Page, string[]>()
  test.beforeEach(({ page }) => {
    const errors: string[] = []
    failures.set(page, errors)
    page.on('pageerror', (error) => errors.push(error.name))
    page.on('response', (response) => { if (response.status() >= 500) errors.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })
  })
  test.afterEach(({ page }) => { expect(failures.get(page)).toEqual([]) })

  test('Owner invites through React; a newly registered recipient accepts explicitly and gains Profile membership only', async ({ page }) => {
    test.setTimeout(60_000)
    await login(page, 'owner')
    await openMembers(page, managementId)
    await expect(page.getByRole('list', { name: 'Thành viên tổ chức', exact: true })).toContainText('Chủ Tổ chức')
    const created = await invite(page, managementId)
    const secret = consumeInvitation()
    const persisted = await page.request.get(`${apiInvitations(managementId)}${created.id}/`)
    expect(persisted.status()).toBe(200)
    const metadata = await persisted.json() as Record<string, unknown>
    expect(metadata.status).toBe('PENDING')
    expect(Object.keys(metadata)).not.toContain('token')
    expect(Object.keys(metadata)).not.toContain('token_digest')
    expect(JSON.stringify(metadata).includes(secret)).toBe(false)
    await logout(page)

    // No User/Profile membership fixture is seeded for this recipient. Signup,
    // login, invitation acceptance and resulting membership are real UI actions.
    await page.goto('/invitations/respond')
    await expect(page).toHaveURL('/login')
    await page.getByRole('link', { name: 'Đăng ký tài khoản', exact: true }).click()
    await page.getByLabel('Email', { exact: true }).fill(recipient)
    await page.getByLabel('Tên đăng nhập', { exact: true }).fill(`invited_${runId.slice(0, 8)}`)
    await page.getByLabel('Tên (không bắt buộc)', { exact: true }).fill('Người nhận')
    await enterSecret(page, 'Mật khẩu', password)
    await enterSecret(page, 'Xác nhận mật khẩu', password)
    const registered = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/register/' && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click()
    expect((await registered).status()).toBe(201)
    await expect(page.getByText(/Tài khoản đã được tạo\./)).toBeVisible()
    await page.getByRole('link', { name: 'Về đăng nhập', exact: true }).click()
    await login(page, 'recipient', true)
    await expect(page).toHaveURL('/invitations/respond')
    const before = await page.request.get('/api/v1/profiles/')
    expect((await before.json() as { count: number }).count).toBe(0)
    const accepted = await respond(page, secret, 'accept')
    expect(accepted.status()).toBe(200)
    expect(await accepted.json()).toMatchObject({ status: 'ACCEPTED', profile_id: managementId, role: 'MEMBER' })
    await expect(page.getByRole('heading', { name: 'Đã tham gia tổ chức', exact: true })).toBeVisible()
    await expect(page.getByLabel('Mã lời mời', { exact: true })).toHaveCount(0)
    await page.getByRole('link', { name: 'Đến tổ chức', exact: true }).click()
    await expect(page).toHaveURL(`/profiles/${managementId}`)
    const permitted = await page.request.get('/api/v1/profiles/')
    expect((await permitted.json() as { results: { id: string }[] }).results.map((profile) => profile.id)).toEqual([managementId])
    const workspaces = await page.request.get(`${apiProfile(managementId)}workspaces/`)
    expect((await workspaces.json() as { count: number }).count).toBe(0)
    expect((await page.request.get(`${apiProfile(managementId)}workspaces/${workspaceId}/`)).status()).toBe(404)
    expect((await page.request.get(`${apiProfile(managementId)}members/`)).status()).toBe(403)
    const replay = await respond(page, secret, 'accept')
    expect(replay.status()).toBe(409)
    await expect(page.getByRole('alert')).toBeVisible()
    expect((await page.request.get(`${apiProfile(otherId)}members/`)).status()).toBe(404)
  })

  test('wrong recipient is rejected, resend rotates the credential, and an existing account may decline through React', async ({ page, browser }) => {
    test.setTimeout(60_000)
    await login(page, 'owner')
    await openMembers(page, studioId)
    const issued = await invite(page, studioId)
    const oldSecret = consumeInvitation()
    const otherContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' })
    try {
      const wrongPage = await otherContext.newPage()
      await login(wrongPage, 'manager')
      const denied = await respond(wrongPage, oldSecret, 'accept')
      expect(denied.status()).toBe(409)
      expect(JSON.stringify(await denied.json()).includes(recipient)).toBe(false)
      await expect(wrongPage.getByRole('alert')).toBeVisible()
    } finally { await otherContext.close() }

    const resent = page.waitForResponse((response) => new URL(response.url()).pathname === `${apiInvitations(studioId)}${issued.id}/resend/` && response.request().method() === 'POST')
    await rowFor(page, 'Đang chờ phản hồi').getByRole('button', { name: 'Gửi lại lời mời', exact: true }).click()
    const replacement = await resent
    expect(replacement.status()).toBe(200)
    const next = await replacement.json() as { id: string; status: string; delivery_status: string }
    expect(next.id === issued.id).toBe(false)
    expect(next).toMatchObject({ status: 'PENDING', delivery_status: 'SENT' })
    const secret = consumeInvitation()
    expect(secret === oldSecret).toBe(false)
    await expect(rowFor(page, 'Đã hủy')).toHaveCount(1)
    await expect(rowFor(page, 'Đang chờ phản hồi')).toHaveCount(1)
    await logout(page)
    await login(page, 'recipient')
    expect((await respond(page, oldSecret, 'accept')).status()).toBe(409)
    const declined = await respond(page, secret, 'decline')
    expect(declined.status()).toBe(200)
    expect(await declined.json()).toEqual({ status: 'DECLINED' })
    const profiles = await page.request.get('/api/v1/profiles/')
    expect((await profiles.json() as { results: { id: string }[] }).results.some((profile) => profile.id === studioId)).toBe(false)
  })

  test('Owner revokes pending invitation; Workspace manager cannot administer Profile invitations or cross tenant boundaries', async ({ page, browser }) => {
    await login(page, 'owner')
    await openMembers(page, otherId)
    const issued = await invite(page, otherId)
    const secret = consumeInvitation()
    await rowFor(page, 'Đang chờ phản hồi').getByRole('button', { name: 'Hủy lời mời', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: 'Hủy lời mời', exact: true })
    const revoked = page.waitForResponse((response) => new URL(response.url()).pathname === `${apiInvitations(otherId)}${issued.id}/revoke/` && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Xác nhận hủy lời mời', exact: true }).click()
    expect((await revoked).status()).toBe(200)
    await expect(dialog).not.toBeVisible()
    await expect(rowFor(page, 'Đã hủy')).toHaveCount(1)
    await logout(page)
    await login(page, 'recipient')
    expect((await respond(page, secret, 'accept')).status()).toBe(409)

    const restricted = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' })
    try {
      const manager = await restricted.newPage()
      await login(manager, 'manager')
      await manager.goto(`/profiles/${managementId}/members`)
      await expect(manager.getByRole('button', { name: 'Mời thành viên', exact: true })).toHaveCount(0)
      await expect(manager.getByText(/Chỉ Chủ sở hữu hoặc Quản trị viên tổ chức/)).toBeVisible()
      expect((await manager.request.get(`${apiProfile(managementId)}members/`)).status()).toBe(403)
      const csrf = await manager.request.get('/api/auth/csrf/')
      const token = (await csrf.json() as { csrf_token: string }).csrf_token
      // Deliberate API-driven negative authorization probe, not a successful UI mutation.
      expect((await manager.request.post(apiInvitations(managementId), { headers: { 'X-CSRFToken': token }, data: { recipient_email: `denied.${runId}@example.test`, requested_role: 'MEMBER' } })).status()).toBe(403)
      expect((await manager.request.get(`${apiProfile(otherId)}members/`)).status()).toBe(404)
    } finally { await restricted.close() }
  })

  test('invitation draft survives real background refresh, stays accessible at four viewports, and preserves Task-create stability', async ({ page }) => {
    test.setTimeout(90_000)
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await login(page, 'owner')
    await openMembers(page, managementId)
    await page.getByRole('button', { name: 'Mời thành viên', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: 'Mời thành viên', exact: true })
    const original = await dialog.elementHandle()
    if (!original) throw new Error('Expected mounted invitation form.')
    const unsent = `unsent.${runId}@example.test`
    await dialog.getByLabel('Email người nhận', { exact: true }).fill(unsent)
    await dialog.getByLabel('Vai trò tổ chức', { exact: true }).selectOption('ADMIN')
    let sent = 0
    page.on('request', (request) => { if (request.method() === 'POST' && new URL(request.url()).pathname === apiInvitations(managementId)) sent += 1 })
    for (const event of ['focus', 'visibilitychange']) {
      const response = page.waitForResponse((item) => new URL(item.url()).pathname === '/api/auth/me/' && item.request().method() === 'GET')
      await page.evaluate((kind) => { if (kind === 'focus') window.dispatchEvent(new Event(kind)); else document.dispatchEvent(new Event(kind)) }, event)
      expect((await response).status()).toBe(200)
      expect(await original.evaluate((element) => element.isConnected && element === document.querySelector('dialog[open]'))).toBe(true)
      await expect(dialog.getByLabel('Email người nhận', { exact: true })).toHaveValue(unsent)
      await expect(dialog.getByLabel('Vai trò tổ chức', { exact: true })).toHaveValue('ADMIN')
    }
    for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
      await page.setViewportSize(size)
      await dialog.getByLabel('Email người nhận', { exact: true }).focus()
      await expect(dialog.getByLabel('Email người nhận', { exact: true })).toBeFocused()
      await page.keyboard.press('Tab')
      await expect(dialog.getByLabel('Vai trò tổ chức', { exact: true })).toBeFocused()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      const accessibility = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
      expect(accessibility.violations.map((violation) => violation.id)).toEqual([])
      await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `members-invite-${size.width}.png`), fullPage: false, animations: 'disabled', caret: 'hide', timeout: 5000 })
    }
    expect(sent).toBe(0)
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'Mời thành viên', exact: true })).toBeFocused()
    await page.goto(`/profiles/${managementId}/workspaces/${workspaceId}/tasks`)
    await page.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
    const taskDialog = page.getByRole('dialog', { name: 'Tạo công việc', exact: true })
    await taskDialog.getByLabel('Tên công việc', { exact: true }).fill('Unsent task stability check')
    const refresh = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/me/' && response.request().method() === 'GET')
    await page.evaluate(() => window.dispatchEvent(new Event('focus')))
    expect((await refresh).status()).toBe(200)
    await expect(taskDialog.getByLabel('Tên công việc', { exact: true })).toHaveValue('Unsent task stability check')
    await page.keyboard.press('Escape')
    expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([])
  })
})

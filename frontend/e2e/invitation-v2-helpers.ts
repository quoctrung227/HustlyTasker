import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { expect, type Page } from '@playwright/test'

export function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated Invitation V2 launcher.')
  return value
}
export const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Unexpected isolated run identity.')
export function fixtureId(label: string): string {
  const hash = createHash('sha1').update(Buffer.from(runId, 'hex')).update(label, 'utf8').digest()
  hash[6] = (hash.readUInt8(6) & 0x0f) | 0x50; hash[8] = (hash.readUInt8(8) & 0x3f) | 0x80
  const hex = hash.subarray(0, 16).toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
export const profileId = fixtureId('invitation_v2_profile')
export const foreignId = fixtureId('invitation_v2_foreign_profile')
export const currentWorkspace = fixtureId('invitation_v2_workspace_current')
export const previousWorkspace = fixtureId('invitation_v2_workspace_previous')
export const managerPath = `/profiles/${profileId}/members`
export const createPath = `/api/v1/profiles/${profileId}/invitations/`
export type Invitation = { id: string; profile_id: string; recipient_email: string | null; recipient_display_label: string; status: string; delivery_status: string; expires_at: string; requested_role: string }
export async function enterSecret(page: Page, label: string, value: string) {
  try {
    await page.getByLabel(label, { exact: true }).evaluate((element, secret) => {
      if (!(element instanceof HTMLInputElement) || element.type !== 'password') throw new Error('Masked field required.')
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      if (!setter) throw new Error('Native setter unavailable.')
      setter.call(element, secret); element.dispatchEvent(new Event('input', { bubbles: true }))
    }, value)
  } catch { throw new Error('Isolated masked credential entry failed.') }
}
export async function login(page: Page, actor: string) {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(actor === 'legacy' ? `acceptance.${runId}@example.test` : `invitation_v2_${actor}.${runId}@example.test`)
  await enterSecret(page, 'Mật khẩu', required('HT_FRONTEND_TEST_PASSWORD'))
  const saved = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/login/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await saved).status()).toBe(200)
  await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
}
export async function logout(page: Page) {
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
  await expect(page).toHaveURL(/\/login(?:\?|$)/)
  await expect(page.locator('.notification-item')).toHaveCount(0)
}
export async function csrf(page: Page) {
  const response = await page.request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  return { 'X-CSRFToken': (await response.json() as { csrf_token: string }).csrf_token }
}
export async function openPicker(page: Page, actor?: string) {
  await page.goto(managerPath)
  await page.getByRole('button', { name: 'Thêm thành viên', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Mời thành viên', exact: true })
  await expect(dialog.getByLabel('Tìm tài khoản', { exact: true })).toBeVisible()
  if (actor) {
    await dialog.getByLabel('Tìm tài khoản', { exact: true }).fill(`fixture_v2_${actor}`)
    await dialog.getByRole('radio', { name: new RegExp(`fixture_v2_${actor}`) }).check()
  }
  return dialog
}
export async function invite(page: Page, actor: string, role = 'MEMBER'): Promise<Invitation> {
  const dialog = await openPicker(page, actor)
  await dialog.getByLabel('Vai trò tổ chức', { exact: true }).selectOption(role)
  const saved = page.waitForResponse((response) => new URL(response.url()).pathname === createPath && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Gửi lời mời', exact: true }).click()
  const response = await saved
  expect(response.status()).toBe(201)
  expect(response.request().postDataJSON()).toEqual({ recipient_user_id: fixtureId(`invitation_v2_${actor}`), requested_role: role })
  expect(Boolean(response.request().headers()['x-csrftoken'])).toBe(true)
  const body = await response.json() as Invitation
  expect(body).toMatchObject({ profile_id: profileId, status: 'PENDING', recipient_email: null })
  expect(Object.keys(body)).not.toContain('token'); expect(Object.keys(body)).not.toContain('token_digest')
  await expect(dialog).not.toBeVisible()
  return body
}
export async function readInvitations(page: Page) {
  const response = await page.request.get(createPath)
  expect(response.status()).toBe(200)
  const data = await response.json() as { count: number; results: Invitation[] }
  for (const row of data.results) {
    expect(row.profile_id).toBe(profileId)
    expect(Object.keys(row)).not.toContain('token'); expect(Object.keys(row)).not.toContain('token_digest')
  }
  return data
}
export function invitationRow(page: Page, item: Invitation) {
  return page.getByRole('list', { name: 'Lời mời tổ chức', exact: true }).getByRole('listitem').filter({ has: page.getByRole('heading', { name: item.recipient_display_label, exact: true }) })
}
export function consumeLegacyInvitation() {
  const container = required('HT_FRONTEND_TEST_BACKEND_CONTAINER')
  if (container !== `ht-fe-${runId}-backend`) throw new Error('Unexpected isolated backend identity.')
  try {
    const token = execFileSync('docker', ['exec', container, 'python', '/workspace/scripts/frontend_integration.py', 'consume-test-mail', 'registered', 'invitation'], {
      encoding: 'utf8', timeout: 15_000, stdio: ['ignore', 'pipe', 'pipe'],
    }).trim()
    if (!/^[A-Za-z0-9_-]{43}$/.test(token)) throw new Error('Unexpected isolated credential format.')
    return token
  } catch { throw new Error('Cannot consume the isolated legacy invitation.') }
}

import { createHash } from 'node:crypto'
import { expect, test, type APIRequestContext, type APIResponse, type Page } from '@playwright/test'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated Invitation delivery failure launcher.')
  return value
}
const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Invalid isolated fixture identity.')
const recipient = `acceptance.${runId}@example.test`
function fixtureId(label: string): string {
  const hash = createHash('sha1').update(Buffer.from(runId, 'hex')).update(label, 'utf8').digest()
  hash[6] = (hash.readUInt8(6) & 0x0f) | 0x50
  hash[8] = (hash.readUInt8(8) & 0x3f) | 0x80
  const hex = hash.subarray(0, 16).toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
const profileId = fixtureId('management_profile')
const membersPage = `/profiles/${profileId}/members`
const invitationPath = `/api/v1/profiles/${profileId}/invitations/`
type Invitation = { id: string; status: string; delivery_status: string; recipient_email: string; profile_id: string }
type Invitations = { count: number; results: Invitation[] }

async function login(page: Page) {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(required('HT_FRONTEND_TEST_OWNER_EMAIL'))
  try {
    await page.getByLabel('Mật khẩu', { exact: true }).evaluate((element, secret) => {
      if (!(element instanceof HTMLInputElement) || element.type !== 'password') throw new Error('Masked input required.')
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      if (!setter) throw new Error('Native setter unavailable.')
      setter.call(element, secret)
      element.dispatchEvent(new Event('input', { bubbles: true }))
    }, required('HT_FRONTEND_TEST_PASSWORD'))
  } catch { throw new Error('Isolated masked login entry failed.') }
  const loggedIn = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/login/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await loggedIn).status()).toBe(200)
  await page.goto(membersPage)
  await expect(page.getByRole('heading', { name: 'Thành viên tổ chức', exact: true, level: 1 })).toBeVisible()
}
async function readInvitations(request: APIRequestContext): Promise<Invitations> {
  const response = await request.get(invitationPath)
  expect(response.status()).toBe(200)
  const page = await response.json() as Invitations
  for (const row of page.results) {
    expect(Object.keys(row)).not.toContain('token')
    expect(Object.keys(row)).not.toContain('token_digest')
    expect(row.profile_id).toBe(profileId)
  }
  return page
}
async function fillInvite(page: Page) {
  await page.getByRole('button', { name: 'Mời thành viên', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Mời thành viên', exact: true })
  await dialog.getByLabel('Email người nhận', { exact: true }).fill(recipient)
  await dialog.getByLabel('Vai trò tổ chức', { exact: true }).selectOption('MEMBER')
  return dialog
}
function rowFor(page: Page, state: string) {
  return page.getByRole('list', { name: 'Lời mời tổ chức', exact: true }).getByRole('listitem').filter({
    has: page.getByRole('heading', { name: recipient, exact: true }),
  }).filter({ hasText: state })
}

test.describe('Invitation delivery — real isolated commit and fake locmem transport', () => {
  test.describe.configure({ mode: 'serial' })
  let failedId: string
  let expectedDeliveryFailures = 0
  const errors = new WeakMap<Page, string[]>()
  test.beforeEach(({ page }) => {
    const failures: string[] = []
    errors.set(page, failures)
    page.on('pageerror', (error) => failures.push(error.name))
    page.on('response', (response) => {
      if (response.status() < 500) return
      const path = new URL(response.url()).pathname
      if (response.status() === 503 && path === invitationPath && response.request().method() === 'POST' && expectedDeliveryFailures === 0) {
        expectedDeliveryFailures += 1
      } else {
        failures.push(`Unexpected HTTP ${response.status()} ${path}`)
      }
    })
  })
  test.afterEach(({ page }) => { expect(errors.get(page)).toEqual([]) })

  test('post-commit delivery failure is visible after refresh; a repeated create conflicts without silently duplicating', async ({ page }) => {
    test.setTimeout(60_000)
    await login(page)
    expect((await readInvitations(page.request)).count).toBe(0)
    let posts = 0
    page.on('request', (request) => { if (request.method() === 'POST' && new URL(request.url()).pathname === invitationPath) posts += 1 })
    const dialog = await fillInvite(page)
    const failed = page.waitForResponse((response) => new URL(response.url()).pathname === invitationPath && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Gửi lời mời', exact: true }).click()
    const response = await failed
    expect(response.status()).toBe(503)
    const failurePayload = await response.json() as Record<string, unknown>
    expect(Object.keys(failurePayload)).toEqual(['detail'])
    expect(failurePayload.detail === 'Invitation delivery is currently unavailable.').toBe(true)
    expect(Boolean(response.request().headers()['x-csrftoken'])).toBe(true)
    await expect(dialog.getByRole('alert')).toContainText('Dịch vụ email hiện chưa sẵn sàng')
    await expect(dialog.getByLabel('Email người nhận', { exact: true })).toHaveValue(recipient)
    await expect(dialog.getByLabel('Vai trò tổ chức', { exact: true })).toHaveValue('MEMBER')
    expect(posts).toBe(1)
    expect(await page.getByText('Đã tạo lời mời. Hãy xem trạng thái email trong danh sách; lời mời chưa đồng nghĩa thành viên đã tham gia.', { exact: true }).count()).toBe(0)
    await dialog.getByRole('button', { name: 'Đóng', exact: true }).click()
    await expect(rowFor(page, 'Đang chờ phản hồi')).toContainText('Gửi email chưa thành công')
    const persisted = await readInvitations(page.request)
    expect(persisted.count).toBe(1)
    expect(persisted.results).toHaveLength(1)
    const failedRow = persisted.results[0]
    if (!failedRow) throw new Error('Expected the isolated failed Invitation row.')
    expect(failedRow).toMatchObject({ recipient_email: recipient, status: 'PENDING', delivery_status: 'FAILED' })
    failedId = failedRow.id
    await page.reload()
    await expect(rowFor(page, 'Đang chờ phản hồi')).toContainText('Gửi email chưa thành công')

    const retryDialog = await fillInvite(page)
    const retry = page.waitForResponse((result) => new URL(result.url()).pathname === invitationPath && result.request().method() === 'POST')
    await retryDialog.getByRole('button', { name: 'Gửi lời mời', exact: true }).click()
    expect((await retry).status()).toBe(409)
    await expect(retryDialog.getByRole('alert')).toBeVisible()
    await expect(retryDialog.getByLabel('Email người nhận', { exact: true })).toHaveValue(recipient)
    expect(posts).toBe(2)
    const unchanged = await readInvitations(page.request)
    expect(unchanged.count).toBe(1)
    expect(unchanged.results[0]).toMatchObject({ id: failedId, status: 'PENDING', delivery_status: 'FAILED' })
    expect(expectedDeliveryFailures).toBe(1)
  })

  test('an explicit resend uses fake locmem success, rotates the failed invitation and rejects replay on the old row', async ({ page }) => {
    test.setTimeout(60_000)
    await login(page)
    const failed = rowFor(page, 'Đang chờ phản hồi')
    await expect(failed).toContainText('Gửi email chưa thành công')
    const resend = page.waitForResponse((response) => new URL(response.url()).pathname === `${invitationPath}${failedId}/resend/` && response.request().method() === 'POST')
    await failed.getByRole('button', { name: 'Gửi lại lời mời', exact: true }).click()
    const response = await resend
    expect(response.status()).toBe(200)
    expect(response.request().postDataJSON()).toEqual({})
    expect(Boolean(response.request().headers()['x-csrftoken'])).toBe(true)
    const replacement = await response.json() as Invitation
    expect(Object.keys(replacement)).not.toContain('token')
    expect(Object.keys(replacement)).not.toContain('token_digest')
    expect(replacement.id === failedId).toBe(false)
    expect(replacement).toMatchObject({ status: 'PENDING', delivery_status: 'SENT', recipient_email: recipient })
    await expect(rowFor(page, 'Đang chờ phản hồi')).toContainText('Hệ thống email đã tiếp nhận')
    await expect(rowFor(page, 'Đã hủy')).toContainText('Gửi email chưa thành công')
    const stored = await readInvitations(page.request)
    expect(stored.count).toBe(2)
    expect(stored.results.filter((row) => row.status === 'PENDING')).toHaveLength(1)
    expect(stored.results.find((row) => row.id === failedId)).toMatchObject({ status: 'REVOKED', delivery_status: 'FAILED' })
    expect(stored.results.find((row) => row.id === replacement.id)).toMatchObject({ status: 'PENDING', delivery_status: 'SENT' })

    // A deliberate negative API probe, not a UI business mutation. Its session
    // and CSRF are still real; no raw credential is retained or diagnosed.
    const bootstrap = await page.request.get('/api/auth/csrf/')
    expect(bootstrap.status()).toBe(200)
    const data = await bootstrap.json() as { csrf_token: string }
    let replay: APIResponse
    try {
      replay = await page.request.post(`${invitationPath}${failedId}/resend/`, { headers: { 'X-CSRFToken': data.csrf_token }, data: {} })
    } catch { throw new Error('Isolated resend replay request failed.') }
    expect(replay.status()).toBe(409)
    expect((await readInvitations(page.request)).count).toBe(2)
    expect(expectedDeliveryFailures).toBe(1)
  })
})

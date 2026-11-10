import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type BrowserContext, type Page } from '@playwright/test'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated Workspace inheritance launcher.')
  return value
}
const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Invalid isolated fixture identity.')
const password = required('HT_FRONTEND_TEST_PASSWORD')
const recipientEmail = `acceptance.${runId}@example.test`
function fixtureId(label: string): string {
  const hash = createHash('sha1').update(Buffer.from(runId, 'hex')).update(label, 'utf8').digest()
  hash[6] = (hash.readUInt8(6) & 0x0f) | 0x50
  hash[8] = (hash.readUInt8(8) & 0x3f) | 0x80
  const hex = hash.subarray(0, 16).toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
const profileId = fixtureId('inheritance_profile')
const sourceId = fixtureId('inheritance_source')
const futureId = fixtureId('inheritance_future')
const firstProfileId = fixtureId('inheritance_first_profile')
const apiProfile = `/api/v1/profiles/${profileId}/`
const apiWorkspaces = `${apiProfile}workspaces/`
const workspaceList = `/profiles/${profileId}/workspaces`
const createdName = `Workspace kế thừa ${runId.slice(0, 8)}`
type Roster = { count: number; results: { id: string; profile_membership_id: string; display_label: string; role: string; is_active: boolean }[] }

async function enterSecret(page: Page, label: string, secret: string) {
  try {
    await page.getByLabel(label, { exact: true }).evaluate((element, value) => {
      if (!(element instanceof HTMLInputElement) || element.type !== 'password') throw new Error('Masked input required.')
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      if (!setter) throw new Error('Native setter unavailable.')
      setter.call(element, value)
      element.dispatchEvent(new Event('input', { bubbles: true }))
    }, secret)
  } catch { throw new Error('Isolated masked credential entry failed.') }
}
async function login(page: Page, actor: string, formAlreadyOpen = false) {
  if (!formAlreadyOpen) await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(actor === 'recipient' ? recipientEmail : `${actor}.${runId}@example.test`)
  await enterSecret(page, 'Mật khẩu', password)
  const response = page.waitForResponse((result) => new URL(result.url()).pathname === '/api/auth/login/' && result.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await response).status()).toBe(200)
  await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
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
async function roster(page: Page, id: string, profile = profileId): Promise<Roster> {
  const response = await page.request.get(`/api/v1/profiles/${profile}/workspaces/${id}/members/`)
  expect(response.status()).toBe(200)
  return response.json() as Promise<Roster>
}
async function csrf(page: Page) {
  const response = await page.request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  return { 'X-CSRFToken': (await response.json() as { csrf_token: string }).csrf_token }
}

test.describe('Workspace membership inheritance — real isolated Django/PostgreSQL', () => {
  test.describe.configure({ mode: 'serial' })
  const contexts: BrowserContext[] = []
  const failures: string[] = []
  let owner: Page
  let createdId: string
  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext({ baseURL: test.info().project.use.baseURL })
    contexts.push(context)
    owner = await context.newPage()
    owner.on('pageerror', (error) => failures.push(error.name))
    owner.on('response', (response) => { if (response.status() >= 500) failures.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })
    await login(owner, 'inheritance_owner')
  })
  test.afterEach(() => { expect(failures).toEqual([]) })
  test.afterAll(async () => { for (const context of contexts) await context.close() })

  test('Owner chooses a source, preserves the draft during auth refresh, previews roles and creates an atomic role snapshot through React', async () => {
    test.setTimeout(90_000)
    const before = await roster(owner, sourceId)
    const sourceTasks = await owner.request.get(`${apiWorkspaces}${sourceId}/tasks/`)
    expect((await sourceTasks.json() as { count: number }).count).toBe(1)
    await owner.goto(workspaceList)
    const trigger = owner.getByRole('button', { name: 'Tạo không gian', exact: true })
    await trigger.focus()
    await owner.keyboard.press('Enter')
    const dialog = owner.getByRole('dialog', { name: 'Tạo không gian làm việc', exact: true })
    await expect(dialog).toBeVisible()
    await owner.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await expect(trigger).toBeFocused()
    await owner.keyboard.press('Enter')
    await dialog.getByLabel('Tên không gian', { exact: true }).fill(createdName)
    await dialog.getByLabel('Mô tả', { exact: true }).fill('Membership snapshot only; source work stays in its original Workspace.')
    await dialog.getByLabel('Tháng làm việc', { exact: true }).fill(new Date().toISOString().slice(0, 7))
    await dialog.getByLabel('Workspace nguồn', { exact: true }).selectOption(sourceId)
    await expect(dialog.getByText('inheritance_admin Kiểm thử', { exact: true })).toBeVisible()
    await expect(dialog.getByText('inheritance_member Kiểm thử', { exact: true })).toBeVisible()
    await expect(dialog.getByText('inheritance_viewer Kiểm thử', { exact: true })).toBeVisible()
    await expect(dialog.getByText('inheritance_revoked Kiểm thử', { exact: true })).toHaveCount(0)
    await expect(dialog.getByText('inheritance_inactive Kiểm thử', { exact: true })).toHaveCount(0)
    const preview = await owner.request.get(`${apiProfile}workspace-inheritance/?source_workspace_id=${sourceId}`)
    expect(preview.status()).toBe(200)
    const proposal = await preview.json() as { count: number; excluded_count: number; results: { profile_membership_id: string; display_name: string; role: string }[] }
    expect(proposal.count).toBe(3)
    expect(proposal.excluded_count).toBe(2)
    expect(proposal.results.map((row) => row.role).sort()).toEqual(['ADMIN', 'MEMBER', 'VIEWER'])
    const refresh = owner.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/me/' && response.request().method() === 'GET')
    await owner.evaluate(() => window.dispatchEvent(new Event('focus')))
    expect((await refresh).status()).toBe(200)
    await expect(dialog.getByLabel('Tên không gian', { exact: true })).toHaveValue(createdName)
    await expect(dialog.getByLabel('Workspace nguồn', { exact: true })).toHaveValue(sourceId)

    await owner.emulateMedia({ reducedMotion: 'reduce' })
    for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
      await owner.setViewportSize(size)
      expect(await owner.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
      expect((await new AxeBuilder({ page: owner }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
      if (size.width === 375 || size.width === 1440) {
        await dialog.getByRole('list', { name: 'Thành viên sẽ được kế thừa', exact: true }).scrollIntoViewIfNeeded()
        await owner.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `inheritance-preview-${size.width}.png`), fullPage: true })
      }
    }
    await owner.setViewportSize({ width: 1440, height: 1000 })
    await dialog.getByLabel('Workspace nguồn', { exact: true }).focus()
    await expect(dialog.getByLabel('Workspace nguồn', { exact: true })).toBeFocused()
    await owner.keyboard.press('Tab')
    expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true)
    const created = owner.waitForResponse((response) => new URL(response.url()).pathname === apiWorkspaces && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Tạo không gian', exact: true }).click()
    const response = await created
    expect(response.status()).toBe(201)
    expect(Boolean(response.request().headers()['x-csrftoken'])).toBe(true)
    expect(response.request().postDataJSON()).toMatchObject({ source_workspace_id: sourceId })
    const body = await response.json() as { id: string }
    createdId = body.id
    await expect(dialog).not.toBeVisible()
    await owner.goto(`${workspaceList}/${createdId}`)
    await expect(owner.getByRole('heading', { name: createdName, exact: true })).toBeVisible()
    const members = await roster(owner, createdId)
    expect(members.count).toBe(3)
    expect(members.results.map((row) => row.role).sort()).toEqual(['ADMIN', 'MEMBER', 'VIEWER'])
    await expect(owner.getByRole('list', { name: 'Thành viên Workspace', exact: true })).toContainText('inheritance_admin Kiểm thử')
    const targetTasks = await owner.request.get(`${apiWorkspaces}${createdId}/tasks/`)
    expect((await targetTasks.json() as { count: number }).count).toBe(0)
    expect(await roster(owner, sourceId)).toEqual(before)
    expect((await (await owner.request.get(`${apiWorkspaces}${sourceId}/tasks/`)).json() as { count: number }).count).toBe(1)
  })

  test('all inherited roles can access the new Workspace, revoked members remain denied, and IDOR/CSRF do not grant access', async ({ browser }) => {
    test.setTimeout(60_000)
    for (const actor of ['inheritance_admin', 'inheritance_member', 'inheritance_viewer', 'inheritance_revoked']) {
      const context = await browser.newContext({ baseURL: test.info().project.use.baseURL })
      contexts.push(context)
      const page = await context.newPage()
      page.on('pageerror', (error) => failures.push(error.name))
      page.on('response', (response) => { if (response.status() >= 500) failures.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })
      await login(page, actor)
      const response = await page.request.get(`${apiWorkspaces}${createdId}/`)
      expect(response.status()).toBe(actor === 'inheritance_revoked' ? 404 : 200)
      await page.goto(`${workspaceList}/${createdId}`)
      if (actor === 'inheritance_revoked') await expect(page.getByRole('heading', { name: createdName, exact: true })).toHaveCount(0)
      else await expect(page.getByRole('heading', { name: createdName, exact: true })).toBeVisible()
      if (actor === 'inheritance_viewer') await expect(page.getByRole('button', { name: 'Thêm thành viên', exact: true })).toHaveCount(0)
    }
    const rejected = { name: 'Rejected cross-tenant source', period: '2099-01-01', source_workspace_id: fixtureId('foreign_workspace') }
    expect((await owner.request.post(apiWorkspaces, { data: rejected })).status()).toBe(403)
    expect((await owner.request.post(apiWorkspaces, { headers: await csrf(owner), data: rejected })).status()).toBe(404)
    expect((await roster(owner, createdId)).count).toBe(3)
  })

  test('new recipient accepts through React and joins only the exact current-month Workspace without replay duplicates', async ({ browser }) => {
    test.setTimeout(90_000)
    await owner.goto(`/profiles/${profileId}/members`)
    await owner.getByRole('button', { name: 'Mời thành viên', exact: true }).click()
    const invitation = owner.getByRole('dialog', { name: 'Mời thành viên', exact: true })
    await invitation.getByLabel('Email người nhận', { exact: true }).fill(recipientEmail)
    await invitation.getByLabel('Vai trò tổ chức', { exact: true }).selectOption('MEMBER')
    const issued = owner.waitForResponse((response) => new URL(response.url()).pathname === `${apiProfile}invitations/` && response.request().method() === 'POST')
    await invitation.getByRole('button', { name: 'Gửi lời mời', exact: true }).click()
    expect((await issued).status()).toBe(201)
    expect((await roster(owner, createdId)).count).toBe(3)
    const secret = consumeInvitation()
    const context = await browser.newContext({ baseURL: test.info().project.use.baseURL })
    contexts.push(context)
    const page = await context.newPage()
    page.on('pageerror', (error) => failures.push(error.name))
    page.on('response', (response) => { if (response.status() >= 500) failures.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })
    await page.goto('/invitations/respond')
    await expect(page).toHaveURL('/login')
    await page.getByRole('link', { name: 'Đăng ký tài khoản', exact: true }).click()
    await page.getByLabel('Email', { exact: true }).fill(recipientEmail)
    await page.getByLabel('Tên đăng nhập', { exact: true }).fill(`inheritance_${runId.slice(0, 8)}`)
    await page.getByLabel('Tên (không bắt buộc)', { exact: true }).fill('Người mới kế thừa')
    await enterSecret(page, 'Mật khẩu', password)
    await enterSecret(page, 'Xác nhận mật khẩu', password)
    const registered = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/register/' && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click()
    expect((await registered).status()).toBe(201)
    await page.getByRole('link', { name: 'Về đăng nhập', exact: true }).click()
    await login(page, 'recipient', true)
    await expect(page).toHaveURL('/invitations/respond')
    await enterSecret(page, 'Mã lời mời', secret)
    const accepted = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/invitations/accept/' && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Chấp nhận lời mời', exact: true }).click()
    expect((await accepted).status()).toBe(200)
    await expect(page.getByRole('heading', { name: 'Đã tham gia tổ chức', exact: true })).toBeVisible()
    const workspaces = await page.request.get(apiWorkspaces)
    expect((await workspaces.json() as { results: { id: string }[] }).results.map((row) => row.id)).toEqual([createdId])
    for (const id of [sourceId, futureId]) expect((await page.request.get(`${apiWorkspaces}${id}/`)).status()).toBe(404)
    await page.goto(`${workspaceList}/${createdId}`)
    await expect(page.getByRole('heading', { name: createdName, exact: true })).toBeVisible()
    const joined = await roster(owner, createdId)
    expect(joined.count).toBe(4)
    expect(joined.results.find((member) => member.display_label === 'Người mới kế thừa')?.role).toBe('MEMBER')
    await page.goto('/invitations/respond')
    await enterSecret(page, 'Mã lời mời', secret)
    const replay = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/invitations/accept/' && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Chấp nhận lời mời', exact: true }).click()
    expect((await replay).status()).toBe(409)
    expect((await roster(owner, createdId)).count).toBe(4)
  })

  test('first Workspace explicitly confirms ordinary Profile members at MEMBER and preserves inherited Owner authority', async () => {
    await owner.goto(`/profiles/${firstProfileId}/workspaces`)
    await owner.getByRole('button', { name: 'Tạo không gian', exact: true }).click()
    const dialog = owner.getByRole('dialog', { name: 'Tạo không gian làm việc', exact: true })
    await dialog.getByLabel('Tên không gian', { exact: true }).fill('First confirmed Workspace')
    await dialog.getByLabel('Tháng làm việc', { exact: true }).fill(new Date().toISOString().slice(0, 7))
    const candidate = dialog.getByRole('checkbox', { name: /inheritance_member Kiểm thử/ })
    await expect(candidate).toBeVisible()
    await candidate.check()
    const path = `/api/v1/profiles/${firstProfileId}/workspaces/`
    const created = owner.waitForResponse((response) => new URL(response.url()).pathname === path && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Tạo không gian', exact: true }).click()
    const response = await created
    expect(response.status()).toBe(201)
    expect(response.request().postDataJSON()).toMatchObject({ initial_profile_membership_ids: [fixtureId('inheritance_first_candidate')] })
    const body = await response.json() as { id: string }
    const members = await roster(owner, body.id, firstProfileId)
    expect(members.count).toBe(1)
    expect(members.results[0]).toMatchObject({ profile_membership_id: fixtureId('inheritance_first_candidate'), role: 'MEMBER' })
    expect(members.results.some((member) => member.display_label === 'Chủ Kế thừa')).toBe(false)
  })
})

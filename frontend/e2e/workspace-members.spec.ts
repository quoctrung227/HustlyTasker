import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type BrowserContext, type Page } from '@playwright/test'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated Workspace members launcher.')
  return value
}
const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Invalid isolated fixture run identity.')
const recipientEmail = `acceptance.${runId}@example.test`
const recipientName = 'Người nhận Workspace'
const password = required('HT_FRONTEND_TEST_PASSWORD')
function fixtureId(label: string): string {
  const hash = createHash('sha1').update(Buffer.from(runId, 'hex')).update(label, 'utf8').digest()
  hash[6] = (hash.readUInt8(6) & 0x0f) | 0x50
  hash[8] = (hash.readUInt8(8) & 0x3f) | 0x80
  const hex = hash.subarray(0, 16).toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
const profileId = fixtureId('management_profile')
const workspaceId = fixtureId('management_workspace')
const archivedId = fixtureId('management_archived_workspace')
const otherProfileId = fixtureId('other_profile')
const foreignWorkspaceId = fixtureId('foreign_workspace')
const managerMembershipId = fixtureId('manager_active_membership')
const workspacePage = `/profiles/${profileId}/workspaces/${workspaceId}`
const taskList = `${workspacePage}/tasks`
const apiProfile = `/api/v1/profiles/${profileId}/`
const apiWorkspace = `${apiProfile}workspaces/${workspaceId}/`
const apiMembers = `${apiWorkspace}members/`
const apiTasks = `${apiWorkspace}tasks/`
const taskTitle = `Workspace access journey ${runId.slice(0, 8)}`

type TaskSnapshot = {
  id: string
  title: string
  status: string
  can_start: boolean
  can_submit: boolean
  active_assignment: { id: string; profile_membership_id: string | null } | null
}
type MemberSnapshot = { id: string; profile_membership_id: string; display_label: string; role: string; is_assignable: boolean }

/** Avoid credentials in fill diagnostics, CLI arguments, assertion values or URLs. */
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
    const value = execFileSync('docker', ['exec', container, 'python', '/workspace/scripts/frontend_integration.py', 'consume-test-mail', 'registered', 'invitation'], {
      encoding: 'utf8', timeout: 15_000, stdio: ['ignore', 'pipe', 'pipe'],
    }).trim()
    if (!/^[A-Za-z0-9_-]{43}$/.test(value)) throw new Error('Unexpected credential format.')
    return value
  } catch { throw new Error('Delivered isolated invitation could not be consumed.') }
}
async function login(page: Page, actor: 'owner' | 'recipient' | 'manager', existingForm = false) {
  if (!existingForm) await page.goto('/login')
  const email = actor === 'owner' ? required('HT_FRONTEND_TEST_OWNER_EMAIL') : actor === 'recipient' ? recipientEmail : `manager.${runId}@example.test`
  await page.getByLabel('Email', { exact: true }).fill(email)
  await enterSecret(page, 'Mật khẩu', password)
  const response = page.waitForResponse((result) => new URL(result.url()).pathname === '/api/auth/login/' && result.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await response).status()).toBe(200)
  await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
}
async function csrf(page: Page) {
  const response = await page.request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  const body = await response.json() as { csrf_token: string }
  return { 'X-CSRFToken': body.csrf_token }
}
async function openWorkspace(page: Page, id = workspaceId) {
  await page.goto(`/profiles/${profileId}/workspaces/${id}`)
  await expect(page.getByRole('heading', { name: 'Thành viên Workspace', level: 2, exact: true })).toBeVisible()
  await expect(page.getByRole('list', { name: 'Thành viên Workspace', exact: true })).toBeVisible()
}
function memberRow(page: Page, name = recipientName) {
  return page.getByRole('list', { name: 'Thành viên Workspace', exact: true }).getByRole('listitem').filter({ has: page.getByRole('heading', { name, exact: true }) })
}
async function currentTask(page: Page, id: string): Promise<TaskSnapshot> {
  const response = await page.request.get(`${apiTasks}${id}/`)
  expect(response.status()).toBe(200)
  return await response.json() as TaskSnapshot
}
async function refreshSession(page: Page) {
  const response = page.waitForResponse((result) => new URL(result.url()).pathname === '/api/auth/me/' && result.request().method() === 'GET')
  await page.evaluate(() => window.dispatchEvent(new Event('focus')))
  expect((await response).status()).toBe(200)
}
async function updateRole(page: Page, membershipId: string, role: 'MEMBER' | 'VIEWER') {
  await memberRow(page).getByRole('button', { name: 'Cập nhật quyền', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Cập nhật quyền Workspace', exact: true })
  await dialog.getByLabel('Vai trò trong Workspace', { exact: true }).selectOption(role)
  const response = page.waitForResponse((result) => new URL(result.url()).pathname === `${apiMembers}${membershipId}/` && result.request().method() === 'PATCH')
  await dialog.getByRole('button', { name: 'Xác nhận cập nhật quyền', exact: true }).click()
  const updated = await response
  expect(updated.status()).toBe(200)
  expect(updated.request().postDataJSON()).toEqual({ role })
  await expect(dialog).not.toBeVisible()
  await expect(memberRow(page)).toContainText(role === 'MEMBER' ? 'Editor (MEMBER)' : 'Chỉ xem (VIEWER)')
}

test.describe('Workspace access and members — real isolated Django/PostgreSQL', () => {
  test.describe.configure({ mode: 'serial' })
  // Three UI logins across this serial journey stay below the existing shared
  // login throttle. Only the launcher seeds baseline synthetic actors/Workspaces.
  const contexts: BrowserContext[] = []
  const failures: string[] = []
  let owner: Page
  let recipient: Page
  let manager: Page
  let recipientMembershipId: string
  let workspaceMembershipId: string
  let taskId: string
  let assignmentId: string
  test.beforeAll(async ({ browser }) => {
    for (let number = 0; number < 3; number += 1) {
      const context = await browser.newContext({ baseURL: test.info().project.use.baseURL })
      contexts.push(context)
      const page = await context.newPage()
      page.on('pageerror', (error) => failures.push(error.name))
      page.on('response', (response) => { if (response.status() >= 500) failures.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })
      if (number === 0) owner = page
      else if (number === 1) recipient = page
      else manager = page
    }
  })
  test.afterEach(() => { expect(failures).toEqual([]) })
  test.afterAll(async () => { for (const context of contexts) await context.close() })

  test('Profile invitation acceptance grants no Workspace; Owner then grants Editor access and assigns a Task through React', async () => {
    test.setTimeout(90_000)
    await login(owner, 'owner')
    await owner.goto(`/profiles/${profileId}`)
    await owner.getByRole('link', { name: 'Thành viên tổ chức', exact: true }).click()
    await owner.getByRole('button', { name: 'Mời thành viên', exact: true }).click()
    let dialog = owner.getByRole('dialog', { name: 'Mời thành viên', exact: true })
    await dialog.getByLabel('Email người nhận', { exact: true }).fill(recipientEmail)
    await dialog.getByLabel('Vai trò tổ chức', { exact: true }).selectOption('MEMBER')
    const invited = owner.waitForResponse((result) => new URL(result.url()).pathname === `${apiProfile}invitations/` && result.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Gửi lời mời', exact: true }).click()
    expect((await invited).status()).toBe(201)
    await expect(dialog).not.toBeVisible()
    const secret = consumeInvitation()

    // This recipient has no seeded account or membership: registration and
    // explicit consent occur through the real React forms and existing APIs.
    await recipient.goto('/invitations/respond')
    await expect(recipient).toHaveURL('/login')
    await recipient.getByRole('link', { name: 'Đăng ký tài khoản', exact: true }).click()
    await recipient.getByLabel('Email', { exact: true }).fill(recipientEmail)
    await recipient.getByLabel('Tên đăng nhập', { exact: true }).fill(`workspace_${runId.slice(0, 8)}`)
    await recipient.getByLabel('Tên (không bắt buộc)', { exact: true }).fill(recipientName)
    await enterSecret(recipient, 'Mật khẩu', password)
    await enterSecret(recipient, 'Xác nhận mật khẩu', password)
    const registered = recipient.waitForResponse((result) => new URL(result.url()).pathname === '/api/auth/register/' && result.request().method() === 'POST')
    await recipient.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click()
    expect((await registered).status()).toBe(201)
    await recipient.getByRole('link', { name: 'Về đăng nhập', exact: true }).click()
    await login(recipient, 'recipient', true)
    await expect(recipient).toHaveURL('/invitations/respond')
    await enterSecret(recipient, 'Mã lời mời', secret)
    const accepted = recipient.waitForResponse((result) => new URL(result.url()).pathname === '/api/v1/invitations/accept/' && result.request().method() === 'POST')
    await recipient.getByRole('button', { name: 'Chấp nhận lời mời', exact: true }).click()
    const acceptedResponse = await accepted
    expect(acceptedResponse.status()).toBe(200)
    const acceptedBody = await acceptedResponse.json() as { profile_id: string; membership_id: string }
    expect(acceptedBody.profile_id).toBe(profileId)
    recipientMembershipId = acceptedBody.membership_id
    expect(recipient.url().includes(secret)).toBe(false)
    await expect(recipient.getByRole('heading', { name: 'Đã tham gia tổ chức', exact: true })).toBeVisible()
    const before = await recipient.request.get(`${apiProfile}workspaces/`)
    expect((await before.json() as { count: number }).count).toBe(0)
    expect((await recipient.request.get(apiWorkspace)).status()).toBe(404)

    await openWorkspace(owner)
    await owner.getByRole('button', { name: 'Thêm thành viên', exact: true }).click()
    dialog = owner.getByRole('dialog', { name: 'Thêm thành viên Workspace', exact: true })
    await expect(dialog.getByLabel('Chọn thành viên tổ chức', { exact: true }).getByRole('option', { name: new RegExp(recipientName) })).toHaveCount(1)
    await dialog.getByLabel('Chọn thành viên tổ chức', { exact: true }).selectOption(recipientMembershipId)
    await dialog.getByLabel('Vai trò trong Workspace', { exact: true }).selectOption('MEMBER')
    const granted = owner.waitForResponse((result) => new URL(result.url()).pathname === apiMembers && result.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Cấp quyền truy cập', exact: true }).click()
    const grant = await granted
    expect(grant.status()).toBe(201)
    expect(grant.request().postDataJSON()).toEqual({ target_profile_membership_id: recipientMembershipId, role: 'MEMBER' })
    expect(Boolean(grant.request().headers()['x-csrftoken'])).toBe(true)
    workspaceMembershipId = (await grant.json() as MemberSnapshot).id
    await expect(dialog).not.toBeVisible()
    await expect(memberRow(owner)).toContainText('Editor (MEMBER)')

    const visible = await recipient.request.get(`${apiProfile}workspaces/`)
    expect((await visible.json() as { results: { id: string }[] }).results.map((row) => row.id)).toEqual([workspaceId])
    await recipient.goto(`/profiles/${profileId}/workspaces`)
    await expect(recipient.getByRole('heading', { name: 'Team Workspace Integration', exact: true })).toBeVisible()
    await expect(recipient.getByRole('heading', { name: 'Archived Team Integration', exact: true })).toHaveCount(0)

    await owner.goto(taskList)
    await owner.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
    dialog = owner.getByRole('dialog', { name: 'Tạo công việc', exact: true })
    await dialog.getByLabel('Tên công việc', { exact: true }).fill(taskTitle)
    const created = owner.waitForResponse((result) => new URL(result.url()).pathname === apiTasks && result.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
    const createdResponse = await created
    expect(createdResponse.status()).toBe(201)
    taskId = (await createdResponse.json() as TaskSnapshot).id
    await owner.goto(`${taskList}/${taskId}`)
    await owner.getByRole('button', { name: 'Phân công', exact: true }).click()
    dialog = owner.getByRole('dialog', { name: 'Phân công công việc', exact: true })
    await expect(dialog.getByLabel('Thành viên', { exact: true }).getByRole('option', { name: new RegExp(recipientName) })).toHaveCount(1)
    await dialog.getByLabel('Thành viên', { exact: true }).selectOption(recipientMembershipId)
    await dialog.getByRole('button', { name: 'Xác nhận phân công', exact: true }).click()
    await expect(dialog).not.toBeVisible()
    const assigned = await currentTask(owner, taskId)
    expect(assigned.status).toBe('ASSIGNED')
    expect(assigned.active_assignment?.profile_membership_id).toBe(recipientMembershipId)
    if (!assigned.active_assignment) throw new Error('Expected the confirmed isolated Task assignment.')
    assignmentId = assigned.active_assignment.id

    await recipient.goto(`${taskList}/${taskId}`)
    await expect(recipient.getByRole('heading', { name: taskTitle, exact: true })).toBeVisible()
    const started = recipient.waitForResponse((result) => new URL(result.url()).pathname === `${apiTasks}${taskId}/start/` && result.request().method() === 'POST')
    await recipient.getByRole('button', { name: 'Bắt đầu công việc', exact: true }).click()
    expect((await started).status()).toBe(200)
    expect(await currentTask(recipient, taskId)).toMatchObject({ status: 'WORKING', can_submit: true })
  })

  test('Workspace Admin changes Editor to Viewer and back without changing Task status or assignment', async () => {
    test.setTimeout(60_000)
    await login(manager, 'manager')
    await openWorkspace(manager)
    expect((await manager.request.get(`${apiProfile}members/`)).status()).toBe(403)
    const candidates = await manager.request.get(`${apiWorkspace}member-candidates/`)
    expect(candidates.status()).toBe(200)
    expect((await candidates.json() as { count: number }).count).toBe(0)
    await memberRow(manager).getByRole('button', { name: 'Cập nhật quyền', exact: true }).click()
    const dialog = manager.getByRole('dialog', { name: 'Cập nhật quyền Workspace', exact: true })
    expect(await dialog.getByLabel('Vai trò trong Workspace', { exact: true }).getByRole('option').evaluateAll((options) => options.map((option) => (option as HTMLOptionElement).value))).toEqual(['', 'MEMBER', 'VIEWER'])
    await dialog.getByLabel('Vai trò trong Workspace', { exact: true }).selectOption('VIEWER')
    const changed = manager.waitForResponse((result) => new URL(result.url()).pathname === `${apiMembers}${workspaceMembershipId}/` && result.request().method() === 'PATCH')
    await dialog.getByRole('button', { name: 'Xác nhận cập nhật quyền', exact: true }).click()
    expect((await changed).status()).toBe(200)
    await expect(dialog).not.toBeVisible()
    await refreshSession(recipient)
    await expect(recipient.getByRole('button', { name: 'Nộp sản phẩm', exact: true })).toHaveCount(0)
    expect(await currentTask(recipient, taskId)).toMatchObject({ status: 'WORKING', can_submit: false,
      active_assignment: { id: assignmentId, profile_membership_id: recipientMembershipId } })
    expect((await recipient.request.post(`${apiTasks}${taskId}/deliverables/`, { headers: await csrf(recipient), data: { file_url: 'https://example.test/denied-viewer' } })).status()).toBe(403)
    await recipient.goto(workspacePage)
    await expect(recipient.getByRole('heading', { name: 'Team Workspace Integration', exact: true })).toBeVisible()
    await expect(recipient.getByRole('button', { name: 'Thêm thành viên', exact: true })).toHaveCount(0)
    await expect(recipient.getByRole('list', { name: 'Thành viên Workspace', exact: true })).toHaveCount(0)

    await updateRole(manager, workspaceMembershipId, 'MEMBER')
    await recipient.goto(`${taskList}/${taskId}`)
    await expect(recipient.getByRole('button', { name: 'Nộp sản phẩm', exact: true })).toBeVisible()
    expect(await currentTask(recipient, taskId)).toMatchObject({ status: 'WORKING', can_submit: true,
      active_assignment: { id: assignmentId, profile_membership_id: recipientMembershipId } })
    const eligible = await owner.request.get(apiMembers)
    expect((await eligible.json() as { results: MemberSnapshot[] }).results.find((row) => row.profile_membership_id === recipientMembershipId)).toMatchObject({ is_assignable: true, role: 'MEMBER' })
  })

  test('role ceilings, duplicate/CSRF/cross-tenant denials and confirmed revoke preserve the Task while removing stale recipient access', async () => {
    test.setTimeout(60_000)
    // These direct API calls intentionally test denials/read-back, not UI writes.
    expect((await owner.request.post(apiMembers, { data: { target_profile_membership_id: recipientMembershipId, role: 'MEMBER' } })).status()).toBe(403)
    expect((await owner.request.post(apiMembers, { headers: await csrf(owner), data: { target_profile_membership_id: recipientMembershipId, role: 'MEMBER' } })).status()).toBe(409)
    expect((await manager.request.patch(`${apiMembers}${managerMembershipId}/`, { headers: await csrf(manager), data: { role: 'VIEWER' } })).status()).toBe(403)
    expect((await manager.request.patch(`${apiMembers}${workspaceMembershipId}/`, { headers: await csrf(manager), data: { role: 'ADMIN' } })).status()).toBe(403)
    expect((await manager.request.get(`/api/v1/profiles/${otherProfileId}/workspaces/${foreignWorkspaceId}/member-candidates/`)).status()).toBe(404)
    const foreign = await owner.request.get(`/api/v1/profiles/${otherProfileId}/members/`)
    expect(foreign.status()).toBe(200)
    const foreignRows = await foreign.json() as { results: { id: string }[] }
    const foreignMembershipId = foreignRows.results[0]?.id
    if (!foreignMembershipId) throw new Error('Expected an isolated foreign Profile membership.')
    expect((await owner.request.post(apiMembers, { headers: await csrf(owner), data: { target_profile_membership_id: foreignMembershipId, role: 'MEMBER' } })).status()).toBe(400)
    await expect(memberRow(manager, 'Quản lý Kiểm thử').getByRole('button', { name: 'Cập nhật quyền', exact: true })).toHaveCount(0)
    await expect(memberRow(manager, 'Quản lý Kiểm thử').getByRole('button', { name: 'Thu hồi quyền', exact: true })).toHaveCount(0)

    await memberRow(manager).getByRole('button', { name: 'Thu hồi quyền', exact: true }).click()
    const dialog = manager.getByRole('dialog', { name: 'Thu hồi quyền Workspace', exact: true })
    const removed = manager.waitForResponse((result) => new URL(result.url()).pathname === `${apiMembers}${workspaceMembershipId}/` && result.request().method() === 'DELETE')
    await dialog.getByRole('button', { name: 'Xác nhận thu hồi quyền', exact: true }).click()
    expect((await removed).status()).toBe(204)
    await expect(dialog).not.toBeVisible()
    await expect(memberRow(manager)).toHaveCount(0)
    await refreshSession(recipient)
    await expect(recipient.getByRole('heading', { name: taskTitle, exact: true })).toHaveCount(0)
    await expect(recipient.getByRole('heading', { name: 'Nội dung không khả dụng', level: 1, exact: true })).toBeVisible()
    expect((await recipient.request.get(apiWorkspace)).status()).toBe(404)
    expect((await recipient.request.get(`${apiTasks}${taskId}/`)).status()).toBe(404)
    expect((await recipient.request.get(`${apiWorkspace}member-candidates/`)).status()).toBe(404)
    const visible = await recipient.request.get(`${apiProfile}workspaces/`)
    expect((await visible.json() as { count: number }).count).toBe(0)
    expect(await currentTask(owner, taskId)).toMatchObject({ id: taskId, title: taskTitle, status: 'WORKING',
      active_assignment: { id: assignmentId, profile_membership_id: recipientMembershipId } })
    const refreshed = await manager.request.get(`${apiWorkspace}member-candidates/`)
    expect((await refreshed.json() as { results: { profile_membership_id: string }[] }).results.map((row) => row.profile_membership_id)).toContain(recipientMembershipId)

    await openWorkspace(owner, archivedId)
    await expect(owner.getByRole('button', { name: 'Thêm thành viên', exact: true })).toHaveCount(0)
    await expect(owner.getByRole('button', { name: 'Cập nhật quyền', exact: true })).toHaveCount(0)
    await expect(owner.getByRole('button', { name: 'Thu hồi quyền', exact: true })).toHaveCount(0)
    const archived = await owner.request.get(`${apiProfile}workspaces/${archivedId}/member-candidates/`)
    expect((await archived.json() as { count: number }).count).toBe(0)
  })

  test('grant draft remains mounted during real auth refresh and is keyboard accessible at four viewports', async () => {
    test.setTimeout(90_000)
    await owner.emulateMedia({ reducedMotion: 'reduce' })
    await openWorkspace(owner)
    await owner.getByRole('button', { name: 'Thêm thành viên', exact: true }).click()
    const dialog = owner.getByRole('dialog', { name: 'Thêm thành viên Workspace', exact: true })
    await dialog.getByLabel('Chọn thành viên tổ chức', { exact: true }).selectOption(recipientMembershipId)
    await dialog.getByLabel('Vai trò trong Workspace', { exact: true }).selectOption('ADMIN')
    const original = await dialog.elementHandle()
    if (!original) throw new Error('Expected a mounted Workspace access form.')
    let submitted = 0
    owner.on('request', (request) => { if (request.method() === 'POST' && new URL(request.url()).pathname === apiMembers) submitted += 1 })
    for (const event of ['focus', 'visibilitychange']) {
      const response = owner.waitForResponse((result) => new URL(result.url()).pathname === '/api/auth/me/' && result.request().method() === 'GET')
      await owner.evaluate((kind) => { if (kind === 'focus') window.dispatchEvent(new Event(kind)); else document.dispatchEvent(new Event(kind)) }, event)
      expect((await response).status()).toBe(200)
      expect(await original.evaluate((element) => element.isConnected && element === document.querySelector('dialog[open]'))).toBe(true)
      await expect(dialog.getByLabel('Chọn thành viên tổ chức', { exact: true })).toHaveValue(recipientMembershipId)
      await expect(dialog.getByLabel('Vai trò trong Workspace', { exact: true })).toHaveValue('ADMIN')
    }
    for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
      await owner.setViewportSize(size)
      await dialog.getByLabel('Chọn thành viên tổ chức', { exact: true }).focus()
      await expect(dialog.getByLabel('Chọn thành viên tổ chức', { exact: true })).toBeFocused()
      await owner.keyboard.press('Tab')
      await expect(dialog.getByLabel('Vai trò trong Workspace', { exact: true })).toBeFocused()
      expect(await owner.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      const result = await new AxeBuilder({ page: owner }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
      expect(result.violations.map((violation) => violation.id)).toEqual([])
      await owner.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `workspace-access-${size.width}.png`), fullPage: false, animations: 'disabled', caret: 'hide', timeout: 5000 })
    }
    expect(submitted).toBe(0)
    await owner.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await expect(owner.getByRole('button', { name: 'Thêm thành viên', exact: true })).toBeFocused()
    await owner.goto(taskList)
    await owner.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
    const taskDialog = owner.getByRole('dialog', { name: 'Tạo công việc', exact: true })
    await taskDialog.getByLabel('Tên công việc', { exact: true }).fill('Unsent Workspace membership regression task')
    await refreshSession(owner)
    await expect(taskDialog.getByLabel('Tên công việc', { exact: true })).toHaveValue('Unsent Workspace membership regression task')
    await owner.keyboard.press('Escape')
    expect(await owner.evaluate(() => Object.keys(localStorage))).toEqual([])
    expect(await recipient.evaluate(() => Object.keys(localStorage))).toEqual([])
  })
})

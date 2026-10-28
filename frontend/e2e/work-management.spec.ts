import { createHash } from 'node:crypto'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use scripts/test-frontend-integration.ps1 with owned isolated fixtures.')
  return value
}

const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Invalid isolated fixture run identity.')

// These deterministic IDs identify synthetic rows inside the fresh owned DB.
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
const foreignProfileId = fixtureId('other_profile')
const foreignWorkspaceId = fixtureId('foreign_workspace')
const rootId = fixtureId('task_root')
const editorMembershipId = fixtureId('editor_profile_membership')
const workspaceList = `/profiles/${profileId}/workspaces`
const workspacePage = `${workspaceList}/${workspaceId}`
const taskPage = `${workspacePage}/tasks`
const apiWorkspaces = `/api/v1/profiles/${profileId}/workspaces/`
const apiWorkspace = `${apiWorkspaces}${workspaceId}/`
const apiTasks = `${apiWorkspace}tasks/`

type TaskResponse = {
  id: string
  title: string
  parent_id: string | null
  priority: string
  deadline: string | null
  status: string
  can_start: boolean
  active_assignment: { profile_membership_id: string | null } | null
}

async function csrf(request: APIRequestContext): Promise<string> {
  const response = await request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  const data = await response.json() as { csrf_token: string }
  expect(typeof data.csrf_token).toBe('string')
  return data.csrf_token
}

async function loginUI(page: Page, role: 'owner' | 'manager' | 'editor' | 'viewer'): Promise<void> {
  await page.goto('/login')
  const email = role === 'owner' ? required('HT_FRONTEND_TEST_OWNER_EMAIL') : `${role}.${runId}@example.test`
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(required('HT_FRONTEND_TEST_PASSWORD'))
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  await expect.poll(() => new URL(page.url()).pathname).toBe('/dashboard')
}

async function getTask(request: APIRequestContext, id: string): Promise<TaskResponse> {
  const response = await request.get(`${apiTasks}${id}/`)
  expect(response.status()).toBe(200)
  return response.json() as Promise<TaskResponse>
}

test.describe('Real work-management UI — isolated Django/PostgreSQL, no API mocks', () => {
  const browserFailures = new WeakMap<Page, string[]>()
  test.beforeEach(({ page }) => {
    const failures: string[] = []
    browserFailures.set(page, failures)
    page.on('pageerror', (error) => failures.push(error.name))
    page.on('response', (response) => {
      if (response.status() >= 500) failures.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`)
    })
  })
  test.afterEach(({ page }) => {
    expect(browserFailures.get(page)).toEqual([])
  })

  test('Owner creates, edits, archives and restores a Workspace through real forms', async ({ page }) => {
    await loginUI(page, 'owner')
    await page.goto(workspaceList)
    await page.getByRole('button', { name: 'Tạo không gian', exact: true }).click()
    let dialog = page.getByRole('dialog', { name: 'Tạo không gian làm việc', exact: true })
    await expect(dialog).toBeVisible()
    await dialog.getByLabel('Tên không gian', { exact: true }).fill('Created Workspace Integration')
    await dialog.getByLabel('Mô tả', { exact: true }).fill('Created through the real frontend in the disposable database.')
    await dialog.getByLabel('Tháng làm việc', { exact: true }).fill('2027-03')
    const createdResponse = page.waitForResponse((response) => new URL(response.url()).pathname === apiWorkspaces && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Tạo không gian', exact: true }).click()
    const created = await createdResponse
    expect(created.status()).toBe(201)
    const workspace = await created.json() as { id: string; period: string }
    expect(workspace.period).toBe('2027-03-01')
    await expect(dialog).not.toBeVisible()
    await page.goto(`${workspaceList}/${workspace.id}`)
    await expect(page.getByRole('heading', { name: 'Created Workspace Integration', exact: true })).toBeVisible()

    await page.getByRole('button', { name: 'Chỉnh sửa không gian', exact: true }).click()
    dialog = page.getByRole('dialog', { name: 'Chỉnh sửa không gian', exact: true })
    await dialog.getByLabel('Tên không gian', { exact: true }).fill('Updated Workspace Integration')
    await dialog.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Updated Workspace Integration', exact: true })).toBeVisible()

    await page.getByRole('button', { name: 'Lưu trữ không gian', exact: true }).click()
    dialog = page.getByRole('dialog', { name: 'Lưu trữ không gian', exact: true })
    await dialog.getByRole('button', { name: 'Xác nhận lưu trữ', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Khôi phục không gian', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Chỉnh sửa không gian', exact: true })).toHaveCount(0)
    let response = await page.request.get(`${apiWorkspaces}${workspace.id}/`)
    expect((await response.json() as { status: string }).status).toBe('ARCHIVED')

    await page.getByRole('button', { name: 'Khôi phục không gian', exact: true }).click()
    dialog = page.getByRole('dialog', { name: 'Khôi phục không gian', exact: true })
    await dialog.getByRole('button', { name: 'Xác nhận khôi phục', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Lưu trữ không gian', exact: true })).toBeVisible()
    response = await page.request.get(`${apiWorkspaces}${workspace.id}/`)
    expect((await response.json() as { status: string }).status).toBe('ACTIVE')
  })

  test('Workspace manager creates, edits, assigns and adds Subtasks without bypassing workflow', async ({ page }) => {
    await loginUI(page, 'manager')
    await page.goto(workspacePage)
    await expect(page.getByRole('heading', { name: 'Team Workspace Integration', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Lưu trữ không gian', exact: true })).toHaveCount(0)
    await page.getByRole('button', { name: 'Chỉnh sửa không gian', exact: true }).click()
    const workspaceDialog = page.getByRole('dialog', { name: 'Chỉnh sửa không gian', exact: true })
    await workspaceDialog.getByLabel('Mô tả', { exact: true }).fill('Metadata edited by an authorized Workspace manager.')
    await workspaceDialog.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click()
    await expect(workspaceDialog).not.toBeVisible()
    await page.goto(workspaceList)
    await expect(page.getByRole('button', { name: 'Tạo không gian', exact: true })).toHaveCount(0)
    await page.goto(taskPage)
    await expect(page.getByRole('heading', { name: 'Công việc', exact: true })).toBeVisible()
    expect((await page.request.post(apiTasks, { data: { title: 'Rejected manager request without CSRF' } })).status()).toBe(403)
    await page.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
    let dialog = page.getByRole('dialog', { name: 'Tạo công việc', exact: true })
    await dialog.getByLabel('Tên công việc', { exact: true }).fill('Created Task Integration')
    await dialog.getByLabel('Mô tả', { exact: true }).fill('Task written only inside the owned test database.')
    await dialog.getByLabel('Ưu tiên', { exact: true }).selectOption('HIGH')
    await dialog.getByLabel('Thời hạn', { exact: true }).fill('2027-03-05T09:30')
    const expectedDeadline = await page.evaluate(() => new Date('2027-03-05T09:30').toISOString())
    const createdResponse = page.waitForResponse((response) => new URL(response.url()).pathname === apiTasks && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
    const response = await createdResponse
    expect(response.status()).toBe(201)
    const task = await response.json() as TaskResponse
    expect(task.priority).toBe('HIGH')
    expect(new Date(task.deadline ?? '').toISOString()).toBe(expectedDeadline)
    expect(task.status).toBe('PENDING')
    await expect(dialog).not.toBeVisible()
    await page.goto(`${taskPage}/${task.id}`)
    await expect(page.getByRole('heading', { name: 'Created Task Integration', exact: true })).toBeVisible()

    await page.getByRole('button', { name: 'Chỉnh sửa công việc', exact: true }).click()
    dialog = page.getByRole('dialog', { name: 'Chỉnh sửa công việc', exact: true })
    await dialog.getByLabel('Tên công việc', { exact: true }).fill('Updated Task Integration')
    await dialog.getByLabel('Ưu tiên', { exact: true }).selectOption('URGENT')
    await dialog.getByLabel('Thời hạn', { exact: true }).fill('')
    await dialog.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Updated Task Integration', exact: true })).toBeVisible()
    const updated = await getTask(page.request, task.id)
    expect(updated.priority).toBe('URGENT')
    expect(updated.deadline).toBeNull()
    expect(updated.status).toBe('PENDING')

    await page.getByRole('button', { name: 'Phân công', exact: true }).click()
    dialog = page.getByRole('dialog', { name: 'Phân công công việc', exact: true })
    const rosterResponse = await page.request.get(`${apiWorkspace}members/`)
    expect(rosterResponse.status()).toBe(200)
    const roster = await rosterResponse.json() as { results: { profile_membership_id: string; display_label: string; is_assignable: boolean; role: string }[] }
    const candidate = roster.results.find((member) => member.profile_membership_id === editorMembershipId)
    expect(candidate).toMatchObject({ display_label: 'Nhân viên Kiểm thử', is_assignable: true })
    expect(roster.results.filter((member) => member.role !== 'MEMBER').every((member) => !member.is_assignable)).toBe(true)
    expect(roster.results.some((member) => member.display_label === 'Chủ Tổ chức' && !member.is_assignable)).toBe(true)
    for (const member of roster.results) {
      for (const field of ['email', 'user_id', 'password', 'phone']) expect(Object.keys(member)).not.toContain(field)
      expect(member.display_label).not.toContain('@example.test')
    }
    await expect(dialog.getByLabel('Thành viên', { exact: true }).getByRole('option', { name: /Nhân viên Kiểm thử/ })).toHaveCount(1)
    await dialog.getByLabel('Thành viên', { exact: true }).selectOption(editorMembershipId)
    await dialog.getByRole('button', { name: 'Xác nhận phân công', exact: true }).click()
    await expect(dialog).not.toBeVisible()
    const assigned = await getTask(page.request, task.id)
    expect(assigned.status).toBe('ASSIGNED')
    expect(assigned.active_assignment?.profile_membership_id).toBe(editorMembershipId)

    await page.getByRole('button', { name: 'Tạo công việc con', exact: true }).click()
    dialog = page.getByRole('dialog', { name: 'Tạo công việc con', exact: true })
    await dialog.getByLabel('Tên công việc', { exact: true }).fill('Created Subtask Integration')
    const childResponse = page.waitForResponse((result) => new URL(result.url()).pathname === apiTasks && result.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Tạo công việc con', exact: true }).click()
    const child = await childResponse
    expect(child.status()).toBe(201)
    const childTask = await child.json() as TaskResponse
    expect(childTask.parent_id).toBe(task.id)
    expect(childTask.status).toBe('PENDING')
    expect((await getTask(page.request, task.id)).status).toBe('ASSIGNED')
    await expect(page.getByRole('button', { name: 'Bắt đầu công việc', exact: true })).toHaveCount(0)
  })

  test('real Task filtering, pagination and hierarchy enforce existing backend contracts', async ({ page }) => {
    await loginUI(page, 'manager')
    await page.goto(taskPage)
    await expect(page.getByRole('heading', { name: 'Công việc', exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Trang sau', exact: true }).click()
    await expect(page.getByText('Trang 2 / 2', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Trang trước', exact: true }).click()
    await expect(page.getByText('Trang 1 / 2', { exact: true })).toBeVisible()
    await page.getByLabel('Mức ưu tiên', { exact: true }).selectOption('HIGH')
    await page.getByLabel('Sắp xếp', { exact: true }).selectOption('-priority')
    const filteredResponse = page.waitForResponse((response) => {
      const url = new URL(response.url())
      return url.pathname === apiTasks && url.searchParams.get('priority') === 'HIGH' && response.request().method() === 'GET'
    })
    await page.getByRole('button', { name: 'Áp dụng bộ lọc', exact: true }).click()
    const filtered = await filteredResponse
    expect(filtered.status()).toBe(200)
    const filteredPage = await filtered.json() as { count: number; results: TaskResponse[] }
    expect(filteredPage.count).toBeGreaterThan(0)
    expect(filteredPage.results.every((task) => task.priority === 'HIGH')).toBe(true)
    await page.getByLabel('Tìm trong trang', { exact: true }).fill('Integration task 02')
    await expect(page.getByRole('link', { name: 'Integration task 02', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Integration task 06', exact: true })).toHaveCount(0)
    await page.getByLabel('Tìm trong trang', { exact: true }).fill('')
    await page.getByRole('button', { name: 'Xóa bộ lọc', exact: true }).click()
    await page.goto(`${taskPage}/${rootId}`)
    await expect(page.getByRole('heading', { name: 'Hierarchy root Integration', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Hierarchy child Integration', exact: true })).toBeVisible()
    const token = await csrf(page.request)
    const headers = { 'X-CSRFToken': token }
    const reject = async (id: string, parent: string) => {
      const response = await page.request.patch(`${apiTasks}${id}/`, { headers, data: { parent_id: parent } })
      expect([400, 404, 409]).toContain(response.status())
    }
    await reject(rootId, rootId)
    await reject(rootId, fixtureId('task_child'))
    await reject(rootId, fixtureId('task_foreign'))
    const tooDeep = await page.request.post(apiTasks, {
      headers, data: { title: 'Rejected depth four Integration', parent_id: fixtureId('task_depth_three') },
    })
    expect([400, 409]).toContain(tooDeep.status())
    for (const data of [{ deadline: 'invalid-date' }, { deadline: '9999-12-31T23:59:59-23:59' }, { priority: 'UNAPPROVED' }]) {
      expect((await page.request.patch(`${apiTasks}${rootId}/`, { headers, data })).status()).toBe(400)
    }
    expect((await getTask(page.request, rootId)).parent_id).toBeNull()
  })

  test('Viewer sees permitted Tasks while write controls, CSRF and cross-tenant access stay closed', async ({ page }) => {
    expect((await page.request.get(apiTasks)).status()).toBe(403)
    await loginUI(page, 'viewer')
    await page.goto(workspaceList)
    await expect(page.getByRole('button', { name: 'Tạo không gian', exact: true })).toHaveCount(0)
    await page.goto(taskPage)
    await expect(page.getByRole('heading', { name: 'Công việc', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Tạo công việc', exact: true })).toHaveCount(0)
    await page.goto(`${taskPage}/${rootId}`)
    await expect(page.getByRole('heading', { name: 'Hierarchy root Integration', exact: true })).toBeVisible()
    for (const name of ['Chỉnh sửa công việc', 'Phân công', 'Tạo công việc con', 'Bắt đầu công việc']) {
      await expect(page.getByRole('button', { name, exact: true })).toHaveCount(0)
    }
    expect((await page.request.post(apiTasks, { data: { title: 'Rejected anonymous-CSRF write' } })).status()).toBe(403)
    const token = await csrf(page.request)
    const headers = { 'X-CSRFToken': token }
    expect((await page.request.post(apiTasks, { headers, data: { title: 'Rejected viewer write' } })).status()).toBe(403)
    expect((await page.request.patch(`${apiTasks}${rootId}/`, { headers, data: { priority: 'URGENT' } })).status()).toBe(403)
    const crossTenant = `/api/v1/profiles/${foreignProfileId}/workspaces/${foreignWorkspaceId}/tasks/${fixtureId('task_foreign')}/`
    expect((await page.request.get(crossTenant)).status()).toBe(404)
    expect((await page.request.get(`${apiTasks}${fixtureId('task_foreign')}/`)).status()).toBe(404)
    await page.goto(`${workspacePage}/tasks/${fixtureId('task_foreign')}`)
    await expect(page.getByRole('heading', { name: 'Nội dung không khả dụng', exact: true })).toBeVisible()
    await expect(page.getByText('Foreign task Integration', { exact: true })).toHaveCount(0)
    await page.goto(`${workspaceList}/${archivedId}/tasks`)
    await expect(page.getByRole('heading', { name: 'Công việc', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Tạo công việc', exact: true })).toHaveCount(0)
    expect((await page.request.get('/api/auth/me/')).status()).toBe(200)
  })

  test('Editor starts only its current assignment through the real authorized CSRF workflow', async ({ page }) => {
    test.setTimeout(60_000)
    await loginUI(page, 'editor')
    await page.goto(`${taskPage}/${fixtureId('task_assigned')}`)
    await expect(page.getByRole('heading', { name: 'Assigned editor Integration', exact: true })).toBeVisible()
    for (const name of ['Chỉnh sửa công việc', 'Phân công', 'Tạo công việc con']) {
      await expect(page.getByRole('button', { name, exact: true })).toHaveCount(0)
    }
    const token = await csrf(page.request)
    const headers = { 'X-CSRFToken': token }
    expect((await page.request.post(apiTasks, { headers, data: { title: 'Rejected Editor create' } })).status()).toBe(403)
    expect((await page.request.patch(`${apiTasks}${rootId}/`, { headers, data: { title: 'Rejected Editor edit' } })).status()).toBe(403)
    expect((await page.request.post(`${apiTasks}${rootId}/assign/`, { headers, data: { target_profile_membership_id: editorMembershipId } })).status()).toBe(403)
    const assignedId = fixtureId('task_assigned')
    expect((await getTask(page.request, assignedId)).can_start).toBe(true)
    expect((await page.request.get(`${apiWorkspace}members/`)).status()).toBe(403)
    expect((await page.request.post(`${apiTasks}${assignedId}/start/`, { data: {} })).status()).toBe(403)
    await page.goto(`${taskPage}/${fixtureId('task_other_assigned')}`)
    await expect(page.getByRole('heading', { name: 'Other editor assignment Integration' })).toBeVisible()
    expect((await getTask(page.request, fixtureId('task_other_assigned'))).can_start).toBe(false)
    await expect(page.getByRole('button', { name: 'Bắt đầu công việc', exact: true })).toHaveCount(0)
    expect((await page.request.post(`${apiTasks}${fixtureId('task_other_assigned')}/start/`, { headers, data: {} })).status()).toBe(403)
    await page.goto(`${taskPage}/${assignedId}`)
    await expect(page.getByRole('button', { name: 'Bắt đầu công việc', exact: true })).toBeVisible()
    for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
      await page.setViewportSize(size)
      await page.getByRole('button', { name: 'Bắt đầu công việc', exact: true }).focus()
      await expect(page.getByRole('button', { name: 'Bắt đầu công việc', exact: true })).toBeFocused()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
      expect(a11y.violations.map((violation) => violation.id)).toEqual([])
      await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `task-start-${size.width}.png`), fullPage: true })
    }
    const startedResponse = page.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${assignedId}/start/` && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Bắt đầu công việc', exact: true }).press('Enter')
    expect((await startedResponse).status()).toBe(200)
    await expect(page.getByRole('button', { name: 'Bắt đầu công việc', exact: true })).toHaveCount(0)
    const started = await getTask(page.request, assignedId)
    expect(started.status).toBe('WORKING')
    expect(started.can_start).toBe(false)
    expect((await page.request.post(`${apiTasks}${assignedId}/start/`, { headers, data: {} })).status()).toBe(409)
  })

  test('archived Workspace remains readable with only the approved restore action', async ({ page }) => {
    await loginUI(page, 'owner')
    await page.goto(`${workspaceList}/${archivedId}`)
    await expect(page.getByRole('heading', { name: 'Archived Team Integration', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Khôi phục không gian', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Chỉnh sửa không gian', exact: true })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Lưu trữ không gian', exact: true })).toHaveCount(0)
    await page.goto(`${workspaceList}/${archivedId}/tasks`)
    await expect(page.getByRole('heading', { name: 'Công việc', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Tạo công việc', exact: true })).toHaveCount(0)
  })

  test('work-management lists, details and forms stay accessible at four viewport sizes', async ({ page }) => {
    test.setTimeout(120_000)
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await loginUI(page, 'owner')
    const screenshots = required('HT_FRONTEND_SCREENSHOT_DIR')
    const verify = async (surface: string, width: number) => {
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
      expect(a11y.violations.map((violation) => ({
        id: violation.id, impact: violation.impact, targets: violation.nodes.map((node) => node.target),
      }))).toEqual([])
      await page.screenshot({
        path: join(screenshots, `${surface}-${width}.png`), fullPage: true,
        mask: [page.getByText(required('HT_FRONTEND_TEST_OWNER_EMAIL'), { exact: true })],
      })
    }
    for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 812, height: 375 }, { width: 1440, height: 1000 }]) {
      await page.setViewportSize(size)
      await page.goto(taskPage)
      await expect(page.getByRole('heading', { name: 'Công việc', exact: true })).toBeVisible()
      await verify('task-list', size.width)
      await page.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
      await expect(page.getByRole('dialog', { name: 'Tạo công việc', exact: true })).toBeVisible()
      await verify('task-create', size.width)
      await page.keyboard.press('Escape')
      await expect(page.getByRole('dialog')).not.toBeVisible()
      await expect(page.getByRole('button', { name: 'Tạo công việc', exact: true })).toBeFocused()
      await page.goto(`${taskPage}/${rootId}`)
      await expect(page.getByRole('heading', { name: 'Hierarchy root Integration', exact: true })).toBeVisible()
      await verify('task-detail', size.width)
      await page.goto(workspaceList)
      await page.getByRole('button', { name: 'Tạo không gian', exact: true }).click()
      await expect(page.getByRole('dialog', { name: 'Tạo không gian làm việc', exact: true })).toBeVisible()
      await verify('workspace-create', size.width)
      await page.keyboard.press('Escape')
      await expect(page.getByRole('dialog')).not.toBeVisible()
    }
  })
})

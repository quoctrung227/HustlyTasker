import { createHash } from 'node:crypto'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type BrowserContext, type Page } from '@playwright/test'
import { expectTaskDeadline, fillTaskDeadline } from './task-deadline'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated frontend integration launcher.')
  return value
}
const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Invalid isolated fixture run identity.')
function fixtureId(label: string): string {
  const hash = createHash('sha1').update(Buffer.from(runId, 'hex')).update(label, 'utf8').digest()
  hash[6] = (hash.readUInt8(6) & 0x0f) | 0x50
  hash[8] = (hash.readUInt8(8) & 0x3f) | 0x80
  const hex = hash.subarray(0, 16).toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
const profileId = fixtureId('management_profile'), workspaceId = fixtureId('management_workspace')
const listPath = `/profiles/${profileId}/workspaces/${workspaceId}/tasks`
const apiTasks = `/api/v1/profiles/${profileId}/workspaces/${workspaceId}/tasks/`
const title = `Phiếu giao dựng video ${runId.slice(0, 8)}`
const amount = '9007199254740993'
const formattedAmount = '9.007.199.254.740.993'
const documents = [
  { field: 'raw_video_url', label: 'Link video gốc (raw)', action: 'Mở video gốc', url: 'https://example.test/private/raw?file=synthetic' },
  { field: 'reference_video_url', label: 'Link video tham khảo', action: 'Mở video tham khảo', url: 'https://example.test/reference' },
  { field: 'template_project_url', label: 'Link dự án mẫu', action: 'Mở dự án mẫu', url: 'https://example.test/template' },
  { field: 'script_url', label: 'Link kịch bản', action: 'Mở kịch bản', url: 'https://example.test/script' },
] as const
type BriefTask = {
  id: string; parent_id: string | null; title: string; status: string; deadline: string | null
  raw_video_url: string | null; reference_video_url: string | null
  template_project_url: string | null; script_url: string | null
  estimated_compensation_vnd: string | null
}
async function login(page: Page, actor: string) {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(`${actor}.${runId}@example.test`)
  try {
    await page.getByLabel('Mật khẩu', { exact: true }).evaluate((element, secret) => {
      if (!(element instanceof HTMLInputElement) || element.type !== 'password') throw new Error('Masked input required.')
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      if (!setter) throw new Error('Native setter unavailable.')
      setter.call(element, secret)
      element.dispatchEvent(new Event('input', { bubbles: true }))
    }, required('HT_FRONTEND_TEST_PASSWORD'))
  } catch { throw new Error('Isolated masked credential entry failed.') }
  const result = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/login/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await result).status()).toBe(200)
  await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
}
async function read(page: Page, id: string): Promise<BriefTask> {
  const response = await page.request.get(`${apiTasks}${id}/`)
  expect(response.status()).toBe(200)
  return response.json() as Promise<BriefTask>
}
async function csrf(page: Page) {
  const response = await page.request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  return { 'X-CSRFToken': (await response.json() as { csrf_token: string }).csrf_token }
}

test.describe('Vietnamese Task brief — real UI, isolated PostgreSQL and no external resources', () => {
  test.describe.configure({ mode: 'serial' })
  const contexts: BrowserContext[] = [], failures: string[] = []
  let manager: Page, taskId: string
  function observe(page: Page) {
    page.on('pageerror', (error) => failures.push(error.name))
    page.on('response', (response) => { if (response.status() >= 500) failures.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })
  }
  test.beforeAll(async ({ browser }) => {
    // English browser locale proves the VI date/24h controls do not depend on it.
    const context = await browser.newContext({ baseURL: test.info().project.use.baseURL, locale: 'en-US', timezoneId: 'Asia/Ho_Chi_Minh' })
    contexts.push(context); manager = await context.newPage(); observe(manager)
    await login(manager, 'manager')
  })
  test.afterEach(() => { expect(failures).toEqual([]) })
  test.afterAll(async () => { for (const context of contexts) await context.close() })

  test('manager creates the complete brief with exact large VNĐ and controlled18:30, keeping one draft during auth refresh', async () => {
    test.setTimeout(120_000)
    await manager.goto(listPath)
    await expect(manager.getByLabel('Cấu trúc', { exact: true })).toHaveCount(0)
    const trigger = manager.getByRole('button', { name: 'Tạo công việc', exact: true })
    await trigger.focus(); await manager.keyboard.press('Enter')
    const dialog = manager.getByRole('dialog', { name: 'Tạo công việc', exact: true })
    await expect(dialog).toBeVisible()
    await manager.keyboard.press('Escape'); await expect(dialog).not.toBeVisible(); await expect(trigger).toBeFocused()
    await manager.keyboard.press('Enter')
    await dialog.getByLabel('Tên công việc', { exact: true }).fill(title)
    await dialog.getByLabel('Mô tả', { exact: true }).fill('Phiếu dựng video giả lập, không tải nội dung liên kết bên ngoài.')
    await dialog.getByLabel('Mức ưu tiên', { exact: true }).selectOption('HIGH')
    for (const document of documents) await dialog.getByLabel(document.label, { exact: true }).fill(document.url)
    await dialog.getByLabel('Tiền công dự kiến (VNĐ)', { exact: true }).fill(formattedAmount)
    await fillTaskDeadline(dialog, '2027-12-31T18:30')
    await dialog.getByText('Chọn ngày từ lịch', { exact: true }).click()
    const calendar = dialog.getByRole('table', { name: 'Lịch tháng 12 năm 2027', exact: true })
    await expect(calendar).toBeVisible()
    await expect(dialog.getByLabel('Tháng trên lịch', { exact: true })).toHaveValue('12')
    for (const width of [375, 1440]) {
      await manager.setViewportSize({ width, height: 1000 })
      await calendar.scrollIntoViewIfNeeded()
      expect(await manager.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      expect((await new AxeBuilder({ page: manager }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
      await manager.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `task-calendar-${width}.png`), fullPage: true })
    }
    await calendar.getByRole('button', { name: 'Ngày 31 tháng 12 năm 2027', exact: true }).focus()
    await manager.keyboard.press('ArrowLeft')
    await expect(calendar.getByRole('button', { name: 'Ngày 30 tháng 12 năm 2027', exact: true })).toBeFocused()
    await manager.keyboard.press('Escape')
    await expect(calendar).not.toBeVisible()
    await expect(dialog).toBeVisible()
    await expectTaskDeadline(dialog, '2027-12-31T18:30')
    await expect(dialog.locator('input[type="datetime-local"]')).toHaveCount(0)
    expect(await dialog.getByLabel('Giờ (00–23)', { exact: true }).evaluate((element) => Array.from((element as HTMLSelectElement).options).filter((option) => option.value).map((option) => option.value))).toEqual(Array.from({ length: 24 }, (_, value) => String(value).padStart(2, '0')))
    await expect(dialog.getByLabel('Link kịch bản', { exact: true })).toHaveAttribute('type', 'url')
    const original = await dialog.elementHandle()
    const refreshed = manager.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/me/' && response.request().method() === 'GET')
    await manager.evaluate(() => window.dispatchEvent(new Event('focus')))
    expect((await refreshed).status()).toBe(200)
    expect(await original?.evaluate((element) => element.isConnected && element === document.querySelector('dialog[open]'))).toBe(true)
    await expect(dialog.getByLabel('Tên công việc', { exact: true })).toHaveValue(title)
    await expect(dialog.getByLabel('Tiền công dự kiến (VNĐ)', { exact: true })).toHaveValue(formattedAmount)
    for (const document of documents) await expect(dialog.getByLabel(document.label, { exact: true })).toHaveValue(document.url)
    await expectTaskDeadline(dialog, '2027-12-31T18:30')
    await manager.emulateMedia({ reducedMotion: 'reduce' })
    for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
      await manager.setViewportSize(size)
      expect(await manager.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      expect((await new AxeBuilder({ page: manager }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
      if (size.width === 375 || size.width === 1440) {
        await dialog.getByLabel('Tiền công dự kiến (VNĐ)', { exact: true }).scrollIntoViewIfNeeded()
        await manager.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `task-brief-form-${size.width}.png`), fullPage: true })
      }
    }
    await manager.setViewportSize({ width: 1440, height: 1000 })
    const created = manager.waitForResponse((response) => new URL(response.url()).pathname === apiTasks && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
    const response = await created
    expect(response.status()).toBe(201)
    expect(Boolean(response.request().headers()['x-csrftoken'])).toBe(true)
    expect(response.request().postDataJSON()).toMatchObject({ estimated_compensation_vnd: amount, deadline: '2027-12-31T11:30:00.000Z' })
    const body = await response.json() as BriefTask
    taskId = body.id
    expect(body.estimated_compensation_vnd).toBe(amount)
    expect(new Date(body.deadline ?? '').toISOString()).toBe('2027-12-31T11:30:00.000Z')
    expect(body.parent_id).toBeNull(); expect(body.status).toBe('PENDING')
    for (const document of documents) expect(body[document.field]).toBe(document.url)
    await expect(dialog).not.toBeVisible()
    await manager.goto(`${listPath}/${taskId}`)
    await expect(manager.getByRole('heading', { name: title, exact: true })).toBeVisible()
    for (const document of documents) {
      const link = manager.getByRole('link', { name: document.action, exact: true })
      await expect(link).toHaveAttribute('href', document.url)
      await expect(link).toHaveAttribute('target', '_blank')
      await expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    }
    await expect(manager.getByText(/9\.007\.199\.254\.740\.993/)).toBeVisible()
    await expect(manager.getByText('31/12/2027 18:30', { exact: true })).toBeVisible()
    await expect(manager.getByRole('heading', { name: 'Công việc con', exact: true })).toHaveCount(0)
    await expect(manager.getByRole('button', { name: 'Tạo công việc con', exact: true })).toHaveCount(0)
    await expect(manager.getByRole('navigation', { name: 'Phân cấp công việc', exact: true })).toHaveCount(0)
  })

  test('only current managers and assignee receive pay in real Network responses, including after reassignment', async ({ browser }) => {
    test.setTimeout(60_000)
    await manager.getByRole('button', { name: 'Phân công', exact: true }).click()
    const dialog = manager.getByRole('dialog', { name: 'Phân công công việc', exact: true })
    await dialog.getByLabel('Thành viên', { exact: true }).selectOption(fixtureId('editor_profile_membership'))
    await dialog.getByRole('button', { name: 'Xác nhận phân công', exact: true }).click()
    await expect(dialog).not.toBeVisible()
    let editor: Page | undefined
    for (const actor of ['owner', 'editor', 'other_editor', 'viewer']) {
      const context = await browser.newContext({ baseURL: test.info().project.use.baseURL, locale: 'en-US', timezoneId: 'Asia/Ho_Chi_Minh' })
      contexts.push(context)
      const page = await context.newPage(); observe(page)
      expect((await page.request.get(`${apiTasks}${taskId}/`)).status()).toBe(403)
      await login(page, actor)
      const received = page.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${taskId}/` && response.request().method() === 'GET')
      await page.goto(`${listPath}/${taskId}`)
      await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
      const network = await received
      expect(network.status()).toBe(200)
      const body = await network.json() as BriefTask
      const permitted = actor === 'owner' || actor === 'editor'
      expect(body.estimated_compensation_vnd).toBe(permitted ? amount : null)
      expect((await read(page, taskId)).estimated_compensation_vnd).toBe(permitted ? amount : null)
      const listed = await page.request.get(`${apiTasks}?page_size=100`)
      expect(listed.status()).toBe(200)
      const listBody = await listed.json() as { results: BriefTask[] }
      expect(listBody.results.find((task) => task.id === taskId)?.estimated_compensation_vnd).toBe(permitted ? amount : null)
      if (permitted) {
        await expect(page.getByText(/9\.007\.199\.254\.740\.993/)).toBeVisible()
      } else {
        expect(await network.text()).not.toContain(amount)
        expect(await listed.text()).not.toContain(amount)
        await expect(page.getByText(/9\.007\.199\.254\.740\.993/)).toHaveCount(0)
        await expect(page.getByRole('heading', { name: 'Tiền công dự kiến', exact: true })).toHaveCount(0)
      }
      if (actor !== 'owner') {
        await expect(page.getByRole('button', { name: 'Chỉnh sửa công việc', exact: true })).toHaveCount(0)
        expect((await page.request.patch(`${apiTasks}${taskId}/`, { data: { estimated_compensation_vnd: '0' } })).status()).toBe(403)
        expect((await page.request.patch(`${apiTasks}${taskId}/`, { headers: await csrf(page), data: { estimated_compensation_vnd: '0' } })).status()).toBe(403)
        expect((await page.request.put(`${apiTasks}${taskId}/`, { headers: await csrf(page), data: { estimated_compensation_vnd: '0' } })).status()).toBe(405)
      }
      expect((await page.request.get(`${apiTasks}${fixtureId('task_foreign')}/`)).status()).toBe(404)
      await page.reload()
      await expect(page.getByRole('link', { name: 'Mở kịch bản', exact: true })).toBeVisible()
      if (!permitted) {
        await expect(page.getByText(/9\.007\.199\.254\.740\.993/)).toHaveCount(0)
        await page.goto(listPath)
        await expect(page.getByRole('link', { name: title, exact: true })).toBeVisible()
        await expect(page.getByText(/9\.007\.199\.254\.740\.993/)).toHaveCount(0)
      }
      if (actor === 'editor') editor = page
    }
    // Assignment history is preserved, but only its current assignee can read pay.
    await manager.getByRole('button', { name: 'Phân công', exact: true }).click()
    const reassign = manager.getByRole('dialog', { name: 'Phân công công việc', exact: true })
    await reassign.getByLabel('Thành viên', { exact: true }).selectOption(fixtureId('other_editor_profile_membership'))
    await reassign.getByRole('button', { name: 'Xác nhận phân công', exact: true }).click()
    await expect(reassign).not.toBeVisible()
    if (!editor) throw new Error('Assigned actor browser was not created.')
    const redacted = editor.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${taskId}/` && response.request().method() === 'GET')
    // Same document and same-user cache: revalidation must replace the old value.
    await editor.evaluate(() => window.dispatchEvent(new Event('focus')))
    expect((await (await redacted).json() as BriefTask).estimated_compensation_vnd).toBeNull()
    await expect(editor.getByText(/9\.007\.199\.254\.740\.993/)).toHaveCount(0)
    await expect(editor.getByRole('heading', { name: 'Tiền công dự kiến', exact: true })).toHaveCount(0)
    expect((await read(editor, taskId)).estimated_compensation_vnd).toBeNull()
    expect((await read(manager, taskId)).estimated_compensation_vnd).toBe(amount)
    expect((await manager.request.patch(`${apiTasks}${taskId}/`, { headers: await csrf(manager), data: { script_url: 'javascript:alert(1)' } })).status()).toBe(400)
    expect((await read(manager, taskId)).script_url).toBe(documents[3].url)
  })

  test('manager reopens, edits and clears every document and compensation, with00:00/23:59/clear round trips', async () => {
    await manager.reload()
    await manager.getByRole('button', { name: 'Chỉnh sửa công việc', exact: true }).click()
    let dialog = manager.getByRole('dialog', { name: 'Chỉnh sửa công việc', exact: true })
    await expectTaskDeadline(dialog, '2027-12-31T18:30')
    await expect(dialog.getByLabel('Tiền công dự kiến (VNĐ)', { exact: true })).toHaveValue(formattedAmount)
    for (const document of documents) await dialog.getByLabel(document.label, { exact: true }).fill('')
    await dialog.getByLabel('Tiền công dự kiến (VNĐ)', { exact: true }).fill('0')
    await fillTaskDeadline(dialog, '2028-01-01T00:00')
    await dialog.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click()
    await expect(dialog).not.toBeVisible()
    let body = await read(manager, taskId)
    for (const document of documents) expect(body[document.field]).toBeNull()
    expect(body.estimated_compensation_vnd).toBe('0')
    expect(new Date(body.deadline ?? '').toISOString()).toBe('2027-12-31T17:00:00.000Z')
    await expect(manager.getByRole('link', { name: 'Mở kịch bản', exact: true })).toHaveCount(0)
    await expect(manager.getByText('0 VNĐ', { exact: true })).toBeVisible()
    await manager.getByRole('button', { name: 'Chỉnh sửa công việc', exact: true }).click()
    dialog = manager.getByRole('dialog', { name: 'Chỉnh sửa công việc', exact: true })
    await expectTaskDeadline(dialog, '2028-01-01T00:00')
    await fillTaskDeadline(dialog, '2028-01-02T23:59')
    await dialog.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click()
    await expect(dialog).not.toBeVisible()
    expect(new Date((await read(manager, taskId)).deadline ?? '').toISOString()).toBe('2028-01-02T16:59:00.000Z')
    await manager.getByRole('button', { name: 'Chỉnh sửa công việc', exact: true }).click()
    dialog = manager.getByRole('dialog', { name: 'Chỉnh sửa công việc', exact: true })
    await expectTaskDeadline(dialog, '2028-01-02T23:59')
    await fillTaskDeadline(dialog, '')
    await dialog.getByLabel('Tiền công dự kiến (VNĐ)', { exact: true }).fill('')
    await dialog.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click()
    await expect(dialog).not.toBeVisible()
    body = await read(manager, taskId)
    expect(body.deadline).toBeNull(); expect(body.estimated_compensation_vnd).toBeNull(); expect(body.status).toBe('ASSIGNED')
  })

  test('name-only creation remains valid and historical child Tasks stay readable without hierarchy affordances or mutations', async () => {
    await manager.goto(listPath)
    await manager.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
    const dialog = manager.getByRole('dialog', { name: 'Tạo công việc', exact: true })
    await dialog.getByLabel('Tên công việc', { exact: true }).fill('Phiếu tối giản chỉ có tên')
    const created = manager.waitForResponse((response) => new URL(response.url()).pathname === apiTasks && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
    const response = await created
    expect(response.status()).toBe(201)
    const body = await response.json() as BriefTask
    for (const document of documents) expect(body[document.field]).toBeNull()
    expect(body.deadline).toBeNull(); expect(body.estimated_compensation_vnd).toBeNull()
    const child = await read(manager, fixtureId('task_child'))
    expect(child.parent_id).toBe(fixtureId('task_root'))
    await manager.goto(`${listPath}/${child.id}`)
    await expect(manager.getByRole('heading', { name: 'Hierarchy child Integration', exact: true })).toBeVisible()
    await expect(manager.getByRole('navigation', { name: 'Phân cấp công việc', exact: true })).toHaveCount(0)
    await expect(manager.getByRole('button', { name: 'Tạo công việc con', exact: true })).toHaveCount(0)
    expect((await read(manager, child.id)).parent_id).toBe(fixtureId('task_root'))
  })
})

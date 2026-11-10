import { createHash } from 'node:crypto'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type BrowserContext, type Locator, type Page } from '@playwright/test'
import { fillTaskDeadline } from './task-deadline'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated Task UX integration launcher.')
  return value
}
const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Invalid isolated fixture identity.')
function fixtureId(label: string): string {
  const hash = createHash('sha1').update(Buffer.from(runId, 'hex')).update(label, 'utf8').digest()
  hash[6] = (hash.readUInt8(6) & 0x0f) | 0x50
  hash[8] = (hash.readUInt8(8) & 0x3f) | 0x80
  const hex = hash.subarray(0, 16).toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
const profileId = fixtureId('management_profile'), workspaceId = fixtureId('management_workspace')
const taskPath = `/profiles/${profileId}/workspaces/${workspaceId}/tasks`
const apiTasks = `/api/v1/profiles/${profileId}/workspaces/${workspaceId}/tasks/`
const title = `Nghiệm thu Task UX ${runId.slice(0, 8)}`
const endMarker = `KẾT THÚC MÔ TẢ ${runId.slice(0, 8)}`
const longDescription = `${'Dựng video giả lập, giữ nguyên từng chi tiết. '.repeat(550)}\nhttps://example.test/${'x'.repeat(1500)}\n${endMarker}`
const shortDescription = 'Mô tả ngắn vẫn giữ đúng bố cục và toàn bộ dữ liệu công việc.'
const documents = [
  { field: 'raw_video_url', label: 'Link video gốc (raw)', action: 'Mở video gốc', url: 'https://example.test/ux-raw' },
  { field: 'reference_video_url', label: 'Link video tham khảo', action: 'Mở video tham khảo', url: 'https://example.test/ux-reference' },
  { field: 'template_project_url', label: 'Link dự án mẫu', action: 'Mở dự án mẫu', url: 'https://example.test/ux-template' },
  { field: 'script_url', label: 'Link kịch bản', action: 'Mở kịch bản', url: 'https://example.test/ux-script' },
] as const
type Task = {
  id: string; status: string; description: string | null; deadline: string | null
  estimated_compensation_vnd: string | null
  active_assignment: { profile_membership_id: string | null; display_name: string | null } | null
}
type Deliverable = { id: string; revision: number; file_url: string; can_approve: boolean; can_request_changes: boolean }
async function login(page: Page, actor: 'manager' | 'editor' | 'viewer') {
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
  const received = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/login/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await received).status()).toBe(200)
  await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
}
async function readTask(page: Page, id: string): Promise<Task> {
  const response = await page.request.get(`${apiTasks}${id}/`)
  expect(response.status()).toBe(200)
  return response.json() as Promise<Task>
}
async function csrf(page: Page) {
  const response = await page.request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  return { 'X-CSRFToken': (await response.json() as { csrf_token: string }).csrf_token }
}
async function box(locator: Locator) {
  const value = await locator.boundingBox()
  if (!value) throw new Error('Expected a visible layout surface.')
  return value
}
function assignmentValue(page: Page) {
  return page.locator('.task-detail-grid .workspace-facts dl > div').filter({ has: page.getByText('Phân công', { exact: true }) }).locator('dd')
}
async function checkDocumentLinks(page: Page) {
  for (const document of documents) {
    const link = page.getByRole('link', { name: document.action, exact: true })
    await expect(link).toHaveAttribute('href', document.url)
    await expect(link).toHaveAttribute('target', '_blank')
    await expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  }
}

test.describe('Task UX refinement — real React mutations and isolated PostgreSQL', () => {
  test.describe.configure({ mode: 'serial' })
  const contexts: BrowserContext[] = [], failures: string[] = [], externalRequests: string[] = []
  let manager: Page, taskId: string, desktopCardHeight: number, desktopFactsHeight: number
  function observe(page: Page) {
    page.on('pageerror', (error) => failures.push(error.name))
    page.on('response', (response) => { if (response.status() >= 500) failures.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })
    page.on('request', (request) => {
      const url = new URL(request.url())
      if (['http:', 'https:'].includes(url.protocol) && !['127.0.0.1', 'localhost'].includes(url.hostname)) externalRequests.push(url.hostname)
    })
  }
  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext({ baseURL: test.info().project.use.baseURL, locale: 'en-US', timezoneId: 'Asia/Ho_Chi_Minh' })
    contexts.push(context); manager = await context.newPage(); observe(manager)
    await login(manager, 'manager')
  })
  test.afterEach(() => { expect(failures).toEqual([]); expect(externalRequests).toEqual([]) })
  test.afterAll(async () => { for (const context of contexts) await context.close() })

  test('long descriptions scroll inside a stable accessible card without stretching adjacent facts at four viewport sizes', async () => {
    test.setTimeout(180_000)
    await manager.setViewportSize({ width: 1440, height: 1000 })
    await manager.goto(taskPath)
    await manager.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
    const dialog = manager.getByRole('dialog', { name: 'Tạo công việc', exact: true })
    await dialog.getByLabel('Tên công việc', { exact: true }).fill(title)
    await dialog.getByLabel('Mô tả', { exact: true }).fill(longDescription)
    await dialog.getByLabel('Mức ưu tiên', { exact: true }).selectOption('HIGH')
    for (const document of documents) await dialog.getByLabel(document.label, { exact: true }).fill(document.url)
    await dialog.getByLabel('Tiền công dự kiến (VNĐ)', { exact: true }).fill('500000')
    await fillTaskDeadline(dialog, '2027-12-31T18:30')
    const created = manager.waitForResponse((response) => new URL(response.url()).pathname === apiTasks && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
    const response = await created
    expect(response.status()).toBe(201)
    const task = await response.json() as Task
    taskId = task.id
    expect(task.description).toBe(longDescription)
    expect(task.estimated_compensation_vnd).toBe('500000')
    expect(new Date(task.deadline ?? '').toISOString()).toBe('2027-12-31T11:30:00.000Z')
    await manager.goto(`${taskPath}/${taskId}`)
    await expect(manager.getByRole('heading', { name: title, exact: true })).toBeVisible()
    await checkDocumentLinks(manager)
    await expect(manager.getByText('500.000 VNĐ', { exact: true })).toBeVisible()
    await expect(manager.getByText('31/12/2027 18:30', { exact: true })).toBeVisible()
    await expect(assignmentValue(manager)).toHaveText('Chưa phân công')
    const card = manager.locator('.task-description-card'), facts = manager.locator('.task-detail-grid .workspace-facts')
    const region = manager.getByRole('region', { name: 'Mô tả công việc', exact: true })
    await expect(region).toHaveAttribute('tabindex', '0')
    expect(await region.textContent()).toBe(longDescription)
    await manager.emulateMedia({ reducedMotion: 'reduce' })
    for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
      await manager.setViewportSize(size)
      await region.evaluate((element) => { element.scrollTop = 0 })
      await region.focus()
      const headerBefore = await box(card.getByRole('heading', { name: 'Thông tin công việc', exact: true }))
      const factsBefore = await box(facts), cardBefore = await box(card)
      const maximum = await manager.evaluate(() => 24 * Number.parseFloat(getComputedStyle(document.documentElement).fontSize))
      if (size.width > 639) expect(Math.abs(cardBefore.height - maximum)).toBeLessThan(2)
      else {
        expect(cardBefore.height).toBeLessThanOrEqual(maximum + 1)
        expect(factsBefore.y).toBeGreaterThanOrEqual(cardBefore.y + cardBefore.height)
      }
      expect(await region.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(true)
      expect(await region.evaluate((element) => element.scrollWidth <= element.clientWidth + 1)).toBe(true)
      await manager.keyboard.press('PageDown')
      await expect.poll(() => region.evaluate((element) => element.scrollTop)).toBeGreaterThan(0)
      expect(await region.evaluate((element) => {
        const style = getComputedStyle(element)
        return element === document.activeElement && style.outlineStyle !== 'none' && Number.parseFloat(style.outlineWidth) > 0
      })).toBe(true)
      await manager.keyboard.press('End')
      await expect.poll(() => region.evaluate((element) => element.scrollHeight - element.clientHeight - element.scrollTop)).toBeLessThan(2)
      await expect(region).toContainText(endMarker)
      const headerAfter = await box(card.getByRole('heading', { name: 'Thông tin công việc', exact: true }))
      expect(Math.abs(headerAfter.y - headerBefore.y)).toBeLessThan(2)
      expect(Math.abs((await box(facts)).height - factsBefore.height)).toBeLessThan(2)
      expect(await manager.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      expect((await new AxeBuilder({ page: manager }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
      if (size.width === 1440) { desktopCardHeight = cardBefore.height; desktopFactsHeight = factsBefore.height }
      if (size.width === 375 || size.width === 1440) await manager.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `task-ux-long-${size.width}.png`), fullPage: true })
    }
  })

  test('UTC date filters stay in one stacked group and a short description keeps desktop geometry without excess scrolling', async () => {
    test.setTimeout(120_000)
    await manager.goto(taskPath)
    await expect(manager.getByRole('link', { name: title, exact: true })).toBeVisible()
    const group = manager.getByRole('group', { name: 'Khoảng thời hạn (UTC)', exact: true })
    const after = group.getByLabel('Thời hạn từ ngày (UTC)', { exact: true }), before = group.getByLabel('Thời hạn đến ngày (UTC)', { exact: true })
    for (const size of [{ width: 1440, height: 1000 }, { width: 768, height: 1024 }, { width: 375, height: 812 }, { width: 812, height: 375 }]) {
      await manager.setViewportSize(size)
      const fromBox = await box(after), toBox = await box(before)
      expect(Math.abs(fromBox.x - toBox.x)).toBeLessThan(2)
      expect(Math.abs(fromBox.width - toBox.width)).toBeLessThan(2)
      expect(toBox.y).toBeGreaterThan(fromBox.y + fromBox.height)
      expect((await box(manager.getByRole('button', { name: 'Áp dụng bộ lọc', exact: true }))).y).toBeGreaterThanOrEqual((await box(group)).y + (await box(group)).height)
      expect(await manager.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      expect((await new AxeBuilder({ page: manager }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
    }
    await manager.setViewportSize({ width: 1440, height: 1000 })
    await after.fill('01/12/2027'); await before.fill('31/12/2027')
    await manager.getByLabel('Trạng thái', { exact: true }).selectOption('PENDING')
    await manager.getByLabel('Mức ưu tiên', { exact: true }).selectOption('HIGH')
    await manager.getByLabel('Sắp xếp', { exact: true }).selectOption('priority')
    const filtered = manager.waitForResponse((response) => {
      const url = new URL(response.url())
      return url.pathname === apiTasks && url.searchParams.get('deadline_after') === '2027-12-01T00:00:00Z' && response.request().method() === 'GET'
    })
    await manager.getByRole('button', { name: 'Áp dụng bộ lọc', exact: true }).click()
    const response = await filtered
    expect(response.status()).toBe(200)
    const query = new URL(response.url()).searchParams
    expect(query.get('deadline_before')).toBe('2027-12-31T23:59:59.999999Z')
    expect(query.get('status')).toBe('PENDING'); expect(query.get('priority')).toBe('HIGH'); expect(query.get('ordering')).toBe('priority')
    expect((await response.json() as { results: Task[] }).results.some((item) => item.id === taskId)).toBe(true)
    await expect(group.getByLabel('Thời hạn từ ngày (UTC)', { exact: true })).toHaveValue('01/12/2027')
    await expect(group.getByLabel('Thời hạn đến ngày (UTC)', { exact: true })).toHaveValue('31/12/2027')
    await manager.getByRole('button', { name: 'Xóa bộ lọc', exact: true }).click()
    await expect(group.getByLabel('Thời hạn từ ngày (UTC)', { exact: true })).toHaveValue('')
    await expect(group.getByLabel('Thời hạn đến ngày (UTC)', { exact: true })).toHaveValue('')
    await manager.goto(`${taskPath}/${taskId}`)
    await manager.getByRole('button', { name: 'Chỉnh sửa công việc', exact: true }).click()
    const dialog = manager.getByRole('dialog', { name: 'Chỉnh sửa công việc', exact: true })
    await dialog.getByLabel('Mô tả', { exact: true }).fill(shortDescription)
    const updated = manager.waitForResponse((value) => new URL(value.url()).pathname === `${apiTasks}${taskId}/` && value.request().method() === 'PATCH')
    await dialog.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click()
    const changed = await updated
    expect(changed.status()).toBe(200)
    expect(changed.request().postDataJSON()).toEqual({ description: shortDescription })
    await expect(dialog).not.toBeVisible()
    const card = manager.locator('.task-description-card'), facts = manager.locator('.task-detail-grid .workspace-facts')
    const region = manager.getByRole('region', { name: 'Mô tả công việc', exact: true })
    await expect(region).toHaveText(shortDescription)
    expect(Math.abs((await box(card)).height - desktopCardHeight)).toBeLessThan(2)
    expect(Math.abs((await box(facts)).height - desktopFactsHeight)).toBeLessThan(2)
    expect(await region.evaluate((element) => element.scrollHeight <= element.clientHeight + 1)).toBe(true)
    await manager.setViewportSize({ width: 375, height: 812 })
    expect((await box(card)).height).toBeLessThan(desktopCardHeight)
    expect(await region.evaluate((element) => element.scrollHeight <= element.clientHeight + 1)).toBe(true)
    await manager.setViewportSize({ width: 1440, height: 1000 })
    await checkDocumentLinks(manager)
    await expect(manager.getByText('500.000 VNĐ', { exact: true })).toBeVisible()
    expect((await readTask(manager, taskId)).deadline).toBe('2027-12-31T11:30:00Z')
  })

  test('UI reassignment refreshes the real assignee name on detail and list without displaying UUIDs or stale names', async () => {
    test.setTimeout(90_000)
    for (const actor of [
      { id: 'editor_profile_membership', name: 'Nhân viên Kiểm thử' },
      { id: 'other_editor_profile_membership', name: 'Đồng nghiệp Kiểm thử' },
      { id: 'editor_profile_membership', name: 'Nhân viên Kiểm thử' },
    ]) {
      await manager.goto(`${taskPath}/${taskId}`)
      await manager.getByRole('button', { name: 'Phân công', exact: true }).click()
      const dialog = manager.getByRole('dialog', { name: 'Phân công công việc', exact: true })
      await dialog.getByLabel('Thành viên', { exact: true }).selectOption(fixtureId(actor.id))
      const assigned = manager.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${taskId}/assign/` && response.request().method() === 'POST')
      await dialog.getByRole('button', { name: 'Xác nhận phân công', exact: true }).click()
      const response = await assigned
      expect(response.status()).toBe(200)
      expect((await response.json() as Task).active_assignment?.display_name).toBe(actor.name)
      await expect(dialog).not.toBeVisible()
      await expect(assignmentValue(manager)).toHaveText(actor.name)
      expect(await manager.locator('.task-detail-grid .workspace-facts').textContent()).not.toContain(fixtureId(actor.id))
      expect((await readTask(manager, taskId)).estimated_compensation_vnd).toBe('500000')
      await manager.goto(taskPath)
      const row = manager.locator('.task-row').filter({ has: manager.getByRole('link', { name: title, exact: true }) })
      await expect(row.locator('.task-assignee')).toHaveText(actor.name)
      expect(await row.locator('.task-assignee').textContent()).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-/i)
    }
  })

  test('Editor submits separate finished-product URLs through revision and approval UI while Viewer gets read-only redacted data', async ({ browser }) => {
    test.setTimeout(180_000)
    const editorContext = await browser.newContext({ baseURL: test.info().project.use.baseURL, locale: 'en-US', timezoneId: 'Asia/Ho_Chi_Minh' })
    contexts.push(editorContext)
    const editor = await editorContext.newPage(); observe(editor)
    await login(editor, 'editor')
    await editor.goto(`${taskPath}/${taskId}`)
    await expect(editor.getByText('500.000 VNĐ', { exact: true })).toBeVisible()
    await expect(editor.getByRole('button', { name: 'Chỉnh sửa công việc', exact: true })).toHaveCount(0)
    const started = editor.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${taskId}/start/` && response.request().method() === 'POST')
    await editor.getByRole('button', { name: 'Bắt đầu công việc', exact: true }).click()
    expect((await started).status()).toBe(200)
    const invalidAPI = await editor.request.post(`${apiTasks}${taskId}/deliverables/`, { headers: await csrf(editor), data: { file_url: 'javascript:alert(1)' } })
    expect(invalidAPI.status()).toBe(400)
    expect((await readTask(editor, taskId)).status).toBe('WORKING')
    let posts = 0
    editor.on('request', (request) => { if (new URL(request.url()).pathname === `${apiTasks}${taskId}/deliverables/` && request.method() === 'POST') posts++ })
    await editor.getByRole('button', { name: 'Nộp sản phẩm', exact: true }).click()
    let dialog = editor.getByRole('dialog', { name: 'Nộp sản phẩm', exact: true })
    const input = dialog.getByLabel('Link sản phẩm hoàn thành', { exact: true })
    await expect(input).toHaveAttribute('type', 'url')
    await input.fill('javascript:alert(1)')
    await dialog.getByRole('button', { name: 'Nộp sản phẩm', exact: true }).click()
    await expect(dialog.getByRole('alert')).toBeVisible()
    await expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(posts).toBe(0)
    const firstUrl = 'https://drive.google.com/file/d/synthetic-task-ux-v1/view'
    await input.fill(firstUrl)
    const submitted = editor.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${taskId}/deliverables/` && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Nộp sản phẩm', exact: true }).click()
    const firstResponse = await submitted
    expect(firstResponse.status()).toBe(201)
    expect(firstResponse.request().postDataJSON()).toEqual({ file_url: firstUrl })
    expect(Boolean(firstResponse.request().headers()['x-csrftoken'])).toBe(true)
    const first = await firstResponse.json() as Deliverable
    expect(first.revision).toBe(1)
    await expect(dialog).not.toBeVisible()
    expect((await readTask(editor, taskId)).status).toBe('REVIEW')
    await expect(editor.getByRole('button', { name: /^(Phê duyệt sản phẩm|Yêu cầu chỉnh sửa)$/ })).toHaveCount(0)
    await manager.goto(`${taskPath}/${taskId}`)
    const firstCard = manager.getByRole('article', { name: 'Phiên bản 1', exact: true })
    await expect(firstCard.getByRole('link', { name: /Mở sản phẩm/ })).toHaveAttribute('href', firstUrl)
    await firstCard.getByRole('button', { name: 'Yêu cầu chỉnh sửa', exact: true }).click()
    let reviewDialog = manager.getByRole('dialog', { name: 'Yêu cầu chỉnh sửa', exact: true })
    await reviewDialog.getByLabel('Nội dung cần chỉnh sửa', { exact: true }).fill('Điều chỉnh phụ đề ở phần kết thúc rồi nộp phiên bản mới.')
    const changes = manager.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${taskId}/deliverables/${first.id}/request-changes/` && response.request().method() === 'POST')
    await reviewDialog.getByRole('button', { name: 'Gửi yêu cầu chỉnh sửa', exact: true }).click()
    expect((await changes).status()).toBe(200)
    await expect(reviewDialog).not.toBeVisible()
    expect((await readTask(manager, taskId)).status).toBe('WORKING')
    await editor.reload()
    await editor.getByRole('button', { name: 'Nộp sản phẩm', exact: true }).click()
    dialog = editor.getByRole('dialog', { name: 'Nộp sản phẩm', exact: true })
    const secondUrl = 'https://www.dropbox.com/s/synthetic-task-ux-v2/final.mp4?dl=0'
    await dialog.getByLabel('Link sản phẩm hoàn thành', { exact: true }).fill(secondUrl)
    const resubmitted = editor.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${taskId}/deliverables/` && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Nộp sản phẩm', exact: true }).click()
    const secondResponse = await resubmitted
    expect(secondResponse.status()).toBe(201)
    const second = await secondResponse.json() as Deliverable
    expect(second.revision).toBe(2)
    await expect(dialog).not.toBeVisible()
    await manager.reload()
    const secondCard = manager.getByRole('article', { name: 'Phiên bản 2', exact: true })
    await expect(secondCard.getByRole('link', { name: /Mở sản phẩm/ })).toHaveAttribute('href', secondUrl)
    await expect(firstCard.getByRole('button', { name: 'Phê duyệt sản phẩm', exact: true })).toHaveCount(0)
    await secondCard.getByRole('button', { name: 'Phê duyệt sản phẩm', exact: true }).click()
    reviewDialog = manager.getByRole('dialog', { name: 'Phê duyệt sản phẩm', exact: true })
    const approved = manager.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${taskId}/deliverables/${second.id}/approve/` && response.request().method() === 'POST')
    await reviewDialog.getByRole('button', { name: 'Xác nhận phê duyệt', exact: true }).click()
    expect((await approved).status()).toBe(200)
    await expect(reviewDialog).not.toBeVisible()
    expect((await readTask(manager, taskId)).status).toBe('COMPLETED')
    for (const [revision, url] of [[1, firstUrl], [2, secondUrl]] as const) {
      const link = manager.getByRole('article', { name: `Phiên bản ${revision}`, exact: true }).getByRole('link', { name: /Mở sản phẩm/ })
      await expect(link).toHaveAttribute('href', url)
      await expect(link).toHaveAttribute('target', '_blank')
      await expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    }
    expect(posts).toBe(2)
    const viewerContext = await browser.newContext({ baseURL: test.info().project.use.baseURL, locale: 'en-US', timezoneId: 'Asia/Ho_Chi_Minh' })
    contexts.push(viewerContext)
    const viewer = await viewerContext.newPage(); observe(viewer)
    await login(viewer, 'viewer')
    const viewed = viewer.waitForResponse((response) => new URL(response.url()).pathname === `${apiTasks}${taskId}/` && response.request().method() === 'GET')
    await viewer.goto(`${taskPath}/${taskId}`)
    const network = await viewed
    expect(network.status()).toBe(200)
    expect((await network.json() as Task).estimated_compensation_vnd).toBeNull()
    expect(await network.text()).not.toContain('500000')
    await expect(viewer.getByRole('heading', { name: title, exact: true })).toBeVisible()
    await expect(viewer.getByRole('heading', { name: 'Tiền công dự kiến', exact: true })).toHaveCount(0)
    await expect(viewer.getByRole('button', { name: /^(Nộp sản phẩm|Bắt đầu công việc|Chỉnh sửa công việc|Phê duyệt sản phẩm|Yêu cầu chỉnh sửa)$/ })).toHaveCount(0)
    await checkDocumentLinks(viewer)
    await expect(assignmentValue(viewer)).toHaveText('Nhân viên Kiểm thử')
    expect((await viewer.request.patch(`${apiTasks}${taskId}/`, { headers: await csrf(viewer), data: { estimated_compensation_vnd: '0' } })).status()).toBe(403)
  })
})

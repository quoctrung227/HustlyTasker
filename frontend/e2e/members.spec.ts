import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { consumeLegacyInvitation, createPath, csrf, currentWorkspace, enterSecret, fixtureId, foreignId, invite, invitationRow, login, logout,
  managerPath, openPicker, previousWorkspace, profileId, readInvitations, required } from './invitation-v2-helpers'

test.describe('Organization members — approved account cutover, isolated PostgreSQL and fake mail', () => {
  test.describe.configure({ mode: 'serial' })
  const failures = new WeakMap<Page, string[]>()
  test.beforeEach(({ page }) => {
    const errors: string[] = []; failures.set(page, errors)
    page.on('pageerror', (error) => errors.push(error.name))
    page.on('response', (response) => { if (response.status() >= 500) errors.push(`HTTP ${response.status()}`) })
  })
  test.afterEach(({ page }) => { expect(failures.get(page)).toEqual([]) })

  test('Owner sends through React; registered nonmember accepts on Web and gains only approved current-month access', async ({ page }) => {
    await login(page, 'owner')
    const issued = await invite(page, 'recipient')
    expect(issued.delivery_status).toBe('SENT')
    await logout(page); await login(page, 'recipient')
    expect((await (await page.request.get('/api/v1/profiles/')).json() as { count: number }).count).toBe(0)
    expect((await page.request.get(`/api/v1/profiles/${profileId}/workspaces/${currentWorkspace}/`)).status()).toBe(404)
    await page.goto('/notifications')
    await expect(page.getByRole('button', { name: 'Chấp nhận lời mời', exact: true })).toBeVisible()
    await expect(page.getByLabel('Mã lời mời', { exact: true })).toHaveCount(0)
    const accepted = page.waitForResponse((response) => new URL(response.url()).pathname === `/api/v1/invitations/${issued.id}/accept/` && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Chấp nhận lời mời', exact: true }).click()
    const response = await accepted
    expect(response.status()).toBe(200); expect(response.request().postDataJSON()).toEqual({})
    await expect(page.getByRole('link', { name: 'Đến tổ chức', exact: true })).toBeVisible()
    expect((await page.request.get(`/api/v1/profiles/${profileId}/workspaces/${currentWorkspace}/`)).status()).toBe(200)
    expect((await page.request.get(`/api/v1/profiles/${profileId}/workspaces/${previousWorkspace}/`)).status()).toBe(404)
    expect((await page.request.get(`/api/v1/profiles/${profileId}/members/`)).status()).toBe(403)
    const replay = await page.request.post(`/api/v1/invitations/${issued.id}/accept/`, { headers: await csrf(page), data: {} })
    expect(replay.status()).toBe(200)
    expect((await (await page.request.get('/api/v1/profiles/')).json() as { count: number }).count).toBe(1)
    expect((await page.request.get(`/api/v1/profiles/${foreignId}/members/`)).status()).toBe(404)
  })

  test('wrong recipient and Admin escalation fail; resend preserves identity and the recipient declines explicitly', async ({ page, browser }) => {
    test.setTimeout(60_000)
    await login(page, 'owner')
    const issued = await invite(page, 'decliner'), count = (await readInvitations(page)).count
    const resend = page.waitForResponse((response) => new URL(response.url()).pathname === `${createPath}${issued.id}/resend/` && response.request().method() === 'POST')
    await invitationRow(page, issued).getByRole('button', { name: 'Thử gửi lại email', exact: true }).click()
    const saved = await resend
    expect(saved.status()).toBe(200)
    expect(await saved.json()).toMatchObject({ id: issued.id, expires_at: issued.expires_at, requested_role: 'MEMBER' })
    expect((await readInvitations(page)).count).toBe(count)
    const context = await browser.newContext({ baseURL: test.info().project.use.baseURL })
    try {
      const admin = await context.newPage(); await login(admin, 'admin')
      expect((await admin.request.get(`/api/v1/invitations/${issued.id}/`)).status()).toBe(404)
      expect((await admin.request.post(`/api/v1/invitations/${issued.id}/accept/`, { headers: await csrf(admin), data: {} })).status()).toBe(404)
      const picker = await openPicker(admin)
      await expect(picker.getByRole('option', { name: 'Quản trị viên', exact: true })).toHaveCount(0)
      expect((await admin.request.post(createPath, { headers: await csrf(admin), data: { recipient_user_id: fixtureId('invitation_v2_switcher'), requested_role: 'ADMIN' } })).status()).toBe(403)
    } finally { await context.close() }
    await logout(page); await login(page, 'decliner'); await page.goto(`/invitations/${issued.id}`)
    await page.getByRole('button', { name: 'Từ chối lời mời', exact: true }).click()
    const declined = page.waitForResponse((response) => new URL(response.url()).pathname === `/api/v1/invitations/${issued.id}/decline/` && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Xác nhận từ chối', exact: true }).click()
    expect((await declined).status()).toBe(200)
    await expect(page.getByText(/Đã từ chối/).first()).toBeVisible()
    expect((await (await page.request.get('/api/v1/profiles/')).json() as { count: number }).count).toBe(0)
  })

  test('revoke blocks membership; Workspace Viewer cannot bypass directory, CSRF or cross-tenant boundaries', async ({ page, browser }) => {
    await login(page, 'owner')
    const issued = await invite(page, 'switcher')
    await invitationRow(page, issued).getByRole('button', { name: 'Hủy lời mời', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: 'Hủy lời mời', exact: true })
    const revoked = page.waitForResponse((response) => new URL(response.url()).pathname === `${createPath}${issued.id}/revoke/` && response.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Xác nhận hủy lời mời', exact: true }).click()
    expect((await revoked).status()).toBe(200)
    await logout(page); await login(page, 'switcher'); await page.goto(`/invitations/${issued.id}`)
    await expect(page.getByText(/Đã thu hồi/)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Chấp nhận lời mời', exact: true })).toHaveCount(0)
    expect((await page.request.post(`/api/v1/invitations/${issued.id}/accept/`, { headers: await csrf(page), data: {} })).status()).toBe(409)
    expect((await (await page.request.get('/api/v1/profiles/')).json() as { results: { id: string }[] }).results.map((row) => row.id)).toEqual([foreignId])
    const context = await browser.newContext({ baseURL: test.info().project.use.baseURL })
    try {
      const viewer = await context.newPage(); await login(viewer, 'member'); await viewer.goto(managerPath)
      await expect(viewer.getByRole('button', { name: 'Thêm thành viên', exact: true })).toHaveCount(0)
      expect((await viewer.request.get(`/api/v1/profiles/${profileId}/invitation-candidates/`)).status()).toBe(403)
      expect((await viewer.request.get(`/api/v1/profiles/${foreignId}/members/`)).status()).toBe(404)
      expect((await viewer.request.post(createPath, { headers: await csrf(viewer), data: { recipient_user_id: fixtureId('invitation_v2_retry'), requested_role: 'MEMBER' } })).status()).toBe(403)
      expect((await viewer.request.post(createPath, { headers: { 'X-CSRFToken': 'invalid' }, data: { recipient_user_id: fixtureId('invitation_v2_retry'), requested_role: 'MEMBER' } })).status()).toBe(403)
    } finally { await context.close() }
  })

  test('picker draft/focus survives refresh and four sizes; legacy token acceptance remains direct and unpromoted', async ({ page }) => {
    test.setTimeout(90_000)
    await page.emulateMedia({ reducedMotion: 'reduce' }); await login(page, 'owner')
    const dialog = await openPicker(page), original = await dialog.elementHandle()
    if (!original) throw new Error('Expected mounted invitation picker.')
    await dialog.getByLabel('Tìm tài khoản', { exact: true }).fill('v2_candidate_00')
    await dialog.getByRole('radio', { name: /v2_candidate_00/ }).check()
    await dialog.getByLabel('Vai trò tổ chức', { exact: true }).selectOption('ADMIN')
    let writes = 0
    page.on('request', (request) => { if (request.method() === 'POST' && new URL(request.url()).pathname === createPath) writes += 1 })
    const refresh = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/me/' && response.request().method() === 'GET')
    await page.evaluate(() => window.dispatchEvent(new Event('focus')))
    expect((await refresh).status()).toBe(200)
    expect(await original.evaluate((element) => element.isConnected && element === document.querySelector('dialog[open]'))).toBe(true)
    for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
      await page.setViewportSize(size)
      await expect(dialog.getByLabel('Tìm tài khoản', { exact: true })).toHaveValue('v2_candidate_00')
      await expect(dialog.getByRole('radio', { name: /v2_candidate_00/ })).toBeChecked()
      await expect(dialog.getByLabel('Vai trò tổ chức', { exact: true })).toHaveValue('ADMIN')
      await dialog.getByLabel('Tìm tài khoản', { exact: true }).focus()
      await expect(dialog.getByLabel('Tìm tài khoản', { exact: true })).toBeFocused()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()).violations.map((item) => item.id)).toEqual([])
      await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `members-v2-${size.width}.png`), animations: 'disabled', caret: 'hide' })
    }
    expect(writes).toBe(0)
    // Chrome's search input may consume Escape as its native clear action.
    // Exercise dialog cancellation from a non-search control, keeping the
    // selected account, role and draft assertions above intact.
    await dialog.getByRole('button', { name: 'Đóng', exact: true }).focus()
    await expect(dialog.getByRole('button', { name: 'Đóng', exact: true })).toBeFocused()
    await expect(dialog.getByLabel('Tìm tài khoản', { exact: true })).toHaveValue('v2_candidate_00')
    await page.keyboard.press('Escape'); await expect(dialog).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'Thêm thành viên', exact: true })).toBeFocused()
    await page.goto(`/profiles/${profileId}/workspaces/${currentWorkspace}/tasks`)
    await page.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
    const task = page.getByRole('dialog', { name: 'Tạo công việc', exact: true })
    await task.getByLabel('Tên công việc', { exact: true }).fill('Unsent task draft')
    const identity = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/me/')
    await page.evaluate(() => window.dispatchEvent(new Event('focus')))
    expect((await identity).status()).toBe(200); await expect(task.getByLabel('Tên công việc', { exact: true })).toHaveValue('Unsent task draft')
    await page.keyboard.press('Escape')
    const secret = consumeLegacyInvitation(); await logout(page); await login(page, 'legacy')
    await page.goto('/invitations/respond'); await enterSecret(page, 'Mã lời mời', secret)
    const legacy = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/invitations/accept/' && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Chấp nhận lời mời', exact: true }).click()
    const response = await legacy
    expect(response.status()).toBe(200)
    expect((response.request().postDataJSON() as { token: string }).token === secret).toBe(true)
    expect(page.url().includes(secret)).toBe(false)
    await expect(page.getByRole('heading', { name: 'Đã tham gia tổ chức', exact: true })).toBeVisible()
    expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([])
  })
})

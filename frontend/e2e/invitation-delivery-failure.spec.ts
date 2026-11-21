import { expect, test, type Page } from '@playwright/test'
import { createPath, csrf, fixtureId, invite, invitationRow, login, logout, managerPath, profileId, readInvitations } from './invitation-v2-helpers'
import type { Invitation } from './invitation-v2-helpers'

test.describe('Invitation delivery — durable Web invitation and isolated fake transport', () => {
  test.describe.configure({ mode: 'serial' })
  let issued: Invitation, count = 0
  const errors = new WeakMap<Page, string[]>()
  test.beforeEach(({ page }) => {
    const failures: string[] = []; errors.set(page, failures)
    page.on('pageerror', (error) => failures.push(error.name))
    page.on('response', (response) => { if (response.status() >= 500) failures.push(`Unexpected HTTP ${response.status()}`) })
  })
  test.afterEach(({ page }) => { expect(errors.get(page)).toEqual([]) })

  test('fake SMTP failure returns201 with a durable visible FAILED Web invitation; duplicate create conflicts', async ({ page }) => {
    await login(page, 'owner'); count = (await readInvitations(page)).count
    let creates = 0
    page.on('request', (request) => { if (request.method() === 'POST' && new URL(request.url()).pathname === createPath) creates += 1 })
    issued = await invite(page, 'retry')
    expect(issued).toMatchObject({ recipient_email: null, status: 'PENDING', delivery_status: 'FAILED' })
    await expect(page.getByText(/Đã tạo lời mời trên Web\. Email chưa gửi được/)).toBeVisible()
    await expect(invitationRow(page, issued)).toContainText('Gửi email chưa thành công')
    await page.reload(); await expect(invitationRow(page, issued)).toContainText('Gửi email chưa thành công')
    expect((await readInvitations(page)).count).toBe(count + 1)
    // Negative API probe, distinct from the real create UI action. The picker
    // itself disables pending recipients, and no automatic resubmission occurs.
    const duplicate = await page.request.post(createPath, { headers: await csrf(page), data: { recipient_user_id: fixtureId('invitation_v2_retry'), requested_role: 'MEMBER' } })
    expect(duplicate.status()).toBe(409)
    expect((await readInvitations(page)).count).toBe(count + 1)
    expect(creates).toBe(1)
  })

  test('explicit retry keeps ID/expiry/count; a separately failed email cannot prevent Web acceptance', async ({ page }) => {
    test.setTimeout(60_000)
    await login(page, 'owner'); await page.goto(managerPath)
    const row = invitationRow(page, issued)
    await expect(row).toContainText('Gửi email chưa thành công')
    const resent = page.waitForResponse((response) => new URL(response.url()).pathname === `${createPath}${issued.id}/resend/` && response.request().method() === 'POST')
    await row.getByRole('button', { name: 'Thử gửi lại email', exact: true }).click()
    const response = await resent
    expect(response.status()).toBe(200); expect(response.request().postDataJSON()).toEqual({})
    expect(await response.json()).toMatchObject({ id: issued.id, expires_at: issued.expires_at, requested_role: issued.requested_role, status: 'PENDING', delivery_status: 'SENT' })
    expect((await readInvitations(page)).count).toBe(count + 1)
    await expect(row).toContainText('Hệ thống email đã tiếp nhận')
    const failed = await invite(page, 'failed')
    expect(failed.delivery_status).toBe('FAILED')
    await logout(page); await login(page, 'failed'); await page.goto(`/invitations/${failed.id}`)
    const accepted = page.waitForResponse((item) => new URL(item.url()).pathname === `/api/v1/invitations/${failed.id}/accept/` && item.request().method() === 'POST')
    await page.getByRole('button', { name: 'Chấp nhận lời mời', exact: true }).click()
    expect((await accepted).status()).toBe(200)
    await expect(page.getByRole('link', { name: 'Đến tổ chức', exact: true })).toBeVisible()
    expect((await (await page.request.get('/api/v1/profiles/')).json() as { results: { id: string }[] }).results.map((item) => item.id)).toEqual([profileId])
    await expect(page.getByLabel('Mã lời mời', { exact: true })).toHaveCount(0)
  })
})

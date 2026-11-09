import { execFileSync } from 'node:child_process'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated onboarding launcher.')
  return value
}
const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Invalid isolated run identity.')
const firstName = 'Tổ chức đầu tiên Integration'
const secondName = 'Tổ chức tiếp theo Integration'
const workspaceName = 'Không gian đầu tiên Integration'
type Profile = { id: string; name: string; status: string }
type ProfilePage = { count: number; results: Profile[] }
type Workspace = { id: string; profile_id: string; name: string }

// Keep fixture passwords out of Playwright fill-call diagnostics on failure.
async function enterPassword(page: Page) {
  try {
    await page.getByLabel('Mật khẩu', { exact: true }).evaluate((element, secret) => {
      if (!(element instanceof HTMLInputElement) || element.type !== 'password') throw new Error('Masked control required.')
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      if (!setter) throw new Error('Native input setter unavailable.')
      setter.call(element, secret)
      element.dispatchEvent(new Event('input', { bubbles: true }))
    }, required('HT_FRONTEND_TEST_PASSWORD'))
  } catch { throw new Error('Isolated masked credential entry failed.') }
}
async function login(page: Page, user: 'onboarding' | 'onboarding_security' | 'onboarding_keyboard' | 'member') {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(user === 'member' ? required('HT_FRONTEND_TEST_EMAIL') : `${user}.${runId}@example.test`)
  await enterPassword(page)
  const response = page.waitForResponse((item) => new URL(item.url()).pathname === '/api/auth/login/' && item.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await response).status()).toBe(200)
  await expect(page.locator('.account__name')).toHaveText(user === 'member' ? 'Thành viên Kiểm thử' : 'Người mới Kiểm thử')
  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { name: /^Xin chào,/ })).toBeVisible()
}
async function profiles(request: APIRequestContext): Promise<ProfilePage> {
  const response = await request.get('/api/v1/profiles/')
  expect(response.status()).toBe(200)
  return response.json() as Promise<ProfilePage>
}
async function csrf(request: APIRequestContext): Promise<string> {
  const response = await request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  return (await response.json() as { csrf_token: string }).csrf_token
}
async function logout(page: Page) {
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
  await expect(page).toHaveURL(/\/login(?:\?|$)/)
  expect((await page.request.get('/api/auth/me/')).status()).toBe(403)
  await expect(page.getByRole('button', { name: 'Mở thông báo', exact: true })).toHaveCount(0)
}
async function createProfileUI(page: Page, name: string): Promise<Profile> {
  await expect(page.getByRole('heading', { name: 'Tạo tổ chức mới', exact: true })).toBeVisible()
  await page.getByLabel(/^Tên tổ chức/).fill(name)
  const response = page.waitForResponse((item) => new URL(item.url()).pathname === '/api/v1/profiles/' && item.request().method() === 'POST')
  await page.getByRole('button', { name: 'Tạo tổ chức', exact: true }).click()
  const created = await response
  expect(created.status()).toBe(201)
  expect(created.request().postDataJSON()).toEqual({ name })
  expect(Boolean(created.request().headers()['x-csrftoken'])).toBe(true)
  const profile = await created.json() as Profile
  expect(profile.name).toBe(name)
  expect(profile.status).toBe('ACTIVE')
  await expect(page).toHaveURL(`/profiles/${profile.id}/workspaces`)
  await expect(page.getByRole('button', { name: 'Tạo không gian', exact: true })).toBeVisible()
  return profile
}

test('first-time user creates a Profile and Workspace through React, selects another Profile and preserves cross-user privacy', async ({ page }) => {
  test.setTimeout(120_000)
  const failures: string[] = []
  page.on('pageerror', (error) => failures.push(error.name))
  page.on('response', (response) => { if (response.status() >= 500) failures.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })

  // Only these synthetic Users are seeded. All successful Profile/Workspace
  // business mutations in this journey occur via React, never API-driven setup.
  await login(page, 'onboarding')
  expect((await profiles(page.request)).count).toBe(0)
  await expect(page.getByRole('heading', { name: 'Bạn chưa có tổ chức nào', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Tạo tổ chức', exact: true }).click()
  await expect(page).toHaveURL('/profiles/new')
  await page.getByRole('button', { name: 'Tạo tổ chức', exact: true }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByLabel(/^Tên tổ chức/)).toHaveAttribute('aria-invalid', 'true')
  expect((await profiles(page.request)).count).toBe(0)

  const first = await createProfileUI(page, firstName)
  expect((await profiles(page.request)).results.map((item) => item.id)).toEqual([first.id])
  expect((await page.request.get(`/api/v1/profiles/${first.id}/`)).status()).toBe(200)
  await expect(page.getByText('Tổ chức đã được tạo. Tạo không gian làm việc đầu tiên để bắt đầu.', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: 'Tạo không gian', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Tạo không gian làm việc', exact: true })
  await dialog.getByLabel('Tên không gian', { exact: true }).fill(workspaceName)
  await dialog.getByLabel('Tháng làm việc', { exact: true }).fill('2027-03')
  const createdWorkspace = page.waitForResponse((item) => new URL(item.url()).pathname === `/api/v1/profiles/${first.id}/workspaces/` && item.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Tạo không gian', exact: true }).click()
  const workspaceResponse = await createdWorkspace
  expect(workspaceResponse.status()).toBe(201)
  const workspace = await workspaceResponse.json() as Workspace
  expect(workspace.profile_id).toBe(first.id)
  await expect(dialog).not.toBeVisible()
  const workspaceLink = page.getByRole('link').filter({ has: page.getByRole('heading', { name: workspaceName, exact: true }) })
  await expect(workspaceLink).toBeVisible()
  await page.reload()
  await expect(page).toHaveURL(`/profiles/${first.id}/workspaces`)
  await expect(workspaceLink).toBeVisible()
  await workspaceLink.click()
  await page.getByRole('link', { name: 'Xem công việc', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Tạo công việc', exact: true })).toBeVisible()

  await page.goto('/profiles')
  await page.getByRole('link', { name: 'Tạo tổ chức', exact: true }).click()
  const second = await createProfileUI(page, secondName)
  expect(second.id).not.toBe(first.id)
  await page.goto('/profiles')
  for (const name of [firstName, secondName]) {
    await expect(page.getByRole('link').filter({ has: page.getByRole('heading', { name, exact: true }) })).toBeVisible()
  }
  await page.getByRole('link').filter({ has: page.getByRole('heading', { name: firstName, exact: true }) }).click()
  await expect(page).toHaveURL(`/profiles/${first.id}`)
  await expect(page.getByRole('heading', { name: firstName, exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: firstName, exact: true })).toBeVisible()
  await logout(page)

  await login(page, 'member')
  await page.goto('/profiles')
  await expect(page.getByRole('heading', { name: firstName, exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: secondName, exact: true })).toHaveCount(0)
  const accessible = await profiles(page.request)
  expect(accessible.count).toBe(1)
  expect(accessible.results.some((profile) => profile.id === first.id || profile.id === second.id)).toBe(false)
  expect((await page.request.get(`/api/v1/profiles/${first.id}/`)).status()).toBe(404)
  expect((await page.request.get(`/api/v1/profiles/${first.id}/workspaces/${workspace.id}/`)).status()).toBe(404)
  await page.goto(`/profiles/${first.id}/workspaces`)
  await expect(page.getByRole('heading', { name: firstName, exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: workspaceName, exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Tạo không gian', exact: true })).toHaveCount(0)
  await logout(page)
  expect(failures).toEqual([])
})

test('onboarding keeps anonymous, CSRF, mass-assignment and expired-session boundaries closed', async ({ page }) => {
  await page.goto('/profiles/new')
  await expect(page).toHaveURL(/\/login(?:\?|$)/)
  expect((await page.request.post('/api/v1/profiles/', { data: { name: 'Rejected anonymous onboarding' } })).status()).toBe(403)
  await login(page, 'onboarding_security')
  expect((await profiles(page.request)).count).toBe(0)
  expect((await page.request.post('/api/v1/profiles/', { data: { name: 'Rejected missing CSRF onboarding' } })).status()).toBe(403)
  const headers = { 'X-CSRFToken': await csrf(page.request) }
  for (const data of [
    { name: 'Rejected Owner injection', owner: '00000000-0000-0000-0000-000000000001' },
    { name: 'Rejected role injection', role: 'OWNER' },
    { name: 'Rejected status injection', status: 'ARCHIVED' },
  ]) {
    expect((await page.request.post('/api/v1/profiles/', { headers, data })).status()).toBe(400)
  }
  expect((await profiles(page.request)).count).toBe(0)
  await page.goto('/profiles/new')
  await page.getByLabel(/^Tên tổ chức/).fill('Must not be created after session expiry')
  const container = required('HT_FRONTEND_TEST_BACKEND_CONTAINER')
  if (container !== `ht-fe-${runId}-backend`) throw new Error('Unexpected isolated backend identity.')
  try {
    const output = execFileSync('docker', ['exec', container, 'python', '/workspace/scripts/frontend_integration.py', 'expire-sessions'], { encoding: 'utf8', timeout: 15_000, stdio: ['ignore', 'pipe', 'pipe'] })
    expect(output.trim()).toBe('OWNED_ISOLATED_SESSIONS_EXPIRED')
  } catch { throw new Error('Owned isolated session expiry failed.') }
  await page.getByRole('button', { name: 'Tạo tổ chức', exact: true }).click()
  await expect(page).toHaveURL(/\/login(?:\?|$)/)
  await expect(page.getByRole('heading', { name: 'Tạo tổ chức mới', exact: true })).toHaveCount(0)
  expect((await page.request.get('/api/auth/me/')).status()).toBe(403)
  await login(page, 'onboarding_security')
  expect((await profiles(page.request)).count).toBe(0)
})

test('zero-Profile onboarding and creation form remain accessible by keyboard and across four viewports', async ({ page }) => {
  test.setTimeout(120_000)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await login(page, 'onboarding_keyboard')
  const verify = async (surface: string, width: number) => {
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
    expect(result.violations.map((item) => ({ id: item.id, targets: item.nodes.map((node) => node.target) }))).toEqual([])
    await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `onboarding-${surface}-${width}.png`), fullPage: true })
  }
  for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
    await page.setViewportSize(size)
    await page.goto('/profiles')
    await expect(page.getByRole('heading', { name: 'Bạn chưa có tổ chức nào', exact: true })).toBeVisible()
    await verify('empty', size.width)
    const create = page.getByRole('link', { name: 'Tạo tổ chức', exact: true })
    await create.focus()
    await expect(create).toBeFocused()
    await create.press('Enter')
    await expect(page).toHaveURL('/profiles/new')
    await expect(page.getByRole('heading', { name: 'Tạo tổ chức mới', exact: true })).toBeVisible()
    const name = page.getByLabel(/^Tên tổ chức/)
    let reachedName = false
    for (let step = 0; step < 16; step++) {
      await page.keyboard.press('Tab')
      if (await name.evaluate((element) => element === document.activeElement)) { reachedName = true; break }
    }
    expect(reachedName).toBe(true)
    await expect(name).toBeFocused()
    await page.getByRole('button', { name: 'Tạo tổ chức', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(name).toHaveAttribute('aria-invalid', 'true')
    await verify('form-errors', size.width)
  }
  expect((await profiles(page.request)).count).toBe(0)
})


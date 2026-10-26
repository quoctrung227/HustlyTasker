import { execFileSync } from 'node:child_process'
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

// UUID5 matches the Python fixture factory; only synthetic non-secret IDs.
function fixtureId(label: string): string {
  const hash = createHash('sha1').update(Buffer.from(runId, 'hex')).update(label, 'utf8').digest()
  hash[6] = (hash.readUInt8(6) & 0x0f) | 0x50
  hash[8] = (hash.readUInt8(8) & 0x3f) | 0x80
  const hex = hash.subarray(0, 16).toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

const profileId = fixtureId('profile')
const workspaceId = fixtureId('workspace')
const otherProfileId = fixtureId('other_profile')
const hiddenWorkspaceId = fixtureId('hidden_workspace')
const membershipId = fixtureId('membership')
const workspacePath = `/api/v1/profiles/${profileId}/workspaces/`
const profileName = 'Studio Integration'
const workspaceName = 'Workspace Integration'

async function csrf(request: APIRequestContext): Promise<string> {
  const response = await request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  const data = await response.json() as { csrf_token: string }
  expect(typeof data.csrf_token).toBe('string')
  return data.csrf_token
}

async function login(request: APIRequestContext, owner = false): Promise<void> {
  const token = await csrf(request)
  const response = await request.post('/api/auth/login/', {
    headers: { 'X-CSRFToken': token },
    data: {
      email: required(owner ? 'HT_FRONTEND_TEST_OWNER_EMAIL' : 'HT_FRONTEND_TEST_EMAIL'),
      password: required('HT_FRONTEND_TEST_PASSWORD'),
    },
  })
  expect(response.status()).toBe(200)
}

async function loginUI(page: Page, destination = '/dashboard'): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(required('HT_FRONTEND_TEST_EMAIL'))
  await page.getByLabel('Mật khẩu', { exact: true }).fill(required('HT_FRONTEND_TEST_PASSWORD'))
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  await expect.poll(() => new URL(page.url()).pathname).toBe(destination)
}

test.describe('Real Django/PostgreSQL integration — no mocked API responses', () => {
  test('real CSRF, session login rotation, invalid credentials, current user and logout', async ({ request }) => {
    expect((await request.get('/api/health/')).status()).toBe(200)
    expect((await request.get('/api/auth/me/')).status()).toBe(403)
    const token = await csrf(request)
    const credentials = {
      email: required('HT_FRONTEND_TEST_EMAIL'), password: required('HT_FRONTEND_TEST_PASSWORD'),
    }
    expect((await request.post('/api/auth/login/', { data: credentials })).status()).toBe(403)
    expect((await request.post('/api/auth/login/', {
      headers: { 'X-CSRFToken': token }, data: { ...credentials, password: 'invalid-isolated-attempt' },
    })).status()).toBe(400)
    expect((await request.post('/api/auth/login/', {
      headers: { 'X-CSRFToken': token }, data: credentials,
    })).status()).toBe(200)
    const me = await request.get('/api/auth/me/')
    expect(me.status()).toBe(200)
    expect((await me.json() as { user: { email: string } }).user.email).toBe(credentials.email)
    // django_login rotates the CSRF secret; replaying the pre-login proof fails.
    expect((await request.post('/api/auth/logout/', { headers: { 'X-CSRFToken': token } })).status()).toBe(403)
    const rotated = await csrf(request)
    expect((await request.post('/api/auth/logout/', { headers: { 'X-CSRFToken': rotated } })).status()).toBe(204)
    expect((await request.get('/api/auth/me/')).status()).toBe(403)
  })

  test('real paginated Profile/Workspace reads preserve canonical tenant scope', async ({ request }) => {
    await login(request)
    const profiles = await request.get('/api/v1/profiles/?page_size=1')
    expect(profiles.status()).toBe(200)
    const profilePage = await profiles.json() as { count: number; results: { id: string }[] }
    expect(profilePage.count).toBe(1)
    expect(profilePage.results[0]?.id).toBe(profileId)
    expect((await request.get(`/api/v1/profiles/${profileId}/`)).status()).toBe(200)
    expect((await request.get(`/api/v1/profiles/${otherProfileId}/`)).status()).toBe(404)
    const workspaces = await request.get(workspacePath)
    expect(workspaces.status()).toBe(200)
    const page = await workspaces.json() as { count: number; results: { id: string; status: string }[] }
    expect(page.count).toBe(2)
    expect(page.results.some((item) => item.id === hiddenWorkspaceId)).toBe(false)
    expect(page.results.some((item) => item.status === 'ARCHIVED')).toBe(true)
    expect((await request.get(`${workspacePath}${workspaceId}/`)).status()).toBe(200)
    expect((await request.get(`${workspacePath}${hiddenWorkspaceId}/`)).status()).toBe(404)
    expect((await request.get(`/api/v1/profiles/${otherProfileId}/workspaces/${workspaceId}/`)).status()).toBe(404)
  })

  test('browser login, read-only pages and logout use actual session cookies', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (error) => errors.push(error.name))
    await page.goto('/profiles')
    await expect(page).toHaveURL(/\/login(?:\?|$)/)
    // A protected-route login intentionally returns to the requested local URL.
    await loginUI(page, '/profiles')
    await page.goto('/profiles')
    await expect(page.getByText(profileName, { exact: true }).first()).toBeVisible()
    await page.goto(`/profiles/${profileId}`)
    await expect(page.getByRole('heading', { name: profileName, exact: true })).toBeVisible()
    await page.goto(`/profiles/${profileId}/workspaces`)
    await expect(page.getByText(workspaceName, { exact: true }).first()).toBeVisible()
    await page.goto(`/profiles/${profileId}/workspaces/${workspaceId}`)
    await expect(page.getByRole('heading', { name: workspaceName, exact: true })).toBeVisible()
    const cookies = await page.context().cookies()
    expect(cookies.some((cookie) => cookie.name === 'sessionid' && cookie.httpOnly)).toBe(true)
    expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([])
    await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
    await expect(page).toHaveURL(/\/login(?:\?|$)/)
    await expect(page.getByText(workspaceName, { exact: true })).toHaveCount(0)
    await expect(page).toHaveTitle('Đăng nhập · HustlyTasker')
    expect((await page.request.get('/api/auth/me/')).status()).toBe(403)
    expect(errors).toEqual([])
  })

  test('real responsive surfaces preserve keyboard access, contrast and readable layout', async ({ page }) => {
    test.setTimeout(90_000)
    const screenshotDir = required('HT_FRONTEND_SCREENSHOT_DIR')
    await page.emulateMedia({ reducedMotion: 'reduce' })
    const sizes = [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 812, height: 375 }, { width: 1440, height: 1000 }]
    const verifySurface = async (surface: string, width: number): Promise<void> => {
      const dimensions = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth, viewport: window.innerWidth,
      }))
      expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.viewport)
      const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
      expect(a11y.violations.map((violation) => ({
        id: violation.id, impact: violation.impact, targets: violation.nodes.map((node) => node.target),
      }))).toEqual([])
      const passwords = page.locator('input[type="password"]')
      const containsPassword = await passwords.evaluateAll((inputs) => inputs.some((input) => (input as HTMLInputElement).value.length > 0))
      await page.screenshot({
        path: join(screenshotDir, `${surface}-${width}.png`), fullPage: true,
        mask: [...(containsPassword ? [passwords] : []), page.getByText(required('HT_FRONTEND_TEST_EMAIL'), { exact: true })],
      })
    }
    for (const size of sizes) {
      await page.setViewportSize(size)
      await page.goto('/login')
      await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible()
      await page.keyboard.press('Tab')
      const focused = page.locator(':focus')
      await expect(focused).toBeVisible()
      expect(await focused.evaluate((element) => {
        const style = getComputedStyle(element)
        const box = element.getBoundingClientRect()
        return parseFloat(style.outlineWidth) >= 2 && style.outlineStyle !== 'none'
          && box.x >= 0 && box.y >= 0 && box.right <= innerWidth && box.bottom <= innerHeight
      })).toBe(true)
      await verifySurface('login', size.width)
    }
    await loginUI(page)
    for (const size of sizes) {
      await page.setViewportSize(size)
      await page.goto('/dashboard')
      await expect(page.getByRole('main')).toBeVisible()
      await expect(page.getByText(profileName, { exact: true }).first()).toBeVisible()
      await verifySurface('dashboard', size.width)
      if (size.width === 375) {
        await page.getByRole('button', { name: 'Mở menu', exact: true }).click()
        await expect(page.getByRole('dialog')).toBeVisible()
        await verifySurface('dashboard-menu', size.width)
        await page.keyboard.press('Escape')
        await expect(page.getByRole('dialog')).not.toBeVisible()
        await expect(page.getByRole('button', { name: 'Mở menu', exact: true })).toBeFocused()
      }
      await page.goto(`/profiles/${profileId}/workspaces/${workspaceId}`)
      await expect(page.getByRole('heading', { name: workspaceName, exact: true })).toBeVisible()
      await verifySurface('workspace', size.width)
    }
  })

  test('expired real session clears mounted private UI on focus revalidation', async ({ page }) => {
    await loginUI(page)
    await page.goto(`/profiles/${profileId}/workspaces/${workspaceId}`)
    await expect(page.getByRole('heading', { name: workspaceName, exact: true })).toBeVisible()
    const container = required('HT_FRONTEND_TEST_BACKEND_CONTAINER')
    if (container !== `ht-fe-${runId}-backend`) throw new Error('Invalid owned integration backend identity.')
    const output = execFileSync('docker', [
      'exec', container, 'python', '/workspace/scripts/frontend_integration.py', 'expire-sessions',
    ], { encoding: 'utf8', timeout: 15_000 })
    expect(output.trim()).toBe('OWNED_ISOLATED_SESSIONS_EXPIRED')
    await page.evaluate(() => window.dispatchEvent(new Event('focus')))
    await expect(page).toHaveURL(/\/login(?:\?|$)/)
    await expect(page.getByText(workspaceName, { exact: true })).toHaveCount(0)
    await expect(page).toHaveTitle('Đăng nhập · HustlyTasker')
  })

  test('revoked Workspace access is denied by real backend without leaking its target', async ({ playwright, page }) => {
    await loginUI(page)
    await page.goto(`/profiles/${profileId}/workspaces/${workspaceId}`)
    await expect(page.getByRole('heading', { name: workspaceName, exact: true })).toBeVisible()
    const manager = await playwright.request.newContext({ baseURL: 'http://127.0.0.1:5173' })
    try {
      await login(manager, true)
      const token = await csrf(manager)
      expect((await manager.delete(`${workspacePath}${workspaceId}/members/${membershipId}/`, {
        headers: { 'X-CSRFToken': token },
      })).status()).toBe(204)
    } finally { await manager.dispose() }
    expect((await page.request.get(`${workspacePath}${workspaceId}/`)).status()).toBe(404)
    await page.reload()
    await expect(page.getByRole('heading', { name: workspaceName, exact: true })).toHaveCount(0)
    await expect(page.getByRole('main')).toBeVisible()
    expect((await page.request.get('/api/auth/me/')).status()).toBe(200)
  })
})

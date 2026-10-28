import { execFileSync } from 'node:child_process'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated account-security launcher.')
  return value
}
const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Invalid isolated run identity.')
const email = `acceptance.${runId}@example.test`
const originalPassword = required('HT_FRONTEND_TEST_PASSWORD')
const newPassword = `${originalPassword}Next`

/** Avoid Playwright fill-call diagnostics containing a credential on failure. */
async function enterSecret(page: Page, label: string, value: string) {
  try {
    const input = page.getByLabel(label, { exact: true })
    await input.evaluate((element, secret) => {
      if (!(element instanceof HTMLInputElement) || element.type !== 'password') throw new Error('Masked secret control required.')
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      if (!setter) throw new Error('Native value setter unavailable.')
      setter.call(element, secret)
      element.dispatchEvent(new Event('input', { bubbles: true }))
    }, value)
  } catch { throw new Error('Masked credential entry failed.') }
}
/** No token in CLI argv, host files, HTTP bridge, URLs or test output. */
function consumeMail(purpose: 'verification' | 'password-reset'): string {
  const container = required('HT_FRONTEND_TEST_BACKEND_CONTAINER')
  if (container !== `ht-fe-${runId}-backend`) throw new Error('Unexpected isolated backend identity.')
  try {
    const token = execFileSync('docker', ['exec', container, 'python', '/workspace/scripts/frontend_integration.py', 'consume-test-mail', 'registered', purpose], { encoding: 'utf8', timeout: 15_000, stdio: ['ignore', 'pipe', 'pipe'] }).trim()
    if (!/^[A-Za-z0-9_-]{43}$/.test(token)) throw new Error('Invalid isolated mail result.')
    return token
  } catch { throw new Error('Delivered isolated mail could not be consumed.') }
}
async function csrf(request: APIRequestContext): Promise<string> {
  const response = await request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  return (await response.json() as { csrf_token: string }).csrf_token
}
async function login(page: Page, password: string, expected = 200) {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await enterSecret(page, 'Mật khẩu', password)
  const response = page.waitForResponse((item) => new URL(item.url()).pathname === '/api/auth/login/' && item.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await response).status()).toBe(expected)
  if (expected === 200) await expect(page).toHaveURL('/dashboard')
  else await expect(page.getByRole('alert')).toBeVisible()
}
async function verifyEmptyForm(page: Page, path: string, heading: string) {
  await page.goto(path)
  await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible()
  for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
    await page.setViewportSize(size)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
    expect(result.violations.map((item) => ({ id: item.id, targets: item.nodes.map((node) => node.target) }))).toEqual([])
    await page.screenshot({ path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `account${path.replaceAll('/', '-')}-${size.width}.png`), fullPage: true })
  }
  await page.setViewportSize({ width: 1440, height: 1000 })
}

test('real account UI registers, verifies delivered mail, resets password and expires an existing session', async ({ page, browser }) => {
  test.setTimeout(180_000)
  const failures: string[] = []
  const watch = (target: Page) => {
    target.on('pageerror', (error) => failures.push(error.name))
    target.on('response', (response) => { if (response.status() >= 500) failures.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`) })
  }
  watch(page)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await verifyEmptyForm(page, '/forgot-password', 'Quên mật khẩu')
  await verifyEmptyForm(page, '/reset-password', 'Đặt lại mật khẩu')
  await verifyEmptyForm(page, '/register', 'Đăng ký tài khoản')

  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Tên đăng nhập', { exact: true }).fill('acceptance_registered')
  await page.getByLabel('Tên (không bắt buộc)', { exact: true }).fill('Tài khoản')
  await page.getByLabel('Họ (không bắt buộc)', { exact: true }).fill('Kiểm thử')
  await enterSecret(page, 'Mật khẩu', originalPassword)
  await enterSecret(page, 'Xác nhận mật khẩu', originalPassword)
  const registered = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/register/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click()
  expect((await registered).status()).toBe(201)
  await expect(page.getByText(/Tài khoản đã được tạo\./)).toBeVisible()
  expect((await page.request.get('/api/auth/me/')).status()).toBe(403)
  await expect(page).toHaveURL('/register')

  await login(page, originalPassword)
  await expect(page.getByText('Chưa có tổ chức nào', { exact: true })).toBeVisible()
  await page.getByRole('navigation', { name: 'Điều hướng chính', exact: true }).getByRole('link', { name: 'Tài khoản', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Tài khoản', exact: true })).toBeVisible()
  await expect(page.getByText('Email chưa được xác minh. Bạn vẫn có thể sử dụng các quyền hiện có.', { exact: true })).toBeVisible()
  expect((await page.request.post('/api/auth/email-verification/request/', { data: {} })).status()).toBe(403)
  const verificationRequest = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/email-verification/request/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Gửi mã xác minh', exact: true }).click()
  expect((await verificationRequest).status()).toBe(202)
  const verificationToken = consumeMail('verification')
  await enterSecret(page, 'Mã xác minh', verificationToken)
  const verified = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/email-verification/confirm/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Xác nhận email', exact: true }).click()
  expect((await verified).status()).toBe(200)
  await expect(page.getByText('Email đã được xác minh.', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Mã xác minh', { exact: true })).toHaveCount(0)
  // Negative replay is an API assertion, not a replacement for the UI success.
  expect((await page.request.post('/api/auth/email-verification/confirm/', { headers: { 'X-CSRFToken': await csrf(page.request) }, data: { token: verificationToken } })).status()).toBe(400)

  const staleContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' })
  const stalePage = await staleContext.newPage()
  watch(stalePage)
  try {
    await login(stalePage, originalPassword)
    await stalePage.getByRole('navigation', { name: 'Điều hướng chính', exact: true }).getByRole('link', { name: 'Tài khoản', exact: true }).click()
    await expect(stalePage.getByText('Email đã được xác minh.', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
    await expect(page).toHaveURL(/\/login(?:\?|$)/)
    await page.getByRole('link', { name: 'Quên mật khẩu?', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Quên mật khẩu', exact: true })).toBeVisible()
    expect((await page.request.post('/api/auth/password-reset/request/', { data: { email } })).status()).toBe(403)

    const requestReset = async (recipient: string) => {
      await page.getByLabel('Email', { exact: true }).fill(recipient)
      const response = page.waitForResponse((item) => new URL(item.url()).pathname === '/api/auth/password-reset/request/' && item.request().method() === 'POST')
      await page.getByRole('button', { name: 'Yêu cầu mã khôi phục', exact: true }).click()
      const accepted = await response
      expect(accepted.status()).toBe(202)
      await expect(page.getByText(/Nếu tài khoản đủ điều kiện tồn tại/)).toBeVisible()
      return accepted.json() as Promise<{ detail: string }>
    }
    const unknown = await requestReset(`unknown.${runId}@example.test`)
    const known = await requestReset(email)
    expect(Object.keys(known)).toEqual(['detail'])
    expect(known).toEqual(unknown)
    const resetToken = consumeMail('password-reset')
    await page.getByRole('link', { name: 'Tôi đã có mã khôi phục', exact: true }).click()
    await enterSecret(page, 'Mã khôi phục', resetToken)
    await enterSecret(page, 'Mật khẩu mới', newPassword)
    await enterSecret(page, 'Xác nhận mật khẩu mới', newPassword)
    const reset = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/password-reset/confirm/' && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Lưu mật khẩu mới', exact: true }).click()
    expect((await reset).status()).toBe(204)
    await expect(page.getByText(/Mật khẩu đã được đặt lại\./)).toBeVisible()
    await expect(page.getByLabel('Mã khôi phục', { exact: true })).toHaveCount(0)
    expect((await page.request.get('/api/auth/me/')).status()).toBe(403)
    await expect(page).toHaveURL('/reset-password')

    // Real old-session hash invalidation, observed by mounted protected UI.
    await stalePage.evaluate(() => window.dispatchEvent(new Event('focus')))
    await expect(stalePage).toHaveURL(/\/login(?:\?|$)/)
    await expect(stalePage.getByText(email, { exact: true })).toHaveCount(0)
    await expect(stalePage.getByRole('button', { name: 'Mở thông báo', exact: true })).toHaveCount(0)

    await page.goto('/reset-password')
    await enterSecret(page, 'Mã khôi phục', resetToken)
    await enterSecret(page, 'Mật khẩu mới', `${newPassword}Again`)
    await enterSecret(page, 'Xác nhận mật khẩu mới', `${newPassword}Again`)
    const replay = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/password-reset/confirm/' && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Lưu mật khẩu mới', exact: true }).click()
    expect((await replay).status()).toBe(400)
    await expect(page.getByRole('alert')).toBeVisible()
    // Never retain screenshots of populated credential forms, even masked.
    await login(page, originalPassword, 400)
    await login(page, newPassword)
    await page.getByRole('navigation', { name: 'Điều hướng chính', exact: true }).getByRole('link', { name: 'Tài khoản', exact: true }).click()
    await expect(page.getByText('Email đã được xác minh.', { exact: true })).toBeVisible()
    expect((await page.request.get('/api/v1/profiles/')).status()).toBe(200)
    const profiles = await page.request.get('/api/v1/profiles/')
    expect((await profiles.json() as { count: number }).count).toBe(0)
    await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
    await expect(page).toHaveURL(/\/login(?:\?|$)/)
  } finally { await staleContext.close() }
  expect(failures).toEqual([])
})

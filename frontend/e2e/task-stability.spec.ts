import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, rmdirSync, unlinkSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type ElementHandle, type Page } from '@playwright/test'

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
const taskPage = `/profiles/${profileId}/workspaces/${workspaceId}/tasks`
const apiTasks = `/api/v1/profiles/${profileId}/workspaces/${workspaceId}/tasks/`
const dialogFor = (page: Page) => page.getByRole('dialog', { name: 'Tạo công việc', exact: true })
const draft = { title: 'Stability synthetic unsaved draft', description: 'Synthetic form values remain only in this disposable browser.', priority: 'HIGH', deadline: '2027-03-06T10:30' }

function deferred<T>() {
  let resolvePromise!: (value: T) => void
  const promise = new Promise<T>((resolveValue) => { resolvePromise = resolveValue })
  return { promise, resolve: resolvePromise }
}
async function loginManager(page: Page) {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(`manager.${runId}@example.test`)
  try {
    await page.getByLabel('Mật khẩu', { exact: true }).evaluate((element, secret) => {
      if (!(element instanceof HTMLInputElement) || element.type !== 'password') throw new Error('Masked input required.')
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      if (!setter) throw new Error('Native setter unavailable.')
      setter.call(element, secret)
      element.dispatchEvent(new Event('input', { bubbles: true }))
    }, required('HT_FRONTEND_TEST_PASSWORD'))
  } catch { throw new Error('Isolated masked credential entry failed.') }
  const loggedIn = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/login/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await loggedIn).status()).toBe(200)
  await expect(page.locator('.account__name')).toHaveText('Quản lý Kiểm thử')
  await page.goto(taskPage)
  await expect(page.getByRole('heading', { name: 'Công việc', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Tạo công việc', exact: true })).toBeVisible()
}
async function openDraft(page: Page) {
  await page.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
  const dialog = dialogFor(page)
  await expect(dialog).toBeVisible()
  await dialog.getByLabel('Tên công việc', { exact: true }).fill(draft.title)
  await dialog.getByLabel('Mô tả', { exact: true }).fill(draft.description)
  await dialog.getByLabel('Ưu tiên', { exact: true }).selectOption(draft.priority)
  await dialog.getByLabel('Thời hạn', { exact: true }).fill(draft.deadline)
  return dialog
}
async function expectDraft(page: Page, original: ElementHandle<HTMLElement | SVGElement>) {
  await expect(dialogFor(page)).toBeVisible()
  // A live old node distinguishes an ordinary render from replacement/remount.
  expect(await original.evaluate((element) => element.isConnected && element === document.querySelector('dialog[open]'))).toBe(true)
  await expect(dialogFor(page).getByLabel('Tên công việc', { exact: true })).toHaveValue(draft.title)
  await expect(dialogFor(page).getByLabel('Mô tả', { exact: true })).toHaveValue(draft.description)
  await expect(dialogFor(page).getByLabel('Ưu tiên', { exact: true })).toHaveValue(draft.priority)
  await expect(dialogFor(page).getByLabel('Thời hạn', { exact: true })).toHaveValue(draft.deadline)
}
async function observeDocument(page: Page) {
  const navigations: string[] = []
  page.on('framenavigated', (frame) => { if (frame === page.mainFrame()) navigations.push(new URL(frame.url()).pathname) })
  const sentinel = await page.evaluate(() => {
    const value = crypto.randomUUID()
    ;(window as Window & { __htStabilityDocument?: string }).__htStabilityDocument = value
    return value
  })
  const original = await dialogFor(page).elementHandle()
  if (!original) throw new Error('Expected mounted task creation dialog.')
  return { original, navigations, sentinel, url: page.url() }
}
async function expectSameDocument(page: Page, observation: Awaited<ReturnType<typeof observeDocument>>) {
  expect(observation.navigations).toEqual([])
  expect(page.url()).toBe(observation.url)
  expect(await page.evaluate(() => (window as Window & { __htStabilityDocument?: string }).__htStabilityDocument)).toBe(observation.sentinel)
  await expectDraft(page, observation.original)
}
const meResponse = (page: Page) => page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/me/' && response.request().method() === 'GET')

test.describe('Task draft stability — real isolated Django/PostgreSQL', () => {
  const failures = new WeakMap<Page, string[]>()
  test.beforeEach(({ page }) => {
    const errors: string[] = []
    failures.set(page, errors)
    page.on('pageerror', (error) => errors.push(error.name))
    page.on('response', (response) => {
      if (response.status() >= 500) errors.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`)
    })
  })
  test.afterEach(({ page }) => { expect(failures.get(page)).toEqual([]) })

  test('same-user focus, visibility, sixty-second check and real Task query completion preserve one mounted draft', async ({ page }) => {
    await page.clock.install()
    await loginManager(page)
    const listReady = deferred<number>(), releaseList = deferred<void>()
    const identityReady = deferred<number>(), releaseIdentity = deferred<void>()
    let posts = 0
    page.on('request', (request) => { if (request.method() === 'POST' && new URL(request.url()).pathname === apiTasks) posts += 1 })
    // Only delivery timing changes: actual filter GET and /me responses are
    // fetched from Django, then forwarded unchanged. No fabricated API response.
    await page.route(`**${apiTasks}*`, async (route) => {
      const url = new URL(route.request().url())
      if (route.request().method() !== 'GET' || url.pathname !== apiTasks || url.searchParams.get('priority') !== 'HIGH') return route.continue()
      const actual = await route.fetch()
      listReady.resolve(actual.status())
      await releaseList.promise
      await route.fulfill({ response: actual })
    })
    try {
      await page.getByLabel('Mức ưu tiên', { exact: true }).selectOption('HIGH')
      await page.getByRole('button', { name: 'Áp dụng bộ lọc', exact: true }).click()
      expect(await listReady.promise).toBe(200)
      await openDraft(page)
      const observation = await observeDocument(page)
      const completedList = page.waitForResponse((response) => new URL(response.url()).pathname === apiTasks && response.request().method() === 'GET')
      releaseList.resolve()
      expect((await completedList).status()).toBe(200)
      await expectSameDocument(page, observation)
      await page.unroute(`**${apiTasks}*`)

      await page.route('**/api/auth/me/', async (route) => {
        const actual = await route.fetch()
        identityReady.resolve(actual.status())
        await releaseIdentity.promise
        await route.fulfill({ response: actual })
      }, { times: 1 })
      const focusCheck = meResponse(page)
      await page.evaluate(() => window.dispatchEvent(new Event('focus')))
      expect(await identityReady.promise).toBe(200)
      await expectSameDocument(page, observation)
      releaseIdentity.resolve()
      expect((await focusCheck).status()).toBe(200)
      await expectSameDocument(page, observation)

      const visibilityCheck = meResponse(page)
      await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')))
      expect((await visibilityCheck).status()).toBe(200)
      await expectSameDocument(page, observation)
      const periodicCheck = meResponse(page)
      await page.clock.fastForward(60_000)
      expect((await periodicCheck).status()).toBe(200)
      await expectSameDocument(page, observation)
      expect(posts).toBe(0)
    } finally {
      releaseList.resolve()
      releaseIdentity.resolve()
      await page.unrouteAll({ behavior: 'wait' })
    }
  })

  test('an injected transport failure keeps the draft; a real CSRF-protected retry stays pending until confirmed and creates once', async ({ page }) => {
    await loginManager(page)
    const before = await page.request.get(apiTasks)
    expect(before.status()).toBe(200)
    const beforeCount = (await before.json() as { count: number }).count
    const dialog = await openDraft(page)
    const original = await dialog.elementHandle()
    if (!original) throw new Error('Expected task form before transport injection.')
    const accepted = deferred<number>(), releaseSuccess = deferred<void>()
    let attempts = 0
    await page.route(`**${apiTasks}*`, async (route) => {
      if (route.request().method() !== 'POST' || new URL(route.request().url()).pathname !== apiTasks) return route.continue()
      attempts += 1
      // Explicit network fault injection before Django sees the first POST.
      if (attempts === 1) return route.abort('failed')
      const actual = await route.fetch()
      accepted.resolve(actual.status())
      await releaseSuccess.promise
      await route.fulfill({ response: actual })
    })
    try {
      await dialog.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
      await expect(dialog.getByText('Chưa thể lưu công việc', { exact: true })).toBeVisible()
      await expectDraft(page, original)
      const savedResponse = page.waitForResponse((response) => new URL(response.url()).pathname === apiTasks && response.request().method() === 'POST')
      await dialog.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
      expect(await accepted.promise).toBe(201)
      await expect(dialog.getByRole('button', { name: 'Tạo công việc', exact: true })).toBeDisabled()
      await expect(dialog.getByRole('button', { name: 'Hủy', exact: true })).toBeDisabled()
      await expect(dialog.getByLabel('Tên công việc', { exact: true })).toBeDisabled()
      await page.keyboard.press('Escape')
      await page.keyboard.press('Enter')
      await expectDraft(page, original)
      expect(attempts).toBe(2)
      releaseSuccess.resolve()
      const saved = await savedResponse
      expect(saved.status()).toBe(201)
      expect(Boolean(saved.request().headers()['x-csrftoken'])).toBe(true)
      const task = await saved.json() as { id: string; title: string; status: string; workspace_id: string }
      expect(task).toMatchObject({ title: draft.title, status: 'PENDING', workspace_id: workspaceId })
      await expect(dialog).not.toBeVisible()
      await expect(page.getByRole('link', { name: draft.title, exact: true })).toBeVisible()
      const after = await page.request.get(apiTasks)
      expect(after.status()).toBe(200)
      expect((await after.json() as { count: number }).count).toBe(beforeCount + 1)
      expect(attempts).toBe(2)
    } finally {
      releaseSuccess.resolve()
      await page.unrouteAll({ behavior: 'wait' })
    }
  })

  test('genuine isolated session expiry removes the private draft and requires login', async ({ page }) => {
    await loginManager(page)
    await openDraft(page)
    const container = required('HT_FRONTEND_TEST_BACKEND_CONTAINER')
    if (container !== `ht-fe-${runId}-backend`) throw new Error('Invalid owned integration backend identity.')
    const output = execFileSync('docker', [
      'exec', container, 'python', '/workspace/scripts/frontend_integration.py', 'expire-sessions',
    ], { encoding: 'utf8', timeout: 15_000 })
    expect(output.trim()).toBe('OWNED_ISOLATED_SESSIONS_EXPIRED')
    const expired = meResponse(page)
    await page.evaluate(() => window.dispatchEvent(new Event('focus')))
    expect((await expired).status()).toBe(403)
    await expect(page).toHaveURL(/\/login(?:\?|$)/)
    await expect(page.getByRole('heading', { name: /Đăng nhập vào/ })).toBeVisible()
    await expect(page.getByRole('dialog', { name: 'Tạo công việc', exact: true })).toHaveCount(0)
    await expect(page.getByLabel('Tên công việc', { exact: true })).toHaveCount(0)
    await expect(page.getByText('Team Workspace Integration', { exact: true })).toHaveCount(0)
  })

  test('unrelated self-accepted Vite HMR preserves the draft, keyboard focus and four-viewport accessibility', async ({ page }) => {
    test.setTimeout(90_000)
    const frontendRoot = fileURLToPath(new URL('../', import.meta.url))
    const artifactRoot = resolve(frontendRoot, 'playwright-report')
    const probeDirectory = resolve(artifactRoot, `ht-stability-hmr-${runId}`)
    const probeFile = join(probeDirectory, 'probe.ts')
    if (relative(artifactRoot, probeDirectory) !== `ht-stability-hmr-${runId}` || dirname(probeFile) !== probeDirectory || existsSync(probeDirectory)) {
      throw new Error('Refusing to overwrite or clean an unowned HMR probe.')
    }
    const probeUrl = `/playwright-report/ht-stability-hmr-${runId}/probe.ts`
    const updates: string[] = [], fullReloads: string[] = []
    page.on('websocket', (socket) => socket.on('framereceived', ({ payload }) => {
      try {
        const message = JSON.parse(typeof payload === 'string' ? payload : payload.toString('utf8')) as { type?: string; path?: string; updates?: { path: string }[] }
        if (message.type === 'update') updates.push(...(message.updates || []).map((entry) => entry.path))
        if (message.type === 'full-reload') fullReloads.push(message.path || '*')
      } catch { /* Non-JSON websocket frames are irrelevant to this probe. */ }
    }))
    let owned = false
    const source = (revision: number) => `export const revision = ${revision}\nconst target = window as Window & { __htStabilityHmr?: { revisions: number[] } }\nconst state = target.__htStabilityHmr ??= { revisions: [] }\nif (import.meta.hot) import.meta.hot.accept((updated) => { if (updated) state.revisions.push(updated.revision) })\n`
    try {
      mkdirSync(artifactRoot, { recursive: true })
      mkdirSync(probeDirectory)
      owned = true
      writeFileSync(probeFile, source(1), { encoding: 'utf8', flag: 'wx' })
      await page.emulateMedia({ reducedMotion: 'reduce' })
      await loginManager(page)
      await openDraft(page)
      const observation = await observeDocument(page)
      expect(await page.evaluate(async (url) => (await import(url)).revision, probeUrl)).toBe(1)
      writeFileSync(probeFile, source(2), { encoding: 'utf8', flag: 'r+' })
      await expect.poll(() => updates.some((path) => path.endsWith(`/ht-stability-hmr-${runId}/probe.ts`)), { timeout: 10_000 }).toBe(true)
      await expect.poll(() => page.evaluate(() => (window as Window & { __htStabilityHmr?: { revisions: number[] } }).__htStabilityHmr?.revisions)).toEqual([2])
      expect(fullReloads).toEqual([])
      await expectSameDocument(page, observation)
      for (const size of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 1000 }, { width: 812, height: 375 }]) {
        await page.setViewportSize(size)
        await dialogFor(page).getByLabel('Tên công việc', { exact: true }).focus()
        await expect(dialogFor(page).getByLabel('Tên công việc', { exact: true })).toBeFocused()
        await page.keyboard.press('Tab')
        await expect(dialogFor(page).getByLabel('Mô tả', { exact: true })).toBeFocused()
        await expectSameDocument(page, observation)
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
        const accessibility = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
        expect(accessibility.violations.map((violation) => violation.id)).toEqual([])
        // Capture the visible native modal without resizing the much taller
        // underlying Task list/backdrop. Keep compositor failures bounded.
        await page.screenshot({
          path: join(required('HT_FRONTEND_SCREENSHOT_DIR'), `task-stability-${size.width}.png`),
          fullPage: false, animations: 'disabled', caret: 'hide', scale: 'css', timeout: 5_000,
        })
        await expectSameDocument(page, observation)
      }
      await page.keyboard.press('Escape')
      await expect(dialogFor(page)).not.toBeVisible()
      await expect(page.getByRole('button', { name: 'Tạo công việc', exact: true })).toBeFocused()
    } finally {
      // Stop observing before removing the uniquely owned probe. Never edit or
      // restore existing runtime source, and never recursively delete a folder.
      await page.close()
      if (owned && dirname(probeFile) === probeDirectory && relative(artifactRoot, probeDirectory) === `ht-stability-hmr-${runId}`) {
        if (existsSync(probeFile)) unlinkSync(probeFile)
        rmdirSync(probeDirectory)
      }
    }
  })
})

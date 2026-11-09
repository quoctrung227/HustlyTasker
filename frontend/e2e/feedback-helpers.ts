import { execFileSync } from 'node:child_process'
import { expect, type Page } from '@playwright/test'
import { fixtureId, required, runId } from './ai-helpers'

export { csrf, fixtureId, required, runId } from './ai-helpers'
export type FeedbackActor = 'analyzer_manager' | 'analyzer_privacy' | 'analyzer_keyboard' | 'analyzer_viewer' | 'analyzer_editor'
export function feedbackScope(actor: FeedbackActor = 'analyzer_manager') {
  const group = actor === 'analyzer_viewer' || actor === 'analyzer_editor' ? 'analyzer_manager' : actor
  const profile = fixtureId(`${group}_profile`), workspace = fixtureId(`${group}_workspace`), task = fixtureId(`${group}_task`)
  const tasks = `/profiles/${profile}/workspaces/${workspace}/tasks`
  const apiTask = `/api/v1${tasks}/${task}/`
  return { group, profile, workspace, task, tasks, detail: `${tasks}/${task}`, apiTask,
    analyze: `${apiTask}ai/feedback-analysis/`, review: fixtureId(`${group}_review`), comment: fixtureId(`${group}_comment`),
    emptyDetail: `${tasks}/${fixtureId(`${group}_empty_task`)}` }
}
export async function feedbackLogin(page: Page, actor: FeedbackActor) {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(`${actor}.${runId}@example.test`)
  try {
    await page.getByLabel('Mật khẩu', { exact: true }).evaluate((element, secret) => {
      if (!(element instanceof HTMLInputElement) || element.type !== 'password') throw new Error('Masked input required')
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      if (!setter) throw new Error('Native input setter unavailable')
      setter.call(element, secret); element.dispatchEvent(new Event('input', { bubbles: true }))
    }, required('HT_FRONTEND_TEST_PASSWORD'))
  } catch { throw new Error('Isolated masked credential entry failed') }
  const response = page.waitForResponse((item) => new URL(item.url()).pathname === '/api/auth/login/' && item.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await response).status()).toBe(200)
  // Authentication may correctly restore a protected return-to Task URL.
  // Start the explicit navigation fixture from the Dashboard afterward.
  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { name: /^Xin chào,/ })).toBeVisible()
}
export async function feedbackNavigate(page: Page, actor: FeedbackActor = 'analyzer_manager') {
  const context = feedbackScope(actor)
  await page.getByRole('navigation', { name: 'Điều hướng chính', exact: true }).getByRole('link', { name: 'Tổ chức', exact: true }).click()
  await page.getByRole('link').filter({ has: page.getByRole('heading', { name: `Feedback ${context.group} Integration`, exact: true }) }).click()
  await page.getByRole('link').filter({ has: page.getByRole('heading', { name: `Feedback ${context.group} Workspace`, exact: true }) }).click()
  await page.getByRole('link', { name: 'Xem công việc', exact: true }).click()
  await page.getByRole('link', { name: `Feedback ${context.group} Task`, exact: true }).click()
  await expect(page).toHaveURL(context.detail)
}
export async function feedbackOpen(page: Page) {
  const panel = page.getByRole('region', { name: 'Phân tích phản hồi', exact: true })
  await panel.getByRole('button', { name: 'Phân tích phản hồi', exact: true }).click()
  await expect(panel.getByRole('checkbox', { name: 'Chọn Đánh giá bản nộp 1', exact: true })).toBeVisible()
  return panel
}
/** Container-local bridge verifies cluster/database ownership before every read. */
export function feedbackState(): unknown {
  const container = required('HT_FRONTEND_TEST_BACKEND_CONTAINER')
  if (container !== `ht-fe-${runId}-backend`) throw new Error('Unexpected isolated backend identity')
  try {
    const raw = execFileSync('docker', ['exec', container, 'python', '/workspace/scripts/frontend_integration.py', 'feedback-state'], { encoding: 'utf8', timeout: 15_000, stdio: ['ignore', 'pipe', 'pipe'] })
    return JSON.parse(raw)
  } catch { throw new Error('Owned isolated state fingerprint unavailable') }
}
export function feedbackExpireSessions() {
  const container = required('HT_FRONTEND_TEST_BACKEND_CONTAINER')
  if (container !== `ht-fe-${runId}-backend`) throw new Error('Unexpected isolated backend identity')
  try {
    const raw = execFileSync('docker', ['exec', container, 'python', '/workspace/scripts/frontend_integration.py', 'expire-sessions'], { encoding: 'utf8', timeout: 15_000, stdio: ['ignore', 'pipe', 'pipe'] })
    expect(raw.trim()).toBe('OWNED_ISOLATED_SESSIONS_EXPIRED')
  } catch { throw new Error('Owned isolated session-expiry setup failed') }
}

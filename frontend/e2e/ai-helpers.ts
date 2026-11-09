import { createHash } from 'node:crypto'
import { expect, type APIRequestContext, type Page } from '@playwright/test'

export function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error('Use the owned isolated AI browser launcher.')
  return value
}
export const runId = required('HT_FRONTEND_TEST_RUN_ID')
if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Invalid isolated run identity.')
export function fixtureId(label: string): string {
  const hash = createHash('sha1').update(Buffer.from(runId, 'hex')).update(label, 'utf8').digest()
  hash[6] = (hash.readUInt8(6) & 0x0f) | 0x50
  hash[8] = (hash.readUInt8(8) & 0x3f) | 0x80
  const hex = hash.subarray(0, 16).toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
export type Actor = 'ai_manager' | 'ai_recovery' | 'ai_keyboard' | 'ai_peer' | 'ai_viewer'
export function scope(actor: Actor = 'ai_manager') {
  const owner = actor === 'ai_peer' || actor === 'ai_viewer' ? 'ai_manager' : actor
  const profileId = fixtureId(`${owner}_profile`), workspaceId = fixtureId(`${owner}_workspace`)
  return { profileId, workspaceId, tasks: `/profiles/${profileId}/workspaces/${workspaceId}/tasks`,
    apiTasks: `/api/v1/profiles/${profileId}/workspaces/${workspaceId}/tasks/`,
    apiAi: `/api/v1/profiles/${profileId}/workspaces/${workspaceId}/ai/task-proposals/` }
}
export async function login(page: Page, actor: Actor) {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(`${actor}.${runId}@example.test`)
  try {
    await page.getByLabel('Mật khẩu', { exact: true }).evaluate((element, secret) => {
      if (!(element instanceof HTMLInputElement) || element.type !== 'password') throw new Error('Masked control required.')
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
      if (!setter) throw new Error('Native setter unavailable.')
      setter.call(element, secret)
      element.dispatchEvent(new Event('input', { bubbles: true }))
    }, required('HT_FRONTEND_TEST_PASSWORD'))
  } catch { throw new Error('Isolated masked credential entry failed.') }
  const loggedIn = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/login/' && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await loggedIn).status()).toBe(200)
  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { name: /^Xin chào,/ })).toBeVisible()
}
export async function openTasksFromNavigation(page: Page, actor: Actor = 'ai_manager') {
  const owner = actor === 'ai_peer' || actor === 'ai_viewer' ? 'ai_manager' : actor
  await page.getByRole('navigation', { name: 'Điều hướng chính', exact: true }).getByRole('link', { name: 'Tổ chức', exact: true }).click()
  await page.getByRole('link').filter({ has: page.getByRole('heading', { name: `AI ${owner} Integration`, exact: true }) }).click()
  await page.getByRole('link').filter({ has: page.getByRole('heading', { name: `AI ${owner} Workspace`, exact: true }) }).click()
  await page.getByRole('link', { name: 'Xem công việc', exact: true }).click()
  await expect(page).toHaveURL(scope(actor).tasks)
}
export async function countTasks(request: APIRequestContext, actor: Actor = 'ai_manager') {
  const response = await request.get(scope(actor).apiTasks)
  expect(response.status()).toBe(200)
  return (await response.json() as { count: number }).count
}
export async function csrf(request: APIRequestContext) {
  const response = await request.get('/api/auth/csrf/')
  expect(response.status()).toBe(200)
  return (await response.json() as { csrf_token: string }).csrf_token
}
export async function generateUI(page: Page, actor: Actor, brief: string) {
  await page.getByRole('link', { name: 'Tạo công việc bằng AI', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Tạo công việc bằng AI', exact: true, level: 1 })).toBeVisible()
  await expect(page.getByText('Bản mô phỏng — không phải AI thật', { exact: true })).toBeVisible()
  await page.getByLabel('Mẫu đề xuất', { exact: true }).selectOption('task-tree-v1')
  await page.getByLabel('Mô tả yêu cầu giả lập', { exact: true }).fill(brief)
  const generated = page.waitForResponse((response) => new URL(response.url()).pathname === scope(actor).apiAi && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Đề xuất công việc', exact: true }).click()
  const response = await generated
  expect(response.status()).toBe(201)
  expect(response.request().postDataJSON()).toEqual({ scenario_id: 'task-tree-v1', brief })
  expect(Boolean(response.request().headers()['x-csrftoken'])).toBe(true)
  const proposal = await response.json() as { proposal_id: string; status: string; mode: string; generated_by_ai: boolean; payload: { tasks: { local_ref: string; parent_ref: string | null }[] } }
  expect(proposal.status).toBe('AVAILABLE')
  expect(proposal.mode).toBe('fixture_demo')
  expect(proposal.generated_by_ai).toBe(false)
  expect(JSON.stringify(proposal)).not.toContain(brief)
  expect(proposal.payload.tasks).toHaveLength(2)
  await expect(page).toHaveURL(`${scope(actor).tasks}/generate?proposal=${proposal.proposal_id}`)
  await expect(page.getByLabel('Tên công việc 1', { exact: true })).toBeVisible()
  return proposal
}


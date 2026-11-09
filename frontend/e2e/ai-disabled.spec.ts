import { expect, test } from '@playwright/test'
import { countTasks, login, openTasksFromNavigation, scope } from './ai-helpers'

test('disabled fixture remains honest and unavailable while manual Task creation still works', async ({ page }) => {
  await login(page, 'ai_manager')
  await openTasksFromNavigation(page)
  const metadata = await page.request.fetch(scope().apiAi, { method: 'OPTIONS' })
  expect(metadata.status()).toBe(200)
  const value = await metadata.json() as { ai: { enabled: boolean; mode: string; generated_by_ai: boolean } }
  expect(value.ai).toMatchObject({ enabled: false, mode: 'fixture_demo', generated_by_ai: false })
  await expect(page.getByRole('button', { name: 'Tạo công việc bằng AI', exact: true })).toBeDisabled()
  await expect(page.getByRole('link', { name: 'Tạo công việc bằng AI', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Tạo công việc', exact: true })).toBeVisible()
  expect(await countTasks(page.request)).toBe(0)
  await page.goto(`${scope().tasks}/generate`)
  await expect(page.getByText('Bản mô phỏng chưa khả dụng', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Đề xuất công việc', exact: true })).toHaveCount(0)
  await expect(page.getByLabel('Mô tả yêu cầu giả lập', { exact: true })).toHaveCount(0)
  expect(await countTasks(page.request)).toBe(0)
  await page.getByRole('link', { name: 'Về danh sách công việc', exact: true }).click()
  await page.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Tạo công việc', exact: true })
  await dialog.getByLabel('Tên công việc', { exact: true }).fill('Manual task with AI disabled Integration')
  await dialog.getByRole('button', { name: 'Tạo công việc', exact: true }).click()
  await expect(dialog).not.toBeVisible()
  await expect(page.getByRole('link', { name: 'Manual task with AI disabled Integration', exact: true })).toBeVisible()
  expect(await countTasks(page.request)).toBe(1)
})


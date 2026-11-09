import { expect, test } from '@playwright/test'
import { feedbackLogin, feedbackNavigate, feedbackScope, feedbackState } from './feedback-helpers'

test('disabled fixture is honest, makes no Analyze POST and preserves ordinary Review/Comment context', async ({ page }) => {
  await feedbackLogin(page, 'analyzer_manager')
  await feedbackNavigate(page)
  const before = feedbackState(), requests: string[] = []
  page.on('request', (request) => { if (request.method() === 'POST') requests.push(new URL(request.url()).pathname) })
  const panel = page.getByRole('region', { name: 'Phân tích phản hồi', exact: true })
  await expect(panel.getByRole('button', { name: 'Phân tích phản hồi', exact: true })).toBeDisabled()
  await expect(panel.getByText('Bản mô phỏng chưa khả dụng', { exact: true })).toBeVisible()
  await expect(panel.getByRole('checkbox')).toHaveCount(0)
  await expect(panel.getByRole('heading', { name: 'Kết quả mô phỏng', exact: true })).toHaveCount(0)
  expect(requests).not.toContain(feedbackScope().analyze)
  await expect(page.getByText('ANALYZER_SYNTHETIC_REVIEW: kiểm tra phụ đề trong ví dụ giả lập.', { exact: true })).toBeVisible()
  expect(feedbackState()).toEqual(before)
})

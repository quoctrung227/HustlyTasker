import { expect, type Locator } from '@playwright/test'

/** Exercise the controlled Vietnamese/24h UI, never a hidden datetime input. */
export async function fillTaskDeadline(scope: Locator, value: string) {
  if (!value) {
    await scope.getByRole('button', { name: 'Xóa thời hạn', exact: true }).click()
    return
  }
  const parts = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value)
  if (!parts) throw new Error('Minute-precision local test date required.')
  await scope.getByLabel('Ngày (dd/mm/yyyy)', { exact: true }).fill(`${parts[3]}/${parts[2]}/${parts[1]}`)
  await scope.getByLabel('Giờ (00–23)', { exact: true }).selectOption(parts[4] ?? '')
  await scope.getByLabel('Phút (00–59)', { exact: true }).selectOption(parts[5] ?? '')
}

export async function expectTaskDeadline(scope: Locator, value: string) {
  const parts = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value)
  if (!parts) throw new Error('Minute-precision local test date required.')
  await expect(scope.getByLabel('Ngày (dd/mm/yyyy)', { exact: true })).toHaveValue(`${parts[3]}/${parts[2]}/${parts[1]}`)
  await expect(scope.getByLabel('Giờ (00–23)', { exact: true })).toHaveValue(parts[4] ?? '')
  await expect(scope.getByLabel('Phút (00–59)', { exact: true })).toHaveValue(parts[5] ?? '')
}

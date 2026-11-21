/** Preserve the decimal entered by the user without binary floating-point rounding. */
export function parseEstimatedHoursInput(value: string): string | null | undefined {
  const input = value.trim()
  if (!input) return null
  const match = /^(\d{1,4})(?:[.,](\d{1,2}))?$/.exec(input)
  if (!match) return undefined
  const whole = Number(match[1])
  const fraction = (match[2] ?? '').padEnd(2, '0')
  const hundredths = whole * 100 + Number(fraction)
  if (hundredths < 1 || hundredths > 100_000) return undefined
  return `${whole}.${fraction}`
}

export function isEstimatedHours(value: unknown): value is string {
  return typeof value === 'string' && parseEstimatedHoursInput(value) === value
}

const hoursFormat = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 })

export function formatEstimatedHours(value: string | number): string {
  return `${hoursFormat.format(Number(value))} giờ`
}

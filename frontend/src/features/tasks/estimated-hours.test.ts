import { expect, it } from 'vitest'
import { isEstimatedHours, parseEstimatedHoursInput } from './estimated-hours'

it('validates nullable hundredths and normalizes decimal input without rounding', () => {
  for (const [input, expected] of [['', null], ['  ', null], ['0,01', '0.01'], ['1000.00', '1000.00'], ['3,2', '3.20'], ['3', '3.00']] as const) {
    expect(parseEstimatedHoursInput(input)).toBe(expected)
  }
  for (const input of ['-1', '0', '1000.01', '0.001', '3,251', '1e2', '12:30', 'text']) {
    expect(parseEstimatedHoursInput(input)).toBeUndefined()
  }
  expect(isEstimatedHours('3.20')).toBe(true)
  expect(isEstimatedHours('3,20')).toBe(false)
  expect(isEstimatedHours('3.2')).toBe(false)
})

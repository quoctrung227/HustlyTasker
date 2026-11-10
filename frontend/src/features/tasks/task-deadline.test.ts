import { describe, expect, it } from 'vitest'
import { calendarDate, calendarWeekday, canonicalTaskDate, deadlineDraft, deadlineInputValue, formatMinuteDeadline, formatVietnameseDeadline, isCanonicalTaskDate, parseMinuteDeadline, shiftCalendarDate, taskDateInputValue, taskDateText } from './task-deadline'

describe('Vietnamese calendar input and invalid local draft', () => {
  it('converts exact dd/mm/yyyy to canonical date without locale inference', () => {
    expect(taskDateInputValue('10/11/2026')).toBe('2026-11-10')
    expect(taskDateText('2026-11-10')).toBe('10/11/2026')
    expect(taskDateInputValue('')).toBe('')
    expect(taskDateText('')).toBe('')
    expect(taskDateInputValue('29/02/2024')).toBe('2024-02-29')
  })
  it.each(['1', '10/', '31/02/2026', '29/02/2026', '01/13/2026', '00/11/2026', '10/11/0000', '2026-11-10', '10/11/10000'])('keeps invalid/partial date %s nonempty and unsendable', (value) => {
    const draft = taskDateInputValue(value)
    expect(draft).not.toBe('')
    expect(taskDateText(draft)).toBe(value)
    expect(isCanonicalTaskDate(draft)).toBe(false)
    expect(() => parseMinuteDeadline(`${draft}T18:30`)).toThrow(TypeError)
  })
  it('retains incomplete individual parts through a controlled parent rerender', () => {
    const incomplete = { date: '10/11/', hour: '18', minute: '' }
    const encoded = deadlineInputValue(incomplete)
    expect(deadlineDraft(encoded)).toEqual(incomplete)
    expect(() => parseMinuteDeadline(encoded)).toThrow(TypeError)
    expect(deadlineInputValue({ date: '', hour: '', minute: '' })).toBe('')
    expect(deadlineInputValue({ date: '10/11/2026', hour: '18', minute: '30' })).toBe('2026-11-10T18:30')
  })
  it('bounds Gregorian dates and calendar navigation without rolling invalid days', () => {
    expect(calendarDate('2026-02-30')).toBeNull()
    expect(calendarDate('0001-01-01')).toEqual({ year: 1, month: 1, day: 1 })
    expect(canonicalTaskDate({ year: 1, month: 1, day: 1 })).toBe('0001-01-01')
    expect(shiftCalendarDate({ year: 1, month: 1, day: 1 }, -1)).toBeNull()
    expect(shiftCalendarDate({ year: 9999, month: 12, day: 31 }, 1)).toBeNull()
    expect(shiftCalendarDate({ year: 2026, month: 11, day: 30 }, 1)).toEqual({ year: 2026, month: 12, day: 1 })
    expect(calendarWeekday({ year: 2026, month: 11, day: 2 })).toBe(0)
  })
})

describe('Task minute-precision timezone conversion', () => {
  it('uses existing device timezone, floors only display precision, and emits UTC', () => {
    const original = '2026-11-10T11:30:15.987Z'
    const local = formatMinuteDeadline(original)
    expect(local).toMatch(/^2026-11-\d{2}T\d{2}:\d{2}$/)
    const expected = new Date(original)
    expected.setSeconds(0, 0)
    expect(parseMinuteDeadline(local)).toBe(expected.toISOString())
    expect(formatMinuteDeadline(null)).toBe('')
    expect(parseMinuteDeadline('')).toBeNull()
  })
  it.each(['2026-11-10T00:00', '2026-11-10T23:59'])('retains valid clock boundary %s', (value) => {
    expect(formatMinuteDeadline(parseMinuteDeadline(value))).toBe(value)
    expect(parseMinuteDeadline(value)).toMatch(/:00\.000Z$/)
  })
  it.each(['2026-02-30T18:30', '2026-11-10T24:00', '2026-11-10T18:60', '0000-01-01T18:30', '10000-01-01T18:30', '2026-11-10T18:30:10', '2026-11-10T18:30:00.000', '2026-11-10T18:30Z', 'not-date'])('rejects invalid/minute-contract input %s', (value) => {
    expect(() => parseMinuteDeadline(value)).toThrow(TypeError)
  })
  it('formats an explicit dd/mm/yyyy 24-hour clock without seconds or AM/PM', () => {
    const result = formatVietnameseDeadline('2026-11-10T11:30:15.987Z')
    expect(result).toMatch(/^\d{2}\/\d{2}\/2026 (?:[01]\d|2[0-3]):[0-5]\d$/)
    expect(result).not.toMatch(/AM|PM|:\d{2}:/)
    expect(formatVietnameseDeadline(null)).toBe('')
    expect(formatVietnameseDeadline('not-date')).toBe('')
  })
  it('rejects a real DST gap without changing the existing local timezone policy', () => {
    const previous = process.env.TZ
    try {
      process.env.TZ = 'America/New_York'
      expect(new Date('2026-03-08T07:30:00Z').getHours()).toBe(3)
      expect(() => parseMinuteDeadline('2026-03-08T02:30')).toThrow(TypeError)
      expect(parseMinuteDeadline('2026-03-08T01:30')).toBe('2026-03-08T06:30:00.000Z')
      expect(parseMinuteDeadline('2026-03-08T03:30')).toBe('2026-03-08T07:30:00.000Z')
    } finally {
      if (previous === undefined) delete process.env.TZ
      else process.env.TZ = previous
    }
  })
  it('rejects UTC overflow at year boundaries even when the local calendar is valid', () => {
    const previous = process.env.TZ
    try {
      process.env.TZ = 'Asia/Ho_Chi_Minh'
      expect(() => parseMinuteDeadline('0001-01-01T00:00')).toThrow(TypeError)
      process.env.TZ = 'America/Los_Angeles'
      expect(() => parseMinuteDeadline('9999-12-31T23:59')).toThrow(TypeError)
    } finally {
      if (previous === undefined) delete process.env.TZ
      else process.env.TZ = previous
    }
  })
})

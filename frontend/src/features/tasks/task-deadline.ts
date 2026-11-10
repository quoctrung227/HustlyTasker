/** Task form dates use the device timezone; API instants remain explicit UTC. */
export type TaskCalendarDate = { year: number; month: number; day: number }
export type TaskDeadlineDraft = { date: string; hour: string; minute: string }

const pad = (value: number, length = 2) => String(value).padStart(length, '0')

export function calendarDate(value: string): TaskCalendarDate | null {
  const parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!parts) return null
  const year = Number(parts[1]), month = Number(parts[2]), day = Number(parts[3])
  if (year < 1 || year > 9999 || month < 1 || month > 12 || day < 1 || day > 31) return null
  const date = new Date(0)
  date.setUTCFullYear(year, month - 1, day)
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null
  return { year, month, day }
}

export function canonicalTaskDate(value: TaskCalendarDate): string {
  return `${pad(value.year, 4)}-${pad(value.month)}-${pad(value.day)}`
}

export function isCanonicalTaskDate(value: string): boolean {
  return calendarDate(value) !== null
}

export function taskDateText(value: string): string {
  const date = calendarDate(value)
  if (date) return `${pad(date.day)}/${pad(date.month)}/${pad(date.year, 4)}`
  return value.startsWith('!') ? value.slice(1) : value
}

/** Invalid/partial text stays nonempty local state and can never become API null. */
export function taskDateInputValue(text: string): string {
  if (!text) return ''
  const parts = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(text)
  const value = parts ? `${parts[3]}-${parts[2]}-${parts[1]}` : ''
  return value && isCanonicalTaskDate(value) ? value : `!${text}`
}

export function deadlineDraft(value: string): TaskDeadlineDraft {
  if (!value) return { date: '', hour: '', minute: '' }
  const parts = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})$/.exec(value)
  if (parts?.[1] && parts[2] && parts[3]) return { date: taskDateText(parts[1]), hour: parts[2], minute: parts[3] }
  if (value.startsWith('!')) {
    try {
      const draft: unknown = JSON.parse(value.slice(1))
      if (draft && typeof draft === 'object' && 'date' in draft && typeof draft.date === 'string' &&
        'hour' in draft && typeof draft.hour === 'string' && 'minute' in draft && typeof draft.minute === 'string') {
        return { date: draft.date, hour: draft.hour, minute: draft.minute }
      }
    } catch { /* A malformed local draft remains invalid instead of becoming null. */ }
  }
  return { date: value, hour: '', minute: '' }
}

export function deadlineInputValue(draft: TaskDeadlineDraft): string {
  if (!draft.date && !draft.hour && !draft.minute) return ''
  const date = taskDateInputValue(draft.date)
  if (isCanonicalTaskDate(date) && /^(?:[01]\d|2[0-3])$/.test(draft.hour) && /^[0-5]\d$/.test(draft.minute)) {
    return `${date}T${draft.hour}:${draft.minute}`
  }
  return `!${JSON.stringify(draft)}`
}

export function parseMinuteDeadline(value: string): string | null {
  if (!value) return null
  const parts = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})$/.exec(value)
  const date = parts?.[1] ? calendarDate(parts[1]) : null
  if (!date || !parts || parts[2] === undefined || parts[3] === undefined) throw new TypeError('Invalid local minute deadline.')
  const hour = Number(parts[2]), minute = Number(parts[3])
  if (hour > 23 || minute > 59) throw new TypeError('Invalid local minute deadline.')
  const instant = new Date(0)
  instant.setFullYear(date.year, date.month - 1, date.day)
  instant.setHours(hour, minute, 0, 0)
  // JavaScript rolls invalid calendar/DST-gap times forward; reject that change.
  if (instant.getFullYear() !== date.year || instant.getMonth() !== date.month - 1 || instant.getDate() !== date.day ||
    instant.getHours() !== hour || instant.getMinutes() !== minute || instant.getUTCFullYear() < 1 || instant.getUTCFullYear() > 9999) {
    throw new TypeError('Invalid local minute deadline.')
  }
  return instant.toISOString()
}

export function formatMinuteDeadline(value: string | null): string {
  if (value === null) return ''
  const instant = new Date(value)
  if (Number.isNaN(instant.getTime()) || instant.getFullYear() < 1 || instant.getFullYear() > 9999) return ''
  return `${pad(instant.getFullYear(), 4)}-${pad(instant.getMonth() + 1)}-${pad(instant.getDate())}T${pad(instant.getHours())}:${pad(instant.getMinutes())}`
}

export function formatVietnameseDeadline(value: string | null): string {
  const local = formatMinuteDeadline(value)
  if (!local) return ''
  const [date = '', clock = ''] = local.split('T')
  return `${taskDateText(date)} ${clock}`
}

export function shiftCalendarDate(date: TaskCalendarDate, days: number): TaskCalendarDate | null {
  const instant = new Date(0)
  instant.setUTCFullYear(date.year, date.month - 1, date.day + days)
  const result = { year: instant.getUTCFullYear(), month: instant.getUTCMonth() + 1, day: instant.getUTCDate() }
  return result.year < 1 || result.year > 9999 ? null : result
}

export function calendarWeekday(date: TaskCalendarDate): number {
  const instant = new Date(0)
  instant.setUTCFullYear(date.year, date.month - 1, date.day)
  return (instant.getUTCDay() + 6) % 7
}

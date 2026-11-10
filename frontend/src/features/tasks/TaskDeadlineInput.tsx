import { useEffect, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { CaretLeftIcon, CaretRightIcon } from '@phosphor-icons/react'
import { Button, Input } from '../../components/ui'
import { calendarDate, calendarWeekday, canonicalTaskDate, deadlineDraft, deadlineInputValue, isCanonicalTaskDate, shiftCalendarDate, taskDateInputValue, taskDateText } from './task-deadline'
import type { TaskCalendarDate } from './task-deadline'
import './TaskDeadlineInput.css'

type DateInputProps = {
  id: string; value: string; onChange: (value: string) => void
  label?: string; disabled?: boolean; error?: string; hint?: string
}
const weekdays = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật']
const shortWeekdays = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
const months = Array.from({ length: 12 }, (_, index) => index + 1)

function currentDate(): TaskCalendarDate {
  const today = new Date()
  return { year: today.getFullYear(), month: today.getMonth() + 1, day: today.getDate() }
}

function calendarMonth(date: TaskCalendarDate, offset: number): TaskCalendarDate | null {
  const index = (date.year - 1) * 12 + date.month - 1 + offset
  if (index < 0 || index >= 9999 * 12) return null
  return { year: Math.floor(index / 12) + 1, month: index % 12 + 1, day: 1 }
}

/** A locale-controlled date field with an optional keyboard-operable VI calendar. */
export function TaskDateInput({ id, value, onChange, label = 'Ngày', disabled = false, error, hint }: DateInputProps) {
  const selected = calendarDate(value)
  const [view, setView] = useState<TaskCalendarDate>(() => selected ?? currentDate())
  const [open, setOpen] = useState(false)
  const [focused, setFocused] = useState(value)
  const focusRequested = useRef(false)
  const input = useRef<HTMLInputElement>(null)
  const summary = useRef<HTMLElement>(null)
  const dayButtons = useRef(new Map<string, HTMLButtonElement>())
  useEffect(() => {
    const date = calendarDate(value)
    if (date) { setView(date); setFocused(value) }
  }, [value])
  useEffect(() => {
    if (disabled) setOpen(false)
  }, [disabled])
  useEffect(() => {
    if (open && focusRequested.current) {
      dayButtons.current.get(focused)?.focus()
      focusRequested.current = false
    }
  }, [open, focused])
  const first = { ...view, day: 1 }
  const firstWeekday = calendarWeekday(first)
  const nextMonth = calendarMonth(first, 1)
  const dayCount = nextMonth ? shiftCalendarDate(nextMonth, -1)?.day ?? 31 : 31
  const cells = Array.from({ length: Math.ceil((firstWeekday + dayCount) / 7) * 7 }, (_, index) => {
    const day = index - firstWeekday + 1
    return day > 0 && day <= dayCount ? day : null
  })
  const weeks = Array.from({ length: cells.length / 7 }, (_, row) => cells.slice(row * 7, row * 7 + 7))
  const focusDate = calendarDate(focused)
  const roving = focusDate?.year === view.year && focusDate.month === view.month ? focused : canonicalTaskDate(first)
  const description = [hint ? `${id}-hint` : '', error ? `${id}-error` : ''].filter(Boolean).join(' ') || undefined

  function choose(date: TaskCalendarDate) {
    onChange(canonicalTaskDate(date))
    setOpen(false)
    input.current?.focus()
  }
  function moveMonth(offset: number) {
    const target = calendarMonth(view, offset)
    if (target) { setView(target); setFocused(canonicalTaskDate(target)) }
  }
  function dayKey(event: KeyboardEvent<HTMLButtonElement>, date: TaskCalendarDate) {
    let target: TaskCalendarDate | null = null
    if (event.key === 'ArrowLeft') target = shiftCalendarDate(date, -1)
    else if (event.key === 'ArrowRight') target = shiftCalendarDate(date, 1)
    else if (event.key === 'ArrowUp') target = shiftCalendarDate(date, -7)
    else if (event.key === 'ArrowDown') target = shiftCalendarDate(date, 7)
    else if (event.key === 'Home') target = shiftCalendarDate(date, -calendarWeekday(date))
    else if (event.key === 'End') target = shiftCalendarDate(date, 6 - calendarWeekday(date))
    else if (event.key === 'PageUp') target = calendarMonth(date, -1)
    else if (event.key === 'PageDown') target = calendarMonth(date, 1)
    else return
    event.preventDefault()
    if (target) { focusRequested.current = true; setView(target); setFocused(canonicalTaskDate(target)) }
  }

  return <div className={`field task-date-field${error ? ' field--invalid' : ''}`}>
    <label className="field__label" htmlFor={id}>{label}</label>
    <Input ref={input} id={id} value={taskDateText(value)} inputMode="numeric" placeholder="dd/mm/yyyy" maxLength={10} autoComplete="off"
      disabled={disabled} onChange={(event) => onChange(taskDateInputValue(event.target.value))}
      aria-invalid={error ? true : undefined} aria-describedby={description} />
    {hint && <p className="field__hint" id={`${id}-hint`}>{hint}</p>}
    {error && <p className="field__error" id={`${id}-error`}>{error}</p>}
    {disabled ? <p className="field__hint task-date-calendar-disabled">Chọn ngày từ lịch</p> : <details className="task-date-calendar" open={open} onToggle={(event) => setOpen(event.currentTarget.open)} onKeyDown={(event) => {
      if (event.key === 'Escape' && open) { event.preventDefault(); event.stopPropagation(); setOpen(false); summary.current?.focus() }
    }}>
      <summary ref={summary} aria-label={`Mở lịch cho ${label}`}>Chọn ngày từ lịch</summary>
      {open && <div className="task-calendar-panel">
        <div className="task-calendar-controls">
          <Button variant="secondary" disabled={disabled || !calendarMonth(view, -1)} aria-label="Tháng trước" onClick={() => moveMonth(-1)} icon={<CaretLeftIcon size={18} aria-hidden="true" />} />
          <div className="task-calendar-period">
            <label htmlFor={`${id}-calendar-month`}>Tháng trên lịch<select id={`${id}-calendar-month`} aria-label="Tháng trên lịch" className="input" value={view.month} disabled={disabled} onChange={(event) => { const next = { ...view, month: Number(event.target.value), day: 1 }; setView(next); setFocused(canonicalTaskDate(next)) }}>
              {months.map((month) => <option value={month} key={month}>Tháng {month}</option>)}
            </select></label>
            <label htmlFor={`${id}-calendar-year`}>Năm trên lịch<Input id={`${id}-calendar-year`} aria-label="Năm trên lịch" type="number" min={1} max={9999} step={1} value={view.year} disabled={disabled} onChange={(event) => {
              const year = Number(event.target.value)
              if (Number.isInteger(year) && year >= 1 && year <= 9999) { const next = { ...view, year, day: 1 }; setView(next); setFocused(canonicalTaskDate(next)) }
            }} /></label>
          </div>
          <Button variant="secondary" disabled={disabled || !nextMonth} aria-label="Tháng sau" onClick={() => moveMonth(1)} icon={<CaretRightIcon size={18} aria-hidden="true" />} />
        </div>
        <p className="task-calendar-heading" aria-live="polite" aria-atomic="true">Tháng {view.month} năm {view.year}</p>
        <table className="task-calendar-grid" aria-label={`Lịch tháng ${view.month} năm ${view.year}`}>
          <thead><tr>{weekdays.map((weekday, index) => <th scope="col" key={weekday} aria-label={weekday}><abbr title={weekday}>{shortWeekdays[index]}</abbr></th>)}</tr></thead>
          <tbody>{weeks.map((week) => <tr key={`${view.year}-${view.month}-${week.find((day) => day !== null)}`}>
            {week.map((day, column) => {
              const date = day === null ? null : { year: view.year, month: view.month, day }
              const key = date ? canonicalTaskDate(date) : `empty-${weekdays[column]}`
              return <td key={key}>{date && <button type="button" className="task-calendar-day" ref={(element) => { if (element) dayButtons.current.set(key, element); else dayButtons.current.delete(key) }}
                disabled={disabled} tabIndex={roving === key ? 0 : -1} aria-pressed={value === key} aria-label={`Ngày ${day} tháng ${view.month} năm ${view.year}`}
                onFocus={() => setFocused(key)} onClick={() => choose(date)} onKeyDown={(event) => dayKey(event, date)}>{day}</button>}</td>
            })}
          </tr>)}</tbody>
        </table>
        <Button variant="ghost" disabled={disabled} onClick={() => choose(currentDate())}>Hôm nay</Button>
        <p className="field__hint">Dùng phím mũi tên để đổi ngày, Page Up/Page Down để đổi tháng, Enter để chọn và Escape để đóng lịch.</p>
      </div>}
    </details>}
  </div>
}

/** Only day/month/year and explicit 24-hour hour/minute controls are rendered. */
export function TaskDeadlineInput({ id, value, onChange, label = 'Thời hạn', disabled = false, error,
  hint = 'Không bắt buộc. Ngày dd/mm/yyyy và giờ 24h theo múi giờ trên thiết bị; chỉ có giờ và phút.' }: DateInputProps) {
  const draft = deadlineDraft(value)
  const dateValue = taskDateInputValue(draft.date)
  const update = (field: 'date' | 'hour' | 'minute', text: string) => {
    const next = { ...draft, [field]: text }
    if (field === 'date' && isCanonicalTaskDate(taskDateInputValue(text))) { next.hour ||= '00'; next.minute ||= '00' }
    if (field === 'hour' && text) next.minute ||= '00'
    if (field === 'minute' && text) next.hour ||= '00'
    onChange(deadlineInputValue(next))
  }
  return <fieldset className={`task-deadline-field${error ? ' field--invalid' : ''}`} id={id} tabIndex={-1} disabled={disabled} aria-describedby={`${id}-hint${error ? ` ${id}-error` : ''}`}>
    <legend className="field__label">{label}</legend>
    <p className="field__hint" id={`${id}-hint`}>{hint}</p>
    <TaskDateInput id={`${id}-date`} label="Ngày (dd/mm/yyyy)" value={dateValue} disabled={disabled} onChange={(next) => update('date', taskDateText(next))} />
    <div className="task-clock-fields">
      <div className="field"><label className="field__label" htmlFor={`${id}-hour`}>Giờ (00–23)</label><select id={`${id}-hour`} className="input" value={draft.hour} disabled={disabled} aria-invalid={error ? true : undefined} aria-describedby={error ? `${id}-error` : undefined} onChange={(event) => update('hour', event.target.value)}>
        <option value="">--</option>{Array.from({ length: 24 }, (_, index) => { const number = String(index).padStart(2, '0'); return <option value={number} key={number}>{number}</option> })}
      </select></div>
      <div className="field"><label className="field__label" htmlFor={`${id}-minute`}>Phút (00–59)</label><select id={`${id}-minute`} className="input" value={draft.minute} disabled={disabled} aria-invalid={error ? true : undefined} aria-describedby={error ? `${id}-error` : undefined} onChange={(event) => update('minute', event.target.value)}>
        <option value="">--</option>{Array.from({ length: 60 }, (_, index) => { const number = String(index).padStart(2, '0'); return <option value={number} key={number}>{number}</option> })}
      </select></div>
    </div>
    {error && <p className="field__error" id={`${id}-error`}>{error}</p>}
    <Button variant="ghost" disabled={disabled || value === ''} onClick={() => onChange('')}>Xóa thời hạn</Button>
  </fieldset>
}

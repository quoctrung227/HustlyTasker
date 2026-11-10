import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { TaskDateInput, TaskDeadlineInput } from './TaskDeadlineInput'
import { parseMinuteDeadline } from './task-deadline'

function ControlledDeadline({ initial = '', disabled = false, error }: { initial?: string; disabled?: boolean; error?: string }) {
  const [value, setValue] = useState(initial)
  return <><TaskDeadlineInput id="test-deadline" value={value} onChange={setValue} disabled={disabled} error={error} /><output data-testid="value">{value}</output></>
}
function ControlledDate({ initial = '' }: { initial?: string }) {
  const [value, setValue] = useState(initial)
  return <><TaskDateInput id="filter-date" label="Thời hạn từ ngày (UTC)" value={value} onChange={setValue} /><output data-testid="value">{value}</output></>
}

describe('controlled Vietnamese date and 24h Task deadline', () => {
  it('renders only day/month/year and explicit hour/minute controls', () => {
    render(<ControlledDeadline />)
    expect(screen.getByLabelText('Ngày (dd/mm/yyyy)')).toHaveAttribute('placeholder', 'dd/mm/yyyy')
    const hours = screen.getByRole('combobox', { name: 'Giờ (00–23)' })
    const minutes = screen.getByRole('combobox', { name: 'Phút (00–59)' })
    expect(within(hours).getAllByRole('option').map((option) => option.textContent)).toEqual(['--', ...Array.from({ length: 24 }, (_, value) => String(value).padStart(2, '0'))])
    expect(within(minutes).getAllByRole('option')).toHaveLength(61)
    expect(document.querySelector('input[type="datetime-local"],input[type="time"],input[type="date"]')).toBeNull()
    expect(screen.queryByText(/AM|PM|mili giây/i)).not.toBeInTheDocument()
  })
  it('accepts18:30, retains exact Vietnamese text and clears the entire optional deadline', async () => {
    const user = userEvent.setup()
    render(<ControlledDeadline />)
    await user.type(screen.getByLabelText('Ngày (dd/mm/yyyy)'), '10/11/2026')
    await user.selectOptions(screen.getByLabelText('Giờ (00–23)'), '18')
    await user.selectOptions(screen.getByLabelText('Phút (00–59)'), '30')
    expect(screen.getByTestId('value')).toHaveTextContent('2026-11-10T18:30')
    expect(screen.getByLabelText('Ngày (dd/mm/yyyy)')).toHaveValue('10/11/2026')
    await user.click(screen.getByRole('button', { name: 'Xóa thời hạn' }))
    expect(screen.getByTestId('value')).toBeEmptyDOMElement()
    expect(screen.getByLabelText('Ngày (dd/mm/yyyy)')).toHaveValue('')
    expect(screen.getByLabelText('Giờ (00–23)')).toHaveValue('')
    expect(screen.getByLabelText('Phút (00–59)')).toHaveValue('')
  })
  it.each(['00:00', '23:59'])('reopens and edits clock boundary %s without seconds', async (clock) => {
    const user = userEvent.setup()
    render(<ControlledDeadline initial={`2026-11-10T${clock}`} />)
    expect(screen.getByLabelText('Ngày (dd/mm/yyyy)')).toHaveValue('10/11/2026')
    expect(screen.getByLabelText('Giờ (00–23)')).toHaveValue(clock.slice(0, 2))
    expect(screen.getByLabelText('Phút (00–59)')).toHaveValue(clock.slice(3))
    await user.clear(screen.getByLabelText('Ngày (dd/mm/yyyy)'))
    await user.type(screen.getByLabelText('Ngày (dd/mm/yyyy)'), '11/11/2026')
    expect(screen.getByTestId('value')).toHaveTextContent(`2026-11-11T${clock}`)
  })
  it('retains a partial/invalid date as invalid draft rather than clearing or silently saving the old time', async () => {
    const user = userEvent.setup()
    render(<ControlledDeadline initial="2026-11-10T18:30" error="Kiểm tra ngày và giờ." />)
    await user.clear(screen.getByLabelText('Ngày (dd/mm/yyyy)'))
    await user.type(screen.getByLabelText('Ngày (dd/mm/yyyy)'), '31/02/2026')
    expect(screen.getByLabelText('Ngày (dd/mm/yyyy)')).toHaveValue('31/02/2026')
    expect(() => parseMinuteDeadline(screen.getByTestId('value').textContent ?? '')).toThrow(TypeError)
    expect(screen.getByRole('group', { name: 'Thời hạn' })).toHaveAccessibleDescription(/Kiểm tra ngày và giờ/)
    expect(screen.getByLabelText('Giờ (00–23)')).toHaveAttribute('aria-invalid', 'true')
  })
  it('disables all deadline mutation controls while the form is pending', async () => {
    const user = userEvent.setup()
    render(<ControlledDeadline initial="2026-11-10T18:30" disabled />)
    expect(screen.getByLabelText('Ngày (dd/mm/yyyy)')).toBeDisabled()
    expect(screen.getByLabelText('Giờ (00–23)')).toBeDisabled()
    expect(screen.getByLabelText('Phút (00–59)')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Xóa thời hạn' })).toBeDisabled()
    await user.click(screen.getByText('Chọn ngày từ lịch'))
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByTestId('value')).toHaveTextContent('2026-11-10T18:30')
  })
})

describe('inline Vietnamese keyboard calendar', () => {
  it('chooses a date in a Vietnamese calendar and returns focus to the text input', async () => {
    const user = userEvent.setup()
    render(<ControlledDate initial="2026-11-10" />)
    await user.click(screen.getByText('Chọn ngày từ lịch'))
    const calendar = await screen.findByRole('table', { name: 'Lịch tháng 11 năm 2026' })
    expect(screen.getByRole('combobox', { name: 'Tháng trên lịch' })).toHaveValue('11')
    expect(screen.getByRole('spinbutton', { name: 'Năm trên lịch' })).toHaveValue(2026)
    expect(within(calendar).getByRole('columnheader', { name: 'Thứ Hai' })).toBeInTheDocument()
    await user.click(within(calendar).getByRole('button', { name: 'Ngày 20 tháng 11 năm 2026' }))
    expect(screen.getByLabelText('Thời hạn từ ngày (UTC)')).toHaveValue('20/11/2026')
    expect(screen.getByTestId('value')).toHaveTextContent('2026-11-20')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Thời hạn từ ngày (UTC)')).toHaveFocus()
  })
  it('supports arrow/page keyboard movement and Escape without dismissing an outer form', async () => {
    const user = userEvent.setup()
    render(<ControlledDate initial="2026-11-10" />)
    await user.click(screen.getByText('Chọn ngày từ lịch'))
    const tenth = await screen.findByRole('button', { name: 'Ngày 10 tháng 11 năm 2026' })
    tenth.focus()
    await user.keyboard('{ArrowRight}')
    expect(screen.getByRole('button', { name: 'Ngày 11 tháng 11 năm 2026' })).toHaveFocus()
    await user.keyboard('{PageDown}')
    expect(await screen.findByRole('table', { name: 'Lịch tháng 12 năm 2026' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Ngày 1 tháng 12 năm 2026' })).toHaveFocus()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByText('Chọn ngày từ lịch')).toHaveFocus()
    expect(screen.getByTestId('value')).toHaveTextContent('2026-11-10')
  })
  it('bounds navigation at first and last supported years', async () => {
    const user = userEvent.setup()
    const { unmount } = render(<ControlledDate initial="0001-01-01" />)
    await user.click(screen.getByText('Chọn ngày từ lịch'))
    expect(screen.getByRole('button', { name: 'Tháng trước' })).toBeDisabled()
    unmount()
    render(<ControlledDate initial="9999-12-31" />)
    await user.click(screen.getByText('Chọn ngày từ lịch'))
    expect(screen.getByRole('button', { name: 'Tháng sau' })).toBeDisabled()
  })
  it('exposes only Vietnamese month controls and permits direct calendar month/year changes', async () => {
    const user = userEvent.setup()
    render(<ControlledDate initial="2026-11-10" />)
    await user.click(screen.getByText('Chọn ngày từ lịch'))
    await user.selectOptions(screen.getByLabelText('Tháng trên lịch'), '2')
    fireEvent.change(screen.getByLabelText('Năm trên lịch'), { target: { value: '2024' } })
    const calendar = await screen.findByRole('table', { name: 'Lịch tháng 2 năm 2024' })
    await user.click(within(calendar).getByRole('button', { name: 'Ngày 29 tháng 2 năm 2024' }))
    expect(screen.getByLabelText('Thời hạn từ ngày (UTC)')).toHaveValue('29/02/2024')
  })
})

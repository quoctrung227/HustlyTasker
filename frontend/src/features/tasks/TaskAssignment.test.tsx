import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/api/client'
import type { Task, WorkspaceMember } from '../../services/api/work-management'
import { TaskAssign } from './TaskAssignment'

const timestamp = '2026-11-10T04:05:06.123456Z'
const task: Task = { id: 'task', workspace_id: 'workspace', parent_id: null, title: 'Task đang làm', description: null, status: 'WORKING', priority: 'MEDIUM', deadline: null, can_start: false, can_submit: false, can_assign: true, can_unassign: true,
  active_assignment: { id: 'assignment-a', profile_membership_id: 'member-a', display_name: 'Nguyễn Editor A', assigned_at: timestamp }, created_at: timestamp, updated_at: timestamp }
const member = (id: string): WorkspaceMember => ({ id, profile_membership_id: id, role: 'MEMBER', is_active: true, is_assignable: true, display_label: id === 'member-a' ? 'Nguyễn Editor A' : 'Editor B', joined_at: timestamp, updated_at: timestamp })
const originalShow = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal'), originalClose = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')
beforeAll(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.open = true } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) { this.open = false; this.dispatchEvent(new Event('close')) } })
})
afterAll(() => { if (originalShow) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', originalShow); else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal'); if (originalClose) Object.defineProperty(HTMLDialogElement.prototype, 'close', originalClose); else Reflect.deleteProperty(HTMLDialogElement.prototype, 'close') })
function setup(overrides: Partial<Parameters<typeof TaskAssign>[0]> = {}) {
  const props = { profileId: 'profile', workspaceId: 'workspace', task, canAssign: true, members: { count: 2, next: null, previous: null, results: [member('member-a'), member('member-b')] }, membersPage: 1,
    onMembersPageChange: vi.fn(), onAssign: vi.fn().mockResolvedValue({ ...task, status: 'ASSIGNED' }), onUnassign: vi.fn().mockResolvedValue({ ...task, status: 'PENDING', active_assignment: null }), onSaved: vi.fn(), onDenied: vi.fn(), ...overrides }
  return { ...render(<TaskAssign {...props} />), props }
}
async function openTransfer() { const user = userEvent.setup(); await user.click(screen.getByRole('button', { name: 'Thay đổi phân công' })); await user.selectOptions(screen.getByLabelText('Thành viên'), 'member-b'); return user }

describe('confirmed assignment handover', () => {
  it('shows the current name, excludes the current member and only submits after explicit confirmation', async () => {
    const { props } = setup()
    const user = await openTransfer()
    expect(screen.getByText('Nguyễn Editor A')).toBeVisible()
    expect(screen.queryByRole('option', { name: 'Nguyễn Editor A' })).not.toBeInTheDocument()
    await user.type(screen.getByLabelText(/Lý do chuyển giao/), 'Chuyển ca')
    await user.click(screen.getByRole('button', { name: 'Kiểm tra thay đổi' }))
    expect(screen.getByText('Chuyển Task từ Nguyễn Editor A sang Editor B?')).toBeVisible()
    expect(props.onAssign).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Xác nhận chuyển giao' }))
    expect(props.onAssign).toHaveBeenCalledExactlyOnceWith({ target_profile_membership_id: 'member-b', expected_assignment_id: 'assignment-a', expected_assigned_at: timestamp, reason: 'Chuyển ca' }, expect.any(AbortSignal))
    expect(props.onSaved).toHaveBeenCalledWith(expect.objectContaining({ status: 'ASSIGNED' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
  it.each(['ASSIGNED', 'WORKING'] as const)('unassigns %s to PENDING through a confirmed action with the precise expectation', async (status) => {
    const { props } = setup({ task: { ...task, status } })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Thay đổi phân công' }))
    await user.click(screen.getByRole('radio', { name: 'Gỡ phân công' }))
    expect(screen.queryByLabelText('Thành viên')).not.toBeInTheDocument()
    await user.type(screen.getByLabelText(/Lý do gỡ phân công/), 'Chưa chọn người thay')
    await user.click(screen.getByRole('button', { name: 'Kiểm tra thay đổi' }))
    expect(props.onUnassign).not.toHaveBeenCalled()
    expect(screen.getByText('Task chuyển về Chờ phân công. Sản phẩm, đánh giá và toàn bộ lịch sử được giữ nguyên; người cũ không còn phụ trách.')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Xác nhận gỡ phân công' }))
    expect(props.onUnassign).toHaveBeenCalledExactlyOnceWith({ expected_assignment_id: 'assignment-a', expected_assigned_at: timestamp, reason: 'Chưa chọn người thay' }, expect.any(AbortSignal))
    expect(props.onAssign).not.toHaveBeenCalled()
    expect(props.onSaved).toHaveBeenCalledWith(expect.objectContaining({ status: 'PENDING', active_assignment: null }))
  })
  it.each(['REVIEW', 'COMPLETED', 'CANCELLED'] as const)('offers no ordinary reassignment on %s', (status) => {
    setup({ task: { ...task, status } })
    expect(screen.queryByRole('button', { name: 'Thay đổi phân công' })).not.toBeInTheDocument()
  })
  it('honors an explicit negative server hint even with a manager UI capability', () => {
    setup({ task: { ...task, can_assign: false } })
    expect(screen.queryByRole('button', { name: 'Thay đổi phân công' })).not.toBeInTheDocument()
  })
  it('blocks a confirmation if a background response replaces the assignment', async () => {
    const { props, rerender } = setup()
    const user = await openTransfer()
    await user.click(screen.getByRole('button', { name: 'Kiểm tra thay đổi' }))
    if (!task.active_assignment) throw new Error('The handover fixture requires an active assignment.')
    rerender(<TaskAssign {...props} task={{ ...task, active_assignment: { ...task.active_assignment, id: 'assignment-other' } }} />)
    expect(screen.getByRole('button', { name: 'Xác nhận chuyển giao' })).toBeDisabled()
    expect(screen.getByText(/Phân công đã thay đổi trong lúc/)).toBeVisible()
    expect(props.onAssign).not.toHaveBeenCalled()
  })
  it.each([403, 404, 409, 503])('preserves drafts and blocks automatic replay after HTTP %s', async (status) => {
    const { props } = setup({ onAssign: vi.fn().mockRejectedValue(new ApiError(status, status === 409 ? 'conflict' : status === 503 ? 'server' : 'forbidden', 'Quyền hoặc phân công đã thay đổi.')) })
    const user = await openTransfer()
    await user.type(screen.getByLabelText(/Lý do chuyển giao/), 'Giữ lại bản nháp')
    await user.click(screen.getByRole('button', { name: 'Kiểm tra thay đổi' })); await user.click(screen.getByRole('button', { name: 'Xác nhận chuyển giao' }))
    expect(await screen.findByRole('alert')).toBeVisible()
    expect(screen.getByLabelText(/Lý do chuyển giao/)).toHaveValue('Giữ lại bản nháp')
    expect(screen.getByRole('button', { name: 'Kiểm tra thay đổi' })).toBeDisabled()
    expect(props.onAssign).toHaveBeenCalledOnce(); expect(props.onDenied).toHaveBeenCalledOnce()
  })
  it.each(['x'.repeat(4001), `bad${String.fromCharCode(0)}value`, '\uD800'])('rejects an invalid reason before any mutation', async (reason) => {
    const { props } = setup()
    const user = await openTransfer()
    fireEvent.change(screen.getByLabelText(/Lý do chuyển giao/), { target: { value: reason } })
    await user.click(screen.getByRole('button', { name: 'Kiểm tra thay đổi' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('4.000 ký tự Unicode hợp lệ')
    expect(props.onAssign).not.toHaveBeenCalled(); expect(props.onUnassign).not.toHaveBeenCalled()
  })
  it('guards double confirmation while a server mutation is pending', async () => {
    let resolve: ((saved: Task) => void) | undefined
    const { props } = setup({ onAssign: vi.fn().mockReturnValue(new Promise<Task>((done) => { resolve = done })) })
    const user = await openTransfer(); await user.click(screen.getByRole('button', { name: 'Kiểm tra thay đổi' }))
    const button = screen.getByRole('button', { name: 'Xác nhận chuyển giao' })
    fireEvent.click(button); fireEvent.click(button)
    expect(props.onAssign).toHaveBeenCalledOnce(); expect(button).toBeDisabled()
    await act(async () => { resolve?.(task) }); await waitFor(() => expect(props.onSaved).toHaveBeenCalledOnce())
  })
})

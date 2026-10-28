/** Component callbacks are mocked; real RBAC/session proof belongs to integration tests. */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/api/client'
import type { Task, WorkspaceMember } from '../../services/api/work-management'
import { formatLocalDeadline, parseLocalDeadline, TaskAssign, TaskCreate, TaskEdit, TaskStart } from './TaskForms'

const task: Task = { id: 'task-a', workspace_id: 'workspace-a', parent_id: null, title: 'Công việc hiện tại', description: null,
  status: 'PENDING', priority: 'MEDIUM', deadline: null, active_assignment: null, can_start: false, can_submit: false, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }
const member = (id: string, role: WorkspaceMember['role'] = 'MEMBER', is_active = true): WorkspaceMember => ({ id: `row-${id}`, profile_membership_id: id, role, is_active, display_label: `Tên ${id}`, is_assignable: role === 'MEMBER' && is_active, joined_at: task.created_at, updated_at: task.updated_at })
const showModalDescriptor = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const closeDescriptor = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')

beforeAll(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.open = true } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) { this.open = false; this.dispatchEvent(new Event('close')) } })
})
afterAll(() => {
  if (showModalDescriptor) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', showModalDescriptor)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
  if (closeDescriptor) Object.defineProperty(HTMLDialogElement.prototype, 'close', closeDescriptor)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
})

function deferred<T>() {
  let resolve: (value: T) => void = () => { throw new Error('Deferred was not initialized') }
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}
function create(overrides: Partial<Parameters<typeof TaskCreate>[0]> = {}) {
  const props = { profileId: 'profile-a', workspaceId: task.workspace_id, canCreate: true,
    onCreate: vi.fn().mockResolvedValue(task), onSaved: vi.fn(), onDenied: vi.fn(), ...overrides }
  return { ...render(<TaskCreate {...props} />), props }
}
function edit(overrides: Partial<Parameters<typeof TaskEdit>[0]> = {}) {
  const props = { profileId: 'profile-a', workspaceId: task.workspace_id, task, canEdit: true,
    onUpdate: vi.fn().mockResolvedValue(task), onSaved: vi.fn(), onDenied: vi.fn(), ...overrides }
  return { ...render(<TaskEdit {...props} />), props }
}
function assign(overrides: Partial<Parameters<typeof TaskAssign>[0]> = {}) {
  const props = { profileId: 'profile-a', workspaceId: task.workspace_id, task, canAssign: true, membersPage: 1,
    members: { count: 1, next: null, previous: null, results: [member('editor-a')] },
    onAssign: vi.fn().mockResolvedValue(task), onSaved: vi.fn(), onDenied: vi.fn(), onOpen: vi.fn(), onMembersPageChange: vi.fn(), ...overrides }
  return { ...render(<TaskAssign {...props} />), props }
}
function start(overrides: Partial<Parameters<typeof TaskStart>[0]> = {}) {
  const props = { profileId: 'profile-a', workspaceId: task.workspace_id, task: { ...task, status: 'ASSIGNED' as const, can_start: true }, active: true,
    onStart: vi.fn().mockResolvedValue({ ...task, status: 'WORKING', can_start: false }), onSaved: vi.fn(), onDenied: vi.fn(), ...overrides }
  return { ...render(<TaskStart {...props} />), props }
}

describe('local deadline conversion', () => {
  it('uses the browser-local timezone, preserves instants, and permits no deadline', () => {
    const source = '2026-10-21T10:30:15.120Z'
    expect(parseLocalDeadline(formatLocalDeadline(source))).toBe(source)
    expect(parseLocalDeadline('')).toBeNull()
    expect(formatLocalDeadline(null)).toBe('')
  })
  it.each(['0000-01-01T10:30', '10000-01-01T10:30', '2026-02-30T10:30', '2026-13-01T10:30', '2026-10-01T24:30', '2026-10-01T10:60', '2026-10-01T10:30Z', 'not-date'])('rejects invalid input %s before sending it', (value) => {
    expect(() => parseLocalDeadline(value)).toThrow(TypeError)
  })
})

describe('Task capability and scope boundaries', () => {
  it('hides creation without a proven capability', () => {
    create({ canCreate: undefined })
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
  it('hides edit for a Task in another Workspace', () => {
    edit({ workspaceId: 'another-workspace' })
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
  it.each(['REVIEW', 'COMPLETED', 'CANCELLED'] as const)('hides assignment for %s without inventing a state transition', (status) => {
    assign({ task: { ...task, status } })
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})

describe('Task creation and editing', () => {
  it('focuses the summary and links required title validation to its field', async () => {
    const { props } = create()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Tạo công việc' }))
    const dialog = screen.getByRole('dialog', { name: 'Tạo công việc' })
    await user.click(within(dialog).getByRole('button', { name: 'Tạo công việc' }))
    const alert = screen.getByRole('alert')
    expect(alert.parentElement).toHaveFocus()
    expect(screen.getByLabelText('Tên công việc')).toHaveAttribute('aria-invalid', 'true')
    await user.click(within(alert).getByRole('link', { name: 'Nhập tên công việc từ 1 đến 255 ký tự.' }))
    expect(screen.getByLabelText('Tên công việc')).toHaveFocus()
    expect(props.onCreate).not.toHaveBeenCalled()
  })
  it('creates only approved metadata with explicit local-to-UTC deadline conversion', async () => {
    const { props } = create()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Tạo công việc' }))
    const dialog = screen.getByRole('dialog', { name: 'Tạo công việc' })
    await user.type(screen.getByLabelText('Tên công việc'), '  Viết báo cáo  ')
    await user.type(screen.getByLabelText('Mô tả'), 'Nội dung cần làm')
    await user.selectOptions(screen.getByLabelText('Ưu tiên'), 'HIGH')
    fireEvent.change(screen.getByLabelText('Thời hạn'), { target: { value: '2026-10-30T15:00' } })
    await user.click(within(dialog).getByRole('button', { name: 'Tạo công việc' }))
    await waitFor(() => expect(props.onSaved).toHaveBeenCalledWith(task))
    expect(props.onCreate).toHaveBeenCalledWith({ title: 'Viết báo cáo', description: 'Nội dung cần làm', priority: 'HIGH', deadline: parseLocalDeadline('2026-10-30T15:00') }, expect.any(AbortSignal))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
  it('creates a child with its fixed parent and no implicit inherited deadline', async () => {
    const { props } = create({ fixedParentId: 'parent-a' })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Tạo công việc con' }))
    const dialog = screen.getByRole('dialog', { name: 'Tạo công việc con' })
    await user.type(screen.getByLabelText('Tên công việc'), 'Việc con')
    await user.click(within(dialog).getByRole('button', { name: 'Tạo công việc con' }))
    expect(props.onCreate).toHaveBeenCalledWith({ title: 'Việc con', description: '', priority: 'MEDIUM', deadline: null, parent_id: 'parent-a' }, expect.any(AbortSignal))
  })
  it('edits only changed metadata and sends no status, identity, parent or assignment', async () => {
    const { props } = edit()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Chỉnh sửa công việc' }))
    expect(screen.getByRole('button', { name: 'Lưu thay đổi' })).toBeDisabled()
    await user.selectOptions(screen.getByLabelText('Ưu tiên'), 'URGENT')
    await user.click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    expect(props.onUpdate).toHaveBeenCalledWith({ priority: 'URGENT' }, expect.any(AbortSignal))
  })
  it('clears a deadline explicitly without rewriting untouched fields', async () => {
    const { props } = edit({ task: { ...task, deadline: '2026-10-30T15:00:00Z' } })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Chỉnh sửa công việc' }))
    fireEvent.change(screen.getByLabelText('Thời hạn'), { target: { value: '' } })
    await user.click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    expect(props.onUpdate).toHaveBeenCalledWith({ deadline: null }, expect.any(AbortSignal))
  })
  it('retains draft values, connects safe API errors and permits explicit retry', async () => {
    const onUpdate = vi.fn().mockRejectedValueOnce(new ApiError(400, 'validation', 'Kiểm tra thông tin.', { title: 'Tên chưa hợp lệ.' })).mockResolvedValueOnce(task)
    const { props } = edit({ onUpdate })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Chỉnh sửa công việc' }))
    await user.clear(screen.getByLabelText('Tên công việc'))
    await user.type(screen.getByLabelText('Tên công việc'), 'Bản nháp mới')
    await user.click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    expect(screen.getByLabelText('Tên công việc')).toHaveValue('Bản nháp mới')
    expect(screen.getByLabelText('Tên công việc')).toHaveAccessibleDescription('Bắt buộc. Tối đa 255 ký tự. Tên chưa hợp lệ.')
    expect(props.onSaved).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    await waitFor(() => expect(props.onSaved).toHaveBeenCalledOnce())
  })
  it('does not reflect an arbitrary exception into a user-facing alert', async () => {
    create({ onCreate: vi.fn().mockRejectedValue(new Error('private diagnostics')) })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Tạo công việc' }))
    await user.type(screen.getByLabelText('Tên công việc'), 'Bản nháp')
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Tạo công việc' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Vui lòng thử lại sau.')
    expect(screen.getByRole('alert')).not.toHaveTextContent('private diagnostics')
  })
  it.each([403, 404])('invalidates authority after HTTP %s and never calls success', async (status) => {
    const { props } = create({ onCreate: vi.fn().mockRejectedValue(new ApiError(status, status === 403 ? 'forbidden' : 'not-found', 'Không thể tạo công việc.')) })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Tạo công việc' }))
    await user.type(screen.getByLabelText('Tên công việc'), 'Bản nháp')
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Tạo công việc' }))
    expect(props.onDenied).toHaveBeenCalledOnce()
    expect(props.onSaved).not.toHaveBeenCalled()
  })
  it('guards duplicate requests and cancellation while a mutation is pending', async () => {
    const pending = deferred<Task>()
    const onCreate = vi.fn().mockReturnValue(pending.promise)
    create({ onCreate })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Tạo công việc' }))
    const dialog = screen.getByRole('dialog')
    await user.type(screen.getByLabelText('Tên công việc'), 'Bản nháp')
    const button = within(dialog).getByRole('button', { name: 'Tạo công việc' })
    await user.click(button)
    expect(button).toBeDisabled()
    expect(within(dialog).getByRole('button', { name: 'Hủy' })).toBeDisabled()
    expect(within(dialog).getByRole('button', { name: 'Đóng hộp thoại' })).toBeDisabled()
    const form = button.closest('form')
    if (!form) throw new Error('Expected form')
    fireEvent.submit(form)
    expect(onCreate).toHaveBeenCalledOnce()
    await act(async () => { pending.resolve(task) })
  })
  it('aborts obsolete requests when switching Workspace and ignores stale success', async () => {
    const pending = deferred<Task>()
    const onCreate = vi.fn().mockReturnValue(pending.promise)
    const { props, rerender } = create({ onCreate })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Tạo công việc' }))
    await user.type(screen.getByLabelText('Tên công việc'), 'Bản nháp')
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Tạo công việc' }))
    const signal = onCreate.mock.calls[0]?.[1] as AbortSignal
    rerender(<TaskCreate {...props} workspaceId="workspace-b" />)
    expect(signal.aborted).toBe(true)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await act(async () => { pending.resolve(task) })
    expect(props.onSaved).not.toHaveBeenCalled()
  })
})

describe('Task assignment', () => {
  it('offers backend-eligible members by display label and sends their real ProfileMembership ID', async () => {
    const { props } = assign({ members: { count: 4, next: null, previous: null, results: [member('editor-a'), member('inactive', 'MEMBER', false), member('manager', 'ADMIN'), member('reader', 'VIEWER')] } })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Phân công' }))
    expect(props.onOpen).toHaveBeenCalledOnce()
    expect(screen.getAllByRole('option')).toHaveLength(2)
    expect(screen.getByRole('option', { name: 'Tên editor-a' })).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Thành viên'), 'editor-a')
    await user.click(screen.getByRole('button', { name: 'Xác nhận phân công' }))
    expect(props.onAssign).toHaveBeenCalledWith({ target_profile_membership_id: 'editor-a' }, expect.any(AbortSignal))
    expect(props.onSaved).toHaveBeenCalledWith(task)
  })
  it('does not infer assignment eligibility from an apparently active Workspace Editor role', async () => {
    const { props } = assign({ members: { count: 1, next: null, previous: null, results: [{ ...member('profile-manager'), is_assignable: false }] } })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Phân công' }))
    expect(screen.queryByRole('option', { name: 'Tên profile-manager' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Xác nhận phân công' })).toBeDisabled()
    expect(props.onAssign).not.toHaveBeenCalled()
  })
  it('renders server labels as text and disambiguates duplicate labels without invented identities', async () => {
    assign({ members: { count: 2, next: null, previous: null, results: [
      { ...member('member-00000001'), display_label: '<b>An Nguyễn</b>' },
      { ...member('member-00000002'), display_label: '<b>An Nguyễn</b>' },
    ] } })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Phân công' }))
    expect(screen.getByRole('option', { name: '<b>An Nguyễn</b> (…00000001)' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '<b>An Nguyễn</b> (…00000002)' })).toBeInTheDocument()
    expect(screen.getByLabelText('Thành viên').querySelector('b')).toBeNull()
  })
  it('excludes the current assignee and does not invent a replacement', async () => {
    assign({ task: { ...task, active_assignment: { id: 'assignment-a', profile_membership_id: 'editor-a', assigned_at: task.created_at } } })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Phân công' }))
    expect(screen.getByRole('button', { name: 'Xác nhận phân công' })).toBeDisabled()
    expect(screen.getByText('Không có Editor phù hợp trong trang này.')).toBeInTheDocument()
  })
  it('paginates the sanitized roster and clears a selected identity', async () => {
    const { props } = assign({ members: { count: 41, next: '/unfollowed', previous: null, results: [member('editor-a')] } })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Phân công' }))
    await user.selectOptions(screen.getByLabelText('Thành viên'), 'editor-a')
    await user.click(screen.getByRole('button', { name: 'Trang sau' }))
    expect(props.onMembersPageChange).toHaveBeenCalledWith(2)
    expect(screen.getByLabelText('Thành viên')).toHaveValue('')
  })
  it('shows loading/error states without authorizing a mutation', async () => {
    const { rerender, props } = assign({ membersLoading: true })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Phân công' }))
    expect(screen.getByRole('status')).toHaveTextContent('Đang tải thành viên')
    expect(screen.getByRole('button', { name: 'Xác nhận phân công' })).toBeDisabled()
    rerender(<TaskAssign {...props} membersLoading={false} membersError={new ApiError(403, 'forbidden', 'Không thể xem thành viên.')} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Không thể xem thành viên.')
    expect(screen.getByRole('button', { name: 'Xác nhận phân công' })).toBeDisabled()
    expect(props.onAssign).not.toHaveBeenCalled()
  })
  it('retains selection after server role validation fails without assuming Profile role', async () => {
    const { props } = assign({ onAssign: vi.fn().mockRejectedValue(new ApiError(400, 'validation', 'Kiểm tra người nhận việc.', { target_profile_membership_id: 'Thành viên chưa đủ điều kiện.' })) })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Phân công' }))
    await user.selectOptions(screen.getByLabelText('Thành viên'), 'editor-a')
    await user.click(screen.getByRole('button', { name: 'Xác nhận phân công' }))
    expect(screen.getByLabelText('Thành viên')).toHaveValue('editor-a')
    expect(screen.getByLabelText('Thành viên')).toHaveAttribute('aria-invalid', 'true')
    expect(props.onSaved).not.toHaveBeenCalled()
  })
  it('aborts pending assignment when authority is revoked', async () => {
    const pending = deferred<Task>()
    const onAssign = vi.fn().mockReturnValue(pending.promise)
    const { props, rerender } = assign({ onAssign })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Phân công' }))
    await user.selectOptions(screen.getByLabelText('Thành viên'), 'editor-a')
    await user.click(screen.getByRole('button', { name: 'Xác nhận phân công' }))
    const signal = onAssign.mock.calls[0]?.[1] as AbortSignal
    rerender(<TaskAssign {...props} canAssign={false} />)
    expect(signal.aborted).toBe(true)
    await act(async () => { pending.resolve(task) })
    expect(props.onSaved).not.toHaveBeenCalled()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('Task start current-user hint', () => {
  it('is hidden without explicit current-user eligibility', () => {
    start({ task })
    expect(screen.queryByRole('button', { name: 'Bắt đầu công việc' })).not.toBeInTheDocument()
  })
  it.each([{ active: false }, { workspaceId: 'another-workspace' }])('is hidden outside an active authorized scope', (overrides) => {
    start(overrides)
    expect(screen.queryByRole('button', { name: 'Bắt đầu công việc' })).not.toBeInTheDocument()
  })
  it('uses the current-user hint without attempting a User/ProfileMembership comparison', async () => {
    const { props } = start({ task: { ...task, status: 'ASSIGNED', can_start: true, active_assignment: { id: 'assignment-a', profile_membership_id: 'server-membership-only', assigned_at: task.created_at } } })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Bắt đầu công việc' }))
    expect(props.onStart).toHaveBeenCalledWith(expect.any(AbortSignal))
    expect(props.onSaved).toHaveBeenCalledWith(expect.objectContaining({ status: 'WORKING', can_start: false }))
    expect(screen.queryByRole('button', { name: 'Bắt đầu công việc' })).not.toBeInTheDocument()
  })
  it('prevents duplicate starts while pending and ignores responses after scope changes', async () => {
    const pending = deferred<Task>()
    const onStart = vi.fn().mockReturnValue(pending.promise)
    const { props, rerender } = start({ onStart })
    const user = userEvent.setup()
    const button = screen.getByRole('button', { name: 'Bắt đầu công việc' })
    await user.click(button)
    expect(button).toBeDisabled()
    fireEvent.click(button)
    expect(onStart).toHaveBeenCalledOnce()
    const signal = onStart.mock.calls[0]?.[0] as AbortSignal
    rerender(<TaskStart {...props} profileId="another-profile" workspaceId="another-workspace" />)
    expect(signal.aborted).toBe(true)
    await act(async () => { pending.resolve({ ...task, status: 'WORKING' }) })
    expect(props.onSaved).not.toHaveBeenCalled()
  })
  it('aborts a pending start if the current-user hint is revoked', async () => {
    const pending = deferred<Task>()
    const onStart = vi.fn().mockReturnValue(pending.promise)
    const { props, rerender } = start({ onStart })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Bắt đầu công việc' }))
    const signal = onStart.mock.calls[0]?.[0] as AbortSignal
    rerender(<TaskStart {...props} task={{ ...props.task, can_start: false }} />)
    expect(signal.aborted).toBe(true)
    await act(async () => { pending.resolve(task) })
    expect(props.onSaved).not.toHaveBeenCalled()
  })
  it.each([403, 404, 409])('shows safe feedback and requests fresh scope after HTTP %s', async (status) => {
    const { props } = start({ onStart: vi.fn().mockRejectedValue(new ApiError(status, status === 403 ? 'forbidden' : status === 404 ? 'not-found' : 'conflict', 'Quyền hoặc trạng thái công việc đã thay đổi.')) })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Bắt đầu công việc' }))
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Quyền hoặc trạng thái công việc đã thay đổi.')
    expect(alert.parentElement).toHaveFocus()
    expect(props.onDenied).toHaveBeenCalledOnce()
    expect(props.onSaved).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Bắt đầu công việc' })).not.toBeInTheDocument()
  })
  it('retains a retryable safe failure without exposing arbitrary diagnostics', async () => {
    const { props } = start({ onStart: vi.fn().mockRejectedValueOnce(new Error('private diagnostics')).mockResolvedValueOnce({ ...task, status: 'WORKING', can_start: false }) })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Bắt đầu công việc' }))
    expect(screen.getByRole('alert')).not.toHaveTextContent('private diagnostics')
    expect(props.onDenied).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Bắt đầu công việc' }))
    expect(props.onSaved).toHaveBeenCalledOnce()
  })
})

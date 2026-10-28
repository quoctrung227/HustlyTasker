import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/api/client'
import type { Workspace } from '../../services/api/types'
import { WorkspaceActions } from './WorkspaceActions'
import { WorkspaceCreate } from './WorkspaceCreate'

const workspace: Workspace = {
  id: 'workspace-a', profile_id: 'profile-a', name: 'Tháng mười', description: 'Nhóm thiết kế',
  period: '2026-10-01', status: 'ACTIVE', created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z',
}

const showModalDescriptor = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const closeDescriptor = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')

// Unit tests exercise the controlled dialog lifecycle; native keyboard/focus
// behavior still needs the task's browser verification.
beforeAll(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.open = true } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) {
    this.open = false
    this.dispatchEvent(new Event('close'))
  } })
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

function actions(overrides: Partial<Parameters<typeof WorkspaceActions>[0]> = {}) {
  const props = {
    profileId: workspace.profile_id, workspace,
    capabilities: { canEdit: true, canArchive: true, canRestore: true },
    onUpdate: vi.fn().mockResolvedValue(workspace),
    onLifecycle: vi.fn().mockResolvedValue(workspace),
    onSaved: vi.fn(), onDenied: vi.fn(), ...overrides,
  }
  return { ...render(<WorkspaceActions {...props} />), props }
}

async function createForm(onCreate = vi.fn().mockResolvedValue(workspace)) {
  const onCreated = vi.fn()
  const user = userEvent.setup()
  const view = render(<WorkspaceCreate profileId="profile-a" canCreate onCreate={onCreate} onCreated={onCreated} />)
  await user.click(screen.getByRole('button', { name: 'Tạo không gian' }))
  const dialog = screen.getByRole('dialog', { name: 'Tạo không gian làm việc' })
  return { ...view, user, dialog, onCreate, onCreated }
}

describe('Workspace capability boundaries', () => {
  it('hides actions when no backend-proven capability exists', () => {
    actions({ capabilities: {} })
    expect(screen.queryByRole('region', { name: 'Quản lý không gian' })).not.toBeInTheDocument()
  })

  it('never presents a mutation for a mismatched Profile scope', () => {
    actions({ profileId: 'another-profile' })
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('defaults creation to hidden', () => {
    render(<WorkspaceCreate profileId="profile-a" onCreate={vi.fn()} />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('shows only restoration for an archived Workspace', async () => {
    actions({ workspace: { ...workspace, status: 'ARCHIVED' } })
    expect(screen.queryByRole('button', { name: 'Chỉnh sửa không gian' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Lưu trữ không gian' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Khôi phục không gian' })).toBeEnabled()
  })

  it('aborts and discards an open form when its capability is revoked', async () => {
    const pending = deferred<Workspace>()
    const onUpdate = vi.fn().mockReturnValue(pending.promise)
    const { rerender, props } = actions({ onUpdate })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Chỉnh sửa không gian' }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    const signal = onUpdate.mock.calls[0]?.[1] as AbortSignal
    rerender(<WorkspaceActions {...props} capabilities={{}} />)
    expect(signal.aborted).toBe(true)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await act(async () => { pending.resolve(workspace) })
    expect(props.onSaved).not.toHaveBeenCalled()
  })
})

describe('Workspace creation', () => {
  it('focuses an accessible summary and links to invalid fields', async () => {
    const { user, dialog, onCreate } = await createForm()
    await user.click(within(dialog).getByRole('button', { name: 'Tạo không gian' }))
    const alert = screen.getByRole('alert')
    expect(alert.parentElement).toHaveFocus()
    expect(within(dialog).getByLabelText('Tên không gian')).toHaveAttribute('aria-invalid', 'true')
    await user.click(within(alert).getByRole('link', { name: 'Chọn tháng làm việc hợp lệ.' }))
    expect(within(dialog).getByLabelText('Tháng làm việc')).toHaveFocus()
    expect(onCreate).not.toHaveBeenCalled()
  })

  it('submits only canonical creation fields and delegates success invalidation', async () => {
    const { user, dialog, onCreate, onCreated } = await createForm()
    await user.type(within(dialog).getByLabelText('Tên không gian'), '  Tháng mười  ')
    await user.type(within(dialog).getByLabelText('Mô tả'), 'Nhóm thiết kế')
    fireEvent.change(within(dialog).getByLabelText('Tháng làm việc'), { target: { value: '2026-10' } })
    await user.click(within(dialog).getByRole('button', { name: 'Tạo không gian' }))
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(workspace))
    expect(onCreate).toHaveBeenCalledWith({ name: 'Tháng mười', description: 'Nhóm thiết kế', period: '2026-10-01' }, expect.any(AbortSignal))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('rejects an unsupported month without calling the server', async () => {
    const { user, dialog, onCreate } = await createForm()
    await user.type(within(dialog).getByLabelText('Tên không gian'), 'Không gian')
    fireEvent.change(within(dialog).getByLabelText('Tháng làm việc'), { target: { value: '0000-01' } })
    await user.click(within(dialog).getByRole('button', { name: 'Tạo không gian' }))
    expect(onCreate).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('Chọn tháng làm việc hợp lệ.')
  })

  it('retains user values after a conflict and allows explicit retry', async () => {
    const onCreate = vi.fn().mockRejectedValueOnce(new ApiError(409, 'conflict', 'Tháng này đã có không gian.')).mockResolvedValueOnce(workspace)
    const { user, dialog, onCreated } = await createForm(onCreate)
    await user.type(within(dialog).getByLabelText('Tên không gian'), 'Không gian chưa lưu')
    fireEvent.change(within(dialog).getByLabelText('Tháng làm việc'), { target: { value: '2026-10' } })
    await user.click(within(dialog).getByRole('button', { name: 'Tạo không gian' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Tháng này đã có không gian.')
    expect(within(dialog).getByLabelText('Tên không gian')).toHaveValue('Không gian chưa lưu')
    expect(within(dialog).getByLabelText('Tháng làm việc')).toHaveValue('2026-10')
    expect(onCreated).not.toHaveBeenCalled()
    await user.click(within(dialog).getByRole('button', { name: 'Tạo không gian' }))
    await waitFor(() => expect(onCreated).toHaveBeenCalledOnce())
  })

  it('blocks duplicate submits and close while a create request is pending', async () => {
    const pending = deferred<Workspace>()
    const onCreate = vi.fn().mockReturnValue(pending.promise)
    const { user, dialog } = await createForm(onCreate)
    await user.type(within(dialog).getByLabelText('Tên không gian'), 'Không gian')
    fireEvent.change(within(dialog).getByLabelText('Tháng làm việc'), { target: { value: '2026-10' } })
    const button = within(dialog).getByRole('button', { name: 'Tạo không gian' })
    await user.click(button)
    expect(button).toBeDisabled()
    expect(within(dialog).getByRole('button', { name: 'Hủy' })).toBeDisabled()
    expect(within(dialog).getByRole('button', { name: 'Đóng hộp thoại' })).toBeDisabled()
    const form = button.closest('form')
    if (!form) throw new Error('Expected a form')
    fireEvent.submit(form)
    expect(onCreate).toHaveBeenCalledOnce()
    await act(async () => { pending.resolve(workspace) })
  })

  it('aborts obsolete requests when switching Profile and ignores their responses', async () => {
    const pending = deferred<Workspace>()
    const onCreate = vi.fn().mockReturnValue(pending.promise)
    const { user, dialog, rerender, onCreated } = await createForm(onCreate)
    await user.type(within(dialog).getByLabelText('Tên không gian'), 'Không gian')
    fireEvent.change(within(dialog).getByLabelText('Tháng làm việc'), { target: { value: '2026-10' } })
    await user.click(within(dialog).getByRole('button', { name: 'Tạo không gian' }))
    const signal = onCreate.mock.calls[0]?.[1] as AbortSignal
    rerender(<WorkspaceCreate profileId="profile-b" canCreate onCreate={onCreate} onCreated={onCreated} />)
    expect(signal.aborted).toBe(true)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await act(async () => { pending.resolve(workspace) })
    expect(onCreated).not.toHaveBeenCalled()
  })
})

describe('Workspace edit and lifecycle', () => {
  it('edits metadata without sending immutable tenant, period or lifecycle fields', async () => {
    const { props } = actions()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Chỉnh sửa không gian' }))
    expect(screen.queryByLabelText('Tháng làm việc')).not.toBeInTheDocument()
    const name = screen.getByLabelText('Tên không gian')
    await user.clear(name)
    await user.type(name, 'Tên mới')
    await user.click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    await waitFor(() => expect(props.onSaved).toHaveBeenCalledWith(workspace))
    expect(props.onUpdate).toHaveBeenCalledWith({ name: 'Tên mới', description: 'Nhóm thiết kế' }, expect.any(AbortSignal))
    expect(props.onLifecycle).not.toHaveBeenCalled()
  })

  it('connects safe server validation errors without reflecting arbitrary exceptions', async () => {
    actions({ onUpdate: vi.fn().mockRejectedValue(new ApiError(400, 'validation', 'Kiểm tra thông tin.', { name: 'Tên chưa hợp lệ.' })) })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Chỉnh sửa không gian' }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Tên chưa hợp lệ.')
    expect(screen.getByLabelText('Tên không gian')).toHaveAccessibleDescription('Tối đa 255 ký tự. Tên chưa hợp lệ.')
    expect(screen.getByLabelText('Tên không gian')).toHaveValue(workspace.name)
  })

  it.each([403, 404])('asks the owner to refresh capabilities after HTTP %s without reporting success', async (status) => {
    const { props } = actions({ onUpdate: vi.fn().mockRejectedValue(new ApiError(status, status === 403 ? 'forbidden' : 'not-found', 'Không thể cập nhật.')) })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Chỉnh sửa không gian' }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    await waitFor(() => expect(props.onDenied).toHaveBeenCalledOnce())
    expect(props.onSaved).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Tên không gian')).toHaveValue(workspace.name)
  })

  it('keeps CSRF errors separate from permission discovery and does not retry automatically', async () => {
    const { props } = actions({ onUpdate: vi.fn().mockRejectedValue(new ApiError(403, 'csrf', 'Phiên bảo mật đã thay đổi.')) })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Chỉnh sửa không gian' }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Phiên bảo mật đã thay đổi.')
    expect(props.onUpdate).toHaveBeenCalledOnce()
    expect(props.onDenied).not.toHaveBeenCalled()
  })

  it('requires explicit archive confirmation and cancellation does not mutate', async () => {
    const { props } = actions()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Lưu trữ không gian' }))
    expect(props.onLifecycle).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog')).toHaveTextContent('chế độ chỉ đọc')
    await user.click(screen.getByRole('button', { name: 'Hủy' }))
    expect(props.onLifecycle).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Lưu trữ không gian' }))
    await user.click(screen.getByRole('button', { name: 'Xác nhận lưu trữ' }))
    await waitFor(() => expect(props.onSaved).toHaveBeenCalledWith(workspace))
    expect(props.onLifecycle).toHaveBeenCalledWith('archive', expect.any(AbortSignal))
  })

  it('restores only through the current archived-state confirmation', async () => {
    const { props } = actions({ workspace: { ...workspace, status: 'ARCHIVED' } })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Khôi phục không gian' }))
    await user.click(screen.getByRole('button', { name: 'Xác nhận khôi phục' }))
    await waitFor(() => expect(props.onLifecycle).toHaveBeenCalledWith('restore', expect.any(AbortSignal)))
  })

  it('prevents repeated lifecycle requests while confirmation is pending', async () => {
    const pending = deferred<Workspace>()
    const onLifecycle = vi.fn().mockReturnValue(pending.promise)
    actions({ onLifecycle })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Lưu trữ không gian' }))
    const confirm = screen.getByRole('button', { name: 'Xác nhận lưu trữ' })
    await user.click(confirm)
    await user.click(confirm)
    expect(confirm).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Hủy' })).toBeDisabled()
    expect(onLifecycle).toHaveBeenCalledOnce()
    await act(async () => { pending.resolve(workspace) })
  })

  it('aborts a lifecycle UI request when leaving its Workspace scope', async () => {
    const pending = deferred<Workspace>()
    const onLifecycle = vi.fn().mockReturnValue(pending.promise)
    const { props, rerender } = actions({ onLifecycle })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Lưu trữ không gian' }))
    await user.click(screen.getByRole('button', { name: 'Xác nhận lưu trữ' }))
    const signal = onLifecycle.mock.calls[0]?.[1] as AbortSignal
    rerender(<WorkspaceActions {...props} workspace={{ ...workspace, id: 'workspace-b' }} />)
    expect(signal.aborted).toBe(true)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await act(async () => { pending.resolve(workspace) })
    expect(props.onSaved).not.toHaveBeenCalled()
  })

  it('retains confirmation and uses a safe message when lifecycle fails', async () => {
    const { props } = actions({ onLifecycle: vi.fn().mockRejectedValue(new Error('private SQL exception')) })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Lưu trữ không gian' }))
    await user.click(screen.getByRole('button', { name: 'Xác nhận lưu trữ' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Chưa thể cập nhật trạng thái không gian.')
    expect(screen.queryByText(/private SQL/)).not.toBeInTheDocument()
    expect(screen.getByRole('alert').parentElement).toHaveFocus()
    expect(screen.getByRole('button', { name: 'Xác nhận lưu trữ' })).toBeEnabled()
    expect(props.onSaved).not.toHaveBeenCalled()
  })
})

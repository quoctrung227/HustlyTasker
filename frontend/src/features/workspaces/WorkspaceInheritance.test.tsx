/** Scoped component/transport mocks; real membership grants use isolated E2E. */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/api/client'
import { tenantApi } from '../../services/api/queries'
import type { Page, Workspace } from '../../services/api/types'
import { workspaceInheritanceApi } from '../../services/api/workspace-inheritance'
import type { WorkspaceInheritancePreview } from '../../services/api/workspace-inheritance'
import { WorkspaceCreate } from './WorkspaceCreate'

const profileId = '00000000-0000-4000-8000-000000000b01'
const userId = '00000000-0000-4000-8000-000000000b02'
const sourceId = '00000000-0000-4000-8000-000000000b03'
const targetId = '00000000-0000-4000-8000-000000000b04'
const memberId = '00000000-0000-4000-8000-000000000b05'
const otherId = '00000000-0000-4000-8000-000000000b06'
const timestamp = '2026-11-10T00:00:00Z'
const source: Workspace = { id: sourceId, profile_id: profileId, name: 'Nguồn tháng mười', description: null, period: '2026-10-01', status: 'ACTIVE', created_at: timestamp, updated_at: timestamp }
const created: Workspace = { ...source, id: targetId, name: 'Tháng mới', period: '2026-11-01' }
const member = { profile_membership_id: memberId, display_name: 'Bình kiểm thử', role: 'MEMBER' as const }
const page = <T,>(results: T[]): Page<T> => ({ count: results.length, next: null, previous: null, results })
const manual: WorkspaceInheritancePreview = { ...page([]), mode: 'manual', source_workspace: null, excluded_count: 0, has_workspaces: true }
const inherited: WorkspaceInheritancePreview = { ...page([member]), mode: 'inheritance', source_workspace: { id: source.id, name: source.name, period: source.period }, excluded_count: 2, has_workspaces: true }
const initial: WorkspaceInheritancePreview = { ...page([member]), mode: 'initial', source_workspace: null, excluded_count: 0, has_workspaces: false }

const showModal = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const close = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')
beforeAll(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.open = true } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) { this.open = false; this.dispatchEvent(new Event('close')) } })
})
afterAll(() => {
  if (showModal) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', showModal)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
  if (close) Object.defineProperty(HTMLDialogElement.prototype, 'close', close)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
})
beforeEach(() => {
  vi.spyOn(tenantApi, 'workspaces').mockResolvedValue(page([source]))
  vi.spyOn(workspaceInheritanceApi, 'preview').mockImplementation(async (_profile, selected) => selected ? inherited : manual)
})
afterEach(() => vi.restoreAllMocks())

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}
async function open(onCreate = vi.fn().mockResolvedValue(created)) {
  const props = { profileId, currentUserId: userId, canCreate: true, onCreate, onCreated: vi.fn(), onDenied: vi.fn() }
  const view = render(<WorkspaceCreate {...props} />)
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Tạo không gian' }))
  const dialog = screen.getByRole('dialog', { name: 'Tạo không gian làm việc' })
  return { ...view, user, dialog, props }
}
async function fill(dialog: HTMLElement) {
  await userEvent.setup().type(within(dialog).getByLabelText('Tên không gian'), 'Tháng mới')
  fireEvent.change(within(dialog).getByLabelText('Tháng làm việc'), { target: { value: '2026-11' } })
}
async function ready(dialog: HTMLElement) {
  await waitFor(() => expect(within(dialog).getByRole('button', { name: 'Tạo không gian' })).toBeEnabled())
}

describe('explicit Workspace source selection', () => {
  it('starts in manual mode without guessing a latest or previous source', async () => {
    const { dialog } = await open()
    await ready(dialog)
    expect(within(dialog).getByLabelText('Workspace nguồn')).toHaveValue('')
    expect(workspaceInheritanceApi.preview).toHaveBeenCalledExactlyOnceWith(profileId, '', 1, expect.any(AbortSignal))
    expect(within(dialog).getByText(/Không kế thừa thành viên/)).toBeVisible()
  })
  it('previews ADMIN/MEMBER/VIEWER and submits only the selected source ID', async () => {
    const rows = [member, { ...member, profile_membership_id: otherId, display_name: 'An kiểm thử', role: 'ADMIN' as const }, { ...member, profile_membership_id: targetId, display_name: 'Chi kiểm thử', role: 'VIEWER' as const }]
    vi.mocked(workspaceInheritanceApi.preview).mockImplementation(async (_profile, selected) => selected ? { ...inherited, ...page(rows) } : manual)
    const { user, dialog, props } = await open()
    await ready(dialog)
    await user.selectOptions(within(dialog).getByLabelText('Workspace nguồn'), sourceId)
    const list = await within(dialog).findByRole('list', { name: 'Thành viên sẽ được kế thừa' })
    expect(list).toHaveTextContent('An kiểm thửQuản lý (ADMIN)')
    expect(list).toHaveTextContent('Bình kiểm thửEditor (MEMBER)')
    expect(list).toHaveTextContent('Chi kiểm thửChỉ xem (VIEWER)')
    expect(within(dialog).getByText(/2 phân quyền nguồn không được sao chép/)).toBeVisible()
    expect(within(dialog).getByText(/Không sao chép Task/)).toBeVisible()
    await fill(dialog); await ready(dialog)
    await user.click(within(dialog).getByRole('button', { name: 'Tạo không gian' }))
    await waitFor(() => expect(props.onCreated).toHaveBeenCalledWith(created))
    expect(props.onCreate).toHaveBeenCalledWith({ name: 'Tháng mới', description: '', period: '2026-11-01', source_workspace_id: sourceId }, expect.any(AbortSignal))
  })
  it('labels archived sources without hiding a readable snapshot', async () => {
    vi.mocked(tenantApi.workspaces).mockResolvedValue(page([{ ...source, status: 'ARCHIVED' }]))
    const { dialog } = await open()
    expect(await within(dialog).findByRole('option', { name: /Nguồn tháng mười.*Đã lưu trữ/ })).toHaveValue(sourceId)
  })
  it('allows deliberate manual creation when no source is selected', async () => {
    const { user, dialog, props } = await open()
    await fill(dialog); await ready(dialog)
    await user.click(within(dialog).getByRole('button', { name: 'Tạo không gian' }))
    expect(props.onCreate).toHaveBeenCalledWith({ name: 'Tháng mới', description: '', period: '2026-11-01' }, expect.any(AbortSignal))
  })
  it('loads another source page in the same Profile and retains the metadata draft', async () => {
    vi.mocked(tenantApi.workspaces).mockImplementation(async (_profile, currentPage) => ({ ...page(currentPage === 1 ? [source] : [{ ...source, id: otherId, name: 'Nguồn thứ hai' }]), count: 21 }))
    const { user, dialog } = await open()
    await fill(dialog); await ready(dialog)
    await user.click(within(within(dialog).getByRole('navigation', { name: 'Phân trang Workspace nguồn' })).getByRole('button', { name: 'Trang sau' }))
    expect(await within(dialog).findByRole('option', { name: /Nguồn thứ hai/ })).toHaveValue(otherId)
    expect(tenantApi.workspaces).toHaveBeenLastCalledWith(profileId, 2, expect.any(AbortSignal))
    expect(within(dialog).getByLabelText('Tên không gian')).toHaveValue('Tháng mới')
  })
})

describe('first Workspace confirmed MEMBER suggestions', () => {
  beforeEach(() => {
    vi.mocked(tenantApi.workspaces).mockResolvedValue(page([]))
    vi.mocked(workspaceInheritanceApi.preview).mockResolvedValue(initial)
  })
  it('suggests fixed MEMBER access and requires explicit checkbox selection', async () => {
    const { user, dialog, props } = await open()
    const checkbox = await within(dialog).findByRole('checkbox', { name: 'Bình kiểm thử · Editor (MEMBER)' })
    expect(checkbox).not.toBeChecked()
    expect(within(dialog).queryByRole('combobox', { name: /Vai trò/ })).not.toBeInTheDocument()
    await user.click(checkbox); await fill(dialog); await ready(dialog)
    await user.click(within(dialog).getByRole('button', { name: 'Tạo không gian' }))
    expect(props.onCreate).toHaveBeenCalledWith({ name: 'Tháng mới', description: '', period: '2026-11-01', initial_profile_membership_ids: [memberId] }, expect.any(AbortSignal))
  })
  it('can leave direct membership empty while explaining inherited Owner/Admin authority', async () => {
    vi.mocked(workspaceInheritanceApi.preview).mockResolvedValue({ ...initial, ...page([]) })
    const { user, dialog, props } = await open()
    expect(await within(dialog).findByText(/Chưa có thành viên cần phân quyền trực tiếp/)).toBeVisible()
    await fill(dialog); await ready(dialog)
    await user.click(within(dialog).getByRole('button', { name: 'Tạo không gian' }))
    expect(props.onCreate).toHaveBeenCalledWith(expect.objectContaining({ initial_profile_membership_ids: [] }), expect.any(AbortSignal))
  })
  it('retains explicit selections across preview pages without re-adding unselected people', async () => {
    vi.mocked(workspaceInheritanceApi.preview).mockImplementation(async (_profile, _source, currentPage) => ({ ...initial, count: 21, results: currentPage === 1 ? [member] : [{ ...member, profile_membership_id: otherId, display_name: 'Chi kiểm thử' }] }))
    const { user, dialog, props } = await open()
    await user.click(await within(dialog).findByRole('checkbox', { name: 'Bình kiểm thử · Editor (MEMBER)' }))
    await user.click(within(within(dialog).getByRole('navigation', { name: 'Phân trang thành viên kế thừa' })).getByRole('button', { name: 'Trang sau' }))
    expect(await within(dialog).findByRole('checkbox', { name: 'Chi kiểm thử · Editor (MEMBER)' })).not.toBeChecked()
    await fill(dialog); await ready(dialog)
    await user.click(within(dialog).getByRole('button', { name: 'Tạo không gian' }))
    expect(props.onCreate).toHaveBeenCalledWith(expect.objectContaining({ initial_profile_membership_ids: [memberId] }), expect.any(AbortSignal))
  })
})

describe('membership preview safety and draft lifetime', () => {
  it('disables create while the eligibility preview is pending', async () => {
    const pending = deferred<WorkspaceInheritancePreview>()
    vi.mocked(workspaceInheritanceApi.preview).mockReturnValue(pending.promise)
    const { dialog, props } = await open()
    await fill(dialog)
    expect(within(dialog).getByRole('button', { name: 'Tạo không gian' })).toBeDisabled()
    fireEvent.submit(within(dialog).getByRole('button', { name: 'Tạo không gian' }).closest('form') as HTMLFormElement)
    expect(props.onCreate).not.toHaveBeenCalled()
    await act(async () => pending.resolve(manual))
    await ready(dialog)
  })
  it.each([403, 404, 500])('retains metadata and requires explicit preview recovery after HTTP %s', async (status) => {
    vi.mocked(workspaceInheritanceApi.preview).mockRejectedValueOnce(new ApiError(status, status === 403 ? 'forbidden' : status === 404 ? 'not-found' : 'server', 'Không tải được thành viên.')).mockResolvedValue(manual)
    const { dialog, props } = await open()
    await fill(dialog)
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Không tải được thành viên.')
    expect(within(dialog).getByLabelText('Tên không gian')).toHaveValue('Tháng mới')
    expect(within(dialog).getByRole('button', { name: 'Tạo không gian' })).toBeDisabled()
    expect(workspaceInheritanceApi.preview).toHaveBeenCalledOnce()
    expect(props.onCreate).not.toHaveBeenCalled()
  })
  it.each([400, 403, 409, 500])('does not auto-retry a create HTTP %s or discard its draft', async (status) => {
    const onCreate = vi.fn().mockRejectedValue(new ApiError(status, status === 403 ? 'forbidden' : status === 409 ? 'conflict' : status === 400 ? 'validation' : 'server', 'Kiểm tra lại thao tác.'))
    const { user, dialog, props } = await open(onCreate)
    await fill(dialog); await ready(dialog)
    await user.click(within(dialog).getByRole('button', { name: 'Tạo không gian' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(status >= 500 ? 'Chưa xác nhận được kết quả' : 'Kiểm tra lại thao tác.')
    expect(within(dialog).getByLabelText('Tên không gian')).toHaveValue('Tháng mới')
    expect(onCreate).toHaveBeenCalledOnce()
    expect(props.onCreated).not.toHaveBeenCalled()
  })
  it('keeps the same form/source/draft during a same-User capability/data rerender', async () => {
    const { user, dialog, props, rerender } = await open()
    await fill(dialog); await ready(dialog)
    await user.selectOptions(within(dialog).getByLabelText('Workspace nguồn'), sourceId)
    await within(dialog).findByRole('list', { name: 'Thành viên sẽ được kế thừa' })
    rerender(<WorkspaceCreate {...props} onCreate={(input, signal) => props.onCreate(input, signal)} />)
    expect(screen.getByRole('dialog')).toBe(dialog)
    expect(within(dialog).getByLabelText('Tên không gian')).toHaveValue('Tháng mới')
    expect(within(dialog).getByLabelText('Workspace nguồn')).toHaveValue(sourceId)
    expect(workspaceInheritanceApi.preview).toHaveBeenCalledTimes(2)
    expect(props.onCreate).not.toHaveBeenCalled()
  })
  it('aborts obsolete preview and discards the form on User identity change', async () => {
    const pending = deferred<WorkspaceInheritancePreview>()
    vi.mocked(workspaceInheritanceApi.preview).mockReturnValue(pending.promise)
    const { dialog, props, rerender } = await open()
    await fill(dialog)
    const signal = vi.mocked(workspaceInheritanceApi.preview).mock.calls[0]?.[3] as AbortSignal
    rerender(<WorkspaceCreate {...props} currentUserId={otherId} />)
    expect(signal.aborted).toBe(true)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await act(async () => pending.resolve(inherited))
    expect(screen.queryByText('Bình kiểm thử')).not.toBeInTheDocument()
    expect(props.onCreate).not.toHaveBeenCalled()
  })
  it('ignores a stale preview that resolves after a different source has been selected', async () => {
    const stale = deferred<WorkspaceInheritancePreview>()
    vi.mocked(tenantApi.workspaces).mockResolvedValue(page([source, { ...source, id: otherId, name: 'Nguồn khác' }]))
    vi.mocked(workspaceInheritanceApi.preview).mockImplementation(async (_profile, selected) => selected === sourceId ? stale.promise : selected ? { ...inherited, source_workspace: { id: otherId, name: 'Nguồn khác', period: source.period }, results: [{ ...member, display_name: 'Chi nguồn khác' }] } : manual)
    const { user, dialog } = await open(); await ready(dialog)
    await user.selectOptions(within(dialog).getByLabelText('Workspace nguồn'), sourceId)
    const staleSignal = vi.mocked(workspaceInheritanceApi.preview).mock.calls.at(-1)?.[3] as AbortSignal
    await user.selectOptions(within(dialog).getByLabelText('Workspace nguồn'), otherId)
    expect(await within(dialog).findByText('Chi nguồn khác')).toBeVisible()
    expect(staleSignal.aborted).toBe(true)
    await act(async () => stale.resolve(inherited))
    expect(within(dialog).queryByText('Bình kiểm thử')).not.toBeInTheDocument()
    expect(within(dialog).getByLabelText('Workspace nguồn')).toHaveValue(otherId)
  })
})

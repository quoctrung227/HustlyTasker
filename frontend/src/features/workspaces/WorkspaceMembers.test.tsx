/** Real React access forms with mocked services; isolated browser proof is separate. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/api/client'
import { queryKeys } from '../../services/api/queries'
import { workKeys } from '../../services/api/work-management'
import { workspaceAccessApi, workspaceAccessKeys } from '../../services/api/workspace-access'
import type { WorkspaceAccessCandidate, WorkspaceAccessMember, WorkspaceAccessMembersPage } from '../../services/api/workspace-access'
import type { Page } from '../../services/api/types'
import { WorkspaceMembers } from './WorkspaceMembers'

const profileId = '00000000-0000-4000-8000-000000000a01'
const workspaceId = '00000000-0000-4000-8000-000000000a02'
const currentUserId = '00000000-0000-4000-8000-000000000a03'
const candidateId = '00000000-0000-4000-8000-000000000a04'
const otherProfileId = '00000000-0000-4000-8000-000000000b01'
const otherWorkspaceId = '00000000-0000-4000-8000-000000000b02'
const otherUserId = '00000000-0000-4000-8000-000000000b03'
const created = '2026-11-09T00:00:00Z'
const candidate: WorkspaceAccessCandidate = { profile_membership_id: candidateId, display_label: 'Người nhận Workspace', profile_role: 'MEMBER', has_inherited_access: false }
const member: WorkspaceAccessMember = {
  id: '00000000-0000-4000-8000-000000000a05', profile_membership_id: candidateId, display_label: 'Editor hiện có', role: 'MEMBER',
  is_active: true, is_assignable: true, joined_at: created, updated_at: created,
  capabilities: { can_update: true, can_revoke: true, allowed_roles: ['ADMIN', 'MEMBER', 'VIEWER'], has_inherited_access: false },
}
const ownerPage: WorkspaceAccessMembersPage = {
  count: 1, next: null, previous: null, results: [member],
  capabilities: { can_add: true, allowed_roles: ['ADMIN', 'MEMBER', 'VIEWER'], profile_role: 'OWNER', workspace_role: null, has_inherited_access: true },
}
const page = <T,>(results: T[], count = results.length): Page<T> => ({ count, next: null, previous: null, results })
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}
function setup(overrides: Partial<{ profileId: string; workspaceId: string; currentUserId: string }> = {}) {
  const props = { profileId, workspaceId, currentUserId, ...overrides }
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0, gcTime: Infinity, refetchOnWindowFocus: false } } })
  const renderPage = (values: typeof props) => <QueryClientProvider client={cache}><MemoryRouter><WorkspaceMembers {...values} /></MemoryRouter></QueryClientProvider>
  const view = render(renderPage(props))
  return { ...view, props, cache, change: (values: typeof props) => view.rerender(renderPage(values)) }
}
async function openAdd() {
  await userEvent.setup().click(await screen.findByRole('button', { name: 'Thêm thành viên' }))
  await screen.findByRole('option', { name: candidate.display_label })
  return screen.getByRole('dialog', { name: 'Thêm thành viên Workspace' })
}
async function fillAdd() {
  const dialog = await openAdd()
  await userEvent.setup().selectOptions(within(dialog).getByLabelText('Chọn thành viên tổ chức'), candidateId)
  return dialog
}
function actions(label = member.display_label) { return screen.getByLabelText(`Quyền của ${label}`) }

const oldShowModal = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const oldClose = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')
beforeAll(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.open = true } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) { this.open = false; this.dispatchEvent(new Event('close')) } })
})
afterAll(() => {
  if (oldShowModal) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', oldShowModal)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
  if (oldClose) Object.defineProperty(HTMLDialogElement.prototype, 'close', oldClose)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
})
beforeEach(() => {
  vi.spyOn(workspaceAccessApi, 'members').mockResolvedValue(ownerPage)
  vi.spyOn(workspaceAccessApi, 'candidates').mockResolvedValue(page([candidate]))
  vi.spyOn(workspaceAccessApi, 'add').mockResolvedValue({ ...member, display_label: candidate.display_label })
  vi.spyOn(workspaceAccessApi, 'update').mockResolvedValue({ ...member, role: 'VIEWER', is_assignable: false })
  vi.spyOn(workspaceAccessApi, 'revoke').mockResolvedValue(undefined)
})
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('Workspace access roster and server authority', () => {
  it('fetches current Workspace scope and does not load candidates before opening a form', async () => {
    setup()
    expect(await screen.findByText(member.display_label)).toBeInTheDocument()
    expect(workspaceAccessApi.members).toHaveBeenCalledWith(profileId, workspaceId, 1, expect.any(AbortSignal))
    expect(workspaceAccessApi.candidates).not.toHaveBeenCalled()
    expect(screen.getByRole('heading', { name: 'Thành viên Workspace' })).toBeInTheDocument()
    expect(document.getElementById('workspace-members')).toBeInTheDocument()
  })

  it('shows direct role and inherited authority without a global User directory or visible IDs', async () => {
    setup()
    expect(await screen.findByText('Editor (MEMBER) · Đang hoạt động')).toBeInTheDocument()
    expect(screen.getByText('Quản trị kế thừa từ tổ chức')).toBeInTheDocument()
    expect(screen.getByText(/Chủ sở hữu\/Quản trị viên tổ chức có quyền kế thừa dù không có dòng/)).toBeInTheDocument()
    expect(screen.queryByText(member.id)).not.toBeInTheDocument()
    expect(screen.queryByText(candidateId)).not.toBeInTheDocument()
  })

  it('provides an honest empty direct-roster state while preserving inherited authority', async () => {
    vi.mocked(workspaceAccessApi.members).mockResolvedValue({ ...ownerPage, ...page([]) })
    setup()
    expect(await screen.findByText('Chưa có phân quyền trực tiếp')).toBeInTheDocument()
    expect(screen.getByText(/Bạn đang có quyền quản trị kế thừa/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Thêm thành viên' })).toBeInTheDocument()
  })

  it.each([403, 404])('shows a safe permission surface for HTTP%s without candidate data/actions or a retry loop', async (status) => {
    vi.mocked(workspaceAccessApi.members).mockRejectedValue(new ApiError(status, status === 403 ? 'forbidden' : 'not-found', 'Nội dung không khả dụng.'))
    setup()
    expect(await screen.findByRole('alert')).toHaveTextContent('Nội dung không khả dụng.')
    expect(screen.queryByText(member.display_label)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Thêm thành viên' })).not.toBeInTheDocument()
    expect(screen.getByText(/Quyền xem công việc không tự cấp quyền quản trị thành viên/)).toBeInTheDocument()
    expect(workspaceAccessApi.candidates).not.toHaveBeenCalled()
    expect(workspaceAccessApi.members).toHaveBeenCalledTimes(1)
  })

  it('uses archived/read-only capabilities without hiding an authorized roster', async () => {
    vi.mocked(workspaceAccessApi.members).mockResolvedValue({ ...ownerPage,
      capabilities: { ...ownerPage.capabilities, can_add: false, allowed_roles: [] },
      results: [{ ...member, capabilities: { ...member.capabilities, can_update: false, can_revoke: false, allowed_roles: [] } }],
    })
    setup()
    expect(await screen.findByText(member.display_label)).toBeInTheDocument()
    expect(screen.getByText(/Workspace hoặc tổ chức đã lưu trữ không thể thay đổi/)).toBeInTheDocument()
    for (const name of ['Thêm thành viên', 'Cập nhật quyền', 'Thu hồi quyền']) expect(screen.queryByRole('button', { name })).not.toBeInTheDocument()
  })

  it('distinguishes an ordinary roster403 from actual missing Workspace404 when purging old work cache', async () => {
    const result = deferred<WorkspaceAccessMembersPage>()
    vi.mocked(workspaceAccessApi.members).mockReturnValue(result.promise)
    const { cache } = setup()
    const taskKey = workKeys.task(profileId, workspaceId, 'cached-task')
    cache.setQueryData(taskKey, { title: 'Previously authorized work' })
    await act(async () => { result.resolve(ownerPage) })
    await screen.findByText(member.display_label)
    vi.mocked(workspaceAccessApi.members).mockRejectedValue(new ApiError(403, 'forbidden', 'Chỉ còn quyền đọc công việc.'))
    await act(async () => { await cache.invalidateQueries({ queryKey: workspaceAccessKeys.members(currentUserId, profileId, workspaceId) }) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Chỉ còn quyền đọc công việc.')
    expect(cache.getQueryData(taskKey)).toEqual({ title: 'Previously authorized work' })
  })

  it('purges cached work and refreshes Workspace authority on a real missing-scope404', async () => {
    const result = deferred<WorkspaceAccessMembersPage>()
    vi.mocked(workspaceAccessApi.members).mockReturnValue(result.promise)
    const { cache } = setup()
    const taskKey = workKeys.task(profileId, workspaceId, 'cached-task')
    cache.setQueryData(taskKey, { title: 'Old private work' })
    cache.setQueryData(queryKeys.workspace(profileId, workspaceId), { id: workspaceId })
    await act(async () => { result.resolve(ownerPage) })
    await screen.findByText(member.display_label)
    vi.mocked(workspaceAccessApi.members).mockRejectedValue(new ApiError(404, 'not-found', 'Không còn Workspace này.'))
    await act(async () => { await cache.invalidateQueries({ queryKey: workspaceAccessKeys.members(currentUserId, profileId, workspaceId) }) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Không còn Workspace này.')
    await waitFor(() => expect(cache.getQueryData(taskKey)).toBeUndefined())
    expect(cache.getQueryState(queryKeys.workspace(profileId, workspaceId))?.isInvalidated).toBe(true)
  })

  it('honors Workspace-manager role ceiling and per-row mutation hints', async () => {
    const manager: WorkspaceAccessMember = { ...member, id: '00000000-0000-4000-8000-000000000a06', display_label: 'Quản lý được bảo vệ', role: 'ADMIN', capabilities: { can_update: false, can_revoke: false, allowed_roles: [], has_inherited_access: false } }
    vi.mocked(workspaceAccessApi.members).mockResolvedValue({ ...ownerPage, count: 2, results: [member, manager],
      capabilities: { can_add: true, allowed_roles: ['MEMBER', 'VIEWER'], profile_role: 'MEMBER', workspace_role: 'ADMIN', has_inherited_access: false },
    })
    setup()
    const dialog = await openAdd()
    expect(within(dialog).queryByRole('option', { name: 'Quản lý (ADMIN)' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Quyền của Quản lý được bảo vệ')).not.toBeInTheDocument()
    expect(within(dialog).queryByRole('link', { name: 'Mời người chưa thuộc tổ chức' })).not.toBeInTheDocument()
  })

  it('paginates only its scoped roster using its own page numbers', async () => {
    vi.mocked(workspaceAccessApi.members).mockResolvedValue({ ...ownerPage, count: 21, next: 'https://untrusted.invalid/' })
    setup()
    const nav = await screen.findByRole('navigation', { name: 'Phân trang thành viên Workspace' })
    await userEvent.setup().click(within(nav).getByRole('button', { name: 'Trang sau' }))
    await waitFor(() => expect(workspaceAccessApi.members).toHaveBeenCalledWith(profileId, workspaceId, 2, expect.any(AbortSignal)))
  })
})

describe('Workspace grant form', () => {
  it('loads eligible candidates under exact tenant scope and validates required selection', async () => {
    setup()
    const dialog = await openAdd()
    expect(workspaceAccessApi.candidates).toHaveBeenCalledWith(profileId, workspaceId, 1, expect.any(AbortSignal))
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Cấp quyền truy cập' }))
    expect(await within(dialog).findByText('Vui lòng kiểm tra thông tin phân quyền.')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Chọn thành viên tổ chức')).toHaveAttribute('aria-invalid', 'true')
    expect(workspaceAccessApi.add).not.toHaveBeenCalled()
  })

  it('explains an empty candidate page without a fake grant or Workspace email invitation', async () => {
    vi.mocked(workspaceAccessApi.candidates).mockResolvedValue(page([]))
    setup()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Thêm thành viên' }))
    const dialog = screen.getByRole('dialog', { name: 'Thêm thành viên Workspace' })
    expect(await within(dialog).findByText(/Không có thành viên đủ điều kiện trong trang này/)).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Cấp quyền truy cập' })).toBeDisabled()
    expect(within(dialog).getByRole('link', { name: 'Mời người chưa thuộc tổ chức' })).toHaveAttribute('href', `/profiles/${profileId}/members`)
    expect(within(dialog).queryByRole('textbox', { name: /Email/ })).not.toBeInTheDocument()
  })

  it('submits server-selected membership/role once and refreshes access, assignment and Workspace caches only after success', async () => {
    const pending = deferred<WorkspaceAccessMember>()
    vi.mocked(workspaceAccessApi.add).mockReturnValue(pending.promise)
    const { cache } = setup()
    cache.setQueryData(workKeys.members(profileId, workspaceId), page([]))
    cache.setQueryData(queryKeys.workspaces(profileId), page([]))
    const dialog = await fillAdd()
    const submit = within(dialog).getByRole('button', { name: 'Cấp quyền truy cập' })
    await userEvent.setup().dblClick(submit)
    expect(workspaceAccessApi.add).toHaveBeenCalledTimes(1)
    expect(workspaceAccessApi.add).toHaveBeenCalledWith(profileId, workspaceId, { target_profile_membership_id: candidateId, role: 'MEMBER' }, expect.any(AbortSignal))
    expect(submit).toBeDisabled()
    expect(screen.queryByText(/Đã cấp phân quyền trực tiếp/)).not.toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Đóng' })).toBeDisabled()
    await act(async () => pending.resolve(member))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.getByText(/Đã cấp phân quyền trực tiếp/)).toBeInTheDocument()
    expect(cache.getQueryState(workKeys.members(profileId, workspaceId))?.isInvalidated).toBe(true)
    expect(cache.getQueryState(queryKeys.workspaces(profileId))?.isInvalidated).toBe(true)
  })

  it('retains selection after server field validation and shows linked accessible errors', async () => {
    vi.mocked(workspaceAccessApi.add).mockRejectedValue(new ApiError(400, 'validation', 'Kiểm tra phân quyền.', { role: 'static', target_profile_membership_id: 'static' }))
    setup()
    const dialog = await fillAdd()
    await userEvent.setup().selectOptions(within(dialog).getByLabelText('Vai trò trong Workspace'), 'VIEWER')
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Cấp quyền truy cập' }))
    expect(await within(dialog).findByText('Kiểm tra phân quyền.')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Chọn thành viên tổ chức')).toHaveValue(candidateId)
    expect(within(dialog).getByLabelText('Vai trò trong Workspace')).toHaveValue('VIEWER')
    await userEvent.setup().click(within(dialog).getByRole('link', { name: 'Chọn vai trò hiện được backend cho phép.' }))
    expect(within(dialog).getByLabelText('Vai trò trong Workspace')).toHaveFocus()
  })

  it.each([409, 503])('retains an unsuccessful HTTP%s form without false success or automatic duplicate write', async (status) => {
    vi.mocked(workspaceAccessApi.add).mockRejectedValue(new ApiError(status, status === 409 ? 'conflict' : 'server', 'Không thể lưu phân quyền.'))
    setup()
    const dialog = await fillAdd()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Cấp quyền truy cập' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(status === 409 ? 'Không thể lưu phân quyền.' : 'Chưa xác nhận được kết quả.')
    expect(within(dialog).getByLabelText('Chọn thành viên tổ chức')).toHaveValue(candidateId)
    expect(screen.queryByText(/Đã cấp phân quyền trực tiếp/)).not.toBeInTheDocument()
    expect(workspaceAccessApi.add).toHaveBeenCalledTimes(1)
  })

  it('keeps a recoverable CSRF403 draft and offers a deliberate retry', async () => {
    vi.mocked(workspaceAccessApi.add).mockRejectedValueOnce(new ApiError(403, 'csrf', 'Phiên bảo vệ đã thay đổi.'))
    setup()
    const dialog = await fillAdd()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Cấp quyền truy cập' }))
    expect(await within(dialog).findByText('Phiên bảo vệ đã thay đổi.')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Chọn thành viên tổ chức')).toHaveValue(candidateId)
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Cấp quyền truy cập' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(workspaceAccessApi.add).toHaveBeenCalledTimes(2)
  })

  it.each([403, 404])('clears private access data and form when mutation loses scope HTTP%s', async (status) => {
    vi.mocked(workspaceAccessApi.add).mockRejectedValue(new ApiError(status, status === 403 ? 'forbidden' : 'not-found', 'Đã mất quyền quản lý.'))
    const { cache } = setup()
    const dialog = await fillAdd()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Cấp quyền truy cập' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Đã mất quyền quản lý.')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.queryByText(member.display_label)).not.toBeInTheDocument()
    // A still-mounted disabled observer may recreate an empty query shell.
    // The security requirement is absence of private data, not metadata objects.
    await waitFor(() => expect(cache.getQueriesData({ queryKey: workspaceAccessKeys.scope(currentUserId, profileId, workspaceId) }).every(([, data]) => data === undefined)).toBe(true))
  })

  it('paginates candidates without carrying a selection into another page', async () => {
    vi.mocked(workspaceAccessApi.candidates).mockImplementation(async (_profile, _workspace, currentPage) => currentPage === 1 ? page([candidate], 21) : page([{ ...candidate, profile_membership_id: '00000000-0000-4000-8000-000000000a07', display_label: 'Ứng viên trang hai' }], 21))
    setup()
    const dialog = await fillAdd()
    await userEvent.setup().click(within(within(dialog).getByRole('navigation', { name: 'Phân trang ứng viên Workspace' })).getByRole('button', { name: 'Trang sau' }))
    await within(dialog).findByRole('option', { name: 'Ứng viên trang hai' })
    expect(within(dialog).getByLabelText('Chọn thành viên tổ chức')).toHaveValue('')
    expect(workspaceAccessApi.candidates).toHaveBeenLastCalledWith(profileId, workspaceId, 2, expect.any(AbortSignal))
  })

  it('does not submit a candidate removed by current backend eligibility', async () => {
    const { cache } = setup()
    const dialog = await fillAdd()
    vi.mocked(workspaceAccessApi.candidates).mockResolvedValue(page([]))
    await act(async () => { await cache.invalidateQueries({ queryKey: workspaceAccessKeys.candidates(currentUserId, profileId, workspaceId) }) })
    await waitFor(() => expect(within(dialog).getByLabelText('Chọn thành viên tổ chức')).toHaveValue(''))
    expect(within(dialog).getByRole('button', { name: 'Cấp quyền truy cập' })).toBeDisabled()
    expect(workspaceAccessApi.add).not.toHaveBeenCalled()
  })
})

describe('Workspace role change and revocation', () => {
  it('requires deliberate role confirmation and keeps old role until server response', async () => {
    const pending = deferred<WorkspaceAccessMember>()
    vi.mocked(workspaceAccessApi.update).mockReturnValue(pending.promise)
    setup()
    await screen.findByText(member.display_label)
    await userEvent.setup().click(within(actions()).getByRole('button', { name: 'Cập nhật quyền' }))
    const dialog = screen.getByRole('dialog', { name: 'Cập nhật quyền Workspace' })
    expect(workspaceAccessApi.update).not.toHaveBeenCalled()
    await userEvent.setup().selectOptions(within(dialog).getByLabelText('Vai trò trong Workspace'), 'VIEWER')
    await userEvent.setup().dblClick(within(dialog).getByRole('button', { name: 'Xác nhận cập nhật quyền' }))
    expect(workspaceAccessApi.update).toHaveBeenCalledTimes(1)
    expect(workspaceAccessApi.update).toHaveBeenCalledWith(profileId, workspaceId, member.id, { role: 'VIEWER' }, expect.any(AbortSignal))
    expect(screen.getByText('Editor (MEMBER) · Đang hoạt động')).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Giữ quyền hiện tại' })).toBeDisabled()
    vi.mocked(workspaceAccessApi.members).mockResolvedValue({ ...ownerPage, results: [{ ...member, role: 'VIEWER' }] })
    await act(async () => pending.resolve({ ...member, role: 'VIEWER' }))
    expect(await screen.findByText('Chỉ xem (VIEWER) · Đang hoạt động')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('keeps editable role after validation failure without claiming success', async () => {
    vi.mocked(workspaceAccessApi.update).mockRejectedValue(new ApiError(400, 'validation', 'Vai trò không hợp lệ.', { role: 'static' }))
    setup()
    await screen.findByText(member.display_label)
    await userEvent.setup().click(within(actions()).getByRole('button', { name: 'Cập nhật quyền' }))
    const dialog = screen.getByRole('dialog', { name: 'Cập nhật quyền Workspace' })
    await userEvent.setup().selectOptions(within(dialog).getByLabelText('Vai trò trong Workspace'), 'VIEWER')
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Xác nhận cập nhật quyền' }))
    expect(await within(dialog).findByText('Vai trò không hợp lệ.')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Vai trò trong Workspace')).toHaveValue('VIEWER')
    expect(screen.queryByText('Đã cập nhật phân quyền trực tiếp.')).not.toBeInTheDocument()
  })

  it('warns that modifying or revoking a Profile manager row does not remove inherited authority', async () => {
    vi.mocked(workspaceAccessApi.members).mockResolvedValue({ ...ownerPage, results: [{ ...member, capabilities: { ...member.capabilities, has_inherited_access: true } }] })
    setup()
    await screen.findByText(member.display_label)
    await userEvent.setup().click(within(actions()).getByRole('button', { name: 'Cập nhật quyền' }))
    let dialog = screen.getByRole('dialog', { name: 'Cập nhật quyền Workspace' })
    expect(within(dialog).getByText(/Thay đổi hoặc thu hồi phân quyền trực tiếp không loại bỏ quyền kế thừa/)).toBeInTheDocument()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Giữ quyền hiện tại' }))
    await userEvent.setup().click(within(actions()).getByRole('button', { name: 'Thu hồi quyền' }))
    dialog = screen.getByRole('dialog', { name: 'Thu hồi quyền Workspace' })
    expect(within(dialog).getByText(/Thay đổi hoặc thu hồi phân quyền trực tiếp không loại bỏ quyền kế thừa/)).toBeInTheDocument()
    expect(workspaceAccessApi.revoke).not.toHaveBeenCalled()
  })

  it('requires revoke confirmation, prevents double submit and removes the row only after confirmed server refresh', async () => {
    const pending = deferred<void>()
    vi.mocked(workspaceAccessApi.revoke).mockReturnValue(pending.promise)
    setup()
    await screen.findByText(member.display_label)
    await userEvent.setup().click(within(actions()).getByRole('button', { name: 'Thu hồi quyền' }))
    const dialog = screen.getByRole('dialog', { name: 'Thu hồi quyền Workspace' })
    expect(workspaceAccessApi.revoke).not.toHaveBeenCalled()
    await userEvent.setup().dblClick(within(dialog).getByRole('button', { name: 'Xác nhận thu hồi quyền' }))
    expect(workspaceAccessApi.revoke).toHaveBeenCalledTimes(1)
    expect(workspaceAccessApi.revoke).toHaveBeenCalledWith(profileId, workspaceId, member.id, expect.any(AbortSignal))
    expect(screen.getByRole('list', { name: 'Thành viên Workspace' })).toHaveTextContent(member.display_label)
    vi.mocked(workspaceAccessApi.members).mockResolvedValue({ ...ownerPage, ...page([]) })
    await act(async () => pending.resolve(undefined))
    expect(await screen.findByText('Chưa có phân quyền trực tiếp')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('retains revoke confirmation on conflict and never shows a success tombstone', async () => {
    vi.mocked(workspaceAccessApi.revoke).mockRejectedValue(new ApiError(409, 'conflict', 'Quyền đã thay đổi.'))
    setup()
    await screen.findByText(member.display_label)
    await userEvent.setup().click(within(actions()).getByRole('button', { name: 'Thu hồi quyền' }))
    const dialog = screen.getByRole('dialog', { name: 'Thu hồi quyền Workspace' })
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Xác nhận thu hồi quyền' }))
    expect(await within(dialog).findByText('Quyền đã thay đổi.')).toBeInTheDocument()
    expect(screen.queryByText('Đã thu hồi phân quyền trực tiếp trong Workspace.')).not.toBeInTheDocument()
  })
})

describe('Workspace access draft lifetime and current scope', () => {
  it('keeps the same grant form and selections during harmless background refresh', async () => {
    const { cache } = setup()
    const dialog = await fillAdd()
    const field = within(dialog).getByLabelText('Chọn thành viên tổ chức')
    const role = within(dialog).getByLabelText('Vai trò trong Workspace')
    await userEvent.setup().selectOptions(role, 'VIEWER')
    await act(async () => { await cache.invalidateQueries({ queryKey: workspaceAccessKeys.scope(currentUserId, profileId, workspaceId) }) })
    expect(screen.getByRole('dialog', { name: 'Thêm thành viên Workspace' })).toBe(dialog)
    expect(within(dialog).getByLabelText('Chọn thành viên tổ chức')).toBe(field)
    expect(field).toHaveValue(candidateId)
    expect(role).toHaveValue('VIEWER')
  })

  it('drops a now-forbidden grant role while keeping the current form', async () => {
    const { cache } = setup()
    const dialog = await fillAdd()
    await userEvent.setup().selectOptions(within(dialog).getByLabelText('Vai trò trong Workspace'), 'ADMIN')
    vi.mocked(workspaceAccessApi.members).mockResolvedValue({ ...ownerPage, capabilities: { ...ownerPage.capabilities, allowed_roles: ['MEMBER', 'VIEWER'] } })
    await act(async () => { await cache.invalidateQueries({ queryKey: workspaceAccessKeys.members(currentUserId, profileId, workspaceId) }) })
    await waitFor(() => expect(within(dialog).getByLabelText('Vai trò trong Workspace')).toHaveValue(''))
    expect(within(dialog).queryByRole('option', { name: 'Quản lý (ADMIN)' })).not.toBeInTheDocument()
    expect(workspaceAccessApi.add).not.toHaveBeenCalled()
  })

  it('closes an obsolete role dialog and aborts its mutation after permission changes', async () => {
    const pending = deferred<WorkspaceAccessMember>()
    vi.mocked(workspaceAccessApi.update).mockReturnValue(pending.promise)
    const { cache } = setup()
    await screen.findByText(member.display_label)
    await userEvent.setup().click(within(actions()).getByRole('button', { name: 'Cập nhật quyền' }))
    const dialog = screen.getByRole('dialog', { name: 'Cập nhật quyền Workspace' })
    await userEvent.setup().selectOptions(within(dialog).getByLabelText('Vai trò trong Workspace'), 'VIEWER')
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Xác nhận cập nhật quyền' }))
    const signal = vi.mocked(workspaceAccessApi.update).mock.calls[0]?.[4]
    vi.mocked(workspaceAccessApi.members).mockResolvedValue({ ...ownerPage, results: [{ ...member, capabilities: { ...member.capabilities, can_update: false, can_revoke: false, allowed_roles: [] } }] })
    await act(async () => { await cache.invalidateQueries({ queryKey: workspaceAccessKeys.members(currentUserId, profileId, workspaceId) }) })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(signal?.aborted).toBe(true)
    await act(async () => pending.resolve(member))
    expect(screen.queryByText('Đã cập nhật phân quyền trực tiếp.')).not.toBeInTheDocument()
  })

  it.each(['currentUserId', 'profileId', 'workspaceId'] as const)('isolates draft, candidates and late grant response after %s changes', async (field) => {
    const pending = deferred<WorkspaceAccessMember>()
    vi.mocked(workspaceAccessApi.add).mockReturnValue(pending.promise)
    const view = setup()
    const dialog = await fillAdd()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Cấp quyền truy cập' }))
    const signal = vi.mocked(workspaceAccessApi.add).mock.calls[0]?.[3]
    const changed = { ...view.props, [field]: field === 'currentUserId' ? otherUserId : field === 'profileId' ? otherProfileId : otherWorkspaceId }
    view.change(changed)
    await screen.findByRole('button', { name: 'Thêm thành viên' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(signal?.aborted).toBe(true)
    await act(async () => pending.resolve(member))
    expect(screen.queryByText(/Đã cấp phân quyền trực tiếp/)).not.toBeInTheDocument()
    expect(workspaceAccessApi.candidates).toHaveBeenCalledTimes(1)
  })

  it('removes old private candidates and roster after current candidate access is revoked', async () => {
    const { cache } = setup()
    const dialog = await fillAdd()
    vi.mocked(workspaceAccessApi.candidates).mockRejectedValue(new ApiError(403, 'forbidden', 'Không còn quyền xem ứng viên.'))
    await act(async () => { await cache.invalidateQueries({ queryKey: workspaceAccessKeys.candidates(currentUserId, profileId, workspaceId) }) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Không còn quyền xem ứng viên.')
    expect(dialog).not.toBeInTheDocument()
    expect(screen.queryByText(member.display_label)).not.toBeInTheDocument()
    await waitFor(() => expect(cache.getQueriesData({ queryKey: workspaceAccessKeys.scope(currentUserId, profileId, workspaceId) }).every(([, data]) => data === undefined)).toBe(true))
  })

  it('keeps labels and semantic selection keyboard-accessible without custom controls', async () => {
    setup()
    const dialog = await openAdd()
    const select = within(dialog).getByLabelText('Chọn thành viên tổ chức')
    expect(select.tagName).toBe('SELECT')
    select.focus()
    fireEvent.change(select, { target: { value: candidateId } })
    expect(select).toHaveFocus()
    expect(select).toHaveValue(candidateId)
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Đóng' }))
    expect(screen.getByRole('button', { name: 'Thêm thành viên' })).toHaveFocus()
  })
})

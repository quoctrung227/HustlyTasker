/** Real membership components with mocked services; isolated browser proof is separate. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/api/client'
import { memberKeys, membersApi } from '../../services/api/members'
import type { InvitationCandidate, ProfileInvitation, ProfileMembersPage } from '../../services/api/members'
import { queryKeys, tenantApi } from '../../services/api/queries'
import type { Page, Profile } from '../../services/api/types'
import { OrganizationMembers } from './OrganizationMembers'

const profileId = '00000000-0000-4000-8000-000000000901'
const currentUserId = '00000000-0000-4000-8000-000000000902'
const otherProfileId = '00000000-0000-4000-8000-000000000911'
const otherUserId = '00000000-0000-4000-8000-000000000912'
const recipientUserId = '00000000-0000-4000-8000-000000000920'
const candidate: InvitationCandidate = { id: recipientUserId, display_label: 'Tài khoản mới', username: 'new-member', masked_email: null, relation: 'AVAILABLE', can_invite: true }
const created = '2026-11-08T00:00:00Z'
const profile: Profile = { id: profileId, name: 'Tổ chức cùng làm', status: 'ACTIVE', created_at: created, updated_at: created }
const ownerPage: ProfileMembersPage = {
  count: 1, next: null, previous: null,
  results: [{ id: '00000000-0000-4000-8000-000000000903', profile_id: profileId, display_label: 'Người quản trị thử nghiệm', role: 'OWNER', is_active: true, joined_at: created }],
  capabilities: { can_invite: true, can_manage_invitations: true, allowed_invitation_roles: ['MEMBER', 'ADMIN'] },
}
const invitation: ProfileInvitation = {
  id: '00000000-0000-4000-8000-000000000904', profile_id: profileId, recipient_email: 'recipient@example.test', requested_role: 'MEMBER', status: 'PENDING', delivery_status: 'SENT',
  created_at: created, updated_at: created, expires_at: '2026-11-15T00:00:00Z', delivery_attempted_at: created, delivered_at: created,
  accepted_at: null, declined_at: null, revoked_at: null, expired_at: null,
}
const accountInvitation: ProfileInvitation = { ...invitation, acceptance_kind: 'ACCOUNT', recipient_email: null,
  recipient_display_label: 'Tài khoản được mời', recipient_username: 'recipient', recipient_masked_email: null }
const page = <T,>(results: T[], count = results.length): Page<T> => ({ count, next: null, previous: null, results })
const denied = () => new ApiError(403, 'forbidden', 'Bạn không có quyền quản lý tổ chức.')
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}
function setup(overrides: Partial<{ profileId: string; currentUserId: string }> = {}) {
  const props = { profileId, currentUserId, ...overrides }
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0, gcTime: Infinity, refetchOnWindowFocus: false } } })
  const renderPage = (values: typeof props) => <QueryClientProvider client={cache}><MemoryRouter><OrganizationMembers {...values} /></MemoryRouter></QueryClientProvider>
  const view = render(renderPage(props))
  return { ...view, cache, props, change: (values: typeof props) => view.rerender(renderPage(values)) }
}
async function openInvite() {
  await userEvent.setup().click(await screen.findByRole('button', { name: 'Thêm thành viên' }))
  return screen.getByRole('dialog', { name: 'Mời thành viên' })
}
async function fillInvite() {
  const dialog = await openInvite()
  await userEvent.setup().click(await within(dialog).findByRole('radio', { name: /Tài khoản mới/ }))
  return dialog
}
function paginatedInvitations(account = false) {
  const older: ProfileInvitation = { ...(account ? accountInvitation : invitation), id: '00000000-0000-4000-8000-000000000908',
    ...(account ? { recipient_display_label: 'Tài khoản cũ' } : { recipient_email: 'older@example.test' }) }
  let currentOlder = older
  let newest: ProfileInvitation | undefined
  vi.mocked(membersApi.invitations).mockImplementation(async (_profileId, currentPage = 1) => page(
    currentPage === 1 ? [newest || invitation] : [currentOlder], newest ? 22 : 21,
  ))
  return { older, setNewest: (value: ProfileInvitation) => { newest = value }, setOlder: (value: ProfileInvitation) => { currentOlder = value } }
}
async function secondInvitationPage(name = 'older@example.test') {
  const nav = await screen.findByRole('navigation', { name: 'Phân trang lời mời' })
  await userEvent.setup().click(within(nav).getByRole('button', { name: 'Trang sau' }))
  await waitFor(() => expect(membersApi.invitations).toHaveBeenLastCalledWith(profileId, 2, expect.any(AbortSignal)))
  await screen.findByRole('heading', { name })
  // Loading an uncached page replaces the list/navigation subtree. Return
  // the live page-two navigation rather than the detached page-one element.
  return screen.getByRole('navigation', { name: 'Phân trang lời mời' })
}

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
  vi.spyOn(tenantApi, 'profile').mockResolvedValue(profile)
  vi.spyOn(membersApi, 'members').mockResolvedValue(ownerPage)
  vi.spyOn(membersApi, 'candidates').mockResolvedValue({ ...page([candidate]), capabilities: ownerPage.capabilities })
  vi.spyOn(membersApi, 'invitations').mockResolvedValue(page([]))
  vi.spyOn(membersApi, 'createInvitation').mockResolvedValue(invitation)
  vi.spyOn(membersApi, 'revokeInvitation').mockResolvedValue({ ...invitation, status: 'REVOKED', revoked_at: created })
  vi.spyOn(membersApi, 'resendInvitation').mockResolvedValue(accountInvitation)
})
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('organization roster and invitation authority', () => {
  it('waits for the authorized Profile before fetching private rosters', async () => {
    const pending = deferred<Profile>()
    vi.mocked(tenantApi.profile).mockReturnValue(pending.promise)
    setup()
    expect(screen.getByRole('status', { name: '' })).toBeInTheDocument()
    expect(membersApi.members).not.toHaveBeenCalled()
    expect(membersApi.invitations).not.toHaveBeenCalled()
    await act(async () => pending.resolve(profile))
    expect(await screen.findByText(ownerPage.results[0]?.display_label || '')).toBeInTheDocument()
  })

  it('shows actual names, roles, inactive state and independent Workspace scope without IDs', async () => {
    const owner = ownerPage.results[0]
    if (!owner) throw new Error('Expected the synthetic Owner membership.')
    vi.mocked(membersApi.members).mockResolvedValue({ ...ownerPage, count: 2, results: [...ownerPage.results, { ...owner, id: '00000000-0000-4000-8000-000000000906', display_label: 'Thành viên tạm ngừng', role: 'MEMBER', is_active: false }] })
    setup()
    expect(await screen.findByText('Thành viên tạm ngừng')).toBeInTheDocument()
    expect(screen.getByText('Thành viên · Không hoạt động')).toBeInTheDocument()
    expect(screen.getByText('Chủ sở hữu · Đang hoạt động')).toBeInTheDocument()
    expect(screen.getByText(/Thành viên tổ chức và quyền Workspace được quản lý độc lập/)).toBeInTheDocument()
    expect(screen.queryByText(owner.id)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Đổi vai trò|Loại thành viên/ })).not.toBeInTheDocument()
  })

  it('provides honest empty member and invitation states', async () => {
    vi.mocked(membersApi.members).mockResolvedValue({ ...ownerPage, count: 0, results: [] })
    setup()
    expect(await screen.findByText('Chưa có thành viên để hiển thị')).toBeInTheDocument()
    expect(await screen.findByText('Chưa có lời mời')).toBeInTheDocument()
  })

  it.each([403, 404])('does not fetch invitation emails or expose actions after roster HTTP%s', async (status) => {
    vi.mocked(membersApi.members).mockRejectedValue(new ApiError(status, status === 403 ? 'forbidden' : 'not-found', 'Nội dung không khả dụng.'))
    setup()
    expect(await screen.findByRole('alert')).toHaveTextContent('Nội dung không khả dụng.')
    expect(screen.queryByRole('button', { name: 'Thêm thành viên' })).not.toBeInTheDocument()
    expect(membersApi.invitations).not.toHaveBeenCalled()
    expect(screen.queryByText((invitation.recipient_email ?? ''))).not.toBeInTheDocument()
  })

  it('uses server-owned role choices for Owner without any Owner invitation choice', async () => {
    setup()
    const dialog = await openInvite()
    const options = within(dialog).getAllByRole('option')
    expect(options.map((option) => option.textContent)).toEqual(['Chọn vai trò', 'Thành viên', 'Quản trị viên'])
    expect(within(dialog).queryByRole('option', { name: 'Chủ sở hữu' })).not.toBeInTheDocument()
  })

  it('offers Admin only the allowed Member invitation choice', async () => {
    vi.mocked(membersApi.members).mockResolvedValue({ ...ownerPage, capabilities: { ...ownerPage.capabilities, allowed_invitation_roles: ['MEMBER'] } })
    setup()
    const dialog = await openInvite()
    expect(within(dialog).queryByRole('option', { name: 'Quản trị viên' })).not.toBeInTheDocument()
    expect(within(dialog).getByRole('option', { name: 'Thành viên' })).toBeInTheDocument()
  })

  it('reads archived history but exposes no invitation mutation controls', async () => {
    vi.mocked(tenantApi.profile).mockResolvedValue({ ...profile, status: 'ARCHIVED' })
    vi.mocked(membersApi.members).mockResolvedValue({ ...ownerPage, capabilities: { can_invite: false, can_manage_invitations: false, allowed_invitation_roles: [] } })
    vi.mocked(membersApi.invitations).mockResolvedValue(page([invitation]))
    setup()
    expect(await screen.findByText((invitation.recipient_email ?? ''))).toBeInTheDocument()
    expect(screen.getByText(/Tổ chức đã lưu trữ/)).toBeInTheDocument()
    for (const name of ['Thêm thành viên', 'Hủy lời mời', 'Gửi lại lời mời']) expect(screen.queryByRole('button', { name })).not.toBeInTheDocument()
  })

  it('shows statuses without treating backend email acceptance as delivered membership', async () => {
    vi.mocked(membersApi.invitations).mockResolvedValue(page([invitation, { ...invitation, id: '00000000-0000-4000-8000-000000000907', recipient_email: 'expired@example.test', status: 'EXPIRED', delivery_status: 'FAILED' }]))
    setup()
    const list = await screen.findByRole('list', { name: 'Lời mời tổ chức' })
    const pendingRow = within(list).getByRole('heading', { name: (invitation.recipient_email ?? '') }).closest('li')
    const expiredRow = within(list).getByRole('heading', { name: 'expired@example.test' }).closest('li')
    if (!pendingRow || !expiredRow) throw new Error('Expected both scoped invitation rows.')
    expect(within(pendingRow).getByText('Thành viên · Đang chờ phản hồi')).toBeInTheDocument()
    expect(within(pendingRow).getByText('Hệ thống email đã tiếp nhận')).toBeInTheDocument()
    expect(within(expiredRow).getByText('Thành viên · Đã hết hạn')).toBeInTheDocument()
    expect(within(expiredRow).getByText('Gửi email chưa thành công')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Gửi lại lời mời|Thử gửi lại email/ })).not.toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Hủy lời mời' })).toHaveLength(1)
  })

  it('paginates inside the User/Profile scope without following response URLs', async () => {
    vi.mocked(membersApi.members).mockResolvedValue({ ...ownerPage, count: 21 })
    setup()
    const nav = await screen.findByRole('navigation', { name: 'Phân trang thành viên' })
    await userEvent.setup().click(within(nav).getByRole('button', { name: 'Trang sau' }))
    await waitFor(() => expect(membersApi.members).toHaveBeenLastCalledWith(profileId, 2, expect.any(AbortSignal)))
  })
})

describe('invitation form stability and submission', () => {
  it('debounces server search by300ms, resets the account page and sends no mutation while searching', async () => {
    setup()
    const dialog = await openInvite()
    await within(dialog).findByRole('radio', { name: /Tài khoản mới/ })
    vi.useFakeTimers()
    try {
      fireEvent.change(within(dialog).getByLabelText('Tìm tài khoản'), { target: { value: 'Người mới' } })
      await act(async () => { vi.advanceTimersByTime(299) })
      expect(membersApi.candidates).toHaveBeenCalledTimes(1)
      await act(async () => { vi.advanceTimersByTime(1) })
      expect(membersApi.candidates).toHaveBeenLastCalledWith(profileId, 'Người mới', 1, expect.any(AbortSignal))
      expect(membersApi.createInvitation).not.toHaveBeenCalled()
    } finally { vi.useRealTimers() }
  })
  it('uses disabled server eligibility for active members, pending invitations and ambiguous identities', async () => {
    vi.mocked(membersApi.candidates).mockResolvedValue({ ...page([
      { ...candidate, relation: 'ACTIVE_MEMBER', can_invite: false },
      { ...candidate, id: otherUserId, display_label: 'Đã được mời', relation: 'PENDING_INVITATION', can_invite: false },
      { ...candidate, id: otherProfileId, display_label: 'Trùng tên không rõ', relation: 'UNAVAILABLE', can_invite: false },
    ]), capabilities: ownerPage.capabilities })
    setup()
    const dialog = await openInvite()
    const radios = await within(dialog).findAllByRole('radio')
    expect(radios).toHaveLength(3)
    for (const radio of radios) expect(radio).toBeDisabled()
    expect(within(dialog).queryByLabelText('Email người nhận')).not.toBeInTheDocument()
  })
  it('keeps a selected account across candidate pagination instead of substituting another account', async () => {
    vi.mocked(membersApi.candidates).mockImplementation(async (_profile, _search, current = 1) => ({ ...page(current === 1 ? [candidate] : [{ ...candidate, id: otherUserId, display_label: 'Tài khoản trang hai' }], 21), capabilities: ownerPage.capabilities }))
    // Settle the existing mount-time search debounce before testing pagination.
    // Otherwise its page-one reset can race this unrelated identity assertion.
    vi.useFakeTimers()
    let dialog: HTMLElement
    try {
      setup()
      await act(async () => { await vi.advanceTimersByTimeAsync(1) })
      fireEvent.click(screen.getByRole('button', { name: 'Thêm thành viên' }))
      await act(async () => { await vi.advanceTimersByTimeAsync(1) })
      dialog = screen.getByRole('dialog', { name: 'Mời thành viên' })
      fireEvent.click(within(dialog).getByRole('radio', { name: /Tài khoản mới/ }))
      await act(async () => { await vi.advanceTimersByTimeAsync(300) })
    } finally { vi.useRealTimers() }
    const nav = within(dialog).getByRole('navigation', { name: 'Phân trang tài khoản' })
    await userEvent.setup().click(within(nav).getByRole('button', { name: 'Trang sau' }))
    await within(dialog).findByRole('radio', { name: /Tài khoản trang hai/ })
    expect(within(dialog).getByText(/^Đã chọn:/)).toHaveTextContent('Đã chọn: Tài khoản mới')
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    expect(membersApi.createInvitation).toHaveBeenCalledWith(profileId, { recipient_user_id: recipientUserId, requested_role: 'MEMBER' }, expect.any(AbortSignal))
  })
  it('reports durable Web creation with FAILED email without asking the recipient for a code', async () => {
    const accountInvitation: ProfileInvitation = { ...invitation, acceptance_kind: 'ACCOUNT', recipient_email: null, recipient_display_label: candidate.display_label, recipient_username: candidate.username, recipient_masked_email: null, delivery_status: 'FAILED', delivered_at: null }
    vi.mocked(membersApi.createInvitation).mockResolvedValue(accountInvitation)
    vi.mocked(membersApi.invitations).mockResolvedValueOnce(page([])).mockResolvedValue(page([accountInvitation]))
    setup()
    const dialog = await fillInvite()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    expect(await screen.findByText(/Đã tạo lời mời trên Web\. Email chưa gửi được/)).toBeVisible()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: candidate.display_label })).toBeVisible()
    expect(screen.getByText('Gửi email chưa thành công')).toBeVisible()
    expect(screen.queryByLabelText('Mã lời mời')).not.toBeInTheDocument()
  })
  it('requires an eligible selected account before any mutation', async () => {
    setup()
    const dialog = await openInvite()
    await within(dialog).findByRole('radio', { name: /Tài khoản mới/ })
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    expect(within(dialog).getByRole('alert')).toHaveTextContent('Vui lòng kiểm tra thông tin lời mời.')
    expect(membersApi.createInvitation).not.toHaveBeenCalled()
    expect(within(dialog).getByRole('radio', { name: /Tài khoản mới/ })).not.toBeChecked()
  })

  it('keeps pending form mounted, blocks duplicate submits and closes only after confirmed success', async () => {
    const pending = deferred<ProfileInvitation>()
    vi.mocked(membersApi.createInvitation).mockReturnValue(pending.promise)
    setup()
    const dialog = await fillInvite()
    const submit = within(dialog).getByRole('button', { name: 'Gửi lời mời' })
    await userEvent.setup().click(submit)
    expect(submit).toBeDisabled()
    expect(within(dialog).getByRole('button', { name: 'Đóng' })).toBeDisabled()
    const form = submit.closest('form')
    if (!form) throw new Error('Expected the invitation form.')
    fireEvent.submit(form)
    expect(membersApi.createInvitation).toHaveBeenCalledOnce()
    expect(membersApi.createInvitation).toHaveBeenCalledWith(profileId, { recipient_user_id: recipientUserId, requested_role: 'MEMBER' }, expect.any(AbortSignal))
    expect(dialog.isConnected).toBe(true)
    await act(async () => pending.resolve(invitation))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.getByText(/Đã tạo lời mời trên Web/)).toBeInTheDocument()
  })

  it('retains values and focuses server validation errors without declaring success', async () => {
    vi.mocked(membersApi.createInvitation).mockRejectedValue(new ApiError(400, 'validation', 'Kiểm tra thông tin.', { recipient_user_id: 'Tài khoản chưa đủ điều kiện.' }))
    setup()
    const dialog = await fillInvite()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    const alert = await within(dialog).findByRole('alert')
    expect(alert).toHaveTextContent('Tài khoản chưa đủ điều kiện.')
    await waitFor(() => expect(alert.parentElement).toHaveFocus())
    expect(within(dialog).getByRole('radio', { name: /Tài khoản mới/ })).toBeChecked()
    expect(screen.queryByText(/Đã tạo lời mời trên Web/)).not.toBeInTheDocument()
  })

  it.each([409, 429])('keeps the draft after non-authority HTTP%s', async (status) => {
    vi.mocked(membersApi.createInvitation).mockRejectedValue(new ApiError(status, status === 409 ? 'conflict' : 'throttled', 'Chưa thể xử lý yêu cầu.'))
    setup()
    const dialog = await fillInvite()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Chưa thể xử lý yêu cầu.')
    expect(within(dialog).getByRole('radio', { name: /Tài khoản mới/ })).toBeChecked()
    expect(screen.getByRole('dialog', { name: 'Mời thành viên' })).toBe(dialog)
    expect(membersApi.createInvitation).toHaveBeenCalledOnce()
  })

  it('retains the draft for a recoverable CSRF403 rather than declaring membership lost', async () => {
    vi.mocked(membersApi.createInvitation).mockRejectedValue(new ApiError(403, 'csrf', 'Phiên bảo vệ yêu cầu chưa hợp lệ. Vui lòng thử lại.'))
    setup()
    const dialog = await fillInvite()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Phiên bảo vệ yêu cầu chưa hợp lệ.')
    expect(screen.getByRole('dialog', { name: 'Mời thành viên' })).toBe(dialog)
    expect(within(dialog).getByRole('radio', { name: /Tài khoản mới/ })).toBeChecked()
    expect(membersApi.createInvitation).toHaveBeenCalledOnce()
  })

  it('does not claim a failed delivery means no invitation was stored or automatically retry', async () => {
    vi.mocked(membersApi.createInvitation).mockRejectedValue(new ApiError(503, 'server', 'Dịch vụ chưa khả dụng.'))
    const { cache } = setup()
    const dialog = await fillInvite()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Lời mời có thể đã được lưu.')
    expect(within(dialog).getByRole('button', { name: 'Gửi lời mời' })).toBeDisabled()
    expect(within(dialog).getByRole('alert')).toHaveTextContent('Đóng biểu mẫu và kiểm tra danh sách')
    expect(within(dialog).getByRole('radio', { name: /Tài khoản mới/ })).toBeChecked()
    await waitFor(() => expect(cache.isFetching()).toBe(0))
    expect(screen.getByText('Chưa có lời mời')).toBeInTheDocument()
    expect(screen.queryByText(/Đã tạo lời mời trên Web/)).not.toBeInTheDocument()
    expect(membersApi.createInvitation).toHaveBeenCalledOnce()
    expect(membersApi.invitations).toHaveBeenCalledTimes(2)
  })

  it('preserves the same account/role draft across ordinary rerender and background refetch', async () => {
    const { cache, change, props } = setup()
    const dialog = await fillInvite()
    await userEvent.setup().selectOptions(within(dialog).getByLabelText('Vai trò tổ chức'), 'ADMIN')
    change({ ...props })
    await act(async () => { await Promise.all([
      cache.refetchQueries({ queryKey: memberKeys.profile(currentUserId, profileId) }),
      cache.refetchQueries({ queryKey: queryKeys.profile(profileId) }),
    ]) })
    expect(screen.getByRole('dialog', { name: 'Mời thành viên' })).toBe(dialog)
    expect(within(dialog).getByRole('radio', { name: /Tài khoản mới/ })).toBeChecked()
    expect(within(dialog).getByLabelText('Vai trò tổ chức')).toHaveValue('ADMIN')
    expect(membersApi.createInvitation).not.toHaveBeenCalled()
  })

  it.each(['profile', 'user', 'unmount'] as const)('aborts pending requests and ignores late success on %s changes', async (changeType) => {
    const pending = deferred<ProfileInvitation>()
    vi.mocked(membersApi.createInvitation).mockReturnValue(pending.promise)
    const { change, props, unmount } = setup()
    const dialog = await fillInvite()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    const signal = vi.mocked(membersApi.createInvitation).mock.calls[0]?.[2]
    if (changeType === 'unmount') unmount()
    else change({ ...props, ...(changeType === 'profile' ? { profileId: otherProfileId } : { currentUserId: otherUserId }) })
    expect(signal?.aborted).toBe(true)
    expect(dialog.isConnected).toBe(false)
    await act(async () => pending.resolve(invitation))
    expect(screen.queryByText(/Đã tạo lời mời trên Web/)).not.toBeInTheDocument()
    expect(screen.queryByRole('radio', { name: /Tài khoản mới/ })).not.toBeInTheDocument()
  })

  it('drops old privileged choices and cancels a pending invitation if the role ceiling changes', async () => {
    const pending = deferred<ProfileInvitation>()
    vi.mocked(membersApi.createInvitation).mockReturnValue(pending.promise)
    const { cache } = setup()
    const dialog = await fillInvite()
    await userEvent.setup().selectOptions(within(dialog).getByLabelText('Vai trò tổ chức'), 'ADMIN')
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    const signal = vi.mocked(membersApi.createInvitation).mock.calls[0]?.[2]
    await act(async () => { cache.setQueryData(memberKeys.members(currentUserId, profileId, 1), { ...ownerPage, capabilities: { ...ownerPage.capabilities, allowed_invitation_roles: ['MEMBER'] } }) })
    await waitFor(() => expect(signal?.aborted).toBe(true))
    expect(within(dialog).queryByRole('option', { name: 'Quản trị viên' })).not.toBeInTheDocument()
    expect(within(dialog).getByLabelText('Vai trò tổ chức')).toHaveValue('')
    await act(async () => pending.resolve(invitation))
    expect(screen.queryByText(/Đã tạo lời mời trên Web/)).not.toBeInTheDocument()
  })

  it('removes cached private lists and the draft when scope authority is revoked', async () => {
    vi.mocked(membersApi.invitations).mockResolvedValue(page([invitation]))
    const { cache } = setup()
    const dialog = await fillInvite()
    vi.mocked(membersApi.members).mockRejectedValue(denied())
    await act(async () => { await cache.refetchQueries({ queryKey: memberKeys.members(currentUserId, profileId, 1) }) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Bạn không có quyền quản lý tổ chức.')
    expect(dialog.isConnected).toBe(false)
    expect(screen.queryByText((invitation.recipient_email ?? ''))).not.toBeInTheDocument()
    await waitFor(() => expect(cache.getQueryData(memberKeys.invitations(currentUserId, profileId, 1))).toBeUndefined())
  })
})

describe('pending invitation lifecycle actions', () => {
  it('requires explicit revoke confirmation and refreshes only after the server confirms', async () => {
    const pending = deferred<ProfileInvitation>()
    vi.mocked(membersApi.invitations).mockResolvedValue(page([invitation]))
    vi.mocked(membersApi.revokeInvitation).mockReturnValue(pending.promise)
    setup()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Hủy lời mời' }))
    let dialog = screen.getByRole('dialog', { name: 'Hủy lời mời' })
    expect(membersApi.revokeInvitation).not.toHaveBeenCalled()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Giữ lời mời' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Hủy lời mời' }))
    dialog = screen.getByRole('dialog', { name: 'Hủy lời mời' })
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Xác nhận hủy lời mời' }))
    expect(within(dialog).getByRole('button', { name: 'Xác nhận hủy lời mời' })).toBeDisabled()
    expect(membersApi.revokeInvitation).toHaveBeenCalledWith(profileId, invitation.id, expect.any(AbortSignal))
    const row = screen.getByRole('heading', { name: (invitation.recipient_email ?? '') }).closest('li')
    if (!row) throw new Error('Expected the invitation row being revoked.')
    expect(within(row).getByText('Thành viên · Đang chờ phản hồi')).toBeInTheDocument()
    vi.mocked(membersApi.invitations).mockResolvedValue(page([{ ...invitation, status: 'REVOKED', revoked_at: created }]))
    await act(async () => pending.resolve({ ...invitation, status: 'REVOKED', revoked_at: created }))
    expect(await within(row).findByText('Thành viên · Đã hủy')).toBeInTheDocument()
    expect(screen.getByText('Đã hủy lời mời.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Gửi lại lời mời' })).not.toBeInTheDocument()
  })

  it('refreshes the same account invitation after an explicit email retry without rotating its identity', async () => {
    vi.mocked(membersApi.invitations).mockResolvedValueOnce(page([accountInvitation])).mockResolvedValue(page([{ ...accountInvitation, delivery_status: 'QUEUED' }]))
    setup()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Thử gửi lại email' }))
    expect(membersApi.resendInvitation).toHaveBeenCalledWith(profileId, invitation.id, expect.any(AbortSignal))
    expect(await screen.findByText('Đang chờ xử lý email')).toBeInTheDocument()
    expect(screen.getByText(/Lời mời, vai trò và thời hạn trên Web được giữ nguyên/)).toBeInTheDocument()
    expect(screen.queryByText(/token|https:\/\/.*invitation/i)).not.toBeInTheDocument()
  })

  it.each(['PENDING', 'EXPIRED'] as const)('retains legacy%s history without promoting token resend', async (status) => {
    vi.mocked(membersApi.invitations).mockResolvedValue(page([{ ...invitation, acceptance_kind: 'EMAIL_TOKEN', status, delivery_status: 'FAILED' }]))
    setup()
    expect(await screen.findByRole('heading', { name: invitation.recipient_email ?? '' })).toBeVisible()
    expect(screen.queryByRole('button', { name: /Gửi lại lời mời|Thử gửi lại email/ })).not.toBeInTheDocument()
    expect(membersApi.resendInvitation).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Hủy lời mời' }) !== null).toBe(status === 'PENDING')
    expect(screen.queryByText(/Mã cũ|lời mời thay thế/)).not.toBeInTheDocument()
  })
})

describe('invitation delivery outcomes remain visible across pagination', () => {
  it('returns to page one after confirmed creation and shows the new invitation', async () => {
    const collection = paginatedInvitations()
    const createdInvitation = { ...invitation, recipient_email: 'new-member@example.test', id: '00000000-0000-4000-8000-000000000909' }
    vi.mocked(membersApi.createInvitation).mockImplementationOnce(async () => {
      collection.setNewest(createdInvitation)
      return createdInvitation
    })
    setup()
    await secondInvitationPage()
    const dialog = await fillInvite()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    await waitFor(() => expect(dialog).not.toBeInTheDocument())
    const list = screen.getByRole('list', { name: 'Lời mời tổ chức' })
    expect(await within(list).findByRole('heading', { name: createdInvitation.recipient_email })).toBeInTheDocument()
    expect(within(screen.getByRole('navigation', { name: 'Phân trang lời mời' })).getByText('Trang 1 / 2')).toBeInTheDocument()
    expect(within(list).queryByRole('heading', { name: (collection.older.recipient_email ?? '') })).not.toBeInTheDocument()
    expect(membersApi.createInvitation).toHaveBeenCalledOnce()
  })

  it('shows a committed FAILED row on page one after creation503 while keeping the same draft', async () => {
    const collection = paginatedInvitations()
    const failedInvitation: ProfileInvitation = { ...invitation, recipient_email: 'new-member@example.test', id: '00000000-0000-4000-8000-000000000909', delivery_status: 'FAILED', delivered_at: null }
    vi.mocked(membersApi.createInvitation).mockImplementationOnce(async () => {
      collection.setNewest(failedInvitation)
      throw new ApiError(503, 'server', 'Untrusted transport details')
    })
    setup()
    await secondInvitationPage()
    const dialog = await fillInvite()
    const email = within(dialog).getByRole('radio', { name: /Tài khoản mới/ })
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Chưa thể xác nhận kết quả.')
    const list = screen.getByRole('list', { name: 'Lời mời tổ chức' })
    expect(await within(list).findByRole('heading', { name: (failedInvitation.recipient_email ?? '') })).toBeInTheDocument()
    expect(within(list).getByText('Gửi email chưa thành công')).toBeInTheDocument()
    expect(within(list).getByText('Thành viên · Đang chờ phản hồi')).toBeInTheDocument()
    expect(within(screen.getByRole('navigation', { name: 'Phân trang lời mời' })).getByText('Trang 1 / 2')).toBeInTheDocument()
    expect(screen.getByRole('dialog', { name: 'Mời thành viên' })).toBe(dialog)
    expect(within(dialog).getByRole('radio', { name: /Tài khoản mới/ })).toBe(email)
    expect(email).toBeChecked()
    expect(screen.queryByText('Untrusted transport details')).not.toBeInTheDocument()
    expect(screen.queryByText(/Đã tạo lời mời trên Web/)).not.toBeInTheDocument()
    expect(membersApi.createInvitation).toHaveBeenCalledOnce()
  })

  it('keeps the same invitation and page after successful email retry from page two', async () => {
    const collection = paginatedInvitations(true)
    const refreshed: ProfileInvitation = { ...collection.older, delivery_status: 'SENT' }
    vi.mocked(membersApi.resendInvitation).mockImplementationOnce(async () => {
      collection.setOlder(refreshed)
      return refreshed
    })
    setup()
    await secondInvitationPage('Tài khoản cũ')
    const row = screen.getByRole('heading', { name: 'Tài khoản cũ' }).closest('li')
    if (!row) throw new Error('Expected the old invitation on page two.')
    await userEvent.setup().click(within(row).getByRole('button', { name: 'Thử gửi lại email' }))
    expect(await screen.findByText(/Lời mời, vai trò và thời hạn trên Web được giữ nguyên/)).toBeInTheDocument()
    await waitFor(() => expect(within(screen.getByRole('navigation', { name: 'Phân trang lời mời' })).getByText('Trang 2 / 2')).toBeInTheDocument())
    await waitFor(() => {
      expect(membersApi.invitations).toHaveBeenLastCalledWith(profileId, 2, expect.any(AbortSignal))
    })
    expect(membersApi.resendInvitation).toHaveBeenCalledOnce()
    expect(membersApi.resendInvitation).toHaveBeenCalledWith(profileId, collection.older.id, expect.any(AbortSignal))
    expect(screen.getByText('Hệ thống email đã tiếp nhận')).toBeInTheDocument()
  })

  it('keeps a failed email retry visible on the same invitation and page', async () => {
    const collection = paginatedInvitations(true)
    const refreshed: ProfileInvitation = { ...collection.older, delivery_status: 'FAILED', delivered_at: null }
    vi.mocked(membersApi.resendInvitation).mockImplementationOnce(async () => {
      collection.setOlder(refreshed)
      return refreshed
    })
    setup()
    await secondInvitationPage('Tài khoản cũ')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Thử gửi lại email' }))
    const notice = await screen.findByRole('alert')
    expect(notice).toHaveTextContent('Lời mời trên Web vẫn còn hiệu lực, nhưng lần thử gửi email chưa thành công.')
    await waitFor(() => expect(within(screen.getByRole('navigation', { name: 'Phân trang lời mời' })).getByText('Trang 2 / 2')).toBeInTheDocument())
    expect(await screen.findByText('Gửi email chưa thành công')).toBeInTheDocument()
    expect(notice).toBeInTheDocument()
    expect(screen.getAllByRole('alert')).toHaveLength(1)
    expect(screen.queryByText('Untrusted transport details')).not.toBeInTheDocument()
    expect(screen.queryByText(/Đã tạo lời mời thay thế/)).not.toBeInTheDocument()
    expect(membersApi.resendInvitation).toHaveBeenCalledOnce()
    expect(membersApi.resendInvitation).toHaveBeenCalledWith(profileId, collection.older.id, expect.any(AbortSignal))
  })

  it('shows an uncertain email retry failure without inventing a replacement or optimistic success', async () => {
    vi.mocked(membersApi.invitations).mockResolvedValue(page([accountInvitation]))
    vi.mocked(membersApi.resendInvitation).mockRejectedValue(new ApiError(503, 'server', 'Untrusted transport details'))
    const { cache } = setup()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Thử gửi lại email' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Chưa thể xác nhận kết quả. Kiểm tra lại danh sách trước khi thao tác tiếp.')
    await waitFor(() => expect(cache.isFetching()).toBe(0))
    expect(screen.getByRole('heading', { name: accountInvitation.recipient_display_label })).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { name: accountInvitation.recipient_display_label })).toHaveLength(1)
    expect(membersApi.resendInvitation).toHaveBeenCalledOnce()
    expect(screen.queryByText(/Đã tạo lời mời thay thế/)).not.toBeInTheDocument()
    expect(screen.queryByText('Untrusted transport details')).not.toBeInTheDocument()
  })

  it('keeps page two and the same form during ordinary background refresh', async () => {
    const collection = paginatedInvitations()
    const { cache } = setup()
    const nav = await secondInvitationPage()
    const dialog = await fillInvite()
    const email = within(dialog).getByRole('radio', { name: /Tài khoản mới/ })
    await userEvent.setup().selectOptions(within(dialog).getByLabelText('Vai trò tổ chức'), 'ADMIN')
    await act(async () => { await cache.refetchQueries({ queryKey: memberKeys.profile(currentUserId, profileId) }) })
    expect(within(nav).getByText('Trang 2 / 2')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: (collection.older.recipient_email ?? '') })).toBeInTheDocument()
    expect(screen.getByRole('dialog', { name: 'Mời thành viên' })).toBe(dialog)
    expect(within(dialog).getByRole('radio', { name: /Tài khoản mới/ })).toBe(email)
    expect(email).toBeChecked()
    expect(within(dialog).getByLabelText('Vai trò tổ chức')).toHaveValue('ADMIN')
    expect(membersApi.createInvitation).not.toHaveBeenCalled()
    expect(membersApi.resendInvitation).not.toHaveBeenCalled()
  })
})

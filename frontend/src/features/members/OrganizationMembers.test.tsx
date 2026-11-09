/** Real membership components with mocked services; isolated browser proof is separate. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/api/client'
import { memberKeys, membersApi } from '../../services/api/members'
import type { ProfileInvitation, ProfileMembersPage } from '../../services/api/members'
import { queryKeys, tenantApi } from '../../services/api/queries'
import type { Page, Profile } from '../../services/api/types'
import { OrganizationMembers } from './OrganizationMembers'

const profileId = '00000000-0000-4000-8000-000000000901'
const currentUserId = '00000000-0000-4000-8000-000000000902'
const otherProfileId = '00000000-0000-4000-8000-000000000911'
const otherUserId = '00000000-0000-4000-8000-000000000912'
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
  await userEvent.setup().click(await screen.findByRole('button', { name: 'Mời thành viên' }))
  return screen.getByRole('dialog', { name: 'Mời thành viên' })
}
async function fillInvite(email = 'new-member@example.test') {
  const dialog = await openInvite()
  await userEvent.setup().type(within(dialog).getByLabelText('Email người nhận'), email)
  return dialog
}
function paginatedInvitations() {
  const older: ProfileInvitation = { ...invitation, id: '00000000-0000-4000-8000-000000000908', recipient_email: 'older@example.test' }
  let newest: ProfileInvitation | undefined
  vi.mocked(membersApi.invitations).mockImplementation(async (_profileId, currentPage = 1) => page(
    currentPage === 1 ? [newest || invitation] : [older], newest ? 22 : 21,
  ))
  return { older, setNewest: (value: ProfileInvitation) => { newest = value } }
}
async function secondInvitationPage() {
  const nav = await screen.findByRole('navigation', { name: 'Phân trang lời mời' })
  await userEvent.setup().click(within(nav).getByRole('button', { name: 'Trang sau' }))
  await waitFor(() => expect(membersApi.invitations).toHaveBeenLastCalledWith(profileId, 2, expect.any(AbortSignal)))
  await screen.findByRole('heading', { name: 'older@example.test' })
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
  vi.spyOn(membersApi, 'invitations').mockResolvedValue(page([]))
  vi.spyOn(membersApi, 'createInvitation').mockResolvedValue(invitation)
  vi.spyOn(membersApi, 'revokeInvitation').mockResolvedValue({ ...invitation, status: 'REVOKED', revoked_at: created })
  vi.spyOn(membersApi, 'resendInvitation').mockResolvedValue({ ...invitation, id: '00000000-0000-4000-8000-000000000905' })
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
    expect(screen.queryByRole('button', { name: 'Mời thành viên' })).not.toBeInTheDocument()
    expect(membersApi.invitations).not.toHaveBeenCalled()
    expect(screen.queryByText(invitation.recipient_email)).not.toBeInTheDocument()
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
    expect(await screen.findByText(invitation.recipient_email)).toBeInTheDocument()
    expect(screen.getByText(/Tổ chức đã lưu trữ/)).toBeInTheDocument()
    for (const name of ['Mời thành viên', 'Hủy lời mời', 'Gửi lại lời mời']) expect(screen.queryByRole('button', { name })).not.toBeInTheDocument()
  })

  it('shows statuses without treating backend email acceptance as delivered membership', async () => {
    vi.mocked(membersApi.invitations).mockResolvedValue(page([invitation, { ...invitation, id: '00000000-0000-4000-8000-000000000907', recipient_email: 'expired@example.test', status: 'EXPIRED', delivery_status: 'FAILED' }]))
    setup()
    const list = await screen.findByRole('list', { name: 'Lời mời tổ chức' })
    const pendingRow = within(list).getByRole('heading', { name: invitation.recipient_email }).closest('li')
    const expiredRow = within(list).getByRole('heading', { name: 'expired@example.test' }).closest('li')
    if (!pendingRow || !expiredRow) throw new Error('Expected both scoped invitation rows.')
    expect(within(pendingRow).getByText('Thành viên · Đang chờ phản hồi')).toBeInTheDocument()
    expect(within(pendingRow).getByText('Hệ thống email đã tiếp nhận')).toBeInTheDocument()
    expect(within(expiredRow).getByText('Thành viên · Đã hết hạn')).toBeInTheDocument()
    expect(within(expiredRow).getByText('Gửi email chưa thành công')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Gửi lại lời mời' })).toHaveLength(2)
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
  it('validates email before issuing any mutation', async () => {
    setup()
    const dialog = await fillInvite('not-an-email')
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    expect(within(dialog).getByRole('alert')).toHaveTextContent('Vui lòng kiểm tra thông tin lời mời.')
    expect(membersApi.createInvitation).not.toHaveBeenCalled()
    expect(within(dialog).getByLabelText('Email người nhận')).toHaveValue('not-an-email')
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
    expect(membersApi.createInvitation).toHaveBeenCalledWith(profileId, { recipient_email: 'new-member@example.test', requested_role: 'MEMBER' }, expect.any(AbortSignal))
    expect(dialog.isConnected).toBe(true)
    await act(async () => pending.resolve(invitation))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.getByText(/Đã tạo lời mời\. Hãy xem trạng thái email/)).toBeInTheDocument()
  })

  it('retains values and focuses server validation errors without declaring success', async () => {
    vi.mocked(membersApi.createInvitation).mockRejectedValue(new ApiError(400, 'validation', 'Kiểm tra thông tin.', { recipient_email: 'Địa chỉ email chưa hợp lệ.' }))
    setup()
    const dialog = await fillInvite()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    const alert = await within(dialog).findByRole('alert')
    expect(alert).toHaveTextContent('Địa chỉ email chưa hợp lệ.')
    await waitFor(() => expect(alert.parentElement).toHaveFocus())
    expect(within(dialog).getByLabelText('Email người nhận')).toHaveValue('new-member@example.test')
    expect(screen.queryByText(/Đã tạo lời mời\. Hãy xem/)).not.toBeInTheDocument()
  })

  it.each([409, 429])('keeps the draft after non-authority HTTP%s', async (status) => {
    vi.mocked(membersApi.createInvitation).mockRejectedValue(new ApiError(status, status === 409 ? 'conflict' : 'throttled', 'Chưa thể xử lý yêu cầu.'))
    setup()
    const dialog = await fillInvite()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Chưa thể xử lý yêu cầu.')
    expect(within(dialog).getByLabelText('Email người nhận')).toHaveValue('new-member@example.test')
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
    expect(within(dialog).getByLabelText('Email người nhận')).toHaveValue('new-member@example.test')
    expect(membersApi.createInvitation).toHaveBeenCalledOnce()
  })

  it('does not claim a failed delivery means no invitation was stored or automatically retry', async () => {
    vi.mocked(membersApi.createInvitation).mockRejectedValue(new ApiError(503, 'server', 'Dịch vụ chưa khả dụng.'))
    const { cache } = setup()
    const dialog = await fillInvite()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Lời mời có thể đã được lưu.')
    expect(within(dialog).getByRole('alert')).toHaveTextContent('Dịch vụ email hiện chưa sẵn sàng hoặc chưa được cấu hình.')
    expect(within(dialog).getByRole('alert')).toHaveTextContent('liên hệ quản trị để kiểm tra cấu hình email')
    expect(within(dialog).getByLabelText('Email người nhận')).toHaveValue('new-member@example.test')
    await waitFor(() => expect(cache.isFetching()).toBe(0))
    expect(screen.getByText('Chưa có lời mời')).toBeInTheDocument()
    expect(screen.queryByText(/Đã tạo lời mời\. Hãy xem/)).not.toBeInTheDocument()
    expect(membersApi.createInvitation).toHaveBeenCalledOnce()
    expect(membersApi.invitations).toHaveBeenCalledTimes(2)
  })

  it('preserves the same email/role draft across ordinary rerender and background refetch', async () => {
    const { cache, change, props } = setup()
    const dialog = await fillInvite()
    await userEvent.setup().selectOptions(within(dialog).getByLabelText('Vai trò tổ chức'), 'ADMIN')
    change({ ...props })
    await act(async () => { await Promise.all([
      cache.refetchQueries({ queryKey: memberKeys.profile(currentUserId, profileId) }),
      cache.refetchQueries({ queryKey: queryKeys.profile(profileId) }),
    ]) })
    expect(screen.getByRole('dialog', { name: 'Mời thành viên' })).toBe(dialog)
    expect(within(dialog).getByLabelText('Email người nhận')).toHaveValue('new-member@example.test')
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
    expect(screen.queryByText(/Đã tạo lời mời\. Hãy xem/)).not.toBeInTheDocument()
    expect(screen.queryByDisplayValue('new-member@example.test')).not.toBeInTheDocument()
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
    expect(screen.queryByText(/Đã tạo lời mời\. Hãy xem/)).not.toBeInTheDocument()
  })

  it('removes cached private lists and the draft when scope authority is revoked', async () => {
    vi.mocked(membersApi.invitations).mockResolvedValue(page([invitation]))
    const { cache } = setup()
    const dialog = await fillInvite()
    vi.mocked(membersApi.members).mockRejectedValue(denied())
    await act(async () => { await cache.refetchQueries({ queryKey: memberKeys.members(currentUserId, profileId, 1) }) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Bạn không có quyền quản lý tổ chức.')
    expect(dialog.isConnected).toBe(false)
    expect(screen.queryByText(invitation.recipient_email)).not.toBeInTheDocument()
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
    const row = screen.getByRole('heading', { name: invitation.recipient_email }).closest('li')
    if (!row) throw new Error('Expected the invitation row being revoked.')
    expect(within(row).getByText('Thành viên · Đang chờ phản hồi')).toBeInTheDocument()
    vi.mocked(membersApi.invitations).mockResolvedValue(page([{ ...invitation, status: 'REVOKED', revoked_at: created }]))
    await act(async () => pending.resolve({ ...invitation, status: 'REVOKED', revoked_at: created }))
    expect(await within(row).findByText('Thành viên · Đã hủy')).toBeInTheDocument()
    expect(screen.getByText('Đã hủy lời mời.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Gửi lại lời mời' })).not.toBeInTheDocument()
  })

  it('refreshes the list after resend rotates to a different invitation without exposing a token', async () => {
    vi.mocked(membersApi.invitations).mockResolvedValueOnce(page([invitation])).mockResolvedValue(page([{ ...invitation, id: '00000000-0000-4000-8000-000000000905', delivery_status: 'QUEUED' }]))
    setup()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Gửi lại lời mời' }))
    expect(membersApi.resendInvitation).toHaveBeenCalledWith(profileId, invitation.id, expect.any(AbortSignal))
    expect(await screen.findByText('Đang chờ xử lý email')).toBeInTheDocument()
    expect(screen.getByText(/Đã tạo lời mời thay thế/)).toBeInTheDocument()
    expect(screen.queryByText(/token|https:\/\/.*invitation/i)).not.toBeInTheDocument()
  })

  it('supports the existing expired-invitation resend contract without offering revoke', async () => {
    vi.mocked(membersApi.invitations).mockResolvedValue(page([{ ...invitation, status: 'EXPIRED', delivery_status: 'FAILED' }]))
    setup()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Gửi lại lời mời' }))
    expect(membersApi.resendInvitation).toHaveBeenCalledWith(profileId, invitation.id, expect.any(AbortSignal))
    expect(screen.queryByRole('button', { name: 'Hủy lời mời' })).not.toBeInTheDocument()
    expect(await screen.findByText(/Đã tạo lời mời thay thế/)).toBeInTheDocument()
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
    expect(within(list).queryByRole('heading', { name: collection.older.recipient_email })).not.toBeInTheDocument()
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
    const email = within(dialog).getByLabelText('Email người nhận')
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Gửi lời mời' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Chưa thể xác nhận việc gửi email.')
    const list = screen.getByRole('list', { name: 'Lời mời tổ chức' })
    expect(await within(list).findByRole('heading', { name: failedInvitation.recipient_email })).toBeInTheDocument()
    expect(within(list).getByText('Gửi email chưa thành công')).toBeInTheDocument()
    expect(within(list).getByText('Thành viên · Đang chờ phản hồi')).toBeInTheDocument()
    expect(within(screen.getByRole('navigation', { name: 'Phân trang lời mời' })).getByText('Trang 1 / 2')).toBeInTheDocument()
    expect(screen.getByRole('dialog', { name: 'Mời thành viên' })).toBe(dialog)
    expect(within(dialog).getByLabelText('Email người nhận')).toBe(email)
    expect(email).toHaveValue('new-member@example.test')
    expect(screen.queryByText('Untrusted transport details')).not.toBeInTheDocument()
    expect(screen.queryByText(/Đã tạo lời mời\. Hãy xem/)).not.toBeInTheDocument()
    expect(membersApi.createInvitation).toHaveBeenCalledOnce()
  })

  it('shows the replacement on page one after successful resend from page two', async () => {
    const collection = paginatedInvitations()
    const replacement: ProfileInvitation = { ...collection.older, id: '00000000-0000-4000-8000-000000000909' }
    vi.mocked(membersApi.resendInvitation).mockImplementationOnce(async () => {
      collection.setNewest(replacement)
      return replacement
    })
    setup()
    await secondInvitationPage()
    const row = screen.getByRole('heading', { name: collection.older.recipient_email }).closest('li')
    if (!row) throw new Error('Expected the old invitation on page two.')
    await userEvent.setup().click(within(row).getByRole('button', { name: 'Gửi lại lời mời' }))
    expect(await screen.findByText(/Đã tạo lời mời thay thế/)).toBeInTheDocument()
    await waitFor(() => expect(within(screen.getByRole('navigation', { name: 'Phân trang lời mời' })).getByText('Trang 1 / 2')).toBeInTheDocument())
    await waitFor(() => {
      expect(membersApi.invitations).toHaveBeenLastCalledWith(profileId, 1, expect.any(AbortSignal))
    })
    expect(membersApi.resendInvitation).toHaveBeenCalledOnce()
    expect(membersApi.resendInvitation).toHaveBeenCalledWith(profileId, collection.older.id, expect.any(AbortSignal))
    expect(screen.getByText('Hệ thống email đã tiếp nhận')).toBeInTheDocument()
  })

  it('retains a safe resend503 notice when the new FAILED replacement moves to page one', async () => {
    const collection = paginatedInvitations()
    const replacement: ProfileInvitation = { ...collection.older, id: '00000000-0000-4000-8000-000000000909', delivery_status: 'FAILED', delivered_at: null }
    vi.mocked(membersApi.resendInvitation).mockImplementationOnce(async () => {
      collection.setNewest(replacement)
      throw new ApiError(503, 'server', 'Untrusted transport details')
    })
    setup()
    await secondInvitationPage()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Gửi lại lời mời' }))
    const notice = await screen.findByRole('alert')
    expect(notice).toHaveTextContent('Dịch vụ email hiện chưa sẵn sàng hoặc chưa được cấu hình.')
    await waitFor(() => expect(within(screen.getByRole('navigation', { name: 'Phân trang lời mời' })).getByText('Trang 1 / 2')).toBeInTheDocument())
    expect(await screen.findByText('Gửi email chưa thành công')).toBeInTheDocument()
    expect(notice).toBeInTheDocument()
    expect(notice).toHaveTextContent('Lời mời có thể đã được lưu.')
    expect(screen.getAllByRole('alert')).toHaveLength(1)
    expect(screen.queryByText('Untrusted transport details')).not.toBeInTheDocument()
    expect(screen.queryByText(/Đã tạo lời mời thay thế/)).not.toBeInTheDocument()
    expect(membersApi.resendInvitation).toHaveBeenCalledOnce()
    expect(membersApi.resendInvitation).toHaveBeenCalledWith(profileId, collection.older.id, expect.any(AbortSignal))
  })

  it('shows truthful resend503 configuration guidance without inventing a replacement when none was stored', async () => {
    vi.mocked(membersApi.invitations).mockResolvedValue(page([invitation]))
    vi.mocked(membersApi.resendInvitation).mockRejectedValue(new ApiError(503, 'server', 'Untrusted transport details'))
    const { cache } = setup()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Gửi lại lời mời' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('liên hệ quản trị để kiểm tra cấu hình email')
    await waitFor(() => expect(cache.isFetching()).toBe(0))
    expect(screen.getByRole('heading', { name: invitation.recipient_email })).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { name: invitation.recipient_email })).toHaveLength(1)
    expect(membersApi.resendInvitation).toHaveBeenCalledOnce()
    expect(screen.queryByText(/Đã tạo lời mời thay thế/)).not.toBeInTheDocument()
    expect(screen.queryByText('Untrusted transport details')).not.toBeInTheDocument()
  })

  it('keeps page two and the same form during ordinary background refresh', async () => {
    const collection = paginatedInvitations()
    const { cache } = setup()
    const nav = await secondInvitationPage()
    const dialog = await fillInvite()
    const email = within(dialog).getByLabelText('Email người nhận')
    await userEvent.setup().selectOptions(within(dialog).getByLabelText('Vai trò tổ chức'), 'ADMIN')
    await act(async () => { await cache.refetchQueries({ queryKey: memberKeys.profile(currentUserId, profileId) }) })
    expect(within(nav).getByText('Trang 2 / 2')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: collection.older.recipient_email })).toBeInTheDocument()
    expect(screen.getByRole('dialog', { name: 'Mời thành viên' })).toBe(dialog)
    expect(within(dialog).getByLabelText('Email người nhận')).toBe(email)
    expect(email).toHaveValue('new-member@example.test')
    expect(within(dialog).getByLabelText('Vai trò tổ chức')).toHaveValue('ADMIN')
    expect(membersApi.createInvitation).not.toHaveBeenCalled()
    expect(membersApi.resendInvitation).not.toHaveBeenCalled()
  })
})

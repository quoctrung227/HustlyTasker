import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/api/client'
import { notificationKeys } from '../../services/api/collaboration'
import { memberKeys, membersApi } from '../../services/api/members'
import type { RecipientInvitation } from '../../services/api/members'
import { InvitationDecision } from './InvitationDecision'

const userId = '00000000-0000-4000-8000-000000002001'
const invitation: RecipientInvitation = { id: '00000000-0000-4000-8000-000000002002', profile_id: '00000000-0000-4000-8000-000000002003',
  profile_name: 'Tổ chức nhận lời mời', inviter_display_label: 'Người mời hợp lệ', requested_role: 'MEMBER', status: 'PENDING', expires_at: '2026-11-20T00:00:00Z',
  can_accept: true, can_decline: true, can_open_profile: false }
const accepted: RecipientInvitation = { ...invitation, status: 'ACCEPTED', can_accept: false, can_decline: false, can_open_profile: true }
const declined: RecipientInvitation = { ...invitation, status: 'DECLINED', can_accept: false, can_decline: false }
function deferred<T>() { let resolve!: (value: T) => void; return { promise: new Promise<T>((done) => { resolve = done }), resolve: (value: T) => resolve(value) } }
function DecisionHarness({ initial }: { initial: RecipientInvitation }) {
  const [current, setCurrent] = useState(initial)
  return <InvitationDecision key={`${userId}:${current.id}`} userId={userId} invitation={current} onUpdated={setCurrent} />
}
function setup(initial = invitation) {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { retry: false } } })
  cache.setQueryData(notificationKeys.feed(userId), { count: 1, next: null, previous: null, results: [{ id: 'notification', target_type: 'PROFILE_INVITATION', invitation_id: initial.id, invitation: initial, is_read: false }] })
  return { cache, ...render(<QueryClientProvider client={cache}><MemoryRouter><DecisionHarness initial={initial} /></MemoryRouter></QueryClientProvider>) }
}
beforeEach(() => {
  vi.spyOn(membersApi, 'acceptAccountInvitation').mockResolvedValue(accepted)
  vi.spyOn(membersApi, 'declineAccountInvitation').mockResolvedValue(declined)
  vi.spyOn(membersApi, 'recipientInvitation').mockResolvedValue(invitation)
})
afterEach(() => { vi.restoreAllMocks() })

describe('explicit account invitation decisions', () => {
  it('offers only server-authorized actions, without consuming a decision merely by rendering', () => {
    setup()
    expect(screen.getByRole('button', { name: 'Chấp nhận lời mời' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Từ chối lời mời' })).toBeEnabled()
    expect(membersApi.acceptAccountInvitation).not.toHaveBeenCalled()
    expect(membersApi.declineAccountInvitation).not.toHaveBeenCalled()
    expect(screen.getByText(/Đọc thông báo không đồng nghĩa/)).toBeVisible()
  })
  it('waits for server confirmation, blocks double-clicks and refreshes existing profile queries', async () => {
    const pending = deferred<RecipientInvitation>()
    vi.mocked(membersApi.acceptAccountInvitation).mockReturnValue(pending.promise)
    const { cache } = setup()
    const invalidate = vi.spyOn(cache, 'invalidateQueries')
    const user = userEvent.setup(), button = screen.getByRole('button', { name: 'Chấp nhận lời mời' })
    await user.click(button); await user.click(button)
    expect(button).toBeDisabled()
    expect(screen.queryByRole('link', { name: 'Đến tổ chức' })).not.toBeInTheDocument()
    expect(screen.getByText(/Đang chờ phản hồi/)).toBeVisible()
    expect(membersApi.acceptAccountInvitation).toHaveBeenCalledExactlyOnceWith(invitation.id, expect.any(AbortSignal))
    await act(async () => pending.resolve(accepted))
    expect(await screen.findByRole('link', { name: 'Đến tổ chức' })).toHaveAttribute('href', `/profiles/${invitation.profile_id}`)
    expect(screen.queryByRole('button', { name: 'Chấp nhận lời mời' })).not.toBeInTheDocument()
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['profiles'] })
    const notifications = cache.getQueryData<{ results: { is_read: boolean; invitation: RecipientInvitation }[] }>(notificationKeys.feed(userId))
    expect(notifications?.results[0]?.is_read).toBe(false)
    expect(notifications?.results[0]?.invitation.status).toBe('ACCEPTED')
  })
  it('requires a separate explicit decline confirmation and never creates a membership', async () => {
    setup()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Từ chối lời mời' }))
    expect(membersApi.declineAccountInvitation).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Quay lại' }))
    expect(membersApi.declineAccountInvitation).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Từ chối lời mời' }))
    await user.click(screen.getByRole('button', { name: 'Xác nhận từ chối' }))
    expect(await screen.findByText(/Đã từ chối lời mời; không tạo tư cách thành viên/)).toBeVisible()
    expect(membersApi.acceptAccountInvitation).not.toHaveBeenCalled()
    expect(membersApi.declineAccountInvitation).toHaveBeenCalledOnce()
    expect(screen.queryByRole('link', { name: 'Đến tổ chức' })).not.toBeInTheDocument()
  })
  it.each(['DECLINED', 'REVOKED', 'EXPIRED'] as const)('offers no mutation for terminal %s invitations', (status) => {
    setup({ ...invitation, status, can_accept: false, can_decline: false })
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
  it('does not present historical acceptance as current access when membership has been revoked', () => {
    setup({ ...accepted, can_open_profile: false })
    expect(screen.getByText(/Đã chấp nhận/)).toBeVisible()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Đến tổ chức' })).not.toBeInTheDocument()
  })
  it('does not automatically replay an uncertain decision; explicit GET refresh resolves the outcome', async () => {
    vi.mocked(membersApi.acceptAccountInvitation).mockRejectedValue(new ApiError(0, 'network', 'Mất kết nối.'))
    vi.mocked(membersApi.recipientInvitation).mockResolvedValue(accepted)
    setup()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Chấp nhận lời mời' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('hệ thống không tự gửi lại quyết định')
    expect(screen.getByRole('button', { name: 'Chấp nhận lời mời' })).toBeDisabled()
    expect(membersApi.acceptAccountInvitation).toHaveBeenCalledOnce()
    expect(membersApi.recipientInvitation).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Làm mới trạng thái lời mời' }))
    expect(await screen.findByRole('link', { name: 'Đến tổ chức' })).toBeVisible()
    expect(membersApi.recipientInvitation).toHaveBeenCalledExactlyOnceWith(invitation.id, expect.any(AbortSignal))
    expect(membersApi.acceptAccountInvitation).toHaveBeenCalledOnce()
  })
  it.each([400, 403, 404, 409, 429])('shows HTTP%s without retrying or claiming a successful response', async (status) => {
    vi.mocked(membersApi.acceptAccountInvitation).mockRejectedValue(new ApiError(status, status === 429 ? 'throttled' : 'conflict', 'Không thể xử lý lời mời.'))
    setup()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Chấp nhận lời mời' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể xử lý lời mời.')
    expect(screen.queryByRole('link', { name: 'Đến tổ chức' })).not.toBeInTheDocument()
    expect(membersApi.acceptAccountInvitation).toHaveBeenCalledOnce()
  })
  it('aborts on unmount and ignores late mutation success', async () => {
    const pending = deferred<RecipientInvitation>()
    vi.mocked(membersApi.acceptAccountInvitation).mockReturnValue(pending.promise)
    const { cache, unmount } = setup()
    const invalidation = vi.spyOn(cache, 'invalidateQueries')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Chấp nhận lời mời' }))
    const signal = vi.mocked(membersApi.acceptAccountInvitation).mock.calls[0]?.[1]
    unmount()
    expect(signal?.aborted).toBe(true)
    await act(async () => pending.resolve(accepted))
    await waitFor(() => expect(invalidation).not.toHaveBeenCalled())
    expect(cache.getQueryData(memberKeys.recipient(userId, invitation.id))).toBeUndefined()
  })
})

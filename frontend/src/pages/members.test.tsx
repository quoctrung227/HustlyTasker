/** Real route/auth/form lifecycles; service responses are mocked, not live E2E. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppRoutes } from '../app/App'
import { AuthProvider } from '../features/auth/AuthProvider'
import { ApiError, apiClient } from '../services/api/client'
import { notificationApi } from '../services/api/collaboration'
import { membersApi } from '../services/api/members'
import { authApi, tenantApi } from '../services/api/queries'
import type { User } from '../services/api/types'

const user: User = { id: '00000000-0000-4000-8000-000000000901', email: 'recipient@example.test', username: 'recipient', first_name: 'Người nhận', last_name: '', created_at: '2026-10-26T00:00:00Z', email_verified: false }
const other: User = { ...user, id: '00000000-0000-4000-8000-000000000902', email: 'other@example.test', first_name: 'Người khác' }
const profileId = '00000000-0000-4000-8000-000000000903'
const accepted = { status: 'ACCEPTED' as const, profile_id: profileId, membership_id: '00000000-0000-4000-8000-000000000904', role: 'MEMBER' as const }
const token = 'synthetic-invitation-credential-for-local-tests'
const path = '/invitations/respond'
function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (error: unknown) => void
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail })
  return { promise, resolve, reject }
}
function LocationProbe() {
  const location = useLocation()
  return <output data-testid="invitation-location">{JSON.stringify({ path: location.pathname, search: location.search, hash: location.hash, state: location.state })}</output>
}
function setup(initialPath = path, state?: unknown) {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity, refetchOnWindowFocus: false } } })
  const url = new URL(initialPath, 'https://test.invalid')
  render(<QueryClientProvider client={cache}><MemoryRouter initialEntries={[{ pathname: url.pathname, search: url.search, hash: url.hash, state }]}><AuthProvider><LocationProbe /><AppRoutes /></AuthProvider></MemoryRouter></QueryClientProvider>)
  return cache
}
async function ready() { return screen.findByLabelText('Mã lời mời') }
async function enterToken() {
  const input = await ready()
  await userEvent.setup().type(input, token)
  return input
}
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
  vi.spyOn(authApi, 'me').mockResolvedValue(user)
  vi.spyOn(authApi, 'login').mockResolvedValue(user)
  vi.spyOn(authApi, 'register').mockResolvedValue(user)
  vi.spyOn(authApi, 'logout').mockResolvedValue(undefined)
  vi.spyOn(notificationApi, 'unreadCount').mockResolvedValue(0)
  vi.spyOn(tenantApi, 'profiles').mockResolvedValue({ count: 0, next: null, previous: null, results: [] })
  vi.spyOn(membersApi, 'acceptInvitation').mockResolvedValue(accepted)
  vi.spyOn(membersApi, 'declineInvitation').mockResolvedValue({ status: 'DECLINED' })
})
afterEach(() => { apiClient.setForbiddenHandler(null) })

describe('recipient invitation routes and secret lifetime', () => {
  it('opens a discoverable protected response form without consuming a token on GET', async () => {
    setup('/profiles')
    await userEvent.setup().click(await screen.findByRole('link', { name: 'Tôi có mã lời mời' }))
    expect(await ready()).toHaveAttribute('type', 'password')
    expect(membersApi.acceptInvitation).not.toHaveBeenCalled()
    expect(membersApi.declineInvitation).not.toHaveBeenCalled()
  })

  it('ignores and removes URL token input without putting it in a form, request or cache', async () => {
    const cache = setup(`${path}?token=${token}#token=${token}`)
    expect(await ready()).toHaveValue('')
    await waitFor(() => expect(screen.getByTestId('invitation-location')).not.toHaveTextContent(token))
    expect(JSON.stringify(cache.getQueryCache().getAll().map((query) => query.queryKey))).not.toContain(token)
    expect(membersApi.acceptInvitation).not.toHaveBeenCalled()
    expect(membersApi.declineInvitation).not.toHaveBeenCalled()
  })

  it('rejects an empty token locally with linked accessible feedback', async () => {
    setup()
    await ready()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Chấp nhận lời mời' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Vui lòng kiểm tra mã lời mời.')
    expect(screen.getByLabelText('Mã lời mời')).toHaveAttribute('aria-invalid', 'true')
    await userEvent.setup().click(within(screen.getByRole('alert')).getByRole('button', { name: /Nhập nguyên mã/ }))
    expect(screen.getByLabelText('Mã lời mời')).toHaveFocus()
    expect(membersApi.acceptInvitation).not.toHaveBeenCalled()
  })

  it('keeps typed input and the same form during pending/successful same-user background verification', async () => {
    setup()
    const input = await enterToken(), identity = deferred<User>()
    vi.mocked(authApi.me).mockReturnValueOnce(identity.promise)
    await act(async () => { window.dispatchEvent(new Event('focus')) })
    expect(screen.getByLabelText('Mã lời mời')).toBe(input)
    expect(input).toHaveValue(token)
    await act(async () => { identity.resolve(user) })
    expect(screen.getByLabelText('Mã lời mời')).toBe(input)
    expect(input).toHaveValue(token)
    expect(membersApi.acceptInvitation).not.toHaveBeenCalled()
  })

  it('submits only on explicit confirmation, prevents duplicates and refreshes Profile discovery after server success', async () => {
    const cache = setup(), operation = deferred<typeof accepted>()
    vi.mocked(membersApi.acceptInvitation).mockReturnValueOnce(operation.promise)
    await enterToken()
    const invalidate = vi.spyOn(cache, 'invalidateQueries')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Chấp nhận lời mời' }))
    const form = screen.getByRole('form', { name: 'Phản hồi lời mời' })
    fireEvent.submit(form)
    expect(membersApi.acceptInvitation).toHaveBeenCalledExactlyOnceWith(token, expect.any(AbortSignal))
    expect(screen.getByLabelText('Mã lời mời')).toBeDisabled()
    expect(screen.queryByRole('heading', { name: 'Đã tham gia tổ chức' })).not.toBeInTheDocument()
    await act(async () => { operation.resolve(accepted) })
    expect(await screen.findByRole('heading', { name: 'Đã tham gia tổ chức' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Đến tổ chức' })).toHaveAttribute('href', `/profiles/${profileId}`)
    expect(screen.queryByLabelText('Mã lời mời')).not.toBeInTheDocument()
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['profiles'] })
    expect(user.email_verified).toBe(false)
    expect(JSON.stringify(cache.getQueryCache().getAll().map((query) => query.queryKey))).not.toContain(token)
  })

  it('uses one generic conflict message for expired, consumed, revoked or mismatched-recipient credentials', async () => {
    vi.mocked(membersApi.acceptInvitation).mockRejectedValueOnce(new ApiError(409, 'conflict', 'untrusted-specific-recipient-diagnostic'))
    setup()
    const input = await enterToken()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Chấp nhận lời mời' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể xử lý mã lời mời này.')
    expect(screen.getByRole('alert')).not.toHaveTextContent('untrusted-specific-recipient-diagnostic')
    expect(input).toHaveValue(token)
    expect(screen.queryByRole('link', { name: 'Đến tổ chức' })).not.toBeInTheDocument()
  })

  it('retains a recoverable CSRF/validation failure without claiming membership or echoing unexpected errors', async () => {
    vi.mocked(membersApi.acceptInvitation).mockRejectedValueOnce(new ApiError(403, 'csrf', 'Phiên làm việc đã thay đổi.')).mockRejectedValueOnce(new Error('private-token-diagnostic'))
    setup()
    const input = await enterToken(), interaction = userEvent.setup()
    await interaction.click(screen.getByRole('button', { name: 'Chấp nhận lời mời' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Phiên làm việc đã thay đổi.')
    expect(input).toHaveValue(token)
    await interaction.click(screen.getByRole('button', { name: 'Chấp nhận lời mời' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Chưa xác nhận được kết quả.')
    expect(screen.getByRole('alert')).not.toHaveTextContent('private-token-diagnostic')
  })

  it('requires a separate native confirmation before decline and creates no membership', async () => {
    setup()
    await enterToken()
    const interaction = userEvent.setup()
    await interaction.click(screen.getByRole('button', { name: 'Từ chối lời mời' }))
    const dialog = screen.getByRole('dialog', { name: 'Từ chối lời mời' })
    expect(membersApi.declineInvitation).not.toHaveBeenCalled()
    await interaction.click(within(dialog).getByRole('button', { name: 'Xác nhận từ chối' }))
    expect(await screen.findByRole('heading', { name: 'Đã từ chối lời mời' })).toBeVisible()
    expect(membersApi.declineInvitation).toHaveBeenCalledExactlyOnceWith(token, expect.any(AbortSignal))
    expect(membersApi.acceptInvitation).not.toHaveBeenCalled()
    expect(screen.queryByRole('link', { name: 'Đến tổ chức' })).not.toBeInTheDocument()
  })

  it('aborts on actual User change and does not display a late acceptance in the next identity', async () => {
    const operation = deferred<typeof accepted>()
    vi.mocked(membersApi.acceptInvitation).mockReturnValueOnce(operation.promise)
    setup()
    await enterToken()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Chấp nhận lời mời' }))
    const signal = vi.mocked(membersApi.acceptInvitation).mock.calls[0]?.[1]
    vi.mocked(authApi.me).mockResolvedValue(other)
    await act(async () => { window.dispatchEvent(new Event('focus')) })
    await waitFor(() => expect(screen.getByLabelText('Mã lời mời')).toHaveValue(''))
    expect(signal?.aborted).toBe(true)
    await act(async () => { operation.resolve(accepted) })
    expect(screen.queryByRole('heading', { name: 'Đã tham gia tổ chức' })).not.toBeInTheDocument()
    expect(screen.getByText(other.email, { exact: true })).toBeVisible()
  })

  it('removes secret input on real session expiry and returns to login without token-bearing redirect state', async () => {
    setup()
    const input = await enterToken()
    vi.mocked(authApi.me).mockRejectedValueOnce(new ApiError(403, 'forbidden', 'Vui lòng đăng nhập.'))
    await act(async () => { window.dispatchEvent(new Event('focus')) })
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible()
    expect(input.isConnected).toBe(false)
    expect(screen.getByTestId('invitation-location')).not.toHaveTextContent(token)
    expect(screen.getByTestId('invitation-location')).toHaveTextContent(path)
  })

  it('supports signup then login return using only the allowlisted response path, never a token', async () => {
    vi.mocked(authApi.me).mockRejectedValue(new ApiError(403, 'forbidden', 'Vui lòng đăng nhập.'))
    setup(`${path}?token=${token}`)
    const interaction = userEvent.setup()
    await interaction.click(await screen.findByRole('link', { name: 'Đăng ký tài khoản' }))
    expect(screen.getByTestId('invitation-location')).not.toHaveTextContent(token)
    await interaction.type(screen.getByLabelText('Email'), user.email)
    await interaction.type(screen.getByLabelText('Tên đăng nhập'), user.username)
    await interaction.type(screen.getByLabelText('Mật khẩu', { exact: true }), 'synthetic-password-for-tests-91')
    await interaction.type(screen.getByLabelText('Xác nhận mật khẩu'), 'synthetic-password-for-tests-91')
    await interaction.click(screen.getByRole('button', { name: 'Tạo tài khoản' }))
    expect(await screen.findByText(/Tài khoản đã được tạo/)).toBeVisible()
    expect(membersApi.acceptInvitation).not.toHaveBeenCalled()
    await interaction.click(screen.getByRole('link', { name: 'Về đăng nhập' }))
    await interaction.type(screen.getByLabelText('Email', { exact: true }), user.email)
    await interaction.type(screen.getByLabelText('Mật khẩu', { exact: true }), 'synthetic-password-for-tests-91')
    await interaction.click(screen.getByRole('button', { name: 'Đăng nhập' }))
    expect(await ready()).toHaveValue('')
    expect(screen.getByTestId('invitation-location')).toHaveTextContent(path)
    expect(screen.getByTestId('invitation-location')).not.toHaveTextContent(token)
    expect(membersApi.acceptInvitation).not.toHaveBeenCalled()
  })
})

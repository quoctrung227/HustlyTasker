/** Mock UI tests. Real isolated account/token delivery flows belong to e2e/. */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { accountSecurityApi } from '../services/api/account-security'
import { ApiError } from '../services/api/client'
import { authApi } from '../services/api/queries'
import type { User } from '../services/api/types'
import { AccountPage, ForgotPasswordPage, RegisterPage, ResetPasswordPage } from './account-security'

const user: User = { id: '00000000-0000-4000-8000-000000000001', email: 'member@example.test', username: 'member', first_name: '', last_name: '', email_verified: false, created_at: '2026-10-27T00:00:00Z' }
const auth = { status: 'anonymous', user: null as User | null, error: null, revalidate: vi.fn().mockResolvedValue(undefined) }
vi.mock('../features/auth/AuthProvider', () => ({ useAuth: () => auth }))
const credential = 'synthetic-manually-pasted-email-credential-only'

function show(element: React.ReactNode) { return render(<MemoryRouter>{element}</MemoryRouter>) }
beforeEach(() => {
  auth.status = 'anonymous'; auth.user = null; auth.error = null; auth.revalidate.mockReset().mockResolvedValue(undefined)
  vi.spyOn(authApi, 'register').mockResolvedValue(user)
  vi.spyOn(accountSecurityApi, 'requestReset').mockResolvedValue(undefined)
  vi.spyOn(accountSecurityApi, 'confirmReset').mockResolvedValue(undefined)
  vi.spyOn(accountSecurityApi, 'requestVerification').mockResolvedValue(undefined)
  vi.spyOn(accountSecurityApi, 'confirmVerification').mockResolvedValue(undefined)
})
async function fillRegistration() {
  fireEvent.change(screen.getByLabelText('Email', { exact: true }), { target: { value: 'new@example.test' } })
  fireEvent.change(screen.getByLabelText('Tên đăng nhập', { exact: true }), { target: { value: 'new-member' } })
  fireEvent.change(screen.getByLabelText('Mật khẩu', { exact: true }), { target: { value: 'Synthetic-password-only' } })
  fireEvent.change(screen.getByLabelText('Xác nhận mật khẩu', { exact: true }), { target: { value: 'Synthetic-password-only' } })
}
function fillReset() {
  fireEvent.change(screen.getByLabelText('Mã khôi phục', { exact: true }), { target: { value: credential } })
  fireEvent.change(screen.getByLabelText('Mật khẩu mới', { exact: true }), { target: { value: 'Synthetic-new-password' } })
  fireEvent.change(screen.getByLabelText('Xác nhận mật khẩu mới', { exact: true }), { target: { value: 'Synthetic-new-password' } })
}

describe('registration frontend', () => {
  it('validates accessible fields before requesting, with linked focused errors', async () => {
    show(<RegisterPage />)
    await userEvent.click(screen.getByRole('button', { name: 'Tạo tài khoản' }))
    expect(authApi.register).not.toHaveBeenCalled()
    const summary = screen.getByRole('alert')
    expect(summary.parentElement).toHaveFocus()
    await userEvent.click(within(summary).getByRole('link', { name: 'Vui lòng nhập địa chỉ email hợp lệ.' }))
    expect(screen.getByLabelText('Email', { exact: true })).toHaveFocus()
  })
  it('creates without auto-login or implied Profile membership, then clears password fields', async () => {
    show(<RegisterPage />); await fillRegistration()
    await userEvent.click(screen.getByRole('button', { name: 'Tạo tài khoản' }))
    expect(authApi.register).toHaveBeenCalledWith(expect.objectContaining({ email: 'new@example.test', username: 'new-member', password_confirm: 'Synthetic-password-only' }), expect.any(AbortSignal))
    expect(await screen.findByRole('status')).toHaveTextContent('Tài khoản đã được tạo')
    expect(screen.queryByLabelText('Mật khẩu', { exact: true })).not.toBeInTheDocument()
    expect(auth.revalidate).not.toHaveBeenCalled()
    expect(screen.getByRole('link', { name: 'Về đăng nhập' })).toHaveAttribute('href', '/login')
  })
  it('exposes password policy errors without rendering server-supplied values', async () => {
    vi.mocked(authApi.register).mockRejectedValue(new ApiError(400, 'validation', 'Kiểm tra lại.', { password: 'Vui lòng kiểm tra mật khẩu.' }))
    show(<RegisterPage />); await fillRegistration()
    await userEvent.click(screen.getByRole('button', { name: 'Tạo tài khoản' }))
    expect(screen.getByLabelText('Mật khẩu', { exact: true })).toHaveAttribute('aria-invalid', 'true')
    expect(authApi.register).toHaveBeenCalledTimes(1)
    expect(screen.queryByText('Tài khoản đã được tạo')).not.toBeInTheDocument()
  })
})

describe('password recovery frontend', () => {
  it('accepts the same neutral request success for every well-formed address', async () => {
    show(<ForgotPasswordPage />)
    fireEvent.change(screen.getByLabelText('Email', { exact: true }), { target: { value: 'unknown@example.test' } })
    await userEvent.click(screen.getByRole('button', { name: 'Yêu cầu mã khôi phục' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Nếu tài khoản đủ điều kiện tồn tại')
    expect(screen.getByRole('status')).toHaveTextContent('không xác nhận việc gửi email thành công')
    expect(screen.getByRole('link', { name: 'Tôi đã có mã khôi phục' })).toHaveAttribute('href', '/reset-password')
  })
  it('validates confirmation and masks the pasted credential without URL or storage use', async () => {
    const storage = vi.spyOn(Storage.prototype, 'setItem')
    show(<ResetPasswordPage />)
    const token = screen.getByLabelText('Mã khôi phục', { exact: true })
    expect(token).toHaveAttribute('type', 'password')
    expect(token).toHaveAttribute('autocomplete', 'off')
    await userEvent.click(screen.getByRole('button', { name: 'Lưu mật khẩu mới' }))
    expect(accountSecurityApi.confirmReset).not.toHaveBeenCalled()
    fillReset()
    await userEvent.click(screen.getByRole('button', { name: 'Lưu mật khẩu mới' }))
    expect(accountSecurityApi.confirmReset).toHaveBeenCalledWith({ token: credential, new_password: 'Synthetic-new-password', new_password_confirm: 'Synthetic-new-password' }, expect.any(AbortSignal))
    await waitFor(() => expect(auth.revalidate).toHaveBeenCalledTimes(1))
    expect(await screen.findByRole('status')).toHaveTextContent('không tự đăng nhập')
    expect(screen.queryByLabelText('Mã khôi phục', { exact: true })).not.toBeInTheDocument()
    expect(storage).not.toHaveBeenCalled()
    expect(window.location.href).not.toContain(credential)
  })
  it.each([400, 403, 404, 409, 429, 503])('retains a safe recoverable state and does not retry confirmation (%s)', async (status) => {
    vi.mocked(accountSecurityApi.confirmReset).mockRejectedValue(new ApiError(status, status === 403 ? 'csrf' : 'validation', 'Yêu cầu chưa hoàn tất.', { token: 'Kiểm tra mã mới nhất.' }))
    show(<ResetPasswordPage />); fillReset()
    await userEvent.click(screen.getByRole('button', { name: 'Lưu mật khẩu mới' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Yêu cầu chưa hoàn tất.')
    expect(screen.getByLabelText('Mã khôi phục', { exact: true })).toHaveAttribute('aria-invalid', 'true')
    expect(accountSecurityApi.confirmReset).toHaveBeenCalledTimes(1)
    expect(auth.revalidate).not.toHaveBeenCalled()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
  it('blocks duplicate requests and aborts on navigation/unmount', async () => {
    let resolve: () => void = () => {}
    vi.mocked(accountSecurityApi.confirmReset).mockReturnValue(new Promise<void>((done) => { resolve = done }))
    const view = show(<ResetPasswordPage />); fillReset()
    const form = screen.getByRole('form', { name: 'Đặt lại mật khẩu' })
    fireEvent.submit(form); fireEvent.submit(form)
    expect(accountSecurityApi.confirmReset).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Lưu mật khẩu mới' })).toBeDisabled()
    const signal = vi.mocked(accountSecurityApi.confirmReset).mock.calls[0]?.[1]
    view.unmount()
    expect(signal?.aborted).toBe(true)
    await act(async () => { resolve() })
    expect(auth.revalidate).not.toHaveBeenCalled()
  })
})

describe('current-user verification frontend', () => {
  beforeEach(() => { auth.status = 'authenticated'; auth.user = user })
  it('requests only the current session email and does not mark verified on send success', async () => {
    show(<AccountPage />)
    await userEvent.click(screen.getByRole('button', { name: 'Gửi mã xác minh' }))
    expect(accountSecurityApi.requestVerification).toHaveBeenCalledWith(expect.any(AbortSignal))
    expect(screen.getByText(/Email chưa được xác minh/)).toBeVisible()
    expect(auth.revalidate).not.toHaveBeenCalled()
    expect(screen.getByRole('status')).toHaveTextContent('Yêu cầu xác minh đã được tiếp nhận')
  })
  it('confirms the masked credential then refreshes the authenticated server identity', async () => {
    show(<AccountPage />)
    fireEvent.change(screen.getByLabelText('Mã xác minh', { exact: true }), { target: { value: credential } })
    await userEvent.click(screen.getByRole('button', { name: 'Xác nhận email' }))
    expect(accountSecurityApi.confirmVerification).toHaveBeenCalledWith(credential, expect.any(AbortSignal))
    expect(auth.revalidate).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(screen.getByLabelText('Mã xác minh', { exact: true })).toHaveValue(''))
  })
  it('hides verification mutations when the server already reports verified', () => {
    auth.user = { ...user, email_verified: true }
    show(<AccountPage />)
    expect(screen.getByText('Email đã được xác minh.', { exact: true })).toBeVisible()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
  it('does not expose a failed delivery as successful verification', async () => {
    vi.mocked(accountSecurityApi.requestVerification).mockRejectedValue(new ApiError(503, 'server', 'Không thể xử lý yêu cầu lúc này.'))
    show(<AccountPage />)
    await userEvent.click(screen.getByRole('button', { name: 'Gửi mã xác minh' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể xử lý')
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(auth.revalidate).not.toHaveBeenCalled()
  })
  it('discards a previous users credential input when identity changes', () => {
    const view = show(<AccountPage />)
    fireEvent.change(screen.getByLabelText('Mã xác minh', { exact: true }), { target: { value: credential } })
    auth.user = { ...user, id: '00000000-0000-4000-8000-000000000002', email: 'other@example.test' }
    view.rerender(<MemoryRouter><AccountPage /></MemoryRouter>)
    expect(screen.getByLabelText('Mã xác minh', { exact: true })).toHaveValue('')
    expect(screen.queryByText(user.email)).not.toBeInTheDocument()
  })
})

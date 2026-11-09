/** Mock service/component tests. Real UI-to-PostgreSQL acceptance is isolated E2E. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppRoutes } from '../app/App'
import { AuthProvider } from '../features/auth/AuthProvider'
import { ApiError, apiClient } from '../services/api/client'
import { notificationApi } from '../services/api/collaboration'
import { authApi, queryKeys, tenantApi } from '../services/api/queries'
import type { Page, Profile, User } from '../services/api/types'
import { workApi } from '../services/api/work-management'

const timestamp = '2026-11-02T00:00:00Z'
const profileId = '00000000-0000-4000-8000-000000000301'
const otherId = '00000000-0000-4000-8000-000000000302'
const profile: Profile = { id: profileId, name: 'Nhóm mới', status: 'ACTIVE', created_at: timestamp, updated_at: timestamp }
const user: User = { id: '00000000-0000-4000-8000-000000000303', username: 'new-member', email: 'new@example.test', first_name: '', last_name: '', created_at: timestamp, email_verified: false }
const page = <T,>(results: T[]): Page<T> => ({ results, count: results.length, next: null, previous: null })
const anonymous = () => new ApiError(403, 'forbidden', 'Vui lòng đăng nhập.')
function Position() { const location = useLocation(); return <output data-testid="location">{location.pathname}</output> }
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}
function renderRoute(path = '/profiles/new') {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0, gcTime: Infinity, refetchOnWindowFocus: false } } })
  const view = render(<QueryClientProvider client={cache}><MemoryRouter initialEntries={[path]}><Position /><AuthProvider><AppRoutes /></AuthProvider></MemoryRouter></QueryClientProvider>)
  return { cache, ...view }
}
async function openForm(path?: string) {
  const view = renderRoute(path)
  await screen.findByRole('heading', { name: 'Tạo tổ chức mới', level: 1 })
  return { ...view, input: screen.getByLabelText('Tên tổ chức *'), submit: screen.getByRole('button', { name: 'Tạo tổ chức' }), user: userEvent.setup() }
}
beforeEach(() => {
  vi.spyOn(authApi, 'me').mockResolvedValue(user)
  vi.spyOn(authApi, 'logout').mockResolvedValue(undefined)
  vi.spyOn(notificationApi, 'unreadCount').mockResolvedValue(0)
  vi.spyOn(tenantApi, 'profiles').mockResolvedValue(page([]))
  vi.spyOn(tenantApi, 'createProfile').mockResolvedValue(profile)
  vi.spyOn(tenantApi, 'profile').mockImplementation(async (id) => ({ ...profile, id }))
  vi.spyOn(tenantApi, 'workspaces').mockResolvedValue(page([]))
  vi.spyOn(workApi, 'capabilities').mockResolvedValue({ createWorkspace: true, manageWorkspace: true, manageTasks: true, manageLifecycle: true })
})

describe('first Profile onboarding', () => {
  it.each(['/profiles', '/dashboard'])('offers a working empty-state action from %s', async (path) => {
    renderRoute(path)
    expect(await screen.findByRole('heading', { name: 'Bạn chưa có tổ chức nào' })).toBeVisible()
    await userEvent.click(screen.getByRole('link', { name: 'Tạo tổ chức' }))
    expect(await screen.findByRole('heading', { name: 'Tạo tổ chức mới', level: 1 })).toBeVisible()
    expect(screen.getByTestId('location')).toHaveTextContent('/profiles/new')
  })

  it('allows existing users to create another Profile without hiding their cards', async () => {
    vi.mocked(tenantApi.profiles).mockResolvedValue(page([profile, { ...profile, id: otherId, name: 'Nhóm thứ hai' }]))
    renderRoute('/profiles')
    expect(await screen.findByRole('link', { name: /Nhóm thứ hai/ })).toBeVisible()
    expect(screen.getByRole('link', { name: /Nhóm mới/ })).toHaveAttribute('href', `/profiles/${profileId}`)
    await userEvent.click(screen.getByRole('link', { name: 'Tạo tổ chức' }))
    expect(await screen.findByLabelText('Tên tổ chức *')).toBeVisible()
  })

  it('does not mistake an empty paginated page for zero memberships', async () => {
    vi.mocked(tenantApi.profiles).mockResolvedValue({ ...page([]), count: 21 })
    renderRoute('/profiles')
    expect(await screen.findByRole('heading', { name: 'Trang này không có tổ chức' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Bạn chưa có tổ chức nào' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Về trang đầu' })).toHaveAttribute('href', '/profiles')
  })

  it('keeps Create Profile behind the existing session route guard', async () => {
    vi.mocked(authApi.me).mockRejectedValue(anonymous())
    renderRoute()
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible()
    expect(screen.queryByLabelText('Tên tổ chức *')).not.toBeInTheDocument()
    expect(tenantApi.createProfile).not.toHaveBeenCalled()
  })

  it.each(['', '   ', 'a'.repeat(256), 'Name\0invalid', 'Name\uD800invalid'])('validates invalid name locally without a request: %j', async (value) => {
    const { input, submit, user } = await openForm()
    fireEvent.change(input, { target: { value } })
    await user.click(submit)
    expect(tenantApi.createProfile).not.toHaveBeenCalled()
    expect(input).toHaveAttribute('aria-invalid', 'true')
    const alert = screen.getByRole('alert')
    expect(alert.parentElement).toHaveFocus()
    await user.click(within(alert).getByRole('link'))
    expect(input).toHaveFocus()
  })

  it('submits only a trimmed name and selects the Profile through the existing URL scope', async () => {
    const { input, submit, user, cache } = await openForm()
    cache.setQueryData(queryKeys.profiles(1), page([]))
    cache.setQueryData(queryKeys.profiles(2), page([]))
    cache.setQueryData(queryKeys.workspaces(otherId), page([]))
    await user.type(input, '  Nhóm mới  ')
    await user.click(submit)
    expect(tenantApi.createProfile).toHaveBeenCalledExactlyOnceWith({ name: 'Nhóm mới' }, expect.any(AbortSignal))
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(`/profiles/${profileId}/workspaces`))
    expect(await screen.findByRole('button', { name: 'Tạo không gian' })).toBeVisible()
    expect(screen.getByText('Tổ chức đã được tạo. Tạo không gian làm việc đầu tiên để bắt đầu.').closest('[role="status"]')).toBeVisible()
    expect(cache.getQueryData(queryKeys.profile(profileId))).toEqual(profile)
    expect(cache.getQueryState(queryKeys.profiles(1))?.isInvalidated).toBe(true)
    expect(cache.getQueryState(queryKeys.profiles(2))?.isInvalidated).toBe(true)
    expect(cache.getQueryState(queryKeys.workspaces(otherId))?.isInvalidated).toBe(false)
    expect(tenantApi.workspaces).toHaveBeenCalledWith(profileId, 1, expect.any(AbortSignal))
    expect(workApi.capabilities).toHaveBeenCalledWith(profileId, undefined, expect.any(AbortSignal))
  })

  it('counts Unicode code points consistently with the backend name limit', async () => {
    const { input, submit, user } = await openForm()
    const name = '😀'.repeat(255)
    fireEvent.change(input, { target: { value: name } })
    await user.click(submit)
    await waitFor(() => expect(tenantApi.createProfile).toHaveBeenCalledWith({ name }, expect.any(AbortSignal)))
  })

  it('prevents rapid duplicate submits and keeps the form busy until the server confirms', async () => {
    const pending = deferred<Profile>()
    vi.mocked(tenantApi.createProfile).mockReturnValue(pending.promise)
    const { input, submit, user } = await openForm()
    await user.type(input, 'Nhóm mới')
    await user.click(submit)
    fireEvent.submit(screen.getByRole('form', { name: 'Tạo tổ chức mới' }))
    expect(tenantApi.createProfile).toHaveBeenCalledOnce()
    expect(submit).toBeDisabled()
    expect(input).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Hủy' })).toBeDisabled()
    expect(screen.getByTestId('location')).toHaveTextContent('/profiles/new')
    await act(async () => pending.resolve(profile))
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(`/profiles/${profileId}/workspaces`))
  })

  it.each([
    new ApiError(400, 'validation', 'Kiểm tra thông tin.', { name: 'Tên không hợp lệ.' }),
    new ApiError(403, 'forbidden', 'Quyền đã thay đổi.'),
    new ApiError(409, 'conflict', 'Dữ liệu đã thay đổi.'),
    new ApiError(0, 'network', 'Không thể kết nối.'),
  ])('preserves the draft and displays safe failure without automatic retry: %j', async (error) => {
    vi.mocked(tenantApi.createProfile).mockRejectedValue(error)
    const { input, submit, user } = await openForm()
    await user.type(input, 'Tên chưa lưu')
    await user.click(submit)
    expect(await screen.findByRole('alert')).toHaveTextContent(error.message)
    expect(input).toHaveValue('Tên chưa lưu')
    expect(submit).toBeEnabled()
    expect(tenantApi.createProfile).toHaveBeenCalledOnce()
    expect(screen.getByTestId('location')).toHaveTextContent('/profiles/new')
    if (error.fieldErrors.name) expect(input).toHaveAccessibleDescription(expect.stringContaining(error.fieldErrors.name))
  })

  it('aborts an in-flight creation when logout removes the form, without repopulating private cache', async () => {
    const pending = deferred<Profile>()
    vi.mocked(tenantApi.createProfile).mockReturnValue(pending.promise)
    const { input, submit, user, cache } = await openForm()
    await user.type(input, 'Nhóm mới')
    await user.click(submit)
    const signal = vi.mocked(tenantApi.createProfile).mock.calls[0]?.[1]
    await user.click(screen.getByRole('button', { name: 'Đăng xuất' }))
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible()
    expect(signal?.aborted).toBe(true)
    await act(async () => pending.resolve(profile))
    expect(cache.getQueryData(queryKeys.profile(profileId))).toBeUndefined()
    expect(screen.queryByText(profile.name)).not.toBeInTheDocument()
  })

  it('discards the form and aborts the request when the session expires', async () => {
    const pending = deferred<Profile>()
    vi.mocked(tenantApi.createProfile).mockReturnValue(pending.promise)
    const { input, submit, user, cache } = await openForm()
    await user.type(input, 'Nhóm mới')
    await user.click(submit)
    const signal = vi.mocked(tenantApi.createProfile).mock.calls[0]?.[1]
    vi.mocked(authApi.me).mockRejectedValue(anonymous())
    fireEvent(window, new Event('focus'))
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible()
    expect(signal?.aborted).toBe(true)
    await act(async () => pending.resolve(profile))
    expect(cache.getQueryData(queryKeys.profile(profileId))).toBeUndefined()
  })

  it('binds the draft and request to the actor even when quiet revalidation changes identity in place', async () => {
    let forbidden: (() => void | Promise<void>) | null = null
    vi.spyOn(apiClient, 'setForbiddenHandler').mockImplementation((handler) => { forbidden = handler })
    const pending = deferred<Profile>()
    vi.mocked(tenantApi.createProfile).mockReturnValue(pending.promise)
    const { input, submit, user: actions, cache } = await openForm()
    await actions.type(input, 'Bản nháp của người trước')
    await actions.click(submit)
    const signal = vi.mocked(tenantApi.createProfile).mock.calls[0]?.[1]
    vi.mocked(authApi.me).mockResolvedValue({ ...user, id: otherId, username: 'another-user' })
    await act(async () => { await forbidden?.() })
    expect(signal?.aborted).toBe(true)
    expect(screen.getByLabelText('Tên tổ chức *')).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Tạo tổ chức' })).toBeEnabled()
    await act(async () => pending.resolve(profile))
    expect(cache.getQueryData(queryKeys.profile(profileId))).toBeUndefined()
    expect(screen.getByTestId('location')).toHaveTextContent('/profiles/new')
  })

  it('resolves the selected Profile from a refreshed deep URL without browser storage', async () => {
    renderRoute(`/profiles/${otherId}/workspaces`)
    expect(await screen.findByRole('button', { name: 'Tạo không gian' })).toBeVisible()
    expect(tenantApi.profile).toHaveBeenCalledWith(otherId, expect.any(AbortSignal))
    expect(tenantApi.workspaces).toHaveBeenCalledWith(otherId, 1, expect.any(AbortSignal))
    expect(tenantApi.createProfile).not.toHaveBeenCalled()
  })
})

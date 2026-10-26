/** Mock service/UI tests only. Real session+tenant proof is in e2e/real-api.spec.ts. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { ApiError, apiClient } from '../services/api/client'
import { authApi, tenantApi } from '../services/api/queries'
import type { Page, Profile, User, Workspace } from '../services/api/types'
import { AppErrorBoundary, AppRoutes } from './App'

const profileId = '00000000-0000-4000-8000-000000000101'
const workspaceId = '00000000-0000-4000-8000-000000000102'
const user: User = { id: '00000000-0000-4000-8000-000000000103', email: 'member@example.test', username: 'member', first_name: 'Bạn', last_name: '', created_at: '2026-10-26T00:00:00Z', email_verified: false }
const profile: Profile = { id: profileId, name: 'Nhóm được phép', status: 'ACTIVE', created_at: '2026-10-26T00:00:00Z', updated_at: '2026-10-26T00:00:00Z' }
const workspace: Workspace = { id: workspaceId, profile_id: profileId, name: 'Không gian được phép', description: 'Mô tả có quyền đọc', period: '2026-10-01', status: 'ARCHIVED', created_at: profile.created_at, updated_at: profile.updated_at }
const page = <T,>(results: T[], count = results.length): Page<T> => ({ count, results, next: null, previous: null })
const anonymous = () => new ApiError(403, 'forbidden', 'Vui lòng đăng nhập.')

function renderRoute(path: string, state?: unknown) {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0, gcTime: 0, refetchOnWindowFocus: false } } })
  render(<QueryClientProvider client={cache}><MemoryRouter initialEntries={[{ pathname: path, state }]}><AuthProvider><AppRoutes /></AuthProvider></MemoryRouter></QueryClientProvider>)
  return cache
}

function BrokenPage(): never { throw new Error('mock-private-render-failure') }

beforeEach(() => {
  vi.spyOn(authApi, 'me').mockResolvedValue(user)
  vi.spyOn(authApi, 'login').mockResolvedValue(user)
  vi.spyOn(authApi, 'logout').mockResolvedValue(undefined)
  vi.spyOn(tenantApi, 'profiles').mockResolvedValue(page([profile]))
  vi.spyOn(tenantApi, 'profile').mockResolvedValue(profile)
  vi.spyOn(tenantApi, 'workspaces').mockResolvedValue(page([workspace]))
  vi.spyOn(tenantApi, 'workspace').mockResolvedValue(workspace)
})

describe('routing and protected identity', () => {
  it('renders a safe fatal fallback outside router context and clears private tab text', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    document.title = 'Private workspace fixture'
    render(<AppErrorBoundary><BrokenPage /></AppErrorBoundary>)
    expect(screen.getByRole('heading', { name: 'Chưa thể hiển thị trang' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Tải lại trang' })).toHaveAttribute('href', '/dashboard')
    expect(document.title).not.toContain('Private workspace fixture')
  })
  it('does not fetch tenant data before auth initialization completes', async () => {
    let resolve: ((value: User) => void) | undefined
    vi.mocked(authApi.me).mockReturnValue(new Promise<User>((done) => { resolve = done }))
    renderRoute('/profiles')
    expect(screen.getByRole('status')).toHaveTextContent('Đang kiểm tra phiên')
    expect(tenantApi.profiles).not.toHaveBeenCalled()
    await act(async () => resolve?.(user))
    expect(await screen.findByText(profile.name)).toBeVisible()
  })

  it('redirects an anonymous protected route to login without a private fetch', async () => {
    vi.mocked(authApi.me).mockRejectedValue(anonymous())
    renderRoute('/profiles')
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible()
    expect(tenantApi.profiles).not.toHaveBeenCalled()
  })

  it.each(['/403', '/404', '/not-a-route'])('shows a safe status page at %s', async (path) => {
    renderRoute(path)
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(path === '/403' ? 'Bạn chưa có quyền truy cập' : 'Không tìm thấy trang')
    expect(tenantApi.profiles).not.toHaveBeenCalled()
  })

  it('keeps a tenant permission403 stable when /me confirms a valid session', async () => {
    let forbidden: (() => void | Promise<void>) | null = null
    vi.spyOn(apiClient, 'setForbiddenHandler').mockImplementation((handler) => { forbidden = handler })
    vi.mocked(tenantApi.profiles).mockImplementation(async () => {
      await forbidden?.()
      throw new ApiError(403, 'forbidden', 'Bạn không có quyền thực hiện thao tác này.')
    })
    renderRoute('/profiles')
    expect(await screen.findByRole('alert')).toHaveTextContent('Bạn không có quyền')
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 50)) })
    expect(authApi.me).toHaveBeenCalledTimes(2)
    expect(tenantApi.profiles).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Đăng xuất' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Đăng nhập' })).not.toBeInTheDocument()
  })
})

describe('Profile/Workspace states and navigation', () => {
  it('shows a useful empty Profile list with no pretend metrics or create controls', async () => {
    vi.mocked(tenantApi.profiles).mockResolvedValue(page([]))
    renderRoute('/profiles')
    expect(await screen.findByRole('heading', { name: 'Chưa có tổ chức nào' })).toBeVisible()
    expect(screen.queryByRole('button', { name: /tạo/i })).not.toBeInTheDocument()
  })

  it('shows loading while the tenant response is pending', async () => {
    vi.mocked(tenantApi.profiles).mockReturnValue(new Promise(() => {}))
    renderRoute('/profiles')
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Đang tải tổ chức'))
  })

  it('renders only scoped Profiles and uses bounded page numbers for pagination', async () => {
    vi.mocked(tenantApi.profiles).mockResolvedValue(page([profile], 21))
    renderRoute('/profiles')
    expect(await screen.findByText(profile.name)).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Trang sau' }))
    await waitFor(() => expect(tenantApi.profiles).toHaveBeenLastCalledWith(2, expect.any(AbortSignal)))
  })

  it('loads Profile detail before requesting its Workspace list', async () => {
    renderRoute(`/profiles/${profileId}`)
    expect(await screen.findByRole('heading', { name: profile.name })).toBeVisible()
    expect(await screen.findByText(workspace.name)).toBeVisible()
    expect(tenantApi.profile).toHaveBeenCalledWith(profileId, expect.any(AbortSignal))
    expect(tenantApi.workspaces).toHaveBeenCalledWith(profileId, 1, expect.any(AbortSignal))
  })

  it('renders Workspace detail with archived status and its authorized description', async () => {
    renderRoute(`/profiles/${profileId}/workspaces/${workspaceId}`)
    expect(await screen.findByRole('heading', { name: workspace.name })).toBeVisible()
    expect(screen.getByText(workspace.description || '')).toBeVisible()
    expect(screen.getAllByText('Đã lưu trữ')).toHaveLength(2)
    expect(tenantApi.workspace).toHaveBeenCalledWith(profileId, workspaceId, expect.any(AbortSignal))
  })

  it.each([new ApiError(404, 'not-found', 'Không tìm thấy nội dung hoặc bạn không có quyền truy cập.'), new ApiError(0, 'network', 'Không thể kết nối.')])('redacts inaccessible Workspace data on errors', async (error) => {
    vi.mocked(tenantApi.workspace).mockRejectedValue(error)
    renderRoute(`/profiles/${profileId}/workspaces/${workspaceId}`)
    expect(await screen.findByRole('alert')).toHaveTextContent(error.message)
    expect(screen.queryByText(workspace.name)).not.toBeInTheDocument()
    expect(document.title).not.toContain(workspace.name)
    expect(screen.queryByText(workspace.description || '')).not.toBeInTheDocument()
  })

  it('removes mounted private data and cache when the session expires on focus', async () => {
    const cache = renderRoute(`/profiles/${profileId}/workspaces/${workspaceId}`)
    expect(await screen.findByRole('heading', { name: workspace.name })).toBeVisible()
    vi.mocked(authApi.me).mockRejectedValue(anonymous())
    fireEvent(window, new Event('focus'))
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible()
    expect(screen.queryByText(workspace.name)).not.toBeInTheDocument()
    expect(cache.getQueryCache().getAll()).toHaveLength(0)
  })
})

describe('login form and identity transitions', () => {
  it('connects field errors to inputs and does not submit invalid values', async () => {
    vi.mocked(authApi.me).mockRejectedValue(anonymous())
    renderRoute('/login')
    await userEvent.click(await screen.findByRole('button', { name: 'Đăng nhập' }))
    expect(await screen.findByRole('alert')).toBeVisible()
    expect(screen.getByLabelText('Email', { exact: true })).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Mật khẩu', { exact: true })).toHaveAttribute('aria-describedby', 'password-error')
    expect(authApi.login).not.toHaveBeenCalled()
  })

  it('allows password managers/paste and never follows an external return destination', async () => {
    vi.mocked(authApi.me).mockRejectedValue(anonymous())
    renderRoute('/login', { from: '//example.test/private' })
    const email = await screen.findByLabelText('Email', { exact: true })
    const password = screen.getByLabelText('Mật khẩu', { exact: true })
    expect(email).toHaveAttribute('autocomplete', 'username')
    expect(password).toHaveAttribute('autocomplete', 'current-password')
    await userEvent.type(email, user.email)
    await userEvent.type(password, 'mock-only-input')
    await userEvent.click(screen.getByRole('button', { name: 'Đăng nhập' }))
    expect(await screen.findByRole('heading', { name: `Xin chào, ${user.first_name}.` })).toBeVisible()
  })

  it('logs out and clears private state after server-confirmed success', async () => {
    const cache = renderRoute('/profiles')
    expect(await screen.findByText(profile.name)).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Đăng xuất' }))
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible()
    expect(screen.queryByText(profile.name)).not.toBeInTheDocument()
    expect(document.title).toBe('Đăng nhập · HustlyTasker')
    expect(cache.getQueryCache().getAll()).toHaveLength(0)
  })
})

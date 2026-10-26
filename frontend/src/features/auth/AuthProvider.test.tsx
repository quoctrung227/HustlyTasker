/** Mocked service tests: live Django/PostgreSQL proof belongs to e2e/. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiClient } from '../../services/api/client'
import { authApi } from '../../services/api/queries'
import type { User } from '../../services/api/types'
import { AuthProvider, useAuth } from './AuthProvider'

const user: User = {
  id: '00000000-0000-4000-8000-000000000011',
  email: 'member@example.test', username: 'member', first_name: 'Thành viên',
  last_name: '', created_at: '2026-10-26T00:00:00Z', email_verified: false,
}
const otherUser: User = { ...user, id: '00000000-0000-4000-8000-000000000012', username: 'other' }
const anonymous = () => new ApiError(403, 'forbidden', 'Vui lòng đăng nhập.')
const network = () => new ApiError(0, 'network', 'Không thể kết nối.')

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}

function TestProviders(cache: QueryClient, { children }: { children: ReactNode }) {
  return <QueryClientProvider client={cache}><AuthProvider>{children}</AuthProvider></QueryClientProvider>
}

function setup() {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  const hook = renderHook(useAuth, { wrapper: TestProviders.bind(null, cache) })
  return { ...hook, cache }
}

beforeEach(() => {
  vi.spyOn(authApi, 'me').mockResolvedValue(user)
  vi.spyOn(authApi, 'login').mockResolvedValue(user)
  vi.spyOn(authApi, 'logout').mockResolvedValue(undefined)
})
afterEach(() => {
  apiClient.setForbiddenHandler(null)
  vi.unstubAllGlobals()
})

describe('auth initialization and fail-closed identity state', () => {
  it('keeps identity null until current-user verification has completed', async () => {
    const initial = deferred<User>()
    vi.mocked(authApi.me).mockReturnValue(initial.promise)
    const { result } = setup()
    expect(result.current.status).toBe('checking')
    expect(result.current.user).toBeNull()
    await act(async () => initial.resolve(user))
    expect(result.current.status).toBe('authenticated')
    expect(result.current.user?.id).toBe(user.id)
  })

  it('accepts DRF SessionAuthentication anonymous 403 rather than requiring 401', async () => {
    vi.mocked(authApi.me).mockRejectedValue(anonymous())
    const { result, cache } = setup()
    cache.setQueryData(['old-private-profile'], { name: 'Private cached fixture' })
    await waitFor(() => expect(result.current.status).toBe('anonymous'))
    expect(result.current.user).toBeNull()
    expect(cache.getQueryData(['old-private-profile'])).toBeUndefined()
  })

  it('uses unavailable state for network failure and removes private cache', async () => {
    vi.mocked(authApi.me).mockRejectedValue(network())
    const { result, cache } = setup()
    cache.setQueryData(['old-private-profile'], { name: 'Private cached fixture' })
    await waitFor(() => expect(result.current.status).toBe('unavailable'))
    expect(result.current.user).toBeNull()
    expect(cache.getQueryData(['old-private-profile'])).toBeUndefined()
  })

  it('does not let a late initial /me response replace a newer login identity', async () => {
    const initial = deferred<User>()
    vi.mocked(authApi.me).mockReturnValue(initial.promise)
    const { result } = setup()
    const initialSignal = vi.mocked(authApi.me).mock.calls[0]?.[0]
    await act(async () => result.current.signIn({ email: user.email, password: 'synthetic-input-only' }))
    expect(initialSignal?.aborted).toBe(true)
    await act(async () => initial.resolve(otherUser))
    expect(result.current.status).toBe('authenticated')
    expect(result.current.user?.id).toBe(user.id)
  })
})

describe('login and logout transitions', () => {
  it('clears prior identity-dependent cache before login and uses the returned user', async () => {
    vi.mocked(authApi.me).mockRejectedValue(anonymous())
    const { result, cache } = setup()
    await waitFor(() => expect(result.current.status).toBe('anonymous'))
    cache.setQueryData(['old-private-profile'], { name: 'Other identity data' })
    await act(async () => result.current.signIn({ email: user.email, password: 'synthetic-input-only' }))
    expect(cache.getQueryData(['old-private-profile'])).toBeUndefined()
    expect(result.current.user).toEqual(user)
    expect(result.current.status).toBe('authenticated')
  })

  it('does not authenticate after failed login', async () => {
    vi.mocked(authApi.me).mockRejectedValue(anonymous())
    vi.mocked(authApi.login).mockRejectedValue(new ApiError(400, 'validation', 'Thông tin chưa hợp lệ.'))
    const { result } = setup()
    await waitFor(() => expect(result.current.status).toBe('anonymous'))
    await act(async () => {
      await expect(result.current.signIn({ email: user.email, password: 'synthetic-input-only' }))
        .rejects.toMatchObject({ status: 400 })
    })
    expect(result.current.status).toBe('anonymous')
    expect(result.current.user).toBeNull()
  })

  it('hides private identity immediately during logout and clears cache on success', async () => {
    const logout = deferred<void>()
    vi.mocked(authApi.logout).mockReturnValue(logout.promise)
    const { result, cache } = setup()
    await waitFor(() => expect(result.current.status).toBe('authenticated'))
    cache.setQueryData(['private-workspace'], { name: 'Private fixture' })
    let pending!: Promise<void>
    await act(async () => { pending = result.current.signOut() })
    expect(result.current.status).toBe('checking')
    expect(result.current.user).toBeNull()
    expect(cache.getQueryData(['private-workspace'])).toBeUndefined()
    await act(async () => { logout.resolve(); await pending })
    expect(result.current.status).toBe('anonymous')
  })

  it.each([
    new ApiError(0, 'network', 'Kết nối thất bại.'),
    new ApiError(403, 'csrf', 'Phiên bảo mật đã thay đổi.'),
  ])('does not falsely claim server logout after transport or CSRF failure', async (error) => {
    vi.mocked(authApi.logout).mockRejectedValue(error)
    const { result, cache } = setup()
    await waitFor(() => expect(result.current.status).toBe('authenticated'))
    cache.setQueryData(['private-workspace'], { name: 'Private fixture' })
    await act(async () => result.current.signOut())
    expect(result.current.status).toBe('unavailable')
    expect(result.current.user).toBeNull()
    expect(cache.getQueryData(['private-workspace'])).toBeUndefined()
  })
})

describe('session expiry and authorization revalidation', () => {
  it('revalidates on focus and keeps private identity hidden while awaiting the result', async () => {
    const refreshed = deferred<User>()
    const { result } = setup()
    await waitFor(() => expect(result.current.status).toBe('authenticated'))
    vi.mocked(authApi.me).mockReturnValueOnce(refreshed.promise)
    await act(async () => { window.dispatchEvent(new Event('focus')) })
    expect(result.current.status).toBe('checking')
    expect(result.current.user).toBeNull()
    await act(async () => refreshed.resolve(user))
    expect(result.current.status).toBe('authenticated')
  })

  it('clears all private state when the focused session has expired', async () => {
    const { result, cache } = setup()
    await waitFor(() => expect(result.current.status).toBe('authenticated'))
    cache.setQueryData(['private-workspace'], { name: 'Private fixture' })
    vi.mocked(authApi.me).mockRejectedValueOnce(anonymous())
    await act(async () => { window.dispatchEvent(new Event('focus')) })
    await waitFor(() => expect(result.current.status).toBe('anonymous'))
    expect(result.current.user).toBeNull()
    expect(cache.getQueryData(['private-workspace'])).toBeUndefined()
  })

  it('does not turn a protected permission 403 into logout while /me still succeeds', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.status).toBe('authenticated'))
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', {
      status: 403, headers: { 'content-type': 'application/json' },
    })))
    await act(async () => {
      await expect(apiClient.request('v1/profiles/', { protected: true })).rejects.toMatchObject({ status: 403 })
    })
    expect(authApi.me).toHaveBeenCalledTimes(2)
    expect(result.current.status).toBe('authenticated')
    expect(result.current.user?.id).toBe(user.id)
  })

  it('clears identity when a protected 403 is followed by an anonymous /me response', async () => {
    const { result, cache } = setup()
    await waitFor(() => expect(result.current.status).toBe('authenticated'))
    cache.setQueryData(['private-workspace'], { name: 'Private fixture' })
    vi.mocked(authApi.me).mockRejectedValueOnce(anonymous())
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', {
      status: 403, headers: { 'content-type': 'application/json' },
    })))
    await act(async () => {
      await expect(apiClient.request('v1/profiles/', { protected: true })).rejects.toMatchObject({ status: 403 })
    })
    expect(result.current.status).toBe('anonymous')
    expect(cache.getQueryData(['private-workspace'])).toBeUndefined()
  })

  it('hides private state when revalidation is unavailable instead of retaining stale identity', async () => {
    const { result, cache } = setup()
    await waitFor(() => expect(result.current.status).toBe('authenticated'))
    cache.setQueryData(['private-workspace'], { name: 'Private fixture' })
    vi.mocked(authApi.me).mockRejectedValueOnce(network())
    await act(async () => { window.dispatchEvent(new Event('focus')) })
    expect(result.current.status).toBe('unavailable')
    expect(result.current.user).toBeNull()
    expect(cache.getQueryData(['private-workspace'])).toBeUndefined()
  })

  it('ignores an older revalidation response after a newer identity check succeeds', async () => {
    const older = deferred<User>()
    const { result } = setup()
    await waitFor(() => expect(result.current.status).toBe('authenticated'))
    vi.mocked(authApi.me).mockReturnValueOnce(older.promise).mockResolvedValueOnce(otherUser)
    let pending!: Promise<void>
    await act(async () => { pending = result.current.revalidate() })
    await act(async () => result.current.revalidate())
    await act(async () => { older.resolve(user); await pending })
    expect(result.current.user?.id).toBe(otherUser.id)
  })

  it('removes focus listeners and aborts pending checks when unmounted', async () => {
    const initial = deferred<User>()
    vi.mocked(authApi.me).mockReturnValue(initial.promise)
    const { unmount } = setup()
    const signal = vi.mocked(authApi.me).mock.calls[0]?.[0]
    unmount()
    expect(signal?.aborted).toBe(true)
    window.dispatchEvent(new Event('focus'))
    expect(authApi.me).toHaveBeenCalledTimes(1)
    initial.resolve(user)
  })
})

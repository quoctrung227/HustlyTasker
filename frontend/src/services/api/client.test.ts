/** Mocked-fetch unit tests. These are not evidence of live backend integration. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiClient, ApiError, apiClient } from './client'
import { authApi, queryKeys, tenantApi } from './queries'

const csrf = 'a'.repeat(64) // Synthetic test-only masked token, not a real secret.
const rotatedCsrf = 'b'.repeat(64)
const profileId = '00000000-0000-4000-8000-000000000101'
const workspaceId = '00000000-0000-4000-8000-000000000102'
const otherId = '00000000-0000-4000-8000-000000000103'
const timestamp = '2026-10-26T00:00:00Z'
const user = {
  id: otherId,
  email: 'reader@example.test',
  username: 'reader',
  first_name: '',
  last_name: '',
  created_at: timestamp,
  email_verified: false,
}
const profile = { id: profileId, name: 'Test team', status: 'ACTIVE', created_at: timestamp, updated_at: timestamp }
const workspace = {
  id: workspaceId, profile_id: profileId, name: 'Test month', description: null,
  period: '2026-10-01', status: 'ARCHIVED', created_at: timestamp, updated_at: timestamp,
}
const json = (value: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(value), { status, headers: { 'content-type': 'application/json', ...headers } })
const fetchMock = vi.fn<typeof fetch>()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  apiClient.clearCsrf()
  apiClient.setForbiddenHandler(null)
})
afterEach(() => vi.unstubAllGlobals())

describe('same-origin transport and CSRF', () => {
  it('sends GET requests with browser-managed cookies and no-store without CSRF', async () => {
    fetchMock.mockResolvedValue(json({ status: 'ok' }))
    await new ApiClient().request('health/')
    expect(fetchMock).toHaveBeenCalledWith('/api/health/', expect.objectContaining({
      method: 'GET', credentials: 'same-origin', cache: 'no-store', redirect: 'error',
      headers: { Accept: 'application/json' },
    }))
  })

  it('bootstraps CSRF and sends JSON with the current token for unsafe requests', async () => {
    fetchMock.mockResolvedValueOnce(json({ csrf_token: csrf })).mockResolvedValueOnce(new Response(null, { status: 204 }))
    await new ApiClient().request('auth/logout/', { method: 'POST' })
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/auth/csrf/', expect.objectContaining({ method: 'GET', credentials: 'same-origin' }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/auth/logout/', expect.objectContaining({
      method: 'POST', credentials: 'same-origin', headers: {
        Accept: 'application/json', 'X-CSRFToken': csrf, 'Content-Type': 'application/json',
      },
    }))
  })

  it('shares concurrent bootstrap and keeps the token only in memory', async () => {
    let complete: ((response: Response) => void) | undefined
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { complete = resolve }))
    const client = new ApiClient()
    const first = client.initializeCsrf()
    const second = client.initializeCsrf()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    complete?.(json({ csrf_token: csrf }))
    await expect(Promise.all([first, second])).resolves.toEqual([csrf, csrf])
    await expect(client.initializeCsrf()).resolves.toBe(csrf)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('rejects a bootstrap response started before a token generation changed', async () => {
    let complete: ((response: Response) => void) | undefined
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { complete = resolve }))
    const client = new ApiClient()
    const pending = client.initializeCsrf()
    client.clearCsrf()
    complete?.(json({ csrf_token: csrf }))
    await expect(pending).rejects.toMatchObject({ kind: 'invalid-response' })
    fetchMock.mockResolvedValueOnce(json({ csrf_token: rotatedCsrf }))
    await expect(client.initializeCsrf()).resolves.toBe(rotatedCsrf)
  })

  it('rotates the cached token after a successful Django login', async () => {
    fetchMock.mockResolvedValueOnce(json({ csrf_token: csrf }))
      .mockResolvedValueOnce(json({ user }))
      .mockResolvedValueOnce(json({ csrf_token: rotatedCsrf }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    await expect(authApi.login({ email: user.email, password: 'synthetic-input-only' })).resolves.toEqual(user)
    await authApi.logout()
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/auth/login/', expect.objectContaining({
      body: JSON.stringify({ email: user.email, password: 'synthetic-input-only' }),
      headers: expect.objectContaining({ 'X-CSRFToken': csrf }),
    }))
    expect(fetchMock).toHaveBeenNthCalledWith(4, '/api/auth/logout/', expect.objectContaining({
      headers: expect.objectContaining({ 'X-CSRFToken': rotatedCsrf }),
    }))
  })

  it('clears token after logout failure without replaying the request', async () => {
    fetchMock.mockResolvedValueOnce(json({ csrf_token: csrf })).mockResolvedValueOnce(json({ detail: 'denied' }, 403))
    await expect(authApi.logout()).rejects.toMatchObject({ status: 403 })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    fetchMock.mockResolvedValueOnce(json({ csrf_token: rotatedCsrf }))
    await expect(apiClient.initializeCsrf()).resolves.toBe(rotatedCsrf)
  })

  it.each([
    [new Response('<html>CSRF verification failed.</html>', { status: 403, headers: { 'content-type': 'text/html' } })],
    [json({ detail: 'CSRF Failed: CSRF token missing.' }, 403)],
  ])('recognizes CSRF rejection, clears token and never replays an unsafe request', async (response) => {
    fetchMock.mockResolvedValueOnce(json({ csrf_token: csrf })).mockResolvedValueOnce(response)
    const client = new ApiClient()
    await expect(client.request('auth/logout/', { method: 'POST' })).rejects.toMatchObject({ status: 403, kind: 'csrf' })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    fetchMock.mockResolvedValueOnce(json({ csrf_token: rotatedCsrf }))
    await expect(client.initializeCsrf()).resolves.toBe(rotatedCsrf)
  })

  it('fails safely when CSRF response does not match the actual backend contract', async () => {
    fetchMock.mockResolvedValue(json({ token: 'not-the-contract' }))
    await expect(new ApiClient().request('auth/login/', { method: 'POST', body: {} }))
      .rejects.toMatchObject({ kind: 'invalid-response' })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it.each(['https://outside.example.test/api/me/', '//outside.example.test/api/', '../outside/', '/admin/', 'auth/me/#secret', 'v1\\outside'])
    ('refuses a path outside same-origin /api/: %s', async (path) => {
      await expect(new ApiClient().request(path)).rejects.toBeInstanceOf(TypeError)
      expect(fetchMock).not.toHaveBeenCalled()
    })

  it('passes AbortSignal and does not convert cancellation to a network alert', async () => {
    const controller = new AbortController()
    const cancellation = new DOMException('Aborted', 'AbortError')
    fetchMock.mockRejectedValue(cancellation)
    await expect(new ApiClient().request('auth/me/', { signal: controller.signal })).rejects.toBe(cancellation)
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/me/', expect.objectContaining({ signal: controller.signal }))
  })

  it('avoids requests for an already cancelled operation', async () => {
    const controller = new AbortController()
    controller.abort()
    await expect(new ApiClient().request('auth/me/', { signal: controller.signal })).rejects.toMatchObject({ name: 'AbortError' })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('does not let a cancelled tenant response revalidate a newer session', async () => {
    const controller = new AbortController()
    const client = new ApiClient()
    const handler = vi.fn()
    client.setForbiddenHandler(handler)
    fetchMock.mockImplementationOnce(async () => {
      controller.abort()
      return json({}, 403)
    })
    await expect(client.request('v1/profiles/', { signal: controller.signal, protected: true }))
      .rejects.toMatchObject({ name: 'AbortError' })
    expect(handler).not.toHaveBeenCalled()
  })
})

describe('safe errors and permission boundaries', () => {
  it.each([
    [400, 'validation'], [401, 'authentication'], [403, 'forbidden'], [404, 'not-found'],
    [409, 'conflict'], [429, 'throttled'], [500, 'server'], [503, 'server'],
  ])('maps status %s without exposing backend detail', async (status, kind) => {
    fetchMock.mockResolvedValue(json({ detail: '<script>private server traceback</script>' }, Number(status)))
    let error: unknown
    try { await new ApiClient().request('v1/profiles/') } catch (caught) { error = caught }
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status, kind })
    expect((error as ApiError).message).not.toContain('private')
    expect(JSON.stringify(error)).not.toContain('traceback')
  })

  it('uses controlled field messages and omits unrecognized fields', async () => {
    fetchMock.mockResolvedValue(json({ email: ['private identity'], password: ['private input'], token: ['private token'] }, 400))
    await expect(new ApiClient().request('auth/me/')).rejects.toMatchObject({
      fieldErrors: { email: 'Vui lòng nhập địa chỉ email hợp lệ.', password: 'Vui lòng kiểm tra mật khẩu.' },
    })
  })

  it('retains safe numeric Retry-After metadata for throttling', async () => {
    fetchMock.mockResolvedValue(json({}, 429, { 'retry-after': '45' }))
    await expect(new ApiClient().request('health/')).rejects.toMatchObject({ retryAfterSeconds: 45 })
  })

  it('does not treat a tenant 403 as proof of session expiry', async () => {
    const handler = vi.fn()
    const client = new ApiClient()
    client.setForbiddenHandler(handler)
    fetchMock.mockResolvedValue(json({}, 403))
    await expect(client.request('v1/profiles/', { protected: true })).rejects.toMatchObject({ kind: 'forbidden' })
    expect(handler).toHaveBeenCalledTimes(1)
    await expect(client.request('auth/me/')).rejects.toMatchObject({ status: 403 })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('does not let a revalidation failure obscure the original permission error', async () => {
    const client = new ApiClient()
    client.setForbiddenHandler(() => Promise.reject(new Error('revalidation failed')))
    fetchMock.mockResolvedValue(json({}, 403))
    await expect(client.request('v1/profiles/', { protected: true })).rejects.toMatchObject({ status: 403, kind: 'forbidden' })
  })

  it('preserves tenant-safe 404 and avoids auth revalidation', async () => {
    const handler = vi.fn()
    apiClient.setForbiddenHandler(handler)
    fetchMock.mockResolvedValue(json({ detail: 'Not found.' }, 404))
    await expect(tenantApi.profile(profileId)).rejects.toMatchObject({ status: 404 })
    expect(handler).not.toHaveBeenCalled()
  })

  it('maps network errors without exposing connection diagnostics', async () => {
    fetchMock.mockRejectedValue(new TypeError('private host diagnostic'))
    await expect(new ApiClient().request('auth/me/')).rejects.toMatchObject({ status: 0, kind: 'network' })
  })

  it.each([
    [new Response('<h1>private traceback</h1>', { headers: { 'content-type': 'text/html' } })],
    [new Response('{invalid', { headers: { 'content-type': 'application/json' } })],
  ])('rejects non-JSON or malformed success responses', async (response) => {
    fetchMock.mockResolvedValue(response)
    await expect(new ApiClient().request('auth/me/')).rejects.toMatchObject({ kind: 'invalid-response' })
  })
})

describe('actual read-only DRF contract', () => {
  it('unwraps the current-user envelope', async () => {
    fetchMock.mockResolvedValue(json({ user }))
    await expect(authApi.me()).resolves.toEqual(user)
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/me/', expect.objectContaining({ method: 'GET' }))
  })

  it('requests pagination locally and never follows an absolute next link', async () => {
    fetchMock.mockResolvedValue(json({ count: 21, next: 'https://outside.example.test/steal', previous: null, results: [profile] }))
    const result = await tenantApi.profiles(2)
    expect(result.count).toBe(21)
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/profiles/?page=2', expect.objectContaining({ method: 'GET' }))
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('preserves profile detail fields and verifies expected identity', async () => {
    fetchMock.mockResolvedValueOnce(json(profile)).mockResolvedValueOnce(json({ ...profile, id: otherId }))
    await expect(tenantApi.profile(profileId)).resolves.toEqual(profile)
    await expect(tenantApi.profile(profileId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('supports archived Workspace metadata and nullable legacy period', async () => {
    const legacy = { ...workspace, period: null }
    fetchMock.mockResolvedValue(json({ count: 1, next: null, previous: null, results: [legacy] }))
    await expect(tenantApi.workspaces(profileId)).resolves.toMatchObject({ results: [legacy] })
    expect(fetchMock).toHaveBeenCalledWith(`/api/v1/profiles/${profileId}/workspaces/?page=1`, expect.anything())
  })

  it('rejects invalid or noncanonical Workspace periods before date rendering', async () => {
    fetchMock.mockResolvedValue(json({ ...workspace, period: '2026-13-01' }))
    await expect(tenantApi.workspace(profileId, workspaceId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('accepts uppercase UUID route spelling without relaxing identity matching', async () => {
    const letterId = 'abcdefab-abcd-4abc-8abc-abcdefabcdef'
    fetchMock.mockResolvedValue(json({ ...profile, id: letterId }))
    await expect(tenantApi.profile(letterId.toUpperCase())).resolves.toMatchObject({ id: letterId })
  })

  it('verifies both parent and Workspace identity for detail', async () => {
    fetchMock.mockResolvedValueOnce(json(workspace)).mockResolvedValueOnce(json({ ...workspace, profile_id: otherId }))
    await expect(tenantApi.workspace(profileId, workspaceId)).resolves.toEqual(workspace)
    await expect(tenantApi.workspace(profileId, workspaceId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('rejects cross-Profile rows even in a successful list response', async () => {
    fetchMock.mockResolvedValue(json({ count: 1, next: null, previous: null, results: [{ ...workspace, profile_id: otherId }] }))
    await expect(tenantApi.workspaces(profileId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it.each([
    { count: -1, next: null, previous: null, results: [] },
    { count: 1, next: null, previous: null, results: [{ ...profile, status: 'UNKNOWN' }] },
    { count: 0, results: [] },
  ])('rejects malformed list data', async (payload) => {
    fetchMock.mockResolvedValue(json(payload))
    await expect(tenantApi.profiles()).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('rejects invalid page numbers before sending a request', async () => {
    await expect(tenantApi.profiles(0)).rejects.toBeInstanceOf(TypeError)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('keeps Workspace cache keys separate across tenant scopes', () => {
    expect(queryKeys.workspaces(profileId)).not.toEqual(queryKeys.workspaces(otherId))
    expect(queryKeys.workspace(profileId, workspaceId)).not.toEqual(queryKeys.workspace(otherId, workspaceId))
    expect(queryKeys.profiles(1)).not.toEqual(queryKeys.profiles(2))
  })
})

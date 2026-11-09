/** Transport/DTO tests use synthetic mocked responses, not a live database. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { tenantApi } from './queries'

const timestamp = '2026-11-02T00:00:00Z'
const profile = { id: '00000000-0000-4000-8000-000000000301', name: 'Nhóm mới', status: 'ACTIVE', created_at: timestamp, updated_at: timestamp }
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'content-type': 'application/json' } })

beforeEach(() => { apiClient.clearCsrf(); apiClient.setForbiddenHandler(null) })
afterEach(() => { apiClient.clearCsrf(); apiClient.setForbiddenHandler(null); vi.unstubAllGlobals() })

describe('Profile creation contract', () => {
  it('sends only name through the existing protected API client', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(profile)
    const controller = new AbortController()
    const input = { name: profile.name, owner_id: 'not-sent', role: 'OWNER', status: 'ARCHIVED' }
    expect(await tenantApi.createProfile(input, controller.signal)).toEqual(profile)
    expect(request).toHaveBeenCalledExactlyOnceWith('v1/profiles/', {
      method: 'POST', body: { name: profile.name }, signal: controller.signal, protected: true,
    })
  })

  it.each([
    null,
    { ...profile, id: 'not-a-uuid' },
    { ...profile, status: 'ARCHIVED' },
    { ...profile, name: null },
    { ...profile, created_at: 'not-a-date' },
  ])('rejects a malformed creation response instead of selecting it: %j', async (payload) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(payload)
    await expect(tenantApi.createProfile({ name: profile.name })).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('uses same-origin cookies and CSRF bootstrap for the real client transport', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(json(profile, 201))
    vi.stubGlobal('fetch', fetchMock)
    await expect(tenantApi.createProfile({ name: profile.name })).resolves.toEqual(profile)
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/auth/csrf/', expect.objectContaining({ method: 'GET', credentials: 'same-origin' }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/v1/profiles/', expect.objectContaining({
      method: 'POST', credentials: 'same-origin', cache: 'no-store', body: JSON.stringify({ name: profile.name }),
      headers: expect.objectContaining({ 'X-CSRFToken': 'a'.repeat(64), 'Content-Type': 'application/json' }),
    }))
  })

  it('renders only safe localized name validation, without raw server text or automatic retry', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) }))
      .mockResolvedValueOnce(json({ name: ['private server diagnostics'], owner_id: ['hidden'] }, 400))
    vi.stubGlobal('fetch', fetchMock)
    const error = await tenantApi.createProfile({ name: profile.name }).catch((value: unknown) => value)
    expect(error).toMatchObject({ status: 400, fieldErrors: { name: 'Vui lòng nhập tên hợp lệ (tối đa 255 ký tự).' } })
    expect(JSON.stringify(error)).not.toContain('private server diagnostics')
    expect(JSON.stringify(error)).not.toContain('owner_id')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('revalidates an expired session through the existing forbidden handler', async () => {
    const forbidden = vi.fn().mockResolvedValue(undefined)
    apiClient.setForbiddenHandler(forbidden)
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) }))
      .mockResolvedValueOnce(json({ detail: 'Authentication credentials were not provided.' }, 403))
    vi.stubGlobal('fetch', fetchMock)
    await expect(tenantApi.createProfile({ name: profile.name })).rejects.toMatchObject({ status: 403, kind: 'forbidden' })
    expect(forbidden).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('does not retry CSRF failures or a request already aborted by navigation', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) }))
      .mockResolvedValueOnce(json({ detail: 'CSRF Failed: incorrect token.' }, 403))
    vi.stubGlobal('fetch', fetchMock)
    await expect(tenantApi.createProfile({ name: profile.name })).rejects.toMatchObject({ kind: 'csrf' })
    const controller = new AbortController()
    controller.abort()
    await expect(tenantApi.createProfile({ name: profile.name }, controller.signal)).rejects.toMatchObject({ name: 'AbortError' })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})

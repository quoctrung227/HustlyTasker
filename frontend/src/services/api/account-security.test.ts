/** Mocked transport contracts, not proof of live email delivery. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { accountSecurityApi } from './account-security'
import { apiClient, ApiError } from './client'
import { authApi } from './queries'

const csrf = 'c'.repeat(64) // Synthetic masked CSRF fixture only.
const credential = 'synthetic-email-credential-for-contract-test-only'
const user = { id: '00000000-0000-4000-8000-000000000001', email: 'new@example.test', username: 'new-member', first_name: '', last_name: '', email_verified: false, created_at: '2026-10-27T00:00:00Z' }
const registration = { email: user.email, username: user.username, password: 'Synthetic-password-only', password_confirm: 'Synthetic-password-only' }
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'content-type': 'application/json' } })
const fetchMock = vi.fn<typeof fetch>()
beforeEach(() => {
  fetchMock.mockReset(); vi.stubGlobal('fetch', fetchMock)
  apiClient.clearCsrf(); apiClient.setForbiddenHandler(null)
  fetchMock.mockResolvedValueOnce(json({ csrf_token: csrf }))
})
afterEach(() => { vi.unstubAllGlobals() })

describe('registration and account-security contracts', () => {
  it('registers exactly the supplied fields with CSRF, without creating a login request', async () => {
    fetchMock.mockResolvedValueOnce(json({ user }, 201))
    expect(await authApi.register(registration)).toEqual(user)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/auth/register/', expect.objectContaining({ method: 'POST', credentials: 'same-origin', body: JSON.stringify(registration), headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrf } }))
  })
  it('rejects a malformed registration identity instead of treating it as success', async () => {
    fetchMock.mockResolvedValueOnce(json({ user: { ...user, email_verified: undefined } }, 201))
    await expect(authApi.register(registration)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('requests verification only for the session owner with an empty body', async () => {
    fetchMock.mockResolvedValueOnce(json({ detail: 'Verification request accepted.' }, 202))
    await accountSecurityApi.requestVerification()
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/auth/email-verification/request/', expect.objectContaining({ method: 'POST', body: '{}' }))
  })
  it('sends verification credentials only in a protected CSRF POST body', async () => {
    fetchMock.mockResolvedValueOnce(json({ detail: 'Email verified.' }))
    await accountSecurityApi.confirmVerification(credential)
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/auth/email-verification/confirm/', expect.objectContaining({ body: JSON.stringify({ token: credential }), credentials: 'same-origin' }))
    expect(fetchMock.mock.calls.every(([url]) => !String(url).includes(credential))).toBe(true)
  })
  it('accepts the neutral reset request envelope without exposing account eligibility', async () => {
    fetchMock.mockResolvedValueOnce(json({ detail: 'If an eligible account exists, the request has been accepted.' }, 202))
    await expect(accountSecurityApi.requestReset('not-known@example.test')).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/auth/password-reset/request/', expect.objectContaining({ body: JSON.stringify({ email: 'not-known@example.test' }) }))
  })
  it('resets through the exact contract, clears stale CSRF and never calls login', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))
    const input = { token: credential, new_password: 'Synthetic-new-password', new_password_confirm: 'Synthetic-new-password' }
    await accountSecurityApi.confirmReset(input)
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/auth/password-reset/confirm/', expect.objectContaining({ method: 'POST', body: JSON.stringify(input) }))
    fetchMock.mockResolvedValueOnce(json({ csrf_token: 'd'.repeat(64) }))
    await apiClient.initializeCsrf()
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes('/login/'))).toHaveLength(0)
  })
  it('rejects an unexpected reset confirmation response body', async () => {
    fetchMock.mockResolvedValueOnce(json({ detail: 'Unexpected acknowledgement.' }))
    await expect(accountSecurityApi.confirmReset({ token: credential, new_password: 'Synthetic-new-password', new_password_confirm: 'Synthetic-new-password' })).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it.each([
    () => accountSecurityApi.requestVerification(),
    () => accountSecurityApi.confirmVerification(credential),
    () => accountSecurityApi.requestReset('member@example.test'),
  ])('does not accept a malformed success envelope (%#)', async (operation) => {
    fetchMock.mockResolvedValueOnce(json({ detail: 'Untrusted raw response' }, 202))
    await expect(operation()).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it.each([400, 403, 404, 409, 429, 503])('keeps failure safe and does not replay reset (%s)', async (status) => {
    fetchMock.mockResolvedValueOnce(json({ detail: credential, token: [credential], new_password: ['private-value'], new_password_confirm: ['private-value'] }, status))
    const error = await accountSecurityApi.confirmReset({ token: credential, new_password: 'Synthetic-new-password', new_password_confirm: 'Synthetic-new-password' }).catch((failure: unknown) => failure)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status })
    expect(String(error)).not.toContain(credential)
    expect(JSON.stringify((error as ApiError).fieldErrors)).not.toContain('private-value')
    expect(JSON.stringify((error as ApiError).fieldErrors)).not.toContain(credential)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
  it('aborts before sending any credentials when its component is gone', async () => {
    const controller = new AbortController(); controller.abort()
    await expect(accountSecurityApi.confirmVerification(credential, controller.signal)).rejects.toMatchObject({ name: 'AbortError' })
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

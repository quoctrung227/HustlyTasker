import { apiClient, invalidResponse } from './client'

function detail(payload: unknown, expected: string): void {
  if (payload === null || typeof payload !== 'object' || !('detail' in payload) || payload.detail !== expected) throw invalidResponse()
}

/** Credentials remain request bodies only; no query key, URL or stored token. */
export const accountSecurityApi = {
  async requestVerification(signal?: AbortSignal): Promise<void> {
    detail(await apiClient.request<unknown>('auth/email-verification/request/', { method: 'POST', body: {}, protected: true, signal }), 'Verification request accepted.')
  },
  async confirmVerification(token: string, signal?: AbortSignal): Promise<void> {
    detail(await apiClient.request<unknown>('auth/email-verification/confirm/', { method: 'POST', body: { token }, protected: true, signal }), 'Email verified.')
  },
  async requestReset(email: string, signal?: AbortSignal): Promise<void> {
    detail(await apiClient.request<unknown>('auth/password-reset/request/', { method: 'POST', body: { email }, signal }), 'If an eligible account exists, the request has been accepted.')
  },
  async confirmReset(input: { token: string; new_password: string; new_password_confirm: string }, signal?: AbortSignal): Promise<void> {
    const payload = await apiClient.request<unknown>('auth/password-reset/confirm/', { method: 'POST', body: input, signal })
    if (payload !== undefined) throw invalidResponse()
    apiClient.clearCsrf()
  },
}

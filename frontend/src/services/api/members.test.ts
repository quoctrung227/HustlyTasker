/** Mock transport/DTO contracts only; real membership transitions belong to isolated E2E. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiClient } from './client'
import { memberKeys, membersApi } from './members'
import type { InvitationCreateInput } from './members'

const userId = '00000000-0000-4000-8000-000000000901'
const profileId = '00000000-0000-4000-8000-000000000902'
const membershipId = '00000000-0000-4000-8000-000000000903'
const invitationId = '00000000-0000-4000-8000-000000000904'
const otherId = '00000000-0000-4000-8000-000000000905'
const replacementId = '00000000-0000-4000-8000-000000000906'
const timestamp = '2026-11-08T00:00:00Z'
const token = 'synthetic-opaque-invitation-code-only'
const base = `v1/profiles/${profileId}/`
const member = { id: membershipId, profile_id: profileId, display_label: 'Thành viên Kiểm thử', role: 'OWNER', is_active: true, joined_at: timestamp }
const capabilities = { can_invite: true, can_manage_invitations: true, allowed_invitation_roles: ['MEMBER', 'ADMIN'] }
const invitation = { id: invitationId, profile_id: profileId, recipient_email: 'recipient@example.test', requested_role: 'MEMBER', status: 'PENDING',
  delivery_status: 'SENT', expires_at: '2026-11-15T00:00:00Z', delivery_attempted_at: timestamp, delivered_at: timestamp,
  accepted_at: null, declined_at: null, revoked_at: null, expired_at: null, created_at: timestamp, updated_at: timestamp }
const accepted = { status: 'ACCEPTED', profile_id: profileId, membership_id: membershipId, role: 'MEMBER' }
const page = <T,>(results: T[]) => ({ count: results.length, results, next: null, previous: null })
const json = (payload: unknown, status = 200) => new Response(JSON.stringify(payload), { status, headers: { 'content-type': 'application/json' } })

beforeEach(() => { apiClient.clearCsrf(); apiClient.setForbiddenHandler(null) })
afterEach(() => { vi.restoreAllMocks(); apiClient.clearCsrf(); apiClient.setForbiddenHandler(null); vi.unstubAllGlobals() })

describe('scoped organization member directory', () => {
  it('uses the actual protected paginated Profile route with the caller signal', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([member]), capabilities })
    const signal = new AbortController().signal
    expect(await membersApi.members(profileId, 2, signal)).toEqual({ ...page([member]), capabilities })
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}members/?page=2`, { signal, protected: true })
  })

  it('keeps only permitted member metadata and server capability hints', async () => {
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([{ ...member, user_id: otherId, email: 'private@example.test', password: 'private-canary' }]),
      capabilities: { ...capabilities, user_id: otherId }, secret: 'private-canary' })
    const result = await membersApi.members(profileId)
    expect(result).toEqual({ ...page([member]), capabilities })
    expect(JSON.stringify(result)).not.toContain('private')
    expect(JSON.stringify(result)).not.toContain('user_id')
  })

  it('accepts an empty page and archived read-only capability envelope without inventing a role', async () => {
    const readonly = { can_invite: false, can_manage_invitations: false, allowed_invitation_roles: [] }
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([]), capabilities: readonly })
    expect(await membersApi.members(profileId)).toEqual({ ...page([]), capabilities: readonly })
  })

  it('keeps inactive membership history distinct from active membership', async () => {
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([{ ...member, role: 'MEMBER', is_active: false }]), capabilities })
    expect((await membersApi.members(profileId)).results[0]).toMatchObject({ role: 'MEMBER', is_active: false })
  })

  it.each([
    { ...member, id: 'not-an-id' }, { ...member, profile_id: otherId }, { ...member, role: 'SUPERUSER' },
    { ...member, is_active: 'true' }, { ...member, display_label: '' }, { ...member, joined_at: 'not-a-date' },
  ])('rejects malformed or cross-Profile roster rows', async (item) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([item]), capabilities })
    await expect(membersApi.members(profileId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it.each([
    null, {}, { ...capabilities, can_invite: 'true' }, { ...capabilities, can_manage_invitations: 1 },
    { ...capabilities, allowed_invitation_roles: ['OWNER'] }, { ...capabilities, allowed_invitation_roles: ['MEMBER', 'MEMBER'] },
    { ...capabilities, allowed_invitation_roles: [] }, { ...capabilities, can_manage_invitations: false },
  ])('fails closed for missing or contradictory invitation capabilities', async (value) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([member]), capabilities: value })
    await expect(membersApi.members(profileId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it.each([0, -1, 1.5, Number.NaN, Infinity])('rejects invalid page numbers before any HTTP request', async (value) => {
    const request = vi.spyOn(apiClient, 'request')
    await expect(membersApi.members(profileId, value)).rejects.toBeInstanceOf(TypeError)
    expect(request).not.toHaveBeenCalled()
  })

  it.each(['../other', 'https://untrusted.invalid', '', `${profileId}/invitations`])('rejects unsafe Profile identifiers before transport', async (value) => {
    const request = vi.spyOn(apiClient, 'request')
    await expect(membersApi.members(value)).rejects.toMatchObject({ status: 404 })
    expect(request).not.toHaveBeenCalled()
  })

  it.each([
    { count: -1, next: null, previous: null, results: [] }, { count: 0.5, next: null, previous: null, results: [] },
    { count: 1, next: false, previous: null, results: [member] }, { ...page(Array.from({ length: 101 }, () => member)) },
  ])('rejects malformed or oversized server pagination', async (value) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...value, capabilities })
    await expect(membersApi.members(profileId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
})

describe('actual invitation manager contracts', () => {
  it('reads sanitized Profile-scoped metadata without following arbitrary next URLs', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([invitation]), next: 'https://untrusted.invalid/next' })
    expect((await membersApi.invitations(profileId, 2)).results).toEqual([invitation])
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}invitations/?page=2`, { signal: undefined, protected: true })
  })

  it('projects credential canaries out of list and detail DTOs', async () => {
    const poisoned = { ...invitation, token: 'private-token-canary', token_digest: 'private-digest-canary', recipient_user_id: otherId }
    vi.spyOn(apiClient, 'request').mockResolvedValueOnce(page([poisoned])).mockResolvedValueOnce(poisoned)
    expect(await membersApi.invitations(profileId)).toEqual(page([invitation]))
    expect(await membersApi.invitation(profileId, invitationId)).toEqual(invitation)
  })

  it.each(['QUEUED', 'SENT', 'FAILED'])('represents delivery status %s separately from invitation acceptance', async (delivery) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(page([{ ...invitation, delivery_status: delivery }]))
    expect((await membersApi.invitations(profileId)).results[0]).toMatchObject({ status: 'PENDING', delivery_status: delivery })
  })

  it.each(['PENDING', 'ACCEPTED', 'DECLINED', 'REVOKED', 'EXPIRED'])('recognizes actual invitation status %s', async (value) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(page([{ ...invitation, status: value }]))
    expect((await membersApi.invitations(profileId)).results[0]?.status).toBe(value)
  })

  it.each([
    { ...invitation, profile_id: otherId }, { ...invitation, requested_role: 'OWNER' }, { ...invitation, status: 'ACTIVE' },
    { ...invitation, delivery_status: 'DELIVERED_TO_INBOX' }, { ...invitation, expires_at: null },
    { ...invitation, accepted_at: 'invalid' }, { ...invitation, recipient_email: '' },
  ])('rejects wrong-tenant or malformed invitation metadata', async (item) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(page([item]))
    await expect(membersApi.invitations(profileId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('creates only the two allowed input fields, never owner/user/membership flags', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(invitation)
    const signal = new AbortController().signal
    const input = { recipient_email: invitation.recipient_email, requested_role: 'MEMBER' as const, user_id: otherId, role: 'OWNER', is_active: true }
    expect(await membersApi.createInvitation(profileId, input, signal)).toEqual(invitation)
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}invitations/`, { method: 'POST',
      body: { recipient_email: invitation.recipient_email, requested_role: 'MEMBER' }, signal, protected: true })
  })

  it('cannot send an invented OWNER invitation role', async () => {
    const request = vi.spyOn(apiClient, 'request')
    await expect(membersApi.createInvitation(profileId, { recipient_email: 'recipient@example.test', requested_role: 'OWNER' } as unknown as InvitationCreateInput)).rejects.toMatchObject({ status: 400 })
    expect(request).not.toHaveBeenCalled()
  })

  it('revokes the exact invitation with an empty body', async () => {
    const value = { ...invitation, status: 'REVOKED', revoked_at: timestamp }
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(value)
    expect(await membersApi.revokeInvitation(profileId, invitationId)).toEqual(value)
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}invitations/${invitationId}/revoke/`, { method: 'POST', body: {}, signal: undefined, protected: true })
  })

  it('resend rotates to a replacement identity instead of reusing a consumed credential', async () => {
    const value = { ...invitation, id: replacementId }
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(value)
    expect(await membersApi.resendInvitation(profileId, invitationId)).toEqual(value)
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}invitations/${invitationId}/resend/`, { method: 'POST', body: {}, signal: undefined, protected: true })
  })

  it('rejects a resend response that does not contain a new pending identity', async () => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(invitation)
    await expect(membersApi.resendInvitation(profileId, invitationId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('rejects wrong-identity detail/revoke responses', async () => {
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...invitation, id: otherId, status: 'REVOKED' })
    await expect(membersApi.invitation(profileId, invitationId)).rejects.toMatchObject({ kind: 'invalid-response' })
    await expect(membersApi.revokeInvitation(profileId, invitationId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('does not retry or claim a delivery outcome when creation returns503', async () => {
    const failure = new ApiError(503, 'server', 'Không thể xử lý yêu cầu lúc này.')
    const request = vi.spyOn(apiClient, 'request').mockRejectedValue(failure)
    await expect(membersApi.createInvitation(profileId, { recipient_email: invitation.recipient_email, requested_role: 'MEMBER' })).rejects.toBe(failure)
    expect(request).toHaveBeenCalledOnce()
  })

  it('maps invitation field errors through static client messages instead of echoing email or role diagnostics', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) }))
      .mockResolvedValueOnce(json({ recipient_email: ['private-recipient-diagnostic'], requested_role: ['private-role-diagnostic'], user_id: ['private-identity-diagnostic'] }, 400))
    vi.stubGlobal('fetch', fetchMock)
    const error = await membersApi.createInvitation(profileId, { recipient_email: invitation.recipient_email, requested_role: 'MEMBER' }).catch((value: unknown) => value)
    expect(error).toMatchObject({ status: 400, kind: 'validation', fieldErrors: { recipient_email: expect.any(String), requested_role: expect.any(String) } })
    expect(JSON.stringify(error)).not.toContain('private-')
    expect(JSON.stringify(error)).not.toContain('user_id')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})

describe('recipient token actions and private cache boundaries', () => {
  it('accepts only through an explicit protected POST and projects safe membership metadata', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue({ ...accepted, token: 'private-token-canary', user_id: otherId })
    const signal = new AbortController().signal
    expect(await membersApi.acceptInvitation(token, signal)).toEqual(accepted)
    expect(request).toHaveBeenCalledExactlyOnceWith('v1/invitations/accept/', { method: 'POST', body: { token }, signal, protected: true })
  })

  it('declines without creating a client-side membership or performing an implicit GET', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue({ status: 'DECLINED', token: 'private-token-canary' })
    expect(await membersApi.declineInvitation(token)).toEqual({ status: 'DECLINED' })
    expect(request).toHaveBeenCalledExactlyOnceWith('v1/invitations/decline/', { method: 'POST', body: { token }, signal: undefined, protected: true })
  })

  it('preserves exact opaque token input rather than trimming or URL-encoding it', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(accepted)
    await membersApi.acceptInvitation(` ${token} `)
    expect(request).toHaveBeenCalledWith('v1/invitations/accept/', expect.objectContaining({ body: { token: ` ${token} ` } }))
  })

  it.each(['', 'x'.repeat(513), 'invalid\u0000code', '\uD800'])('rejects locally invalid token input without transport or secret error values', async (value) => {
    const request = vi.spyOn(apiClient, 'request')
    const error = await membersApi.acceptInvitation(value).catch((result: unknown) => result)
    expect(error).toMatchObject({ status: 400, kind: 'validation' })
    expect(JSON.stringify(error)).not.toContain(value || 'unused-private-canary')
    expect(request).not.toHaveBeenCalled()
  })

  it.each([
    { ...accepted, status: 'PENDING' }, { ...accepted, profile_id: 'not-an-id' },
    { ...accepted, membership_id: null }, { ...accepted, role: 'OWNER' },
  ])('rejects malformed acceptance or unsupported ownership escalation', async (value) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(value)
    await expect(membersApi.acceptInvitation(token)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it.each([403, 404, 409, 429])('retains sanitized server failure HTTP%s without automatic acceptance retry', async (code) => {
    const failure = new ApiError(code, code === 403 ? 'forbidden' : code === 404 ? 'not-found' : code === 429 ? 'throttled' : 'conflict', 'Không thể xử lý lời mời này.')
    const request = vi.spyOn(apiClient, 'request').mockRejectedValue(failure)
    await expect(membersApi.acceptInvitation(token)).rejects.toBe(failure)
    expect(request).toHaveBeenCalledOnce()
  })

  it('separates User/Profile/page keys and never puts recipient credentials in a key', () => {
    expect(memberKeys.members(userId, profileId, 1)).not.toEqual(memberKeys.members(otherId, profileId, 1))
    expect(memberKeys.invitations(userId, profileId, 1)).not.toEqual(memberKeys.invitations(userId, otherId, 1))
    expect(memberKeys.members(userId, profileId, 1)).not.toEqual(memberKeys.members(userId, profileId, 2))
    expect(memberKeys.profile(userId, profileId)).toEqual(['organization-members', userId, 'profiles', profileId])
    expect(JSON.stringify(memberKeys.invitations(userId, profileId))).not.toContain(token)
  })

  it('keeps invalid route identifiers opaque in cache keys without issuing or authorizing a request', () => {
    const request = vi.spyOn(apiClient, 'request')
    expect(memberKeys.members('Pending-Identity', 'Not-A-UUID')).toEqual(['organization-members', 'pending-identity', 'profiles', 'not-a-uuid', 'members', 1])
    expect(request).not.toHaveBeenCalled()
  })

  it('uses existing same-origin cookies and CSRF for the actual client request construction', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(json(accepted))
    vi.stubGlobal('fetch', fetchMock)
    await expect(membersApi.acceptInvitation(token)).resolves.toEqual(accepted)
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/auth/csrf/', expect.objectContaining({ method: 'GET', credentials: 'same-origin' }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/v1/invitations/accept/', expect.objectContaining({ method: 'POST', credentials: 'same-origin',
      body: JSON.stringify({ token }), headers: expect.objectContaining({ 'X-CSRFToken': 'a'.repeat(64) }) }))
  })

  it('does not reveal why a token was rejected or retain raw backend diagnostics', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) }))
      .mockResolvedValueOnce(json({ detail: 'private-recipient-identity-and-token-canary' }, 409))
    vi.stubGlobal('fetch', fetchMock)
    const error = await membersApi.acceptInvitation(token).catch((value: unknown) => value)
    expect(error).toMatchObject({ status: 409, kind: 'conflict' })
    expect(JSON.stringify(error)).not.toContain('private-recipient')
    expect(JSON.stringify(error)).not.toContain(token)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})

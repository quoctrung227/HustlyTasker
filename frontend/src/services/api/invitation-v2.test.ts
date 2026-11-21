import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiClient } from './client'
import { notificationApi, notificationTaskPath } from './collaboration'
import { memberKeys, membersApi, parseRecipientInvitation } from './members'
import type { InvitationCreateInput } from './members'

const userId = '00000000-0000-4000-8000-000000001001'
const profileId = '00000000-0000-4000-8000-000000001002'
const id = '00000000-0000-4000-8000-000000001003'
const otherId = '00000000-0000-4000-8000-000000001004'
const created = '2026-11-13T00:00:00Z'
const capabilities = { can_invite: true, can_manage_invitations: true, allowed_invitation_roles: ['MEMBER', 'ADMIN'] }
const candidate = { id: userId, display_label: 'Người nhận thử nghiệm', username: 'recipient', masked_email: null, relation: 'AVAILABLE', can_invite: true }
const recipient = { id, profile_id: profileId, profile_name: 'Tổ chức mời', inviter_display_label: 'Người quản lý', requested_role: 'MEMBER', status: 'PENDING',
  expires_at: '2026-11-20T00:00:00Z', can_accept: true, can_decline: true, can_open_profile: false }
const manager = { id, profile_id: profileId, recipient_email: null, acceptance_kind: 'ACCOUNT', recipient_display_label: candidate.display_label,
  recipient_username: candidate.username, recipient_masked_email: null, requested_role: 'MEMBER', status: 'PENDING', delivery_status: 'FAILED',
  created_at: created, updated_at: created, expires_at: recipient.expires_at, delivery_attempted_at: created, delivered_at: null,
  accepted_at: null, declined_at: null, revoked_at: null, expired_at: null }
const notification = { id: otherId, profile_id: profileId, target_type: 'PROFILE_INVITATION', event_type: 'PROFILE_INVITED', workspace_id: null, task_id: null,
  invitation_id: id, invitation: recipient, title: 'Lời mời tổ chức', message: 'Bạn có lời mời trên Web.', target_url: 'https://untrusted.example/ignored',
  is_read: false, created_at: created, updated_at: created }
const page = <T,>(results: T[], count = results.length) => ({ count, results, next: null, previous: null })
beforeEach(() => { vi.spyOn(apiClient, 'request') })
afterEach(() => { vi.restoreAllMocks(); apiClient.clearCsrf(); vi.unstubAllGlobals() })

describe('approved account directory contracts', () => {
  it('uses a protected server search/page URL with safe encoding and caller cancellation', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...page([candidate]), capabilities })
    const signal = new AbortController().signal
    expect(await membersApi.candidates(profileId, ' tên & tên ', 2, signal)).toEqual({ ...page([candidate]), capabilities })
    expect(apiClient.request).toHaveBeenCalledExactlyOnceWith(`v1/profiles/${profileId}/invitation-candidates/?search=${encodeURIComponent('tên & tên')}&page=2`, { signal, protected: true })
  })
  it('projects full email, phone, staff flags and other-organization data out of the directory', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...page([{ ...candidate, email: 'private@example.test', phone: 'private-phone', is_staff: true, profiles: ['private-profile'] }]), capabilities })
    expect((await membersApi.candidates(profileId)).results).toEqual([candidate])
  })
  it.each(['bad\0search', 'x'.repeat(101), '\uD800', 'bad\nsearch'])('rejects malformed search before transport', async (search) => {
    await expect(membersApi.candidates(profileId, search)).rejects.toMatchObject({ status: 400 })
    expect(apiClient.request).not.toHaveBeenCalled()
  })
  it.each([
    { ...candidate, id: 'bad' }, { ...candidate, can_invite: true, relation: 'ACTIVE_MEMBER' },
    { ...candidate, relation: 'FOREIGN_PROFILE_ADMIN' }, { ...candidate, username: 10 }, { ...candidate, display_label: '' },
  ])('fails closed for malformed candidate authority metadata', async (row) => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...page([row]), capabilities })
    await expect(membersApi.candidates(profileId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('enforces the approved twenty-account result boundary', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...page(Array.from({ length: 21 }, () => candidate)), capabilities })
    await expect(membersApi.candidates(profileId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('isolates search/page keys by account and organization', () => {
    const key = memberKeys.candidates(userId, profileId, 'name', 2)
    expect(key).not.toEqual(memberKeys.candidates(otherId, profileId, 'name', 2))
    expect(key).not.toEqual(memberKeys.candidates(userId, otherId, 'name', 2))
    expect(key).not.toEqual(memberKeys.candidates(userId, profileId, 'other', 2))
    expect(memberKeys.inbox(userId)).not.toEqual(memberKeys.inbox(otherId))
  })
})

describe('account invitation creation and personal decisions', () => {
  it('sends only account and approved role, and accepts durable Web success with FAILED email', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(manager)
    const input = { recipient_user_id: userId, requested_role: 'MEMBER' as const, owner: otherId, status: 'ACCEPTED', recipient_email: 'private@example.test' }
    expect(await membersApi.createInvitation(profileId, input)).toEqual(manager)
    expect(apiClient.request).toHaveBeenCalledExactlyOnceWith(`v1/profiles/${profileId}/invitations/`, {
      method: 'POST', body: { recipient_user_id: userId, requested_role: 'MEMBER' }, signal: undefined, protected: true,
    })
  })
  it('refuses the removed email-only create contract', async () => {
    await expect(membersApi.createInvitation(profileId, { recipient_email: 'legacy@example.test', requested_role: 'MEMBER' } as unknown as InvitationCreateInput)).rejects.toMatchObject({ status: 400 })
    expect(apiClient.request).not.toHaveBeenCalled()
  })
  it('retries ACCOUNT email on the same invitation identity', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(manager)
    expect(await membersApi.resendInvitation(profileId, id)).toEqual(manager)
    vi.mocked(apiClient.request).mockResolvedValue({ ...manager, id: otherId })
    await expect(membersApi.resendInvitation(profileId, id)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('loads the personal inbox without an existing Profile membership or a supplied tenant', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(page([recipient]))
    expect(await membersApi.recipientInvitations(2)).toEqual(page([recipient]))
    expect(apiClient.request).toHaveBeenCalledExactlyOnceWith('v1/invitations/?page=2', { signal: undefined, protected: true })
  })
  it('projects only permitted recipient metadata, excluding delivery details and identities', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...recipient, recipient_email: 'private@example.test', invited_by_user_id: userId, token_digest: 'private-digest', delivery_error: 'private-provider' })
    expect(await membersApi.recipientInvitation(id)).toEqual(recipient)
  })
  it.each(['accept', 'decline'] as const)('uses explicit ID-bound %s with empty body and Session/CSRF API handling', async (action) => {
    const status = action === 'accept' ? 'ACCEPTED' : 'DECLINED'
    const result = { ...recipient, status, can_accept: false, can_decline: false }
    vi.mocked(apiClient.request).mockResolvedValue(result)
    const signal = new AbortController().signal
    expect(await (action === 'accept' ? membersApi.acceptAccountInvitation(id, signal) : membersApi.declineAccountInvitation(id, signal))).toEqual(result)
    expect(apiClient.request).toHaveBeenCalledExactlyOnceWith(`v1/invitations/${id}/${action}/`, { method: 'POST', body: {}, signal, protected: true })
  })
  it.each([
    { ...recipient, id: otherId }, { ...recipient, can_accept: 'yes' }, { ...recipient, status: 'ACCEPTED' },
    { ...recipient, requested_role: 'OWNER' }, { ...recipient, can_open_profile: undefined },
  ])('rejects mismatched identity, invalid role or contradictory lifecycle capabilities', async (value) => {
    vi.mocked(apiClient.request).mockResolvedValue(value)
    await expect(membersApi.recipientInvitation(id)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('does not infer current access from historical ACCEPTED', () => {
    expect(parseRecipientInvitation({ ...recipient, status: 'ACCEPTED', can_accept: false, can_decline: false, can_open_profile: false }).can_open_profile).toBe(false)
  })
  it('preserves actual forbidden/conflict/throttled errors without retrying a decision', async () => {
    for (const status of [403, 404, 409, 429]) {
      const error = new ApiError(status, status === 429 ? 'throttled' : 'forbidden', 'Nội dung không khả dụng.')
      vi.mocked(apiClient.request).mockRejectedValueOnce(error)
      await expect(membersApi.acceptAccountInvitation(id)).rejects.toBe(error)
    }
    expect(apiClient.request).toHaveBeenCalledTimes(4)
  })
})

describe('typed invitation notification boundaries', () => {
  it('accepts a recipient-only context without a fake Task and strips unapproved metadata', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(page([{ ...notification, invitation: { ...recipient, email: 'private@example.test' }, private_canary: 'private' }]))
    expect(await notificationApi.feed()).toEqual(page([notification]))
    expect(() => notificationTaskPath({ profile_id: profileId, workspace_id: null, task_id: null })).toThrow()
  })
  it.each([
    { ...notification, workspace_id: profileId }, { ...notification, event_type: 'TASK_ASSIGNED' },
    { ...notification, invitation_id: otherId }, { ...notification, invitation: { ...recipient, profile_id: otherId } },
    { ...notification, target_type: 'UNKNOWN' },
  ])('rejects cross-context or mismatched invitation notification payloads', async (item) => {
    vi.mocked(apiClient.request).mockResolvedValue(page([item]))
    await expect(notificationApi.feed()).rejects.toMatchObject({ kind: 'invalid-response' })
  })
})

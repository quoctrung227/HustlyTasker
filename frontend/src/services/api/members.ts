/** Profile membership/invitation DTOs. Capability hints never authorize mutations. */
import { ApiError, apiClient, invalidResponse } from './client'
import type { Page } from './types'

export const invitationRoles = ['MEMBER', 'ADMIN'] as const
export type InvitationRole = typeof invitationRoles[number]
export type ProfileRole = 'OWNER' | 'ADMIN' | 'MEMBER'
export type InvitationStatus = 'PENDING' | 'ACCEPTED' | 'DECLINED' | 'REVOKED' | 'EXPIRED'
export type InvitationDeliveryStatus = 'QUEUED' | 'SENT' | 'FAILED'

export interface ProfileMember {
  id: string
  profile_id: string
  display_label: string
  role: ProfileRole
  is_active: boolean
  joined_at: string
}
export interface MemberCapabilities {
  can_invite: boolean
  can_manage_invitations: boolean
  allowed_invitation_roles: InvitationRole[]
}
export interface ProfileMembersPage extends Page<ProfileMember> {
  capabilities: MemberCapabilities
}
export interface ProfileInvitation {
  id: string
  profile_id: string
  recipient_email: string | null
  acceptance_kind?: 'EMAIL_TOKEN' | 'ACCOUNT'
  recipient_display_label?: string
  recipient_username?: string | null
  recipient_masked_email?: string | null
  requested_role: InvitationRole
  status: InvitationStatus
  delivery_status: InvitationDeliveryStatus
  expires_at: string
  delivery_attempted_at: string | null
  delivered_at: string | null
  accepted_at: string | null
  declined_at: string | null
  revoked_at: string | null
  expired_at: string | null
  created_at: string
  updated_at: string
}
export interface InvitationCreateInput {
  readonly recipient_user_id: string
  readonly requested_role: InvitationRole
}
export interface InvitationCandidate {
  id: string
  display_label: string
  username: string | null
  masked_email: string | null
  relation: 'AVAILABLE' | 'ACTIVE_MEMBER' | 'PENDING_INVITATION' | 'UNAVAILABLE'
  can_invite: boolean
}
export interface InvitationCandidatesPage extends Page<InvitationCandidate> { capabilities: MemberCapabilities }
export interface RecipientInvitation {
  id: string
  profile_id: string
  profile_name: string
  inviter_display_label: string
  requested_role: InvitationRole
  status: InvitationStatus
  expires_at: string
  can_accept: boolean
  can_decline: boolean
  can_open_profile: boolean
}
export interface AcceptedInvitation {
  status: 'ACCEPTED'
  profile_id: string
  membership_id: string
  role: InvitationRole
}
export interface DeclinedInvitation { status: 'DECLINED' }

const record = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown): value is string => typeof value === 'string'
const uuid = (value: unknown): value is string => text(value) && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
const dateTime = (value: unknown): value is string => text(value) && Number.isFinite(Date.parse(value))
const nullableDateTime = (value: unknown): value is string | null => value === null || dateTime(value)
const nullableText = (value: unknown): value is string | null => value === null || text(value)
const role = (value: unknown): value is InvitationRole => value === 'ADMIN' || value === 'MEMBER'
const profileRole = (value: unknown): value is ProfileRole => role(value) || value === 'OWNER'
const status = (value: unknown): value is InvitationStatus => value === 'PENDING' || value === 'ACCEPTED' || value === 'DECLINED' || value === 'REVOKED' || value === 'EXPIRED'
const deliveryStatus = (value: unknown): value is InvitationDeliveryStatus => value === 'QUEUED' || value === 'SENT' || value === 'FAILED'
const sameId = (left: string, right: string) => left.toLowerCase() === right.toLowerCase()

function entityId(value: string): string {
  if (!uuid(value)) throw new ApiError(404, 'not-found', 'Không tìm thấy nội dung hoặc bạn không có quyền truy cập.')
  return value.toLowerCase()
}
function pageNumber(value: number): number {
  if (!Number.isSafeInteger(value) || value < 1) throw new TypeError('Page must be a positive integer.')
  return value
}
function profilePath(profileId: string) { return `v1/profiles/${entityId(profileId)}/` }
function invitationPath(profileId: string, invitationId?: string) {
  return `${profilePath(profileId)}invitations/${invitationId === undefined ? '' : `${entityId(invitationId)}/`}`
}

function parsePage<T>(payload: unknown, parse: (item: unknown) => T): Page<T> {
  if (!record(payload) || typeof payload.count !== 'number' || !Number.isSafeInteger(payload.count) || payload.count < 0 ||
      !nullableText(payload.next) || !nullableText(payload.previous) || !Array.isArray(payload.results) || payload.results.length > 100 ||
      payload.results.length > payload.count) throw invalidResponse()
  // Never follow server pagination links: callers request our own scoped page URL.
  return { count: payload.count, next: payload.next, previous: payload.previous, results: payload.results.map(parse) }
}
function parseMember(payload: unknown, profileId: string): ProfileMember {
  if (!record(payload) || !uuid(payload.id) || !uuid(payload.profile_id) || !sameId(payload.profile_id, profileId) ||
      !text(payload.display_label) || !payload.display_label.trim() || !profileRole(payload.role) ||
      typeof payload.is_active !== 'boolean' || !dateTime(payload.joined_at)) throw invalidResponse()
  return { id: payload.id, profile_id: payload.profile_id, display_label: payload.display_label, role: payload.role,
    is_active: payload.is_active, joined_at: payload.joined_at }
}
function parseCapabilities(payload: unknown): MemberCapabilities {
  if (!record(payload) || typeof payload.can_invite !== 'boolean' || typeof payload.can_manage_invitations !== 'boolean' ||
      !Array.isArray(payload.allowed_invitation_roles) || !payload.allowed_invitation_roles.every(role) ||
      new Set(payload.allowed_invitation_roles).size !== payload.allowed_invitation_roles.length ||
      (payload.can_invite && (!payload.can_manage_invitations || !payload.allowed_invitation_roles.length))) throw invalidResponse()
  return { can_invite: payload.can_invite, can_manage_invitations: payload.can_manage_invitations,
    allowed_invitation_roles: [...payload.allowed_invitation_roles] }
}
function parseInvitation(payload: unknown, profileId: string, invitationId?: string): ProfileInvitation {
  if (!record(payload) || !uuid(payload.id) || !uuid(payload.profile_id) || !sameId(payload.profile_id, profileId) ||
      (invitationId !== undefined && !sameId(payload.id, invitationId)) || !nullableText(payload.recipient_email) ||
      (payload.recipient_email !== null && (!payload.recipient_email.trim() || payload.recipient_email.length > 254)) || !role(payload.requested_role) ||
      !status(payload.status) || !deliveryStatus(payload.delivery_status) || !dateTime(payload.expires_at) ||
      !dateTime(payload.created_at) || !dateTime(payload.updated_at) || !nullableDateTime(payload.delivery_attempted_at) ||
      !nullableDateTime(payload.delivered_at) || !nullableDateTime(payload.accepted_at) || !nullableDateTime(payload.declined_at) ||
      !nullableDateTime(payload.revoked_at) || !nullableDateTime(payload.expired_at)) throw invalidResponse()
  // Project the actual serializer fields; unexpected tokens/User fields never enter cache.
  const result: ProfileInvitation = { id: payload.id, profile_id: payload.profile_id, recipient_email: payload.recipient_email,
    requested_role: payload.requested_role, status: payload.status, delivery_status: payload.delivery_status,
    expires_at: payload.expires_at, delivery_attempted_at: payload.delivery_attempted_at, delivered_at: payload.delivered_at,
    accepted_at: payload.accepted_at, declined_at: payload.declined_at, revoked_at: payload.revoked_at,
    expired_at: payload.expired_at, created_at: payload.created_at, updated_at: payload.updated_at }
  if (payload.acceptance_kind !== undefined) {
    if (!['EMAIL_TOKEN', 'ACCOUNT'].includes(String(payload.acceptance_kind)) || !text(payload.recipient_display_label) ||
        !payload.recipient_display_label.trim() || !nullableText(payload.recipient_username) || !nullableText(payload.recipient_masked_email) ||
        (payload.acceptance_kind === 'ACCOUNT' && payload.recipient_email !== null)) throw invalidResponse()
    result.acceptance_kind = payload.acceptance_kind as 'EMAIL_TOKEN' | 'ACCOUNT'
    result.recipient_display_label = payload.recipient_display_label
    result.recipient_username = payload.recipient_username
    result.recipient_masked_email = payload.recipient_masked_email
  } else if (payload.recipient_email === null) throw invalidResponse()
  return result
}

/** The backend alone supplies recipient capabilities; IDs never grant access. */
export function parseRecipientInvitation(payload: unknown, expectedId?: string): RecipientInvitation {
  if (!record(payload) || !uuid(payload.id) || (expectedId !== undefined && !sameId(payload.id, expectedId)) || !uuid(payload.profile_id) ||
      !text(payload.profile_name) || !payload.profile_name.trim() || !text(payload.inviter_display_label) || !payload.inviter_display_label.trim() ||
      !role(payload.requested_role) || !status(payload.status) || !dateTime(payload.expires_at) ||
      typeof payload.can_accept !== 'boolean' || typeof payload.can_decline !== 'boolean' || typeof payload.can_open_profile !== 'boolean' ||
      (payload.status !== 'PENDING' && (payload.can_accept || payload.can_decline))) throw invalidResponse()
  return { id: payload.id, profile_id: payload.profile_id, profile_name: payload.profile_name, inviter_display_label: payload.inviter_display_label,
    requested_role: payload.requested_role, status: payload.status, expires_at: payload.expires_at,
    can_accept: payload.can_accept, can_decline: payload.can_decline, can_open_profile: payload.can_open_profile }
}
function searchText(value: string) {
  const characters = Array.from(value)
  const invalidCharacter = characters.some((character) => {
    const point = character.codePointAt(0) ?? 0
    return point < 32 || (point >= 127 && point <= 159) || (point >= 0xd800 && point <= 0xdfff)
  })
  if (!text(value) || characters.length > 100 || invalidCharacter) {
    throw new ApiError(400, 'validation', 'Nội dung tìm kiếm chưa hợp lệ. Dùng tối đa 100 ký tự.')
  }
  return value.trim()
}
function parseCandidate(payload: unknown): InvitationCandidate {
  if (!record(payload) || !uuid(payload.id) || !text(payload.display_label) || !payload.display_label.trim() ||
      !nullableText(payload.username) || !nullableText(payload.masked_email) ||
      !['AVAILABLE', 'ACTIVE_MEMBER', 'PENDING_INVITATION', 'UNAVAILABLE'].includes(String(payload.relation)) ||
      typeof payload.can_invite !== 'boolean' || (payload.can_invite && payload.relation !== 'AVAILABLE')) throw invalidResponse()
  return { id: payload.id, display_label: payload.display_label, username: payload.username, masked_email: payload.masked_email,
    relation: payload.relation as InvitationCandidate['relation'], can_invite: payload.can_invite }
}

/** Opaque credential stays transient: never a URL, query key, response or error value. */
function tokenBody(token: string) {
  if (!text(token) || !token || token.length > 512 || token.includes('\0') || /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(token)) {
    throw new ApiError(400, 'validation', 'Mã lời mời chưa hợp lệ. Vui lòng kiểm tra mã mới nhất.', { token: 'Nhập mã lời mời hợp lệ (tối đa 512 ký tự).' })
  }
  // DRF explicitly does not trim the token; do not alter credential identity.
  return { token }
}

// Keys are opaque cache scopes, not authorization or render-time URL validators.
// Invalid route IDs reach the HTTP helper's safe asynchronous404 path instead.
const userKey = (userId: string) => ['organization-members', userId.toLowerCase()] as const
const profileKey = (userId: string, profileId: string) => [...userKey(userId), 'profiles', profileId.toLowerCase()] as const
export const memberKeys = {
  user: userKey,
  profile: profileKey,
  members: (userId: string, profileId: string, page = 1) => [...profileKey(userId, profileId), 'members', pageNumber(page)] as const,
  invitations: (userId: string, profileId: string, page = 1) => [...profileKey(userId, profileId), 'invitations', pageNumber(page)] as const,
  candidates: (userId: string, profileId: string, search = '', page = 1) => [...profileKey(userId, profileId), 'invitation-candidates', search, pageNumber(page)] as const,
  recipientRoot: (userId: string) => [...userKey(userId), 'recipient-invitations'] as const,
  inbox: (userId: string, page = 1) => [...userKey(userId), 'recipient-invitations', 'inbox', pageNumber(page)] as const,
  recipient: (userId: string, invitationId: string) => [...userKey(userId), 'recipient-invitations', 'detail', invitationId.toLowerCase()] as const,
}

export const membersApi = {
  async candidates(profileId: string, search = '', page = 1, signal?: AbortSignal): Promise<InvitationCandidatesPage> {
    const payload = await apiClient.request<unknown>(`${profilePath(profileId)}invitation-candidates/?search=${encodeURIComponent(searchText(search))}&page=${pageNumber(page)}`, { signal, protected: true })
    const parsed = parsePage(payload, parseCandidate)
    if (!record(payload) || parsed.results.length > 20) throw invalidResponse()
    return { ...parsed, capabilities: parseCapabilities(payload.capabilities) }
  },
  async members(profileId: string, page = 1, signal?: AbortSignal): Promise<ProfileMembersPage> {
    const payload = await apiClient.request<unknown>(`${profilePath(profileId)}members/?page=${pageNumber(page)}`, { signal, protected: true })
    const parsed = parsePage(payload, (item) => parseMember(item, profileId))
    if (!record(payload)) throw invalidResponse()
    return { ...parsed, capabilities: parseCapabilities(payload.capabilities) }
  },
  async invitations(profileId: string, page = 1, signal?: AbortSignal): Promise<Page<ProfileInvitation>> {
    return parsePage(await apiClient.request<unknown>(`${invitationPath(profileId)}?page=${pageNumber(page)}`, { signal, protected: true }),
      (item) => parseInvitation(item, profileId))
  },
  async invitation(profileId: string, invitationId: string, signal?: AbortSignal): Promise<ProfileInvitation> {
    return parseInvitation(await apiClient.request<unknown>(invitationPath(profileId, invitationId), { signal, protected: true }), profileId, invitationId)
  },
  async createInvitation(profileId: string, input: InvitationCreateInput, signal?: AbortSignal): Promise<ProfileInvitation> {
    if (!record(input) || !uuid(input.recipient_user_id) || !role(input.requested_role)) {
      throw new ApiError(400, 'validation', 'Thông tin lời mời chưa hợp lệ. Vui lòng kiểm tra lại.')
    }
    return parseInvitation(await apiClient.request<unknown>(invitationPath(profileId), {
      method: 'POST', body: { recipient_user_id: entityId(input.recipient_user_id), requested_role: input.requested_role }, signal, protected: true,
    }), profileId)
  },
  async revokeInvitation(profileId: string, invitationId: string, signal?: AbortSignal): Promise<ProfileInvitation> {
    const result = parseInvitation(await apiClient.request<unknown>(`${invitationPath(profileId, invitationId)}revoke/`, {
      method: 'POST', body: {}, signal, protected: true,
    }), profileId, invitationId)
    if (result.status !== 'REVOKED') throw invalidResponse()
    return result
  },
  async resendInvitation(profileId: string, invitationId: string, signal?: AbortSignal): Promise<ProfileInvitation> {
    const result = parseInvitation(await apiClient.request<unknown>(`${invitationPath(profileId, invitationId)}resend/`, {
      method: 'POST', body: {}, signal, protected: true,
    }), profileId)
    if (result.acceptance_kind !== 'ACCOUNT' || !sameId(result.id, invitationId) || result.status !== 'PENDING') throw invalidResponse()
    return result
  },
  async recipientInvitations(page = 1, signal?: AbortSignal): Promise<Page<RecipientInvitation>> {
    return parsePage(await apiClient.request<unknown>(`v1/invitations/?page=${pageNumber(page)}`, { signal, protected: true }), (item) => parseRecipientInvitation(item))
  },
  async recipientInvitation(invitationId: string, signal?: AbortSignal): Promise<RecipientInvitation> {
    return parseRecipientInvitation(await apiClient.request<unknown>(`v1/invitations/${entityId(invitationId)}/`, { signal, protected: true }), invitationId)
  },
  async acceptAccountInvitation(invitationId: string, signal?: AbortSignal): Promise<RecipientInvitation> {
    const result = parseRecipientInvitation(await apiClient.request<unknown>(`v1/invitations/${entityId(invitationId)}/accept/`, { method: 'POST', body: {}, signal, protected: true }), invitationId)
    if (result.status !== 'ACCEPTED') throw invalidResponse()
    return result
  },
  async declineAccountInvitation(invitationId: string, signal?: AbortSignal): Promise<RecipientInvitation> {
    const result = parseRecipientInvitation(await apiClient.request<unknown>(`v1/invitations/${entityId(invitationId)}/decline/`, { method: 'POST', body: {}, signal, protected: true }), invitationId)
    if (result.status !== 'DECLINED') throw invalidResponse()
    return result
  },
  async acceptInvitation(token: string, signal?: AbortSignal): Promise<AcceptedInvitation> {
    const payload = await apiClient.request<unknown>('v1/invitations/accept/', { method: 'POST', body: tokenBody(token), signal, protected: true })
    if (!record(payload) || payload.status !== 'ACCEPTED' || !uuid(payload.profile_id) || !uuid(payload.membership_id) || !role(payload.role)) throw invalidResponse()
    return { status: 'ACCEPTED', profile_id: payload.profile_id, membership_id: payload.membership_id, role: payload.role }
  },
  async declineInvitation(token: string, signal?: AbortSignal): Promise<DeclinedInvitation> {
    const payload = await apiClient.request<unknown>('v1/invitations/decline/', { method: 'POST', body: tokenBody(token), signal, protected: true })
    if (!record(payload) || payload.status !== 'DECLINED') throw invalidResponse()
    return { status: 'DECLINED' }
  },
}

/** Workspace access DTOs; read-only capability hints never authorize a write. */
import { ApiError, apiClient, invalidResponse } from './client'
import type { Page } from './types'

export const workspaceAccessRoles = ['ADMIN', 'MEMBER', 'VIEWER'] as const
export type WorkspaceAccessRole = typeof workspaceAccessRoles[number]
export type WorkspaceAccessProfileRole = 'OWNER' | 'ADMIN' | 'MEMBER'

export interface WorkspaceAccessCapabilities {
  can_add: boolean
  allowed_roles: WorkspaceAccessRole[]
  profile_role: WorkspaceAccessProfileRole
  workspace_role: WorkspaceAccessRole | null
  has_inherited_access: boolean
}
export interface WorkspaceAccessMemberCapabilities {
  can_update: boolean
  can_revoke: boolean
  allowed_roles: WorkspaceAccessRole[]
  has_inherited_access: boolean
}
export interface WorkspaceAccessMember {
  id: string
  profile_membership_id: string
  display_label: string
  is_assignable: boolean
  role: WorkspaceAccessRole
  is_active: boolean
  joined_at: string
  updated_at: string
  capabilities: WorkspaceAccessMemberCapabilities
}
export interface WorkspaceAccessMembersPage extends Page<WorkspaceAccessMember> {
  capabilities: WorkspaceAccessCapabilities
}
export type WorkspaceAccessPage = WorkspaceAccessMembersPage
export interface WorkspaceAccessCandidate {
  profile_membership_id: string
  display_label: string
  profile_role: WorkspaceAccessProfileRole
  has_inherited_access: boolean
}
export type WorkspaceAccessCandidatesPage = Page<WorkspaceAccessCandidate>
export interface WorkspaceAccessAddInput {
  readonly target_profile_membership_id: string
  readonly role: WorkspaceAccessRole
}
export interface WorkspaceAccessUpdateInput {
  readonly role: WorkspaceAccessRole
}

const record = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown): value is string => typeof value === 'string'
const uuid = (value: unknown): value is string => text(value) && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
const dateTime = (value: unknown): value is string => text(value) && Number.isFinite(Date.parse(value))
const nullableText = (value: unknown): value is string | null => value === null || text(value)
const role = (value: unknown): value is WorkspaceAccessRole => value === 'ADMIN' || value === 'MEMBER' || value === 'VIEWER'
const profileRole = (value: unknown): value is WorkspaceAccessProfileRole => value === 'OWNER' || value === 'ADMIN' || value === 'MEMBER'
const roles = (value: unknown): value is WorkspaceAccessRole[] => Array.isArray(value) && value.every(role) && new Set(value).size === value.length
const sameId = (left: string, right: string) => left.toLowerCase() === right.toLowerCase()

function entityId(value: string): string {
  if (!uuid(value)) throw new ApiError(404, 'not-found', 'Không tìm thấy nội dung hoặc bạn không có quyền truy cập.')
  return value.toLowerCase()
}
function pageNumber(value: number): number {
  if (!Number.isSafeInteger(value) || value < 1) throw new TypeError('Page must be a positive integer.')
  return value
}
function workspacePath(profileId: string, workspaceId: string) {
  return `v1/profiles/${entityId(profileId)}/workspaces/${entityId(workspaceId)}/`
}
function memberPath(profileId: string, workspaceId: string, membershipId?: string) {
  return `${workspacePath(profileId, workspaceId)}members/${membershipId === undefined ? '' : `${entityId(membershipId)}/`}`
}
function parsePage<T>(payload: unknown, parse: (value: unknown) => T): Page<T> {
  if (!record(payload) || typeof payload.count !== 'number' || !Number.isSafeInteger(payload.count) || payload.count < 0 ||
      !nullableText(payload.next) || !nullableText(payload.previous) || !Array.isArray(payload.results) ||
      payload.results.length > 100 || payload.results.length > payload.count) throw invalidResponse()
  // Pagination links are metadata only; requests always reconstruct this tenant scope.
  return { count: payload.count, next: payload.next, previous: payload.previous, results: payload.results.map(parse) }
}
function parseCapabilities(payload: unknown): WorkspaceAccessCapabilities {
  if (!record(payload) || typeof payload.can_add !== 'boolean' || !roles(payload.allowed_roles) ||
      !profileRole(payload.profile_role) || (payload.workspace_role !== null && !role(payload.workspace_role)) ||
      typeof payload.has_inherited_access !== 'boolean' || (payload.can_add && !payload.allowed_roles.length)) throw invalidResponse()
  return { can_add: payload.can_add, allowed_roles: [...payload.allowed_roles], profile_role: payload.profile_role,
    workspace_role: payload.workspace_role, has_inherited_access: payload.has_inherited_access }
}
function parseMemberCapabilities(payload: unknown): WorkspaceAccessMemberCapabilities {
  if (!record(payload) || typeof payload.can_update !== 'boolean' || typeof payload.can_revoke !== 'boolean' ||
      !roles(payload.allowed_roles) || typeof payload.has_inherited_access !== 'boolean' ||
      (payload.can_update && !payload.allowed_roles.length)) throw invalidResponse()
  return { can_update: payload.can_update, can_revoke: payload.can_revoke,
    allowed_roles: [...payload.allowed_roles], has_inherited_access: payload.has_inherited_access }
}
function parseMember(payload: unknown, membershipId?: string): WorkspaceAccessMember {
  if (!record(payload) || !uuid(payload.id) || (membershipId !== undefined && !sameId(payload.id, membershipId)) ||
      !uuid(payload.profile_membership_id) || !text(payload.display_label) || !payload.display_label.trim() ||
      typeof payload.is_assignable !== 'boolean' || !role(payload.role) || typeof payload.is_active !== 'boolean' ||
      !dateTime(payload.joined_at) || !dateTime(payload.updated_at)) throw invalidResponse()
  return { id: payload.id, profile_membership_id: payload.profile_membership_id, display_label: payload.display_label,
    is_assignable: payload.is_assignable, role: payload.role, is_active: payload.is_active,
    joined_at: payload.joined_at, updated_at: payload.updated_at, capabilities: parseMemberCapabilities(payload.capabilities) }
}
function parseCandidate(payload: unknown): WorkspaceAccessCandidate {
  if (!record(payload) || !uuid(payload.profile_membership_id) || !text(payload.display_label) ||
      !payload.display_label.trim() || !profileRole(payload.profile_role) || typeof payload.has_inherited_access !== 'boolean') throw invalidResponse()
  return { profile_membership_id: payload.profile_membership_id, display_label: payload.display_label,
    profile_role: payload.profile_role, has_inherited_access: payload.has_inherited_access }
}
function validatedRole(input: WorkspaceAccessUpdateInput): WorkspaceAccessRole {
  if (!record(input) || !role(input.role)) {
    throw new ApiError(400, 'validation', 'Vui lòng chọn vai trò Workspace hợp lệ.', { role: 'Chọn vai trò được máy chủ cho phép.' })
  }
  return input.role
}

// Cache scopes are opaque identities, not authorization or render-time URL validators.
const userKey = (userId: string) => ['workspace-access', userId.toLowerCase()] as const
const scopeKey = (userId: string, profileId: string, workspaceId: string) => [...userKey(userId), 'profiles', profileId.toLowerCase(), 'workspaces', workspaceId.toLowerCase()] as const
export const workspaceAccessKeys = {
  user: userKey,
  scope: scopeKey,
  members: (userId: string, profileId: string, workspaceId: string, page = 1) => [...scopeKey(userId, profileId, workspaceId), 'members', pageNumber(page)] as const,
  candidates: (userId: string, profileId: string, workspaceId: string, page = 1) => [...scopeKey(userId, profileId, workspaceId), 'candidates', pageNumber(page)] as const,
}

export const workspaceAccessApi = {
  async members(profileId: string, workspaceId: string, page = 1, signal?: AbortSignal): Promise<WorkspaceAccessMembersPage> {
    const payload = await apiClient.request<unknown>(`${memberPath(profileId, workspaceId)}?page=${pageNumber(page)}`, { signal, protected: true })
    const result = parsePage(payload, (item) => parseMember(item))
    if (!record(payload)) throw invalidResponse()
    return { ...result, capabilities: parseCapabilities(payload.capabilities) }
  },
  async candidates(profileId: string, workspaceId: string, page = 1, signal?: AbortSignal): Promise<WorkspaceAccessCandidatesPage> {
    return parsePage(await apiClient.request<unknown>(`${workspacePath(profileId, workspaceId)}member-candidates/?page=${pageNumber(page)}`, { signal, protected: true }), parseCandidate)
  },
  async add(profileId: string, workspaceId: string, input: WorkspaceAccessAddInput, signal?: AbortSignal): Promise<WorkspaceAccessMember> {
    const requestedRole = validatedRole(input)
    if (!uuid(input.target_profile_membership_id)) {
      throw new ApiError(400, 'validation', 'Vui lòng chọn thành viên tổ chức hợp lệ.', { target_profile_membership_id: 'Chọn thành viên từ danh sách được cấp quyền.' })
    }
    const result = parseMember(await apiClient.request<unknown>(memberPath(profileId, workspaceId), { method: 'POST',
      body: { target_profile_membership_id: input.target_profile_membership_id, role: requestedRole }, signal, protected: true }))
    if (!sameId(result.profile_membership_id, input.target_profile_membership_id) || !result.is_active || result.role !== requestedRole) throw invalidResponse()
    return result
  },
  async update(profileId: string, workspaceId: string, membershipId: string, input: WorkspaceAccessUpdateInput, signal?: AbortSignal): Promise<WorkspaceAccessMember> {
    const requestedRole = validatedRole(input)
    const result = parseMember(await apiClient.request<unknown>(memberPath(profileId, workspaceId, membershipId), {
      method: 'PATCH', body: { role: requestedRole }, signal, protected: true,
    }), membershipId)
    if (!result.is_active || result.role !== requestedRole) throw invalidResponse()
    return result
  },
  async revoke(profileId: string, workspaceId: string, membershipId: string, signal?: AbortSignal): Promise<void> {
    const payload = await apiClient.request<unknown>(memberPath(profileId, workspaceId, membershipId), { method: 'DELETE', signal, protected: true })
    if (payload !== undefined) throw invalidResponse()
  },
}

/** Creation previews are current-user hints; the atomic create service revalidates. */
import { ApiError, apiClient, invalidResponse } from './client'
import type { Page } from './types'
import type { WorkspaceAccessRole } from './workspace-access'

export interface WorkspaceInheritanceMember {
  profile_membership_id: string
  display_name: string
  role: WorkspaceAccessRole
}
export interface WorkspaceInheritancePreview extends Page<WorkspaceInheritanceMember> {
  mode: 'inheritance' | 'initial' | 'manual'
  source_workspace: { id: string; name: string; period: string | null } | null
  excluded_count: number
  has_workspaces: boolean
}
export interface WorkspaceMembershipInput {
  readonly source_workspace_id?: string
  readonly initial_profile_membership_ids?: string[]
}
const record = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value)
const uuid = (value: unknown): value is string => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
const count = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
const nullableText = (value: unknown): value is string | null => value === null || typeof value === 'string'
const period = (value: unknown) => value === null || (typeof value === 'string' && /^(?!0000)\d{4}-(0[1-9]|1[0-2])-01$/.test(value))
function entity(value: string): string {
  if (!uuid(value)) throw new ApiError(404, 'not-found', 'Không tìm thấy nội dung hoặc bạn không có quyền truy cập.')
  return value.toLowerCase()
}

export const workspaceInheritanceApi = {
  async preview(profileId: string, sourceWorkspaceId = '', page = 1, signal?: AbortSignal): Promise<WorkspaceInheritancePreview> {
    if (!Number.isSafeInteger(page) || page < 1) throw new TypeError('Page must be a positive integer.')
    const query = new URLSearchParams({ page: String(page) })
    if (sourceWorkspaceId) query.set('source_workspace_id', entity(sourceWorkspaceId))
    const payload = await apiClient.request<unknown>(`v1/profiles/${entity(profileId)}/workspace-inheritance/?${query}`, { signal, protected: true })
    if (!record(payload) || !count(payload.count) || !count(payload.excluded_count) || typeof payload.has_workspaces !== 'boolean' ||
      !nullableText(payload.next) || !nullableText(payload.previous) || !Array.isArray(payload.results) || payload.results.length > 100 || payload.results.length > payload.count ||
      !['inheritance', 'initial', 'manual'].includes(String(payload.mode))) throw invalidResponse()
    const results = payload.results.map((member) => {
      if (!record(member) || !uuid(member.profile_membership_id) || typeof member.display_name !== 'string' || !member.display_name.trim() ||
        !['ADMIN', 'MEMBER', 'VIEWER'].includes(String(member.role))) throw invalidResponse()
      if (payload.mode === 'initial' && member.role !== 'MEMBER') throw invalidResponse()
      return { profile_membership_id: member.profile_membership_id, display_name: member.display_name, role: member.role as WorkspaceAccessRole }
    })
    if (new Set(results.map((member) => member.profile_membership_id.toLowerCase())).size !== results.length) throw invalidResponse()
    let source: WorkspaceInheritancePreview['source_workspace'] = null
    if (sourceWorkspaceId) {
      const value = payload.source_workspace
      if (payload.mode !== 'inheritance' || !record(value) || !uuid(value.id) || value.id.toLowerCase() !== sourceWorkspaceId.toLowerCase() ||
        typeof value.name !== 'string' || !period(value.period) || !payload.has_workspaces) throw invalidResponse()
      source = { id: value.id, name: value.name, period: value.period as string | null }
    } else if (payload.source_workspace !== null || payload.mode === 'inheritance' ||
      (payload.mode === 'initial' && payload.has_workspaces) || (payload.mode === 'manual' && (!payload.has_workspaces || payload.count !== 0))) throw invalidResponse()
    return { count: payload.count, next: payload.next, previous: payload.previous, results,
      mode: payload.mode as WorkspaceInheritancePreview['mode'], source_workspace: source, excluded_count: payload.excluded_count, has_workspaces: payload.has_workspaces }
  },
}

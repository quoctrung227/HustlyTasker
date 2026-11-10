/** Mocked DTO/transport checks; authorization and transactions use PostgreSQL. */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { workspaceInheritanceApi } from './workspace-inheritance'
import { workApi } from './work-management'

const profileId = '00000000-0000-4000-8000-000000000b01'
const sourceId = '00000000-0000-4000-8000-000000000b02'
const memberId = '00000000-0000-4000-8000-000000000b03'
const member = { profile_membership_id: memberId, display_name: 'Thành viên thử nghiệm', role: 'MEMBER' }
const initial = { count: 1, next: null, previous: null, results: [member], mode: 'initial', source_workspace: null, excluded_count: 0, has_workspaces: false }
const inherited = { ...initial, mode: 'inheritance', has_workspaces: true, source_workspace: { id: sourceId, name: 'Nguồn tháng trước', period: '2026-10-01' }, excluded_count: 2 }
const timestamp = '2026-11-10T00:00:00Z'
const workspace = { id: sourceId, profile_id: profileId, name: 'Tháng mới', description: null, period: '2026-11-01', status: 'ACTIVE', created_at: timestamp, updated_at: timestamp }
afterEach(() => vi.restoreAllMocks())

describe('Workspace inheritance read contract', () => {
  it('loads current-profile initial suggestions with a protected request and signal', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(initial)
    const signal = new AbortController().signal
    expect(await workspaceInheritanceApi.preview(profileId, '', 2, signal)).toEqual(initial)
    expect(request).toHaveBeenCalledExactlyOnceWith(`v1/profiles/${profileId}/workspace-inheritance/?page=2`, { signal, protected: true })
  })
  it('scopes a chosen source explicitly and never follows untrusted pagination URLs', async () => {
    const payload = { ...inherited, next: 'https://untrusted.invalid/?page=2' }
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(payload)
    expect(await workspaceInheritanceApi.preview(profileId, sourceId)).toEqual(payload)
    expect(request).toHaveBeenCalledExactlyOnceWith(`v1/profiles/${profileId}/workspace-inheritance/?page=1&source_workspace_id=${sourceId}`, { signal: undefined, protected: true })
  })
  it('projects only safe display labels/membership roles, without retaining unknown PII', async () => {
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...initial, email: 'private@example.test', results: [{ ...member, user_id: sourceId, email: 'private@example.test' }] })
    expect(await workspaceInheritanceApi.preview(profileId)).toEqual(initial)
  })
  it('accepts explicit manual setup with zero proposed memberships', async () => {
    const payload = { ...initial, count: 0, results: [], mode: 'manual', has_workspaces: true }
    vi.spyOn(apiClient, 'request').mockResolvedValue(payload)
    expect(await workspaceInheritanceApi.preview(profileId)).toEqual(payload)
  })
  it.each([
    { ...initial, count: -1 }, { ...initial, count: 0 }, { ...initial, excluded_count: '1' },
    { ...initial, mode: 'new-role' }, { ...initial, has_workspaces: true }, { ...initial, next: 1 },
    { ...initial, results: [{ ...member, profile_membership_id: 'bad' }] },
    { ...initial, results: [{ ...member, display_name: ' ' }] },
    { ...initial, results: [{ ...member, role: 'ADMIN' }] },
    { ...initial, count: 2, results: [member, member] },
    { ...initial, source_workspace: inherited.source_workspace },
  ])('fails closed on malformed initial preview %j', async (payload) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(payload)
    await expect(workspaceInheritanceApi.preview(profileId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it.each([
    { ...inherited, mode: 'manual' }, { ...inherited, source_workspace: null },
    { ...inherited, source_workspace: { ...inherited.source_workspace, id: memberId } },
    { ...inherited, source_workspace: { ...inherited.source_workspace, period: '2026-10-15' } },
    { ...inherited, results: [{ ...member, role: 'OWNER' }] },
  ])('rejects a wrong source identity or invalid snapshot %j', async (payload) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(payload)
    await expect(workspaceInheritanceApi.preview(profileId, sourceId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it.each([0, -1, 1.5, Number.NaN])('rejects invalid page %s before transport', async (page) => {
    const request = vi.spyOn(apiClient, 'request')
    await expect(workspaceInheritanceApi.preview(profileId, '', page)).rejects.toBeInstanceOf(TypeError)
    expect(request).not.toHaveBeenCalled()
  })
  it('rejects malformed Profile/source IDs before transport', async () => {
    const request = vi.spyOn(apiClient, 'request')
    await expect(workspaceInheritanceApi.preview('../private')).rejects.toMatchObject({ status: 404 })
    await expect(workspaceInheritanceApi.preview(profileId, '../private')).rejects.toMatchObject({ status: 404 })
    expect(request).not.toHaveBeenCalled()
  })
})

describe('additive Workspace creation input', () => {
  it.each([{ source_workspace_id: sourceId }, { initial_profile_membership_ids: [memberId] }, {}])('preserves existing transport/CSRF path with %j', async (memberships) => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(workspace)
    const input = { name: 'Tháng mới', period: '2026-11-01', ...memberships }
    expect(await workApi.createWorkspace(profileId, input)).toEqual(workspace)
    expect(request).toHaveBeenCalledExactlyOnceWith(`v1/profiles/${profileId}/workspaces/`, { method: 'POST', body: input, signal: undefined, protected: true })
  })
})

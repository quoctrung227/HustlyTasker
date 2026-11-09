/** Mocked transport/DTO contracts; business transitions use isolated browser tests. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiClient } from './client'
import { workspaceAccessApi, workspaceAccessKeys } from './workspace-access'
import type { WorkspaceAccessAddInput, WorkspaceAccessUpdateInput } from './workspace-access'

const userId = '00000000-0000-4000-8000-000000000a01'
const profileId = '00000000-0000-4000-8000-000000000a02'
const workspaceId = '00000000-0000-4000-8000-000000000a03'
const membershipId = '00000000-0000-4000-8000-000000000a04'
const targetId = '00000000-0000-4000-8000-000000000a05'
const otherId = '00000000-0000-4000-8000-000000000a06'
const timestamp = '2026-11-09T00:00:00Z'
const base = `v1/profiles/${profileId}/workspaces/${workspaceId}/`
const capabilities = { can_add: true, allowed_roles: ['ADMIN', 'MEMBER', 'VIEWER'], profile_role: 'OWNER', workspace_role: null, has_inherited_access: true }
const rowCapabilities = { can_update: true, can_revoke: true, allowed_roles: ['ADMIN', 'MEMBER', 'VIEWER'], has_inherited_access: false }
const member = { id: membershipId, profile_membership_id: targetId, display_label: 'Thành viên Kiểm thử', is_assignable: true,
  role: 'MEMBER', is_active: true, joined_at: timestamp, updated_at: timestamp, capabilities: rowCapabilities }
const candidate = { profile_membership_id: targetId, display_label: 'Thành viên Kiểm thử', profile_role: 'MEMBER', has_inherited_access: false }
const page = <T,>(results: T[]) => ({ count: results.length, next: null, previous: null, results })
const json = (payload: unknown, status = 200) => new Response(JSON.stringify(payload), { status, headers: { 'content-type': 'application/json' } })

beforeEach(() => { apiClient.clearCsrf(); apiClient.setForbiddenHandler(null) })
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); apiClient.clearCsrf(); apiClient.setForbiddenHandler(null) })

describe('Workspace-scoped management reads', () => {
  it('loads the existing protected roster with explicit Profile/Workspace/page/signal scope', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([member]), capabilities })
    const signal = new AbortController().signal
    expect(await workspaceAccessApi.members(profileId, workspaceId, 2, signal)).toEqual({ ...page([member]), capabilities })
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}members/?page=2`, { signal, protected: true })
  })

  it('projects safe labels and server capabilities without retaining global User data', async () => {
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([{ ...member, user_id: otherId, email: 'private@example.test', password: 'private-canary',
      capabilities: { ...rowCapabilities, user_id: otherId } }]), capabilities: { ...capabilities, session: 'private-canary' }, secret: 'private-canary' })
    const value = await workspaceAccessApi.members(profileId, workspaceId)
    expect(value).toEqual({ ...page([member]), capabilities })
    expect(JSON.stringify(value)).not.toMatch(/private|user_id|session|password/)
  })

  it('keeps a Workspace Admin ceiling and explicit/inherited access distinct', async () => {
    const actor = { can_add: true, allowed_roles: ['MEMBER', 'VIEWER'], profile_role: 'MEMBER', workspace_role: 'ADMIN', has_inherited_access: false }
    const row = { ...member, capabilities: { ...rowCapabilities, allowed_roles: ['MEMBER', 'VIEWER'], has_inherited_access: true } }
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([row]), capabilities: actor })
    expect(await workspaceAccessApi.members(profileId, workspaceId)).toEqual({ ...page([row]), capabilities: actor })
  })

  it('accepts archived read-only roster metadata without inventing mutation rights', async () => {
    const readonly = { ...capabilities, can_add: false, allowed_roles: [] }
    const row = { ...member, is_assignable: false, capabilities: { ...rowCapabilities, can_update: false, can_revoke: false, allowed_roles: [] } }
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([row]), capabilities: readonly })
    expect(await workspaceAccessApi.members(profileId, workspaceId)).toEqual({ ...page([row]), capabilities: readonly })
  })

  it.each([
    undefined, {}, { ...capabilities, can_add: 'true' }, { ...capabilities, allowed_roles: ['OWNER'] },
    { ...capabilities, allowed_roles: ['MEMBER', 'MEMBER'] }, { ...capabilities, allowed_roles: [] },
    { ...capabilities, profile_role: 'SUPERUSER' }, { ...capabilities, workspace_role: 'OWNER' },
    { ...capabilities, has_inherited_access: 1 },
  ])('fails closed when the current actor capability envelope is absent or invalid', async (value) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([member]), capabilities: value })
    await expect(workspaceAccessApi.members(profileId, workspaceId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it.each([
    { ...member, id: 'not-an-id' }, { ...member, profile_membership_id: null }, { ...member, display_label: ' ' },
    { ...member, role: 'OWNER' }, { ...member, is_active: 'true' }, { ...member, is_assignable: 1 },
    { ...member, updated_at: 'invalid-date' }, { ...member, capabilities: undefined },
    { ...member, capabilities: { ...rowCapabilities, can_update: 'true' } },
    { ...member, capabilities: { ...rowCapabilities, allowed_roles: ['MEMBER', 'MEMBER'] } },
    { ...member, capabilities: { ...rowCapabilities, allowed_roles: [] } },
  ])('rejects malformed rows or missing row-level mutation hints', async (value) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...page([value]), capabilities })
    await expect(workspaceAccessApi.members(profileId, workspaceId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('uses the dedicated Workspace-authorized candidate route rather than the Profile governance directory', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(page([candidate]))
    const signal = new AbortController().signal
    expect(await workspaceAccessApi.candidates(profileId, workspaceId, 2, signal)).toEqual(page([candidate]))
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}member-candidates/?page=2`, { signal, protected: true })
  })

  it('preserves an inherited-access candidate warning while omitting unneeded identities', async () => {
    const owner = { ...candidate, profile_role: 'OWNER', has_inherited_access: true }
    vi.spyOn(apiClient, 'request').mockResolvedValue(page([{ ...owner, user_id: otherId, email: 'private@example.test' }]))
    const value = await workspaceAccessApi.candidates(profileId, workspaceId)
    expect(value).toEqual(page([owner]))
    expect(JSON.stringify(value)).not.toMatch(/user_id|email|private/)
  })

  it('accepts an empty candidate page without fabricating a user or selection', async () => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(page([]))
    expect(await workspaceAccessApi.candidates(profileId, workspaceId)).toEqual(page([]))
  })

  it.each([
    { ...candidate, profile_membership_id: 'not-an-id' }, { ...candidate, display_label: '' },
    { ...candidate, profile_role: 'VIEWER' }, { ...candidate, has_inherited_access: 'false' },
  ])('rejects malformed candidate identities and Profile-role metadata', async (value) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(page([value]))
    await expect(workspaceAccessApi.candidates(profileId, workspaceId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it.each([
    { count: -1, next: null, previous: null, results: [] },
    { count: 0.5, next: null, previous: null, results: [] },
    { count: 0, next: null, previous: null, results: [candidate] },
    { count: 1, next: false, previous: null, results: [candidate] },
    page(Array.from({ length: 101 }, () => candidate)),
  ])('rejects malformed or oversized candidate pagination', async (value) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(value)
    await expect(workspaceAccessApi.candidates(profileId, workspaceId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('keeps external pagination URLs as metadata and never follows them', async () => {
    const payload = { ...page([candidate]), next: 'https://untrusted.invalid/private?page=2' }
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(payload)
    expect(await workspaceAccessApi.candidates(profileId, workspaceId)).toEqual(payload)
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}member-candidates/?page=1`, { signal: undefined, protected: true })
  })
})

describe('existing Workspace membership write contracts', () => {
  it('posts only a ProfileMembership target and valid Workspace role', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(member)
    const signal = new AbortController().signal
    const input = { target_profile_membership_id: targetId, role: 'MEMBER', user_id: otherId, owner_id: otherId, is_active: false } as WorkspaceAccessAddInput
    expect(await workspaceAccessApi.add(profileId, workspaceId, input, signal)).toEqual(member)
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}members/`, { method: 'POST',
      body: { target_profile_membership_id: targetId, role: 'MEMBER' }, signal, protected: true })
  })

  it.each([201, 200])('handles new creation/reactivation HTTP%s through the existing CSRF/session client', async (status) => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(json(member, status))
    vi.stubGlobal('fetch', fetchMock)
    expect(await workspaceAccessApi.add(profileId, workspaceId, { target_profile_membership_id: targetId, role: 'MEMBER' })).toEqual(member)
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/auth/csrf/', expect.objectContaining({ method: 'GET', credentials: 'same-origin' }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, `/api/${base}members/`, expect.objectContaining({ method: 'POST', credentials: 'same-origin',
      body: JSON.stringify({ target_profile_membership_id: targetId, role: 'MEMBER' }), headers: expect.objectContaining({ 'X-CSRFToken': 'a'.repeat(64) }) }))
  })

  it('patches only the role of the selected WorkspaceMember row', async () => {
    const updated = { ...member, role: 'VIEWER', is_assignable: false }
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(updated)
    const signal = new AbortController().signal
    const input = { role: 'VIEWER', target_profile_membership_id: otherId } as WorkspaceAccessUpdateInput
    expect(await workspaceAccessApi.update(profileId, workspaceId, membershipId, input, signal)).toEqual(updated)
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}members/${membershipId}/`, { method: 'PATCH', body: { role: 'VIEWER' }, signal, protected: true })
  })

  it('requires a successful204 response for revoke and sends no invented membership body', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(undefined)
    const signal = new AbortController().signal
    await expect(workspaceAccessApi.revoke(profileId, workspaceId, membershipId, signal)).resolves.toBeUndefined()
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}members/${membershipId}/`, { method: 'DELETE', signal, protected: true })
  })

  it('does not treat a JSON response as a confirmed204 revoke', async () => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(member)
    await expect(workspaceAccessApi.revoke(profileId, workspaceId, membershipId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('rejects wrong-target creation responses without declaring the requested grant successful', async () => {
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...member, profile_membership_id: otherId })
    await expect(workspaceAccessApi.add(profileId, workspaceId, { target_profile_membership_id: targetId, role: 'MEMBER' })).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('rejects update responses belonging to another WorkspaceMember row', async () => {
    vi.spyOn(apiClient, 'request').mockResolvedValue({ ...member, id: otherId })
    await expect(workspaceAccessApi.update(profileId, workspaceId, membershipId, { role: 'MEMBER' })).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it.each([{ ...member, is_active: false }, { ...member, role: 'VIEWER' }])('does not report a different role or inactive result as the requested grant', async (value) => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(value)
    await expect(workspaceAccessApi.add(profileId, workspaceId, { target_profile_membership_id: targetId, role: 'MEMBER' })).rejects.toMatchObject({ kind: 'invalid-response' })
    await expect(workspaceAccessApi.update(profileId, workspaceId, membershipId, { role: 'MEMBER' })).rejects.toMatchObject({ kind: 'invalid-response' })
  })

  it('rejects invented roles and malformed target identities before transport', async () => {
    const request = vi.spyOn(apiClient, 'request')
    await expect(workspaceAccessApi.add(profileId, workspaceId, { target_profile_membership_id: targetId, role: 'OWNER' } as unknown as WorkspaceAccessAddInput)).rejects.toMatchObject({ status: 400, fieldErrors: { role: expect.any(String) } })
    await expect(workspaceAccessApi.update(profileId, workspaceId, membershipId, { role: 'SUPERUSER' } as unknown as WorkspaceAccessUpdateInput)).rejects.toMatchObject({ status: 400 })
    await expect(workspaceAccessApi.add(profileId, workspaceId, { target_profile_membership_id: '../private', role: 'MEMBER' })).rejects.toMatchObject({ status: 400, fieldErrors: { target_profile_membership_id: expect.any(String) } })
    expect(request).not.toHaveBeenCalled()
  })

  it.each(['', '../private', 'https://untrusted.invalid', `${profileId}/members`])('rejects invalid route IDs before any request', async (value) => {
    const request = vi.spyOn(apiClient, 'request')
    await expect(workspaceAccessApi.members(value, workspaceId)).rejects.toMatchObject({ status: 404 })
    await expect(workspaceAccessApi.candidates(profileId, value)).rejects.toMatchObject({ status: 404 })
    await expect(workspaceAccessApi.revoke(profileId, workspaceId, value)).rejects.toMatchObject({ status: 404 })
    expect(request).not.toHaveBeenCalled()
  })

  it.each([0, -1, 1.5, Number.NaN, Infinity])('rejects invalid pages before transport', async (value) => {
    const request = vi.spyOn(apiClient, 'request')
    await expect(workspaceAccessApi.members(profileId, workspaceId, value)).rejects.toBeInstanceOf(TypeError)
    await expect(workspaceAccessApi.candidates(profileId, workspaceId, value)).rejects.toBeInstanceOf(TypeError)
    expect(request).not.toHaveBeenCalled()
  })

  it.each([400, 403, 404, 409, 429])('preserves safe HTTP%s errors without automatic grant retry or backend details', async (status) => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) }))
      .mockResolvedValueOnce(json({ detail: 'private-tenant-identity-canary', user_id: ['private-user-canary'] }, status))
    vi.stubGlobal('fetch', fetchMock)
    const error: unknown = await workspaceAccessApi.add(profileId, workspaceId, { target_profile_membership_id: targetId, role: 'MEMBER' }).catch((value: unknown) => value)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status })
    expect(JSON.stringify(error)).not.toMatch(/private-|user_id/)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('keeps CSRF denial distinct from lost Workspace authority and requires an explicit retry', async () => {
    const forbidden = vi.fn()
    apiClient.setForbiddenHandler(forbidden)
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) }))
      .mockResolvedValueOnce(json({ detail: 'CSRF Failed: synthetic denial' }, 403))
      .mockResolvedValueOnce(json({ csrf_token: 'b'.repeat(64) })).mockResolvedValueOnce(json(member, 201))
    vi.stubGlobal('fetch', fetchMock)
    const input: WorkspaceAccessAddInput = { target_profile_membership_id: targetId, role: 'MEMBER' }
    await expect(workspaceAccessApi.add(profileId, workspaceId, input)).rejects.toMatchObject({ kind: 'csrf', status: 403 })
    expect(forbidden).not.toHaveBeenCalled()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    await expect(workspaceAccessApi.add(profileId, workspaceId, input)).resolves.toEqual(member)
    expect(fetchMock).toHaveBeenCalledTimes(4)
  })

  it('delegates expired-session revalidation to the existing protected client without retaining a roster', async () => {
    const forbidden = vi.fn()
    apiClient.setForbiddenHandler(forbidden)
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ detail: 'private-expired-session' }, 401))
    vi.stubGlobal('fetch', fetchMock)
    await expect(workspaceAccessApi.members(profileId, workspaceId)).rejects.toMatchObject({ kind: 'authentication', status: 401 })
    expect(forbidden).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledOnce()
  })

  it('forwards cancellation and never retries an aborted membership mutation', async () => {
    const signal = new AbortController().signal
    const failure = new DOMException('The operation was aborted.', 'AbortError')
    const request = vi.spyOn(apiClient, 'request').mockRejectedValue(failure)
    await expect(workspaceAccessApi.update(profileId, workspaceId, membershipId, { role: 'VIEWER' }, signal)).rejects.toBe(failure)
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}members/${membershipId}/`, { method: 'PATCH', body: { role: 'VIEWER' }, signal, protected: true })
  })
})

describe('private Workspace access query scopes', () => {
  it('separates every User/Profile/Workspace/page and candidate versus roster key', () => {
    const initial = workspaceAccessKeys.members(userId, profileId, workspaceId)
    expect(initial).not.toEqual(workspaceAccessKeys.members(otherId, profileId, workspaceId))
    expect(initial).not.toEqual(workspaceAccessKeys.members(userId, otherId, workspaceId))
    expect(initial).not.toEqual(workspaceAccessKeys.members(userId, profileId, otherId))
    expect(initial).not.toEqual(workspaceAccessKeys.members(userId, profileId, workspaceId, 2))
    expect(initial).not.toEqual(workspaceAccessKeys.candidates(userId, profileId, workspaceId))
    expect(workspaceAccessKeys.scope(userId, profileId, workspaceId)).toEqual(['workspace-access', userId, 'profiles', profileId, 'workspaces', workspaceId])
  })

  it('normalizes opaque key IDs without throwing during invalid-route renders or authorizing transport', () => {
    const request = vi.spyOn(apiClient, 'request')
    expect(workspaceAccessKeys.members('Pending-Identity', 'Invalid-Profile', 'Invalid-Workspace')).toEqual([
      'workspace-access', 'pending-identity', 'profiles', 'invalid-profile', 'workspaces', 'invalid-workspace', 'members', 1,
    ])
    expect(workspaceAccessKeys.scope(userId.toUpperCase(), profileId.toUpperCase(), workspaceId.toUpperCase())).toEqual(workspaceAccessKeys.scope(userId, profileId, workspaceId))
    expect(request).not.toHaveBeenCalled()
  })
})

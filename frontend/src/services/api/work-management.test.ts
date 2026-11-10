/** Mock transport/contract tests, not real permission or mutation proof. */
import { QueryClient } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiClient, ApiError, apiClient } from './client'
import { taskQuery, workApi, workKeys } from './work-management'
import type { Task, WorkspaceMember } from './work-management'

const profileId = '00000000-0000-4000-8000-000000000101'
const workspaceId = '00000000-0000-4000-8000-000000000102'
const otherId = '00000000-0000-4000-8000-000000000103'
const taskId = '00000000-0000-4000-8000-000000000104'
const memberId = '00000000-0000-4000-8000-000000000105'
const timestamp = '2026-10-26T00:00:00Z'
const task: Task = { id: taskId, workspace_id: workspaceId, parent_id: null, title: 'Allowed fixture', description: null, status: 'PENDING', priority: 'MEDIUM', deadline: null, active_assignment: null, can_start: false, can_submit: false, created_at: timestamp, updated_at: timestamp,
  raw_video_url: null, reference_video_url: null, template_project_url: null, script_url: null, estimated_compensation_vnd: null }
const workspace = { id: workspaceId, profile_id: profileId, name: 'Scoped fixture', description: null, period: '2026-10-01', status: 'ACTIVE', created_at: timestamp, updated_at: timestamp }
const member: WorkspaceMember = { id: otherId, profile_membership_id: memberId, role: 'MEMBER', is_active: true, display_label: 'An Nguyễn', is_assignable: true, joined_at: timestamp, updated_at: timestamp }
const page = <T,>(results: T[]) => ({ count: results.length, next: null, previous: null, results })
const metadata = (post?: Record<string, unknown>) => ({ name: 'Existing view', renders: ['application/json'], parses: ['application/json'], ...(post === undefined ? {} : { actions: { POST: post } }) })
const wsPath = `v1/profiles/${profileId}/workspaces/${workspaceId}/`
const taskPath = `${wsPath}tasks/`

beforeEach(() => { vi.spyOn(apiClient, 'request') })

describe('safe OPTIONS and localized field errors', () => {
  it('sends OPTIONS as a safe same-origin no-store request without CSRF bootstrap/header', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(metadata({})), { status: 200, headers: { 'content-type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    try {
      await new ApiClient().request('v1/profiles/', { method: 'OPTIONS' })
      expect(fetchMock).toHaveBeenCalledTimes(1)
      expect(fetchMock).toHaveBeenCalledWith('/api/v1/profiles/', expect.objectContaining({ method: 'OPTIONS', credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } }))
    } finally { vi.unstubAllGlobals() }
  })

  it('maps only known validation field names to local text, including Django parent errors', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: 'a'.repeat(64) }), { headers: { 'content-type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ title: ['private server text'], parent: ['private server text'], unexpected_secret: ['hidden'], target_profile_membership_id: ['hidden'] }), { status: 400, headers: { 'content-type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    try {
      const error = await new ApiClient().request(taskPath, { method: 'POST', body: { title: '' } }).catch((value: unknown) => value)
      expect(error).toMatchObject({ status: 400, fieldErrors: { title: expect.any(String), parent_id: expect.any(String), target_profile_membership_id: expect.any(String) } })
      expect(JSON.stringify(error)).not.toContain('private server text')
      expect(JSON.stringify(error)).not.toContain('unexpected_secret')
    } finally { vi.unstubAllGlobals() }
  })
})

describe('Task filters, scope and read contracts', () => {
  it('normalizes missing legacy brief fields to null without rejecting older Task responses', async () => {
    const legacy = { ...task }
    delete legacy.raw_video_url; delete legacy.reference_video_url; delete legacy.template_project_url; delete legacy.script_url; delete legacy.estimated_compensation_vnd
    vi.mocked(apiClient.request).mockResolvedValue(legacy)
    expect(await workApi.task(profileId, workspaceId, taskId)).toEqual(task)
    vi.mocked(apiClient.request).mockResolvedValue(page([legacy]))
    expect(await workApi.tasks(profileId, workspaceId)).toEqual(page([task]))
  })
  it('preserves exact large compensation strings and allowed private document links in read responses', async () => {
    const brief = { ...task, raw_video_url: 'https://drive.google.com/file/d/synthetic/view', script_url: 'https://docs.google.com/document/d/synthetic/edit', estimated_compensation_vnd: '9007199254740993' }
    vi.mocked(apiClient.request).mockResolvedValue(brief)
    expect(await workApi.task(profileId, workspaceId, taskId)).toEqual(brief)
  })
  it.each(['detail', 'list', 'subtasks', 'create', 'update', 'assign', 'start'] as const)('keeps server-redacted null compensation in the %s response without reconstructing a hidden amount', async (action) => {
    const redacted = { ...task, script_url: 'https://example.test/script', estimated_compensation_vnd: null }
    vi.mocked(apiClient.request).mockResolvedValue(
      action === 'list' ? page([redacted]) : action === 'subtasks' ? page([{ ...redacted, id: otherId, parent_id: taskId }]) : redacted,
    )
    let result: Task | undefined
    switch (action) {
      case 'list': result = (await workApi.tasks(profileId, workspaceId)).results[0]; break
      case 'subtasks': result = (await workApi.subtasks(profileId, workspaceId, taskId)).results[0]; break
      case 'create': result = await workApi.createTask(profileId, workspaceId, { title: 'Allowed metadata' }); break
      case 'update': result = await workApi.updateTask(profileId, workspaceId, taskId, { description: 'Only metadata' }); break
      case 'assign': result = await workApi.assignTask(profileId, workspaceId, taskId, { target_profile_membership_id: memberId }); break
      case 'start': result = await workApi.startTask(profileId, workspaceId, taskId); break
      default: result = await workApi.task(profileId, workspaceId, taskId)
    }
    expect(result?.estimated_compensation_vnd).toBeNull()
    expect(result?.script_url).toBe('https://example.test/script')
    expect(JSON.stringify(result)).not.toContain('9007199254740993')
    if (action === 'update') expect(apiClient.request).toHaveBeenCalledWith(`${taskPath}${taskId}/`, expect.objectContaining({ method: 'PATCH', body: { description: 'Only metadata' } }))
  })
  it('replaces cached detail and list amounts with server-redacted nulls under the same tenant keys', async () => {
    const cache = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } })
    const visible = { ...task, estimated_compensation_vnd: '9007199254740993' }
    const redacted = { ...task, estimated_compensation_vnd: null }
    const detailKey = workKeys.task(profileId, workspaceId, taskId)
    const listKey = workKeys.tasks(profileId, workspaceId)
    try {
      cache.setQueryData(detailKey, visible)
      cache.setQueryData(listKey, page([visible]))
      vi.mocked(apiClient.request).mockResolvedValueOnce(redacted).mockResolvedValueOnce(page([redacted]))
      await cache.fetchQuery({ queryKey: detailKey, queryFn: () => workApi.task(profileId, workspaceId, taskId) })
      await cache.fetchQuery({ queryKey: listKey, queryFn: () => workApi.tasks(profileId, workspaceId) })
      expect(cache.getQueryData<Task>(detailKey)?.estimated_compensation_vnd).toBeNull()
      expect(cache.getQueryData<{ results: Task[] }>(listKey)?.results[0]?.estimated_compensation_vnd).toBeNull()
      expect(JSON.stringify(cache.getQueryData(detailKey))).not.toContain('9007199254740993')
      expect(JSON.stringify(cache.getQueryData(listKey))).not.toContain('9007199254740993')
    } finally { cache.clear() }
  })
  it.each([
    { raw_video_url: 'javascript:alert(1)' }, { reference_video_url: 'data:text/plain,x' }, { template_project_url: 42 }, { script_url: 'not a URL' },
    { estimated_compensation_vnd: -1 }, { estimated_compensation_vnd: 500000 }, { estimated_compensation_vnd: '1.5' }, { estimated_compensation_vnd: '1e6' },
    { estimated_compensation_vnd: '1000000000000000000' },
  ])('rejects malformed/unsafe brief metadata %#', async (metadata) => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...task, ...metadata })
    await expect(workApi.task(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it.each([undefined, null, 'true', 1])('rejects a missing or non-boolean submission capability (%s)', async (can_submit) => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...task, can_submit })
    await expect(workApi.task(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('uses only supported server filters and local page numbers', () => {
    const result = new URLSearchParams(taskQuery({ status: 'WORKING', priority: 'URGENT', root_only: true, ordering: '-deadline', deadline_after: timestamp }, 2))
    expect(Object.fromEntries(result)).toEqual({ page: '2', status: 'WORKING', priority: 'URGENT', ordering: '-deadline', deadline_after: timestamp, root_only: 'true' })
    expect(result.has('search')).toBe(false)
  })
  it('rejects impossible combined parent/root filters and reversed/invalid dates', () => {
    expect(() => taskQuery({ root_only: true, parent_id: taskId })).toThrow()
    expect(() => taskQuery({ deadline_after: 'not-a-date' })).toThrow()
    expect(() => taskQuery({ deadline_after: '2026-10-27T00:00:00Z', deadline_before: timestamp })).toThrow()
    expect(() => taskQuery({}, 0)).toThrow()
  })
  it('reads the scoped flat Task page without inventing aggregates', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(page([task]))
    expect(await workApi.tasks(profileId, workspaceId, { priority: 'HIGH' }, 2)).toEqual(page([task]))
    expect(apiClient.request).toHaveBeenCalledWith(`${taskPath}?page=2&priority=HIGH`, { signal: undefined, protected: true })
  })
  it('preserves the existing server CANCELLED legacy value without adding a transition', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...task, status: 'CANCELLED' })
    expect((await workApi.task(profileId, workspaceId, taskId)).status).toBe('CANCELLED')
  })
  it.each([{ ...task, workspace_id: otherId }, { ...task, status: 'NEW_CLIENT_STATUS' }, { ...task, deadline: 'overflow' }])('rejects malformed or wrong-Workspace Task details', async (payload) => {
    vi.mocked(apiClient.request).mockResolvedValue(payload)
    await expect(workApi.task(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('accepts null historical assignment identity but validates present attribution', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...task, active_assignment: { id: otherId, profile_membership_id: null, assigned_at: timestamp } })
    expect((await workApi.task(profileId, workspaceId, taskId)).active_assignment?.profile_membership_id).toBeNull()
    vi.mocked(apiClient.request).mockResolvedValue({ ...task, active_assignment: { id: otherId, profile_membership_id: 'not-a-uuid', assigned_at: timestamp } })
    await expect(workApi.task(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it.each(['An Nguyễn', null, undefined])('accepts the additive scoped assignee name %s without requiring a global User ID', async (display_name) => {
    const active_assignment = { id: otherId, profile_membership_id: memberId, assigned_at: timestamp, display_name }
    vi.mocked(apiClient.request).mockResolvedValue({ ...task, active_assignment })
    const result = await workApi.task(profileId, workspaceId, taskId)
    expect(result.active_assignment).toEqual(active_assignment)
    expect(result.active_assignment).not.toHaveProperty('user_id')
  })
  it.each([true, 12, {}, '', '   '])('rejects malformed assignee display labels %j', async (display_name) => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...task, active_assignment: { id: otherId, profile_membership_id: memberId, assigned_at: timestamp, display_name } })
    await expect(workApi.task(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('replaces a formerly readable assignee name with the current nullable projection in the same query cache', async () => {
    const cache = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } })
    const key = workKeys.task(profileId, workspaceId, taskId)
    const visible = { ...task, active_assignment: { id: otherId, profile_membership_id: memberId, assigned_at: timestamp, display_name: 'Tên cũ' } }
    const redacted = { ...task, active_assignment: { ...visible.active_assignment, display_name: null } }
    try {
      cache.setQueryData(key, visible)
      vi.mocked(apiClient.request).mockResolvedValue(redacted)
      await cache.fetchQuery({ queryKey: key, queryFn: () => workApi.task(profileId, workspaceId, taskId) })
      expect(cache.getQueryData<Task>(key)?.active_assignment?.display_name).toBeNull()
      expect(JSON.stringify(cache.getQueryData(key))).not.toContain('Tên cũ')
    } finally { cache.clear() }
  })
  it('requests exactly one direct child level and rejects a mismatched parent', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(page([{ ...task, id: otherId, parent_id: taskId }]))
    expect((await workApi.subtasks(profileId, workspaceId, taskId)).results).toHaveLength(1)
    expect(apiClient.request).toHaveBeenCalledWith(`${taskPath}${taskId}/subtasks/?page=1`, { signal: undefined, protected: true })
    vi.mocked(apiClient.request).mockResolvedValue(page([{ ...task, id: otherId, parent_id: memberId }]))
    await expect(workApi.subtasks(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('keeps every read/query key scoped to Profile and Workspace', () => {
    expect(workKeys.tasks(profileId, workspaceId)).not.toEqual(workKeys.tasks(otherId, workspaceId))
    expect(workKeys.tasks(profileId, workspaceId)).not.toEqual(workKeys.tasks(profileId, otherId))
    expect(workKeys.capabilities(profileId, workspaceId)).not.toEqual(workKeys.capabilities(otherId, workspaceId))
    expect(workKeys.scope(profileId, workspaceId)).toEqual(['work', profileId, 'workspaces', workspaceId])
  })
  it('rejects malformed IDs before any request and preserves tenant404', async () => {
    await expect(workApi.task(profileId, workspaceId, '../foreign')).rejects.toMatchObject({ status: 404 })
    expect(apiClient.request).not.toHaveBeenCalled()
    const denied = new ApiError(404, 'not-found', 'Không tìm thấy nội dung hoặc bạn không có quyền truy cập.')
    vi.mocked(apiClient.request).mockRejectedValue(denied)
    await expect(workApi.task(profileId, workspaceId, taskId)).rejects.toBe(denied)
  })
  it('reads paginated sanitized members without requiring names or global User IDs', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(page([member]))
    expect(await workApi.members(profileId, workspaceId, 2)).toEqual(page([member]))
    expect(apiClient.request).toHaveBeenCalledWith(`${wsPath}members/?page=2`, { signal: undefined, protected: true })
  })
  it.each([undefined, null, 'true', 1])('rejects an absent or non-boolean current-user start hint %s', async (can_start) => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...task, can_start })
    await expect(workApi.task(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('keeps backend start eligibility without trying to map a User ID to membership identity', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...task, status: 'ASSIGNED', can_start: true, active_assignment: { id: otherId, profile_membership_id: memberId, assigned_at: timestamp } })
    expect((await workApi.task(profileId, workspaceId, taskId)).can_start).toBe(true)
  })
  it.each([{ ...member, display_label: undefined }, { ...member, display_label: '' }, { ...member, is_assignable: 'true' }])('fails closed on missing or malformed member presentation contracts', async (payload) => {
    vi.mocked(apiClient.request).mockResolvedValue(page([payload]))
    await expect(workApi.members(profileId, workspaceId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
})

describe('existing mutation contracts', () => {
  it('creates a Task without mixing assignment or arbitrary status fields', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(task)
    const input = { title: 'Scoped task', priority: 'HIGH' as const, parent_id: null, deadline: timestamp }
    await workApi.createTask(profileId, workspaceId, input)
    expect(apiClient.request).toHaveBeenCalledWith(taskPath, { method: 'POST', body: input, signal: undefined, protected: true })
    expect(Object.keys(input)).not.toContain('status')
    expect(Object.keys(input)).not.toContain('assignee')
  })
  it('updates only the supplied mutable metadata via PATCH', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(task)
    await workApi.updateTask(profileId, workspaceId, taskId, { deadline: null, priority: 'LOW' })
    expect(apiClient.request).toHaveBeenCalledWith(`${taskPath}${taskId}/`, { method: 'PATCH', body: { deadline: null, priority: 'LOW' }, signal: undefined, protected: true })
  })
  it('assigns using the server ProfileMembership identifier in a separate action', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(task)
    await workApi.assignTask(profileId, workspaceId, taskId, { target_profile_membership_id: memberId })
    expect(apiClient.request).toHaveBeenCalledWith(`${taskPath}${taskId}/assign/`, { method: 'POST', body: { target_profile_membership_id: memberId }, signal: undefined, protected: true })
  })
  it('start transport uses an empty service action, not a status patch', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(task)
    await workApi.startTask(profileId, workspaceId, taskId)
    expect(apiClient.request).toHaveBeenCalledWith(`${taskPath}${taskId}/start/`, { method: 'POST', body: {}, signal: undefined, protected: true })
  })
  it('creates and updates Workspace metadata through the actual methods', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(workspace)
    await workApi.createWorkspace(profileId, { name: 'New month', period: '2026-11-01' })
    expect(apiClient.request).toHaveBeenLastCalledWith(`v1/profiles/${profileId}/workspaces/`, { method: 'POST', body: { name: 'New month', period: '2026-11-01' }, signal: undefined, protected: true })
    await workApi.updateWorkspace(profileId, workspaceId, { description: 'Updated' })
    expect(apiClient.request).toHaveBeenLastCalledWith(wsPath, { method: 'PATCH', body: { description: 'Updated' }, signal: undefined, protected: true })
  })
  it.each(['archive', 'restore'] as const)('uses the %s lifecycle action with an empty body', async (action) => {
    vi.mocked(apiClient.request).mockResolvedValue(workspace)
    await workApi.setWorkspaceStatus(profileId, workspaceId, action)
    expect(apiClient.request).toHaveBeenCalledWith(`${wsPath}${action}/`, { method: 'POST', body: {}, signal: undefined, protected: true })
  })
  it('rejects a mutation response moved to a foreign tenant', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...workspace, profile_id: otherId })
    await expect(workApi.updateWorkspace(profileId, workspaceId, { name: 'Any' })).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('does not turn server validation/conflict/permission failures into success', async () => {
    for (const status of [400, 403, 409]) {
      const failure = new ApiError(status, status === 409 ? 'conflict' : status === 403 ? 'forbidden' : 'validation', 'Local safe error')
      vi.mocked(apiClient.request).mockRejectedValueOnce(failure)
      await expect(workApi.createTask(profileId, workspaceId, { title: 'Retained form' })).rejects.toBe(failure)
    }
  })
})

describe('permission metadata hints fail closed', () => {
  it('recognizes verified POST even when the accepted body is empty', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(metadata({}))
    expect(await workApi.capabilities(profileId, workspaceId)).toEqual({ createWorkspace: true, manageTasks: true, manageWorkspace: true, manageLifecycle: true })
    expect(apiClient.request).toHaveBeenCalledTimes(3)
    for (const call of vi.mocked(apiClient.request).mock.calls) expect(call[1]).toEqual({ method: 'OPTIONS', signal: undefined })
  })
  it('does not infer permissions from allowed methods or read-only serializer metadata', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...metadata(), allowed_methods: ['POST', 'PATCH'] })
    expect(await workApi.capabilities(profileId, workspaceId)).toEqual({ createWorkspace: false, manageTasks: false, manageWorkspace: false, manageLifecycle: false })
  })
  it.each([401, 403, 404])('treats expected capability denial %s as false without a mutation or auth callback', async (status) => {
    vi.mocked(apiClient.request).mockRejectedValue(new ApiError(status, 'forbidden', 'Safe denial'))
    expect(await workApi.capabilities(profileId)).toEqual({ createWorkspace: false, manageTasks: false, manageWorkspace: false, manageLifecycle: false })
  })
  it.each([{}, { ...metadata(), actions: null }, { ...metadata(), actions: { POST: 'not metadata' } }])('rejects malformed metadata instead of enabling controls', async (value) => {
    vi.mocked(apiClient.request).mockResolvedValue(value)
    await expect(workApi.capabilities(profileId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('does not hide server or network failure as an authoritative denied permission', async () => {
    const failure = new ApiError(503, 'server', 'Unavailable')
    vi.mocked(apiClient.request).mockRejectedValue(failure)
    await expect(workApi.capabilities(profileId)).rejects.toBe(failure)
  })
})

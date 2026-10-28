/** Existing Django contracts; these UI hints never replace service authorization. */
import { ApiError, apiClient, invalidResponse } from './client'
import type { LifecycleStatus, Page, Workspace } from './types'

export const taskStatuses = ['PENDING', 'ASSIGNED', 'WORKING', 'REVIEW', 'COMPLETED', 'CANCELLED'] as const
export const taskPriorities = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'] as const
export const taskOrderings = ['created_at', '-created_at', 'deadline', '-deadline', 'priority', '-priority'] as const
export type TaskStatus = typeof taskStatuses[number]
export type TaskPriority = typeof taskPriorities[number]
export type TaskOrdering = typeof taskOrderings[number]

export interface TaskAssignment {
  id: string
  profile_membership_id: string | null
  assigned_at: string
}
export interface Task {
  id: string
  workspace_id: string
  parent_id: string | null
  title: string
  description: string | null
  /** CANCELLED is an existing legacy server value, not a new UI transition. */
  status: TaskStatus
  priority: TaskPriority
  deadline: string | null
  active_assignment: TaskAssignment | null
  /** Current-user hint only; the existing start service revalidates every POST. */
  can_start: boolean
  /** Current-user submission hint; the submission service revalidates every POST. */
  can_submit: boolean
  created_at: string
  updated_at: string
}
export interface WorkspaceMember {
  id: string
  profile_membership_id: string
  role: 'ADMIN' | 'MEMBER' | 'VIEWER'
  is_active: boolean
  display_label: string
  is_assignable: boolean
  joined_at: string
  updated_at: string
}
export interface TaskFilters {
  readonly status?: TaskStatus
  readonly priority?: TaskPriority
  readonly root_only?: boolean
  readonly parent_id?: string
  readonly deadline_before?: string
  readonly deadline_after?: string
  readonly ordering?: TaskOrdering
}
export interface TaskCreateInput {
  readonly title: string
  readonly description?: string | null
  readonly priority?: TaskPriority
  readonly deadline?: string | null
  readonly parent_id?: string | null
}
export type TaskUpdateInput = Partial<TaskCreateInput>
export interface WorkspaceCreateInput {
  readonly name: string
  readonly description?: string | null
  readonly period: string
}
export type WorkspaceUpdateInput = Partial<Pick<WorkspaceCreateInput, 'name' | 'description'>>
export interface WorkCapabilities {
  createWorkspace: boolean
  manageWorkspace: boolean
  manageTasks: boolean
  manageLifecycle: boolean
}

const record = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown): value is string => typeof value === 'string'
const uuid = (value: unknown): value is string => text(value) && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
const nullableText = (value: unknown): value is string | null => value === null || text(value)
const dateTime = (value: unknown): value is string => text(value) && !Number.isNaN(Date.parse(value))
const nullableUuid = (value: unknown): value is string | null => value === null || uuid(value)
const memberRole = (value: unknown): value is WorkspaceMember['role'] => value === 'ADMIN' || value === 'MEMBER' || value === 'VIEWER'
const lifecycle = (value: unknown): value is LifecycleStatus => value === 'ACTIVE' || value === 'ARCHIVED'
const sameId = (left: string, right: string) => left.toLowerCase() === right.toLowerCase()
const contains = <T extends string>(values: readonly T[], value: unknown): value is T => text(value) && values.some((item) => item === value)

function entityId(value: string): string {
  if (!uuid(value)) throw new ApiError(404, 'not-found', 'Không tìm thấy nội dung hoặc bạn không có quyền truy cập.')
  return value.toLowerCase()
}
function pageNumber(page: number): number {
  if (!Number.isSafeInteger(page) || page < 1) throw new TypeError('Page must be a positive integer.')
  return page
}
function isTask(value: unknown): value is Task {
  return record(value) && uuid(value.id) && uuid(value.workspace_id) && nullableUuid(value.parent_id) &&
    text(value.title) && nullableText(value.description) && contains(taskStatuses, value.status) &&
    contains(taskPriorities, value.priority) && typeof value.can_start === 'boolean' && typeof value.can_submit === 'boolean' && (value.deadline === null || dateTime(value.deadline)) &&
    dateTime(value.created_at) && dateTime(value.updated_at) && (value.active_assignment === null ||
      (record(value.active_assignment) && uuid(value.active_assignment.id) && nullableUuid(value.active_assignment.profile_membership_id) && dateTime(value.active_assignment.assigned_at)))
}
function isMember(value: unknown): value is WorkspaceMember {
  return record(value) && uuid(value.id) && uuid(value.profile_membership_id) && memberRole(value.role) &&
    typeof value.is_active === 'boolean' && text(value.display_label) && value.display_label.trim().length > 0 &&
    typeof value.is_assignable === 'boolean' && dateTime(value.joined_at) && dateTime(value.updated_at)
}
function isWorkspace(value: unknown): value is Workspace {
  return record(value) && uuid(value.id) && uuid(value.profile_id) && text(value.name) &&
    nullableText(value.description) && lifecycle(value.status) && dateTime(value.created_at) && dateTime(value.updated_at) &&
    (value.period === null || (text(value.period) && /^\d{4}-(0[1-9]|1[0-2])-01$/.test(value.period)))
}
function asPage<T>(payload: unknown, guard: (value: unknown) => value is T): Page<T> {
  if (!record(payload) || typeof payload.count !== 'number' || !Number.isSafeInteger(payload.count) || payload.count < 0 ||
      !nullableText(payload.next) || !nullableText(payload.previous) || !Array.isArray(payload.results) || !payload.results.every(guard)) throw invalidResponse()
  return { count: payload.count, next: payload.next, previous: payload.previous, results: payload.results }
}
function taskResult(payload: unknown, workspaceId: string, taskId?: string): Task {
  if (!isTask(payload) || !sameId(payload.workspace_id, workspaceId) || (taskId !== undefined && !sameId(payload.id, taskId))) throw invalidResponse()
  return payload
}
function workspaceResult(payload: unknown, profileId: string, workspaceId?: string): Workspace {
  if (!isWorkspace(payload) || !sameId(payload.profile_id, profileId) || (workspaceId !== undefined && !sameId(payload.id, workspaceId))) throw invalidResponse()
  return payload
}
function workspacePath(profileId: string, workspaceId?: string): string {
  return `v1/profiles/${entityId(profileId)}/workspaces/${workspaceId ? `${entityId(workspaceId)}/` : ''}`
}
function taskPath(profileId: string, workspaceId: string, taskId?: string): string {
  return `${workspacePath(profileId, workspaceId)}tasks/${taskId ? `${entityId(taskId)}/` : ''}`
}

export function taskQuery(filters: TaskFilters = {}, page = 1): string {
  if (filters.root_only && filters.parent_id) throw new TypeError('Use parent_id or root_only, not both.')
  if (filters.status !== undefined && !contains(taskStatuses, filters.status)) throw new TypeError('Invalid Task status filter.')
  if (filters.priority !== undefined && !contains(taskPriorities, filters.priority)) throw new TypeError('Invalid Task priority filter.')
  if (filters.ordering !== undefined && !contains(taskOrderings, filters.ordering)) throw new TypeError('Invalid Task ordering.')
  for (const name of ['deadline_after', 'deadline_before'] as const) {
    if (filters[name] !== undefined && !dateTime(filters[name])) throw new TypeError('Invalid deadline bound.')
  }
  if (filters.deadline_after && filters.deadline_before && Date.parse(filters.deadline_after) > Date.parse(filters.deadline_before)) throw new TypeError('Deadline lower bound exceeds upper bound.')
  const query = new URLSearchParams({ page: String(pageNumber(page)) })
  for (const name of ['status', 'priority', 'ordering', 'deadline_after', 'deadline_before'] as const) {
    const value = filters[name]
    if (value !== undefined) query.set(name, value)
  }
  if (filters.root_only !== undefined) query.set('root_only', String(filters.root_only))
  if (filters.parent_id) query.set('parent_id', entityId(filters.parent_id))
  return query.toString()
}

/** Only metadata's verified POST action is a hint; never infer authority from Allow. */
async function postAvailable(path: string, signal?: AbortSignal): Promise<boolean> {
  let payload: unknown
  try {
    // Expected probe denial must not trigger global auth revalidation/refetch loops.
    payload = await apiClient.request<unknown>(path, { method: 'OPTIONS', signal })
  } catch (error) {
    if (error instanceof ApiError && [401, 403, 404].includes(error.status)) return false
    throw error
  }
  if (!record(payload) || !text(payload.name) || !Array.isArray(payload.renders) || !payload.renders.every(text) ||
      !Array.isArray(payload.parses) || !payload.parses.every(text)) throw invalidResponse()
  if (payload.actions === undefined) return false
  if (!record(payload.actions)) throw invalidResponse()
  if (!Object.hasOwn(payload.actions, 'POST')) return false
  if (!record(payload.actions.POST)) throw invalidResponse()
  return true
}

const profileKey = (profileId: string) => ['work', profileId.toLowerCase()] as const
const scopeKey = (profileId: string, workspaceId: string) => [...profileKey(profileId), 'workspaces', workspaceId.toLowerCase()] as const
export const workKeys = {
  profile: profileKey,
  scope: scopeKey,
  tasks: (profileId: string, workspaceId: string, filters: TaskFilters = {}, page = 1) => [...scopeKey(profileId, workspaceId), 'tasks', filters, page] as const,
  task: (profileId: string, workspaceId: string, taskId: string) => [...scopeKey(profileId, workspaceId), 'task', taskId.toLowerCase()] as const,
  subtasks: (profileId: string, workspaceId: string, taskId: string, filters: TaskFilters = {}, page = 1) => [...scopeKey(profileId, workspaceId), 'subtasks', taskId.toLowerCase(), filters, page] as const,
  members: (profileId: string, workspaceId: string, page = 1) => [...scopeKey(profileId, workspaceId), 'members', page] as const,
  capabilities: (profileId: string, workspaceId?: string) => workspaceId ? [...scopeKey(profileId, workspaceId), 'capabilities'] as const : [...profileKey(profileId), 'capabilities'] as const,
}

export const workApi = {
  async tasks(profileId: string, workspaceId: string, filters: TaskFilters = {}, page = 1, signal?: AbortSignal): Promise<Page<Task>> {
    const data = asPage(await apiClient.request<unknown>(`${taskPath(profileId, workspaceId)}?${taskQuery(filters, page)}`, { signal, protected: true }), isTask)
    if (data.results.some((task) => !sameId(task.workspace_id, workspaceId))) throw invalidResponse()
    return data
  },
  async task(profileId: string, workspaceId: string, taskId: string, signal?: AbortSignal): Promise<Task> {
    return taskResult(await apiClient.request<unknown>(taskPath(profileId, workspaceId, taskId), { signal, protected: true }), workspaceId, taskId)
  },
  async subtasks(profileId: string, workspaceId: string, taskId: string, filters: TaskFilters = {}, page = 1, signal?: AbortSignal): Promise<Page<Task>> {
    const data = asPage(await apiClient.request<unknown>(`${taskPath(profileId, workspaceId, taskId)}subtasks/?${taskQuery(filters, page)}`, { signal, protected: true }), isTask)
    if (data.results.some((task) => !sameId(task.workspace_id, workspaceId) || task.parent_id === null || !sameId(task.parent_id, taskId))) throw invalidResponse()
    return data
  },
  async members(profileId: string, workspaceId: string, page = 1, signal?: AbortSignal): Promise<Page<WorkspaceMember>> {
    return asPage(await apiClient.request<unknown>(`${workspacePath(profileId, workspaceId)}members/?page=${pageNumber(page)}`, { signal, protected: true }), isMember)
  },
  async createTask(profileId: string, workspaceId: string, input: TaskCreateInput, signal?: AbortSignal): Promise<Task> {
    return taskResult(await apiClient.request<unknown>(taskPath(profileId, workspaceId), { method: 'POST', body: input, signal, protected: true }), workspaceId)
  },
  async updateTask(profileId: string, workspaceId: string, taskId: string, input: TaskUpdateInput, signal?: AbortSignal): Promise<Task> {
    return taskResult(await apiClient.request<unknown>(taskPath(profileId, workspaceId, taskId), { method: 'PATCH', body: input, signal, protected: true }), workspaceId, taskId)
  },
  async assignTask(profileId: string, workspaceId: string, taskId: string, input: { target_profile_membership_id: string }, signal?: AbortSignal): Promise<Task> {
    return taskResult(await apiClient.request<unknown>(`${taskPath(profileId, workspaceId, taskId)}assign/`, { method: 'POST', body: input, signal, protected: true }), workspaceId, taskId)
  },
  async startTask(profileId: string, workspaceId: string, taskId: string, signal?: AbortSignal): Promise<Task> {
    // Eligibility comes from can_start, never a guessed User/ProfileMembership match.
    return taskResult(await apiClient.request<unknown>(`${taskPath(profileId, workspaceId, taskId)}start/`, { method: 'POST', body: {}, signal, protected: true }), workspaceId, taskId)
  },
  async createWorkspace(profileId: string, input: WorkspaceCreateInput, signal?: AbortSignal): Promise<Workspace> {
    return workspaceResult(await apiClient.request<unknown>(workspacePath(profileId), { method: 'POST', body: input, signal, protected: true }), profileId)
  },
  async updateWorkspace(profileId: string, workspaceId: string, input: WorkspaceUpdateInput, signal?: AbortSignal): Promise<Workspace> {
    return workspaceResult(await apiClient.request<unknown>(workspacePath(profileId, workspaceId), { method: 'PATCH', body: input, signal, protected: true }), profileId, workspaceId)
  },
  async setWorkspaceStatus(profileId: string, workspaceId: string, action: 'archive' | 'restore', signal?: AbortSignal): Promise<Workspace> {
    if (action !== 'archive' && action !== 'restore') throw new TypeError('Unknown lifecycle action.')
    return workspaceResult(await apiClient.request<unknown>(`${workspacePath(profileId, workspaceId)}${action}/`, { method: 'POST', body: {}, signal, protected: true }), profileId, workspaceId)
  },
  async capabilities(profileId: string, workspaceId?: string, signal?: AbortSignal): Promise<WorkCapabilities> {
    const createRequest = postAvailable(workspacePath(profileId), signal)
    if (!workspaceId) return { createWorkspace: await createRequest, manageWorkspace: false, manageTasks: false, manageLifecycle: false }
    const [createWorkspace, manageTasks, manageLifecycle] = await Promise.all([
      createRequest,
      postAvailable(taskPath(profileId, workspaceId), signal),
      postAvailable(`${workspacePath(profileId, workspaceId)}archive/`, signal),
    ])
    // These two existing server capability functions have identical role/state rules.
    return { createWorkspace, manageTasks, manageWorkspace: manageTasks, manageLifecycle }
  },
}

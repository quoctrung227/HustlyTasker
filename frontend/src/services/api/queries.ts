import { apiClient, invalidResponse } from './client'
import type { LoginInput, Page, Profile, User, UserEnvelope, Workspace } from './types'

const record = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown): value is string => typeof value === 'string'
const nullableText = (value: unknown): value is string | null => value === null || text(value)
const uuid = (value: unknown): value is string =>
  text(value) && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
const dateTime = (value: unknown): value is string => text(value) && !Number.isNaN(Date.parse(value))
const status = (value: unknown): boolean => value === 'ACTIVE' || value === 'ARCHIVED'

function isUser(value: unknown): value is User {
  return record(value) && uuid(value.id) && text(value.email) && text(value.username) &&
    text(value.first_name) && text(value.last_name) && dateTime(value.created_at) && typeof value.email_verified === 'boolean'
}

function isProfile(value: unknown): value is Profile {
  return record(value) && uuid(value.id) && text(value.name) && status(value.status) &&
    dateTime(value.created_at) && dateTime(value.updated_at)
}

function isWorkspace(value: unknown): value is Workspace {
  return record(value) && uuid(value.id) && uuid(value.profile_id) && text(value.name) &&
    nullableText(value.description) && (value.period === null ||
      (text(value.period) && /^[0-9]{4}-(0[1-9]|1[0-2])-01$/.test(value.period))) &&
    status(value.status) && dateTime(value.created_at) && dateTime(value.updated_at)
}

function asUser(payload: unknown): User {
  if (!record(payload) || !isUser(payload.user)) throw invalidResponse()
  return (payload as unknown as UserEnvelope).user
}

function asPage<T>(payload: unknown, guard: (item: unknown) => item is T): Page<T> {
  if (!record(payload) || typeof payload.count !== 'number' || !Number.isSafeInteger(payload.count) ||
      payload.count < 0 || !nullableText(payload.next) || !nullableText(payload.previous) ||
      !Array.isArray(payload.results) || !payload.results.every(guard)) throw invalidResponse()
  return { count: payload.count, next: payload.next, previous: payload.previous, results: payload.results }
}

function pageNumber(page: number): number {
  if (!Number.isSafeInteger(page) || page < 1) throw new TypeError('Page must be a positive integer.')
  return page
}

const id = (value: string): string => encodeURIComponent(value)
const sameId = (left: string, right: string): boolean => left.toLowerCase() === right.toLowerCase()

export const queryKeys = {
  currentUser: ['auth', 'me'] as const,
  profiles: (page = 1) => ['profiles', page] as const,
  profile: (profileId: string) => ['profiles', profileId] as const,
  workspaces: (profileId: string, page = 1) => ['profiles', profileId, 'workspaces', page] as const,
  workspace: (profileId: string, workspaceId: string) => ['profiles', profileId, 'workspaces', workspaceId] as const,
}

export const authApi = {
  async me(signal?: AbortSignal): Promise<User> {
    return asUser(await apiClient.request<unknown>('auth/me/', { signal }))
  },
  async login(input: LoginInput, signal?: AbortSignal): Promise<User> {
    const payload = await apiClient.request<unknown>('auth/login/', { method: 'POST', body: input, signal })
    // Django login rotates the CSRF secret. Never reuse the pre-login token.
    apiClient.clearCsrf()
    return asUser(payload)
  },
  async logout(signal?: AbortSignal): Promise<void> {
    try {
      await apiClient.request<void>('auth/logout/', { method: 'POST', signal })
    } finally {
      apiClient.clearCsrf()
    }
  },
}

export const tenantApi = {
  async profiles(page = 1, signal?: AbortSignal): Promise<Page<Profile>> {
    return asPage(await apiClient.request<unknown>(`v1/profiles/?page=${pageNumber(page)}`, { signal, protected: true }), isProfile)
  },
  async profile(profileId: string, signal?: AbortSignal): Promise<Profile> {
    const payload = await apiClient.request<unknown>(`v1/profiles/${id(profileId)}/`, { signal, protected: true })
    if (!isProfile(payload) || !sameId(payload.id, profileId)) throw invalidResponse()
    return payload
  },
  async workspaces(profileId: string, page = 1, signal?: AbortSignal): Promise<Page<Workspace>> {
    const payload = asPage(await apiClient.request<unknown>(
      `v1/profiles/${id(profileId)}/workspaces/?page=${pageNumber(page)}`, { signal, protected: true }), isWorkspace)
    if (payload.results.some((workspace) => !sameId(workspace.profile_id, profileId))) throw invalidResponse()
    return payload
  },
  async workspace(profileId: string, workspaceId: string, signal?: AbortSignal): Promise<Workspace> {
    const payload = await apiClient.request<unknown>(
      `v1/profiles/${id(profileId)}/workspaces/${id(workspaceId)}/`, { signal, protected: true })
    if (!isWorkspace(payload) || !sameId(payload.id, workspaceId) || !sameId(payload.profile_id, profileId)) throw invalidResponse()
    return payload
  },
}

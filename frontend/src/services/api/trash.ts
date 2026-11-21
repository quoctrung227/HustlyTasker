import { apiClient, invalidResponse } from './client'
import type { Page } from './types'

export const trashObjectTypes = ['TASK', 'WORKSPACE', 'PROFILE'] as const
export type TrashObjectType = typeof trashObjectTypes[number]
export interface TrashItem {
  id: string
  object_type: TrashObjectType
  title: string
  profile_id: string
  workspace_id: string | null
  parent_id: string | null
  deleted_by: { display_name: string | null }
  deleted_at: string
  purge_after: string
  days_remaining: number
  parent_deleted: boolean
  affected_counts: Record<string, number>
  can_restore: boolean
  can_purge: boolean
  restore_blocker: string | null
  purge_blockers: { code: string; message: string }[]
}
export interface TrashFilters {
  object_type?: TrashObjectType
  search?: string
  profile_id?: string
}
const record = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown): value is string => typeof value === 'string'
const uuid = (value: unknown): value is string => text(value) && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
const nullableId = (value: unknown): value is string | null => value === null || uuid(value)
const nullableText = (value: unknown): value is string | null => value === null || text(value)
const instant = (value: unknown): value is string => text(value) && /^\d{4}-\d\d-\d\dT/.test(value) && Number.isFinite(Date.parse(value))
const count = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
const validType = (value: unknown): value is TrashObjectType => trashObjectTypes.some((type) => type === value)
const sameId = (left: string, right: string) => left.toLowerCase() === right.toLowerCase()

export function parseTrashItem(value: unknown): TrashItem {
  if (!record(value) || !uuid(value.id) || !validType(value.object_type) || !text(value.title) || !uuid(value.profile_id) ||
      !nullableId(value.workspace_id) || !nullableId(value.parent_id) || !record(value.deleted_by) || !nullableText(value.deleted_by.display_name) ||
      !instant(value.deleted_at) || !instant(value.purge_after) || Date.parse(value.purge_after) < Date.parse(value.deleted_at) ||
      !count(value.days_remaining) || typeof value.parent_deleted !== 'boolean' || !record(value.affected_counts) ||
      !Object.values(value.affected_counts).every(count) || typeof value.can_restore !== 'boolean' || typeof value.can_purge !== 'boolean' ||
      !nullableText(value.restore_blocker) || !Array.isArray(value.purge_blockers) || !value.purge_blockers.every((blocker) =>
        record(blocker) && text(blocker.code) && text(blocker.message))) throw invalidResponse()
  if ((value.object_type === 'PROFILE' && !sameId(value.id, value.profile_id)) ||
      (value.object_type === 'WORKSPACE' && (!uuid(value.workspace_id) || !sameId(value.id, value.workspace_id))) ||
      (value.object_type === 'TASK' && !uuid(value.workspace_id))) throw invalidResponse()
  return value as unknown as TrashItem
}

function entityId(value: string): string {
  if (!uuid(value)) throw new TypeError('Invalid object reference.')
  return encodeURIComponent(value.toLowerCase())
}
function path(type: TrashObjectType, id: string, action: 'delete' | 'restore' | 'purge') {
  if (!validType(type)) throw new TypeError('Invalid trash object type.')
  return `v1/trash/${type.toLowerCase()}/${entityId(id)}/${action}/`
}
export const trashKeys = {
  user: (userId: string) => ['trash', userId.toLowerCase()] as const,
  list: (userId: string, filters: TrashFilters, page = 1) => [...trashKeys.user(userId), filters, page] as const,
}
export const trashApi = {
  async list(filters: TrashFilters = {}, page = 1, signal?: AbortSignal): Promise<Page<TrashItem>> {
    if (!Number.isSafeInteger(page) || page < 1) throw new TypeError('Invalid page.')
    if (filters.object_type !== undefined && !validType(filters.object_type)) throw new TypeError('Invalid trash object type.')
    const search = filters.search || ''
    const characters = Array.from(search)
    if (characters.length > 100 || characters.some((character) => {
      const point = character.codePointAt(0) ?? 0
      return point < 32 || (point >= 127 && point <= 159) || (point >= 0xD800 && point <= 0xDFFF) || point === 0xFFFD
    })) throw new TypeError('Invalid search.')
    const query = new URLSearchParams({ page: String(page) })
    if (filters.object_type) query.set('object_type', filters.object_type)
    if (search) query.set('search', search)
    if (filters.profile_id) query.set('profile_id', entityId(filters.profile_id))
    const payload = await apiClient.request<unknown>(`v1/trash/?${query}`, { signal, protected: true })
    if (!record(payload) || !count(payload.count) || !nullableText(payload.next) || !nullableText(payload.previous) || !Array.isArray(payload.results)) throw invalidResponse()
    const results = payload.results.map(parseTrashItem)
    if (results.some((row) => (filters.object_type && row.object_type !== filters.object_type) ||
        (filters.profile_id && !sameId(row.profile_id, filters.profile_id || '')))) throw invalidResponse()
    return { count: payload.count, next: payload.next, previous: payload.previous, results }
  },
  async delete(type: TrashObjectType, id: string, signal?: AbortSignal): Promise<TrashItem> {
    const item = parseTrashItem(await apiClient.request<unknown>(path(type, id, 'delete'), { method: 'POST', body: {}, signal, protected: true }))
    if (!sameId(item.id, id) || item.object_type !== type) throw invalidResponse()
    return item
  },
  async restore(type: TrashObjectType, id: string, signal?: AbortSignal): Promise<void> {
    await apiClient.request<void>(path(type, id, 'restore'), { method: 'POST', body: {}, signal, protected: true })
  },
  async purge(item: Pick<TrashItem, 'object_type' | 'id' | 'title'>, confirmationName: string, signal?: AbortSignal): Promise<void> {
    const body = item.object_type === 'TASK' ? { confirm: true } : { confirm: true, confirmation_name: confirmationName }
    await apiClient.request<void>(path(item.object_type, item.id, 'purge'), { method: 'POST', body, signal, protected: true })
  },
}

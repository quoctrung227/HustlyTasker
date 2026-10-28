/** Existing collaboration contracts. Read identities never grant mutation rights. */
import { ApiError, apiClient, invalidResponse } from './client'
import type { Page } from './types'

export type DeliverableStatus = 'PENDING' | 'SUBMITTED' | 'APPROVED' | 'REJECTED'
export type ReviewStatus = 'PENDING' | 'APPROVED' | 'REQUEST_CHANGE'
export type NotificationEvent = 'TASK_ASSIGNED' | 'REVIEW_SUBMITTED' | 'REVIEW_APPROVED' | 'REVIEW_CHANGES_REQUESTED' | 'TASK_COMMENTED'
export interface Review {
  id: string
  status: ReviewStatus
  comment: string | null
  reviewer_profile_membership_id: string | null
  created_at: string
  updated_at: string
}
export interface Deliverable {
  id: string
  task_id: string
  revision: number | null
  file_url: string
  status: DeliverableStatus
  uploaded_by_profile_membership_id: string | null
  review: Review | null
  /** Current-request hints; mutation services always revalidate. */
  can_approve: boolean
  can_request_changes: boolean
  created_at: string
  updated_at: string
}
export interface TaskComment {
  id: string
  task_id: string
  author_profile_membership_id: string | null
  content: string | null
  is_deleted: boolean
  can_edit: boolean
  can_delete: boolean
  edited_at: string | null
  deleted_at: string | null
  created_at: string
  updated_at: string
}
export interface AppNotification {
  id: string
  event_type: NotificationEvent
  profile_id: string
  workspace_id: string
  task_id: string
  title: string
  message: string
  /** Server metadata only. Navigation is built from validated IDs instead. */
  target_url: string
  is_read: boolean
  created_at: string
  updated_at: string
}
export interface CommentInput { readonly content: string }
export interface DeliverableSubmitInput { readonly file_url: string }
export interface DeliverableApproveInput { readonly comment?: string | null }
export interface DeliverableChangesInput { readonly comment: string }

const record = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown): value is string => typeof value === 'string'
const uuid = (value: unknown): value is string => text(value) && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
const nullableUuid = (value: unknown): value is string | null => value === null || uuid(value)
const nullableText = (value: unknown): value is string | null => value === null || text(value)
const dateTime = (value: unknown): value is string => text(value) && Number.isFinite(Date.parse(value))
const nullableDateTime = (value: unknown): value is string | null => value === null || dateTime(value)
const sameId = (left: string, right: string) => left.toLowerCase() === right.toLowerCase()
const timestamps = (value: Record<string, unknown>) => dateTime(value.created_at) && dateTime(value.updated_at)
const oneOf = <T extends string>(values: readonly T[], value: unknown): value is T => text(value) && values.some((item) => item === value)

function entityId(value: string): string {
  if (!uuid(value)) throw new ApiError(404, 'not-found', 'Không tìm thấy nội dung hoặc bạn không có quyền truy cập.')
  return value.toLowerCase()
}
function pageNumber(value: number): number {
  if (!Number.isSafeInteger(value) || value < 1) throw new TypeError('Page must be a positive integer.')
  return value
}
function taskPath(profileId: string, workspaceId: string, taskId: string): string {
  return `v1/profiles/${entityId(profileId)}/workspaces/${entityId(workspaceId)}/tasks/${entityId(taskId)}/`
}
function isReview(value: unknown): value is Review {
  return record(value) && uuid(value.id) && oneOf(['PENDING', 'APPROVED', 'REQUEST_CHANGE'], value.status) &&
    nullableText(value.comment) && nullableUuid(value.reviewer_profile_membership_id) && timestamps(value)
}
function isDeliverable(value: unknown): value is Deliverable {
  return record(value) && uuid(value.id) && uuid(value.task_id) &&
    (value.revision === null || (typeof value.revision === 'number' && Number.isSafeInteger(value.revision) && value.revision >= 1)) &&
    text(value.file_url) && oneOf(['PENDING', 'SUBMITTED', 'APPROVED', 'REJECTED'], value.status) &&
    nullableUuid(value.uploaded_by_profile_membership_id) && (value.review === null || isReview(value.review)) &&
    typeof value.can_approve === 'boolean' && typeof value.can_request_changes === 'boolean' && timestamps(value)
}
function isComment(value: unknown): value is TaskComment {
  return record(value) && uuid(value.id) && uuid(value.task_id) && nullableUuid(value.author_profile_membership_id) &&
    typeof value.is_deleted === 'boolean' && typeof value.can_edit === 'boolean' && typeof value.can_delete === 'boolean' && nullableDateTime(value.edited_at) && timestamps(value) &&
    // Fail closed if a tombstone unexpectedly contains its retained private body.
    (value.is_deleted ? value.content === null && dateTime(value.deleted_at) : text(value.content) && value.deleted_at === null)
}
function isNotification(value: unknown): value is AppNotification {
  return record(value) && uuid(value.id) && uuid(value.profile_id) && uuid(value.workspace_id) && uuid(value.task_id) &&
    oneOf(['TASK_ASSIGNED', 'REVIEW_SUBMITTED', 'REVIEW_APPROVED', 'REVIEW_CHANGES_REQUESTED', 'TASK_COMMENTED'], value.event_type) &&
    text(value.title) && text(value.message) && text(value.target_url) && typeof value.is_read === 'boolean' && timestamps(value)
}
function asPage<T>(value: unknown, guard: (item: unknown) => item is T): Page<T> {
  if (!record(value) || typeof value.count !== 'number' || !Number.isSafeInteger(value.count) || value.count < 0 ||
    !nullableText(value.next) || !nullableText(value.previous) || !Array.isArray(value.results) || !value.results.every(guard)) throw invalidResponse()
  return { count: value.count, next: value.next, previous: value.previous, results: value.results }
}
function deliverableResult(value: unknown, taskId: string, deliverableId?: string): Deliverable {
  if (!isDeliverable(value) || !sameId(value.task_id, taskId) || (deliverableId !== undefined && !sameId(value.id, deliverableId))) throw invalidResponse()
  return value
}
function commentResult(value: unknown, taskId: string, commentId?: string): TaskComment {
  if (!isComment(value) || !sameId(value.task_id, taskId) || (commentId !== undefined && !sameId(value.id, commentId))) throw invalidResponse()
  return value
}

/** A stored Deliverable is arbitrary text, never an implicitly trusted link. */
export function safeDeliverableUrl(value: string): string | null {
  const hasControl = Array.from(value).some((character) => {
    const code = character.charCodeAt(0)
    return code <= 31 || (code >= 127 && code <= 159)
  })
  if (!/^https?:\/\//i.test(value) || /[\s\\]/u.test(value) || hasControl) return null
  try {
    const url = new URL(value)
    if (!['http:', 'https:'].includes(url.protocol) || !url.hostname || url.username || url.password) return null
    return url.href
  } catch { return null }
}

export function notificationTaskPath(notification: Pick<AppNotification, 'profile_id' | 'workspace_id' | 'task_id'>): string {
  return `/profiles/${entityId(notification.profile_id)}/workspaces/${entityId(notification.workspace_id)}/tasks/${entityId(notification.task_id)}`
}

const scopeKey = (userId: string, profileId: string, workspaceId: string, taskId: string) =>
  ['collaboration', userId.toLowerCase(), profileId.toLowerCase(), workspaceId.toLowerCase(), taskId.toLowerCase()] as const
export const collaborationKeys = {
  scope: scopeKey,
  deliverables: (userId: string, profileId: string, workspaceId: string, taskId: string, page = 1) => [...scopeKey(userId, profileId, workspaceId, taskId), 'deliverables', page] as const,
  comments: (userId: string, profileId: string, workspaceId: string, taskId: string, page = 1) => [...scopeKey(userId, profileId, workspaceId, taskId), 'comments', page] as const,
  comment: (userId: string, profileId: string, workspaceId: string, taskId: string, commentId: string) => [...scopeKey(userId, profileId, workspaceId, taskId), 'comment', commentId.toLowerCase()] as const,
  commentCapabilities: (userId: string, profileId: string, workspaceId: string, taskId: string) => [...scopeKey(userId, profileId, workspaceId, taskId), 'comment-capabilities'] as const,
}
const userKey = (userId: string) => ['notifications', userId.toLowerCase()] as const
export const notificationKeys = {
  user: userKey,
  feed: (userId: string, isRead?: boolean, page = 1) => [...userKey(userId), 'feed', isRead ?? 'all', page] as const,
  unreadCount: (userId: string) => [...userKey(userId), 'unread-count'] as const,
}

export const collaborationApi = {
  async deliverables(profileId: string, workspaceId: string, taskId: string, page = 1, signal?: AbortSignal): Promise<Page<Deliverable>> {
    const value = asPage(await apiClient.request<unknown>(`${taskPath(profileId, workspaceId, taskId)}deliverables/?page=${pageNumber(page)}`, { signal, protected: true }), isDeliverable)
    if (value.results.some((item) => !sameId(item.task_id, taskId))) throw invalidResponse()
    return value
  },
  async submitDeliverable(profileId: string, workspaceId: string, taskId: string, input: DeliverableSubmitInput, signal?: AbortSignal): Promise<Deliverable> {
    return deliverableResult(await apiClient.request<unknown>(`${taskPath(profileId, workspaceId, taskId)}deliverables/`, { method: 'POST', body: input, signal, protected: true }), taskId)
  },
  async approveDeliverable(profileId: string, workspaceId: string, taskId: string, deliverableId: string, input: DeliverableApproveInput, signal?: AbortSignal): Promise<Deliverable> {
    return deliverableResult(await apiClient.request<unknown>(`${taskPath(profileId, workspaceId, taskId)}deliverables/${entityId(deliverableId)}/approve/`, { method: 'POST', body: input, signal, protected: true }), taskId, deliverableId)
  },
  async requestDeliverableChanges(profileId: string, workspaceId: string, taskId: string, deliverableId: string, input: DeliverableChangesInput, signal?: AbortSignal): Promise<Deliverable> {
    return deliverableResult(await apiClient.request<unknown>(`${taskPath(profileId, workspaceId, taskId)}deliverables/${entityId(deliverableId)}/request-changes/`, { method: 'POST', body: input, signal, protected: true }), taskId, deliverableId)
  },
  async comments(profileId: string, workspaceId: string, taskId: string, page = 1, signal?: AbortSignal): Promise<Page<TaskComment>> {
    const value = asPage(await apiClient.request<unknown>(`${taskPath(profileId, workspaceId, taskId)}comments/?page=${pageNumber(page)}`, { signal, protected: true }), isComment)
    if (value.results.some((item) => !sameId(item.task_id, taskId))) throw invalidResponse()
    return value
  },
  async comment(profileId: string, workspaceId: string, taskId: string, commentId: string, signal?: AbortSignal): Promise<TaskComment> {
    return commentResult(await apiClient.request<unknown>(`${taskPath(profileId, workspaceId, taskId)}comments/${entityId(commentId)}/`, { signal, protected: true }), taskId, commentId)
  },
  async createComment(profileId: string, workspaceId: string, taskId: string, input: CommentInput, signal?: AbortSignal): Promise<TaskComment> {
    return commentResult(await apiClient.request<unknown>(`${taskPath(profileId, workspaceId, taskId)}comments/`, { method: 'POST', body: input, signal, protected: true }), taskId)
  },
  async updateComment(profileId: string, workspaceId: string, taskId: string, commentId: string, input: CommentInput, signal?: AbortSignal): Promise<TaskComment> {
    return commentResult(await apiClient.request<unknown>(`${taskPath(profileId, workspaceId, taskId)}comments/${entityId(commentId)}/`, { method: 'PATCH', body: input, signal, protected: true }), taskId, commentId)
  },
  async deleteComment(profileId: string, workspaceId: string, taskId: string, commentId: string, signal?: AbortSignal): Promise<void> {
    await apiClient.request<void>(`${taskPath(profileId, workspaceId, taskId)}comments/${entityId(commentId)}/`, { method: 'DELETE', body: {}, signal, protected: true })
  },
  async commentCapabilities(profileId: string, workspaceId: string, taskId: string, signal?: AbortSignal): Promise<{ createComment: boolean }> {
    let value: unknown
    try { value = await apiClient.request<unknown>(`${taskPath(profileId, workspaceId, taskId)}comments/`, { method: 'OPTIONS', signal }) } catch (error) {
      if (error instanceof ApiError && [401, 403, 404].includes(error.status)) return { createComment: false }
      throw error
    }
    if (!record(value) || !text(value.name) || !Array.isArray(value.renders) || !value.renders.every(text) || !Array.isArray(value.parses) || !value.parses.every(text)) throw invalidResponse()
    if (value.actions === undefined) return { createComment: false }
    if (!record(value.actions) || (Object.hasOwn(value.actions, 'POST') && !record(value.actions.POST))) throw invalidResponse()
    return { createComment: Object.hasOwn(value.actions, 'POST') }
  },
}

export const notificationApi = {
  async feed(isRead?: boolean, page = 1, signal?: AbortSignal): Promise<Page<AppNotification>> {
    if (isRead !== undefined && typeof isRead !== 'boolean') throw new TypeError('Invalid read filter.')
    const query = new URLSearchParams({ page: String(pageNumber(page)) })
    if (isRead !== undefined) query.set('is_read', String(isRead))
    return asPage(await apiClient.request<unknown>(`v1/notifications/?${query}`, { signal, protected: true }), isNotification)
  },
  async unreadCount(signal?: AbortSignal): Promise<number> {
    const value = await apiClient.request<unknown>('v1/notifications/unread-count/', { signal, protected: true })
    if (!record(value) || typeof value.unread_count !== 'number' || !Number.isSafeInteger(value.unread_count) || value.unread_count < 0) throw invalidResponse()
    return value.unread_count
  },
  async markRead(notificationId: string, signal?: AbortSignal): Promise<AppNotification> {
    const value = await apiClient.request<unknown>(`v1/notifications/${entityId(notificationId)}/read/`, { method: 'POST', body: {}, signal, protected: true })
    if (!isNotification(value) || !sameId(value.id, notificationId) || !value.is_read) throw invalidResponse()
    return value
  },
}

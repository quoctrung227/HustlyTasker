/** Mock transport contracts; these tests do not establish live permissions. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiClient, ApiError, apiClient } from './client'
import { collaborationApi, collaborationKeys, notificationApi, notificationKeys, notificationTaskPath, safeDeliverableUrl } from './collaboration'
import type { AppNotification, Deliverable, TaskComment } from './collaboration'

const profileId = '00000000-0000-4000-8000-000000000101'
const workspaceId = '00000000-0000-4000-8000-000000000102'
const taskId = '00000000-0000-4000-8000-000000000103'
const commentId = '00000000-0000-4000-8000-000000000104'
const deliverableId = '00000000-0000-4000-8000-000000000105'
const reviewId = '00000000-0000-4000-8000-000000000106'
const userId = '00000000-0000-4000-8000-000000000107'
const notificationId = '00000000-0000-4000-8000-000000000108'
const membershipId = '00000000-0000-4000-8000-000000000109'
const otherId = '00000000-0000-4000-8000-000000000110'
const created = '2026-10-26T00:00:00Z'
const base = `v1/profiles/${profileId}/workspaces/${workspaceId}/tasks/${taskId}/`
const deliverable: Deliverable = { id: deliverableId, task_id: taskId, revision: 1, file_url: 'https://files.example.invalid/result', status: 'SUBMITTED',
  uploaded_by_profile_membership_id: membershipId, review: null, can_approve: false, can_request_changes: false, created_at: created, updated_at: created }
const comment: TaskComment = { id: commentId, task_id: taskId, author_profile_membership_id: membershipId, content: 'Nội dung được phép đọc', is_deleted: false,
  can_edit: false, can_delete: false, edited_at: null, deleted_at: null, created_at: created, updated_at: created }
const notification: AppNotification = { id: notificationId, event_type: 'TASK_ASSIGNED', profile_id: profileId, workspace_id: workspaceId, task_id: taskId,
  title: 'Task assigned', message: 'An accessible work item changed.', target_url: '/api/v1/generated-server-target/', is_read: false, created_at: created, updated_at: created }
const page = <T,>(results: T[]) => ({ count: results.length, next: null, previous: null, results })
const metadata = (actions?: unknown) => ({ name: 'Existing comment view', renders: ['application/json'], parses: ['application/json'], ...(actions === undefined ? {} : { actions }) })
beforeEach(() => { vi.spyOn(apiClient, 'request') })

describe('Deliverable and nested Review read contracts', () => {
  it.each([undefined, null, 'true', 1])('rejects non-boolean or missing review capabilities (%s)', async (value) => {
    vi.mocked(apiClient.request).mockResolvedValue(page([{ ...deliverable, can_approve: value }]))
    await expect(collaborationApi.deliverables(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
    vi.mocked(apiClient.request).mockResolvedValue(page([{ ...deliverable, can_request_changes: value }]))
    await expect(collaborationApi.deliverables(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('reads one bounded page at the exact existing nested route', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...page([deliverable]), next: 'https://untrusted.invalid/pagination' })
    expect((await collaborationApi.deliverables(profileId, workspaceId, taskId, 2)).results).toEqual([deliverable])
    expect(apiClient.request).toHaveBeenCalledWith(`${base}deliverables/?page=2`, { signal: undefined, protected: true })
    expect(apiClient.request).toHaveBeenCalledOnce()
  })
  it('accepts nullable legacy revisions/attribution and the actual REQUEST_CHANGE Review state', async () => {
    const value = { ...deliverable, revision: null, uploaded_by_profile_membership_id: null,
      review: { id: reviewId, status: 'REQUEST_CHANGE', comment: 'Cần chỉnh sửa', reviewer_profile_membership_id: null, created_at: created, updated_at: created } }
    vi.mocked(apiClient.request).mockResolvedValue(page([value]))
    expect((await collaborationApi.deliverables(profileId, workspaceId, taskId)).results[0]).toEqual(value)
  })
  it.each([{ ...deliverable, task_id: otherId }, { ...deliverable, revision: 0 }, { ...deliverable, status: 'COMPLETED' }, { ...deliverable, review: { id: reviewId, status: 'APPROVED' } }])('rejects wrong-parent or malformed deliverables', async (value) => {
    vi.mocked(apiClient.request).mockResolvedValue(page([value]))
    await expect(collaborationApi.deliverables(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('submits the existing URL-string contract without an upload or status mutation', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(deliverable)
    await collaborationApi.submitDeliverable(profileId, workspaceId, taskId, { file_url: deliverable.file_url })
    expect(apiClient.request).toHaveBeenCalledWith(`${base}deliverables/`, { method: 'POST', body: { file_url: deliverable.file_url }, signal: undefined, protected: true })
  })
  it('uses the existing internal-review actions with strict comment bodies', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(deliverable)
    await collaborationApi.approveDeliverable(profileId, workspaceId, taskId, deliverableId, {})
    expect(apiClient.request).toHaveBeenLastCalledWith(`${base}deliverables/${deliverableId}/approve/`, { method: 'POST', body: {}, signal: undefined, protected: true })
    await collaborationApi.requestDeliverableChanges(profileId, workspaceId, taskId, deliverableId, { comment: 'Cần chỉnh sửa' })
    expect(apiClient.request).toHaveBeenLastCalledWith(`${base}deliverables/${deliverableId}/request-changes/`, { method: 'POST', body: { comment: 'Cần chỉnh sửa' }, signal: undefined, protected: true })
  })
  it('rejects a successful-looking review response for a different deliverable', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...deliverable, id: otherId })
    await expect(collaborationApi.approveDeliverable(profileId, workspaceId, taskId, deliverableId, {})).rejects.toMatchObject({ kind: 'invalid-response' })
  })
})

describe('Comment scope, tombstones and exact mutation contracts', () => {
  it('reads a page and a nested detail without requiring global User identity', async () => {
    vi.mocked(apiClient.request).mockResolvedValueOnce(page([comment])).mockResolvedValueOnce(comment)
    expect(await collaborationApi.comments(profileId, workspaceId, taskId)).toEqual(page([comment]))
    expect(await collaborationApi.comment(profileId, workspaceId, taskId, commentId)).toEqual(comment)
    expect(apiClient.request).toHaveBeenLastCalledWith(`${base}comments/${commentId}/`, { signal: undefined, protected: true })
  })
  it('preserves a redacted tombstone and nullable former-author attribution', async () => {
    const tombstone = { ...comment, author_profile_membership_id: null, content: null, is_deleted: true, deleted_at: created }
    vi.mocked(apiClient.request).mockResolvedValue(page([tombstone]))
    expect((await collaborationApi.comments(profileId, workspaceId, taskId)).results[0]).toEqual(tombstone)
  })
  it.each([{ ...comment, content: null }, { ...comment, is_deleted: true, deleted_at: created }, { ...comment, is_deleted: true, content: null }, { ...comment, task_id: otherId }])('rejects wrong-parent or leaking/malformed tombstones before rendering', async (value) => {
    vi.mocked(apiClient.request).mockResolvedValue(page([value]))
    await expect(collaborationApi.comments(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('creates and edits only the content contract and deletes with an empty body', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(comment)
    await collaborationApi.createComment(profileId, workspaceId, taskId, { content: 'Bình luận mới' })
    expect(apiClient.request).toHaveBeenLastCalledWith(`${base}comments/`, { method: 'POST', body: { content: 'Bình luận mới' }, signal: undefined, protected: true })
    await collaborationApi.updateComment(profileId, workspaceId, taskId, commentId, { content: 'Đã sửa' })
    expect(apiClient.request).toHaveBeenLastCalledWith(`${base}comments/${commentId}/`, { method: 'PATCH', body: { content: 'Đã sửa' }, signal: undefined, protected: true })
    vi.mocked(apiClient.request).mockResolvedValue(undefined)
    await expect(collaborationApi.deleteComment(profileId, workspaceId, taskId, commentId)).resolves.toBeUndefined()
    expect(apiClient.request).toHaveBeenLastCalledWith(`${base}comments/${commentId}/`, { method: 'DELETE', body: {}, signal: undefined, protected: true })
  })
  it.each([400, 403, 404, 409])('retains HTTP %s without converting a rejected mutation to success', async (status) => {
    const error = new ApiError(status, 'validation', 'Thông tin chưa hợp lệ.')
    vi.mocked(apiClient.request).mockRejectedValue(error)
    await expect(collaborationApi.updateComment(profileId, workspaceId, taskId, commentId, { content: 'Bản nháp' })).rejects.toBe(error)
  })
  it('rejects malformed resource IDs and invalid page numbers before transport', async () => {
    await expect(collaborationApi.comment(profileId, workspaceId, taskId, '../foreign')).rejects.toMatchObject({ status: 404 })
    await expect(collaborationApi.comments(profileId, workspaceId, taskId, 0)).rejects.toThrow(TypeError)
    expect(apiClient.request).not.toHaveBeenCalled()
  })
})

describe('Comment collection metadata is a create hint, not author authority', () => {
  it.each([undefined, null, 'true', 1])('rejects non-boolean or missing comment capabilities (%s)', async (value) => {
    vi.mocked(apiClient.request).mockResolvedValue(page([{ ...comment, can_edit: value }]))
    await expect(collaborationApi.comments(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
    vi.mocked(apiClient.request).mockResolvedValue(page([{ ...comment, can_delete: value }]))
    await expect(collaborationApi.comments(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('recognizes only a verified POST action and does not require CSRF or protected denial callback', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(metadata({ POST: {} }))
    expect(await collaborationApi.commentCapabilities(profileId, workspaceId, taskId)).toEqual({ createComment: true })
    expect(apiClient.request).toHaveBeenCalledWith(`${base}comments/`, { method: 'OPTIONS', signal: undefined })
  })
  it('ignores allowed-method hints and does not invent PATCH/DELETE identity capabilities', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...metadata(), allowed_methods: ['POST', 'PATCH', 'DELETE'] })
    expect(await collaborationApi.commentCapabilities(profileId, workspaceId, taskId)).toEqual({ createComment: false })
  })
  it.each([401, 403, 404])('fails closed for expected permission denial %s', async (status) => {
    vi.mocked(apiClient.request).mockRejectedValue(new ApiError(status, 'forbidden', 'Không có quyền.'))
    expect(await collaborationApi.commentCapabilities(profileId, workspaceId, taskId)).toEqual({ createComment: false })
  })
  it.each([{}, metadata(null), metadata({ POST: true })])('rejects invalid metadata instead of enabling actions', async (value) => {
    vi.mocked(apiClient.request).mockResolvedValue(value)
    await expect(collaborationApi.commentCapabilities(profileId, workspaceId, taskId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('preserves network failure for explicit retry rather than treating it as authorization', async () => {
    const failure = new ApiError(503, 'server', 'Tạm thời không thể kết nối.')
    vi.mocked(apiClient.request).mockRejectedValue(failure)
    await expect(collaborationApi.commentCapabilities(profileId, workspaceId, taskId)).rejects.toBe(failure)
  })
})

describe('Personal notification contracts and navigation', () => {
  it('uses only the supported read filter and a locally constructed page', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(page([notification]))
    expect(await notificationApi.feed(false, 2)).toEqual(page([notification]))
    expect(apiClient.request).toHaveBeenCalledWith('v1/notifications/?page=2&is_read=false', { signal: undefined, protected: true })
  })
  it('reads the own unread count and marks one own notification with an empty action body', async () => {
    vi.mocked(apiClient.request).mockResolvedValueOnce({ unread_count: 2 }).mockResolvedValueOnce({ ...notification, is_read: true })
    expect(await notificationApi.unreadCount()).toBe(2)
    expect((await notificationApi.markRead(notificationId)).is_read).toBe(true)
    expect(apiClient.request).toHaveBeenLastCalledWith(`v1/notifications/${notificationId}/read/`, { method: 'POST', body: {}, signal: undefined, protected: true })
  })
  it.each([-1, 1.5, '3', undefined])('rejects an invalid unread count %s', async (unread_count) => {
    vi.mocked(apiClient.request).mockResolvedValue({ unread_count })
    await expect(notificationApi.unreadCount()).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it.each([{ ...notification, event_type: 'UNKNOWN' }, { ...notification, profile_id: null }, { ...notification, is_read: 'true' }])('rejects unscoped legacy or malformed feed rows', async (value) => {
    vi.mocked(apiClient.request).mockResolvedValue(page([value]))
    await expect(notificationApi.feed()).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it.each([{ ...notification, is_read: false }, { ...notification, id: otherId, is_read: true }])('does not accept an unread or wrong-ID mark-read result', async (value) => {
    vi.mocked(apiClient.request).mockResolvedValue(value)
    await expect(notificationApi.markRead(notificationId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('builds a SPA Task link from validated IDs and never navigates server target_url', () => {
    const value = { ...notification, target_url: 'javascript:alert(1)' }
    expect(notificationTaskPath(value)).toBe(`/profiles/${profileId}/workspaces/${workspaceId}/tasks/${taskId}`)
    expect(() => notificationTaskPath({ ...value, task_id: '../foreign' })).toThrow(ApiError)
    expect(apiClient.request).not.toHaveBeenCalled()
  })
  it('separates notification cache by User and collaboration by User/Profile/Workspace/Task', () => {
    const original = collaborationKeys.comments(userId, profileId, workspaceId, taskId)
    expect(original).not.toEqual(collaborationKeys.comments(otherId, profileId, workspaceId, taskId))
    expect(original).not.toEqual(collaborationKeys.comments(userId, otherId, workspaceId, taskId))
    expect(original).not.toEqual(collaborationKeys.comments(userId, profileId, otherId, taskId))
    expect(original).not.toEqual(collaborationKeys.comments(userId, profileId, workspaceId, otherId))
    expect(notificationKeys.feed(userId, false)).not.toEqual(notificationKeys.feed(otherId, false))
    expect(notificationKeys.feed(userId)).not.toEqual(notificationKeys.feed(userId, false))
    expect(notificationKeys.unreadCount(userId)).toEqual([...notificationKeys.user(userId), 'unread-count'])
  })
})

describe('Untrusted external Deliverable links', () => {
  it.each(['https://files.example.invalid/result#page=2', 'http://files.example.invalid/result'])('permits an explicit HTTP(S) URL %s', (value) => {
    expect(safeDeliverableUrl(value)).toBe(value)
  })
  it.each(['javascript:alert(1)', 'data:text/html,<h1>test</h1>', '//files.example.invalid/result', '/relative', 'ftp://files.example.invalid/result',
    'https://name:password@files.example.invalid/result', 'https://files.example.invalid/with space', 'https://files.example.invalid/\nnext', 'https://files.example.invalid/\u0000next', 'https://files.example.invalid/\u0085next', 'https://files.example.invalid\\@else.invalid', ' https://files.example.invalid/result', 'not a link'])('keeps unsafe/ambiguous legacy values as plain text %s', (value) => {
    expect(safeDeliverableUrl(value)).toBeNull()
    expect(apiClient.request).not.toHaveBeenCalled()
  })
})

describe('Safe localized collaboration field errors', () => {
  it('maps allowlisted fields without reflecting backend values or unknown keys', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: 'a'.repeat(64) }), { headers: { 'content-type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ content: ['private comment body'], file_url: ['private location'], comment: ['private feedback'], secret: ['private'] }), { status: 400, headers: { 'content-type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    try {
      const error = await new ApiClient().request(`${base}comments/`, { method: 'POST', body: { content: '' } }).catch((value: unknown) => value)
      expect(error).toMatchObject({ status: 400, fieldErrors: { content: expect.any(String), file_url: expect.any(String), comment: expect.any(String) } })
      expect(JSON.stringify(error)).not.toContain('private')
      expect(JSON.stringify(error)).not.toContain('secret')
    } finally { vi.unstubAllGlobals() }
  })
})

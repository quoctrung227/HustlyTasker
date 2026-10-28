import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/api/client'
import { collaborationApi, collaborationKeys } from '../../services/api/collaboration'
import type { Deliverable, TaskComment } from '../../services/api/collaboration'
import type { Page } from '../../services/api/types'
import type { Task } from '../../services/api/work-management'
import { TaskCollaboration } from './TaskCollaboration'

const profileId = '00000000-0000-4000-8000-000000000301'
const workspaceId = '00000000-0000-4000-8000-000000000302'
const taskId = '00000000-0000-4000-8000-000000000303'
const userId = '00000000-0000-4000-8000-000000000304'
const commentId = '00000000-0000-4000-8000-000000000305'
const time = '2026-10-26T09:00:00Z'
const task: Task = { id: taskId, workspace_id: workspaceId, parent_id: null, title: 'Công việc có phản hồi', description: null, priority: 'MEDIUM', status: 'WORKING', deadline: null, active_assignment: null, can_start: false, can_submit: false, created_at: time, updated_at: time }
const comment: TaskComment = { id: commentId, task_id: taskId, content: 'Nội dung bình luận hiện có', is_deleted: false, can_edit: false, can_delete: false, author_profile_membership_id: '00000000-0000-4000-8000-000000000306', created_at: time, updated_at: time, edited_at: null, deleted_at: null }
const deliverable: Deliverable = { id: '00000000-0000-4000-8000-000000000307', task_id: taskId, revision: 1, file_url: 'https://example.test/deliverable', status: 'REJECTED', can_approve: false, can_request_changes: false, uploaded_by_profile_membership_id: comment.author_profile_membership_id, review: { id: '00000000-0000-4000-8000-000000000308', status: 'REQUEST_CHANGE', comment: 'Hãy sửa lại phần mở đầu.', reviewer_profile_membership_id: '00000000-0000-4000-8000-000000000309', created_at: time, updated_at: time }, created_at: time, updated_at: time }
const page = <T,>(results: T[], count = results.length): Page<T> => ({ results, count, next: null, previous: null })
let rows: TaskComment[]
const showModalDescriptor = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const closeDescriptor = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')

beforeAll(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.open = true } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) { this.open = false; this.dispatchEvent(new Event('close')) } })
})
afterAll(() => {
  if (showModalDescriptor) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', showModalDescriptor)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
  if (closeDescriptor) Object.defineProperty(HTMLDialogElement.prototype, 'close', closeDescriptor)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
})
beforeEach(() => {
  rows = [comment]
  vi.spyOn(collaborationApi, 'deliverables').mockResolvedValue(page([deliverable]))
  vi.spyOn(collaborationApi, 'comments').mockImplementation(async () => page([...rows]))
  vi.spyOn(collaborationApi, 'commentCapabilities').mockResolvedValue({ createComment: true })
  vi.spyOn(collaborationApi, 'createComment').mockImplementation(async (_p, _w, _t, input) => {
    const saved = { ...comment, id: '00000000-0000-4000-8000-000000000310', content: input.content, can_edit: true, can_delete: true }
    rows = [...rows, saved]; return saved
  })
  vi.spyOn(collaborationApi, 'updateComment').mockImplementation(async (_p, _w, _t, id, input) => {
    const saved = { ...comment, id, content: input.content, edited_at: time, can_edit: true, can_delete: true }
    rows = rows.map((item) => item.id === id ? saved : item); return saved
  })
  vi.spyOn(collaborationApi, 'deleteComment').mockImplementation(async (_p, _w, _t, id) => {
    rows = rows.map((item) => item.id === id ? { ...item, content: null, is_deleted: true, deleted_at: time } : item)
  })
})
function deferred<T>() {
  let resolve: (value: T) => void = () => { throw new Error('Missing deferred resolver') }
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}
function setup(overrides: Partial<Parameters<typeof TaskCollaboration>[0]> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity, refetchOnWindowFocus: false } } })
  const props = { profileId, workspaceId, task, currentUserId: userId, active: true, canManage: false, onChanged: vi.fn(), onDenied: vi.fn(), ...overrides }
  const tree = (next = props) => <QueryClientProvider client={client}><TaskCollaboration {...next} /></QueryClientProvider>
  return { ...render(tree()), client, props, tree }
}
const commentsSection = () => within(screen.getByRole('heading', { name: 'Thảo luận' }).closest('section') as HTMLElement)
async function createOwn() {
  const user = userEvent.setup()
  await screen.findByLabelText('Nội dung bình luận')
  fireEvent.change(screen.getByLabelText('Nội dung bình luận'), { target: { value: 'Bình luận tôi vừa gửi' } })
  await user.click(screen.getByRole('button', { name: 'Gửi bình luận' }))
  await screen.findByRole('button', { name: 'Chỉnh sửa bình luận' })
  return user
}

describe('scoped collaboration reads', () => {
  it('shows revision/review history and a safe external URL without inventing blocked actions', async () => {
    setup()
    expect(await screen.findByText('Hãy sửa lại phần mở đầu.')).toBeVisible()
    const link = screen.getByRole('link', { name: /Mở sản phẩm bàn giao/ })
    expect(link).toHaveAttribute('href', deliverable.file_url)
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link).toHaveAttribute('referrerpolicy', 'no-referrer')
    expect(screen.queryByRole('button', { name: /Nộp|Phê duyệt|Yêu cầu chỉnh sửa/ })).not.toBeInTheDocument()
  })
  it('renders untrusted URLs and markup as plain text without creating executable links', async () => {
    if (!deliverable.review) throw new Error('Expected review fixture')
    vi.mocked(collaborationApi.deliverables).mockResolvedValue(page([{ ...deliverable, file_url: 'javascript:alert(1)', review: { ...deliverable.review, comment: '<img src=x onerror=alert(1)>' } }]))
    setup()
    expect(await screen.findByText('javascript:alert(1)')).toBeVisible()
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeVisible()
    expect(screen.queryByRole('link', { name: /Mở sản phẩm/ })).not.toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
  })
  it('supports nullable legacy revision/attribution and no nested review', async () => {
    vi.mocked(collaborationApi.deliverables).mockResolvedValue(page([{ ...deliverable, revision: null, uploaded_by_profile_membership_id: null, review: null }]))
    setup()
    expect(await screen.findByText('Bản ghi cũ · chưa có phiên bản')).toBeVisible()
    expect(screen.getByText(/Thông tin thành viên không còn khả dụng/)).toBeVisible()
    expect(screen.getByText('Chưa có quyết định đánh giá cho phiên bản này.')).toBeVisible()
  })
  it('uses useful empty states without fake submissions or comments', async () => {
    rows = []
    vi.mocked(collaborationApi.deliverables).mockResolvedValue(page([]))
    setup()
    expect(await screen.findByText('Chưa có sản phẩm bàn giao')).toBeVisible()
    expect(await screen.findByText('Chưa có bình luận')).toBeVisible()
  })
  it('shows errors instead of stale cached private content after a denied refetch', async () => {
    const { client } = setup()
    await screen.findByText(comment.content ?? '')
    vi.mocked(collaborationApi.comments).mockRejectedValue(new ApiError(404, 'not-found', 'Nội dung không khả dụng.'))
    await act(async () => { await client.invalidateQueries({ queryKey: collaborationKeys.comments(userId, profileId, workspaceId, taskId).slice(0, -1) }) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Nội dung không khả dụng.')
    expect(screen.queryByText(comment.content ?? '')).not.toBeInTheDocument()
  })
  it('never starts queries for a mismatched Task/Workspace scope', () => {
    setup({ workspaceId: '00000000-0000-4000-8000-000000000399' })
    expect(collaborationApi.comments).not.toHaveBeenCalled()
    expect(collaborationApi.deliverables).not.toHaveBeenCalled()
  })
  it('requests comment pagination from the server without loading every page', async () => {
    vi.mocked(collaborationApi.comments).mockResolvedValue(page([comment], 41))
    setup()
    await screen.findByText(comment.content ?? '')
    await userEvent.setup().click(commentsSection().getByRole('button', { name: 'Trang sau' }))
    await waitFor(() => expect(collaborationApi.comments).toHaveBeenLastCalledWith(profileId, workspaceId, taskId, 2, expect.any(AbortSignal)))
    expect(collaborationApi.comments).toHaveBeenCalledTimes(2)
  })
})

describe('request-specific comment capabilities', () => {
  it('edits an existing comment from server capabilities after reload without a local creation proof', async () => {
    rows = [{ ...comment, can_edit: true, can_delete: true }]
    vi.mocked(collaborationApi.commentCapabilities).mockResolvedValue({ createComment: false })
    const first = setup()
    await screen.findByRole('button', { name: 'Chỉnh sửa bình luận' })
    first.unmount()
    setup()
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'Chỉnh sửa bình luận' }))
    const dialog = screen.getByRole('dialog', { name: 'Chỉnh sửa bình luận' })
    fireEvent.change(within(dialog).getByLabelText('Nội dung bình luận'), { target: { value: 'Sửa sau khi tải lại' } })
    await user.click(within(dialog).getByRole('button', { name: 'Lưu bình luận' }))
    await waitFor(() => expect(collaborationApi.updateComment).toHaveBeenCalledWith(profileId, workspaceId, taskId, commentId, { content: 'Sửa sau khi tải lại' }, expect.any(AbortSignal)))
    expect(collaborationApi.createComment).not.toHaveBeenCalled()
  })
  it('does not infer row permissions from a manager prop when the server says false', async () => {
    setup({ canManage: true })
    await screen.findByText(comment.content ?? '')
    expect(screen.queryByRole('button', { name: 'Chỉnh sửa bình luận' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Xóa bình luận' })).not.toBeInTheDocument()
  })
  it('keeps an ordinary commenter from editing or deleting existing author IDs', async () => {
    setup()
    await screen.findByLabelText('Nội dung bình luận')
    expect(screen.queryByRole('button', { name: 'Chỉnh sửa bình luận' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Xóa bình luận' })).not.toBeInTheDocument()
  })
  it('allows manager moderation but never manager editing of another author', async () => {
    rows = [{ ...comment, can_delete: true }]
    setup({ canManage: true })
    expect(await screen.findByRole('button', { name: 'Xóa bình luận' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Chỉnh sửa bình luận' })).not.toBeInTheDocument()
  })
  it('keeps Viewer reads while hiding mutations without a verified POST capability', async () => {
    vi.mocked(collaborationApi.commentCapabilities).mockResolvedValue({ createComment: false })
    setup()
    await screen.findByText(comment.content ?? '')
    await waitFor(() => expect(screen.queryByLabelText('Nội dung bình luận')).not.toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Xóa bình luận' })).not.toBeInTheDocument()
  })
  it('keeps archived scopes read-only even for a prior manager', async () => {
    setup({ active: false, canManage: true })
    await screen.findByText(comment.content ?? '')
    expect(collaborationApi.commentCapabilities).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Xóa bình luận' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Nội dung bình luận')).not.toBeInTheDocument()
  })
  it('creates through the current scope, then edits only the exact newly returned comment', async () => {
    setup()
    const user = await createOwn()
    expect(collaborationApi.createComment).toHaveBeenCalledWith(profileId, workspaceId, taskId, { content: 'Bình luận tôi vừa gửi' }, expect.any(AbortSignal))
    await user.click(screen.getByRole('button', { name: 'Chỉnh sửa bình luận' }))
    const dialog = screen.getByRole('dialog', { name: 'Chỉnh sửa bình luận' })
    fireEvent.change(within(dialog).getByLabelText('Nội dung bình luận'), { target: { value: '  Nội dung mới đã sửa  ' } })
    await user.click(within(dialog).getByRole('button', { name: 'Lưu bình luận' }))
    await waitFor(() => expect(collaborationApi.updateComment).toHaveBeenCalledWith(profileId, workspaceId, taskId, '00000000-0000-4000-8000-000000000310', { content: 'Nội dung mới đã sửa' }, expect.any(AbortSignal)))
    expect(await screen.findByText('Nội dung mới đã sửa')).toBeVisible()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
  it('uses freshly loaded capabilities after the authenticated User changes', async () => {
    const view = setup()
    await createOwn()
    rows = rows.map((row) => ({ ...row, can_edit: false, can_delete: false }))
    view.rerender(view.tree({ ...view.props, currentUserId: '00000000-0000-4000-8000-000000000399' }))
    await screen.findByText('Bình luận tôi vừa gửi')
    expect(screen.queryByRole('button', { name: 'Chỉnh sửa bình luận' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Xóa bình luận' })).not.toBeInTheDocument()
  })
  it('fails closed when a capability refetch errors even if previous data was allowed', async () => {
    const { client } = setup()
    await screen.findByLabelText('Nội dung bình luận')
    vi.mocked(collaborationApi.commentCapabilities).mockRejectedValue(new ApiError(403, 'forbidden', 'Không có quyền.'))
    await act(async () => { await client.invalidateQueries({ queryKey: collaborationKeys.commentCapabilities(userId, profileId, workspaceId, taskId) }) })
    await waitFor(() => expect(screen.queryByLabelText('Nội dung bình luận')).not.toBeInTheDocument())
  })
})

describe('comment validation and failure recovery', () => {
  it.each(['', 'a'.repeat(4001), 'Có\0NUL', '\uD800'])('rejects invalid content before any mutation (%#)', async (value) => {
    setup()
    const input = await screen.findByLabelText('Nội dung bình luận')
    fireEvent.change(input, { target: { value } })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Gửi bình luận' }))
    expect(collaborationApi.createComment).not.toHaveBeenCalled()
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByRole('alert').parentElement).toHaveFocus()
  })
  it('counts Unicode code points and accepts 4000 astral characters like the backend', async () => {
    setup()
    const input = await screen.findByLabelText('Nội dung bình luận')
    const content = '😀'.repeat(4000)
    fireEvent.change(input, { target: { value: content } })
    expect(screen.getByText('4.000 / 4.000 ký tự')).toBeVisible()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Gửi bình luận' }))
    expect(collaborationApi.createComment).toHaveBeenCalledWith(profileId, workspaceId, taskId, { content }, expect.any(AbortSignal))
  })
  it('keeps a draft and safe inline errors after a recoverable server validation failure', async () => {
    vi.mocked(collaborationApi.createComment).mockRejectedValue(new ApiError(400, 'validation', 'Thông tin chưa hợp lệ.', { content: 'Kiểm tra nội dung bình luận.' }))
    setup()
    const input = await screen.findByLabelText('Nội dung bình luận')
    fireEvent.change(input, { target: { value: 'Bản nháp cần giữ' } })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Gửi bình luận' }))
    expect(input).toHaveValue('Bản nháp cần giữ')
    const summary = screen.getByRole('alert')
    await userEvent.setup().click(within(summary).getByRole('link', { name: 'Kiểm tra nội dung bình luận.' }))
    expect(input).toHaveFocus()
  })
  it('blocks duplicate submissions and aborts a pending request on scope unmount', async () => {
    const pending = deferred<TaskComment>()
    vi.mocked(collaborationApi.createComment).mockReturnValue(pending.promise)
    const view = setup()
    const input = await screen.findByLabelText('Nội dung bình luận')
    fireEvent.change(input, { target: { value: 'Bình luận đang gửi' } })
    const form = input.closest('form') as HTMLFormElement
    fireEvent.submit(form); fireEvent.submit(form)
    expect(collaborationApi.createComment).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Gửi bình luận' })).toBeDisabled()
    const signal = vi.mocked(collaborationApi.createComment).mock.calls[0]?.[4] as AbortSignal
    view.unmount()
    expect(signal.aborted).toBe(true)
    await act(async () => { pending.resolve(comment) })
    expect(view.props.onChanged).not.toHaveBeenCalled()
  })
  it.each([403, 404])('refreshes a denied scope once without an automatic mutation retry (%s)', async (status) => {
    vi.mocked(collaborationApi.createComment).mockRejectedValue(new ApiError(status, status === 403 ? 'forbidden' : 'not-found', 'Không có quyền.'))
    const { props } = setup()
    const input = await screen.findByLabelText('Nội dung bình luận')
    vi.mocked(collaborationApi.commentCapabilities).mockResolvedValue({ createComment: false })
    fireEvent.change(input, { target: { value: 'Phản hồi' } })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Gửi bình luận' }))
    await waitFor(() => expect(props.onDenied).toHaveBeenCalledTimes(1))
    expect(collaborationApi.createComment).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(screen.queryByLabelText('Nội dung bình luận')).not.toBeInTheDocument())
  })
})

describe('soft deletion and cache privacy', () => {
  it('closes an author editor when a current read proves the comment was deleted elsewhere', async () => {
    const view = setup()
    const user = await createOwn()
    await user.click(screen.getByRole('button', { name: 'Chỉnh sửa bình luận' }))
    expect(screen.getByRole('dialog')).toBeVisible()
    act(() => {
      view.client.setQueryData(collaborationKeys.comments(userId, profileId, workspaceId, taskId, 1), page(rows.map((row) => ({ ...row, is_deleted: true, content: null, deleted_at: time }))))
    })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.queryByText('Bình luận tôi vừa gửi')).not.toBeInTheDocument()
  })
  it('renders tombstones without retaining a body in the DOM', async () => {
    rows = [{ ...comment, content: 'Body that must stay hidden', is_deleted: true, deleted_at: time }]
    setup({ canManage: true })
    expect(await screen.findByText('Bình luận đã được xóa.')).toBeVisible()
    expect(screen.queryByText('Body that must stay hidden')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Xóa bình luận' })).not.toBeInTheDocument()
  })
  it('requires confirmation and redacts every cached page before delayed refetch completes', async () => {
    rows = [{ ...comment, can_delete: true }]
    const view = setup({ canManage: true })
    await screen.findByRole('button', { name: 'Xóa bình luận' })
    const secondKey = collaborationKeys.comments(userId, profileId, workspaceId, taskId, 2)
    view.client.setQueryData(secondKey, page([comment]))
    const otherKey = collaborationKeys.comments('another-user', profileId, workspaceId, taskId, 1)
    view.client.setQueryData(otherKey, page([comment]))
    const refetch = deferred<Page<TaskComment>>()
    vi.mocked(collaborationApi.comments).mockReturnValue(refetch.promise)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Xóa bình luận' }))
    expect(collaborationApi.deleteComment).not.toHaveBeenCalled()
    await user.click(within(screen.getByRole('dialog', { name: 'Xóa bình luận' })).getByRole('button', { name: 'Xác nhận xóa' }))
    expect(await screen.findByText('Bình luận đã được xóa.')).toBeVisible()
    expect(screen.queryByText(comment.content ?? '')).not.toBeInTheDocument()
    expect(view.client.getQueryData<Page<TaskComment>>(secondKey)?.results[0]?.content).toBeNull()
    expect(view.client.getQueryData<Page<TaskComment>>(otherKey)?.results[0]?.content).toBe(comment.content)
    expect(collaborationApi.deleteComment).toHaveBeenCalledWith(profileId, workspaceId, taskId, commentId, expect.any(AbortSignal))
  })
  it('cancels pre-delete reads so their old body cannot reappear after confirmation', async () => {
    rows = [{ ...comment, can_delete: true }]
    const view = setup({ canManage: true })
    await screen.findByRole('button', { name: 'Xóa bình luận' })
    const oldRead = deferred<Page<TaskComment>>(), newRead = deferred<Page<TaskComment>>()
    vi.mocked(collaborationApi.comments).mockReturnValueOnce(oldRead.promise).mockReturnValue(newRead.promise)
    const key = collaborationKeys.comments(userId, profileId, workspaceId, taskId, 1)
    act(() => { void view.client.invalidateQueries({ queryKey: key }) })
    await waitFor(() => expect(collaborationApi.comments).toHaveBeenCalledTimes(2))
    const oldSignal = vi.mocked(collaborationApi.comments).mock.calls[1]?.[4] as AbortSignal
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Xóa bình luận' }))
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Xác nhận xóa' }))
    await screen.findByText('Bình luận đã được xóa.')
    expect(oldSignal.aborted).toBe(true)
    await act(async () => { oldRead.resolve(page([comment])) })
    expect(screen.queryByText(comment.content ?? '')).not.toBeInTheDocument()
  })
})

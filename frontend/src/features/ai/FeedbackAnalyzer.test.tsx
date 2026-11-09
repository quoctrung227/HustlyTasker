/** Component tests mock HTTP service boundaries; real browser proof is separate. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import { FeedbackAnalyzer } from './FeedbackAnalyzer'
import { AuthProvider, useAuth } from '../auth/AuthProvider'
import { authApi } from '../../services/api/queries'
import type { User, Page } from '../../services/api/types'
import { aiApi } from '../../services/api/ai'
import type { AiAvailability } from '../../services/api/ai'
import { ApiError, apiClient } from '../../services/api/client'
import { collaborationApi, collaborationKeys } from '../../services/api/collaboration'
import type { Deliverable, Review, TaskComment } from '../../services/api/collaboration'
import { feedbackAnalysisApi } from '../../services/api/feedback-analysis'
import type { FeedbackAnalysisInput, FeedbackAnalysisResult } from '../../services/api/feedback-analysis'
import { workApi } from '../../services/api/work-management'

const userId = '00000000-0000-4000-8000-000000000701'
const profileId = '00000000-0000-4000-8000-000000000702'
const workspaceId = '00000000-0000-4000-8000-000000000703'
const taskId = '00000000-0000-4000-8000-000000000704'
const reviewId = '00000000-0000-4000-8000-000000000705'
const commentId = '00000000-0000-4000-8000-000000000706'
const otherId = '00000000-0000-4000-8000-000000000707'
const stamp = '2026-11-02T06:00:00Z'
const user: User = { id: userId, email: 'synthetic-analyzer@example.test', username: 'synthetic-analyzer', first_name: '', last_name: '', created_at: stamp, email_verified: false }
const available: AiAvailability = { contract_version: 'ai.v1', enabled: true, mode: 'fixture_demo', generated_by_ai: false,
  scenarios: [{ id: 'subtitle-check-v1', label: 'Mẫu phụ đề', brief: 'Mẫu giả lập.' }, { id: 'task-tree-v1', label: 'Mẫu cây', brief: 'Mẫu giả lập.' }],
  limits: { max_brief_chars: 6000, max_tasks: 20, max_depth: 3, max_request_bytes: 32768 } }
const review: Review = { id: reviewId, comment: 'Phản hồi đánh giá synthetic.', status: 'REQUEST_CHANGE', reviewer_profile_membership_id: null, created_at: stamp, updated_at: stamp }
const deliverable: Deliverable = { id: otherId, task_id: taskId, revision: 1, file_url: 'https://example.test/synthetic', status: 'REJECTED', uploaded_by_profile_membership_id: null, can_approve: false, can_request_changes: false,
  review, created_at: stamp, updated_at: stamp }
const comment: TaskComment = { id: commentId, task_id: taskId, content: 'Bình luận synthetic.', author_profile_membership_id: null, is_deleted: false, can_edit: false, can_delete: false, edited_at: null, deleted_at: null, created_at: stamp, updated_at: stamp }
const page = <T,>(results: T[], count = results.length): Page<T> => ({ results, count, next: null, previous: null })
function outcome(input: FeedbackAnalysisInput): FeedbackAnalysisResult {
  return { contract_version: 'ai.v1', status: 'READY', mode: 'fixture_demo', generated_by_ai: false, persisted: false, fixture_version: 'fixture.v1',
    sources: input.sources.map((source, index) => ({ ...source, ref: `S${index + 1}` })),
    payload: { contract_version: 'ai.feedback.v1', summary: 'Tóm tắt synthetic cố định.', issues: [{ category: 'TECHNICAL', description: 'Vấn đề minh họa.', source_refs: ['S1'] }],
      suggested_actions: [{ action: 'Kiểm tra tương phản phụ đề.', priority: 'MEDIUM', rationale: 'Gợi ý minh họa.', source_refs: ['S1'] }], uncertainty: 'Không có mô hình AI đọc nội dung.', warnings: ['Chỉ là mẫu giả lập.'] },
    usage: { input_tokens: 0, billable_output_tokens: 0, cost_usd: '0.000000', status: 'fixture_zero' } }
}
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>((done) => { resolve = done }); return { promise, resolve } }
const denied = vi.fn()
function Harness({ allowed = true }: { allowed?: boolean }) {
  const auth = useAuth()
  const [scope, setScope] = useState({ profileId, workspaceId, taskId })
  if (auth.status !== 'authenticated') return <p>Phiên chưa đăng nhập</p>
  return <><button type="button" onClick={() => setScope((current) => ({ ...current, taskId: otherId }))}>Đổi công việc thử nghiệm</button>
    <button type="button" onClick={() => setScope((current) => ({ ...current, profileId: otherId, workspaceId: otherId }))}>Đổi tổ chức thử nghiệm</button>
    <button type="button" onClick={() => void auth.signOut()}>Đăng xuất thử nghiệm</button>
    <FeedbackAnalyzer {...scope} allowed={allowed} onDenied={denied} /></>
}
function mount(allowed = true) {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0, gcTime: Infinity, refetchOnWindowFocus: false } } })
  const view = render(<QueryClientProvider client={cache}><AuthProvider><Harness allowed={allowed} /></AuthProvider></QueryClientProvider>)
  return { cache, ...view, actions: userEvent.setup() }
}
async function open() {
  const view = mount()
  await waitFor(() => expect(screen.getByRole('button', { name: 'Phân tích phản hồi' })).toBeEnabled())
  await view.actions.click(screen.getByRole('button', { name: 'Phân tích phản hồi' }))
  await screen.findByRole('group', { name: 'Phản hồi đánh giá' })
  return view
}
async function selectReview(actions: ReturnType<typeof userEvent.setup>) {
  await actions.click(await screen.findByRole('checkbox', { name: 'Chọn Đánh giá bản nộp 1' }))
}
async function analyze(actions: ReturnType<typeof userEvent.setup>) {
  await actions.click(screen.getByRole('button', { name: 'Phân tích phản hồi' }))
}
beforeEach(() => {
  denied.mockReset()
  vi.spyOn(authApi, 'me').mockResolvedValue(user)
  vi.spyOn(authApi, 'logout').mockResolvedValue(undefined)
  vi.spyOn(aiApi, 'availability').mockResolvedValue(available)
  vi.spyOn(collaborationApi, 'deliverables').mockResolvedValue(page([deliverable]))
  vi.spyOn(collaborationApi, 'comments').mockResolvedValue(page([comment]))
  vi.spyOn(feedbackAnalysisApi, 'analyze').mockImplementation(async (_p, _w, _t, input) => outcome(input))
  vi.spyOn(workApi, 'createTask').mockRejectedValue(new Error('Analyzer cannot mutate Tasks'))
  for (const name of ['submitDeliverable', 'approveDeliverable', 'requestDeliverableChanges', 'createComment', 'updateComment', 'deleteComment'] as const) {
    vi.spyOn(collaborationApi, name).mockRejectedValue(new Error('Analyzer cannot mutate collaboration'))
  }
})

describe('stateless fixture Feedback Analyzer', () => {
  it('does not expose an action or collect sources for a user without manager capability', async () => {
    mount(false)
    await screen.findByRole('button', { name: 'Đăng xuất thử nghiệm' })
    expect(screen.queryByRole('button', { name: 'Phân tích phản hồi' })).not.toBeInTheDocument()
    expect(aiApi.availability).not.toHaveBeenCalled()
    expect(collaborationApi.deliverables).not.toHaveBeenCalled()
    expect(feedbackAnalysisApi.analyze).not.toHaveBeenCalled()
  })
  it('uses actual shared availability and honestly disables the feature without loading feedback', async () => {
    vi.mocked(aiApi.availability).mockResolvedValue({ ...available, enabled: false })
    mount()
    expect(await screen.findByText('Bản mô phỏng chưa khả dụng')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Phân tích phản hồi' })).toBeDisabled()
    expect(collaborationApi.comments).not.toHaveBeenCalled()
    expect(feedbackAnalysisApi.analyze).not.toHaveBeenCalled()
  })
  it('loads authorized source pages only after an explicit open action', async () => {
    const view = mount()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Phân tích phản hồi' })).toBeEnabled())
    expect(collaborationApi.deliverables).not.toHaveBeenCalled()
    await view.actions.click(screen.getByRole('button', { name: 'Phân tích phản hồi' }))
    expect(await screen.findByRole('checkbox', { name: 'Chọn Đánh giá bản nộp 1' })).toBeVisible()
    expect(collaborationApi.deliverables).toHaveBeenCalledWith(profileId, workspaceId, taskId, 1, expect.any(AbortSignal))
    expect(screen.getByRole('button', { name: 'Phân tích phản hồi' })).toBeDisabled()
    expect(feedbackAnalysisApi.analyze).not.toHaveBeenCalled()
  })
  it('excludes blank Review feedback and deleted Comment tombstones', async () => {
    vi.mocked(collaborationApi.deliverables).mockResolvedValue(page([{ ...deliverable, review: { ...review, comment: '  ' } }]))
    vi.mocked(collaborationApi.comments).mockResolvedValue(page([{ ...comment, content: null, is_deleted: true, deleted_at: stamp }]))
    await open()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    expect(screen.queryByText('Bình luận synthetic.')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Phân tích phản hồi' })).toBeDisabled()
  })
  it('explains a genuinely empty feedback source set', async () => {
    vi.mocked(collaborationApi.deliverables).mockResolvedValue(page([]))
    vi.mocked(collaborationApi.comments).mockResolvedValue(page([]))
    await open()
    expect(screen.getByText(/Chưa có phản hồi phù hợp/)).toBeVisible()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })
  it('sends exact scoped source references and optional focus only after explicit Analyze', async () => {
    const { actions } = await open()
    await selectReview(actions)
    await actions.click(screen.getByRole('checkbox', { name: 'Chọn Bình luận 1' }))
    await actions.type(screen.getByLabelText('Trọng tâm phân tích (không bắt buộc)'), 'Tập trung vào phụ đề synthetic.')
    expect(feedbackAnalysisApi.analyze).not.toHaveBeenCalled()
    await analyze(actions)
    expect(await screen.findByRole('heading', { name: 'Kết quả mô phỏng' })).toBeVisible()
    expect(feedbackAnalysisApi.analyze).toHaveBeenCalledWith(profileId, workspaceId, taskId, { sources: [{ kind: 'review', id: reviewId }, { kind: 'comment', id: commentId }], focus: 'Tập trung vào phụ đề synthetic.' }, expect.any(AbortSignal))
    for (const citation of screen.getAllByText('S1 · Đánh giá bản nộp 1')) expect(citation).toBeVisible()
    for (const disclosure of screen.getAllByText(/Kết quả chỉ mang tính minh họa/)) expect(disclosure).toBeVisible()
    expect(screen.getByText(/Không có công việc hoặc quyết định Review nào/)).toBeVisible()
    expect(workApi.createTask).not.toHaveBeenCalled()
    for (const name of ['submitDeliverable', 'approveDeliverable', 'requestDeliverableChanges', 'createComment', 'updateComment', 'deleteComment'] as const) expect(collaborationApi[name]).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: /Áp dụng|Xác nhận tạo/ })).not.toBeInTheDocument()
  })
  it('omits empty focus and cannot duplicate a checked source', async () => {
    const { actions } = await open()
    await selectReview(actions); await selectReview(actions); await selectReview(actions)
    await analyze(actions)
    await screen.findByRole('heading', { name: 'Kết quả mô phỏng' })
    expect(vi.mocked(feedbackAnalysisApi.analyze).mock.calls[0]?.[3]).toEqual({ sources: [{ kind: 'review', id: reviewId }] })
  })
  it.each(['x'.repeat(1001), 'NUL\0synthetic', '\uD800'])('rejects invalid focus without an HTTP request', async (value) => {
    const { actions } = await open(); await selectReview(actions)
    fireEvent.change(screen.getByLabelText('Trọng tâm phân tích (không bắt buộc)'), { target: { value } })
    expect(screen.getByRole('button', { name: 'Phân tích phản hồi' })).toBeDisabled()
    expect(screen.getByLabelText('Trọng tâm phân tích (không bắt buộc)')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText('Nhập tối đa 1.000 ký tự hợp lệ, không chứa ký tự NUL.')).toBeVisible()
    expect(feedbackAnalysisApi.analyze).not.toHaveBeenCalled()
  })
  it('blocks a source selection above the existing aggregate12000-character cap', async () => {
    vi.mocked(collaborationApi.deliverables).mockResolvedValue(page([{ ...deliverable, review: { ...review, comment: 'x'.repeat(12001) } }]))
    const { actions } = await open(); await selectReview(actions)
    expect(screen.getByRole('button', { name: 'Phân tích phản hồi' })).toBeDisabled()
    expect(feedbackAnalysisApi.analyze).not.toHaveBeenCalled()
  })
  it('keeps selections across ordinary paginated source pages and caps them at20', async () => {
    const rows = Array.from({ length: 21 }, (_, index) => ({ ...comment, id: `00000000-0000-4000-8000-${String(800 + index).padStart(12, '0')}` }))
    vi.mocked(collaborationApi.comments).mockImplementation(async (_p, _w, _t, current = 1) => page(current === 1 ? rows.slice(0, 20) : rows.slice(20), 21))
    const { actions } = await open()
    const group = within(screen.getByRole('group', { name: 'Bình luận công việc' }))
    for (const checkbox of group.getAllByRole('checkbox')) await actions.click(checkbox)
    await actions.click(group.getByRole('button', { name: 'Trang sau' }))
    expect(await screen.findByRole('checkbox', { name: 'Chọn Bình luận 21' })).toBeDisabled()
    expect(screen.getByText(/Đã chọn 20\/20 nguồn/)).toBeVisible()
    expect(feedbackAnalysisApi.analyze).not.toHaveBeenCalled()
  })
  it('guards double-submit and locks source/focus changes while a request is pending', async () => {
    const waiting = deferred<FeedbackAnalysisResult>()
    vi.mocked(feedbackAnalysisApi.analyze).mockReturnValueOnce(waiting.promise)
    const { actions } = await open(); await selectReview(actions); await analyze(actions)
    await waitFor(() => expect(feedbackAnalysisApi.analyze).toHaveBeenCalledOnce())
    expect(screen.getByLabelText('Trọng tâm phân tích (không bắt buộc)')).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Phân tích phản hồi' }))
    expect(feedbackAnalysisApi.analyze).toHaveBeenCalledOnce()
    await act(async () => waiting.resolve(outcome({ sources: [{ kind: 'review', id: reviewId }] })))
    expect(await screen.findByRole('heading', { name: 'Kết quả mô phỏng' })).toBeVisible()
  })
  it('preserves selected sources on ordinary server validation errors and focuses a linked summary', async () => {
    vi.mocked(feedbackAnalysisApi.analyze).mockRejectedValueOnce(new ApiError(400, 'validation', 'Kiểm tra lại.', { focus: 'Trọng tâm chưa hợp lệ.' }))
    const { actions } = await open(); await selectReview(actions); await analyze(actions)
    expect(await screen.findByRole('alert')).toHaveTextContent('Kiểm tra lại.')
    expect(screen.getByRole('checkbox', { name: 'Chọn Đánh giá bản nộp 1' })).toBeChecked()
    expect(screen.getByRole('link', { name: 'Trọng tâm chưa hợp lệ.' })).toBeVisible()
    await waitFor(() => expect(screen.getByRole('alert').parentElement).toHaveFocus())
  })
  it.each([new ApiError(429, 'throttled', 'Limit', {}, 20), new ApiError(0, 'network', 'Network'), new ApiError(502, 'server', 'Phản hồi không hợp lệ.')])('shows safe recoverable failure with no automatic analysis retry', async (error) => {
    vi.mocked(feedbackAnalysisApi.analyze).mockRejectedValueOnce(error)
    const { actions } = await open(); await selectReview(actions); await analyze(actions)
    expect(await screen.findByRole('alert')).toBeVisible()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Phân tích phản hồi' })).toBeEnabled())
    expect(feedbackAnalysisApi.analyze).toHaveBeenCalledOnce()
    expect(screen.queryByRole('heading', { name: 'Kết quả mô phỏng' })).not.toBeInTheDocument()
  })
  it('allows a deliberate new stateless retry after a lost network response', async () => {
    vi.mocked(feedbackAnalysisApi.analyze).mockRejectedValueOnce(new ApiError(0, 'network', 'Network'))
    const { actions } = await open(); await selectReview(actions); await analyze(actions)
    expect(await screen.findByRole('alert')).toHaveTextContent('Kết quả chưa được lưu')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Phân tích phản hồi' })).toBeEnabled())
    await analyze(actions)
    expect(await screen.findByRole('heading', { name: 'Kết quả mô phỏng' })).toBeVisible()
    expect(feedbackAnalysisApi.analyze).toHaveBeenCalledTimes(2)
  })
  it('handles runtime feature disablement without keeping an analysis or inputs', async () => {
    vi.mocked(feedbackAnalysisApi.analyze).mockRejectedValueOnce(new ApiError(503, 'server', 'Disabled', {}, null, 'AI_DISABLED'))
    const { actions } = await open(); await selectReview(actions); await analyze(actions)
    expect(await screen.findByText('Bản mô phỏng chưa khả dụng')).toBeVisible()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Trọng tâm phân tích (không bắt buộc)')).not.toBeInTheDocument()
  })
  it.each([403, 404, 409])('denies changed permission/source with status%s and no stale output', async (status) => {
    vi.mocked(feedbackAnalysisApi.analyze).mockRejectedValueOnce(new ApiError(status, status === 403 ? 'forbidden' : status === 404 ? 'not-found' : 'conflict', 'Changed', {}, null, status === 409 ? 'STALE_CONTEXT' : null))
    const { actions } = await open(); await selectReview(actions); await analyze(actions)
    expect(await screen.findByRole('alert')).toHaveTextContent(/Nguồn hoặc quyền|Bạn không còn quyền/)
    expect(screen.queryByRole('heading', { name: 'Kết quả mô phỏng' })).not.toBeInTheDocument()
    expect(feedbackAnalysisApi.analyze).toHaveBeenCalledOnce()
    if (status !== 409) expect(denied).toHaveBeenCalled()
  })
  it('clears displayed result when focus or selection changes', async () => {
    const { actions } = await open(); await selectReview(actions); await analyze(actions)
    await screen.findByRole('heading', { name: 'Kết quả mô phỏng' })
    await actions.type(screen.getByLabelText('Trọng tâm phân tích (không bắt buộc)'), 'Mới')
    expect(screen.queryByRole('heading', { name: 'Kết quả mô phỏng' })).not.toBeInTheDocument()
  })
  it('reacts to existing Comment soft-delete cache redaction without displaying retained content/result', async () => {
    const { actions, cache } = await open()
    await actions.click(screen.getByRole('checkbox', { name: 'Chọn Bình luận 1' })); await analyze(actions)
    await screen.findByRole('heading', { name: 'Kết quả mô phỏng' })
    act(() => { cache.setQueryData(collaborationKeys.comments(userId, profileId, workspaceId, taskId, 1), page([{ ...comment, content: null, is_deleted: true, deleted_at: stamp }])) })
    expect(screen.queryByRole('heading', { name: 'Kết quả mô phỏng' })).not.toBeInTheDocument()
    expect(screen.queryByText('Bình luận synthetic.')).not.toBeInTheDocument()
    expect(screen.getByText(/Đã chọn 0\/20 nguồn/)).toBeVisible()
  })
  it('aborts in-flight analysis when a selected source changes in the shared cache', async () => {
    const waiting = deferred<FeedbackAnalysisResult>(); vi.mocked(feedbackAnalysisApi.analyze).mockReturnValueOnce(waiting.promise)
    const { actions, cache } = await open(); await selectReview(actions); await analyze(actions)
    await waitFor(() => expect(feedbackAnalysisApi.analyze).toHaveBeenCalledOnce())
    const signal = vi.mocked(feedbackAnalysisApi.analyze).mock.calls[0]?.[4]
    act(() => { cache.setQueryData(collaborationKeys.deliverables(userId, profileId, workspaceId, taskId, 1), page([{ ...deliverable, review: { ...review, comment: 'Đã thay đổi' } }])) })
    expect(signal?.aborted).toBe(true)
    await act(async () => waiting.resolve(outcome({ sources: [{ kind: 'review', id: reviewId }] })))
    expect(screen.queryByRole('heading', { name: 'Kết quả mô phỏng' })).not.toBeInTheDocument()
  })
  it.each(['Đổi công việc thử nghiệm', 'Đổi tổ chức thử nghiệm', 'Đăng xuất thử nghiệm'])('aborts on%s and ignores a late old-scope result', async (button) => {
    const waiting = deferred<FeedbackAnalysisResult>(); vi.mocked(feedbackAnalysisApi.analyze).mockReturnValueOnce(waiting.promise)
    const { actions, cache } = await open(); await selectReview(actions); await analyze(actions)
    await waitFor(() => expect(feedbackAnalysisApi.analyze).toHaveBeenCalledOnce())
    const signal = vi.mocked(feedbackAnalysisApi.analyze).mock.calls[0]?.[4]
    await actions.click(screen.getByRole('button', { name: button }))
    expect(signal?.aborted).toBe(true)
    await act(async () => waiting.resolve(outcome({ sources: [{ kind: 'review', id: reviewId }] })))
    expect(screen.queryByRole('heading', { name: 'Kết quả mô phỏng' })).not.toBeInTheDocument()
    if (button === 'Đăng xuất thử nghiệm') expect(cache.getQueryData(collaborationKeys.deliverables(userId, profileId, workspaceId, taskId, 1))).toBeUndefined()
  })
  it('clears private local result when quiet auth revalidation switches User on the same Task', async () => {
    let forbidden: (() => void | Promise<void>) | null = null
    vi.spyOn(apiClient, 'setForbiddenHandler').mockImplementation((handler) => { forbidden = handler })
    const { actions } = await open(); await selectReview(actions); await analyze(actions)
    await screen.findByRole('heading', { name: 'Kết quả mô phỏng' })
    vi.mocked(authApi.me).mockResolvedValue({ ...user, id: otherId })
    await act(async () => { await forbidden?.() })
    expect(screen.queryByRole('heading', { name: 'Kết quả mô phỏng' })).not.toBeInTheDocument()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })
  it('hides stale output on source-read failure until an explicit retry succeeds', async () => {
    const { actions, cache } = await open(); await selectReview(actions); await analyze(actions)
    await screen.findByRole('heading', { name: 'Kết quả mô phỏng' })
    vi.mocked(collaborationApi.comments).mockRejectedValue(new ApiError(0, 'network', 'Network'))
    await act(async () => { await cache.refetchQueries({ queryKey: collaborationKeys.comments(userId, profileId, workspaceId, taskId, 1) }) })
    expect(screen.queryByRole('heading', { name: 'Kết quả mô phỏng' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Trọng tâm phân tích (không bắt buộc)')).not.toBeInTheDocument()
  })
  it('renders source text as escaped text rather than executable HTML', async () => {
    vi.mocked(collaborationApi.comments).mockResolvedValue(page([{ ...comment, content: '<img src=x onerror=alert(1)>' }]))
    await open()
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeVisible()
    expect(document.querySelector('img')).toBeNull()
  })
  it('cannot restore an unselected deleted Comment from a late selected-page refresh', async () => {
    const otherComment: TaskComment = { ...comment, id: otherId, content: 'Unselected synthetic body to redact' }
    vi.mocked(collaborationApi.comments).mockResolvedValue(page([comment, otherComment]))
    const { actions, cache } = await open()
    await actions.click(screen.getByRole('checkbox', { name: 'Chọn Bình luận 1' }))
    const waiting = deferred<Page<TaskComment>>()
    vi.mocked(collaborationApi.comments).mockReturnValueOnce(waiting.promise)
    await analyze(actions)
    await waitFor(() => expect(collaborationApi.comments).toHaveBeenCalledTimes(2))
    const signal = vi.mocked(collaborationApi.comments).mock.calls[1]?.[4]
    const queryKey = collaborationKeys.comments(userId, profileId, workspaceId, taskId, 1)
    // The established Comment soft-delete flow cancels reads before redaction.
    await act(async () => { await cache.cancelQueries({ queryKey, exact: true }) })
    act(() => { cache.setQueryData(queryKey, page([comment, { ...otherComment, content: null, is_deleted: true, deleted_at: stamp }])) })
    expect(signal?.aborted).toBe(true)
    // Simulate a transport that still resolves after cancellation.
    await act(async () => { waiting.resolve(page([comment, otherComment])); await Promise.resolve() })
    expect(cache.getQueryData<Page<TaskComment>>(queryKey)?.results[1]?.content).toBeNull()
    await waitFor(() => expect(screen.queryByText('Unselected synthetic body to redact')).not.toBeInTheDocument())
    expect(feedbackAnalysisApi.analyze).not.toHaveBeenCalled()
    expect(screen.queryByRole('heading', { name: 'Kết quả mô phỏng' })).not.toBeInTheDocument()
  })
})

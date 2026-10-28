import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Card, Dialog, EmptyState, ErrorState, PageSkeleton, Pagination } from '../../components/ui'
import { isApiError } from '../../services/api/client'
import { collaborationApi, collaborationKeys, notificationKeys, safeDeliverableUrl } from '../../services/api/collaboration'
import type { Deliverable, Review, TaskComment } from '../../services/api/collaboration'
import type { Page } from '../../services/api/types'
import type { Task } from '../../services/api/work-management'
import { workKeys } from '../../services/api/work-management'
import { ReviewDeliverable, SubmitDeliverable } from './CollaborationActions'

const deliverableLabels: Record<Deliverable['status'], string> = { PENDING: 'Chờ nộp', SUBMITTED: 'Chờ duyệt', APPROVED: 'Đã duyệt', REJECTED: 'Cần chỉnh sửa' }
const reviewLabels: Record<Review['status'], string> = { PENDING: 'Chờ đánh giá', APPROVED: 'Đã phê duyệt', REQUEST_CHANGE: 'Yêu cầu chỉnh sửa' }
const memberLabel = (id: string | null) => id ? `Thành viên ${id.slice(0, 8)}` : 'Thông tin thành viên không còn khả dụng'
const dateTime = (value: string) => new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

function DeliverableCard({ item, children }: { item: Deliverable; children?: ReactNode }) {
  const href = safeDeliverableUrl(item.file_url)
  return <Card className="collaboration-item"><article aria-label={item.revision === null ? 'Sản phẩm bàn giao cũ' : `Phiên bản ${item.revision}`}>
    <div className="section-heading"><h3>{item.revision === null ? 'Bản ghi cũ · chưa có phiên bản' : `Phiên bản ${item.revision}`}</h3><span className="collaboration-status">{deliverableLabels[item.status]}</span></div>
    <p className="collaboration-meta">{memberLabel(item.uploaded_by_profile_membership_id)} · <time dateTime={item.created_at}>{dateTime(item.created_at)}</time></p>
    {href ? <a className="text-link comment-content" href={href} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">Mở sản phẩm bàn giao<span className="sr-only"> (mở trong thẻ mới)</span></a>
      : <p className="comment-content">{item.file_url || 'Chưa có đường dẫn sản phẩm.'}</p>}
    {item.review ? <div className="collaboration-review"><h4>{reviewLabels[item.review.status]}</h4>
      <p className="collaboration-meta">{memberLabel(item.review.reviewer_profile_membership_id)} · <time dateTime={item.review.created_at}>{dateTime(item.review.created_at)}</time></p>
      <p className="comment-content">{item.review.comment || 'Không có nhận xét bổ sung.'}</p>
    </div> : <p className="field__hint">Chưa có quyết định đánh giá cho phiên bản này.</p>}
    {children}
  </article></Card>
}

function CommentEditor({ initialContent = '', editing = false, onSubmit, onSaved, onCancel, onPendingChange, onFailure }: {
  initialContent?: string; editing?: boolean
  onSubmit: (content: string, signal: AbortSignal) => Promise<TaskComment>
  onSaved: (comment: TaskComment) => void
  onCancel?: () => void; onPendingChange?: (pending: boolean) => void
  onFailure: (error: unknown) => void
}) {
  const id = useId()
  const [content, setContent] = useState(initialContent)
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<{ message: string; field?: string } | null>(null)
  const summary = useRef<HTMLDivElement>(null)
  const request = useRef<AbortController | null>(null)
  const length = Array.from(content.trim()).length
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { if (failure) summary.current?.focus() }, [failure])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (request.current) return
    let field = ''
    if (!content.trim() || length > 4000) field = 'Nhập bình luận từ 1 đến 4.000 ký tự.'
    if (content.includes('\0') || Array.from(content).some((char) => char.length === 1 && /[\uD800-\uDFFF]/u.test(char))) field = 'Bình luận chứa ký tự không hợp lệ. Vui lòng kiểm tra lại nội dung.'
    if (field) { setFailure({ message: 'Bình luận chưa hợp lệ.', field }); return }
    const controller = new AbortController()
    request.current = controller
    setPending(true); onPendingChange?.(true); setFailure(null)
    let saved: TaskComment | undefined
    try { saved = await onSubmit(content.trim(), controller.signal) } catch (error) {
      if (!controller.signal.aborted) {
        const apiError = isApiError(error) ? error : null
        setFailure({ message: apiError?.message ?? 'Chưa thể gửi bình luận. Vui lòng thử lại sau.', field: apiError?.fieldErrors.content })
        onFailure(error)
      }
    } finally {
      if (!controller.signal.aborted) { request.current = null; setPending(false); onPendingChange?.(false) }
    }
    if (saved && !controller.signal.aborted) { setContent(''); onSaved(saved) }
  }

  return <form className="comment-composer work-form" onSubmit={submit} noValidate aria-busy={pending || undefined}>
    {failure && <div ref={summary} className="form-summary" tabIndex={-1}><Alert kind="error" title="Chưa thể lưu bình luận">
      <p>{failure.message}</p>{failure.field && <a href={`#${id}`} onClick={(event) => { event.preventDefault(); document.getElementById(id)?.focus() }}>{failure.field}</a>}
    </Alert></div>}
    <div className={`field${failure?.field ? ' field--invalid' : ''}`}>
      <label className="field__label" htmlFor={id}>Nội dung bình luận</label>
      <textarea id={id} className="input" rows={4} maxLength={8000} required disabled={pending} value={content} onChange={(event) => setContent(event.target.value)}
        aria-invalid={failure?.field ? true : undefined} aria-describedby={`${id}-hint ${id}-count${failure?.field ? ` ${id}-error` : ''}`} />
      <p className="field__hint" id={`${id}-hint`}>Tối đa 4.000 ký tự. Khoảng trắng đầu và cuối được bỏ khi gửi.</p>
      <p className="comment-counter" id={`${id}-count`}>{new Intl.NumberFormat('vi-VN').format(length)} / 4.000 ký tự</p>
      {failure?.field && <p className="field__error" id={`${id}-error`}>{failure.field}</p>}
    </div>
    <div className="work-actions"><Button type="submit" busy={pending}>{editing ? 'Lưu bình luận' : 'Gửi bình luận'}</Button>
      {onCancel && <Button variant="secondary" disabled={pending} onClick={onCancel}>Hủy</Button>}</div>
  </form>
}

type CollaborationProps = {
  profileId: string; workspaceId: string; task: Task; currentUserId: string
  active: boolean; canManage?: boolean; onChanged?: () => void; onDenied?: () => void
}

export function TaskCollaboration(props: CollaborationProps) {
  if (!props.currentUserId || props.task.workspace_id !== props.workspaceId) return null
  return <ScopedTaskCollaboration key={`${props.currentUserId}:${props.profileId}:${props.workspaceId}:${props.task.id}`} {...props} />
}

function ScopedTaskCollaboration({ profileId, workspaceId, task, currentUserId, active, onChanged, onDenied }: CollaborationProps) {
  const client = useQueryClient()
  const [deliverablePage, setDeliverablePage] = useState(1)
  const [commentPage, setCommentPage] = useState(1)
  const [blockedSubmitTask, setBlockedSubmitTask] = useState<Task | null>(null)
  const [action, setAction] = useState<{ type: 'edit' | 'delete'; comment: TaskComment } | null>(null)
  const [pending, setPending] = useState(false)
  const [notice, setNotice] = useState('')
  const [denial, setDenial] = useState('')
  const [deleteError, setDeleteError] = useState('')
  const deleteRequest = useRef<AbortController | null>(null)
  const deleteSummary = useRef<HTMLDivElement>(null)
  const scope = collaborationKeys.scope(currentUserId, profileId, workspaceId, task.id)
  const commentPrefix = collaborationKeys.comments(currentUserId, profileId, workspaceId, task.id).slice(0, -1)
  const deliverables = useQuery({ queryKey: collaborationKeys.deliverables(currentUserId, profileId, workspaceId, task.id, deliverablePage), queryFn: ({ signal }) => collaborationApi.deliverables(profileId, workspaceId, task.id, deliverablePage, signal) })
  const comments = useQuery({ queryKey: collaborationKeys.comments(currentUserId, profileId, workspaceId, task.id, commentPage), queryFn: ({ signal }) => collaborationApi.comments(profileId, workspaceId, task.id, commentPage, signal) })
  const capabilities = useQuery({ queryKey: collaborationKeys.commentCapabilities(currentUserId, profileId, workspaceId, task.id), queryFn: ({ signal }) => collaborationApi.commentCapabilities(profileId, workspaceId, task.id, signal), enabled: active, staleTime: 0 })
  const canComment = active && capabilities.isSuccess && capabilities.data.createComment && comments.isSuccess
  const selected = action && comments.data?.results.find((comment) => comment.id === action.comment.id)
  const selectedDeleted = !!action && comments.data?.results.some((comment) => comment.id === action.comment.id && comment.is_deleted)
  const canEditSelected = !!action && active && comments.isSuccess && !!selected?.can_edit && !action.comment.is_deleted && !selectedDeleted
  const canDeleteSelected = !!action && active && comments.isSuccess && !!selected?.can_delete && !action.comment.is_deleted && !selectedDeleted
  useEffect(() => () => { deleteRequest.current?.abort() }, [])
  useEffect(() => { if (deleteError) deleteSummary.current?.focus() }, [deleteError])
  useEffect(() => {
    const deleted = action && comments.data?.results.some((comment) => comment.id === action.comment.id && comment.is_deleted)
    if (action && (deleted || (action.type === 'edit' ? !canEditSelected : !canDeleteSelected))) {
      deleteRequest.current?.abort(); deleteRequest.current = null
      setAction(null); setPending(false)
    }
  }, [action, canEditSelected, canDeleteSelected, comments.data])

  function refresh() {
    void client.invalidateQueries({ queryKey: scope })
    void client.invalidateQueries({ queryKey: workKeys.scope(profileId, workspaceId) })
    void client.invalidateQueries({ queryKey: notificationKeys.user(currentUserId) })
    onChanged?.()
  }
  function failed(error: unknown) {
    const apiError = isApiError(error) ? error : null
    if (apiError && [403, 404, 409].includes(apiError.status)) {
      setBlockedSubmitTask(task)
      client.setQueriesData<Page<Deliverable>>({ queryKey: [...scope, 'deliverables'] }, (old) => old ? { ...old, results: old.results.map((item) => ({ ...item, can_approve: false, can_request_changes: false })) } : old)
      client.setQueriesData<Page<TaskComment>>({ queryKey: commentPrefix }, (old) => old ? { ...old, results: old.results.map((item) => ({ ...item, can_edit: false, can_delete: false })) } : old)
      setDenial(apiError.message)
      void client.invalidateQueries({ queryKey: workKeys.scope(profileId, workspaceId) })
      void client.invalidateQueries({ queryKey: scope })
    }
    if (apiError?.kind === 'forbidden' || apiError?.status === 404) {
      client.setQueryData(collaborationKeys.commentCapabilities(currentUserId, profileId, workspaceId, task.id), { createComment: false })
      setDenial('Quyền thảo luận đã thay đổi. Đang kiểm tra lại phạm vi truy cập.')
      onDenied?.()
      void client.invalidateQueries({ queryKey: scope })
    }
  }
  function saveDeliverable(saved: Deliverable, mutation: 'submit' | 'approve' | 'changes') {
    void client.cancelQueries({ queryKey: [...scope, 'deliverables'] })
    client.setQueriesData<Page<Deliverable>>({ queryKey: [...scope, 'deliverables'] }, (old) => old ? { ...old, results: old.results.map((item) => item.id === saved.id ? saved : item) } : old)
    if (mutation === 'submit') { setBlockedSubmitTask(task); setDeliverablePage(1) }
    setNotice(mutation === 'submit' ? 'Đã nộp sản phẩm.' : mutation === 'approve' ? 'Đã phê duyệt sản phẩm.' : 'Đã gửi yêu cầu chỉnh sửa.')
    refresh()
  }
  function saveComment(saved: TaskComment, created = false) {
    // A read started before the confirmed mutation must not overwrite its body.
    void client.cancelQueries({ queryKey: commentPrefix })
    client.setQueryData(collaborationKeys.comment(currentUserId, profileId, workspaceId, task.id, saved.id), saved)
    client.setQueriesData<Page<TaskComment>>({ queryKey: commentPrefix }, (old) => old ? { ...old, results: old.results.map((item) => item.id === saved.id ? saved : item) } : old)
    if (created) {
      setCommentPage(Math.max(1, Math.ceil(((comments.data?.count ?? 0) + 1) / 20)))
    }
    setAction(null); setNotice(created ? 'Đã gửi bình luận.' : 'Đã lưu bình luận.'); refresh()
  }
  async function removeComment() {
    if (action?.type !== 'delete' || !canDeleteSelected || deleteRequest.current) return
    const target = action.comment
    const controller = new AbortController()
    deleteRequest.current = controller; setPending(true); setDeleteError('')
    let removed = false
    try { await collaborationApi.deleteComment(profileId, workspaceId, task.id, target.id, controller.signal); removed = true } catch (error) {
      if (!controller.signal.aborted) { setDeleteError(isApiError(error) ? error.message : 'Chưa thể xóa bình luận. Vui lòng thử lại sau.'); failed(error) }
    } finally { if (!controller.signal.aborted) { deleteRequest.current = null; setPending(false) } }
    if (!removed || controller.signal.aborted) return
    // DELETE has been confirmed. Redact every cached page immediately while
    // refetching the server tombstone; never retain the body until refetch ends.
    void client.cancelQueries({ queryKey: commentPrefix })
    const redact = (comment: TaskComment): TaskComment => ({ ...comment, content: null, is_deleted: true, can_edit: false, can_delete: false })
    client.setQueriesData<Page<TaskComment>>({ queryKey: commentPrefix }, (old) => old ? { ...old, results: old.results.map((item) => item.id === target.id ? redact(item) : item) } : old)
    client.setQueryData<TaskComment>(collaborationKeys.comment(currentUserId, profileId, workspaceId, task.id, target.id), (old) => old ? redact(old) : old)
    setAction(null); setNotice('Đã xóa bình luận. Nội dung đã được ẩn.'); refresh()
  }
  const close = () => { if (!pending) { setAction(null); setDeleteError('') } }

  return <>
    <section id="deliverables" className="collaboration-section" aria-labelledby="deliverables-title"><div className="section-heading"><div><p className="eyebrow">SẢN PHẨM VÀ PHẢN HỒI</p><h2 id="deliverables-title">Deliverable &amp; Review</h2></div></div>
      <p className="read-note">Lịch sử nộp và đánh giá của riêng công việc này. Quy trình duyệt được quản lý trên máy chủ.</p>
      <SubmitDeliverable profileId={profileId} workspaceId={workspaceId} taskId={task.id} active={active} canSubmit={task.can_submit && task !== blockedSubmitTask} onSaved={saveDeliverable} onFailure={failed} />
      {deliverables.isPending ? <PageSkeleton label="Đang tải sản phẩm bàn giao…" /> : deliverables.isError ? <ErrorState error={deliverables.error} onRetry={() => void deliverables.refetch()} />
        : <>{deliverables.data.results.length ? <ol className="collaboration-list">{deliverables.data.results.map((item) => <li key={item.id}><DeliverableCard item={item}><ReviewDeliverable item={item} profileId={profileId} workspaceId={workspaceId} taskId={task.id} active={active} onSaved={saveDeliverable} onFailure={failed} /></DeliverableCard></li>)}</ol>
          : <EmptyState title="Chưa có sản phẩm bàn giao" description="Các phiên bản và nhận xét đánh giá sẽ xuất hiện tại đây khi được nộp." />}<Pagination page={deliverablePage} count={deliverables.data.count} onPageChange={setDeliverablePage} /></>}
    </section>
    <section id="comments" className="collaboration-section" aria-labelledby="comments-title"><div className="section-heading"><div><p className="eyebrow">CÙNG LÀM RÕ CÔNG VIỆC</p><h2 id="comments-title">Thảo luận</h2></div></div>
      {notice && <Alert kind="success">{notice}</Alert>}{denial && <Alert kind="error">{denial}</Alert>}
      {!active && <p className="read-note">Không gian hoặc tổ chức đã lưu trữ. Thảo luận được giữ ở chế độ chỉ đọc.</p>}
      {comments.isPending ? <PageSkeleton label="Đang tải bình luận…" /> : comments.isError ? <ErrorState error={comments.error} onRetry={() => void comments.refetch()} /> : <>
        {comments.data.results.length ? <ol className="collaboration-list">{comments.data.results.map((comment) => <li key={comment.id} id={`comment-${comment.id}`}><Card className="collaboration-item"><article aria-label={`Bình luận ${comment.id.slice(0, 8)}`}>
          <p className="collaboration-meta">{memberLabel(comment.author_profile_membership_id)} · <time dateTime={comment.created_at}>{dateTime(comment.created_at)}</time>{comment.edited_at && <> · Đã chỉnh sửa <time dateTime={comment.edited_at}>{dateTime(comment.edited_at)}</time></>}</p>
          {comment.is_deleted ? <p className="read-note">Bình luận đã được xóa.</p> : <><p className="comment-content">{comment.content}</p><div className="work-actions">
            {active && comment.can_edit && <Button variant="ghost" onClick={() => setAction({ type: 'edit', comment })}>Chỉnh sửa bình luận</Button>}
            {active && comment.can_delete && <Button variant="ghost" onClick={() => setAction({ type: 'delete', comment })}>Xóa bình luận</Button>}
          </div></>}
        </article></Card></li>)}</ol> : <EmptyState title="Chưa có bình luận" description="Bắt đầu bằng một câu hỏi hoặc phản hồi rõ ràng về công việc." />}
        <Pagination page={commentPage} count={comments.data.count} onPageChange={setCommentPage} disabled={pending} />
      </>}
      {canComment && <CommentEditor onSubmit={(content, signal) => collaborationApi.createComment(profileId, workspaceId, task.id, { content }, signal)} onSaved={(comment) => saveComment(comment, true)} onFailure={failed} />}
      {capabilities.isError && <p className="read-note">Chưa xác minh được quyền bình luận. Các thao tác tạm thời được ẩn.</p>}
    </section>
    {action?.type === 'edit' && canEditSelected && <Dialog open busy={pending} title="Chỉnh sửa bình luận" onClose={close}>
      <CommentEditor key={action.comment.id} editing initialContent={action.comment.content ?? ''} onPendingChange={setPending} onCancel={close}
        onSubmit={(content, signal) => collaborationApi.updateComment(profileId, workspaceId, task.id, action.comment.id, { content }, signal)} onSaved={(comment) => saveComment(comment)} onFailure={failed} />
    </Dialog>}
    {action?.type === 'delete' && canDeleteSelected && <Dialog open busy={pending} title="Xóa bình luận" onClose={close}>
      {deleteError && <div ref={deleteSummary} className="form-summary" tabIndex={-1}><Alert kind="error">{deleteError}</Alert></div>}
      <p>Xóa bình luận này? Nội dung sẽ được ẩn và dấu vết thảo luận vẫn được giữ lại.</p><div className="work-actions"><Button variant="danger" busy={pending} onClick={() => { void removeComment() }}>Xác nhận xóa</Button><Button variant="secondary" disabled={pending} onClick={close}>Hủy</Button></div>
    </Dialog>}
  </>
}

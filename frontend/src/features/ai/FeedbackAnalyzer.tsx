import { useEffect, useId, useMemo, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Card, ErrorState, PageSkeleton, Pagination } from '../../components/ui'
import { useAuth } from '../auth/AuthProvider'
import { aiApi, aiKeys } from '../../services/api/ai'
import { isApiError } from '../../services/api/client'
import { collaborationApi, collaborationKeys } from '../../services/api/collaboration'
import type { Deliverable, TaskComment } from '../../services/api/collaboration'
import { feedbackAnalysisApi, validateFeedbackFocus, validateFeedbackInput } from '../../services/api/feedback-analysis'
import type { FeedbackAnalysisResult, FeedbackSelection } from '../../services/api/feedback-analysis'
import type { Page } from '../../services/api/types'

type Source = FeedbackSelection & { text: string; updatedAt: string; label: string; page: number }
type Failure = { message: string; focus?: string; sources?: string }
type Props = { profileId: string; workspaceId: string; taskId: string; allowed: boolean; onDenied?: () => void }
const sourceKey = (source: FeedbackSelection) => `${source.kind}:${source.id.toLowerCase()}`
const sameSource = (left: Source, right: Source) => sourceKey(left) === sourceKey(right) && left.text === right.text && left.updatedAt === right.updatedAt
const priorities = { LOW: 'Thấp', MEDIUM: 'Trung bình', HIGH: 'Cao', URGENT: 'Khẩn cấp' }
const categories = { CLARITY: 'Độ rõ ràng', TECHNICAL: 'Kỹ thuật', CONTENT: 'Nội dung', PROCESS: 'Quy trình', OTHER: 'Khác' }
const usable = (value: string | null) => typeof value === 'string' && !!value.trim()
function keyed<T>(items: T[]) {
  const counts = new Map<string, number>()
  return items.map((value) => { const text = JSON.stringify(value); const occurrence = counts.get(text) || 0; counts.set(text, occurrence + 1); return { key: `${text}:${occurrence}`, value } })
}

function reviewSources(items: Deliverable[], page: number): Source[] {
  return items.flatMap((item) => item.review && usable(item.review.comment) ? [{
    kind: 'review' as const, id: item.review.id, text: item.review.comment as string,
    updatedAt: item.review.updated_at, page,
    label: item.revision === null ? 'Đánh giá bản nộp cũ' : `Đánh giá bản nộp ${item.revision}`,
  }] : [])
}
function commentSources(items: TaskComment[], page: number): Source[] {
  return items.filter((item) => !item.is_deleted && usable(item.content)).map((item, index) => ({
    kind: 'comment', id: item.id, text: item.content as string, updatedAt: item.updated_at, page,
    label: `Bình luận ${((page - 1) * 20) + index + 1}`,
  }))
}

/** UI hints never grant authority; the existing endpoint reauthorizes every call. */
export function FeedbackAnalyzer(props: Props) {
  const { user, status } = useAuth()
  if (!props.allowed || !user || status !== 'authenticated') return null
  return <ScopedAnalyzer key={`${user.id}:${props.profileId}:${props.workspaceId}:${props.taskId}`} {...props} userId={user.id} />
}

function ScopedAnalyzer({ userId, profileId, workspaceId, taskId, onDenied }: Props & { userId: string }) {
  const cache = useQueryClient(), id = useId()
  const [opened, setOpened] = useState(false), [reviewPage, setReviewPage] = useState(1), [commentPage, setCommentPage] = useState(1)
  const [selected, setSelected] = useState<Source[]>([]), [focus, setFocus] = useState('')
  const [result, setResult] = useState<FeedbackAnalysisResult | null>(null), [failure, setFailure] = useState<Failure | null>(null)
  const [pending, setPending] = useState(false), [unavailable, setUnavailable] = useState(false)
  const request = useRef<AbortController | null>(null), selection = useRef(selected), denial = useRef(onDenied)
  const summary = useRef<HTMLDivElement>(null), deniedOnce = useRef(false)
  selection.current = selected; denial.current = onDenied
  const scope = useMemo(() => collaborationKeys.scope(userId, profileId, workspaceId, taskId), [userId, profileId, workspaceId, taskId])
  const availability = useQuery({ queryKey: aiKeys.availability(userId, profileId, workspaceId),
    queryFn: ({ signal }) => aiApi.availability(profileId, workspaceId, signal), retry: false })
  const enabled = availability.isSuccess && availability.data.enabled && !unavailable
  const reviews = useQuery({ queryKey: collaborationKeys.deliverables(userId, profileId, workspaceId, taskId, reviewPage),
    queryFn: ({ signal }) => collaborationApi.deliverables(profileId, workspaceId, taskId, reviewPage, signal), enabled: opened && enabled, retry: false })
  const comments = useQuery({ queryKey: collaborationKeys.comments(userId, profileId, workspaceId, taskId, commentPage),
    queryFn: ({ signal }) => collaborationApi.comments(profileId, workspaceId, taskId, commentPage, signal), enabled: opened && enabled, retry: false })
  const reviewItems = reviews.isSuccess ? reviewSources(reviews.data.results, reviewPage) : []
  const commentItems = comments.isSuccess ? commentSources(comments.data.results, commentPage) : []
  const sourceError = reviews.isError ? reviews.error : comments.isError ? comments.error : null
  const sourceChars = selected.reduce((total, source) => total + Array.from(source.text).length, 0)
  const focusValid = validateFeedbackFocus(focus)
  const focusError = failure?.focus || (!focusValid ? 'Nhập tối đa 1.000 ký tự hợp lệ, không chứa ký tự NUL.' : undefined)

  function abort() { request.current?.abort(); request.current = null; setPending(false) }
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { if (failure) summary.current?.focus() }, [failure])
  useEffect(() => {
    // Existing Comment CRUD redacts/updates every cached page. Observe those
    // writes even when a selected source lives on a different pagination page.
    return cache.getQueryCache().subscribe((event) => {
      const key = event.query.queryKey
      if (!scope.every((part, index) => key[index] === part)) return
      const kind = key[scope.length] === 'deliverables' ? 'review' : key[scope.length] === 'comments' ? 'comment' : null
      if (!kind) return
      if (event.type === 'removed' || event.query.state.status === 'error') {
        request.current?.abort(); request.current = null; setPending(false); setResult(null)
        if (event.type === 'removed') { setSelected([]); selection.current = [] }
        return
      }
      if (event.type !== 'updated' || event.query.state.status !== 'success' || !event.query.state.data) return
      const page = Number(key[scope.length + 1])
      const current = kind === 'review' ? reviewSources((event.query.state.data as Page<Deliverable>).results, page)
        : commentSources((event.query.state.data as Page<TaskComment>).results, page)
      const invalid = selection.current.filter((source) => source.kind === kind && source.page === page && !current.some((item) => sameSource(source, item)))
      if (!invalid.length) return
      const invalidKeys = new Set(invalid.map(sourceKey))
      request.current?.abort(); request.current = null; setPending(false); setResult(null)
      const remaining = selection.current.filter((source) => !invalidKeys.has(sourceKey(source)))
      selection.current = remaining; setSelected(remaining)
      setFailure({ message: 'Một nguồn phản hồi đã thay đổi hoặc bị xóa. Hãy kiểm tra và chọn lại trước khi phân tích.' })
    })
  }, [cache, scope])
  useEffect(() => {
    if (!sourceError) return
    setResult(null)
    if (isApiError(sourceError) && [403, 404].includes(sourceError.status) && !deniedOnce.current) {
      deniedOnce.current = true; setSelected([]); denial.current?.()
    }
  }, [sourceError])
  useEffect(() => {
    if (!enabled) { request.current?.abort(); request.current = null; setPending(false); setResult(null); setSelected([]) }
  }, [enabled])

  function toggle(source: Source) {
    if (pending) return
    setResult(null); setFailure(null)
    const exists = selected.some((item) => sourceKey(item) === sourceKey(source))
    if (!exists && selected.length >= 20) { setFailure({ message: 'Bạn đã chọn tối đa 20 nguồn.', sources: 'Bỏ chọn một nguồn trước khi chọn thêm.' }); return }
    setSelected((current) => exists ? current.filter((item) => sourceKey(item) !== sourceKey(source)) : [...current, source])
  }

  async function currentSources(snapshot: Source[], signal: AbortSignal) {
    // Only explicitly selected pages are refreshed, bounded by20 sources. Do
    // not eagerly collect an entire Task/Workspace or follow arbitrary links.
    const pages = new Map<string, { kind: Source['kind']; page: number }>()
    for (const source of snapshot) pages.set(`${source.kind}:${source.page}`, { kind: source.kind, page: source.page })
    const fresh: Source[] = []
    for (const entry of pages.values()) {
      if (signal.aborted) return false
      const queryKey = entry.kind === 'review'
        ? collaborationKeys.deliverables(userId, profileId, workspaceId, taskId, entry.page)
        : collaborationKeys.comments(userId, profileId, workspaceId, taskId, entry.page)
      // Track refreshes under the existing read key. Comment deletion cancels
      // this query before redacting its cache, so a late page cannot restore
      // another (unselected) deleted Comment's old body. Never write raw GET
      // results directly into a shared cache outside its cancellation protocol.
      const cancel = () => { void cache.cancelQueries({ queryKey, exact: true }) }
      signal.addEventListener('abort', cancel, { once: true })
      try {
        // Own a fresh tracked read instead of coalescing with an older request.
        // This client version can resolve a cancelled fetch with reverted cache
        // data, so that value alone is not proof that a refresh completed.
        await cache.cancelQueries({ queryKey, exact: true })
        if (signal.aborted) return false
        let refreshSignal: AbortSignal | undefined
        const data = await cache.fetchQuery<Page<Deliverable> | Page<TaskComment>>({
          queryKey, staleTime: 0, retry: false,
          queryFn: ({ signal: querySignal }) => {
            refreshSignal = querySignal
            return entry.kind === 'review'
              ? collaborationApi.deliverables(profileId, workspaceId, taskId, entry.page, querySignal)
              : collaborationApi.comments(profileId, workspaceId, taskId, entry.page, querySignal)
          },
        })
        if (signal.aborted) return false
        if (!refreshSignal || refreshSignal.aborted) {
          setFailure({ message: 'Nguồn phản hồi vừa được cập nhật. Hãy kiểm tra lại và chủ động phân tích lại.' })
          return false
        }
        fresh.push(...(entry.kind === 'review' ? reviewSources((data as Page<Deliverable>).results, entry.page)
          : commentSources((data as Page<TaskComment>).results, entry.page)))
      } finally { signal.removeEventListener('abort', cancel) }
    }
    return !signal.aborted && snapshot.every((source) => fresh.some((item) => sameSource(source, item)))
  }

  async function analyze(event: FormEvent) {
    event.preventDefault()
    if (request.current || !enabled || !reviews.isSuccess || !comments.isSuccess) return
    const fields: Failure = { message: 'Kiểm tra thông tin trước khi phân tích.' }
    if (!selected.length || selected.length > 20) fields.sources = 'Chọn từ 1 đến 20 nguồn phản hồi.'
    if (sourceChars > 12000) fields.sources = 'Tổng phản hồi được chọn vượt 12.000 ký tự. Hãy chọn ít nguồn hơn.'
    if (!validateFeedbackFocus(focus)) fields.focus = 'Nhập tối đa 1.000 ký tự hợp lệ, không chứa ký tự NUL.'
    if (fields.sources || fields.focus) { setFailure(fields); return }
    const snapshot = selected.map((source) => ({ ...source }))
    const input = validateFeedbackInput({ sources: snapshot.map(({ kind, id }) => ({ kind, id })), ...(focus === '' ? {} : { focus }) })
    const controller = new AbortController(); request.current = controller; setPending(true); setFailure(null); setResult(null)
    try {
      if (!await currentSources(snapshot, controller.signal)) return
      const value = await feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, input, controller.signal)
      if (controller.signal.aborted) return
      if (!await currentSources(snapshot, controller.signal)) return
      if (!controller.signal.aborted && request.current === controller) setResult(value)
    } catch (error) {
      if (controller.signal.aborted) return
      const api = isApiError(error) ? error : null
      if (api?.code === 'AI_DISABLED') setUnavailable(true)
      if (api && [403, 404].includes(api.status)) {
        setSelected([]); selection.current = []; denial.current?.()
      }
      if (api?.status === 409 || api?.status === 404) {
        setSelected([]); selection.current = []
        void cache.invalidateQueries({ queryKey: scope })
      }
      setFailure({ message: api?.code === 'AI_DISABLED' ? 'Bản mô phỏng đang tắt. Bạn vẫn có thể xem và xử lý phản hồi thủ công.'
        : api?.code === 'STALE_CONTEXT' || api?.status === 409 || api?.status === 404 ? 'Nguồn hoặc quyền truy cập đã thay đổi. Hãy tải lại phản hồi và chọn lại.'
        : api?.status === 429 ? 'Đã đạt giới hạn phân tích. Hãy chờ trước khi thử lại; mỗi lần gửi lại có thể tính vào hạn mức.'
        : api?.status === 403 ? 'Bạn không còn quyền phân tích phản hồi này. Đang kiểm tra lại quyền truy cập.'
        : api?.kind === 'network' ? 'Kết nối bị gián đoạn. Kết quả chưa được lưu; bạn có thể chủ động phân tích lại, lần gửi mới sẽ được kiểm tra hạn mức.'
        : api?.message || 'Chưa thể phân tích phản hồi. Hãy kiểm tra kết nối và thử lại.',
        ...(api?.fieldErrors.focus ? { focus: api.fieldErrors.focus } : {}),
        ...(api?.fieldErrors.sources ? { sources: api.fieldErrors.sources } : {}),
      })
    } finally { if (request.current === controller) { request.current = null; setPending(false) } }
  }

  const title = <div className="section-heading"><div><p className="eyebrow">GỢI Ý, KHÔNG THAY QUYẾT ĐỊNH</p><h2 id={`${id}-title`}>Phân tích phản hồi</h2><p>Chọn các nhận xét cần tổng hợp để xem những gợi ý chỉnh sửa.</p></div></div>
  if (availability.isPending) return <section className="collaboration-section" aria-labelledby={`${id}-title`}>{title}<Button disabled>Phân tích phản hồi</Button><p className="read-note">Đang kiểm tra bản mô phỏng…</p></section>
  if (availability.isError) return <section className="collaboration-section" aria-labelledby={`${id}-title`}>{title}<ErrorState error={availability.error} onRetry={() => void availability.refetch()} /></section>
  if (!enabled) return <section className="collaboration-section" aria-labelledby={`${id}-title`}>{title}<Alert title="Bản mô phỏng chưa khả dụng">Chức năng đang tắt trong môi trường này. Bạn vẫn có thể xem phản hồi và thực hiện Review thủ công theo quyền hiện tại.</Alert><Button disabled>Phân tích phản hồi</Button></section>
  return <section className="collaboration-section feedback-analyzer" aria-labelledby={`${id}-title`}>
    {title}
    <Alert title="Bản mô phỏng — không phải AI thật">Đây là kết quả mô phỏng, chưa sử dụng AI thật để hiểu nội dung phản hồi. Kết quả chỉ mang tính minh họa; không tự sửa công việc hoặc quyết định Review.</Alert>
    {!opened ? <Button variant="secondary" onClick={() => setOpened(true)}>Phân tích phản hồi</Button> : <>
      {sourceError ? <ErrorState error={sourceError} onRetry={() => { void reviews.refetch(); void comments.refetch() }} /> : reviews.isPending || comments.isPending ? <PageSkeleton label="Đang tải nguồn phản hồi…" /> : <form className="work-form" noValidate aria-label="Chọn nguồn phân tích phản hồi" onSubmit={(event) => void analyze(event)}>
        {failure && <div className="form-summary" tabIndex={-1} ref={summary}><Alert kind="error" title="Cần kiểm tra lại"><p>{failure.message}</p>{failure.sources && <p><a href={`#${id}-sources`}>{failure.sources}</a></p>}{failure.focus && <p><a href={`#${id}-focus`} onClick={(event) => { event.preventDefault(); document.getElementById(`${id}-focus`)?.focus() }}>{failure.focus}</a></p>}</Alert></div>}
        <div id={`${id}-sources`} className="feedback-source-groups" tabIndex={-1}>
          <SourceGroup kind="review" legend="Phản hồi đánh giá" items={reviewItems} selected={selected} disabled={pending} maximum={selected.length >= 20} error={failure?.sources} id={`${id}-reviews`} onToggle={toggle}><Pagination page={reviewPage} count={reviews.data?.count ?? 0} onPageChange={setReviewPage} disabled={pending} /></SourceGroup>
          <SourceGroup kind="comment" legend="Bình luận công việc" items={commentItems} selected={selected} disabled={pending} maximum={selected.length >= 20} error={failure?.sources} id={`${id}-comments`} onToggle={toggle}><Pagination page={commentPage} count={comments.data?.count ?? 0} onPageChange={setCommentPage} disabled={pending} /></SourceGroup>
        </div>
        {!reviewItems.length && !commentItems.length && reviews.data?.count === 0 && comments.data?.count === 0 && <p role="status">Chưa có phản hồi phù hợp. Hãy dùng bình luận hoặc quy trình Review hiện có trước khi phân tích.</p>}
        <div className="feedback-selected" aria-live="polite" aria-atomic="true"><p>Đã chọn {selected.length}/20 nguồn · {sourceChars.toLocaleString('vi-VN')}/12.000 ký tự</p></div>
        {selected.length > 0 && <ul className="feedback-selected-list">{selected.map((source) => <li className="feedback-selected-item" key={sourceKey(source)}><span className="feedback-selected-item__label">{source.label}</span><Button type="button" variant="ghost" disabled={pending} onClick={() => toggle(source)} aria-label={`Bỏ chọn ${source.label}`}>Bỏ chọn</Button></li>)}</ul>}
        <label className="field__label" htmlFor={`${id}-focus`}>Trọng tâm phân tích (không bắt buộc)</label>
        <textarea id={`${id}-focus`} className="input" rows={3} value={focus} disabled={pending} aria-invalid={!!focusError} aria-describedby={`${id}-focus-hint${focusError ? ` ${id}-focus-error` : ''}`} onChange={(event) => { setFocus(event.target.value); setResult(null); setFailure(null) }} placeholder="Ưu tiên các yêu cầu chỉnh sửa phụ đề và âm thanh." />
        <p className="field__hint" id={`${id}-focus-hint`}>{Array.from(focus).length}/1.000 ký tự. Trong bản mô phỏng, trường này không làm kết quả hiểu hoặc điều chỉnh theo nội dung.</p>
        {focusError && <p className="field__error" id={`${id}-focus-error`}>{focusError}</p>}
        <p className="read-note">Không lưu lịch sử phân tích. Gửi lại là một lần phân tích mới và được kiểm tra quyền, nguồn, hạn mức lại.</p>
        <div className="work-actions"><Button type="submit" busy={pending} disabled={!selected.length || sourceChars > 12000 || !focusValid}>Phân tích phản hồi</Button>{pending && <Button type="button" variant="secondary" onClick={abort}>Hủy yêu cầu phân tích</Button>}<Button type="button" variant="ghost" disabled={pending} onClick={() => { setOpened(false); setSelected([]); setResult(null); setFocus(''); setFailure(null) }}>Đóng phân tích</Button></div>
      </form>}
      {result && !sourceError && <AnalysisResult result={result} selected={selected} />}
    </>}
  </section>
}

function SourceGroup({ kind, legend, items, selected, disabled, maximum, error, id, onToggle, children }: {
  kind: Source['kind']; legend: string; items: Source[]; selected: Source[]; disabled: boolean; maximum: boolean; error?: string; id: string; onToggle: (source: Source) => void; children: ReactNode
}) {
  return <fieldset disabled={disabled} className="feedback-source-group" aria-describedby={error ? `${id}-error` : undefined}><legend>{legend}</legend>
    {items.length ? <ul className="feedback-source-list">{items.map((source) => { const checked = selected.some((item) => sourceKey(item) === sourceKey(source)); return <li key={source.id}><label className="feedback-source"><input type="checkbox" checked={checked} disabled={!checked && maximum} onChange={() => onToggle(source)} aria-label={`Chọn ${source.label}`} /><span><strong>{source.label}</strong><span className="preserve-text">{source.text}</span></span></label></li> })}</ul> : <p className="read-note">Trang này chưa có {kind === 'review' ? 'đánh giá có nội dung' : 'bình luận chưa xóa'} để chọn.</p>}
    {error && <p className="field__error" id={`${id}-error`}>{error}</p>}{children}
  </fieldset>
}

function AnalysisResult({ result, selected }: { result: FeedbackAnalysisResult; selected: Source[] }) {
  const title = useRef<HTMLHeadingElement>(null)
  useEffect(() => { title.current?.focus() }, [])
  function citations(refs: string[]) {
    return <p className="feedback-citations">Liên kết lựa chọn: {refs.map((ref) => { const manifest = result.sources.find((source) => source.ref === ref); const source = manifest && selected.find((item) => sourceKey(item) === sourceKey(manifest)); return <span className="feedback-citation" key={ref}>{ref} · {source?.label || 'Nguồn không còn khả dụng'}</span> })}</p>
  }
  return <Card className="feedback-analysis-result"><h3 ref={title} tabIndex={-1}>Kết quả mô phỏng</h3><p>Kết quả chỉ mang tính minh họa. Hệ thống chưa phân tích nội dung bằng mô hình AI thật. Ký hiệu nguồn chỉ liên kết lựa chọn, không chứng minh đã hiểu nội dung.</p>
    <h4>Tóm tắt minh họa</h4><p className="preserve-text">{result.payload.summary}</p>
    {result.payload.issues.length > 0 && <><h4>Vấn đề trong mẫu</h4><ul>{keyed(result.payload.issues).map(({ key, value: issue }) => <li className="feedback-analysis-item" key={key}><strong>{categories[issue.category]}</strong><p className="preserve-text">{issue.description}</p>{citations(issue.source_refs)}</li>)}</ul></>}
    {result.payload.suggested_actions.length > 0 && <><h4>Gợi ý chỉnh sửa minh họa</h4><ol>{keyed(result.payload.suggested_actions).map(({ key, value: action }) => <li className="feedback-analysis-item" key={key}><strong>{action.action}</strong><p>Mức ưu tiên gợi ý: {priorities[action.priority]}</p><p className="preserve-text">{action.rationale}</p>{citations(action.source_refs)}</li>)}</ol></>}
    {result.payload.uncertainty && <p className="preserve-text">{result.payload.uncertainty}</p>}
    {result.payload.warnings.length > 0 && <><h4>Giới hạn của mẫu</h4><ul>{[...new Set(result.payload.warnings)].map((warning) => <li className="preserve-text" key={warning}>{warning}</li>)}</ul></>}
    <p className="read-note">Kết quả không được lưu thành lịch sử. Không có công việc hoặc quyết định Review nào được tạo từ những gợi ý này.</p>
  </Card>
}

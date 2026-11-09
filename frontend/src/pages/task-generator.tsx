import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { FormEvent, MouseEvent as ReactMouseEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { Alert, Button, Card, Dialog, ErrorState, FormField, Input, PageSkeleton } from '../components/ui'
import { PageHeader } from '../components/page'
import { useAuth } from '../features/auth/AuthProvider'
import { useWorkContext } from '../features/workspaces/useWorkContext'
import { formatLocalDeadline, parseLocalDeadline } from '../features/tasks/TaskForms'
import { aiApi, aiKeys, aiPriorities, validateAiBrief, validateAiPlan } from '../services/api/ai'
import type { AiConfirmInput, AiGenerateInput, AiProposal, AiScenarioId, AiTaskNode, AiTaskPlan } from '../services/api/ai'
import { isApiError } from '../services/api/client'
import { workKeys } from '../services/api/work-management'

const uuid = (value: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
const priorityLabels = { LOW: 'Thấp', MEDIUM: 'Trung bình', HIGH: 'Cao', URGENT: 'Khẩn cấp' }
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T
const safeText = (value: string, maximum: number, required = false) => Array.from(value).length <= maximum && !value.includes('\0') && !/[\uD800-\uDFFF]/u.test(value) && (!required || !!value.trim())
type Draft = { plan: AiTaskPlan; deadlines: string[] }
type Failure = { message: string; fields?: Record<string, string> }
type Generation = { input: AiGenerateInput; key: string }
type Confirmation = { input: AiConfirmInput; key: string; proposalId: string }

export function TaskGeneratorPage() {
  const { profileId = '', workspaceId = '' } = useParams()
  const { user } = useAuth()
  return <ScopedGenerator key={`${user?.id}:${profileId}:${workspaceId}`} userId={user?.id || ''} profileId={profileId} workspaceId={workspaceId} />
}

function ScopedGenerator({ userId, profileId, workspaceId }: { userId: string; profileId: string; workspaceId: string }) {
  const context = useWorkContext(profileId, workspaceId)
  const cache = useQueryClient()
  const navigate = useNavigate()
  const [search, setSearch] = useSearchParams()
  const proposalId = search.get('proposal') || ''
  const routeProposal = useRef(proposalId)
  routeProposal.current = proposalId
  const base = `/profiles/${profileId}/workspaces/${workspaceId}/tasks`
  const canManage = context.active && context.capabilities.data?.manageTasks === true
  const availability = useQuery({ queryKey: aiKeys.availability(userId, profileId, workspaceId),
    queryFn: ({ signal }) => aiApi.availability(profileId, workspaceId, signal), enabled: canManage && !!userId, retry: false })
  const [disabled, setDisabled] = useState(false)
  const enabled = canManage && availability.isSuccess && availability.data.enabled && !disabled
  const restored = useQuery({ queryKey: aiKeys.proposal(userId, profileId, workspaceId, proposalId),
    queryFn: ({ signal }) => aiApi.proposal(profileId, workspaceId, proposalId, signal),
    enabled: enabled && uuid(proposalId), retry: false, refetchOnWindowFocus: false })
  const [proposal, setProposal] = useState<AiProposal | null>(null)
  const proposalRef = useRef<AiProposal | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [scenario, setScenario] = useState<AiScenarioId>('task-tree-v1')
  const [brief, setBrief] = useState('')
  const [touched, setTouched] = useState(false)
  const [pending, setPending] = useState<'generate' | 'confirm' | 'recover' | null>(null)
  const [failure, setFailure] = useState<Failure | null>(null)
  const [generationUnknown, setGenerationUnknown] = useState(false)
  const [confirmationUnknown, setConfirmationUnknown] = useState(false)
  const [canRetryConfirm, setCanRetryConfirm] = useState(false)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [discardTarget, setDiscardTarget] = useState<string | null>(null)
  const [now, setNow] = useState(Date.now())
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null)
  const generation = useRef<Generation | null>(null)
  const request = useRef<AbortController | null>(null)
  const summary = useRef<HTMLDivElement>(null)
  const id = useId()
  const dirty = (touched || !!draft || generationUnknown || confirmationUnknown) && proposal?.status !== 'CONFIRMED'
  const expired = !!proposal && (proposal.status === 'EXPIRED' || Date.parse(proposal.expires_at) <= now) && proposal.status !== 'CONFIRMED'

  useEffect(() => () => {
    request.current?.abort()
    cache.removeQueries({ queryKey: aiKeys.scope(userId, profileId, workspaceId) })
  }, [cache, userId, profileId, workspaceId])
  useEffect(() => { if (failure) summary.current?.focus() }, [failure])
  useEffect(() => { const timer = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(timer) }, [])
  useEffect(() => {
    if (!proposalRef.current || proposalRef.current.proposal_id === proposalId) return
    request.current?.abort(); request.current = null
    setPending(null); setReviewOpen(false); setConfirmation(null); setCanRetryConfirm(false)
    setConfirmationUnknown(false); setDraft(null); setProposal(null); proposalRef.current = null
    setTouched(false); setFailure(null)
  }, [proposalId])
  useEffect(() => {
    if (!dirty) return
    const unload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    const click = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey || !(event.target instanceof Element)) return
      const anchor = event.target.closest('a')
      if (!(anchor instanceof HTMLAnchorElement) || anchor.target || anchor.download || !anchor.href) return
      const destination = new URL(anchor.href)
      if (destination.origin !== window.location.origin || destination.hash || destination.pathname + destination.search === window.location.pathname + window.location.search) return
      event.preventDefault(); event.stopPropagation()
      setDiscardTarget(destination.pathname + destination.search)
    }
    window.addEventListener('beforeunload', unload)
    document.addEventListener('click', click, true)
    return () => { window.removeEventListener('beforeunload', unload); document.removeEventListener('click', click, true) }
  }, [dirty])

  const receive = useCallback((value: AiProposal) => {
    // A slower pre-confirm GET may not restore a consumed proposal's old payload.
    if (proposalRef.current?.proposal_id === value.proposal_id && proposalRef.current.status === 'CONFIRMED' && value.status !== 'CONFIRMED') return
    const changed = proposalRef.current?.proposal_id !== value.proposal_id || proposalRef.current.revision !== value.revision
    proposalRef.current = value; setProposal(value)
    cache.setQueryData(aiKeys.proposal(userId, profileId, workspaceId, value.proposal_id), value)
    if (value.status === 'CONFIRMED') {
      setDraft(null); setTouched(false); setConfirmationUnknown(false); setGenerationUnknown(false); setCanRetryConfirm(false); setReviewOpen(false)
      void cache.invalidateQueries({ queryKey: workKeys.scope(profileId, workspaceId) })
    } else if (value.status === 'EXPIRED') setDraft(null)
    else if (value.payload) {
      const payload = value.payload
      setDraft((current) => changed || !current ? { plan: clone(payload), deadlines: payload.tasks.map((node) => formatLocalDeadline(node.proposed_deadline)) } : current)
    }
  }, [cache, userId, profileId, workspaceId])
  useEffect(() => { if (restored.isSuccess) receive(restored.data) }, [restored.data, restored.isSuccess, receive])
  useEffect(() => {
    if (restored.isError) { setDraft(null); setProposal(null); proposalRef.current = null }
  }, [restored.isError])

  function rejected(error: unknown): Failure {
    const api = isApiError(error) ? error : null
    if (api?.status === 403 || api?.status === 404) {
      setDraft(null); setProposal(null); proposalRef.current = null; setConfirmation(null)
      context.denied()
    }
    if (api?.code === 'AI_DISABLED') { setDisabled(true); setDraft(null) }
    const message = api?.code === 'EXPIRED' ? 'Đề xuất đã hết hạn. Hãy tạo đề xuất mới.'
      : api?.code === 'RECOVERY_EXPIRED' ? 'Đã hết thời hạn khôi phục kết quả. Hãy kiểm tra danh sách công việc.'
      : api?.code === 'IDEMPOTENCY_CONFLICT' ? 'Yêu cầu đã thay đổi so với lần gửi trước. Hãy kiểm tra trạng thái đề xuất.'
      : api?.code === 'STALE_PROPOSAL' || api?.code === 'ALREADY_CONFIRMED' ? 'Trạng thái đề xuất đã thay đổi. Hãy kiểm tra lại kết quả trên máy chủ.'
      : api?.status === 429 ? 'Đã đạt giới hạn đề xuất. Vui lòng chờ trước khi thử lại.'
      : api?.message || 'Chưa thể hoàn thành yêu cầu. Vui lòng kiểm tra lại kết nối.'
    return { message }
  }

  async function generate(retry = false) {
    if (request.current || !enabled || proposal) return
    if (!retry) {
      if (brief !== '' && !validateAiBrief(brief)) { setFailure({ message: 'Mô tả chưa hợp lệ.', fields: { brief: 'Nhập tối đa 6.000 ký tự hợp lệ; để trống để dùng mẫu giả lập.' } }); return }
      generation.current = { key: crypto.randomUUID(), input: { scenario_id: scenario, ...(brief !== '' ? { brief } : {}) } }
    }
    if (!generation.current) return
    const controller = new AbortController(); request.current = controller; setPending('generate'); setFailure(null)
    try {
      const value = await aiApi.generate(profileId, workspaceId, generation.current.input, generation.current.key, controller.signal)
      if (controller.signal.aborted) return
      receive(value); setGenerationUnknown(false)
      setSearch({ proposal: value.proposal_id }, { replace: true })
    } catch (error) {
      if (!controller.signal.aborted) {
        const api = isApiError(error) ? error : null
        setGenerationUnknown(!api || api.kind === 'network' || api.kind === 'invalid-response' || api.status >= 500)
        setFailure(rejected(error))
      }
    } finally { if (!controller.signal.aborted) { request.current = null; setPending(null) } }
  }

  function prepare(event: FormEvent) {
    event.preventDefault()
    if (!proposal || proposal.proposal_id !== proposalId || !draft || pending || expired || confirmationUnknown) return
    const fields: Record<string, string> = {}
    const tasks = draft.plan.tasks.map((node, index) => {
      if (!safeText(node.title, 255, true)) fields[`${index}-title`] = 'Tên công việc cần từ 1 đến 255 ký tự hợp lệ.'
      if (!safeText(node.description, 2000)) fields[`${index}-description`] = 'Mô tả tối đa 2.000 ký tự hợp lệ.'
      let deadline: string | null = null
      try { deadline = parseLocalDeadline(draft.deadlines[index] || '') } catch { fields[`${index}-deadline`] = 'Nhập thời hạn hợp lệ theo múi giờ thiết bị, trong khoảng năm 0001–9999.' }
      return { ...node, proposed_deadline: deadline }
    })
    if (Object.keys(fields).length) { setFailure({ message: 'Kiểm tra các công việc trước khi xác nhận.', fields }); return }
    try {
      const input: AiConfirmInput = { proposal_revision: proposal.revision, confirmed: true,
        payload: validateAiPlan({ ...draft.plan, tasks }) }
      setConfirmation({ proposalId: proposal.proposal_id, input: clone(input), key: crypto.randomUUID() })
      setFailure(null); setReviewOpen(true)
    } catch { setFailure({ message: 'Đề xuất chưa hợp lệ hoặc vượt giới hạn. Kiểm tra thời hạn, mức ưu tiên và cấu trúc công việc.' }) }
  }

  async function recover(afterError?: unknown) {
    if (request.current || !proposalRef.current || proposalRef.current.proposal_id !== routeProposal.current || !enabled) return
    const recoveryId = proposalRef.current.proposal_id
    const controller = new AbortController(); request.current = controller; setPending('recover')
    try {
      const value = await aiApi.proposal(profileId, workspaceId, recoveryId, controller.signal)
      if (controller.signal.aborted || routeProposal.current !== recoveryId) return
      if (value.proposal_id !== recoveryId) {
        setConfirmation(null); setCanRetryConfirm(false); setReviewOpen(false)
        setFailure({ message: 'Kết quả khôi phục không đúng đề xuất. Hãy kiểm tra lại trạng thái trên máy chủ trước khi tiếp tục.' })
        return
      }
      receive(value)
      if (value.status === 'AVAILABLE') {
        if (confirmation?.proposalId === value.proposal_id && confirmation.input.proposal_revision === value.revision) {
          setCanRetryConfirm(true); setFailure({ message: 'Máy chủ chưa ghi nhận xác nhận. Bạn có thể gửi lại đúng yêu cầu đã đóng băng, không tạo khóa mới.' })
        } else {
          setConfirmation(null); setCanRetryConfirm(false); setConfirmationUnknown(false); setReviewOpen(false)
          if (value.payload) setDraft({ plan: clone(value.payload), deadlines: value.payload.tasks.map((node) => formatLocalDeadline(node.proposed_deadline)) })
          setFailure({ message: 'Đề xuất đã thay đổi. Bản xác nhận cũ đã bị hủy; hãy xem lại nội dung hiện tại và xác nhận riêng.' })
        }
      }
      else if (value.status === 'CONFIRMED') setFailure(null)
      else setFailure({ message: 'Đề xuất đã hết hạn; không thể xác nhận.' })
    } catch (error) { if (!controller.signal.aborted) { setCanRetryConfirm(false); setFailure(rejected(error || afterError)) } }
    finally { if (!controller.signal.aborted) { request.current = null; setPending(null) } }
  }

  async function confirm() {
    if (!confirmation || request.current || !enabled || expired || proposal?.status !== 'AVAILABLE' || (confirmationUnknown && !canRetryConfirm)) return
    if (confirmation.proposalId !== proposal.proposal_id || confirmation.proposalId !== routeProposal.current || confirmation.input.proposal_revision !== proposal.revision) {
      setReviewOpen(false); setConfirmation(null); setCanRetryConfirm(false); setConfirmationUnknown(false)
      setFailure({ message: 'Đề xuất đã thay đổi. Hãy xem lại nội dung hiện tại trước khi xác nhận.' })
      return
    }
    const controller = new AbortController(); request.current = controller; setPending('confirm'); setFailure(null)
    let ambiguous: unknown = null
    try {
      // A restoration GET started before confirmation must not repopulate consumed payload.
      await cache.cancelQueries({ queryKey: aiKeys.proposal(userId, profileId, workspaceId, confirmation.proposalId), exact: true })
      if (controller.signal.aborted || routeProposal.current !== confirmation.proposalId || proposalRef.current?.proposal_id !== confirmation.proposalId || proposalRef.current.revision !== confirmation.input.proposal_revision) return
      const value = await aiApi.confirm(profileId, workspaceId, confirmation.proposalId, confirmation.input, confirmation.key, controller.signal)
      if (controller.signal.aborted) return
      receive(value); setReviewOpen(false)
    } catch (error) {
      if (!controller.signal.aborted) {
        const api = isApiError(error) ? error : null
        if (!api || api.kind === 'network' || api.kind === 'invalid-response' || api.status >= 500 || api.status === 409 || api.status === 410) {
          setConfirmationUnknown(true); setCanRetryConfirm(false); setReviewOpen(false); ambiguous = error
          setFailure({ message: 'Chưa xác định kết quả xác nhận. Đang kiểm tra đề xuất trên máy chủ; không tạo lại công việc.' })
        } else { setReviewOpen(false); setFailure(rejected(error)) }
      }
    } finally { if (!controller.signal.aborted) { request.current = null; setPending(null) } }
    if (ambiguous && !controller.signal.aborted) await recover(ambiguous)
  }

  function updateNode(index: number, patch: Partial<AiTaskNode>) {
    if (pending || confirmationUnknown) return
    setDraft((current) => current ? { ...current, plan: { ...current.plan, tasks: current.plan.tasks.map((node, position) => position === index ? { ...node, ...patch } : node) } } : null)
  }
  function leave(event: ReactMouseEvent<HTMLAnchorElement>) {
    if (dirty) { event.preventDefault(); setDiscardTarget(base) }
  }
  if (context.profile.isError || context.workspace.isError) return <><PageHeader title="Nội dung không khả dụng" back={{ to: base, label: 'Công việc' }} /><ErrorState error={context.profile.error || context.workspace.error} /></>
  if (context.workspace.isPending || context.capabilities.isPending) return <PageSkeleton label="Đang kiểm tra quyền đề xuất…" />
  const workspace = context.workspace.data
  const header = <PageHeader eyebrow={workspace?.name || 'KHÔNG GIAN LÀM VIỆC'} title="Tạo công việc bằng AI" description="Xem lại và xác nhận đề xuất trước khi tạo công việc thật." back={{ to: base, label: 'Công việc' }} />
  if (!canManage) return <>{header}<Alert>Chức năng đề xuất chỉ dành cho người có quyền quản lý công việc trong không gian đang hoạt động.</Alert><Link className="button button--secondary" to={base}>Về danh sách công việc</Link></>
  if (availability.isPending) return <>{header}<PageSkeleton label="Đang kiểm tra bản mô phỏng…" /></>
  if (availability.isError) return <>{header}<ErrorState error={availability.error} onRetry={() => void availability.refetch()} /></>
  if (!enabled) return <>{header}<Alert title="Bản mô phỏng chưa khả dụng">Chức năng đang tắt trong môi trường này. Không có AI thật được gọi. Bạn vẫn có thể tạo công việc thủ công.</Alert><Link className="button button--secondary" to={base}>Về danh sách công việc</Link></>
  if (proposalId && !uuid(proposalId)) return <>{header}<Alert kind="error">Mã đề xuất không hợp lệ.</Alert><Link className="button button--secondary" to={base}>Về danh sách công việc</Link></>
  if (restored.isError) return <>{header}<ErrorState error={restored.error} /><Link className="button button--secondary" to={base}>Về danh sách công việc</Link></>
  const fieldError = (key: string) => failure?.fields?.[key]

  return <>{header}
    <Alert title="Bản mô phỏng — không phải AI thật">Chỉ nhập dữ liệu giả lập. Kết quả là mẫu cố định, không phân tích mô tả của bạn. Không gửi dữ liệu khách hàng thật. Đề xuất chưa phải công việc; chỉ xác nhận mới tạo công việc thật.</Alert>
    {failure && <div className="form-summary" tabIndex={-1} ref={summary}><Alert kind="error" title="Cần kiểm tra lại"><p>{failure.message}</p>
      {failure.fields && <ul>{Object.entries(failure.fields).map(([key, message]) => <li key={key}><a href={`#${id}-${key}`} onClick={(event) => { event.preventDefault(); document.getElementById(`${id}-${key}`)?.focus() }}>{message}</a></li>)}</ul>}
    </Alert></div>}
    {proposalId && restored.isPending && !proposal ? <PageSkeleton label="Đang khôi phục đề xuất…" /> : proposal?.status === 'CONFIRMED' ? <Card className="ai-result"><h2>Đã tạo công việc</h2><p>Kết quả đã được máy chủ xác nhận. Đề xuất này không thể tạo công việc lần thứ hai.</p>
      <ul>{Object.entries(proposal.created_tasks || {}).map(([ref, taskId]) => <li key={ref}><Link to={`${base}/${taskId}`}>Mở công việc {ref}</Link></li>)}</ul><Link className="button button--primary" to={base}>Xem danh sách công việc</Link></Card>
      : proposal && expired ? <Card className="ai-result"><h2>Đề xuất đã hết hạn</h2><p>Đề xuất không còn đủ điều kiện xác nhận. Nếu đã gửi xác nhận trước đó, hãy kiểm tra danh sách công việc trước khi tạo đề xuất mới.</p><Link className="button button--secondary" to={base} onClick={leave}>Về danh sách công việc</Link></Card>
        : !proposal ? <Card className="ai-brief-card"><form className="work-form" noValidate aria-label="Yêu cầu đề xuất công việc" onSubmit={(event) => { event.preventDefault(); void generate() }}>
          <h2>Nhập yêu cầu giả lập</h2>
          <label className="field__label" htmlFor={`${id}-scenario`}>Mẫu đề xuất</label><select id={`${id}-scenario`} className="input" value={scenario} disabled={!!pending || generationUnknown} onChange={(event) => { setScenario(event.target.value as AiScenarioId); setTouched(true) }}>
            {availability.data?.scenarios.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select>
          <p className="field__hint">Mẫu quyết định cấu trúc mô phỏng; thay đổi mô tả không làm mẫu trở thành kết quả AI thật.</p>
          <label className="field__label" htmlFor={`${id}-brief`}>Mô tả yêu cầu giả lập</label><textarea id={`${id}-brief`} className="input" value={brief} disabled={!!pending || generationUnknown} aria-invalid={!!fieldError('brief')} aria-describedby={`${id}-brief-hint${fieldError('brief') ? ` ${id}-brief-error` : ''}`} onChange={(event) => { setBrief(event.target.value); setTouched(true) }} rows={5} />
          <p className="field__hint" id={`${id}-brief-hint`}>Không bắt buộc; tối đa 6.000 ký tự. Nội dung thô không được lưu trong đề xuất. {Array.from(brief).length}/6.000 ký tự.</p>
          {fieldError('brief') && <p className="field__error" id={`${id}-brief-error`}>{fieldError('brief')}</p>}
          {generationUnknown ? <Alert>Chưa nhận được kết quả. Thử lại sử dụng nguyên khóa và nội dung cũ để khôi phục, không gửi yêu cầu mới.</Alert> : null}
          <div className="work-actions">{generationUnknown ? <Button busy={pending === 'generate'} onClick={() => void generate(true)}>Khôi phục đề xuất</Button> : <Button type="submit" busy={pending === 'generate'}>Đề xuất công việc</Button>}<Link className="button button--secondary" to={base} onClick={leave}>Hủy</Link></div>
        </form></Card>
          : draft ? <form className="work-form ai-proposal" noValidate aria-label="Chỉnh sửa đề xuất công việc" onSubmit={prepare}>
            <div className="section-heading"><div><h2>Đề xuất công việc</h2><p>Đây là đề xuất. Công việc chỉ được tạo sau khi bạn xác nhận.</p></div><span className="collaboration-status">Bản đề xuất {proposal.revision} · {draft.plan.tasks.length} công việc</span></div>
            <p className="field__hint">Chỉnh sửa chỉ nằm trong bản nháp trên trang này, chưa lưu trên máy chủ. Cấu trúc cha/con giữ nguyên. Thời hạn theo múi giờ thiết bị; không tự đoán ngày.</p>
            <p>Hết hạn: <time dateTime={proposal.expires_at}>{new Date(proposal.expires_at).toLocaleString('vi-VN')}</time></p>
            {draft.plan.tasks.map((node, index) => <Card key={node.local_ref} className="ai-task-node"><fieldset disabled={!!pending || confirmationUnknown || reviewOpen}><legend>{node.parent_ref ? 'Công việc con' : 'Công việc gốc'} {index + 1}</legend>
              <p className="field__hint">{node.parent_ref ? `Thuộc ${node.parent_ref}` : 'Cấp gốc'} · {node.local_ref}</p>
              <FormField id={`${id}-${index}-title`} label={`Tên công việc ${index + 1}`} error={fieldError(`${index}-title`)}><Input value={node.title} required onChange={(event) => updateNode(index, { title: event.target.value })} /></FormField>
              <label className="field__label" htmlFor={`${id}-${index}-description`}>Mô tả công việc {index + 1}</label><textarea className="input" id={`${id}-${index}-description`} value={node.description} rows={3} aria-invalid={!!fieldError(`${index}-description`)} aria-describedby={fieldError(`${index}-description`) ? `${id}-${index}-description-error` : undefined} onChange={(event) => updateNode(index, { description: event.target.value })} />
              {fieldError(`${index}-description`) && <p className="field__error" id={`${id}-${index}-description-error`}>{fieldError(`${index}-description`)}</p>}
              <div className="ai-planning-fields"><div className="field"><label className="field__label" htmlFor={`${id}-${index}-priority`}>Mức ưu tiên {index + 1}</label><select id={`${id}-${index}-priority`} className="input" value={node.priority} onChange={(event) => updateNode(index, { priority: event.target.value as AiTaskNode['priority'] })}>{aiPriorities.map((value) => <option value={value} key={value}>{priorityLabels[value]}</option>)}</select></div>
                <FormField id={`${id}-${index}-deadline`} label={`Thời hạn ${index + 1}`} hint="Không bắt buộc; múi giờ thiết bị, lưu dưới dạng UTC." error={fieldError(`${index}-deadline`)}><Input type="datetime-local" step="0.001" min="0001-01-01T00:00" max="9999-12-31T23:59:59.999" value={draft.deadlines[index] || ''} onChange={(event) => setDraft((current) => current ? { ...current, deadlines: current.deadlines.map((value, position) => position === index ? event.target.value : value) } : null)} /></FormField></div>
              {node.notes && <p className="preserve-text field__hint">Ghi chú xem trước (không lưu vào Task): {node.notes}</p>}
            </fieldset></Card>)}
            <PlanMetadata plan={draft.plan} />
            {confirmationUnknown ? <Alert>Kết quả xác nhận cần được kiểm tra. Bản gửi trước được giữ nguyên để tránh tạo trùng; chỉnh sửa đang khóa.</Alert> : null}
            <div className="work-actions">{confirmationUnknown ? <><Button variant="secondary" busy={pending === 'recover'} onClick={() => void recover()}>Kiểm tra trạng thái</Button>{confirmation && canRetryConfirm && proposal.status === 'AVAILABLE' && <Button disabled={!!pending} onClick={() => { setReviewOpen(true) }}>Gửi lại xác nhận cũ</Button>}</> : <Button type="submit" disabled={!!pending}>Kiểm tra và xác nhận</Button>}
              <Link className="button button--secondary" to={base} onClick={leave}>Hủy đề xuất</Link></div>
          </form> : null}
    <Dialog open={reviewOpen} onClose={() => { if (!pending) setReviewOpen(false) }} title="Xác nhận tạo công việc" busy={!!pending} className="ai-confirm-dialog">
      {confirmation && <><p>Không gian: <strong>{workspace?.name}</strong></p><p>Chỉ khi bấm xác nhận, máy chủ mới tạo {confirmation.input.payload.tasks.length} công việc từ đúng nội dung dưới đây.</p>
        <ol className="ai-confirm-list">{confirmation.input.payload.tasks.map((node) => <li key={node.local_ref}><strong>{node.title}</strong><p className="preserve-text">{node.description || 'Không có mô tả.'}</p><p>{priorityLabels[node.priority]} · {node.parent_ref ? `Con của ${node.parent_ref}` : 'Công việc gốc'} · {node.proposed_deadline ? new Date(node.proposed_deadline).toLocaleString('vi-VN') : 'Chưa có thời hạn'}</p></li>)}</ol>
        <p>Không tự phân công hoặc đổi trạng thái ngoài quy trình. Các công việc bắt đầu ở trạng thái chờ phân công.</p><div className="work-actions"><Button busy={pending === 'confirm'} disabled={pending === 'recover'} onClick={() => void confirm()}>Xác nhận tạo công việc</Button><Button variant="secondary" disabled={!!pending} onClick={() => setReviewOpen(false)}>Quay lại đề xuất</Button></div></>}
    </Dialog>
    <Dialog open={discardTarget !== null} onClose={() => setDiscardTarget(null)} title="Rời bản nháp đề xuất">
      <p>Các chỉnh sửa chưa xác nhận chỉ nằm trên trang này và sẽ mất khi rời đi. Nếu một xác nhận đang chờ kết quả, hãy mở lại liên kết đề xuất để kiểm tra trước khi tạo thêm.</p><div className="work-actions"><Button variant="danger" onClick={() => { request.current?.abort(); if (discardTarget) navigate(discardTarget) }}>Rời trang</Button><Button variant="secondary" onClick={() => setDiscardTarget(null)}>Ở lại chỉnh sửa</Button></div>
    </Dialog>
  </>
}

function PlanMetadata({ plan }: { plan: AiTaskPlan }) {
  return <div className="ai-plan-metadata">{plan.assumptions.length > 0 && <section><h3>Giả định của mẫu</h3><ul>{[...new Set(plan.assumptions)].map((text) => <li key={text}>{text}</li>)}</ul></section>}{plan.warnings.length > 0 && <section><h3>Lưu ý</h3><ul>{[...new Set(plan.warnings)].map((text) => <li key={text}>{text}</li>)}</ul></section>}<p className="field__hint">Giả định, lưu ý và ghi chú chỉ phục vụ xem trước; không phải trường dữ liệu được lưu vào Task.</p></div>
}

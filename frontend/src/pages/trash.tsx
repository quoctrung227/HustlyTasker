import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation, useSearchParams } from 'react-router'
import { ArrowCounterClockwiseIcon, TrashIcon } from '@phosphor-icons/react'
import { Alert, Button, Card, Dialog, EmptyState, ErrorState, FormField, Input, PageSkeleton, Pagination } from '../components/ui'
import { PageHeader } from '../components/page'
import { useAuth } from '../features/auth/AuthProvider'
import { resetPrivateAfterTrash, trashTypeLabels } from '../features/trash/TrashActions'
import { isApiError } from '../services/api/client'
import { trashApi, trashKeys, trashObjectTypes } from '../services/api/trash'
import type { TrashFilters, TrashItem, TrashObjectType } from '../services/api/trash'
import './trash.css'

const countLabels: Record<string, string> = {
  tasks: 'công việc', workspaces: 'không gian', assignments: 'phân công', deliverables: 'sản phẩm', reviews: 'đánh giá',
  comments: 'bình luận', notifications: 'thông báo', invitations: 'lời mời', memberships: 'tư cách thành viên',
}
const reasonLabels: Record<string, string> = {
  PARENT_DELETED: 'Khôi phục đối tượng cha trước khi khôi phục mục này.',
  PARENT_ARCHIVED: 'Khôi phục trạng thái hoạt động của đối tượng cha trước.',
  EXPIRED: 'Đã hết thời hạn khôi phục 30 ngày.',
  RESTORE_EXPIRED: 'Đã hết thời hạn khôi phục 30 ngày.',
  PURGE_DISABLED: 'Xóa vĩnh viễn đang chờ phê duyệt kích hoạt.',
  PURGE_NOT_DUE: 'Chưa đủ 30 ngày kể từ thời điểm xóa.',
  RETENTION_NOT_ELAPSED: 'Chưa đủ 30 ngày kể từ thời điểm xóa.',
  NOT_DUE: 'Chưa đủ 30 ngày kể từ thời điểm xóa.',
  FINANCIAL_HISTORY: 'Lịch sử nghiệm thu hoặc tiền công đang được bảo toàn.',
  PROTECTED_FINANCIAL_HISTORY: 'Lịch sử nghiệm thu hoặc tiền công đang được bảo toàn.',
  PROTECTED_HISTORY: 'Lịch sử nghiệm thu hoặc tiền công đang được bảo toàn.',
  INVITATION_RETENTION: 'Lịch sử lời mời chưa đủ thời hạn lưu giữ.',
  AI_DEPENDENCY: 'Còn dữ liệu đề xuất liên quan cần được giữ lại.',
  PROTECTED_DEPENDENCY: 'Còn dữ liệu liên quan chưa thể xóa an toàn.',
  UNKNOWN_REFERENCE: 'Còn ràng buộc dữ liệu chưa thể xử lý an toàn.',
  OWNER_REQUIRED: 'Chỉ chủ sở hữu tổ chức được xóa vĩnh viễn.',
  FORBIDDEN: 'Quyền hiện tại không cho phép thao tác này.',
}
function reason(value: string) { return reasonLabels[value] || value }
function moment(value: string) { return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
function actorLabel(item: TrashItem) {
  const label = item.deleted_by.display_name?.trim()
  return label && !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(label) ? label : 'Người dùng không còn khả dụng'
}
function ImpactCounts({ item }: { item: TrashItem }) {
  const counts = Object.entries(item.affected_counts).filter(([key, value]) => countLabels[key] && value > 0)
  return <p className="trash-impact"><strong>Dữ liệu bị ảnh hưởng: </strong>{counts.length ? counts.map(([key, value]) => `${value.toLocaleString('vi-VN')} ${countLabels[key]}`).join(' · ') : 'Không có dữ liệu con.'}</p>
}
function parsedFilters(params: URLSearchParams): { filters: TrashFilters; page: number } {
  const type = params.get('object_type'), page = Number(params.get('page') || 1)
  const filters: TrashFilters = {
    ...(trashObjectTypes.some((value) => value === type) ? { object_type: type as TrashObjectType } : {}),
    ...(params.get('search') ? { search: params.get('search') || '' } : {}),
    ...(params.get('profile_id') ? { profile_id: params.get('profile_id') || '' } : {}),
  }
  return { filters, page: Number.isSafeInteger(page) && page > 0 ? page : 1 }
}

export function TrashPage() {
  const { user } = useAuth(), cache = useQueryClient(), location = useLocation()
  const [params, setParams] = useSearchParams(), { filters, page } = parsedFilters(params)
  const [draft, setDraft] = useState(filters.search || '')
  const [selection, setSelection] = useState<{ id: string; type: TrashObjectType; action: 'restore' | 'purge' } | null>(null)
  const [pending, setPending] = useState(false), [failure, setFailure] = useState(''), [uncertain, setUncertain] = useState(false)
  const [confirmation, setConfirmation] = useState(''), [understood, setUnderstood] = useState(false)
  const [notice, setNotice] = useState(location.state?.trashMutation === 'deleted' ? 'Đã chuyển vào Thùng rác. Trạng thái nghiệp vụ và lịch sử được giữ lại.' : '')
  const request = useRef<AbortController | null>(null), heading = useRef<HTMLDivElement>(null), summary = useRef<HTMLDivElement>(null)
  const query = useQuery({ queryKey: trashKeys.list(user?.id || '', filters, page), queryFn: ({ signal }) => trashApi.list(filters, page, signal), enabled: !!user })
  const selected = query.isSuccess && selection ? query.data.results.find((item) => item.id === selection.id && item.object_type === selection.type) : undefined

  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { setDraft(filters.search || '') }, [filters.search])
  useEffect(() => {
    if (draft === (filters.search || '')) return
    const timer = window.setTimeout(() => setParams((old) => {
      const next = new URLSearchParams(old)
      if (draft.trim()) next.set('search', draft.trim()); else next.delete('search')
      next.delete('page'); return next
    }, { replace: true }), 300)
    return () => window.clearTimeout(timer)
  }, [draft, filters.search, setParams])
  useEffect(() => { if (failure) summary.current?.focus() }, [failure])
  useEffect(() => { if (selection && query.isSuccess && !selected && !pending) setSelection(null) }, [selection, query.isSuccess, selected, pending])

  function setType(type?: TrashObjectType) {
    setSelection(null)
    setParams((old) => { const next = new URLSearchParams(old); if (type) next.set('object_type', type); else next.delete('object_type'); next.delete('page'); return next })
  }
  function open(item: TrashItem, action: 'restore' | 'purge') {
    if (request.current) return
    setSelection({ id: item.id, type: item.object_type, action }); setConfirmation(''); setUnderstood(false); setFailure(''); setUncertain(false)
  }
  function close() { if (!pending) { setSelection(null); setFailure(''); setUncertain(false) } }
  async function refresh() {
    if (request.current) return
    close(); setNotice('Đã yêu cầu tải lại trạng thái hiện tại.'); await query.refetch()
  }
  async function submit() {
    if (!selected || !selection || request.current || uncertain) return
    const action = selection.action
    if ((action === 'restore' && !selected.can_restore) || (action === 'purge' && (!selected.can_purge || !understood || (selected.object_type !== 'TASK' && confirmation !== selected.title)))) return
    const controller = new AbortController()
    request.current = controller; setPending(true); setFailure('')
    try {
      if (action === 'restore') await trashApi.restore(selected.object_type, selected.id, controller.signal)
      else await trashApi.purge(selected, confirmation, controller.signal)
      if (controller.signal.aborted) return
      setSelection(null)
      setParams((old) => { const next = new URLSearchParams(old); next.delete('page'); return next }, { replace: true })
      setNotice(action === 'restore' ? 'Đã khôi phục. Các quyền bị thu hồi và các mục con đã xóa riêng được giữ nguyên.' : 'Máy chủ đã xác nhận xóa vĩnh viễn mục đã chọn.')
      await resetPrivateAfterTrash(cache)
      heading.current?.querySelector('h1')?.focus({ preventScroll: true })
    } catch (error) {
      if (controller.signal.aborted) return
      const unknownResult = !isApiError(error) || error.status === 0 || error.status >= 500
      setUncertain(unknownResult)
      setFailure(unknownResult ? 'Chưa thể xác nhận kết quả. Tải lại trạng thái trước khi thao tác tiếp; hệ thống không tự gửi lại yêu cầu.' : isApiError(error) ? error.message : 'Chưa thể xử lý mục trong Thùng rác.')
    } finally { if (!controller.signal.aborted) { request.current = null; setPending(false) } }
  }
  const requiresName = selected?.object_type !== 'TASK'
  const filtered = !!filters.object_type || !!filters.search || !!filters.profile_id
  return <>
    <div ref={heading}><PageHeader eyebrow="QUẢN LÝ DỮ LIỆU" title="Thùng rác" description="Khôi phục dữ liệu đã xóa trong 30 ngày. Xóa vĩnh viễn chỉ khi đủ quyền và đủ điều kiện bảo toàn lịch sử." /></div>
    {notice && <Alert kind="success">{notice}</Alert>}
    <div className="trash-toolbar">
      <fieldset className="trash-type-filters"><legend className="sr-only">Lọc loại dữ liệu</legend>
        {([{ type: undefined, label: 'Tất cả' }, { type: 'TASK', label: 'Task' }, { type: 'WORKSPACE', label: 'Workspace' }, { type: 'PROFILE', label: 'Tổ chức' }] as const).map(({ type, label }) =>
          <Button key={label} variant={filters.object_type === type ? 'primary' : 'secondary'} aria-pressed={filters.object_type === type} disabled={pending} onClick={() => setType(type)}>{label}</Button>)}
      </fieldset>
      <FormField id="trash-search" label="Tìm trong Thùng rác" hint="Tìm kiếm trên máy chủ, tối đa 100 ký tự."><Input type="search" maxLength={100} value={draft} onChange={(event) => setDraft(event.target.value)} disabled={pending} /></FormField>
    </div>
    <p className="read-note">Lưu trữ và xóa là hai thao tác riêng. Khôi phục không tự kích hoạt lại quyền đã thu hồi. Mục có lịch sử được bảo vệ có thể được giữ lại sau ngày đến hạn.</p>
    {query.isPending ? <PageSkeleton label="Đang tải Thùng rác…" /> : query.isError ? <ErrorState error={query.error} onRetry={() => { void query.refetch() }} /> : query.data.results.length === 0 ?
      <Card><EmptyState title={filtered ? 'Không tìm thấy mục phù hợp' : 'Thùng rác trống'} description={filtered ? 'Thử thay đổi từ khóa hoặc bỏ bộ lọc để xem các mục bạn được phép quản lý.' : 'Các mục được chuyển vào Thùng rác sẽ hiển thị tại đây theo quyền hiện tại.'} action={filtered ? <Button variant="secondary" onClick={() => { setDraft(''); setParams({}) }}>Bỏ bộ lọc</Button> : undefined} /></Card> : <>
        <p className="subtle-label">{query.data.count.toLocaleString('vi-VN')} mục trong phạm vi quản lý của bạn</p>
        <ul className="trash-list" aria-label="Các mục trong Thùng rác">{query.data.results.map((item) => <li key={`${item.object_type}:${item.id}`}>
          <Card className="trash-card"><div className="trash-card__heading"><div><p className="eyebrow">{trashTypeLabels[item.object_type]}</p><h2>{item.title}</h2></div><span className="trash-countdown">{item.days_remaining > 0 ? `Còn ${item.days_remaining} ngày` : 'Đã đến hạn'}</span></div>
            <dl className="trash-metadata"><div><dt>Người xóa</dt><dd>{actorLabel(item)}</dd></div><div><dt>Thời điểm xóa</dt><dd><time dateTime={item.deleted_at}>{moment(item.deleted_at)}</time></dd></div><div><dt>Ngày đến hạn xóa</dt><dd><time dateTime={item.purge_after}>{moment(item.purge_after)}</time></dd></div></dl>
            <ImpactCounts item={item} />
            {item.parent_deleted && <p className="read-note">Đối tượng cha đang ở trong Thùng rác. Cần khôi phục đối tượng cha trước.</p>}
            {item.restore_blocker && <p className="field__hint">Khôi phục: {reason(item.restore_blocker)}</p>}
            {item.purge_blockers.length > 0 && <ul className="trash-blockers" aria-label="Điều kiện xóa vĩnh viễn">{item.purge_blockers.map((blocker) => <li key={blocker.code}>{reasonLabels[blocker.code] || blocker.message}</li>)}</ul>}
            <div className="work-actions"><Button variant="secondary" icon={<ArrowCounterClockwiseIcon />} disabled={pending || !item.can_restore} onClick={() => open(item, 'restore')}>Khôi phục</Button><Button variant="danger" icon={<TrashIcon />} disabled={pending || !item.can_purge} onClick={() => open(item, 'purge')}>Xóa vĩnh viễn</Button></div>
          </Card>
        </li>)}</ul>
        <Pagination page={page} count={query.data.count} disabled={pending || query.isFetching} onPageChange={(nextPage) => setParams((old) => { const next = new URLSearchParams(old); if (nextPage === 1) next.delete('page'); else next.set('page', String(nextPage)); return next })} />
      </>}
    {selected && selection && <Dialog open busy={pending} onClose={close} title={selection.action === 'restore' ? 'Khôi phục dữ liệu' : 'Xóa vĩnh viễn'}>
      {failure && <div ref={summary} className="form-summary" tabIndex={-1}><Alert kind="error">{failure}</Alert></div>}
      <p><strong>{selected.title}</strong></p><ImpactCounts item={selected} />
      {selection.action === 'restore' ? <p>Khôi phục mục này với trạng thái nghiệp vụ hiện có. Những đối tượng con đã xóa riêng và quyền đã thu hồi không tự được khôi phục.</p> : <>
        <Alert kind="error" title="Không thể hoàn tác">Thao tác xóa vĩnh viễn chỉ thực hiện sau khi máy chủ kiểm tra quyền, thời hạn và các dữ liệu cần bảo toàn.</Alert>
        {requiresName && <FormField id="trash-confirmation-name" label="Nhập chính xác tên để xác nhận" hint={`Tên cần nhập: ${selected.title}`}><Input value={confirmation} autoComplete="off" disabled={pending || uncertain} onChange={(event) => setConfirmation(event.target.value)} /></FormField>}
        <label className="trash-confirmation"><input type="checkbox" checked={understood} disabled={pending || uncertain} onChange={(event) => setUnderstood(event.target.checked)} />Tôi hiểu dữ liệu được chọn sẽ bị xóa vĩnh viễn.</label>
      </>}
      <div className="work-actions"><Button variant={selection.action === 'purge' ? 'danger' : 'primary'} busy={pending} disabled={uncertain || (selection.action === 'restore' ? !selected.can_restore : !selected.can_purge || !understood || (requiresName && confirmation !== selected.title))} onClick={() => void submit()}>{selection.action === 'restore' ? 'Xác nhận khôi phục' : 'Xác nhận xóa vĩnh viễn'}</Button><Button variant="secondary" disabled={pending} onClick={close}>Hủy</Button>{uncertain && <Button variant="secondary" onClick={() => void refresh()}>Làm mới trạng thái</Button>}</div>
    </Dialog>}
  </>
}

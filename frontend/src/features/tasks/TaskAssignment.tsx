import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Alert, Button, Dialog, ErrorState, Pagination } from '../../components/ui'
import { isApiError } from '../../services/api/client'
import type { Page } from '../../services/api/types'
import type { Task, TaskAssignInput, TaskUnassignInput, WorkspaceMember } from '../../services/api/work-management'
import './TaskAssignment.css'

interface AssignmentProps {
  profileId: string; workspaceId: string; task: Task; canAssign?: boolean
  members?: Page<WorkspaceMember>; membersPage: number; membersLoading?: boolean; membersError?: unknown
  onMembersPageChange: (page: number) => void; onRetryMembers?: () => void; onOpen?: () => void
  onAssign: (input: TaskAssignInput, signal?: AbortSignal) => Promise<Task>
  onUnassign?: (input: TaskUnassignInput, signal?: AbortSignal) => Promise<Task>
  onSaved?: (task: Task) => void; onDenied?: () => void
}

function currentName(task: Task) {
  if (!task.active_assignment) return 'Chưa phân công'
  const label = task.active_assignment.display_name?.trim()
  return label && !/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i.test(label) ? label : 'Thành viên đang phụ trách'
}

export function TaskAssign(props: AssignmentProps) {
  return <ScopedTaskAssign key={`${props.profileId}:${props.workspaceId}:${props.task.id}`} {...props} />
}

function ScopedTaskAssign(props: AssignmentProps) {
  const [open, setOpen] = useState(false), [pending, setPending] = useState(false)
  const allowed = props.canAssign === true && props.task.can_assign !== false && !!props.profileId && props.task.workspace_id === props.workspaceId && ['PENDING', 'ASSIGNED', 'WORKING'].includes(props.task.status)
  useEffect(() => { if (!allowed) { setOpen(false); setPending(false) } }, [allowed])
  if (!allowed) return null
  const close = () => { if (!pending) setOpen(false) }
  return <>
    <Button variant="secondary" onClick={() => { setOpen(true); props.onOpen?.() }}>{props.task.active_assignment ? 'Thay đổi phân công' : 'Phân công nhân viên'}</Button>
    {open && <Dialog open busy={pending} title={props.task.active_assignment ? 'Thay đổi phân công' : 'Phân công công việc'} onClose={close}>
      <AssignmentForm {...props} onPendingChange={setPending} onCancel={close} onSaved={(saved) => { setOpen(false); props.onSaved?.(saved) }} />
    </Dialog>}
  </>
}

function AssignmentForm(props: AssignmentProps & { onPendingChange: (pending: boolean) => void; onCancel: () => void }) {
  const [initial] = useState(props.task)
  const [action, setAction] = useState<'transfer' | 'remove'>('transfer')
  const [selected, setSelected] = useState(''), [search, setSearch] = useState(''), [reason, setReason] = useState('')
  const [pending, setPending] = useState(false), [confirming, setConfirming] = useState(false), [blocked, setBlocked] = useState(false)
  const [failure, setFailure] = useState<{ message: string; field?: 'target' | 'reason' } | null>(null)
  const id = useId(), summary = useRef<HTMLDivElement>(null), request = useRef<AbortController | null>(null)
  const assigned = initial.active_assignment
  const changed = props.task.active_assignment?.id !== assigned?.id || props.task.active_assignment?.assigned_at !== assigned?.assigned_at
  const removable = !!assigned && props.task.can_unassign !== false && !!props.onUnassign
  const eligible = props.members?.results.filter((member) => member.is_active && member.is_assignable && member.profile_membership_id !== assigned?.profile_membership_id) ?? []
  const candidates = eligible.filter((member) => member.display_label.toLocaleLowerCase('vi-VN').includes(search.trim().toLocaleLowerCase('vi-VN')))
  const candidate = candidates.find((member) => member.profile_membership_id === selected)
  const rosterUnavailable = action === 'transfer' && (props.membersLoading || !!props.membersError)
  const cannotSubmit = pending || blocked || changed || rosterUnavailable || (action === 'transfer' ? !candidate : !removable)
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { if (failure) summary.current?.focus() }, [failure])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (request.current || blocked || changed || rosterUnavailable) return
    if (Array.from(reason).length > 4000 || reason.includes(String.fromCharCode(0)) || /[\uD800-\uDFFF]/u.test(reason)) { setFailure({ message: 'Nhập lý do tối đa 4.000 ký tự Unicode hợp lệ, không chứa ký tự NUL.', field: 'reason' }); return }
    if (action === 'transfer' && !candidate) { setFailure({ message: 'Chọn một thành viên đủ điều kiện trong trang hiện tại.', field: 'target' }); return }
    if (action === 'remove' && !removable) return
    if (assigned && !confirming) { setFailure(null); setConfirming(true); return }
    const controller = new AbortController()
    request.current = controller; setPending(true); props.onPendingChange(true); setFailure(null)
    const expectation = { expected_assignment_id: assigned?.id ?? null, expected_assigned_at: assigned?.assigned_at ?? null, ...(reason.trim() ? { reason: reason.trim() } : {}) }
    let saved: Task | undefined
    try {
      saved = action === 'remove' && assigned && props.onUnassign
        ? await props.onUnassign({ ...expectation, expected_assignment_id: assigned.id, expected_assigned_at: assigned.assigned_at }, controller.signal)
        : candidate ? await props.onAssign({ ...expectation, target_profile_membership_id: candidate.profile_membership_id }, controller.signal) : undefined
    } catch (error) {
      if (!controller.signal.aborted) {
        const api = isApiError(error) ? error : null
        setFailure({ message: api && api.status > 0 && api.status < 500 ? api.message : 'Chưa xác nhận được kết quả. Đóng hộp thoại và kiểm tra phân công hiện tại trước khi thử lại.', ...(api?.fieldErrors.reason ? { field: 'reason' as const } : api?.fieldErrors.target_profile_membership_id ? { field: 'target' as const } : {}) })
        if (!api || api.status === 0 || api.status >= 500 || [403, 404, 409].includes(api.status)) { setBlocked(true); props.onDenied?.() }
        setConfirming(false)
      }
    } finally { if (!controller.signal.aborted) { request.current = null; setPending(false); props.onPendingChange(false) } }
    if (saved && !controller.signal.aborted) props.onSaved?.(saved)
  }

  return <form className="work-form" noValidate onSubmit={(event) => { void submit(event) }} aria-busy={pending || undefined}>
    <p><strong>Đang phụ trách:</strong> {currentName(initial)}</p>
    {changed && <Alert kind="error">Phân công đã thay đổi trong lúc hộp thoại mở. Đóng và mở lại để kiểm tra người phụ trách mới.</Alert>}
    {failure && <div className="form-summary" ref={summary} tabIndex={-1}><Alert kind="error" title="Chưa thể thay đổi phân công"><p>{failure.message}</p>{failure.field && <a href={`#${id}-${failure.field}`} onClick={(event) => { event.preventDefault(); document.getElementById(`${id}-${failure.field}`)?.focus() }}>Kiểm tra {failure.field === 'reason' ? 'lý do' : 'thành viên'}</a>}</Alert></div>}
    {assigned && !confirming && <fieldset className="assignment-actions" disabled={pending || blocked || changed}><legend>Thao tác</legend>
      <label><input type="radio" name={`${id}-action`} checked={action === 'transfer'} onChange={() => setAction('transfer')} /> Chuyển người phụ trách</label>
      {removable && <label><input type="radio" name={`${id}-action`} checked={action === 'remove'} onChange={() => setAction('remove')} /> Gỡ phân công</label>}
    </fieldset>}
    {confirming ? <Alert title="Kiểm tra trước khi xác nhận">{action === 'remove' ? `Gỡ ${currentName(initial)} khỏi Task này?` : `Chuyển Task từ ${currentName(initial)} sang ${candidate?.display_label ?? 'thành viên đã chọn'}?`}<p>{action === 'remove' ? 'Task chuyển về Chờ phân công. Sản phẩm, đánh giá và toàn bộ lịch sử được giữ nguyên; người cũ không còn phụ trách.' : 'Task chuyển về Đã phân công để người mới bắt đầu. Sản phẩm, đánh giá và tác giả các phiên bản cũ được giữ nguyên.'}</p>{reason.trim() && <p className="preserve-text">Lý do: {reason.trim()}</p>}</Alert> : <>
      {action === 'transfer' && <>
        {props.membersLoading && <p role="status">Đang tải thành viên…</p>}
        {Boolean(props.membersError) && <ErrorState error={props.membersError} onRetry={props.onRetryMembers} />}
        <label className="field">Tìm nhân viên trong trang<input className="input" type="search" value={search} onChange={(event) => { setSearch(event.target.value); setSelected('') }} disabled={pending || blocked || changed} placeholder="Tên hiển thị trong danh sách" /></label>
        <div className="field"><label className="field__label" htmlFor={`${id}-target`}>Thành viên</label>
          <select className="input" id={`${id}-target`} value={candidate?.profile_membership_id ?? ''} onChange={(event) => setSelected(event.target.value)} disabled={pending || rosterUnavailable || blocked || changed} aria-invalid={failure?.field === 'target' || undefined} aria-describedby={`${id}-hint`}>
            <option value="">Chọn thành viên</option>{candidates.map((member) => <option key={member.id} value={member.profile_membership_id}>{member.display_label}{eligible.filter((other) => other.display_label === member.display_label).length > 1 ? ` (…${member.profile_membership_id.slice(-8)})` : ''}</option>)}
          </select><p className="field__hint" id={`${id}-hint`}>Chỉ người đang hoạt động và đủ điều kiện nhận việc. Tìm kiếm áp dụng cho trang thành viên hiện tại; có thể chuyển trang.</p>
        </div>
        {!props.membersLoading && !props.membersError && !candidates.length && <p className="field__hint">Không có Editor phù hợp trong trang này.</p>}
        {props.members && <Pagination disabled={pending || props.membersLoading || blocked || changed} count={props.members.count} page={props.membersPage} onPageChange={(page) => { setSelected(''); setSearch(''); props.onMembersPageChange(page) }} />}
      </>}
      <div className="field"><label className="field__label" htmlFor={`${id}-reason`}>{action === 'remove' ? 'Lý do gỡ phân công' : 'Lý do chuyển giao'} <span className="field__hint">(không bắt buộc)</span></label><textarea className="input" id={`${id}-reason`} rows={3} value={reason} onChange={(event) => setReason(event.target.value)} disabled={pending || blocked || changed} aria-invalid={failure?.field === 'reason' || undefined} aria-describedby={`${id}-reason-count`} /><p className="field__hint" id={`${id}-reason-count`}>{Array.from(reason).length.toLocaleString('vi-VN')} / 4.000 ký tự</p></div>
    </>}
    {blocked && <p className="field__hint">Đang làm mới quyền và phân công. Đóng rồi mở lại trước khi gửi thao tác mới; không tự động thử lại.</p>}
    <div className="work-actions"><Button type="submit" variant={action === 'remove' ? 'danger' : 'primary'} busy={pending} disabled={cannotSubmit}>{assigned ? confirming ? action === 'remove' ? 'Xác nhận gỡ phân công' : 'Xác nhận chuyển giao' : 'Kiểm tra thay đổi' : 'Xác nhận phân công'}</Button>
      {confirming && <Button variant="secondary" disabled={pending} onClick={() => setConfirming(false)}>Quay lại</Button>}<Button variant="secondary" disabled={pending} onClick={props.onCancel}>Hủy</Button></div>
  </form>
}

import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Alert, Button, Dialog, ErrorState, FormField, Input, Pagination } from '../../components/ui'
import { isApiError } from '../../services/api/client'
import type { Page } from '../../services/api/types'
import { taskPriorities } from '../../services/api/work-management'
import type { Task, TaskCreateInput, TaskPriority, TaskUpdateInput, WorkspaceMember } from '../../services/api/work-management'

const priorities: Record<TaskPriority, string> = { LOW: 'Thấp', MEDIUM: 'Trung bình', HIGH: 'Cao', URGENT: 'Khẩn cấp' }

/** Browser-local input becomes an explicit UTC instant; empty means no deadline. */
export function parseLocalDeadline(value: string): string | null {
  if (!value) return null
  const parts = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?$/.exec(value)
  if (!parts) throw new TypeError('Invalid local deadline.')
  const [year, month, day, hour, minute, second, millisecond] = [
    Number(parts[1]), Number(parts[2]), Number(parts[3]), Number(parts[4]), Number(parts[5]), Number(parts[6] ?? 0), Number((parts[7] ?? '').padEnd(3, '0')),
  ]
  if (year === undefined || month === undefined || day === undefined || hour === undefined || minute === undefined || second === undefined || millisecond === undefined ||
    year < 1 || year > 9999 || month < 1 || month > 12 || day < 1 || day > 31 || hour > 23 || minute > 59 || second > 59) throw new TypeError('Invalid local deadline.')
  const instant = new Date(0)
  instant.setFullYear(year, month - 1, day)
  instant.setHours(hour, minute, second, millisecond)
  // Also reject nonexistent calendar dates and local times skipped by DST.
  if (instant.getFullYear() !== year || instant.getMonth() !== month - 1 || instant.getDate() !== day || instant.getHours() !== hour ||
    instant.getMinutes() !== minute || instant.getSeconds() !== second || instant.getUTCFullYear() < 1 || instant.getUTCFullYear() > 9999) throw new TypeError('Invalid local deadline.')
  return instant.toISOString()
}

export function formatLocalDeadline(value: string | null): string {
  if (value === null) return ''
  const instant = new Date(value)
  if (Number.isNaN(instant.getTime()) || instant.getFullYear() < 1 || instant.getFullYear() > 9999) return ''
  const pad = (number: number, length = 2) => String(number).padStart(length, '0')
  const base = `${pad(instant.getFullYear(), 4)}-${pad(instant.getMonth() + 1)}-${pad(instant.getDate())}T${pad(instant.getHours())}:${pad(instant.getMinutes())}`
  return instant.getSeconds() || instant.getMilliseconds()
    ? `${base}:${pad(instant.getSeconds())}${instant.getMilliseconds() ? `.${pad(instant.getMilliseconds(), 3)}` : ''}`
    : base
}

type SavedProps = { onSaved?: (task: Task) => void; onDenied?: () => void }
type ScopeProps = { profileId: string; workspaceId: string }
type TaskCreateProps = ScopeProps & SavedProps & {
  canCreate?: boolean
  fixedParentId?: string
  onCreate: (input: TaskCreateInput, signal?: AbortSignal) => Promise<Task>
}
type TaskEditProps = ScopeProps & SavedProps & {
  task: Task
  canEdit?: boolean
  onUpdate: (input: TaskUpdateInput, signal?: AbortSignal) => Promise<Task>
}
type TaskStartProps = ScopeProps & SavedProps & {
  task: Task
  active?: boolean
  onStart: (signal?: AbortSignal) => Promise<Task>
}
type FormProps = { onCancel: () => void; onPendingChange: (pending: boolean) => void } & SavedProps & (
  | { mode: 'create'; fixedParentId?: string; onSubmit: TaskCreateProps['onCreate'] }
  | { mode: 'edit'; task: Task; onSubmit: TaskEditProps['onUpdate'] }
)
type Field = 'title' | 'description' | 'priority' | 'deadline' | 'parent_id' | 'target_profile_membership_id'
type Failure = { message: string; fields: Partial<Record<Field, string>> }

function FormFailure({ failure, ids, title = 'Chưa thể lưu công việc' }: { failure: Failure; ids: Partial<Record<Field, string>>; title?: string }) {
  const summary = useRef<HTMLDivElement>(null)
  useEffect(() => { if (failure) if (failure) summary.current?.focus() }, [failure])
  return <div ref={summary} className="form-summary" tabIndex={-1}>
    <Alert kind="error" title={title}>
      <p>{failure.message}</p>
      {Object.keys(failure.fields).length > 0 && <ul>{Object.entries(failure.fields).map(([field, message]) => {
        const target = ids[field as Field]
        return <li key={field}>{target ? <a href={`#${target}`} onClick={(event) => {
          event.preventDefault()
          document.getElementById(target)?.focus()
        }}>{message}</a> : message}</li>
      })}</ul>}
    </Alert>
  </div>
}

function formFailure(error: unknown, fields: readonly Field[], onDenied?: () => void): Failure {
  const apiError = isApiError(error) ? error : null
  const messages: Failure['fields'] = {}
  for (const field of fields) if (apiError?.fieldErrors[field]) messages[field] = apiError.fieldErrors[field]
  if (apiError?.kind === 'forbidden' || apiError?.status === 404) onDenied?.()
  return { message: apiError?.message ?? 'Chưa thể lưu công việc. Vui lòng thử lại sau.', fields: messages }
}

function TaskForm(props: FormProps) {
  const initial = props.mode === 'edit' ? props.task : null
  const id = useId()
  const [title, setTitle] = useState(initial?.title ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [priority, setPriority] = useState<TaskPriority>(initial?.priority ?? 'MEDIUM')
  const initialDeadline = formatLocalDeadline(initial?.deadline ?? null)
  const [deadline, setDeadline] = useState(initialDeadline)
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<Failure | null>(null)
  const request = useRef<AbortController | null>(null)
  const ids = { title: `${id}-title`, description: `${id}-description`, priority: `${id}-priority`, deadline: `${id}-deadline` }
  const changed = !initial || title.trim() !== initial.title || description !== (initial.description ?? '') || priority !== initial.priority || deadline !== initialDeadline
  useEffect(() => () => { request.current?.abort() }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (request.current || !changed) return
    const fields: Failure['fields'] = {}
    if (!title.trim() || title.trim().length > 255) fields.title = 'Nhập tên công việc từ 1 đến 255 ký tự.'
    if (!taskPriorities.some((value) => value === priority)) fields.priority = 'Chọn mức ưu tiên hợp lệ.'
    let parsedDeadline: string | null = null
    try { parsedDeadline = parseLocalDeadline(deadline) } catch { fields.deadline = 'Nhập thời hạn hợp lệ trong khoảng năm 0001–9999.' }
    if (Object.keys(fields).length) { setFailure({ message: 'Vui lòng kiểm tra các thông tin bên dưới.', fields }); return }
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    props.onPendingChange(true)
    setFailure(null)
    let saved: Task | undefined
    try {
      if (props.mode === 'create') {
        saved = await props.onSubmit({ title: title.trim(), description, priority, deadline: parsedDeadline,
          ...(props.fixedParentId ? { parent_id: props.fixedParentId } : {}) }, controller.signal)
      } else {
        const input: TaskUpdateInput = {
          ...(title.trim() !== props.task.title ? { title: title.trim() } : {}),
          ...(description !== (props.task.description ?? '') ? { description } : {}),
          ...(priority !== props.task.priority ? { priority } : {}),
          ...(deadline !== initialDeadline ? { deadline: parsedDeadline } : {}),
        }
        saved = await props.onSubmit(input, controller.signal)
      }
    } catch (error) {
      if (!controller.signal.aborted) setFailure(formFailure(error, ['title', 'description', 'priority', 'deadline', 'parent_id'], props.onDenied))
    } finally {
      if (!controller.signal.aborted) { request.current = null; setPending(false); props.onPendingChange(false) }
    }
    if (saved && !controller.signal.aborted) props.onSaved?.(saved)
  }

  return <form className="work-form" onSubmit={submit} noValidate aria-busy={pending || undefined}>
    {failure && <FormFailure failure={failure} ids={ids} />}
    <FormField id={ids.title} label="Tên công việc" hint="Bắt buộc. Tối đa 255 ký tự." error={failure?.fields.title}>
      <Input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={255} required disabled={pending} autoComplete="off" />
    </FormField>
    <div className={`field${failure?.fields.description ? ' field--invalid' : ''}`}>
      <label className="field__label" htmlFor={ids.description}>Mô tả</label>
      <textarea className="input" id={ids.description} rows={4} value={description} onChange={(event) => setDescription(event.target.value)} disabled={pending}
        aria-invalid={failure?.fields.description ? true : undefined} aria-describedby={failure?.fields.description ? `${ids.description}-error` : undefined} />
      {failure?.fields.description && <p className="field__error" id={`${ids.description}-error`}>{failure.fields.description}</p>}
    </div>
    <div className={`field${failure?.fields.priority ? ' field--invalid' : ''}`}>
      <label className="field__label" htmlFor={ids.priority}>Ưu tiên</label>
      <select className="input" id={ids.priority} value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority)} disabled={pending}
        aria-invalid={failure?.fields.priority ? true : undefined} aria-describedby={failure?.fields.priority ? `${ids.priority}-error` : undefined}>
        {taskPriorities.map((value) => <option key={value} value={value}>{priorities[value]}</option>)}
      </select>
      {failure?.fields.priority && <p className="field__error" id={`${ids.priority}-error`}>{failure.fields.priority}</p>}
    </div>
    <FormField id={ids.deadline} label="Thời hạn" hint="Không bắt buộc. Nhập theo múi giờ trên thiết bị; để trống khi chưa có thời hạn." error={failure?.fields.deadline}>
      <Input type="datetime-local" step="0.001" min="0001-01-01T00:00" max="9999-12-31T23:59:59.999" value={deadline} onChange={(event) => setDeadline(event.target.value)} disabled={pending} />
    </FormField>
    <div className="work-actions">
      <Button type="submit" busy={pending} disabled={!changed}>{props.mode === 'edit' ? 'Lưu thay đổi' : props.fixedParentId ? 'Tạo công việc con' : 'Tạo công việc'}</Button>
      <Button variant="secondary" disabled={pending} onClick={props.onCancel}>Hủy</Button>
    </div>
  </form>
}

export function TaskCreate(props: TaskCreateProps) {
  return <ScopedTaskCreate key={`${props.profileId}:${props.workspaceId}:${props.fixedParentId ?? 'root'}`} {...props} />
}

function ScopedTaskCreate({ profileId, workspaceId, canCreate = false, fixedParentId, onCreate, onSaved, onDenied }: TaskCreateProps) {
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const allowed = canCreate && Boolean(profileId) && Boolean(workspaceId)
  useEffect(() => { if (!allowed) { setOpen(false); setPending(false) } }, [allowed])
  if (!allowed) return null
  const label = fixedParentId ? 'Tạo công việc con' : 'Tạo công việc'
  const close = () => { if (!pending) setOpen(false) }
  return <>
    <Button onClick={() => setOpen(true)}>{label}</Button>
    {open && <Dialog open busy={pending} title={label} onClose={close}>
      <TaskForm mode="create" fixedParentId={fixedParentId} onSubmit={onCreate} onPendingChange={setPending} onCancel={close} onDenied={onDenied}
        onSaved={(task) => { setOpen(false); onSaved?.(task) }} />
    </Dialog>}
  </>
}

export function TaskEdit(props: TaskEditProps) {
  return <ScopedTaskEdit key={`${props.profileId}:${props.workspaceId}:${props.task.id}`} {...props} />
}

function ScopedTaskEdit({ profileId, workspaceId, task, canEdit = false, onUpdate, onSaved, onDenied }: TaskEditProps) {
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const allowed = canEdit && Boolean(profileId) && task.workspace_id === workspaceId
  useEffect(() => { if (!allowed) { setOpen(false); setPending(false) } }, [allowed])
  if (!allowed) return null
  const close = () => { if (!pending) setOpen(false) }
  return <>
    <Button variant="secondary" onClick={() => setOpen(true)}>Chỉnh sửa công việc</Button>
    {open && <Dialog open busy={pending} title="Chỉnh sửa công việc" onClose={close}>
      <TaskForm mode="edit" task={task} onSubmit={onUpdate} onPendingChange={setPending} onCancel={close} onDenied={onDenied}
        onSaved={(saved) => { setOpen(false); onSaved?.(saved) }} />
    </Dialog>}
  </>
}

export function TaskStart(props: TaskStartProps) {
  return <ScopedTaskStart key={`${props.profileId}:${props.workspaceId}:${props.task.id}`} {...props} />
}

function ScopedTaskStart({ profileId, workspaceId, task, active = false, onStart, onSaved, onDenied }: TaskStartProps) {
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<Failure | null>(null)
  const [needsRefresh, setNeedsRefresh] = useState(false)
  const request = useRef<AbortController | null>(null)
  const allowed = active && Boolean(profileId) && task.workspace_id === workspaceId && task.can_start === true
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => {
    if (!allowed) { request.current?.abort(); request.current = null; setPending(false) }
  }, [allowed])

  async function start() {
    if (request.current || !allowed || needsRefresh) return
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    setFailure(null)
    let saved: Task | undefined
    try { saved = await onStart(controller.signal) } catch (error) {
      if (!controller.signal.aborted) {
        setFailure(formFailure(error, []))
        if (isApiError(error) && error.kind !== 'csrf' && [403, 404, 409].includes(error.status)) {
          setNeedsRefresh(true)
          onDenied?.()
        }
      }
    } finally {
      if (!controller.signal.aborted) { request.current = null; setPending(false) }
    }
    if (saved && !controller.signal.aborted) { setNeedsRefresh(true); onSaved?.(saved) }
  }

  if (!allowed && !failure) return null
  return <div>
    {failure && <FormFailure failure={failure} ids={{}} title="Chưa thể bắt đầu công việc" />}
    {allowed && !needsRefresh && <Button busy={pending} onClick={() => { void start() }}>Bắt đầu công việc</Button>}
  </div>
}

type TaskAssignProps = ScopeProps & SavedProps & {
  task: Task
  canAssign?: boolean
  members?: Page<WorkspaceMember>
  membersPage: number
  membersLoading?: boolean
  membersError?: unknown
  onMembersPageChange: (page: number) => void
  onRetryMembers?: () => void
  onOpen?: () => void
  onAssign: (input: { target_profile_membership_id: string }, signal?: AbortSignal) => Promise<Task>
}

export function TaskAssign(props: TaskAssignProps) {
  return <ScopedTaskAssign key={`${props.profileId}:${props.workspaceId}:${props.task.id}`} {...props} />
}

function ScopedTaskAssign(props: TaskAssignProps) {
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const allowed = props.canAssign === true && Boolean(props.profileId) && props.task.workspace_id === props.workspaceId &&
    ['PENDING', 'ASSIGNED', 'WORKING'].includes(props.task.status)
  useEffect(() => { if (!allowed) { setOpen(false); setPending(false) } }, [allowed])
  if (!allowed) return null
  const close = () => { if (!pending) setOpen(false) }
  return <>
    <Button variant="secondary" onClick={() => { setOpen(true); props.onOpen?.() }}>Phân công</Button>
    {open && <Dialog open busy={pending} title="Phân công công việc" onClose={close}>
      <AssignmentForm {...props} onPendingChange={setPending} onCancel={close} onSaved={(task) => { setOpen(false); props.onSaved?.(task) }} />
    </Dialog>}
  </>
}

function AssignmentForm(props: TaskAssignProps & { onPendingChange: (pending: boolean) => void; onCancel: () => void }) {
  const id = useId()
  const [selected, setSelected] = useState('')
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<Failure | null>(null)
  const request = useRef<AbortController | null>(null)
  const candidates = props.members?.results.filter((member) => member.is_assignable === true && member.profile_membership_id !== props.task.active_assignment?.profile_membership_id) ?? []
  const currentSelection = candidates.some((member) => member.profile_membership_id === selected) ? selected : ''
  useEffect(() => () => { request.current?.abort() }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (request.current || props.membersLoading || props.membersError) return
    if (!currentSelection) { setFailure({ message: 'Chọn một thành viên có thể nhận việc.', fields: { target_profile_membership_id: 'Chọn Editor đang hoạt động trong trang này.' } }); return }
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    props.onPendingChange(true)
    setFailure(null)
    let saved: Task | undefined
    try { saved = await props.onAssign({ target_profile_membership_id: currentSelection }, controller.signal) } catch (error) {
      if (!controller.signal.aborted) setFailure(formFailure(error, ['target_profile_membership_id'], props.onDenied))
    } finally {
      if (!controller.signal.aborted) { request.current = null; setPending(false); props.onPendingChange(false) }
    }
    if (saved && !controller.signal.aborted) props.onSaved?.(saved)
  }

  return <form className="work-form" onSubmit={submit} noValidate aria-busy={pending || props.membersLoading || undefined}>
    {failure && <FormFailure failure={failure} ids={{ target_profile_membership_id: id }} />}
    {props.membersLoading && <p role="status">Đang tải thành viên…</p>}
    {Boolean(props.membersError) && <ErrorState error={props.membersError} onRetry={props.onRetryMembers} />}
    <div className={`field${failure?.fields.target_profile_membership_id ? ' field--invalid' : ''}`}>
      <label className="field__label" htmlFor={id}>Thành viên</label>
      <select className="input" id={id} value={currentSelection} onChange={(event) => setSelected(event.target.value)} disabled={pending || props.membersLoading || Boolean(props.membersError)}
        aria-invalid={failure?.fields.target_profile_membership_id ? true : undefined} aria-describedby={`${id}-hint${failure?.fields.target_profile_membership_id ? ` ${id}-error` : ''}`}>
        <option value="">Chọn thành viên</option>
        {candidates.map((member) => <option key={member.id} value={member.profile_membership_id}>
          {member.display_label}{candidates.filter((candidate) => candidate.display_label === member.display_label).length > 1 ? ` (…${member.profile_membership_id.slice(-8)})` : ''}
        </option>)}
      </select>
      <p className="field__hint" id={`${id}-hint`}>Danh sách hiển thị người đủ điều kiện nhận việc. Quyền nhận việc sẽ được kiểm tra lại khi phân công.</p>
      {failure?.fields.target_profile_membership_id && <p className="field__error" id={`${id}-error`}>{failure.fields.target_profile_membership_id}</p>}
    </div>
    {!props.membersLoading && !props.membersError && !candidates.length && <p className="field__hint">Không có Editor phù hợp trong trang này.</p>}
    {props.members && <Pagination disabled={pending || props.membersLoading} count={props.members.count} page={props.membersPage} onPageChange={(page) => {
      if (!pending && !props.membersLoading) { setSelected(''); props.onMembersPageChange(page) }
    }} />}
    <div className="work-actions">
      <Button type="submit" busy={pending} disabled={props.membersLoading || Boolean(props.membersError) || !candidates.length}>Xác nhận phân công</Button>
      <Button variant="secondary" disabled={pending} onClick={props.onCancel}>Hủy</Button>
    </div>
  </form>
}

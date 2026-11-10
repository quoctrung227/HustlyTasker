import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useOutletContext, useParams, useSearchParams } from 'react-router'
import { ArrowRightIcon, ListChecksIcon } from '@phosphor-icons/react'
import { Alert, Button, Card, EmptyState, ErrorState, PageSkeleton, Pagination } from '../components/ui'
import { PageHeader, dateLabel, periodLabel } from '../components/page'
import { TaskAssign, TaskCreate, TaskEdit, TaskStart } from '../features/tasks/TaskForms'
import { TaskDateInput } from '../features/tasks/TaskDeadlineInput'
import { formatVietnameseDeadline, isCanonicalTaskDate } from '../features/tasks/task-deadline'
import { formatEstimatedCompensation, taskDocumentFields, validTaskDocumentUrl } from '../features/tasks/task-brief'
import { useWorkContext } from '../features/workspaces/useWorkContext'
import { TaskCollaboration } from '../features/collaboration/TaskCollaboration'
import { GeneratorEntry } from '../features/ai/GeneratorEntry'
import { FeedbackAnalyzer } from '../features/ai/FeedbackAnalyzer'
import { workApi, workKeys, taskStatuses, taskPriorities, taskOrderings } from '../services/api/work-management'
import type { Task, TaskFilters, TaskPriority, TaskStatus, TaskOrdering } from '../services/api/work-management'

export const statusLabels: Record<TaskStatus, string> = { PENDING: 'Chờ phân công', ASSIGNED: 'Đã phân công', WORKING: 'Đang thực hiện', REVIEW: 'Chờ duyệt', COMPLETED: 'Hoàn thành', CANCELLED: 'Đã hủy (cũ)' }
export const priorityLabels: Record<TaskPriority, string> = { LOW: 'Thấp', MEDIUM: 'Trung bình', HIGH: 'Cao', URGENT: 'Khẩn cấp' }
const orderingLabels: Record<TaskOrdering, string> = { created_at: 'Cũ nhất', '-created_at': 'Mới nhất', deadline: 'Thời hạn gần nhất', '-deadline': 'Thời hạn xa nhất', priority: 'Ưu tiên tăng dần', '-priority': 'Ưu tiên giảm dần' }
const pageValue = (raw: string | null) => raw && /^[1-9]\d*$/.test(raw) && Number.isSafeInteger(Number(raw)) ? Number(raw) : 1

export function filtersFromSearch(search: URLSearchParams): TaskFilters {
  const status = search.get('status'), priority = search.get('priority'), ordering = search.get('ordering')
  const filters: TaskFilters = {
    ...(taskStatuses.some((value) => value === status) ? { status: status as TaskStatus } : {}),
    ...(taskPriorities.some((value) => value === priority) ? { priority: priority as TaskPriority } : {}),
    ...(taskOrderings.some((value) => value === ordering) ? { ordering: ordering as TaskOrdering } : { ordering: '-created_at' }),
  }
  const after = search.get('deadline_after'), before = search.get('deadline_before')
  const validDate = (value: string | null): value is string => !!value && /^\d{4}-\d\d-\d\dT/.test(value) && Number.isFinite(Date.parse(value))
  return { ...filters, ...(validDate(after) ? { deadline_after: after } : {}), ...(validDate(before) ? { deadline_before: before } : {}) }
}

function TaskPills({ task }: { task: Task }) {
  return <div className="task-pills"><span className={`task-status task-status--${task.status.toLowerCase()}`}>{statusLabels[task.status]}</span><span className={`task-priority task-priority--${task.priority.toLowerCase()}`}>{priorityLabels[task.priority]}</span></div>
}
function Deadline({ task }: { task: Task }) {
  if (!task.deadline) return <span className="subtle-label">Chưa có thời hạn</span>
  const overdue = Date.parse(task.deadline) < Date.now() && !['COMPLETED', 'CANCELLED'].includes(task.status)
  return <span className={overdue ? 'task-overdue' : ''}><time dateTime={task.deadline}>{formatVietnameseDeadline(task.deadline)}</time>{overdue && <small>Quá hạn</small>}</span>
}
function assigneeLabel(task: Task): string {
  const assignment = task.active_assignment
  if (!assignment) return 'Chưa phân công'
  const name = assignment.display_name?.trim()
  // Old DTOs may lack the additive label. Never fall back to an identifier or
  // a roster lookup; only the current response may supply a person's name.
  if (name && !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(name)) return name
  return assignment.display_name === null || assignment.profile_membership_id === null
    ? 'Thành viên không còn khả dụng' : 'Thành viên được phân công'
}
function TaskRows({ tasks, base }: { tasks: Task[]; base: string }) {
  return <ul className="task-list" aria-label="Danh sách công việc">{tasks.map((task) => <li key={task.id} className="task-row"><div className="task-row__main"><span className="eyebrow">CÔNG VIỆC</span><Link to={`${base}/${task.id}`} className="task-title">{task.title}</Link>{task.description && <p className="task-preview">{task.description}</p>}<span className="task-updated">Cập nhật {dateLabel(task.updated_at)}</span><span className="task-assignee">{assigneeLabel(task)}</span></div><TaskPills task={task} /><div className="task-row__deadline"><Deadline task={task} /></div><Link to={`${base}/${task.id}`} className="task-open" aria-label={`Xem ${task.title}`}><ArrowRightIcon aria-hidden="true" /></Link></li>)}</ul>
}
function TaskFiltersForm({ initial, onApply }: { initial: TaskFilters; onApply: (search: URLSearchParams) => void }) {
  const [status, setStatus] = useState(initial.status || '')
  const [priority, setPriority] = useState(initial.priority || '')
  const [ordering, setOrdering] = useState<string>(initial.ordering || '-created_at')
  const [after, setAfter] = useState(initial.deadline_after?.slice(0, 10) || '')
  const [before, setBefore] = useState(initial.deadline_before?.slice(0, 10) || '')
  const [error, setError] = useState('')
  return <form className="task-filters" onSubmit={(event) => {
    event.preventDefault()
    if ((after && !isCanonicalTaskDate(after)) || (before && !isCanonicalTaskDate(before)) || (after && before && after > before)) { setError('Khoảng thời hạn chưa hợp lệ. Nhập ngày dd/mm/yyyy; ngày bắt đầu phải trước hoặc bằng ngày kết thúc.'); return }
    const query = new URLSearchParams()
    if (status) query.set('status', status)
    if (priority) query.set('priority', priority)
    query.set('ordering', ordering)
    if (after) query.set('deadline_after', `${after}T00:00:00Z`)
    if (before) query.set('deadline_before', `${before}T23:59:59.999999Z`)
    setError(''); onApply(query)
  }}>
    <label>Trạng thái<select aria-label="Trạng thái" className="input" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Tất cả trạng thái</option>{taskStatuses.map((value) => <option key={value} value={value}>{statusLabels[value]}</option>)}</select></label>
    <label>Mức ưu tiên<select aria-label="Mức ưu tiên" className="input" value={priority} onChange={(e) => setPriority(e.target.value)}><option value="">Tất cả mức ưu tiên</option>{taskPriorities.map((value) => <option key={value} value={value}>{priorityLabels[value]}</option>)}</select></label>
    <label>Sắp xếp<select aria-label="Sắp xếp" className="input" value={ordering} onChange={(e) => setOrdering(e.target.value)}>{taskOrderings.map((value) => <option key={value} value={value}>{orderingLabels[value]}</option>)}</select></label>
    <fieldset className="task-filter-dates" aria-label="Khoảng thời hạn (UTC)">
      <TaskDateInput id="task-filter-after" label="Thời hạn từ ngày (UTC)" value={after} onChange={setAfter} />
      <TaskDateInput id="task-filter-before" label="Thời hạn đến ngày (UTC)" value={before} onChange={setBefore} />
    </fieldset>
    <div className="work-actions"><Button type="submit" variant="secondary">Áp dụng bộ lọc</Button><Button variant="ghost" onClick={() => onApply(new URLSearchParams())}>Xóa bộ lọc</Button></div>
    {error && <Alert kind="error">{error}</Alert>}
  </form>
}

export function TasksPage() {
  const { profileId = '', workspaceId = '' } = useParams()
  return <ScopedTasksPage key={`${profileId}:${workspaceId}`} profileId={profileId} workspaceId={workspaceId} />
}
function ScopedTasksPage({ profileId, workspaceId }: { profileId: string; workspaceId: string }) {
  const context = useWorkContext(profileId, workspaceId)
  const [search, setSearch] = useSearchParams()
  const [pageSearch, setPageSearch] = useState('')
  const [notice, setNotice] = useState('')
  const filters = filtersFromSearch(search), page = pageValue(search.get('page'))
  const invalidRange = !!(filters.deadline_after && filters.deadline_before && Date.parse(filters.deadline_after) > Date.parse(filters.deadline_before))
  const tasks = useQuery({ queryKey: workKeys.tasks(profileId, workspaceId, filters, page), queryFn: ({ signal }) => workApi.tasks(profileId, workspaceId, filters, page, signal), enabled: context.workspace.isSuccess && !invalidRange })
  const base = `/profiles/${profileId}/workspaces/${workspaceId}`
  if (context.profile.isError || context.workspace.isError) return <><PageHeader title="Nội dung không khả dụng" back={{ to: `/profiles/${profileId}/workspaces`, label: 'Không gian làm việc' }} /><ErrorState error={context.profile.error || context.workspace.error} /></>
  if (!context.workspace.data) return <PageSkeleton />
  const visible = tasks.data?.results.filter((task) => task.title.toLocaleLowerCase('vi-VN').includes(pageSearch.trim().toLocaleLowerCase('vi-VN'))) || []
  return <><PageHeader eyebrow={context.workspace.data.name} title="Công việc" description="Giữ công việc rõ ràng, để cả nhóm cùng tiến về phía trước." back={{ to: base, label: 'Thông tin không gian' }} action={<div className="ai-entry-actions"><TaskCreate profileId={profileId} workspaceId={workspaceId} canCreate={context.active && context.capabilities.data?.manageTasks} onCreate={(input, signal) => workApi.createTask(profileId, workspaceId, input, signal)} onSaved={() => { context.invalidate(); setNotice('Đã tạo công việc. Bạn có thể mở chi tiết để phân công.'); }} onDenied={context.denied} /><GeneratorEntry profileId={profileId} workspaceId={workspaceId} allowed={context.active && context.capabilities.data?.manageTasks === true} /></div>} />
    {!context.active && <Alert>Không gian hoặc tổ chức đã lưu trữ. Công việc được giữ ở chế độ chỉ đọc.</Alert>}
    {notice && <Alert kind="success">{notice}</Alert>}
    <Card className="task-filter-card"><TaskFiltersForm key={search.toString()} initial={filters} onApply={(next) => { setPageSearch(''); setSearch(next) }} /></Card>
    <div className="list-toolbar"><p>{tasks.data ? <><strong>{tasks.data.count}</strong> công việc theo bộ lọc trên máy chủ</> : 'Danh sách công việc'}</p><label className="page-search">Tìm trong trang<input className="input" type="search" value={pageSearch} onChange={(e) => setPageSearch(e.target.value)} placeholder="Tên công việc trên trang này" /></label></div>
    {invalidRange ? <Alert kind="error">Khoảng thời hạn trong đường dẫn chưa hợp lệ. Hãy sửa hoặc xóa bộ lọc.</Alert> : tasks.isPending ? <PageSkeleton /> : tasks.isError ? <ErrorState error={tasks.error} onRetry={() => void tasks.refetch()} /> : <>{visible.length ? <TaskRows tasks={visible} base={`${base}/tasks`} /> : <EmptyState title="Chưa tìm thấy công việc" description={pageSearch ? 'Không có tên phù hợp trong trang hiện tại. Thử xóa từ khóa hoặc chuyển trang.' : 'Chưa có công việc phù hợp trong không gian và bộ lọc này.'} />}<Pagination page={page} count={tasks.data.count} onPageChange={(next) => { const query = new URLSearchParams(search); query.set('page', String(next)); setSearch(query) }} /></>}
    {context.capabilities.isError && <p className="read-note">Chưa xác minh được quyền thao tác. Các nút chỉnh sửa tạm thời được ẩn.</p>}
  </>
}

export function TaskDetailPage() {
  const { profileId = '', workspaceId = '', taskId = '' } = useParams()
  const session = useOutletContext<{ currentUserId: string } | null>()
  return <ScopedTaskDetail key={`${profileId}:${workspaceId}:${taskId}`} profileId={profileId} workspaceId={workspaceId} taskId={taskId} currentUserId={session?.currentUserId || ''} />
}
function ScopedTaskDetail({ profileId, workspaceId, taskId, currentUserId }: { profileId: string; workspaceId: string; taskId: string; currentUserId: string }) {
  const context = useWorkContext(profileId, workspaceId)
  const [memberPage, setMemberPage] = useState(1), [notice, setNotice] = useState(''), [membersOpened, setMembersOpened] = useState(false)
  const task = useQuery({ queryKey: workKeys.task(profileId, workspaceId, taskId), queryFn: ({ signal }) => workApi.task(profileId, workspaceId, taskId, signal), enabled: context.workspace.isSuccess })
  const canManage = context.active && context.capabilities.data?.manageTasks === true
  const members = useQuery({ queryKey: workKeys.members(profileId, workspaceId, memberPage), queryFn: ({ signal }) => workApi.members(profileId, workspaceId, memberPage, signal), enabled: task.isSuccess && canManage && membersOpened })
  const base = `/profiles/${profileId}/workspaces/${workspaceId}/tasks`
  function saved() { context.invalidate(); setNotice('Đã lưu thay đổi công việc.'); }
  if (context.profile.isError || context.workspace.isError || task.isError) return <><PageHeader title="Nội dung không khả dụng" back={{ to: base, label: 'Công việc' }} /><ErrorState error={context.profile.error || context.workspace.error || task.error} /></>
  if (!task.data || !context.workspace.data) return <PageSkeleton />
  const value = task.data
  return <><PageHeader eyebrow={context.workspace.data.name} title={value.title} back={{ to: base, label: 'Công việc' }} action={<TaskPills task={value} />} />
    {notice && <Alert kind="success">{notice}</Alert>}
    {!context.active && <Alert>Không gian hoặc tổ chức đã lưu trữ. Chỉ có thể xem công việc.</Alert>}
    <div className="work-actions"><TaskStart key={`${taskId}:${task.dataUpdatedAt}`} profileId={profileId} workspaceId={workspaceId} task={value} active={context.active && task.isSuccess} onStart={(signal) => workApi.startTask(profileId, workspaceId, taskId, signal)} onSaved={() => { context.invalidate(); setNotice('Đã bắt đầu công việc.'); }} onDenied={context.denied} /><TaskEdit profileId={profileId} workspaceId={workspaceId} task={value} canEdit={canManage} onUpdate={(input, signal) => workApi.updateTask(profileId, workspaceId, taskId, input, signal)} onSaved={saved} onDenied={context.denied} /><TaskAssign profileId={profileId} workspaceId={workspaceId} task={value} canAssign={canManage && ['PENDING', 'ASSIGNED', 'WORKING'].includes(value.status)} onOpen={() => setMembersOpened(true)} members={members.data} membersPage={memberPage} membersLoading={members.isPending} membersError={members.error} onMembersPageChange={setMemberPage} onRetryMembers={() => void members.refetch()} onAssign={(input, signal) => workApi.assignTask(profileId, workspaceId, taskId, input, signal)} onSaved={saved} onDenied={context.denied} /></div>
    <div className="workspace-detail-grid task-detail-grid">
      <Card className="workspace-about task-description-card">
        <h2>Thông tin công việc</h2>
        {/* biome-ignore lint/a11y/noNoninteractiveTabindex: This bounded scroll region needs keyboard focus for reading long descriptions. */}
        <section className="task-description-scroll" aria-label="Mô tả công việc" tabIndex={0}>
          <p className="preserve-text task-description-text">{value.description || 'Công việc chưa có mô tả.'}</p>
        </section>
      </Card>
      <Card className="workspace-facts"><h2>Thời hạn và phân công</h2><dl><div><dt>Thời hạn · {Intl.DateTimeFormat().resolvedOptions().timeZone}</dt><dd><Deadline task={value} /></dd></div><div><dt>Phân công</dt><dd className="break-code">{assigneeLabel(value)}</dd></div><div><dt>Ngày tạo</dt><dd>{dateLabel(value.created_at)}</dd></div><div><dt>Cập nhật gần nhất</dt><dd>{dateLabel(value.updated_at)}</dd></div><div><dt>Kỳ làm việc</dt><dd>{periodLabel(context.workspace.data.period)}</dd></div></dl></Card>
    </div>
    {taskDocumentFields.some(({ key }) => validTaskDocumentUrl(value[key])) && <Card className="task-brief-documents"><h2>Tài liệu và nguyên liệu</h2><ul>{taskDocumentFields.map(({ key, label, action }) => {
      const url = value[key]
      return validTaskDocumentUrl(url) ? <li className="task-document-row" key={key}><span>{label}</span><a href={url} target="_blank" rel="noopener noreferrer" className="text-link">{action}<ArrowRightIcon aria-hidden="true" /></a></li> : null
    })}</ul></Card>}
    {value.estimated_compensation_vnd !== null && value.estimated_compensation_vnd !== undefined && <Card className="task-brief-compensation"><h2>Tiền công dự kiến</h2><p className="task-brief-amount">{formatEstimatedCompensation(value.estimated_compensation_vnd)} VNĐ</p><p className="read-note">Cho toàn bộ công việc, không nhân theo số người nhận; không phải xác nhận đã thanh toán. Chỉ hiển thị khi máy chủ xác nhận quyền xem hiện tại.</p></Card>}
    <p className="read-note"><ListChecksIcon aria-hidden="true" />Mỗi công việc có sản phẩm và đánh giá riêng, theo quy trình được kiểm tra trên máy chủ.</p>
    {currentUserId && <TaskCollaboration profileId={profileId} workspaceId={workspaceId} task={value} currentUserId={currentUserId} active={context.active && task.isSuccess} canManage={canManage} onChanged={() => context.invalidate()} onDenied={context.denied} />}
    {currentUserId && <FeedbackAnalyzer profileId={profileId} workspaceId={workspaceId} taskId={taskId} allowed={canManage} onDenied={context.denied} />}
  </>
}

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useOutletContext, useParams, useSearchParams } from 'react-router'
import { ArrowRightIcon, ListChecksIcon } from '@phosphor-icons/react'
import { Alert, Button, Card, EmptyState, ErrorState, PageSkeleton, Pagination } from '../components/ui'
import { PageHeader, dateLabel, periodLabel } from '../components/page'
import { TaskAssign, TaskCreate, TaskEdit, TaskStart } from '../features/tasks/TaskForms'
import { useWorkContext } from '../features/workspaces/useWorkContext'
import { TaskCollaboration } from '../features/collaboration/TaskCollaboration'
import { workApi, workKeys, taskStatuses, taskPriorities, taskOrderings } from '../services/api/work-management'
import type { Task, TaskFilters, TaskPriority, TaskStatus, TaskOrdering } from '../services/api/work-management'

export const statusLabels: Record<TaskStatus, string> = { PENDING: 'Chờ phân công', ASSIGNED: 'Đã phân công', WORKING: 'Đang thực hiện', REVIEW: 'Chờ duyệt', COMPLETED: 'Hoàn thành', CANCELLED: 'Đã hủy (cũ)' }
export const priorityLabels: Record<TaskPriority, string> = { LOW: 'Thấp', MEDIUM: 'Trung bình', HIGH: 'Cao', URGENT: 'Khẩn cấp' }
const orderingLabels: Record<TaskOrdering, string> = { created_at: 'Cũ nhất', '-created_at': 'Mới nhất', deadline: 'Thời hạn gần nhất', '-deadline': 'Thời hạn xa nhất', priority: 'Ưu tiên tăng dần', '-priority': 'Ưu tiên giảm dần' }
const pageValue = (raw: string | null) => raw && /^[1-9]\d*$/.test(raw) && Number.isSafeInteger(Number(raw)) ? Number(raw) : 1
const isUuid = (value: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)

export function filtersFromSearch(search: URLSearchParams): TaskFilters {
  const status = search.get('status'), priority = search.get('priority'), ordering = search.get('ordering'), parent = search.get('parent_id')
  const filters: TaskFilters = {
    ...(taskStatuses.some((value) => value === status) ? { status: status as TaskStatus } : {}),
    ...(taskPriorities.some((value) => value === priority) ? { priority: priority as TaskPriority } : {}),
    ...(taskOrderings.some((value) => value === ordering) ? { ordering: ordering as TaskOrdering } : { ordering: '-created_at' }),
    ...(parent && isUuid(parent) ? { parent_id: parent } : search.get('root_only') === 'true' ? { root_only: true } : {}),
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
  return <span className={overdue ? 'task-overdue' : ''}><time dateTime={task.deadline}>{new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(task.deadline))}</time>{overdue && <small>Quá hạn</small>}</span>
}
function TaskRows({ tasks, base }: { tasks: Task[]; base: string }) {
  return <ul className="task-list" aria-label="Danh sách công việc">{tasks.map((task) => <li key={task.id} className="task-row"><div className="task-row__main"><span className="eyebrow">{task.parent_id ? 'CÔNG VIỆC CON' : 'CÔNG VIỆC GỐC'}</span><Link to={`${base}/${task.id}`} className="task-title">{task.title}</Link>{task.description && <p className="task-preview">{task.description}</p>}<span className="task-updated">Cập nhật {dateLabel(task.updated_at)}</span><span className="task-assignee">{task.active_assignment?.profile_membership_id ? `Thành viên ${task.active_assignment.profile_membership_id}` : 'Chưa phân công'}</span></div><TaskPills task={task} /><div className="task-row__deadline"><Deadline task={task} /></div><Link to={`${base}/${task.id}`} className="task-open" aria-label={`Xem ${task.title}`}><ArrowRightIcon aria-hidden="true" /></Link></li>)}</ul>
}
function TaskFiltersForm({ initial, onApply }: { initial: TaskFilters; onApply: (search: URLSearchParams) => void }) {
  const [status, setStatus] = useState(initial.status || '')
  const [priority, setPriority] = useState(initial.priority || '')
  const [structure, setStructure] = useState(initial.parent_id ? 'parent' : initial.root_only ? 'root' : 'all')
  const [ordering, setOrdering] = useState<string>(initial.ordering || '-created_at')
  const [after, setAfter] = useState(initial.deadline_after?.slice(0, 10) || '')
  const [before, setBefore] = useState(initial.deadline_before?.slice(0, 10) || '')
  const [error, setError] = useState('')
  return <form className="task-filters" onSubmit={(event) => {
    event.preventDefault()
    if ((after && !/^\d{4}-\d\d-\d\d$/.test(after)) || (before && !/^\d{4}-\d\d-\d\d$/.test(before)) || (after && before && after > before)) { setError('Khoảng thời hạn chưa hợp lệ. Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.'); return }
    const query = new URLSearchParams()
    if (status) query.set('status', status)
    if (priority) query.set('priority', priority)
    if (structure === 'root') query.set('root_only', 'true')
    if (structure === 'parent' && initial.parent_id) query.set('parent_id', initial.parent_id)
    query.set('ordering', ordering)
    if (after) query.set('deadline_after', `${after}T00:00:00Z`)
    if (before) query.set('deadline_before', `${before}T23:59:59.999999Z`)
    setError(''); onApply(query)
  }}>
    <label>Trạng thái<select aria-label="Trạng thái" className="input" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Tất cả trạng thái</option>{taskStatuses.map((value) => <option key={value} value={value}>{statusLabels[value]}</option>)}</select></label>
    <label>Mức ưu tiên<select aria-label="Mức ưu tiên" className="input" value={priority} onChange={(e) => setPriority(e.target.value)}><option value="">Tất cả mức ưu tiên</option>{taskPriorities.map((value) => <option key={value} value={value}>{priorityLabels[value]}</option>)}</select></label>
    <label>Cấu trúc<select aria-label="Cấu trúc" className="input" value={structure} onChange={(e) => setStructure(e.target.value)}><option value="all">Tất cả cấp</option><option value="root">Chỉ công việc gốc</option>{initial.parent_id && <option value="parent">Con của công việc đã chọn</option>}</select></label>
    <label>Sắp xếp<select aria-label="Sắp xếp" className="input" value={ordering} onChange={(e) => setOrdering(e.target.value)}>{taskOrderings.map((value) => <option key={value} value={value}>{orderingLabels[value]}</option>)}</select></label>
    <label>Thời hạn từ ngày (UTC)<input className="input" type="date" value={after} max="9999-12-31" onChange={(e) => setAfter(e.target.value)} /></label>
    <label>Thời hạn đến ngày (UTC)<input className="input" type="date" value={before} max="9999-12-31" onChange={(e) => setBefore(e.target.value)} /></label>
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
  return <><PageHeader eyebrow={context.workspace.data.name} title="Công việc" description="Giữ công việc rõ ràng, để cả nhóm cùng tiến về phía trước." back={{ to: base, label: 'Thông tin không gian' }} action={<TaskCreate profileId={profileId} workspaceId={workspaceId} canCreate={context.active && context.capabilities.data?.manageTasks} onCreate={(input, signal) => workApi.createTask(profileId, workspaceId, input, signal)} onSaved={() => { context.invalidate(); setNotice('Đã tạo công việc. Bạn có thể mở chi tiết để phân công.'); }} onDenied={context.denied} />} />
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
  const client = useQueryClient()
  const [page, setPage] = useState(1), [memberPage, setMemberPage] = useState(1), [notice, setNotice] = useState(''), [membersOpened, setMembersOpened] = useState(false)
  const task = useQuery({ queryKey: workKeys.task(profileId, workspaceId, taskId), queryFn: ({ signal }) => workApi.task(profileId, workspaceId, taskId, signal), enabled: context.workspace.isSuccess })
  const children = useQuery({ queryKey: workKeys.subtasks(profileId, workspaceId, taskId, {}, page), queryFn: ({ signal }) => workApi.subtasks(profileId, workspaceId, taskId, {}, page, signal), enabled: task.isSuccess })
  const ancestors = useQuery({ queryKey: [...workKeys.task(profileId, workspaceId, taskId), 'ancestors', task.data?.parent_id], queryFn: async ({ signal }) => {
    const items: Task[] = [], seen = new Set([taskId]); let parent = task.data?.parent_id
    while (parent && items.length < 3) {
      if (seen.has(parent)) throw new Error('Invalid hierarchy')
      seen.add(parent)
      const item: Task = await client.fetchQuery({ queryKey: workKeys.task(profileId, workspaceId, parent), queryFn: () => workApi.task(profileId, workspaceId, parent || '', signal), staleTime: 0 })
      items.unshift(item); parent = item.parent_id
    }
    if (parent) throw new Error('Invalid hierarchy depth')
    return items
  }, enabled: task.isSuccess })
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
    <nav className="task-breadcrumbs" aria-label="Phân cấp công việc"><Link to={base}>Tất cả công việc</Link>{ancestors.data?.map((parent) => <Link key={parent.id} to={`${base}/${parent.id}`}>{parent.title}</Link>)}<span aria-current="page">{value.parent_id ? `Công việc con · Cấp ${ancestors.data?.length ?? '…'}/3` : 'Công việc gốc · Cấp 0'}</span></nav>
    {ancestors.isError && <Alert kind="error">Chưa thể xác minh đầy đủ phân cấp. Tạm thời không thể thêm cấp con.</Alert>}
    <div className="work-actions"><TaskStart key={`${taskId}:${task.dataUpdatedAt}`} profileId={profileId} workspaceId={workspaceId} task={value} active={context.active && task.isSuccess} onStart={(signal) => workApi.startTask(profileId, workspaceId, taskId, signal)} onSaved={() => { context.invalidate(); setNotice('Đã bắt đầu công việc.'); }} onDenied={context.denied} /><TaskEdit profileId={profileId} workspaceId={workspaceId} task={value} canEdit={canManage} onUpdate={(input, signal) => workApi.updateTask(profileId, workspaceId, taskId, input, signal)} onSaved={saved} onDenied={context.denied} /><TaskAssign profileId={profileId} workspaceId={workspaceId} task={value} canAssign={canManage && ['PENDING', 'ASSIGNED', 'WORKING'].includes(value.status)} onOpen={() => setMembersOpened(true)} members={members.data} membersPage={memberPage} membersLoading={members.isPending} membersError={members.error} onMembersPageChange={setMemberPage} onRetryMembers={() => void members.refetch()} onAssign={(input, signal) => workApi.assignTask(profileId, workspaceId, taskId, input, signal)} onSaved={saved} onDenied={context.denied} /></div>
    <div className="workspace-detail-grid"><Card className="workspace-about"><h2>Nội dung công việc</h2><p className="preserve-text">{value.description || 'Công việc chưa có mô tả.'}</p><p className="read-note">{value.parent_id ? 'Công việc con có quy trình thực hiện và duyệt riêng.' : 'Công việc gốc có quy trình thực hiện và duyệt riêng.'} Thời hạn và ưu tiên không tự áp dụng sang công việc con.</p></Card><Card className="workspace-facts"><h2>Thông tin công việc</h2><dl><div><dt>Thời hạn · {Intl.DateTimeFormat().resolvedOptions().timeZone}</dt><dd><Deadline task={value} /></dd></div><div><dt>Phân công</dt><dd className="break-code">{value.active_assignment?.profile_membership_id || 'Chưa phân công'}</dd></div><div><dt>Ngày tạo</dt><dd>{dateLabel(value.created_at)}</dd></div><div><dt>Cập nhật gần nhất</dt><dd>{dateLabel(value.updated_at)}</dd></div><div><dt>Kỳ làm việc</dt><dd>{periodLabel(context.workspace.data.period)}</dd></div></dl></Card></div>
    <section className="section-block"><div className="section-heading"><div><p className="eyebrow">TỪNG BƯỚC NHỎ, CÙNG TIẾN XA</p><h2>Công việc con</h2><Link className="text-link" to={`${base}?parent_id=${taskId}`}>Lọc danh sách con trực tiếp</Link></div><TaskCreate profileId={profileId} workspaceId={workspaceId} canCreate={canManage && ancestors.isSuccess && ancestors.data.length < 3} fixedParentId={taskId} onCreate={(input, signal) => workApi.createTask(profileId, workspaceId, input, signal)} onSaved={() => { saved(); setPage(1) }} onDenied={context.denied} /></div>
      {ancestors.isSuccess && ancestors.data.length === 3 && <p className="read-note">Đã đến giới hạn 3 cấp con. Không thể thêm cấp sâu hơn.</p>}
      {children.isPending ? <PageSkeleton /> : children.isError ? <ErrorState error={children.error} onRetry={() => void children.refetch()} /> : <>{children.data.results.length ? <TaskRows tasks={children.data.results} base={base} /> : <EmptyState title="Chưa có công việc con" description="Chia nhỏ một mục tiêu thành những bước có thể thực hiện. Mỗi công việc con được quản lý độc lập." />}<Pagination page={page} count={children.data.count} onPageChange={setPage} /></>}
    </section><p className="read-note"><ListChecksIcon aria-hidden="true" />Mỗi công việc có sản phẩm và đánh giá riêng, theo quy trình được kiểm tra trên máy chủ.</p>
    {currentUserId && <TaskCollaboration profileId={profileId} workspaceId={workspaceId} task={value} currentUserId={currentUserId} active={context.active && task.isSuccess} canManage={canManage} onChanged={() => context.invalidate()} onDenied={context.denied} />}
  </>
}

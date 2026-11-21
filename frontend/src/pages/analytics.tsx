import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router'
import { ChartBarIcon, CheckCircleIcon, ClockIcon, ListChecksIcon, UserMinusIcon, WarningCircleIcon } from '@phosphor-icons/react'
import { Alert, Button, Card, EmptyState, ErrorState, PageSkeleton, Pagination } from '../components/ui'
import { PageHeader } from '../components/page'
import { useAuth } from '../features/auth/AuthProvider'
import { ApprovalChart, StatusChart } from '../features/analytics/AnalyticsCharts'
import { analyticsApi, analyticsAuthority, analyticsKeys, currentHcmMonth, employeeOrderings, formatAnalyticsVnd, isAnalyticsDate, monthDateRange } from '../services/api/analytics'
import type { AnalyticsEmployee, AnalyticsFilters, AnalyticsSummary, EmployeeOrdering } from '../services/api/analytics'
import { queryKeys, tenantApi } from '../services/api/queries'
import { isApiError } from '../services/api/client'
import { statusLabels } from './tasks'
import './analytics.css'

const countLabel = (value: number) => value.toLocaleString('vi-VN')
const employeeName = (row: AnalyticsEmployee) => row.is_available && row.display_name ? row.display_name : 'Thành viên không còn khả dụng'
const orderingLabels: Record<EmployeeOrdering, string> = { '-active_tasks': 'Đang nhận: nhiều nhất', active_tasks: 'Đang nhận: ít nhất', '-approved_tasks': 'Nghiệm thu: nhiều nhất', approved_tasks: 'Nghiệm thu: ít nhất', '-approved_value': 'Giá trị nghiệm thu: cao nhất', approved_value: 'Giá trị nghiệm thu: thấp nhất' }

export function AnalyticsPage() {
  const { user } = useAuth()
  const [search, setSearch] = useSearchParams(), [profilePage, setProfilePage] = useState(1)
  const profiles = useQuery({ queryKey: queryKeys.profiles(profilePage), queryFn: ({ signal }) => tenantApi.profiles(profilePage, signal) })
  const profileId = search.get('profile_id') || profiles.data?.results[0]?.id || ''
  const selected = useQuery({ queryKey: queryKeys.profile(profileId), queryFn: ({ signal }) => tenantApi.profile(profileId, signal), enabled: !!profileId && profiles.isSuccess })
  return <>
    <PageHeader eyebrow="GÓC NHÌN CÔNG VIỆC" title="Thống kê" description="Hiệu suất công việc và thù lao của tổ chức" />
    {profiles.isPending ? <PageSkeleton /> : profiles.isError ? <ErrorState error={profiles.error} onRetry={() => void profiles.refetch()} /> : !profiles.data.count ? <EmptyState title="Chưa có tổ chức để thống kê" description="Tạo hoặc tham gia một tổ chức để bắt đầu theo dõi công việc." action={<Link className="button button--primary" to="/profiles">Xem tổ chức</Link>} /> : <>
      <Card className="analytics-profile-filter"><label className="field">Chọn tổ chức<select className="input" value={profileId} onChange={(event) => { setSearch({ profile_id: event.target.value }) }}>
        {selected.data && !profiles.data.results.some((row) => row.id === profileId) && <option value={profileId}>{selected.data.name}</option>}{profiles.data.results.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
      </select></label>{profiles.data.count > 20 && <Pagination label="Phân trang tổ chức" page={profilePage} count={profiles.data.count} onPageChange={setProfilePage} />}</Card>
      {selected.isError ? <ErrorState error={selected.error} /> : !selected.isSuccess ? <PageSkeleton /> : <ScopedAnalytics key={`${user?.id}:${profileId}`} profileId={profileId} />}
    </>}
  </>
}

function ScopedAnalytics({ profileId }: { profileId: string }) {
  const cache = useQueryClient()
  const [search, setSearch] = useSearchParams(), [workspacePage, setWorkspacePage] = useState(1)
  const defaults = monthDateRange(currentHcmMonth())
  const from = search.get('from') ?? defaults.from, to = search.get('to') ?? defaults.to, workspaceId = search.get('workspace_id') ?? ''
  const valid = isAnalyticsDate(from) && isAnalyticsDate(to) && from <= to
  const filters: AnalyticsFilters = { from, to, ...(workspaceId ? { workspace_id: workspaceId } : {}) }
  const signature = `${workspaceId}|${from}|${to}`
  const [denial, setDenial] = useState<{ signature: string; error: unknown } | null>(null)
  const activeDenial = denial?.signature === signature ? denial : null
  const onDenied = useCallback((error: unknown) => {
    if (isApiError(error) && [403, 404].includes(error.status)) setDenial((previous) => previous?.signature === signature && previous.error === error ? previous : { signature, error })
  }, [signature])
  const workspaces = useQuery({ queryKey: queryKeys.workspaces(profileId, workspacePage), queryFn: ({ signal }) => tenantApi.workspaces(profileId, workspacePage, signal) })
  const selectedWorkspace = useQuery({ queryKey: queryKeys.workspace(profileId, workspaceId), queryFn: ({ signal }) => tenantApi.workspace(profileId, workspaceId, signal), enabled: !!workspaceId })
  const summary = useQuery({ queryKey: analyticsKeys.summary(profileId, filters), queryFn: ({ signal }) => analyticsApi.summary(profileId, filters, signal), enabled: valid && !activeDenial })
  const authority = summary.isSuccess ? analyticsAuthority(summary.data) : 'unresolved'
  const previousAuthority = useRef<string | null>(null)
  useEffect(() => { if (summary.isError) onDenied(summary.error) }, [summary.isError, summary.error, onDenied])
  useEffect(() => {
    if (!activeDenial) return
    // The observer is disabled before removal, so a denied payload cannot be
    // retained privately or trigger a remove/refetch/403 loop.
    void cache.cancelQueries({ queryKey: analyticsKeys.profile(profileId) }).then(() => cache.removeQueries({ queryKey: analyticsKeys.profile(profileId) }))
  }, [activeDenial, cache, profileId])
  useEffect(() => {
    if (!summary.isSuccess) return
    const previous = previousAuthority.current; previousAuthority.current = authority
    if (previous && previous !== authority) {
      const stale = { predicate: (query: { queryKey: readonly unknown[] }) => query.queryKey[0] === 'work' && query.queryKey[1] === profileId.toLowerCase() && query.queryKey[2] === 'analytics' && ['employees', 'employee'].includes(String(query.queryKey[3])) && query.queryKey[4] !== authority }
      void cache.cancelQueries(stale).then(() => cache.removeQueries(stale))
    }
  }, [summary.isSuccess, authority, cache, profileId])
  const unavailableWorkspace = !!workspaceId && !selectedWorkspace.isSuccess
  return <div className="analytics-page">
    <Card className="analytics-filter-card"><div className="analytics-workspace-filter"><label className="field">Chọn Workspace<select className="input" value={workspaceId} disabled={!workspaces.isSuccess} onChange={(event) => { const next = new URLSearchParams(search); next.set('profile_id', profileId); if (event.target.value) next.set('workspace_id', event.target.value); else next.delete('workspace_id'); setSearch(next) }}><option value="">Tất cả Workspace</option>
      {selectedWorkspace.data && !workspaces.data?.results.some((row) => row.id === workspaceId) && <option value={workspaceId}>{selectedWorkspace.data.name}</option>}{workspaces.data?.results.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
    </select></label>{workspaces.isError && <ErrorState error={workspaces.error} onRetry={() => void workspaces.refetch()} />}{workspaces.data && workspaces.data.count > 20 && <Pagination label="Phân trang Workspace" page={workspacePage} count={workspaces.data.count} onPageChange={setWorkspacePage} />}</div>
      <TimeFilters key={`${from}:${to}`} from={from} to={to} onApply={(range) => { const next = new URLSearchParams(search); next.set('profile_id', profileId); next.set('from', range.from); next.set('to', range.to); setSearch(next) }} />
    </Card>
    {!valid ? <Alert kind="error">Khoảng ngày trong đường dẫn chưa hợp lệ. Chọn lại khoảng ngày bắt đầu và kết thúc.</Alert> : selectedWorkspace.isError ? <ErrorState error={selectedWorkspace.error} /> : activeDenial ? <ErrorState error={activeDenial.error} onRetry={() => setDenial(null)} /> : summary.isError ? <ErrorState error={summary.error} onRetry={() => void summary.refetch()} /> : !summary.isSuccess || unavailableWorkspace ? <PageSkeleton label="Đang tính thống kê từ dữ liệu thực…" /> : <AnalyticsContent key={`${profileId}:${workspaceId}:${from}:${to}:${authority}`} profileId={profileId} filters={filters} summary={summary.data} onDenied={onDenied} />}
  </div>
}

function TimeFilters({ from, to, onApply }: { from: string; to: string; onApply: (range: { from: string; to: string }) => void }) {
  const fullMonth = isAnalyticsDate(from) && from.endsWith('-01') && monthDateRange(from.slice(0, 7)).to === to
  const [mode, setMode] = useState<'month' | 'range'>(fullMonth ? 'month' : 'range')
  const [month, setMonth] = useState(isAnalyticsDate(from) ? from.slice(0, 7) : currentHcmMonth())
  const [start, setStart] = useState(from), [end, setEnd] = useState(to), [error, setError] = useState('')
  return <form className="analytics-time-filter" noValidate onSubmit={(event) => { event.preventDefault(); let range: { from: string; to: string }; try { range = mode === 'month' ? monthDateRange(month) : { from: start, to: end } } catch { setError('Chọn tháng và năm hợp lệ.'); return }; if (!isAnalyticsDate(range.from) || !isAnalyticsDate(range.to) || range.from > range.to) { setError('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc hợp lệ.'); return }; if (Date.parse(`${range.to}T00:00:00Z`) - Date.parse(`${range.from}T00:00:00Z`) >= 366 * 86400000) { setError('Chọn khoảng thời gian tối đa 366 ngày, bao gồm cả hai đầu.'); return }; setError(''); onApply(range) }}>
    <label className="field">Chọn thời gian<select className="input" value={mode} onChange={(event) => setMode(event.target.value as 'month' | 'range')}><option value="month">Theo tháng</option><option value="range">Khoảng ngày</option></select></label>
    {mode === 'month' ? <label className="field">Tháng / năm<input className="input" type="month" value={month} onChange={(event) => setMonth(event.target.value)} /></label> : <><label className="field">Từ ngày<input className="input" type="date" value={start} onChange={(event) => setStart(event.target.value)} /></label><label className="field">Đến ngày<input className="input" type="date" value={end} onChange={(event) => setEnd(event.target.value)} /></label></>}
    <Button type="submit" variant="secondary">Áp dụng thời gian</Button><p className="field__hint">Ngày bao gồm cả hai đầu, theo Asia/Ho_Chi_Minh. Tối đa 366 ngày mỗi lần.</p>{error && <Alert kind="error">{error}</Alert>}
  </form>
}

function AnalyticsContent({ profileId, filters, summary, onDenied }: { profileId: string; filters: AnalyticsFilters; summary: AnalyticsSummary; onDenied: (error: unknown) => void }) {
  const self = summary.scope.mode === 'self'
  const cards = [
    { key: 'total_tasks', label: 'Tổng Task', Icon: ListChecksIcon, hint: 'Task tạo trong khoảng ngày đã chọn, gồm cả Task con.' },
    { key: 'approved_tasks', label: 'Đã nghiệm thu', Icon: CheckCircleIcon, hint: 'Task tạo trong kỳ, đang Hoàn thành và có Review phê duyệt được đối chiếu.' },
    { key: 'working_tasks', label: 'Đang thực hiện', Icon: ChartBarIcon, hint: 'Task tạo trong kỳ, trạng thái WORKING hiện tại.' },
    { key: 'review_tasks', label: 'Chờ duyệt', Icon: ClockIcon, hint: 'Task tạo trong kỳ, trạng thái REVIEW hiện tại.' },
    { key: 'overdue_tasks', label: 'Quá hạn', Icon: WarningCircleIcon, hint: 'Task tạo trong kỳ, quá deadline hiện tại và chưa kết thúc; có thể trùng nhóm khác.' },
    { key: 'unassigned_tasks', label: 'Chưa phân công', Icon: UserMinusIcon, hint: 'Task tạo trong kỳ, chưa kết thúc và hiện không có phân công hoạt động.' },
  ] as const
  return <>
    {self && <Alert title="Thống kê của tôi">Chỉ gồm công việc và thù lao bạn được phép xem của chính mình. Chọn Workspace bạn quản lý để xem thống kê quản lý trong phạm vi đó.</Alert>}
    <div className="analytics-scope-note"><p><strong>KPI và phân bổ:</strong> Task tạo từ {filters.from} đến {filters.to}; trạng thái và phân công tại thời điểm xem.</p><p><strong>Nghiệm thu theo tháng và giá trị nghiệm thu:</strong> sự kiện Review phê duyệt trong kỳ, không giới hạn ngày tạo Task. Các nhóm KPI có thể chồng lấp, không cộng cả sáu thẻ thành tổng.</p></div>
    <section className="analytics-kpis" aria-label="Sáu chỉ số công việc">{cards.map(({ key, label, Icon, hint }) => <Card className={`analytics-kpi${key === 'overdue_tasks' ? ' analytics-kpi--warning' : ''}`} key={key}><div className="analytics-kpi-label"><Icon aria-hidden="true" /><h2>{label}</h2></div><strong className="analytics-kpi-number">{countLabel(summary.kpis[key])}</strong><p>{hint}</p></Card>)}</section>
    {summary.kpis.unverified_completed_tasks > 0 && <Alert>{countLabel(summary.kpis.unverified_completed_tasks)} Task có trạng thái Hoàn thành nhưng chưa đối chiếu được Review phê duyệt; không tính vào KPI đã nghiệm thu.</Alert>}
    {summary.kpis.unattributed_approved_tasks > 0 && <Alert>{countLabel(summary.kpis.unattributed_approved_tasks)} lượt nghiệm thu chưa đối chiếu được thành viên trong tổ chức. Tổng nghiệm thu có thể chưa được phân bổ đầy đủ vào bảng nhân viên; không suy đoán người hoàn thành.</Alert>}
    {summary.capabilities.can_view_financial_totals && summary.finance && <><FinanceSection summary={summary} self={self} /><p className="read-note">Giá trị đã nghiệm thu giữ lại lịch sử của công việc hoặc không gian đã chuyển vào Thùng rác; số lượng công việc đang hoạt động không bao gồm các mục đó.</p></>}
    <section className="analytics-charts" aria-label="Biểu đồ công việc"><StatusChart rows={summary.distribution} total={summary.kpis.total_tasks} /><ApprovalChart rows={summary.approval_trend} /></section>
    <Employees profileId={profileId} filters={filters} self={self} showFinance={summary.capabilities.can_view_financial_totals} authority={analyticsAuthority(summary)} onDenied={onDenied} />
  </>
}

function FinanceSection({ summary, self }: { summary: AnalyticsSummary; self: boolean }) {
  const finance = summary.finance
  if (!finance) return null
  return <section className="analytics-finance" aria-label={self ? 'Thù lao dự kiến của tôi' : 'Tài chính công việc'}><div><p className="eyebrow">{self ? 'TRONG PHẠM VI CỦA BẠN' : 'TÀI CHÍNH CÔNG VIỆC'}</p><h2>{self ? 'Thù lao dự kiến của tôi' : 'Thù lao dự kiến'}</h2><p>Giá trị công việc, không phải xác nhận đã thanh toán.</p></div><div className="analytics-finance-values"><div><h3>Tổng thù lao dự kiến</h3><strong>{formatAnalyticsVnd(finance.estimated_total_vnd)}</strong><p>Task tạo trong kỳ, giá trị hiện tại.</p><small>Số Task chưa nhập thù lao: {countLabel(finance.estimated_unpriced_tasks)}</small></div><div><h3>Giá trị đã nghiệm thu</h3><strong>{formatAnalyticsVnd(finance.approved_total_vnd)}</strong><p>Theo sự kiện nghiệm thu trong kỳ và giá trị được ghi nhận khi phê duyệt.</p><small>Chưa nhập tại lúc nghiệm thu: {countLabel(finance.approved_unpriced_tasks)}</small></div></div>{finance.approved_unknown_tasks > 0 && <Alert>{countLabel(finance.approved_unknown_tasks)} lượt nghiệm thu cũ chưa có snapshot thù lao đáng tin cậy. Giá trị trên chưa bao gồm các lượt này; không dùng giá hiện tại để suy đoán lịch sử.</Alert>}</section>
}

function Employees({ profileId, filters, self, showFinance, authority, onDenied }: { profileId: string; filters: AnalyticsFilters; self: boolean; showFinance: boolean; authority: string; onDenied: (error: unknown) => void }) {
  const [search, setSearch] = useState(''), [submittedSearch, setSubmittedSearch] = useState(''), [ordering, setOrdering] = useState<EmployeeOrdering>('-active_tasks'), [page, setPage] = useState(1), [selected, setSelected] = useState('')
  const rows = useQuery({ queryKey: analyticsKeys.employees(profileId, filters, submittedSearch, ordering, page, authority), queryFn: ({ signal }) => analyticsApi.employees(profileId, filters, submittedSearch, ordering, page, signal) })
  useEffect(() => { if (rows.isError) onDenied(rows.error) }, [rows.isError, rows.error, onDenied])
  return <section className="analytics-employees" aria-label={self ? 'Hiệu suất của tôi' : 'Hiệu suất nhân viên'}><div className="section-heading"><div><p className="eyebrow">{self ? 'CÔNG VIỆC CỦA BẠN' : 'GÓC NHÌN NHÂN VIÊN'}</p><h2>{self ? 'Hiệu suất của tôi' : 'Hiệu suất nhân viên'}</h2><p className="field__hint">Đang nhận: phân công hiện tại trên Task tạo trong kỳ. Đã nghiệm thu: người nộp phiên bản được duyệt trong kỳ, không lấy assignee hiện tại để thay lịch sử.</p></div></div>
    <Card><form className="analytics-employee-controls" onSubmit={(event) => { event.preventDefault(); setSubmittedSearch(search.trim()); setPage(1); setSelected('') }}><label className="field">Tìm nhân viên<input className="input" type="search" value={search} maxLength={100} onChange={(event) => setSearch(event.target.value)} placeholder="Họ tên hoặc username" /></label><Button type="submit" variant="secondary">Tìm kiếm</Button><label className="field">Sắp xếp nhân viên<select className="input" value={ordering} onChange={(event) => { setOrdering(event.target.value as EmployeeOrdering); setPage(1); setSelected('') }}>{employeeOrderings.filter((value) => showFinance || !value.includes('value')).map((value) => <option key={value} value={value}>{orderingLabels[value]}</option>)}</select></label></form>
      {rows.isError ? <ErrorState error={rows.error} onRetry={() => void rows.refetch()} /> : !rows.isSuccess ? <PageSkeleton label="Đang tải hiệu suất nhân viên…" /> : !rows.data.results.length ? <EmptyState title="Chưa có nhân viên phù hợp" description="Thử chọn phạm vi khác hoặc xóa từ khóa tìm kiếm." /> : <><div className="analytics-table-wrap"><table className="analytics-table"><caption className="sr-only">{self ? 'Công việc trong phạm vi của tôi' : 'Hiệu suất nhân viên trong phạm vi đã chọn'}</caption><thead><tr><th scope="col">Nhân viên</th><th scope="col" aria-sort={ordering.includes('active_tasks') ? ordering.startsWith('-') ? 'descending' : 'ascending' : 'none'}>Đang nhận</th><th scope="col" aria-sort={ordering.includes('approved_tasks') ? ordering.startsWith('-') ? 'descending' : 'ascending' : 'none'}>Đã nghiệm thu</th><th scope="col">Quá hạn</th>{showFinance && <><th scope="col">Thù lao dự kiến đang nhận</th><th scope="col" aria-sort={ordering.includes('approved_value') ? ordering.startsWith('-') ? 'descending' : 'ascending' : 'none'}>Giá trị nghiệm thu</th></>}<th scope="col"><span className="sr-only">Chi tiết</span></th></tr></thead><tbody>{rows.data.results.map((row) => <tr key={row.id}><th scope="row"><span className="analytics-person"><span className="avatar" aria-hidden="true">{Array.from(employeeName(row))[0]?.toLocaleUpperCase('vi-VN')}</span><span>{employeeName(row)}</span></span></th><td data-label="Đang nhận">{countLabel(row.active_tasks)}</td><td data-label="Đã nghiệm thu">{countLabel(row.approved_tasks)}</td><td data-label="Quá hạn">{countLabel(row.overdue_tasks)}</td>{showFinance && <><td data-label="Thù lao dự kiến đang nhận" className="analytics-money">{row.finance ? <>{formatAnalyticsVnd(row.finance.active_total_vnd)}{row.finance.active_unpriced_tasks > 0 && <small>{countLabel(row.finance.active_unpriced_tasks)} Task chưa nhập thù lao.</small>}</> : 'Không có quyền xem'}</td><td data-label="Giá trị nghiệm thu" className="analytics-money">{row.finance ? <>{formatAnalyticsVnd(row.finance.approved_total_vnd)}{row.finance.approved_unknown_tasks > 0 && <small>Chưa gồm {countLabel(row.finance.approved_unknown_tasks)} lượt thiếu snapshot.</small>}</> : 'Không có quyền xem'}</td></>}<td><Button variant="ghost" aria-label={`Xem chi tiết ${employeeName(row)}`} onClick={() => setSelected(row.id)}>Xem chi tiết</Button></td></tr>)}</tbody></table></div><Pagination page={page} count={rows.data.count} onPageChange={(next) => { setPage(next); setSelected('') }} /></>}
    </Card>{selected && !rows.isError && <EmployeePanel key={selected} profileId={profileId} membershipId={selected} filters={filters} showFinance={showFinance} authority={authority} onDenied={onDenied} onClose={() => setSelected('')} />}
  </section>
}

function EmployeePanel({ profileId, membershipId, filters, showFinance, authority, onDenied, onClose }: { profileId: string; membershipId: string; filters: AnalyticsFilters; showFinance: boolean; authority: string; onDenied: (error: unknown) => void; onClose: () => void }) {
  const [page, setPage] = useState(1), heading = useRef<HTMLHeadingElement>(null)
  const detail = useQuery({ queryKey: analyticsKeys.employee(profileId, filters, membershipId, page, authority), queryFn: ({ signal }) => analyticsApi.employee(profileId, membershipId, filters, page, signal) })
  useEffect(() => { if (detail.isError) onDenied(detail.error) }, [detail.isError, detail.error, onDenied])
  useEffect(() => { if (detail.isSuccess) heading.current?.focus() }, [detail.isSuccess])
  if (detail.isError) return <Card><ErrorState error={detail.error} /><Button variant="secondary" onClick={onClose}>Đóng chi tiết</Button></Card>
  if (!detail.isSuccess) return <PageSkeleton label="Đang tải chi tiết nhân viên…" />
  const row = detail.data.employee
  return <Card className="analytics-employee-detail"><div className="section-heading"><h2 ref={heading} tabIndex={-1}>{employeeName(row)}</h2><Button variant="secondary" onClick={onClose}>Đóng chi tiết</Button></div><dl className="analytics-detail-stats"><div><dt>Task đang nhận</dt><dd>{countLabel(row.active_tasks)}</dd></div><div><dt>Task đã nghiệm thu</dt><dd>{countLabel(row.approved_tasks)}</dd></div><div><dt>Task quá hạn</dt><dd>{countLabel(row.overdue_tasks)}</dd></div>{showFinance && row.finance && <><div><dt>Giá trị đã nghiệm thu</dt><dd>{formatAnalyticsVnd(row.finance.approved_total_vnd)}</dd></div><div><dt>Giá trị Task đang phụ trách</dt><dd>{formatAnalyticsVnd(row.finance.active_total_vnd)}</dd></div></>}</dl>{showFinance && row.finance && row.finance.approved_unknown_tasks > 0 && <Alert>Còn {countLabel(row.finance.approved_unknown_tasks)} lượt nghiệm thu chưa xác định được thù lao lịch sử.</Alert>}
    {detail.data.results.length ? <ul className="analytics-employee-tasks">{detail.data.results.map((task) => <li key={task.id}><Link className="text-link" to={`/profiles/${profileId}/workspaces/${task.workspace_id}/tasks/${task.id}`}>{task.title}</Link><span>{statusLabels[task.status]}</span><small>{task.relation === 'current' ? 'Đang phụ trách' : task.relation === 'approved' ? 'Được ghi nhận nghiệm thu' : 'Đang phụ trách và đã nghiệm thu'}</small></li>)}</ul> : <p>Chưa có Task liên quan trong phạm vi này.</p>}<Pagination page={page} count={detail.data.count} onPageChange={setPage} />
  </Card>
}

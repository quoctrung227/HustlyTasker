import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppLayout } from '../layouts/AppLayout'
import { ApiError } from '../services/api/client'
import { analyticsApi, analyticsAuthority, analyticsKeys, formatAnalyticsVnd } from '../services/api/analytics'
import { tenantApi } from '../services/api/queries'
import { analyticsEmployee as employee, analyticsFilters as filters, analyticsMemberId as memberId, analyticsOtherId as otherId, analyticsProfileId as profileId, analyticsSummary as summary, analyticsTimestamp as timestamp, analyticsWorkspaceId as workspaceId } from '../test/analytics-fixtures'
import { AnalyticsPage } from './analytics'

vi.mock('../features/auth/AuthProvider', () => ({ useAuth: () => ({ user: { id: '00000000-0000-4000-8000-000000000399', username: 'synthetic_actor' }, signOut: vi.fn() }) }))
vi.mock('../features/notifications/NotificationHub', () => ({ NotificationMenu: () => null }))
const profile = { id: profileId, name: 'Tổ chức được phép', status: 'ACTIVE' as const, created_at: timestamp, updated_at: timestamp }
const workspace = { id: workspaceId, profile_id: profileId, name: 'Workspace được phép', description: null, period: '2026-11-01', status: 'ACTIVE' as const, created_at: timestamp, updated_at: timestamp }
const page = <T,>(results: T[], count = results.length) => ({ count, next: null, previous: null, results })
const task = { id: otherId, workspace_id: workspaceId, title: 'Task có thể mở', status: 'WORKING' as const, deadline: null, relation: 'current' as const }
beforeEach(() => {
  vi.restoreAllMocks()
  vi.spyOn(tenantApi, 'profiles').mockResolvedValue(page([profile, { ...profile, id: otherId, name: 'Tổ chức khác' }]))
  vi.spyOn(tenantApi, 'profile').mockImplementation(async (id) => ({ ...profile, id }))
  vi.spyOn(tenantApi, 'workspaces').mockResolvedValue(page([workspace]))
  vi.spyOn(tenantApi, 'workspace').mockResolvedValue(workspace)
  vi.spyOn(analyticsApi, 'summary').mockImplementation(async (id, value) => ({ ...summary, scope: { ...summary.scope, profile_id: id, workspace_id: value.workspace_id ?? null, from: value.from, to: value.to } }))
  vi.spyOn(analyticsApi, 'employees').mockResolvedValue(page([employee]))
  vi.spyOn(analyticsApi, 'employee').mockResolvedValue({ ...page([task]), employee })
})
function setup(path = `/analytics?profile_id=${profileId}&from=${filters.from}&to=${filters.to}`) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity }, mutations: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><Routes><Route path="/analytics" element={<AnalyticsPage />} /></Routes></MemoryRouter></QueryClientProvider>)
  return client
}

describe('approved analytics dashboard layout', () => {
  it('uses real server values in all five areas and distinguishes current cohort from historical approval events', async () => {
    setup()
    expect(await screen.findByRole('heading', { name: 'Hiệu suất nhân viên' })).toBeVisible()
    const kpis = screen.getByRole('region', { name: 'Sáu chỉ số công việc' })
    for (const label of ['Tổng Task', 'Đã nghiệm thu', 'Đang thực hiện', 'Chờ duyệt', 'Quá hạn', 'Chưa phân công']) expect(within(kpis).getByRole('heading', { name: label })).toBeVisible()
    expect(screen.getByText('1.999.999.999.999.999.998 ₫')).toBeVisible()
    expect(screen.getByText(/lượt nghiệm thu cũ chưa có snapshot/)).toBeVisible()
    expect(screen.getByText(/trạng thái Hoàn thành nhưng chưa đối chiếu/)).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Phân bổ trạng thái Task' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Task được nghiệm thu theo tháng' })).toBeVisible()
    expect(screen.getByText(/sự kiện Review phê duyệt trong kỳ, không giới hạn ngày tạo Task/)).toBeVisible()
    expect(screen.queryByText('Tiền đã nhận')).not.toBeInTheDocument()
    const employees = await screen.findByRole('table', { name: 'Hiệu suất nhân viên trong phạm vi đã chọn' })
    expect(within(employees).getByRole('columnheader', { name: 'Quá hạn' })).toBeVisible()
    expect(within(employees).getByRole('columnheader', { name: 'Thù lao dự kiến đang nhận' })).toBeVisible()
    const employeeRow = await within(employees).findByRole('row', { name: /Editor kiểm thử/ })
    if (!employee.finance) throw new Error('The management fixture requires permitted finance data.')
    expect(within(employeeRow).getByText(formatAnalyticsVnd(employee.finance.active_total_vnd))).toBeVisible()
    expect(analyticsApi.summary).toHaveBeenCalledWith(profileId, filters, expect.any(AbortSignal))
  })
  it('provides keyboard-operable chart values and safe employee Task links', async () => {
    setup(); const user = userEvent.setup()
    await screen.findByRole('heading', { name: 'Hiệu suất nhân viên' })
    const months = screen.getByRole('region', { name: 'Số Task nghiệm thu từng tháng' })
    const november = within(months).getByRole('button', { name: '11/2026 2 Task' })
    november.focus(); await user.keyboard('{Enter}')
    expect(november).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('11/2026: 2 Task được nghiệm thu.')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Xem chi tiết Editor kiểm thử' }))
    expect(await screen.findByRole('link', { name: 'Task có thể mở' })).toHaveAttribute('href', `/profiles/${profileId}/workspaces/${workspaceId}/tasks/${otherId}`)
    expect(analyticsApi.employee).toHaveBeenCalledWith(profileId, memberId, filters, 1, expect.any(AbortSignal))
  })
  it('passes Workspace and local-inclusive custom dates to the server instead of summing Tasks in React', async () => {
    setup(); const user = userEvent.setup()
    await screen.findByRole('heading', { name: 'Hiệu suất nhân viên' })
    await user.selectOptions(screen.getByLabelText('Chọn Workspace'), workspaceId)
    await waitFor(() => expect(analyticsApi.summary).toHaveBeenLastCalledWith(profileId, { ...filters, workspace_id: workspaceId }, expect.any(AbortSignal)))
    fireEvent.change(screen.getByLabelText('Từ ngày'), { target: { value: '2026-11-01' } }); fireEvent.change(screen.getByLabelText('Đến ngày'), { target: { value: '2026-11-30' } })
    await user.click(screen.getByRole('button', { name: 'Áp dụng thời gian' }))
    await waitFor(() => expect(analyticsApi.summary).toHaveBeenLastCalledWith(profileId, { from: '2026-11-01', to: '2026-11-30', workspace_id: workspaceId }, expect.any(AbortSignal)))
  })
  it('keeps invalid range input local and enforces the backend search bound', async () => {
    setup(); const user = userEvent.setup()
    await screen.findByRole('heading', { name: 'Hiệu suất nhân viên' })
    expect(screen.getByLabelText('Tìm nhân viên')).toHaveAttribute('maxlength', '100')
    const calls = vi.mocked(analyticsApi.summary).mock.calls.length
    fireEvent.change(screen.getByLabelText('Từ ngày'), { target: { value: '2027-01-01' } })
    await user.click(screen.getByRole('button', { name: 'Áp dụng thời gian' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc')
    expect(analyticsApi.summary).toHaveBeenCalledTimes(calls)
  })
  it('searches/sorts/paginates employee data on the backend', async () => {
    vi.mocked(analyticsApi.employees).mockResolvedValue(page([employee], 41))
    setup(); const user = userEvent.setup()
    await screen.findByRole('button', { name: 'Xem chi tiết Editor kiểm thử' })
    await user.type(screen.getByLabelText('Tìm nhân viên'), 'Editor'); await user.click(screen.getByRole('button', { name: 'Tìm kiếm' }))
    await waitFor(() => expect(analyticsApi.employees).toHaveBeenLastCalledWith(profileId, filters, 'Editor', '-active_tasks', 1, expect.any(AbortSignal)))
    await user.selectOptions(screen.getByLabelText('Sắp xếp nhân viên'), '-approved_tasks')
    await waitFor(() => expect(analyticsApi.employees).toHaveBeenLastCalledWith(profileId, filters, 'Editor', '-approved_tasks', 1, expect.any(AbortSignal)))
    await user.click(screen.getByRole('button', { name: 'Trang sau' }))
    await waitFor(() => expect(analyticsApi.employees).toHaveBeenLastCalledWith(profileId, filters, 'Editor', '-approved_tasks', 2, expect.any(AbortSignal)))
  })
  it('renders loading/error/empty states without fabricated dashboard metrics', async () => {
    vi.mocked(analyticsApi.summary).mockReturnValue(new Promise(() => {}))
    setup(); expect(await screen.findByText('Đang tính thống kê từ dữ liệu thực…')).toBeInTheDocument()
    expect(screen.queryByText('1.999.999.999.999.999.998 ₫')).not.toBeInTheDocument()
  })
  it('handles an empty Profile inventory with an actual navigation action', async () => {
    vi.mocked(tenantApi.profiles).mockResolvedValue(page([]))
    setup('/analytics')
    expect(await screen.findByRole('heading', { name: 'Chưa có tổ chức để thống kê' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Xem tổ chức' })).toHaveAttribute('href', '/profiles')
    expect(analyticsApi.summary).not.toHaveBeenCalled()
  })
})

describe('analytics authority and tenant privacy', () => {
  it('does not retain prior-Profile data while the next Profile request is pending', async () => {
    vi.mocked(analyticsApi.summary).mockImplementation(async (id) => id === otherId ? new Promise(() => {}) : summary)
    setup(); const user = userEvent.setup()
    await screen.findByText('1.999.999.999.999.999.998 ₫')
    await user.selectOptions(screen.getByLabelText('Chọn tổ chức'), otherId)
    await waitFor(() => expect(analyticsApi.summary).toHaveBeenCalledWith(otherId, expect.any(Object), expect.any(AbortSignal)))
    expect(screen.queryByText('1.999.999.999.999.999.998 ₫')).not.toBeInTheDocument()
    expect(screen.queryByText('Editor kiểm thử')).not.toBeInTheDocument()
  })
  it('clears management employee caches before a delayed self/redacted response can reuse them', async () => {
    const client = setup()
    await screen.findByRole('button', { name: 'Xem chi tiết Editor kiểm thử' })
    const oldKey = analyticsKeys.employees(profileId, filters, '', '-active_tasks', 1, analyticsAuthority(summary))
    expect(client.getQueryData(oldKey)).toBeDefined()
    vi.mocked(analyticsApi.summary).mockResolvedValue({ ...summary, scope: { ...summary.scope, mode: 'self' }, capabilities: { can_view_employee_breakdown: false, can_view_financial_totals: false }, finance: null })
    vi.mocked(analyticsApi.employees).mockReturnValue(new Promise(() => {}))
    await act(async () => { await client.invalidateQueries({ queryKey: analyticsKeys.summary(profileId, filters) }) })
    expect(await screen.findByRole('heading', { name: 'Hiệu suất của tôi' })).toBeVisible()
    expect(screen.queryByText('Editor kiểm thử')).not.toBeInTheDocument()
    expect(screen.queryByText('1.999.999.999.999.999.998 ₫')).not.toBeInTheDocument()
    expect(screen.queryByText('500.000 ₫')).not.toBeInTheDocument()
    await waitFor(() => expect(client.getQueryData(oldKey)).toBeUndefined())
    expect(client.getQueriesData({ queryKey: analyticsKeys.profile(profileId) }).some(([, value]) => JSON.stringify(value)?.includes('Editor kiểm thử'))).toBe(false)
  })
  it.each([403, 404])('clears private analytics payloads after HTTP%s without a refetch loop', async (status) => {
    const client = setup()
    await screen.findByRole('button', { name: 'Xem chi tiết Editor kiểm thử' })
    vi.mocked(analyticsApi.summary).mockRejectedValue(new ApiError(status, status === 403 ? 'forbidden' : 'not-found', 'Phạm vi không còn khả dụng.'))
    await act(async () => { await client.invalidateQueries({ queryKey: analyticsKeys.summary(profileId, filters) }) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Phạm vi không còn khả dụng.')
    await waitFor(() => expect(client.getQueriesData({ queryKey: analyticsKeys.profile(profileId) }).length).toBe(0))
    expect(screen.queryByText('Editor kiểm thử')).not.toBeInTheDocument()
    expect(screen.queryByText('1.999.999.999.999.999.998 ₫')).not.toBeInTheDocument()
    expect(analyticsApi.summary).toHaveBeenCalledTimes(2)
  })
  it('never renders redacted financial totals or value-sort options in Viewer scope', async () => {
    vi.mocked(analyticsApi.summary).mockResolvedValue({ ...summary, scope: { ...summary.scope, mode: 'self' }, capabilities: { can_view_employee_breakdown: false, can_view_financial_totals: false }, finance: null })
    vi.mocked(analyticsApi.employees).mockResolvedValue(page([{ ...employee, finance: null }]))
    setup()
    expect(await screen.findByRole('heading', { name: 'Hiệu suất của tôi' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Tổng thù lao dự kiến' })).not.toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'Giá trị nghiệm thu' })).not.toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'Thù lao dự kiến đang nhận' })).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Giá trị nghiệm thu: cao nhất' })).not.toBeInTheDocument()
  })
})

it('places the active Analytics navigation between Organization and Notifications', () => {
  const client = new QueryClient()
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/analytics']}><Routes><Route element={<AppLayout />}><Route path="/analytics" element={<p>Trang thống kê</p>} /></Route></Routes></MemoryRouter></QueryClientProvider>)
  const navigation = screen.getByRole('navigation', { name: 'Điều hướng chính' })
  expect(within(navigation).getAllByRole('link').map((link) => link.textContent)).toEqual(['Tổng quan', 'Tổ chức', 'Thống kê', 'Thông báo', 'Thùng rác', 'Tài khoản'])
  expect(within(navigation).getByRole('link', { name: 'Thống kê' })).toHaveAttribute('aria-current', 'page')
})

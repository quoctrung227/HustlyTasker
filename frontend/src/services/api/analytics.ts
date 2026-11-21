/** Read-only server aggregations. Monetary values stay exact decimal strings. */
import { ApiError, apiClient, invalidResponse } from './client'
import type { Page } from './types'
import { taskStatuses, workKeys } from './work-management'
import type { TaskStatus } from './work-management'

export interface AnalyticsFilters { readonly workspace_id?: string; readonly from: string; readonly to: string }
export type EmployeeOrdering = 'active_tasks' | '-active_tasks' | 'approved_tasks' | '-approved_tasks' | 'approved_value' | '-approved_value'
export interface AnalyticsScope {
  mode: 'management' | 'self'; profile_id: string; workspace_id: string | null
  timezone: 'Asia/Ho_Chi_Minh'; from: string; to: string; start_at: string; end_before: string; snapshot_at: string
  cohort_basis: 'task_created_at'; approvals_basis: 'review_created_at'; include_subtasks: true
}
export interface AnalyticsFinance {
  estimated_total_vnd: string | null; estimated_known_tasks: number; estimated_unpriced_tasks: number
  approved_total_vnd: string | null; approved_priced_tasks: number; approved_unpriced_tasks: number; approved_unknown_tasks: number
}
export interface AnalyticsSummary {
  scope: AnalyticsScope
  capabilities: { can_view_employee_breakdown: boolean; can_view_financial_totals: boolean }
  kpis: { total_tasks: number; approved_tasks: number; working_tasks: number; review_tasks: number; overdue_tasks: number; unassigned_tasks: number; unverified_completed_tasks: number; unattributed_approved_tasks: number }
  finance: AnalyticsFinance | null
  distribution: { status: TaskStatus; count: number }[]
  approval_trend: { month: string; count: number }[]
}
export interface EmployeeFinance {
  active_total_vnd: string | null; active_known_tasks: number; active_unpriced_tasks: number
  approved_total_vnd: string | null; approved_priced_tasks: number; approved_unpriced_tasks: number; approved_unknown_tasks: number
}
export interface AnalyticsEmployee {
  id: string; display_name: string | null; is_available: boolean
  active_tasks: number; approved_tasks: number; overdue_tasks: number; finance: EmployeeFinance | null
}
export interface EmployeeTask {
  id: string; workspace_id: string; title: string; status: TaskStatus; deadline: string | null
  relation: 'current' | 'approved' | 'current_and_approved'
}
export interface EmployeeDetail extends Page<EmployeeTask> { employee: AnalyticsEmployee }
export function analyticsAuthority(summary: AnalyticsSummary): string {
  return `${summary.scope.mode}:${summary.capabilities.can_view_employee_breakdown}:${summary.capabilities.can_view_financial_totals}`
}

const record = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown): value is string => typeof value === 'string'
const uuid = (value: unknown): value is string => text(value) && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
const count = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
const amount = (value: unknown): value is string | null => value === null || (text(value) && /^(0|[1-9]\d*)$/.test(value))
const nullableText = (value: unknown): value is string | null => value === null || text(value)
const timestamp = (value: unknown): value is string => text(value) && Number.isFinite(Date.parse(value))
const status = (value: unknown): value is TaskStatus => taskStatuses.some((item) => item === value)
export const employeeOrderings: readonly EmployeeOrdering[] = ['-active_tasks', 'active_tasks', '-approved_tasks', 'approved_tasks', '-approved_value', 'approved_value']

export function isAnalyticsDate(value: unknown): value is string {
  if (!text(value) || !/^\d{4}-(0[1-9]|1[0-2])-\d{2}$/.test(value)) return false
  const year = Number(value.slice(0, 4)), month = Number(value.slice(5, 7)), day = Number(value.slice(8))
  const date = new Date(0); date.setUTCFullYear(year, month - 1, day); date.setUTCHours(0, 0, 0, 0)
  return year > 0 && date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
}
export function currentHcmMonth(now = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit' }).formatToParts(now)
  return `${parts.find((part) => part.type === 'year')?.value}-${parts.find((part) => part.type === 'month')?.value}`
}
export function monthDateRange(month: string): { from: string; to: string } {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(month) || Number(month.slice(0, 4)) < 1) throw new TypeError('Invalid analytics month.')
  const end = new Date(0); end.setUTCFullYear(Number(month.slice(0, 4)), Number(month.slice(5)), 0)
  return { from: `${month}-01`, to: `${month}-${String(end.getUTCDate()).padStart(2, '0')}` }
}
export function formatAnalyticsVnd(value: string | null): string {
  if (value === null) return 'Chưa có giá trị xác định'
  if (!amount(value)) throw new TypeError('Invalid exact monetary total.')
  return `${value.replace(/\B(?=(\d{3})+(?!\d))/g, '.')} ₫`
}
function entity(value: string): string {
  if (!uuid(value)) throw new ApiError(404, 'not-found', 'Không tìm thấy phạm vi thống kê hoặc bạn không có quyền truy cập.')
  return value.toLowerCase()
}
function filterQuery(filters: AnalyticsFilters): URLSearchParams {
  if (!isAnalyticsDate(filters.from) || !isAnalyticsDate(filters.to) || filters.from > filters.to) throw new TypeError('Invalid analytics date range.')
  if (Date.parse(`${filters.to}T00:00:00Z`) - Date.parse(`${filters.from}T00:00:00Z`) >= 366 * 86400000) throw new TypeError('Analytics ranges are at most 366 inclusive days.')
  const query = new URLSearchParams({ from: filters.from, to: filters.to })
  if (filters.workspace_id) query.set('workspace_id', entity(filters.workspace_id))
  return query
}
function path(profileId: string) { return `v1/profiles/${entity(profileId)}/analytics/` }
function finance(value: unknown, active = false): value is AnalyticsFinance | EmployeeFinance | null {
  if (value === null) return true
  if (!record(value) || !amount(value.approved_total_vnd) || !count(value.approved_priced_tasks) || !count(value.approved_unpriced_tasks) || !count(value.approved_unknown_tasks)) return false
  return active ? amount(value.active_total_vnd) && count(value.active_known_tasks) && count(value.active_unpriced_tasks)
    : amount(value.estimated_total_vnd) && count(value.estimated_known_tasks) && count(value.estimated_unpriced_tasks)
}
function employee(value: unknown): value is AnalyticsEmployee {
  return record(value) && uuid(value.id) && nullableText(value.display_name) && (value.display_name === null || value.display_name.trim().length > 0) &&
    typeof value.is_available === 'boolean' && count(value.active_tasks) && count(value.approved_tasks) && count(value.overdue_tasks) && finance(value.finance, true)
}
function page<T>(value: unknown, guard: (item: unknown) => item is T): Page<T> {
  if (!record(value) || !count(value.count) || !nullableText(value.next) || !nullableText(value.previous) || !Array.isArray(value.results) || !value.results.every(guard)) throw invalidResponse()
  return { count: value.count, next: value.next, previous: value.previous, results: value.results }
}
function pageNumber(value: number) { if (!Number.isSafeInteger(value) || value < 1) throw new TypeError('Invalid analytics page.'); return String(value) }
function summary(value: unknown, profileId: string, filters: AnalyticsFilters): AnalyticsSummary {
  if (!record(value) || !record(value.scope) || !record(value.capabilities) || !record(value.kpis)) throw invalidResponse()
  const s = value.scope, k = value.kpis, c = value.capabilities
  if (!['management', 'self'].includes(String(s.mode)) || s.profile_id !== entity(profileId) || s.workspace_id !== (filters.workspace_id ? entity(filters.workspace_id) : null) ||
    s.timezone !== 'Asia/Ho_Chi_Minh' || s.from !== filters.from || s.to !== filters.to || !timestamp(s.start_at) || !timestamp(s.end_before) || !timestamp(s.snapshot_at) ||
    s.cohort_basis !== 'task_created_at' || s.approvals_basis !== 'review_created_at' || s.include_subtasks !== true ||
    typeof c.can_view_employee_breakdown !== 'boolean' || typeof c.can_view_financial_totals !== 'boolean' || (c.can_view_financial_totals ? value.finance === null : value.finance !== null) ||
    !['total_tasks', 'approved_tasks', 'working_tasks', 'review_tasks', 'overdue_tasks', 'unassigned_tasks', 'unverified_completed_tasks', 'unattributed_approved_tasks'].every((key) => count(k[key])) || !finance(value.finance) ||
    !Array.isArray(value.distribution) || !value.distribution.every((row) => record(row) && status(row.status) && count(row.count)) ||
    new Set(value.distribution.map((row) => row.status)).size !== value.distribution.length || value.distribution.reduce((total, row) => total + row.count, 0) !== k.total_tasks ||
    !Array.isArray(value.approval_trend) || !value.approval_trend.every((row) => record(row) && text(row.month) && /^\d{4}-(0[1-9]|1[0-2])$/.test(row.month) && count(row.count))) throw invalidResponse()
  return value as unknown as AnalyticsSummary
}

export const analyticsKeys = {
  profile: (profileId: string) => [...workKeys.profile(profileId), 'analytics'] as const,
  summary: (profileId: string, filters: AnalyticsFilters) => [...analyticsKeys.profile(profileId), 'summary', filters] as const,
  employees: (profileId: string, filters: AnalyticsFilters, search = '', ordering: EmployeeOrdering = '-active_tasks', page = 1, authority = 'unresolved') => [...analyticsKeys.profile(profileId), 'employees', authority, filters, search, ordering, page] as const,
  employee: (profileId: string, filters: AnalyticsFilters, membershipId: string, page = 1, authority = 'unresolved') => [...analyticsKeys.profile(profileId), 'employee', authority, filters, membershipId, page] as const,
}
export const analyticsApi = {
  async summary(profileId: string, filters: AnalyticsFilters, signal?: AbortSignal): Promise<AnalyticsSummary> {
    return summary(await apiClient.request<unknown>(`${path(profileId)}?${filterQuery(filters)}`, { signal, protected: true }), profileId, filters)
  },
  async employees(profileId: string, filters: AnalyticsFilters, search = '', ordering: EmployeeOrdering = '-active_tasks', pageNo = 1, signal?: AbortSignal): Promise<Page<AnalyticsEmployee>> {
    if (!employeeOrderings.includes(ordering)) throw new TypeError('Invalid employee ordering.')
    if (Array.from(search).length > 100 || search.includes(String.fromCharCode(0)) || /[\uD800-\uDFFF]/u.test(search)) throw new TypeError('Invalid employee search.')
    const query = filterQuery(filters); query.set('search', search); query.set('ordering', ordering); query.set('page', pageNumber(pageNo))
    return page(await apiClient.request<unknown>(`${path(profileId)}employees/?${query}`, { signal, protected: true }), employee)
  },
  async employee(profileId: string, membershipId: string, filters: AnalyticsFilters, pageNo = 1, signal?: AbortSignal): Promise<EmployeeDetail> {
    const query = filterQuery(filters); query.set('page', pageNumber(pageNo))
    const value = await apiClient.request<unknown>(`${path(profileId)}employees/${entity(membershipId)}/?${query}`, { signal, protected: true })
    if (!record(value) || !employee(value.employee) || value.employee.id !== entity(membershipId)) throw invalidResponse()
    const result = page(value, (row): row is EmployeeTask => record(row) && uuid(row.id) && uuid(row.workspace_id) && text(row.title) && status(row.status) && (row.deadline === null || timestamp(row.deadline)) && ['current', 'approved', 'current_and_approved'].includes(String(row.relation)))
    if (filters.workspace_id && result.results.some((row) => row.workspace_id !== entity(filters.workspace_id ?? ''))) throw invalidResponse()
    return { ...result, employee: value.employee }
  },
}

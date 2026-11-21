import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { analyticsApi, analyticsKeys, currentHcmMonth, formatAnalyticsVnd, isAnalyticsDate, monthDateRange } from './analytics'
import { analyticsEmployee as employee, analyticsFilters as filters, analyticsMemberId as memberId, analyticsOtherId as otherId, analyticsProfileId as profileId, analyticsSummary as summary, analyticsTimestamp as timestamp, analyticsWorkspaceId as workspaceId } from '../../test/analytics-fixtures'

beforeEach(() => { vi.restoreAllMocks(); vi.spyOn(apiClient, 'request') })
const page = (results: unknown[]) => ({ count: results.length, next: null, previous: null, results })
describe('analytics read contracts', () => {
  it('reads exact server aggregates including amounts above safe integer and keeps the cohort/event distinction', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(summary)
    const result = await analyticsApi.summary(profileId, filters)
    expect(result.finance?.estimated_total_vnd).toBe('1999999999999999998')
    expect(result.scope.approvals_basis).toBe('review_created_at')
    expect(apiClient.request).toHaveBeenCalledExactlyOnceWith(`v1/profiles/${profileId}/analytics/?from=2026-06-01&to=2026-11-30`, { signal: undefined, protected: true })
  })
  it.each([
    { ...summary, scope: { ...summary.scope, profile_id: otherId } },
    { ...summary, scope: { ...summary.scope, workspace_id: workspaceId } },
    { ...summary, scope: { ...summary.scope, from: '2026-05-01' } },
    { ...summary, scope: { ...summary.scope, timezone: 'UTC' } },
    { ...summary, finance: { ...summary.finance, estimated_total_vnd: Number('1999999999999999998') } },
    { ...summary, capabilities: { ...summary.capabilities, can_view_financial_totals: false } },
    { ...summary, distribution: [{ status: 'WORKING', count: 4 }] },
    { ...summary, kpis: { ...summary.kpis, total_tasks: -1 } },
  ])('rejects an inconsistent or unsafe aggregation response %#', async (payload) => {
    vi.mocked(apiClient.request).mockResolvedValue(payload)
    await expect(analyticsApi.summary(profileId, filters)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('accepts explicit self scope with own permitted finance or redacted null', async () => {
    const own = { ...summary, scope: { ...summary.scope, mode: 'self' }, capabilities: { can_view_employee_breakdown: false, can_view_financial_totals: false }, finance: null }
    vi.mocked(apiClient.request).mockResolvedValue(own)
    expect((await analyticsApi.summary(profileId, filters)).finance).toBeNull()
  })
  it.each([{ from: '2026-02-29', to: '2026-03-01' }, { from: '2026-11-10', to: '2026-11-01' }, { from: 'not-a-date', to: '2026-11-01' }])('rejects bad filter dates before requesting %#', async (value) => {
    await expect(analyticsApi.summary(profileId, value)).rejects.toBeInstanceOf(TypeError)
    expect(apiClient.request).not.toHaveBeenCalled()
  })
  it('builds employee search/order/page locally and never follows server pagination URLs', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ ...page([employee]), next: 'https://untrusted.test/' })
    const result = await analyticsApi.employees(profileId, { ...filters, workspace_id: workspaceId }, 'Editor B', '-approved_value', 2)
    expect(result.results[0]?.finance?.approved_total_vnd).toBe('500000')
    expect(apiClient.request).toHaveBeenCalledWith(`v1/profiles/${profileId}/analytics/employees/?from=2026-06-01&to=2026-11-30&workspace_id=${workspaceId}&search=Editor+B&ordering=-approved_value&page=2`, { signal: undefined, protected: true })
  })
  it('checks employee identity and selected Workspace before exposing a detail task link', async () => {
    const task = { id: otherId, workspace_id: workspaceId, title: 'Task synthetic', status: 'WORKING', deadline: timestamp, relation: 'current' }
    vi.mocked(apiClient.request).mockResolvedValue({ ...page([task]), employee })
    expect((await analyticsApi.employee(profileId, memberId, { ...filters, workspace_id: workspaceId })).results[0]?.title).toBe('Task synthetic')
    vi.mocked(apiClient.request).mockResolvedValue({ ...page([{ ...task, workspace_id: otherId }]), employee })
    await expect(analyticsApi.employee(profileId, memberId, { ...filters, workspace_id: workspaceId })).rejects.toMatchObject({ kind: 'invalid-response' })
    vi.mocked(apiClient.request).mockResolvedValue({ ...page([task]), employee: { ...employee, id: otherId } })
    await expect(analyticsApi.employee(profileId, memberId, filters)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('keeps tenant/filter/employee/page cache keys distinct', () => {
    expect(analyticsKeys.summary(profileId, filters)).not.toEqual(analyticsKeys.summary(otherId, filters))
    expect(analyticsKeys.summary(profileId, filters)).not.toEqual(analyticsKeys.summary(profileId, { ...filters, workspace_id: workspaceId }))
    expect(analyticsKeys.employee(profileId, filters, memberId, 1)).not.toEqual(analyticsKeys.employee(profileId, filters, memberId, 2))
  })
})
describe('exact amounts and HCM calendar filters', () => {
  it.each([['0', '0 ₫'], ['1999999999999999998', '1.999.999.999.999.999.998 ₫'], [null, 'Chưa có giá trị xác định']])('formats %s without Number conversion', (value, expected) => { expect(formatAnalyticsVnd(value)).toBe(expected) })
  it('uses the HCM month around the UTC boundary and real leap-calendar dates', () => {
    expect(currentHcmMonth(new Date('2026-01-31T18:00:00Z'))).toBe('2026-02')
    expect(monthDateRange('2024-02')).toEqual({ from: '2024-02-01', to: '2024-02-29' })
    expect(monthDateRange('0001-02')).toEqual({ from: '0001-02-01', to: '0001-02-28' })
    expect(isAnalyticsDate('2026-02-29')).toBe(false)
  })
})

/** Synthetic fixtures for isolated frontend tests only; never application data. */
import type { AnalyticsEmployee, AnalyticsSummary } from '../services/api/analytics'
export const analyticsProfileId = '00000000-0000-4000-8000-000000000301'
export const analyticsWorkspaceId = '00000000-0000-4000-8000-000000000302'
export const analyticsMemberId = '00000000-0000-4000-8000-000000000303'
export const analyticsOtherId = '00000000-0000-4000-8000-000000000304'
export const analyticsTimestamp = '2026-11-10T00:00:00Z'
export const analyticsFilters = { from: '2026-06-01', to: '2026-11-30' }
export const analyticsSummary: AnalyticsSummary = {
  scope: { mode: 'management', profile_id: analyticsProfileId, workspace_id: null, timezone: 'Asia/Ho_Chi_Minh', from: analyticsFilters.from, to: analyticsFilters.to, start_at: '2026-05-31T17:00:00Z', end_before: '2026-11-30T17:00:00Z', snapshot_at: analyticsTimestamp, cohort_basis: 'task_created_at', approvals_basis: 'review_created_at', include_subtasks: true },
  capabilities: { can_view_employee_breakdown: true, can_view_financial_totals: true },
  kpis: { total_tasks: 3, approved_tasks: 0, working_tasks: 1, review_tasks: 0, overdue_tasks: 1, unassigned_tasks: 1, unverified_completed_tasks: 1, unattributed_approved_tasks: 0 },
  finance: { estimated_total_vnd: '1999999999999999998', estimated_known_tasks: 2, estimated_unpriced_tasks: 1, approved_total_vnd: '500000', approved_priced_tasks: 1, approved_unpriced_tasks: 0, approved_unknown_tasks: 1 },
  distribution: [{ status: 'PENDING', count: 0 }, { status: 'ASSIGNED', count: 1 }, { status: 'WORKING', count: 1 }, { status: 'REVIEW', count: 0 }, { status: 'COMPLETED', count: 1 }, { status: 'CANCELLED', count: 0 }],
  approval_trend: ['2026-06', '2026-07', '2026-08', '2026-09', '2026-10', '2026-11'].map((month, index) => ({ month, count: index === 5 ? 2 : 0 })),
}
export const analyticsEmployee: AnalyticsEmployee = { id: analyticsMemberId, display_name: 'Editor kiểm thử', is_available: true, active_tasks: 1, approved_tasks: 2, overdue_tasks: 1,
  finance: { active_total_vnd: '999999999999999999', active_known_tasks: 1, active_unpriced_tasks: 0, approved_total_vnd: '500000', approved_priced_tasks: 1, approved_unpriced_tasks: 0, approved_unknown_tasks: 1 } }

# Task reassignment and analytics V1

Task: HT-TASK-REASSIGN-ANALYTICS-V1. Owner-authorized implementation and isolated
candidate migrations only. Persistent development rollout requires separate
approval. Existing Profile→Workspace→Task architecture, Session/CSRF and
compensation RBAC remain authoritative.

## Owner preflight — SRS correction and migration review

Task: **HT-TASK-REASSIGN-ANALYTICS-OWNER-PREFLIGHT — BUSINESS PASS /
MIGRATION PREFLIGHT PASS WITH COORDINATED WRITER STOP REQUIRED**.
The Owner supplied SRS V3 section4.2.1 after the V1 review. Repository source and
document searches did not locate a SRS V3 file; the supplied excerpt is the
current business authority, not a claim that the full SRS was independently read.

Initial business audit **FAIL**: unassign_task in services.py really deactivated
the assignment and saved only Task.updated_at. Both ASSIGNED and WORKING therefore
remained unchanged. The earlier report correctly described that implementation,
but the implementation did not satisfy the Owner's SRS rule. The service,
audit state metadata, related UI copy and regression expectations are corrected:

| Action | Required resulting state |
|---|---|
| Remove assignee from ASSIGNED | PENDING |
| Remove assignee from WORKING | PENDING |
| Transfer WORKING to another eligible worker | ASSIGNED |
| Ordinary removal/transfer in REVIEW or COMPLETED | Reject409 |

Existing PENDING handling remains PENDING and CANCELLED stays denied. Preserve
the Task, all versions/authors/Reviews/Comments and durable assignment/audit history.
The one ACTIVE assignment, current manager/tenant checks, ID+timestamp CAS and
atomic audit/notification policy are unchanged. No new schema is required for
this business fix. Fresh guarded PostgreSQL preflight158/158 PASS60.885s, run
cd7a89a5764b4403b9847984160474ea, actual Python/launcher0 and cleanup0. This covers
business/security regressions and seven migration tests. Full frontend1182/1182
PASS46.81s/npm0 and lint112files0. Guarded real browser4/4 PASS47.7s, run
e8cbb590088b42dfba66b8b568d7025e; actual launcher/Playwright/backend0, owned
database/resources removed and UI unassign PENDING asserted. Typecheck/build0,
Vite10.33s/chunk639.43kB advisory. Final read-only preservation05:43:43Z PASS:
exact29-table schema/history/data fingerprint and37migrations retained, with
5Users/2Sessions/2Profiles/3ProfileMemberships/3Workspaces/3WorkspaceMembers/
2Invitations/4Tasks/38Audits/0AIrows. Canonical SHA256 before=after
6bf61a2742683fbd8dfa18ab36051611c060165e6e942c1b82b2c6b085efd639.
Both candidates/ai.0002 remain UNAPPLIED, tasks.0005 APPLIED and0owned resources.
[HANDOVER](HANDOVER.md) owns receipts; V1 counts below are historical, not current PASS. Full
backend1051 was not rerun in this preflight.
Owner approval of this correction does not authorize either development migration.

The two unchanged candidates depend only on their respective0002 migrations.
Isolated preflight rebuilt the actual read-only37-migration development history
and verified exact matching tables/columns/constraints/indexes. Each forward plan
contains only its candidate, resulting in39 records without ai.0002; a guard
forbids ai.0002 even in this isolated run. Synthetic legacy fixtures retain their
rows and false/NULL historical amounts. This is schema-equivalent reconstruction,
not a restore of a development backup. Old Review reads work, but old writers
fail23502 because the new NOT NULL field has no permanent database default.
Review reversal demonstrably loses snapshots; Notification reversal with new
TASK_UNASSIGNED rows fails atomically, while reversal without them succeeds.
Preflight PASS therefore requires coordinated activation with old writers stopped;
unsafe mixed-version writing and automatic rollback are FAIL/not authorized.
See the detailed
[migration compatibility/recovery gate](DATABASE_SCHEMA.md). Development remains
read-only. **STOP AT OWNER APPROVAL GATE — DEVELOPMENT MIGRATION APPROVAL PENDING**.

## Reviewed implementation boundaries

The source audit confirms assign/reassign already locks the tenant aggregate and
Task, deactivates the previous assignment and enforces one ACTIVE row. It allows
PENDING/ASSIGNED/WORKING and resets to ASSIGNED. Reusing a former (task,user) row
updates assigned_at; AuditLog is the durable transfer chronology.

The corrected unassign operation resets ASSIGNED/WORKING to PENDING, as required
by the Owner-supplied SRS V3 section4.2.1; PENDING stays PENDING. The earlier V1
preserve-status interpretation is superseded, while all work/history is retained.
It shares the same allowed states and manager/lifecycle checks;
REVIEW/COMPLETED/CANCELLED remain blocked. A Task awaiting review must use the
existing Request Changes flow before a transfer. No mutation changes old
Deliverable authors, links, revisions, Reviews or Comments.

The new UI always confirms against expected_assignment_id plus
expected_assigned_at, preventing stale confirmation and A→B→A reuse. Existing
assign clients may omit the additive pair for compatibility. Unassign requires
both current values. Optional reason uses the existing4000-character text bound,
validated for NUL/invalid Unicode. Audit records the old/new references, actor,
time and reason, never compensation. Assignment and both recipients' database
notifications commit/rollback atomically, using current membership eligibility.

## Historical evidence and candidate schema

Review(APPROVED).created_at is the acceptance time; the approved Deliverable's
uploaded_by is the credited worker. Never attribute accepted work to the current
assignment. A canonical approved latest revision plus COMPLETED state is needed;
legacy completed rows without sufficient proof are reported separately.

Current Task compensation is editable even after completion. It is therefore
not evidence of the amount at approval. A minimal additive Review candidate adds
compensation_snapshot_vnd nullable numeric(18,0) and
compensation_snapshot_recorded defaultFalse. Future approval captures both in
the existing atomic transaction. True+NULL means no price at approval;
False+NULL means historical amount unknown. Legacy rows remain unknown, with no
guessed data backfill. Known amounts are summed exactly and coverage is disclosed.

A Notification candidate adds TASK_UNASSIGNED and updates its event CHECK so
the previous worker receives a truthful removal message, not TASK_ASSIGNED.
The new worker uses the existing assignment event. Revoked recipients and the
actor-self exclusion retain current notification conventions.

These designs were reviewed against source by the root and independent backend
audits before implementation. The current Owner request authorizes candidate
code/tests, not development application. No AI migration is included.

## Metric definitions

The selected inclusive local dates use Asia/Ho_Chi_Minh and convert to a UTC
half-open range. Default is the current local month. A366-day query cap and
existing20/max100 pagination are technical V1 bounds, not financial policy.

- C: currently readable Tasks created in the selected period and Workspace scope.
- Total: count(C). Accepted KPI: C with canonical approved completion evidence.
- Working: C.status=WORKING; awaiting: C.status=REVIEW.
- Overdue: nonterminal C with deadline before response snapshot time. This
  overlaps other KPI groups and is never a donut slice.
- Unassigned: nonterminal C without an ACTIVE assignment. Corrected unassign
  sets PENDING; the KPI still checks actual current assignment rows rather than
  assuming status always proves responsibility in legacy data.
- Donut: six real, mutually exclusive Task statuses; counts sum to count(C).
- Monthly acceptance and accepted value: approved events in the selected period
  by Review.created_at, independently of the Task creation cohort.
- Current employee responsibility/value: active assignments within C.
- Accepted employee credit/value: canonical approved event uploader, never
  active assignment. Reassignment changes current counts without moving credit.

Money is computed on the backend with exact numeric/Decimal, transported as
integer strings and formatted without JavaScript float aggregation. NULL is not
0. Missing-price and missing-historical-snapshot counts remain distinct. No
actual payment, payroll, revenue or profit claim is supported.

## Scope and UX

Profile Owner/Admin can view management analytics in the readable Profile scope.
An ordinary Profile MEMBER gets management analytics only when selecting a
Workspace where they currently have ADMIN authority. Their all-Workspace view
defaults to self scope; MEMBER/VIEWER views never receive coworkers' financial
payloads. Historical money still requires current Task read and existing
financial eligibility. Revocation/archival policies and tenant-safe404 apply.

The approved order is retained: Profile/Workspace/HCM date filters; six KPI cards;
pale-teal financial cards; status donut and monthly line; searchable/sortable
employee table and detail panel. Sidebar Thống kê sits between Tổ chức and Thông
báo. Existing tokens/shared components and accessible SVG/data-table alternatives
are reused; no new chart/UI dependency or design system. Task assignment uses
the existing native dialog with explicit transfer/removal confirmation.

Implementation and fresh evidence are tracked in HANDOVER. Candidate rollout,
backup/rehearsal and Owner website acceptance remain separate gates.

## Historical V1 resume evidence and acceptance boundaries — 2026-11-13

These results predate the SRS unassign correction. They remain genuine evidence
for the prior source, not passing verification of the current correction.

| Area | Current evidence/status |
|---|---|
| Backend reassignment/analytics/security | Implemented; fresh full isolated PostgreSQL1051/1051 PASS, launcher/Python0; targeted152 passed earlier in this task |
| Frontend/sidebar/dashboard/employee details | Implemented; full1181/1181 and focused279/279 PASS; typecheck/lint/build0 |
| New real UI integration |4/4 PASS, including transfer/removal, current counts, immutable accepted credit, exact money and role privacy |
| Responsive/accessibility |375/768/1440/812×375, reduced motion, native dialog/keyboard/focus and axe0 verified; desktop/mobile screenshots inspected |
| Affected regressions | Eight suites37/37 PASS; with new4, final41/41 across9 passing real browser suites, all process exits0 and owned cleanup verified |
| Migration candidates | Review snapshot and Notification event tested only in isolated PostgreSQL; both remain UNAPPLIED development |
| Development/source preservation | Original and resume baselines retained; Nov11 external activity distinguished. Final29-table read-only resume fingerprints match; source/HEAD and tested hashes preserved |
| Runtime rollout / Owner manual acceptance | OUT OF SCOPE for execution here; separate migration approval and controlled rollout required first |

Test fixtures use synthetic tenants in ownership-checked disposable PostgreSQL,
not fake values in the production application. New transfer/removal mutations
are exercised through React; denied requests and state readbacks use API calls
and are explicitly not described as UI mutations. Mobile tests verify reflow,
accessibility and dialog operation; the new mutation journey runs at1440px.
No claim of manual Owner acceptance, live email/AI, production readiness or
new feature availability on persistent development is made.

Historical V1 status: **IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION
APPROVAL — OWNER REVIEW GATE**. Final test/cleanup/source receipts are documented
in [HANDOVER](HANDOVER.md). The first backend full attempt had one corrected
fixture-chronology failure; the first new browser attempt failed on a wrapped
select locator, leaving three cases unrun. Both failed attempts remain retained;
final passing counts refer only to the corrected completed runs.

## Owner acceptance after separately approved migration rollout

1. Confirm both candidate migrations have completed through the documented
   backup/restore/targeted-plan gate; tasks.0005 must stay APPLIED and ai.0002
   UNAPPLIED. Only then use one restarted Django backend and the existing Vite
   command; never start a second server on an occupied port.
2. As a legitimate manager, open an assigned eligible Task. Check the current
   name, choose Thay đổi phân công, select a different eligible ACTIVE worker,
   optionally enter a reason, inspect the confirmation and confirm once.
3. Confirm the name updates immediately and after reload. Remove the assignment
   with confirmation; the Task has no assignee and becomes PENDING, preserving
   all submitted versions/comments/reviews. Assign again and use Start as
   required by the existing workflow.
4. Open Thống kê, select the managed Workspace and HCM period. Check six KPI,
   current estimate coverage, approved snapshot/unknown coverage, real status
   distribution, approval-event trend, employee search/order/details and Task
   navigation. Current responsibility/value should move A→B once; organization
   totals and accepted uploader credit must not move.
5. Verify old/new workers receive only eligible in-app notifications. As an
   ordinary MEMBER use Thống kê của tôi; Viewer must see no monetary values or
   coworkers' financial payloads in either UI or Network responses.
6. Confirm REVIEW/COMPLETED Tasks cannot be reassigned through normal controls;
   pending decisions use the authorized Review workflow. Check mobile navigation,
   keyboard, Escape/focus return, empty/error states and another Profile scope.

Manual mutations create real development records. Only the Owner decides when
to perform them and how to retain them; this implementation inserts no demo
development data. Do not delete accepted historical rows to make totals match.

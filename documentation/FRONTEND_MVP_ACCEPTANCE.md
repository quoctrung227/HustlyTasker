# Frontend MVP completeness and acceptance — HT-FE-P3-04

## Current bounded follow-up — HT-FE-WORKSPACE-MEMBERS-01,2026-11-09

**IMPLEMENTATION COMPLETE — OWNER REVIEW GATE.** Owner separately
approved the previously deferred Workspace member candidate/management surface.
Existing inline Workspace Detail now provides real same-Profile candidate grant,
confirmed role update/revoke, roster/current capabilities and inherited-access
explanation. Existing Profile invitation/recipient and Task stability remain;
no new schema, authorization model or generalized Profile governance is implied.
Profile role/remove and recipient inbox/preview are still separate contracts.

Current backend95/full863 PASS, API67/finalUI34 and type/lint/build0; broader
frontend902/902 passed before the final semantic-only fieldset/CSS reset, whose
final focused/UI checks pass. Real Workspace4+Members4+stability4+foundation6=
18/18 PASS, actual exits0 and owned cleanup. Final08:17:28Z read-only development
proof matches all29-table data/schema/history/sequence/identity fingerprints,
36 migrations/4 Users/2 Sessions retained; ai.0002 still UNAPPLIED.
No development business writes, AI/migration apply or manual Owner acceptance.
Current evidence/final status belongs in HANDOVER.

## Historical bounded follow-up — HT-FE-MEMBERS-01,2026-11-08

**IMPLEMENTATION COMPLETE — OWNER REVIEW GATE.** Owner now separately approved
organization Members/Invitation React integration. Historical FE04/FE05 exclusions
below do not prohibit this completed slice. Profile creation stays complete.
New protected Members roster/history and invite/resend/revoke controls consume
existing Invitation APIs plus minimal GET Profile members. Explicit authenticated
masked-code accept/decline and safe login/signup return complete recipient flow.
No token preview, no automatic Workspace grant, no Profile role/remove workflow
or general Workspace membership candidate UI is claimed.

Fresh frontend801/801, targeted backend51/full839, real Members4+stability4+
foundation6=14/14 and type/lint/build PASS. Full Python/browser child exits0,
owned cleanup verified; targeted launcher0/summary retained but separate child
event unavailable. Four-size keyboard/reflow/axe checks and375/1440 screenshot
inspection pass. Exact29-table development snapshot is unchanged:36 migrations,
4 Users,2 Sessions, existing business rows; no Invitation or AI rows created.
ai.0002 is still UNAPPLIED. No credentials/flags/provider/migration/deployment.
**REAL EMAIL DELIVERY NOT VERIFIED; AUTOMATED VERIFIED / MANUAL OWNER CHECK
PENDING.** See FRONTEND_GUIDE for recipient-code workflow and limitations.

## Historical bounded follow-up — HT-FE-P3-05,2026-11-02

**IMPLEMENTATION COMPLETE — OWNER REVIEW GATE.** Owner separately authorizes
Create Profile & First-Time User Onboarding. The earlier FE04 exclusion below
is historical scope, not a current prohibition. Invitation UI, member-candidate
API and remaining general membership/onboarding management are still pending
separate review. HT-AI-P4-02C remains reserved for Generator UI, not FE05.

Source now provides strict authenticated name-only POST /api/v1/profiles/ through
the existing atomic initial-owner service and protected React /profiles/new.
Zero-Profile Dashboard/Tổ chức CTAs, existing-user create-another, safe errors/
pending, list invalidation and URL selection lead to existing Workspace creation.
No automatic Workspace or unrelated membership is created. Existing Session/
CSRF/tenant/RBAC boundaries and the design master remain authoritative.

Targeted isolated backend40/40 PASS1.577s/full662/662 PASS245.938s, launcher/
Python exits0 and cleanup verified. Frontend426/426 PASS28.98s across16files,
typecheck/lint/build PASS; real isolated onboarding3/3 PASS48.1s and foundation6/6
PASS42.8s. All remaining real browser regressions passed: work7/7(1.2min),
collaboration7/7(1.3min), cohesive MVP acceptance1/1(35.1s), account-security1/1
(23.3s), for **25/25 across six suites**. Every launcher/Playwright/backend exit0,
owned database/container/network cleanup verified. Four-size empty/form-error
surfaces have axe0/keyboard/overflow checks; desktop empty/mobile form PNGs were
inspected. These are automated isolated results, not manual development testing.

The UI journey creates first/second Profile and Workspace through React, selects
and refreshes Profile URLs and checks cross-user privacy. Direct API assertions
are only read-back/negative checks; initial synthetic identity fixtures live
solely in the owned isolated cluster. Authentication, CSRF, injection, session
expiry, current-identity abort and scoped caching remain covered by current tests.

Final read-only development preservation at2026-11-02T04:37:31Z matches every
original row fingerprint, schema, sequence and migration history:36 migrations/
ai.0001 applied,3 Users/2 Sessions/business0/AI0. All52 model/migration/AI hashes
and19 tested changed-file hashes remain stable; no isolated test resource remains.
No schema, AI runtime, private .env or persistent development business fixture
was changed. **AUTOMATED VERIFIED / MANUAL OWNER CHECK PENDING.** Stop at the
Owner review gate; the guide lists the real website steps for the Owner.

## Historical FE04 acceptance matrix and evidence

Date: 2026-10-27. Status: **COMPLETE / OWNER REVIEW GATE**. This matrix audits the implemented
team-work MVP, not completion of every target requirement/business domain.
Current runtime evidence belongs in HANDOVER.md. Historical485 backend/356
frontend/browser7+7+6 results are baseline only, not this task's PASS evidence.

Owner confirmed the proposed MVP scope: account lifecycle and the existing work/
collaboration flows. Invitation, Profile Creation, member-candidate API and
remaining onboarding/management are OUT OF CURRENT TASK SCOPE / PENDING OWNER
REVIEW. These remain product requirements scheduled outside this bounded
acceptance task and are retained in the roadmap.

| Area | Source checkpoint | Backend support / action in FE04 |
|---|---|---|
| Login/logout/session expiry/CSRF | DONE — current isolated UI verified | Existing single AuthProvider/client and browser-managed SessionAuthentication; finite403 identity probe and private-cache clearing retained |
| Registration/recovery/email verification | DONE source and current isolated UI | Existing APIs consumed through bounded forms; register/reset no auto-login, token/password masked memory only; real provider delivery not verified |
| Profile list/detail/selection | DONE — current isolated UI verified | Current scoped reads and URL selection; switching never grants authority |
| Profile create/general edit | OUT OF CURRENT TASK SCOPE / PENDING OWNER REVIEW | No Profile collection POST/detail PATCH API. Do not fabricate endpoints or silently bootstrap tenants |
| Profile archive/restore UI | Not implemented, Owner scope review | Backend Owner-only actions exist; no implicit approval to implement general Profile administration |
| Workspace list/detail/create/update/archive/restore/month | DONE — current isolated UI verified | Existing API/forms and immutable canonical period; current role/lifecycle gates retained |
| Workspace roster/assignment candidates | DONE — current isolated UI verified | Existing manager-only paginated display_label/is_assignable reads |
| General membership direct-add/role/revoke UI | OUT OF CURRENT TASK SCOPE / PENDING OWNER REVIEW; roster implemented | Write endpoints exist, but no Profile member directory for safe usable add-target selection. No guessed identities or global User directory; complete consumer scope needs separate review |
| Invitation management/recipient UI | OUT OF CURRENT TASK SCOPE / PENDING OWNER REVIEW | Backend APIs and independent recipient proof exist; account verification never implies invitation acceptance. Owner explicitly defers this frontend integration |
| Task/Subtask/create/edit/assignment/Start | DONE — current isolated UI verified | Existing hierarchy max3 child levels, tenant-scoped metadata and current-assignee Start |
| Deadline/priority/filters/pagination | DONE — current isolated UI verified | Existing nullable aware deadline and priority choices; no status/deadline cascade |
| Deliverable/Review/changes/resubmit/approve | DONE — current isolated UI verified | Five API03A hints plus unchanged locked services; text/file_url only, no upload/edit/delete storage API |
| Comment/Notification | DONE — current isolated UI verified | Current author edit/author-or-manager soft-delete, tombstone/cache redaction and own readable feed/count/read |
| Dashboard | DONE — current isolated UI verified | Real accessible Profile overview and navigation; no fabricated analytics or aggregate API |
| Full cohesive UI journey | DONE current isolated UI | Manager creates Task/Subtask and assigns parent; Editor starts/submits, reviewer changes/approves parent; child stays PENDING. Comments/notifications and same-browser identity switch verified; exact evidence in HANDOVER |
| Local environment startup | DONE automated non-mutating verification | Safe launcher, existing stable ignored .env/venv, Django check and READ ONLY PostgreSQL connection; actual Django/Vite startup/proxy health/CSRF/anonymous boundaries pass; manual Owner check pending |
| AI Smart Task Generator / Feedback Analyzer | OUT OF SCOPE — design only | Readiness notes below; no SDK/provider/endpoint/schema/background job |
| Project/Client Portal/Finance/Payroll | OUT OF SCOPE | Project remains PENDING OWNER DECISION; no changes to these modules |

DONE source means implementation inspected, not that a historical test is
accepted as current runtime proof. Final status must distinguish completed
implemented journeys, remaining frontend scope/API gaps, configuration blockers,
automated browser verification and manual Owner checks. No all-product or
production-ready claim follows from this bounded task.

## Security and acceptance method

Every mutation success called UI E2E must be performed through React. Fixture
seed/negative direct API assertions are named separately. PostgreSQL fixtures,
mail adapter and all unsafe browser tests stay in owned disposable databases.
No persistent development login or business mutation is authorized.

Revalidate roles/assignment/lifecycle/state at the server, not through display
names or capability hints. Keep User/tenant-scoped caches, no unsafe automatic
retry, no stale deleted Comment, no old user's private screen after logout or
expiry. Check375/768/1440 and landscape, keyboard/native-dialog focus, axe,
readable labels/error summaries/loading/empty states and no horizontal overflow.

## SRS/HLD and outstanding product decisions

Repository preflight found requirements/architecture Markdown and legacy audit
references, not a separately named current SRS/HLD or approval artifact. No claim
of lecturer approval is made. ORIGINAL_REQUIREMENTS describes downstream client
approval/finance; approved internal Review completion is the current operational
boundary and must not be presented as implementing those downstream workflows.

PROJECT_ARCHITECTURE_REVIEW.md remains authoritative for the pending proposal:
Task stays in monthly Workspace; any future optional Project grouping must
reconcile accepted Profile/Client ownership across months. Do not introduce a
mandatory Workspace-owned Project or change Task.Workspace in this MVP task.

## AI integration readiness — proposal only

| Future feature | Reuse | Data/API dependencies and review boundary |
|---|---|---|
| Smart Task Generator | Authorized Workspace Task list/create dialog, Task/Subtask hierarchy, deadline/priority forms | Requirement input → preview of proposed hierarchy/priority/deadline → editable human confirmation → existing task permissions rechecked. No estimated_duration field exists; duration units/storage and atomic batch/idempotency/partial-failure contract require separate design. Never let a model write DB directly |
| Feedback Analyzer | Authorized Task Detail Review feedback, Deliverable revisions, paginated Comment thread | User selects authorized feedback/revision sources → summary/issues/proposed edits with source references → human review before any Task/Subtask creation. Need bounded full-source collection (not only current page), citation integrity, revoked/deleted content exclusion and stale revision handling |

Both need strict JSON output schema validation before preview: reject unknown
fields, invalid choices/dates, excessive item counts, cycles/depth overflow and
foreign IDs; recheck all values and live authority after human confirmation.
No free-form model output may become a command or unchecked database mutation.
Both need a separately approved backend/provider contract: tenant-aware data
minimization, prompt-injection handling, explicit input/output limits, server-side
credentials, cost/rate budgets, timeouts, error/retry/cancellation policy and audit
metadata without private prompt/token leakage. Provider choice, consent/retention,
estimated-duration schema and AI authorization are not decided by these notes.
No AI control, fake preview, SDK/key/network call or migration is added here.

## Local startup and final evidence

See FRONTEND_GUIDE.md for the two-terminal procedure. The launcher uses the
existing Windows venv and ignored .env, never guesses credentials, mutates the
database or applies migrations. Owner configuration is now validated and actual
local non-mutating connectivity verified. Synthetic guard tests are reported
separately; no persistent development login, real email delivery or manual
browser verification is claimed. Exact configuration was moved from the supplied
example into ignored .env without generating/changing credentials.

Final verification: frontend395/395 across14files (15.94s), TypeScript/Biome52/
productionbuild6.65s PASS/native exits0; safe launcher13/13 PASS/native0. Five
real isolated browser suites total22/22 PASS (acceptance1,account1,collaboration7,
work7,foundation6), all native launcher/Playwright/backend exits0 and owned
cleanup verified. Current axe0/focus/overflow at four viewports; three new PNGs
visually inspected. Existing backend485/485 remains historical, not rerun; all
144 protected source hashes and dependency locks unchanged. Before/after read-only
development counts match35 migrations/3 Users/2 Sessions/0 business rows. No
persistent login/fixtures/migrate. Exact run IDs/evidence/continuation are in
HANDOVER.md. AUTOMATED VERIFIED / MANUAL OWNER CHECK PENDING. Real email/remote
CI/production unverified. STOP at OWNER REVIEW GATE; no automatic next task.

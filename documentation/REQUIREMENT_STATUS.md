# HUSTLYTASKER REQUIREMENT STATUS

Last updated: 2026-10-28

## Quy ước đánh giá

- `COMPLETE`: đã triển khai và được kiểm chứng bằng lệnh chạy hoặc test phù hợp.
- `ACCEPTED`: quyết định kiến trúc/nghiệp vụ đã được owner phê duyệt; không tự
  đồng nghĩa mọi phần của kiến trúc đích đã được implement.
- `PARTIAL`: đã có một phần code/schema nhưng chưa hoàn thành luồng nghiệp vụ hoặc chưa đủ test.
- `DESIGN READY — PENDING APPROVAL`: deliverable thiết kế đã đủ để review nhưng
  còn quyết định của owner và chưa cho phép implementation; không đồng nghĩa
  với `COMPLETE` hay `Accepted`.
- `NOT STARTED`: chưa có implementation trong source hiện hành.
- `BLOCKED`: không thể tiếp tục nếu chưa có quyết định hoặc dependency bắt buộc.
- `UNKNOWN`: chưa đủ bằng chứng để kết luận.

Source of truth cho trạng thái là source code, migration đã áp dụng và kết quả kiểm thử. `documentation/` mô tả định hướng hiện hành. `reference/original_document/` là audit của hệ Next.js/Prisma cũ và chỉ được dùng để kế thừa business rules, không phải yêu cầu đổi Django sang Spring Boot hoặc công nghệ khác.

Current checkpoint: **HT-AI-P4-01 — DESIGN COMPLETE / PENDING OWNER APPROVAL**.
Owner newly requests two AI capabilities: Smart Task Generator and Feedback
Analyzer. This is an architecture/security/provider/contract design task only;
it does not make either feature implemented or retroactively complete an Fxx
requirement. [AI_ARCHITECTURE_DESIGN.md](AI_ARCHITECTURE_DESIGN.md) separates
approved boundaries from provider/model, authority, budget and persistence
proposals that still require Owner approval.

Generator needs human preview/edit/confirmation before existing Task services;
Analyzer returns selected-source analysis without Review/Task/Comment/Notification
mutation. Current Task priority/deadline/depth/tenant/workflow constraints stay.
No estimated-duration, Project or new role is added. Shared adapter/strict JSON,
data minimization, synthetic-only unpaid demo, cost reservations and durable
idempotency are designed, not implemented. Final design checks preserve209
runtime hashes/path set with only8 docs changed. Five JSON blocks parse and
two canonical schemas/three examples were checked through a limited in-memory
keyword validator plus DAG/depth/citations; this is not full JSON Schema engine
or application testing. Cost arithmetic, 20 local links and normal git diff
--check pass. No new application tests/provider quality/live result is claimed.
No runtime/.env/database/key/SDK/billing action is part of this task. Historical
FE04395/22/13 and backend485 evidence below is retained under its original scope.
AI implementation remains NOT STARTED. Stop at OWNER REVIEW GATE; proposed
provider/model/roles/caps/schema/retention decisions need explicit approval.

### Historical completed FE04 checkpoint

Historical checkpoint: **HT-FE-P3-04 — COMPLETE / OWNER REVIEW GATE**. Owner
confirms account lifecycle and current Workspace/Task/Review/Comment/Notification
as the accepted MVP. Invitation UI, Profile Creation, membership candidate API
and remaining onboarding/management are OUT OF CURRENT TASK SCOPE / PENDING
OWNER REVIEW. They remain product requirements rather than removed features.

Existing-API registration/recovery/own-verification UI, safe local launcher and
cohesive browser specs/test-only locmem adapter are implemented. Private root
.env now contains the exact Owner-provided values; example secrets are blank.
ValidateOnly, existing venv Django check and Django READ ONLY PostgreSQL
connection pass with exit0:16.14/hustlytasker_db, pending migrations0,
35 records/3 Users/2 Sessions/0 checked business/token/Notification/Audit rows.
Current frontend395/395 PASS15.94s/typecheck/Biome52/build6.65s exits0. Acceptance
1/1 PASS43.6s, account-security1/1 PASS22.4s, collaboration7/7 PASS1.2m,
work7/7 PASS1.0m and foundation6/6 PASS36.3s total22/22, with actual native/
Playwright/backend exits0 and owned cleanup. Local Django/Vite
non-mutating smoke PASS, orchestrator0 and intentional child server stops-1;
AUTOMATED VERIFIED / MANUAL OWNER CHECK PENDING. No new backend/schema/auth/RBAC or
downstream-domain approval. Matrix/AI design-only notes are in
FRONTEND_MVP_ACCEPTANCE.md; older results below are historical baseline. Current
four-size axe0/keyboard/focus/responsive and safe PNG review pass. No bounded-MVP
implementation blocker remains.144 protected assets and development35/3/2/0
are preserved. REAL EMAIL DELIVERY NOT VERIFIED; remote CI/production/manual
Owner remain unverified. Application backend485 tests are historical, not rerun.

### Historical completed API03A checkpoint

Historical checkpoint: **HT-API-FE-P3-03A — COMPLETE / OWNER REVIEW GATE**.
**HT-FE-P3-03 — IMPLEMENTATION COMPLETE.**

Owner approved the limited read-contract/frontend extension. Source resolves
Submit identity/state, Review non-self/latest/state and existing-Comment author
capability gaps through five required read-only booleans: Task.can_submit,
Deliverable.can_approve/can_request_changes and Comment.can_edit/can_delete.
Each uses authenticated request, verified tenant context and existing service
predicates; no role, permission, workflow, model or migration is added.

Frontend uses these hints for real Submit/Approve/Request Changes forms and old
Comment edit/delete after reload/pagination. No guessed identity or mounted-only
ownership proof remains. Server mutations revalidate every check; existing
SessionAuthentication, CSRF, tenant caches and tombstone privacy remain.

Current targeted isolated PostgreSQL95/95 PASS13.020s, run
a718df8ac97a4813aa6c2aebfff0ccd8, actual native/Python exits0 and owned cleanup.
Current frontend356/356 PASS41.49s (12files), typecheck/lint46/build6.69s PASS,
exits0. Full isolated PostgreSQL485/485 PASS231.054s, run
3b2abcd913324644b6240bfc49ca1c18, actual native/Python exits0/DjangoOK/owned cleanup.
Current real browser collaboration7/7 PASS1.3m
(ff6abc6459954d6d83f47ec94c426a62), Workspace/Task/Start7/7 PASS1.1m
(3074e74939f84f3b8039665dab7196ba) and Auth/CSRF/tenant6/6 PASS43.0s
(c125145b536b480badeccfba582f4c90); actual native/Playwright/backend exits0 and
owned cleanup. Real React Submit/Approve/Request Changes and existing-comment
edit after reload/page2 pass. Four-size axe0/keyboard/focus/overflow pass;
24 collaboration screenshots retained and three form PNGs visually reviewed.

All three gaps and accepted FE03 criteria pass. Fresh read-only development
remains35 migrations/3 Users/2 Sessions/0 checked business/token/Notification/
Audit rows;137 protected source hashes unchanged. No new schema/migration,
persistent fixture or production action. No implementation blocker remains;
real email, remote CI and production remain unverified. Stop at OWNER REVIEW
GATE; Project stays PENDING OWNER DECISION and AI remains outside scope.

### Historical FE03 partial checkpoint before HT-API-FE-P3-03A approval

Historical checkpoint: **HT-FE-P3-03 — PARTIAL — API GAP / OWNER REVIEW**.

The existing frontend now integrates Deliverable/revision/nested Review reads,
Comment thread/composer/scoped author actions/manager soft-delete and personal
Notification preview/count/feed/mark-read with `/notifications`. User/tenant/Task
cache keys, SessionAuthentication/CSRF, existing role boundaries and shared
design master remain in use. No backend/model/migration/security-setting change.

The verified `FE03_CONTRACT_MATRIX.md` limits acceptance: Submit metadata does
not prove current assignee in WORKING; Review role metadata does not prove
non-self/latest/state authority; old Comment author membership IDs cannot prove
the current User. These controls remain unavailable. Only exact new comment UUIDs
from a legitimate POST in the current mounted User/scope permit own edit/delete;
that proof is discarded on remount/logout/context change. Manager moderation
uses the existing manager capability and tombstones redact deleted content.

Frozen frontend322/322 PASS (21.69s); focused106 contracts/client,27 collaboration
and12 notifications PASS. Typecheck, Biome44 files and build13.75s PASS. Current
real collaboration7/7 (1.4m; ca613d41c174462c9375f03c201ac4c8) and Workspace/Task/
Start regression7/7 (1.6m; f97f35926ad24bc2abb174f9a4edd83d) PASS with actual
native/Playwright/backend exits0 and owned cleanup. Axe0 at four viewports,
keyboard/overflow and four representative PNG visual reviews pass.144 protected
backend/config hashes and lock unchanged; backend448 stays historical. Existing
API-driven Submit/Review tests do not imply blocked UI actions are implemented.
Current foundation Auth/CSRF/tenant6/6 PASS (55.6s), run
f7f4970fb102434699fcd26c9ef9d8e2, with actual exits0/owned cleanup. Fresh read-only
development35 migrations/3 Users/2 Sessions/0 checked business/token/Notification/
Audit rows and0 owned frontend test containers/networks verify preservation.
All unblocked UI/test work is verified. Keep FE03 partial for the core API gaps
and stop at Owner review. Proposed HT-API-FE-P3-03A would add bounded Submit/
per-Deliverable Review/per-Comment edit-delete hints only after separate approval.

### Historical completed API extension checkpoint before FE03 authorization

Historical checkpoint: **HT-API-FE-P3-02A — COMPLETE / OWNER REVIEW GATE**.
**HT-FE-P3-02 — IMPLEMENTATION COMPLETE.** Both approved API gaps are resolved.

Owner approved resolving the two FE02 gaps through three additive read fields:
Task.can_start and manager-roster display_label/is_assignable. The request and
verified Workspace context bind actual TaskAssignment.User identity; no client
actor ID or email/name identity matching is trusted. Start keeps existing active
Editor/ASSIGNED/assignment predicates and locked mutation revalidation. Roster
eligibility matches active User/Profile MEMBER/Workspace MEMBER and lifecycle
rules; labels use full name or safe membership code, never username/email fallback.
Existing endpoint visibility/pagination, authentication, schema and workflow stay.

Frontend Start/label/eligibility integration uses existing shared components and
tenant cache keys. Final targeted backend91/91 PASS (8.358s), full PostgreSQL
448/448 PASS (199.251s), frontend targeted107/full224 PASS (10.20s), typecheck/
lint36/build6.42s PASS. Current isolated real work-browser7/7 and foundation
Auth/CSRF/tenant6/6 PASS (36.3s), with actual native/Python/Playwright/backend
exits0 and owned cleanup verified. All accepted FE02/extension criteria pass.
Fresh read-only development stays35 migrations/3 Users/2 Sessions/0 business
rows;135 protected model/service/schema/config assets unchanged. No persistent
fixture/login/write/migration, schema or production action occurred. No remaining
blocker within scope. Stop at Owner review; Project/AI and HT-FE-P3-03 retain
their gates, with no automatic next task.

### Historical FE02 partial checkpoint before HT-API-FE-P3-02A

The following gap description and201/7/6 results predate the approved extension.

Historical checkpoint: **HT-FE-P3-02 — PARTIAL — API GAP / OWNER REVIEW**.

Owner-authorized source extends the existing SPA with Workspace create/edit/
archive/restore and Task list/detail/create/edit/assignment, direct Subtask
creation/navigation, existing priority/deadline and paginated server filters.
The existing design master, SessionAuthentication, CSRF and server tenant/RBAC
rules are retained. Verified scoped OPTIONS POST metadata and archive state are
UI hints only; current server permissions govern every write. Assignment choices
are sanitized ProfileMembership IDs, with final Profile/Workspace eligibility
checked by the backend rather than inferred from a display name or global ID.

START UI is **BLOCKED / API GAP**: current User ID and assignment membership ID
cannot be safely mapped through the available contracts. Role-only OPTIONS
authorization does not prove current-assignee identity. No new backend API is
included; Owner review must separately scope the missing contract. CANCELLED
exists in current source as a legacy status and is read-only in the UI, without
a cancel action or a new five-state workflow transition.

New mocked and seven isolated real-browser cases exist; the shared integration
runner separates them from the preserved six foundation cases in fresh owned
database/runtime runs, without changing throttles. Current typecheck/lint 36/
build 7.01s, mock 201/201 (11.35s), real work 7/7 (56.5s) and foundation 6/6 (34.2s) PASS.
Each actual launcher/Playwright/backend exit0 and owned cleanup verified;
responsive/axe/keyboard and representative PNG visual checks passed. These
results cover implemented surfaces, not the missing START/identity contract.
Read-only development confirms PostgreSQL16.14,35 migrations,3 Users/2 Sessions
and0 checked business/token/notification/Audit rows. No persistent fixture,
login or migration was performed. Project remains PENDING OWNER DECISION;
no adjacent module starts automatically. Stop at OWNER REVIEW GATE with partial
status while the START gap remains.

### Historical completed frontend checkpoint — HT-FE-P3-01 — 2026-10-26

The foundation evidence below predates the separate HT-FE-P3-02 authorization.

Historical checkpoint: **HT-FE-P3-01 — IMPLEMENTATION COMPLETE / OWNER REVIEW GATE**.

Owner-authorized frontend source now provides one strict TypeScript React/Vite
SPA with a shared design system, layout/routes, typed same-origin API client,
SessionAuthentication/CSRF login/logout/me and Profile/Workspace read-only UI.
Final strict typecheck, Biome lint24 files, production build6.67s and full
frontend mocked96/96 (4 files,8.60s) PASS. Separate real isolated Django/
PostgreSQL/Chrome6/6 PASS40.7s with actual launcher/Playwright/backend exits0
and owned database/container/two-network cleanup. Responsive375/768/1440 and
812×375 landscape, keyboard/native-dialog and axe WCAG2/2.1 AA checks PASS with
0 violations;13 screenshots retained and visually reviewed. Interactive manual
browser testing and authenticated persistent-development flows were not run.
Final development35 migrations/3 Users/2 Sessions/0 checked business rows and143
protected backend/config/harness hashes unchanged. Backend415/415 is historical,
not rerun because no backend code changed. Source privacy hardening clears
private tab titles after identity loss and keeps fatal fallback Router-independent.
The design master documents actual ui-ux-pro-max research and selected tokens.
No business write UI, backend/schema/data change, Project/AI or production
deployment is included. Documentation/HANDOVER updated; no blocker remains.
HT-FE-P3-02 remains pending separate Owner authorization. Real email delivery,
remote CI and production deployment are unverified; stop at OWNER REVIEW GATE.

### Historical completed backend checkpoint — HT-DB-P1-11 — 2026-10-26

Historical checkpoint: **HT-DB-P1-11 — COMPLETE / OWNER REVIEW GATE**.

DONE: approved development-only application of tasks.0004 followed by
notifications.0002, each exactly once after verified backup/restore rehearsal.
Development now has 35 migration records, 8 Comment/12 Notification columns and
44 valid orphan-free FKs. CHECKs/indexes/partial UNIQUE/nullability/defaults
verify; no guessed mapping or schema drift. Exact legacy rows remain unchanged:
3 Users/2 Sessions, 0 business/token/Audit rows and metadata 23/92/7. No source,
Authentication, RBAC or Task/Review policy changed in this rollout.

Development READ ONLY smoke: 67 anonymous requests plus 28 serializer-only checks
PASS without login/fixture/email/row changes/HTTP 500. Authenticated success and
mutations are reserved for isolated PostgreSQL tests. Current post-rollout
Comment 40/40 (13.140s), Notification 34/34 (8.431s), Task/Review 128/128
(41.694s), security/RBAC 253/253 (224.745s) and full PostgreSQL 415/415
(259.978s) PASS. All five actual launcher/Python exits are 0; Django OK,
dependency/system/model-drift/graph/full-chain and owned cleanup PASS. Final
schema/inventory/exact legacy-row comparison and backup size/hash recheck PASS.
Owned rehearsal DB/container copy removed; host backup retained. No disposable
test resources remain; all 143 protected asset hashes unchanged. No blocker.
The prior 415/415 implementation run below is historical. See HANDOVER.md for
backup, apply times and evidence. Project remains PENDING OWNER DECISION;
stop at OWNER REVIEW GATE. Proposed next step is Project A/B′ scope review,
with no automatic implementation. Real email delivery/remote CI remain unverified.

### Historical implementation checkpoint — HT-COM-P2-06 — 2026-10-25

The pre-rollout pending-migration state below is superseded by HT-DB-P1-11.

Historical checkpoint: **HT-COM-P2-06 — IMPLEMENTATION COMPLETE — PENDING
DEVELOPMENT MIGRATION APPROVAL / OWNER REVIEW GATE**.

Source now implements scoped Task/Subtask Comment CRUD and typed personal
in-app Notifications. Current Comment **40/40 (6.919s)**, Notification
**34/34 (5.401s)**, Task/Review **128/128 (22.637s)**, security/RBAC
**253/253 (165.756s)** and full PostgreSQL **415/415 (191.226s)** PASS. All five
native launcher/Python die-event exits are 0; Django OK, dependency/system/
drift/graph/full-chain and owned cleanup checks pass. The older 341/341 result
below is historical, not new-feature evidence. Final read-only development stays
at 33 migrations, 3 Users/2 Sessions, 0 Comment/Notification/business/token/Audit
rows. New tasks.0004 and notifications.0002 are not applied or authorized for
persistent development in this task. Project remains PENDING OWNER DECISION.
New columns/migration records remain absent; no disposable test DB/container/
network remains. Proposed next step is Owner review, then explicitly authorized
controlled development rollout of these exact two migrations.

Historical completed rollout checkpoint: **HT-DB-P1-10 — COMPLETE / OWNER REVIEW GATE**.

Exact tasks.0003 applied once to the approved PostgreSQL 16.14 development
target at 2026-10-25 03:43:19.588793 UTC after fresh backup/restore rehearsal.
Development now has 33 migrations, 11 Task columns, 40 valid FKs/no orphans,
validated nullable UUID parent/self-parent CHECK/FK and ready/valid lookup index.
All legacy rows compare exactly before/after: 3 Users/2 Sessions, 0 checked
business/security-token/AuditLog rows; metadata 23/92/7 unchanged. Direct smoke
passes 51 read-only requests plus 16 serializer-only checks, no fixture/login/
email/mutation/500. Authenticated success/mutations are NOT TESTED ON PERSISTENT
DEVELOPMENT. Current isolated Task 88/88 PASS (11.780s), related regression
253/253 PASS (162.615s), full PostgreSQL 341/341 PASS (170.987s). Each run has
actual launcher exit 0/Python-container die-event exit 0, Django `OK` and owned
DB cleanup. Final system/drift/migration checks, empty plan and exact post-test
legacy-row comparison PASS. Fresh host backup remains unchanged and retained;
only verified rehearsal/temp copy removed. No test/rehearsal resources remain.
All 129 baseline backend/configuration/Docker/harness asset hashes unchanged.
Project stays PENDING OWNER DECISION. No adjacent task starts automatically.

Historical preceding implementation checkpoint: **HT-TASK-P2-05 — IMPLEMENTATION COMPLETE — PENDING
DEVELOPMENT MIGRATION APPROVAL / OWNER REVIEW GATE**.
Task hierarchy/deadline/priority implementation is present. Isolated Task API
42/42 (4.990s), hierarchy/existing workflow43/43 (4.770s), and migration2/2
(1.465s) pass with dependency/system/model-drift/migration-chain checks.
Workspace/RBAC122/122 (60.495s) and full PostgreSQL341/341 (174.058s) PASS.
Django reports `OK` and owned-test-DB removal is verified in logs; the wrapper
did not retain the child exit code, so no launcher exit-0 claim is made.
At that earlier gate, `tasks.0003_task_hierarchy` was isolated-test-only and
development had 32 migrations, 3 Users, 2 Sessions, zero verified Users/tokens
and zero checked business/AuditLog rows; parent column/migration record were
absent. No disposable test resources remained. Persistent rollout required
the later separate HT-DB-P1-10 authorization and is now completed above.

The Owner replaced the proposed bundled HT-PROJ-P2-05 with authorized
HT-TASK-P2-05 plus **PROJECT ARCHITECTURE REVIEW — PENDING OWNER DECISION**.
`PROJECT_ARCHITECTURE_REVIEW.md` compares A/B and an optional cross-month
Profile/Client-scoped B′. No Project model/API/migration is included.

Historical preceding checkpoint: **HT-TEST-P1-01 — COMPLETE / OWNER REVIEW GATE**.
**LOCAL TEST HARNESS VERIFIED**. Dedicated isolated test
settings, shared guarded PostgreSQL runner, PowerShell/Docker local command,
and backend GitHub Actions workflow are implemented. Historical tooling evidence
is 14/14 harness guard tests, targeted API 10/10, and full PostgreSQL 286/286
(166.382s) PASS with migration-chain/owned-DB cleanup checks. Failure exit-code,
owned-interruption cleanup and wrong-repository refusal checks pass. Local
PowerShell/Compose/actionlint/diff checks and exact original User/Session
preservation pass. **CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED.**

HT-DB-P1-09 remains the completed rollout baseline: `accounts.0002` applied
once, 32 migrations, 3 active Users/2 Sessions preserved, and zero verified
Users/token/business/AuditLog rows. Its historical 286/286 result does not
substitute for the current Task hierarchy gate. That completed tooling task
changed no development migration, business rule, authentication mechanism or
API contract. HT-TASK-P2-05 adds the Task hierarchy contract described above.

## Tổng quan hiện tại

Dự án đang ở `PHASE 3 - Frontend Foundation`; Owner đã phê duyệt
HT-API-FE-P3-03A để đóng ba API GAP của HT-FE-P3-03; cả hai phạm vi hiện đã
hoàn thành implementation và dừng OWNER REVIEW GATE. Source có năm capability
read-only và form Submit/Approve/Request Changes, Comment cũ edit/delete theo
quyền server. Backend targeted95/full485, frontend356/typecheck/lint/build và
real UI browser7/7/6 đã PASS với exit0/cleanup; responsive/axe/focus và bảo toàn
development đã kiểm chứng. Không đổi models, schema, migrations, service
business rules, RBAC hoặc authentication. Backend
history below remains a completed historical baseline:
`HT-RBAC-DESIGN-P0-01` đã
`COMPLETE / ACCEPTED — APPROVED BY OWNER DELEGATION`; `HT-RBAC-P1-03` Tenant
Access Context and Scoped Service Foundation đã hoàn thành, sau đó Owner cho
phép triển khai `HT-API-P1-04`. Bốn Profile/Workspace read route, DRF tenant
permissions, scoped querysets và pagination đã hoàn thành. Owner đã mở
`HT-DB-P1-05` để rollout có kiểm soát migration hiện hữu trên development;
task đó đã hoàn thành với full PostgreSQL suite 101/101. Owner sau đó mở
`HT-WORK-P2-02`, rồi phê duyệt rollout `workspace.0003` qua `HT-DB-P1-06`.
Sau review gate đó, Owner mở `HT-TASK-P2-03`, rồi phê duyệt controlled
development rollout qua `HT-DB-P1-07`. Owner tiếp tục mở `HT-INV-P2-04`.
Sau khi implementation đạt review gate, Owner mở controlled rollout
`HT-DB-P1-08`. That rollout is the immediate completed baseline. The Owner
subsequently authorized HT-AUTH-P1-02 implementation, now complete, and then
controlled development rollout HT-DB-P1-09 as recorded above.
Workspace write/membership, Profile/Workspace lifecycle, monthly period và
membership soft revoke/reactivate đã triển khai; `workspace.0003` đã được
backup/rehearsal và apply lên development. Direct smoke và full PostgreSQL
169/169 của gate trước PASS. Task/Deliverable/internal Review workflow mới đã
implement trong source; `tasks.0002`/`reviews.0002` đã được backup/rehearsal và
apply trên development. Current Task 33/33, Auth/API 29/29, Workspace 140/140
và full PostgreSQL 202/202 đều PASS. Profile Invitation hiện đã implement model,
additive `workspace.0004`, locked services, mail-delivery abstraction, RBAC/API,
audit và tests; Invitation 39/39, regression liên quan 173/173 và full
PostgreSQL 241/241 PASS tại implementation gate. `workspace.0004` hiện đã được
backup/rehearsal và apply có kiểm soát trên development; schema/inventory và
fixture-free smoke đạt.
Current Invitation 39/39, Auth/API 29/29, Workspace/RBAC/Task/Review 173/173
và full PostgreSQL 241/241 đều PASS; từng test DB đã bị hủy. Production không
bị truy cập. Account verification/recovery is implementation-complete in
source and its additive migration is applied to approved development through
HT-DB-P1-09. Older counts/tests in this overview are historical. Owner then
authorized HT-TEST-P1-01 test tooling/CI standardization, whose local
verification is complete as recorded above. Remote GitHub execution,
real-provider verification,
remaining business APIs, frontend, and deployment are not complete.

## Nền tảng kỹ thuật

| Hạng mục | Trạng thái | Đã triển khai | Còn thiếu / vấn đề | Căn cứ |
|---|---|---|---|---|
| Dependency manifest | COMPLETE | Pinned manifests retained; existing Windows venv Python3.12.5 and Django check verified in FE04 with permitted access | Sandbox exit103 is an access limitation, not evidence of broken venv; production/runtime upgrades remain separate | `backend/requirements.txt`; `HANDOVER.md` |
| Django configuration | PARTIAL OVERALL — FE04 local automated verification PASS | Existing settings unchanged; ignored .env/PowerShell launcher validation/Django check, READ ONLY PostgreSQL connection and Django8000/Vite5174 non-mutating smoke pass; pending migrations0 | Manual Owner browser, production/trusted-proxy/static/deploy and real email provider remain unverified; orchestrator0, child stops intentionally-1 | `scripts/start-backend-dev.ps1`; `FRONTEND_GUIDE.md`; `HANDOVER.md` |
| Database migrations | PARTIAL — HT-DB-P1-11 DEVELOPMENT ROLLOUT COMPLETE | tasks.0004 then notifications.0002 applied once on approved development after verified backup/rehearsal; 35 records, valid CHECKs/indexes and 44 orphan-free FKs; legacy values preserved; full regression and final cleanup PASS | Other persistent targets unauthorized; other domain migrations absent | HT-DB-P1-11 operational evidence; `DATABASE_SCHEMA.md` |
| Business schema | PARTIAL | Existing hierarchy/workflow retained; Comment lifecycle/protected Task FK and nullable complete-or-legacy Notification context/event/recipient uniqueness now exist in approved development | Cross-row tenant checks remain validated service/query responsibilities; Task soft delete and other tenant domains absent | Task/Notification models; HT-DB-P1-11; `DATABASE_SCHEMA.md` |
| Tenancy/ownership design | COMPLETE / ACCEPTED | Owner đã phê duyệt 11 nhóm quyết định; HT-TASK-P2-03 tiếp tục chốt internal workflow trong đúng tenant boundary | Billing, public-link capabilities, retention duration và các domain action chưa implement vẫn defer sang task tương ứng; Client/Guest review và Payroll tách khỏi internal approval | `documentation/DECISION_LOG.md`; owner approvals 2026-10-16 và 2026-10-21 |
| RBAC/access/invitation design | COMPLETE / ACCEPTED | 14 nền RBAC được chốt; Task manager/reviewer contract và Profile Invitation role/identity/lifecycle contract đã được hiện thực hóa trong các slice được duyệt | Client/Guest capabilities, payroll pricing/eligibility và downstream domain details vẫn ở task riêng | `documentation/RBAC_DESIGN.md`; `DECISION_LOG.md`; HT-INV-P2-04 checkpoint |
| Django Admin | PARTIAL | User, Workspace, WorkspaceMember, Task, TaskAssignment, TaskComment; Task domain hiện inspection-only; Workspace hard delete bị chặn để không cascade workflow history; mapped Profile/period và lifecycle/member fields vẫn protected/read-only | Profile/ProfileMembership và 8 model trước chưa register; chưa có tenant-scoped Admin; aggregate CASCADE vẫn tồn tại ở schema và chỉ được chặn trên current Admin/API surfaces | `backend/apps/{tasks,workspace}/admin.py`; source review 2026-10-21 |
| DRF/API foundation | PARTIAL OVERALL — accepted capability extension COMPLETE | Existing scoped APIs/applied schema and five request-bound hints retained; historical API03A targeted95/full485 PASS; FE04 leaves backend unchanged and verifies current consumers separately | Authenticated mutations not tested on persistent development; adjacent APIs absent | HT-API-FE-P3-03A source/tests; `API_DOCUMENTATION.md`; `HANDOVER.md` |
| Authentication/RBAC | PARTIAL OVERALL — FE04 accepted regression VERIFIED | Existing identity/tenant/manager/Editor/author authority, locked services and Session/CSRF retained; current account lifecycle and five real browser suites22/22 PASS | Real production email/distributed throttle/deploy remain separate; no new auth or role policy | Existing access/services; `RBAC_DESIGN.md`; `HANDOVER.md` |
| Automated tests | FE04 ACCEPTED SCOPE VERIFIED | Current frontend395/395 PASS15.94s/typecheck/lint52/build6.65s exits0; five real browser suites22/22 actual exits0/owned cleanup,13 launcher guards/local checks/axe0 pass;144 hashes match | Backend485 is historical baseline; remote CI/interactive manual Owner/real email/production unverified | `FRONTEND_MVP_ACCEPTANCE.md`; `PROGRESS.md`; `HANDOVER.md` |
| Frontend | PARTIAL OVERALL — FE04 accepted MVP COMPLETE | Existing work/collaboration preserved; registration/recovery/own-verification UI and cohesive real acceptance verified with shared UI/UX master/protected client; no bounded-MVP blocker | Invitation/Profile Creation/member candidate/onboarding OUT OF CURRENT TASK SCOPE pending Owner review; retained product requirements. AI/downstream domains/production remain separate | `frontend/`; `FRONTEND_MVP_ACCEPTANCE.md`; `HANDOVER.md` |
| Docker/deployment/CI | PARTIAL — TEST BASELINE IMPLEMENTED | Development Compose retained; separate tmpfs PostgreSQL 16/Python 3.12 local test project/dependency-only image and PR/push-main backend CI workflow; source read-only, no development volume/credentials, contents-read/no deploy; local full/failure/cleanup/actionlint PASS | CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED; production backend image/deploy/monitoring still absent | `docker/compose.test.yml`; `docker/Dockerfile.test`; `.github/workflows/backend-ci.yml`; `README.md` |

## Trạng thái yêu cầu nghiệp vụ F01-F16

| ID | Module | Trạng thái | Đã triển khai | Còn thiếu / vấn đề |
|---|---|---|---|---|
| F01 | Authentication | PARTIAL OVERALL — FE04 accepted account lifecycle UI VERIFIED | Existing Session/verification/reset backend and applied accounts.0002 retained; register/forgot/reset/own-verification UI with masked memory-only credentials/no auto-login; current frontend395/395 and five real browser suites22/22 pass | Locmem proves test delivery only: REAL EMAIL DELIVERY NOT VERIFIED. Timing equalization, logout-all/deactivation, real provider/distributed throttle and production remain separate |
| F02 | Profile & Workspace | PARTIAL OVERALL — accepted Workspace UI retained | Existing monthly Workspace/lifecycle/roster and Task assignment UI retained; local development schema remains35 records with no FE04 migration | Profile Creation/member candidate API/general onboarding-management OUT OF CURRENT TASK SCOPE / PENDING OWNER REVIEW; retained product requirements, no fabricated endpoints |
| F03 | Membership Invitation | PARTIAL — backend/rollout retained, UI OUT OF CURRENT TASK SCOPE | Existing invitation consent/token/role-ceiling/identity/locked onboarding/audit APIs and applied workspace.0004 retained | Owner explicitly defers Invitation UI to separate review; it is not removed from product. Account verification does not replace independent recipient proof. REAL EMAIL DELIVERY NOT VERIFIED; production cache/retention/deploy remain separate |
| F04 | Task Lifecycle | PARTIAL OVERALL — FE04 accepted UI workflow VERIFIED | Existing hierarchy/workflow/Start/assignment retained; current real UI acceptance1/1 creates/assigns/starts/submits/changes/resubmits/approves through React; full five browser suites22/22 pass. API03A backend95/485 is historical only | No arbitrary transition or auto-completion. Legacy CANCELLED has no cancel action; downstream domains remain separate |
| F05 | Marketplace | NOT STARTED | Chưa có implementation | Publish/claim rules, concurrency guard, API và tests |
| F06 | Review Upload | PARTIAL OVERALL — accepted text/file_url backend and UI COMPLETE | Existing revisioned text/file_url API/read UI retained; Task.can_submit proves current assignee/state; real React Submit and targeted/full regression PASS | Only text/file_url backend, no upload/storage/media service; other target rollout unauthorized |
| F07 | Team Review Status | PARTIAL OVERALL — internal backend/rollout/UI COMPLETE | Existing manager review services, one decision per Deliverable and self/stale/concurrency guards retained; per-Deliverable hints and real React Approve/Request Changes/resubmission verified | Client/Guest approval and other target rollout remain separate |
| F08 | Guest Review Decision | NOT STARTED | Kiến trúc đã chốt GuestReviewLink tách khỏi Client Portal | Chưa có scoped hashed token, exact capabilities, expiry/revoke, decision flow hoặc throttle |
| F09 | Client Portal | NOT STARTED | Client/ShareLink hiện chỉ là schema primitive; target hỗ trợ account và secure link độc lập với internal membership | Chưa migrate Client→Profile, chưa có secure link replacement, portal/API/capabilities |
| F10 | Client Request Inbox | NOT STARTED | Chưa có model/code | Request intake, triage, conversion to task và permissions |
| F11 | Task Comments | ACCEPTED backend/rollout/FE03 CRUD scope COMPLETE | Existing4000-character/current-access CRUD, soft-delete/tombstone/audit retained. Server can_edit/can_delete author/moderation controls after reload/pagination and cache redaction verified by current unit/security/real browser tests | No rich text, mentions, revision history, realtime or retention expansion |
| F12 | Notifications | PARTIAL OVERALL — BACKEND/ROLLOUT AND FE03 UI VERIFIED | Existing five atomic events, recipient dedup/current-access projection and personal list/count/read API retained. FE03 User-keyed preview/badge/feed/filter/page/mark-read and safe Task navigation verified | No read-all, unread toggle, email/push/worker or retention expansion; restored access may reveal earlier valid feed rows |
| F13 | Payroll | NOT STARTED | Chưa có model/code | Payroll calculation, lock, approval/payment workflow và audit |
| F14 | Finance Invoice | PARTIAL | Invoice và Payment models; approved target places Invoice in one Workspace, same-Profile Client, Payment under Invoice | Target ownership chưa migrate; numbering/billing workflow, positive amount constraints, service/API/tests còn thiếu |
| F15 | CRM Share Link | PARTIAL | Client và ShareLink models; approved target puts Client in Profile and separates portal/review credentials | Tenant ownership chưa migrate; token hiện plaintext/có thể lộ qua `__str__`; thiếu hash/revoke/capability/expiry |
| F16 | Automation | NOT STARTED | Chưa có cron/webhook worker hiện hành | Job design, idempotency, authentication, monitoring và deployment |

## AI capabilities requested by Owner — 2026-10-28

These are new Phase4 requirements traced to the current Owner instruction, not
claims that the original F01–F16 already contain implemented AI runtime.

| Capability | Design status | Implementation status | Required gate |
|---|---|---|---|
| AI Smart Task Generator | DESIGN COMPLETE — PENDING OWNER APPROVAL | NOT STARTED | Approve authority/provider/data policy, strict proposal contract, durable confirmation/budget schema and P4-02 scope; no direct model mutation |
| AI Feedback Analyzer | DESIGN COMPLETE — PENDING OWNER APPROVAL | NOT STARTED | Approve feature authority/source coverage and P4-03 scope; selected-source citations, no automatic Review or Task action |
| Shared AI provider/cost/security foundation | DESIGN COMPLETE — PENDING OWNER APPROVAL | NOT STARTED | Approve numeric limits, persistence/retention, configuration and adapter choice; default disabled, no unapproved egress/paid fallback |

Current task does not change the F04/F06/F07/F11/F12 implementation or workflow
statuses. Project, Invitation UI/Profile Creation/onboarding, production, real
email and remote CI keep their existing separate scope/review limitations.

## Quyết định sản phẩm/kiến trúc còn cần chốt

**PROJECT ARCHITECTURE REVIEW — PENDING OWNER DECISION:** Task/Subtask,
deadline and priority continue independently under HT-TASK-P2-05. Choose
whether to defer Project or separately scope optional Profile/Client-owned
cross-month grouping. Literal Workspace-owned Project would require explicit
revision of accepted cross-month ownership. See `PROJECT_ARCHITECTURE_REVIEW.md`.
AI estimated duration remains a future proposal; no AI schema/provider is added.
Feedback Analyzer readiness now includes authorized Task/Workspace context,
Comments and existing Review/Deliverable revisions. Comments do not constitute
Review decisions. Full Comment text revision history, exact revision binding,
source citation/versioning and human-confirmed suggestion semantics remain
future data/API decisions; no AI writer or Suggestions table is implemented.
Retained soft-deleted bodies are not available to an AI consumer by default;
future retrieval must honor current authorization and the tombstone projection.
Notification failure intentionally rolls back business mutation/audit under the
chosen atomic policy; successful replay preserves existing notification read state.

The implementation review gate was followed by completed Owner-authorized
HT-DB-P1-10, which applied tasks.0003 after inventory, verified backup and
rehearsal. Current smoke, isolated regression/full suite and cleanup pass.
Stop at **OWNER REVIEW GATE**. Proposed next step is Project A/B′ scope selection
or another separately authorized roadmap task, not another tasks.0003 apply.
Project implementation remains unauthorized; no new domain starts automatically.

Không còn câu hỏi nào của review gate `HT-RBAC-DESIGN-P0-01`; 14 quyết định đã
được chốt qua Owner delegation và không được yêu cầu quyết định lại.

Các task sau vẫn phải chốt contract riêng trước implementation: payroll
pricing/eligibility và business trigger ngoài invariant “internal approval
không tự tạo Payroll/Payment”; full deactivation/standalone logout-all flow;
production email-provider/shared-cache
deployment cho Invitation; Invoice numbering/billing;
Client Portal/Guest Review exact capabilities/default expiry; retention legal
hold/purge; và project-wide response/error convention ngoài các mapping hiện
có. Policy migration vẫn là kiểm kê từng môi trường, không tự gán tenant
cho dữ liệu không xác định.

`HT-API-P1-04`, `HT-DB-P1-05`, implementation `HT-WORK-P2-02`, rollout
`HT-DB-P1-06`, `HT-TASK-P2-03` và rollout `HT-DB-P1-07` đã hoàn thành.
`HT-DB-P1-06` đã backup/rehearse/apply `workspace.0003` đúng development,
post-check schema/data, smoke request stack và rerun full regressions đạt;
production không bị tác động. `HT-TASK-P2-03` source implementation và
`HT-DB-P1-07` controlled development rollout đều đạt: backup/restore rehearsal,
explicit Tasks/Reviews 0002 apply, post-check, direct fixture-free smoke,
targeted suites và full 202/202. `HT-INV-P2-04` implementation tiếp theo đã
đạt Invitation 39/39 và full 241/241. Owner sau đó mở `HT-DB-P1-08`; fresh
backup/restore rehearsal, exact development apply 0004, schema/inventory
post-check và fixture-free smoke đã đạt. Current targeted/regression/full rerun
cũng đạt Invitation 39/39, Auth/API 29/29, Workspace/RBAC/Task/Review 173/173
và full 241/241. Đây là completed baseline **HT-DB-P1-08 — COMPLETE / OWNER
REVIEW GATE** ngay trước task hiện tại.

The Owner subsequently opened `HT-AUTH-P1-02 — Account Verification &
Recovery` and then separately authorized `HT-DB-P1-09`. The existing migration
is now applied to approved development; final full-suite verification,
cleanup, and documentation are complete. HT-DB-P1-09 is COMPLETE. Owner then
opened HT-TEST-P1-01, limited to test tooling and CI. Its local gates and
documentation are complete: LOCAL TEST HARNESS VERIFIED; CI WORKFLOW
IMPLEMENTED — REMOTE RUN NOT VERIFIED. That historical gate is followed by the
Owner-authorized HT-TASK-P2-05 and separate pending Project architecture gate
described above; the earlier proposed HT-PROJ-P2-05 bundle is superseded. See
`documentation/HANDOVER.md`, `RBAC_DESIGN.md`, and `DECISION_LOG.md`.

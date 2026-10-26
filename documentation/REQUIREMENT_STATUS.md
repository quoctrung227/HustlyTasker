# HUSTLYTASKER REQUIREMENT STATUS

Last updated: 2026-10-26

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

Current checkpoint: **HT-FE-P3-01 — IMPLEMENTATION COMPLETE / OWNER REVIEW GATE**.

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

Dự án đang ở `PHASE 3 - Frontend Foundation`, trong phạm vi HT-FE-P3-01
được Owner phê duyệt. Frontend source đã có, nhưng acceptance còn đang kiểm
chứng như checkpoint trên. Backend history below remains a completed baseline:
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
| Dependency manifest | COMPLETE | Manifest UTF-8/pinned; Django 6.1.2 và DRF 3.18.3; current container runtime pass `pip check` | Owner host shell báo venv hoạt động, nhưng Codex managed context exit 103 và không thấy base interpreter path; cached Python 3.12 container là fallback đã kiểm chứng | `backend/requirements.txt`; xác minh HT-DB-P1-05 ngày 2026-10-19 |
| Django configuration | PARTIAL | Secret/debug/hosts/DB/CSRF/security/mailer lấy từ environment; development/production fail-fast; production-like deploy check sạch | Chưa có giá trị production thật, trusted-proxy/static/deploy contract; secret cũ cần rotate nếu từng dùng ngoài local | `backend/config/settings.py`; `.env.example`; kiểm chứng Docker 2026-10-13 |
| Database migrations | PARTIAL — HT-DB-P1-11 DEVELOPMENT ROLLOUT COMPLETE | tasks.0004 then notifications.0002 applied once on approved development after verified backup/rehearsal; 35 records, valid CHECKs/indexes and 44 orphan-free FKs; legacy values preserved; full regression and final cleanup PASS | Other persistent targets unauthorized; other domain migrations absent | HT-DB-P1-11 operational evidence; `DATABASE_SCHEMA.md` |
| Business schema | PARTIAL | Existing hierarchy/workflow retained; Comment lifecycle/protected Task FK and nullable complete-or-legacy Notification context/event/recipient uniqueness now exist in approved development | Cross-row tenant checks remain validated service/query responsibilities; Task soft delete and other tenant domains absent | Task/Notification models; HT-DB-P1-11; `DATABASE_SCHEMA.md` |
| Tenancy/ownership design | COMPLETE / ACCEPTED | Owner đã phê duyệt 11 nhóm quyết định; HT-TASK-P2-03 tiếp tục chốt internal workflow trong đúng tenant boundary | Billing, public-link capabilities, retention duration và các domain action chưa implement vẫn defer sang task tương ứng; Client/Guest review và Payroll tách khỏi internal approval | `documentation/DECISION_LOG.md`; owner approvals 2026-10-16 và 2026-10-21 |
| RBAC/access/invitation design | COMPLETE / ACCEPTED | 14 nền RBAC được chốt; Task manager/reviewer contract và Profile Invitation role/identity/lifecycle contract đã được hiện thực hóa trong các slice được duyệt | Client/Guest capabilities, payroll pricing/eligibility và downstream domain details vẫn ở task riêng | `documentation/RBAC_DESIGN.md`; `DECISION_LOG.md`; HT-INV-P2-04 checkpoint |
| Django Admin | PARTIAL | User, Workspace, WorkspaceMember, Task, TaskAssignment, TaskComment; Task domain hiện inspection-only; Workspace hard delete bị chặn để không cascade workflow history; mapped Profile/period và lifecycle/member fields vẫn protected/read-only | Profile/ProfileMembership và 8 model trước chưa register; chưa có tenant-scoped Admin; aggregate CASCADE vẫn tồn tại ở schema và chỉ được chặn trên current Admin/API surfaces | `backend/apps/{tasks,workspace}/admin.py`; source review 2026-10-21 |
| DRF/API foundation | PARTIAL | Scoped Comment CRUD and own Notification list/count/read implemented; required development schema applied; SessionAuthentication/global deny-by-default retained; READ ONLY smoke 67 requests/28 serializer checks and current isolated full 415/415 PASS | Authenticated success/mutations not tested on persistent development; adjacent APIs absent | HT-COM-P2-06 source and HT-DB-P1-11 evidence; `API_DOCUMENTATION.md` |
| Authentication/RBAC | PARTIAL | Existing identity/tenant foundations reused; current managers/Editors comment, author-only edits and bounded moderation; own Notification feed revalidates Task access, no staff bypass; current security 253/253/full 415/415 PASS; no policy change in rollout | Existing production delivery/cache/account-lifecycle limits unchanged | Comment/Notification sources; HT-DB-P1-11; `RBAC_DESIGN.md` |
| Automated tests | LOCAL BASELINE COMPLETE; HT-FE-P3-01 VERIFICATION PASS | Last backend rollout full415/415 and related groups passed; unchanged backend was not rerun here. Current frontend strict typecheck/Biome24/build PASS, mocked96/96 (8.60s), separate real Django/PostgreSQL/Chrome6/6 (40.7s), actual launcher/Playwright/backend exits0 and owned cleanup PASS | Mocked and real evidence are distinct; remote CI and interactive manual-browser testing remain unverified | Frontend test modules/integration helpers; `PROGRESS.md`; historical backend runner evidence |
| Frontend | PARTIAL OVERALL — HT-FE-P3-01 FOUNDATION IMPLEMENTATION COMPLETE | Single React19/TypeScript6/Vite6 SPA, Router7/Tailwind4/Query5/Biome2, shared design system/shell/components, verified Session/CSRF/auth guards and read-only Profile/Workspace UI; typecheck/lint/build/mock96/real6/responsive/keyboard/axe PASS; docs refreshed | Broader business UI and deployment remain future tasks; no authenticated persistent-development or interactive manual-browser test. HT-FE-P3-02 requires Owner scope | `frontend/`; design-system/hustlytasker/MASTER.md; `HANDOVER.md` |
| Docker/deployment/CI | PARTIAL — TEST BASELINE IMPLEMENTED | Development Compose retained; separate tmpfs PostgreSQL 16/Python 3.12 local test project/dependency-only image and PR/push-main backend CI workflow; source read-only, no development volume/credentials, contents-read/no deploy; local full/failure/cleanup/actionlint PASS | CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED; production backend image/deploy/monitoring still absent | `docker/compose.test.yml`; `docker/Dockerfile.test`; `.github/workflows/backend-ci.yml`; `README.md` |

## Trạng thái yêu cầu nghiệp vụ F01-F16

| ID | Module | Trạng thái | Đã triển khai | Còn thiếu / vấn đề |
|---|---|---|---|---|
| F01 | Authentication | PARTIAL — IMPLEMENTATION & DEVELOPMENT ROLLOUT COMPLETE | Session auth plus verification/reset foundation; accounts.0002 development apply, legacy Users/Sessions and zero auto-verification preserved; current HT-DB-P1-10 related 253/253 and full 341/341 regression PASS | Timing not equalized; no standalone logout-all/deactivation, real-provider verification, or distributed throttle cache; production rollout not authorized |
| F02 | Profile & Workspace | PARTIAL | Foundation `workspace.0002`/`0003`, monthly Workspace/lifecycle/member manager và Invitation onboarding source đã có; `workspace.0004` development rollout đã xác minh | Chưa Profile creation/general membership API/domain-wide RBAC; mọi non-development rollout còn gated riêng |
| F03 | Membership Invitation | PARTIAL — CORE IMPLEMENTATION & DEVELOPMENT ROLLOUT COMPLETE | ProfileInvitation model/0004, consent lifecycle, role ceiling, digest token, per-invitation recipient proof, delivery abstraction, locked membership onboarding, audit, APIs/tests và controlled development rollout đã hoàn tất | Account verification signal now exists in source but Invitation deliberately keeps its independent proof contract; REAL EMAIL DELIVERY NOT VERIFIED; chưa inbox, shared production cache hoặc automated retention purge; non-development rollout chưa authorize |
| F04 | Task Lifecycle | PARTIAL — HIERARCHY IMPLEMENTATION & DEVELOPMENT ROLLOUT COMPLETE | tasks.0003 applied approved development; unchanged manager-only same-Workspace hierarchy, depth3/cycle/self guards, paginated API/planning fields and independent workflow; current Task 88/88 and full 341/341 PASS | Task soft delete, cancel transition, Marketplace/claim and Client approval absent; production/other targets remain unauthorized |
| F05 | Marketplace | NOT STARTED | Chưa có implementation | Publish/claim rules, concurrency guard, API và tests |
| F06 | Review Upload | PARTIAL | Revisioned Deliverable URL submission/history, uploader tenant attribution, status constraints và scoped API/service đã implement; required migrations đã apply development | Chỉ nhận `file_url`; actual upload/storage/media validation/processing chưa có; production/other target rollout chưa được authorize |
| F07 | Team Review Status | PARTIAL — INTERNAL SLICE & DEV ROLLOUT COMPLETE | Internal manager approval/request-changes, one Review per Deliverable, no self-review, stale/repeat/concurrency guards và Task/Deliverable synchronization; development rollout và full 202/202 PASS | Client/Guest approval độc lập chưa có; production/other target rollout chưa được authorize |
| F08 | Guest Review Decision | NOT STARTED | Kiến trúc đã chốt GuestReviewLink tách khỏi Client Portal | Chưa có scoped hashed token, exact capabilities, expiry/revoke, decision flow hoặc throttle |
| F09 | Client Portal | NOT STARTED | Client/ShareLink hiện chỉ là schema primitive; target hỗ trợ account và secure link độc lập với internal membership | Chưa migrate Client→Profile, chưa có secure link replacement, portal/API/capabilities |
| F10 | Client Request Inbox | NOT STARTED | Chưa có model/code | Request intake, triage, conversion to task và permissions |
| F11 | Task Comments | PARTIAL — FOUNDATION IMPLEMENTATION & DEVELOPMENT ROLLOUT COMPLETE | Reused TaskComment; scoped Task/Subtask CRUD, 4000-character validation, author/current-access edits, author/manager soft-delete/tombstones/audit, protected history; tasks.0004 applied; current Comment/migration 40/40 and full 415/415 PASS | Last-writer-wins edits, no full text revision history, mentions or automated retention; other targets unauthorized |
| F12 | Notifications | PARTIAL — FOUNDATION IMPLEMENTATION & DEVELOPMENT ROLLOUT COMPLETE | Typed tenant/Task/AuditLog event, five atomic producers, current eligible recipients, per-event/recipient dedup and own paginated/read/count API; notifications.0002 applied; current Notification/migration 34/34 and full 415/415 PASS | No HTTP POST idempotency key, email/push/worker or automated retention; hidden feed rows may reappear after access restoration; other targets unauthorized |
| F13 | Payroll | NOT STARTED | Chưa có model/code | Payroll calculation, lock, approval/payment workflow và audit |
| F14 | Finance Invoice | PARTIAL | Invoice và Payment models; approved target places Invoice in one Workspace, same-Profile Client, Payment under Invoice | Target ownership chưa migrate; numbering/billing workflow, positive amount constraints, service/API/tests còn thiếu |
| F15 | CRM Share Link | PARTIAL | Client và ShareLink models; approved target puts Client in Profile and separates portal/review credentials | Tenant ownership chưa migrate; token hiện plaintext/có thể lộ qua `__str__`; thiếu hash/revoke/capability/expiry |
| F16 | Automation | NOT STARTED | Chưa có cron/webhook worker hiện hành | Job design, idempotency, authentication, monitoring và deployment |

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

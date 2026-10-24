# HUSTLYTASKER REQUIREMENT STATUS

Last updated: 2026-10-24

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

Current checkpoint: **HT-TEST-P1-01 — COMPLETE / OWNER REVIEW GATE**.
**LOCAL TEST HARNESS VERIFIED**. Dedicated isolated test
settings, shared guarded PostgreSQL runner, PowerShell/Docker local command,
and backend GitHub Actions workflow are implemented. Actual current evidence
is 14/14 harness guard tests, targeted API 10/10, and full PostgreSQL 286/286
(166.382s) PASS with migration-chain/owned-DB cleanup checks. Failure exit-code,
owned-interruption cleanup and wrong-repository refusal checks pass. Local
PowerShell/Compose/actionlint/diff checks and exact original User/Session
preservation pass. **CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED.**

HT-DB-P1-09 remains the completed rollout baseline: `accounts.0002` applied
once, 32 migrations, 3 active Users/2 Sessions preserved, and zero verified
Users/token/business/AuditLog rows. Its historical 286/286 result does not
substitute for the current harness gate. No development migration, business
rule, authentication mechanism, or API contract change is part of this task.

## Tổng quan hiện tại

Dự án đang ở `PHASE 2.2 - API Architecture`. `HT-RBAC-DESIGN-P0-01` đã
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
| Database migrations | PARTIAL | Initial/additive migrations through `workspace.0004` and `accounts.0002` applied development; 32 migration records, validated schema, preserved legacy rows; HT-DB-P1-09 backup/restore/rehearsal/apply/smoke/full-suite/cleanup complete | Every non-development target needs separate authorization/safety gate; Client/Project/Finance/Audit/retention migrations absent | migration source; HT-DB-P1-09 checkpoint |
| Business schema | PARTIAL | Profile/ProfileMembership, Workspace lifecycle, Task/Review, ProfileInvitation, nullable User verification state, and digest-only AccountSecurityToken including reset password-state binding exist in source and approved development | Workspace Profile/legacy period and legacy Deliverable revision remain nullable; Task soft delete and Client/Project/Finance/Audit/retention migrations absent | `backend/apps/{accounts,tasks,reviews,workspace}/models.py`; `documentation/DATABASE_SCHEMA.md` |
| Tenancy/ownership design | COMPLETE / ACCEPTED | Owner đã phê duyệt 11 nhóm quyết định; HT-TASK-P2-03 tiếp tục chốt internal workflow trong đúng tenant boundary | Billing, public-link capabilities, retention duration và các domain action chưa implement vẫn defer sang task tương ứng; Client/Guest review và Payroll tách khỏi internal approval | `documentation/DECISION_LOG.md`; owner approvals 2026-10-16 và 2026-10-21 |
| RBAC/access/invitation design | COMPLETE / ACCEPTED | 14 nền RBAC được chốt; Task manager/reviewer contract và Profile Invitation role/identity/lifecycle contract đã được hiện thực hóa trong các slice được duyệt | Client/Guest capabilities, payroll pricing/eligibility và downstream domain details vẫn ở task riêng | `documentation/RBAC_DESIGN.md`; `DECISION_LOG.md`; HT-INV-P2-04 checkpoint |
| Django Admin | PARTIAL | User, Workspace, WorkspaceMember, Task, TaskAssignment, TaskComment; Task domain hiện inspection-only; Workspace hard delete bị chặn để không cascade workflow history; mapped Profile/period và lifecycle/member fields vẫn protected/read-only | Profile/ProfileMembership và 8 model trước chưa register; chưa có tenant-scoped Admin; aggregate CASCADE vẫn tồn tại ở schema và chỉ được chặn trên current Admin/API surfaces | `backend/apps/{tasks,workspace}/admin.py`; source review 2026-10-21 |
| DRF/API foundation | PARTIAL | SessionAuthentication/global IsAuthenticated unchanged; account-security schema now applied development; 45-request read-only CSRF smoke including Task/Review boundaries passes without 500 or data change; strict/no-cache verification/reset APIs unchanged | Authenticated success is not tested on persistent development; Profile creation, invitation inbox, Comments, Task soft delete, Client/Guest/Finance/Payroll/media routes absent | API sources; `API_DOCUMENTATION.md`; HT-DB-P1-09 |
| Authentication/RBAC | PARTIAL | Verification/reset implementation and controlled development rollout complete; token security, password-state binding, neutral status/body, validators, session invalidation and independent Invitation proof unchanged; current full 286/286 PASS | Timing not equalized; standalone logout-all/deactivation, real provider, shared cache, external review and other domain RBAC absent | account/Invitation sources; HT-DB-P1-09; `RBAC_DESIGN.md` |
| Automated tests | LOCAL BASELINE COMPLETE — HT-TEST-P1-01 | Dedicated isolated settings, shared full/targeted PostgreSQL runner, owned-DB/resource cleanup, one-command local Docker launcher and guard tests; guards 14/14, targeted API 10/10, full286/286 and migration-chain/failure/ownership/preservation checks PASS | Remote CI and real email provider remain unverified; later features still need their own tests | `scripts/test_backend.py`; `scripts/test_test_backend.py`; test config; `PROGRESS.md` |
| Frontend | NOT STARTED | Chỉ có định hướng React/Next.js | Không có source hoặc package manifest; chưa chốt React SPA hay Next.js | `documentation/TECH_STACK_DECISION.md` |
| Docker/deployment/CI | PARTIAL — TEST BASELINE IMPLEMENTED | Development Compose retained; separate tmpfs PostgreSQL 16/Python 3.12 local test project/dependency-only image and PR/push-main backend CI workflow; source read-only, no development volume/credentials, contents-read/no deploy; local full/failure/cleanup/actionlint PASS | CI WORKFLOW IMPLEMENTED — REMOTE RUN NOT VERIFIED; production backend image/deploy/monitoring still absent | `docker/compose.test.yml`; `docker/Dockerfile.test`; `.github/workflows/backend-ci.yml`; `README.md` |

## Trạng thái yêu cầu nghiệp vụ F01-F16

| ID | Module | Trạng thái | Đã triển khai | Còn thiếu / vấn đề |
|---|---|---|---|---|
| F01 | Authentication | PARTIAL — IMPLEMENTATION & DEVELOPMENT ROLLOUT COMPLETE | Session auth plus verification/reset foundation; exact accounts.0002 development apply, unchanged legacy Users/Sessions, zero auto-verification, 45-request read-only CSRF smoke and full PostgreSQL 286/286 PASS | Timing not equalized; no standalone logout-all/deactivation, real-provider verification, or distributed throttle cache; production rollout not authorized |
| F02 | Profile & Workspace | PARTIAL | Foundation `workspace.0002`/`0003`, monthly Workspace/lifecycle/member manager và Invitation onboarding source đã có; `workspace.0004` development rollout đã xác minh | Chưa Profile creation/general membership API/domain-wide RBAC; mọi non-development rollout còn gated riêng |
| F03 | Membership Invitation | PARTIAL — CORE IMPLEMENTATION & DEVELOPMENT ROLLOUT COMPLETE | ProfileInvitation model/0004, consent lifecycle, role ceiling, digest token, per-invitation recipient proof, delivery abstraction, locked membership onboarding, audit, APIs/tests và controlled development rollout đã hoàn tất | Account verification signal now exists in source but Invitation deliberately keeps its independent proof contract; REAL EMAIL DELIVERY NOT VERIFIED; chưa inbox, shared production cache hoặc automated retention purge; non-development rollout chưa authorize |
| F04 | Task Lifecycle | PARTIAL — CORE IMPLEMENTATION & DEV ROLLOUT COMPLETE | Manager create/update/assign; Editor start/submit; internal review approve/request changes; completion-after-approval invariant; locked services, audit, API; `tasks.0002`/`reviews.0002` applied development; final full 202/202 PASS | Task soft delete, cancel transition, Marketplace/claim và Client approval chưa có; production/other environment rollout chưa được authorize |
| F05 | Marketplace | NOT STARTED | Chưa có implementation | Publish/claim rules, concurrency guard, API và tests |
| F06 | Review Upload | PARTIAL | Revisioned Deliverable URL submission/history, uploader tenant attribution, status constraints và scoped API/service đã implement; required migrations đã apply development | Chỉ nhận `file_url`; actual upload/storage/media validation/processing chưa có; production/other target rollout chưa được authorize |
| F07 | Team Review Status | PARTIAL — INTERNAL SLICE & DEV ROLLOUT COMPLETE | Internal manager approval/request-changes, one Review per Deliverable, no self-review, stale/repeat/concurrency guards và Task/Deliverable synchronization; development rollout và full 202/202 PASS | Client/Guest approval độc lập chưa có; production/other target rollout chưa được authorize |
| F08 | Guest Review Decision | NOT STARTED | Kiến trúc đã chốt GuestReviewLink tách khỏi Client Portal | Chưa có scoped hashed token, exact capabilities, expiry/revoke, decision flow hoặc throttle |
| F09 | Client Portal | NOT STARTED | Client/ShareLink hiện chỉ là schema primitive; target hỗ trợ account và secure link độc lập với internal membership | Chưa migrate Client→Profile, chưa có secure link replacement, portal/API/capabilities |
| F10 | Client Request Inbox | NOT STARTED | Chưa có model/code | Request intake, triage, conversion to task và permissions |
| F11 | Task Comments | PARTIAL | TaskComment model; Admin inspection-only | Comments API, visibility rules, mentions, membership validation và tests không thuộc HT-TASK-P2-03 |
| F12 | Notifications | PARTIAL | Notification model | Producers, delivery/read APIs, email integration và retention |
| F13 | Payroll | NOT STARTED | Chưa có model/code | Payroll calculation, lock, approval/payment workflow và audit |
| F14 | Finance Invoice | PARTIAL | Invoice và Payment models; approved target places Invoice in one Workspace, same-Profile Client, Payment under Invoice | Target ownership chưa migrate; numbering/billing workflow, positive amount constraints, service/API/tests còn thiếu |
| F15 | CRM Share Link | PARTIAL | Client và ShareLink models; approved target puts Client in Profile and separates portal/review credentials | Tenant ownership chưa migrate; token hiện plaintext/có thể lộ qua `__str__`; thiếu hash/revoke/capability/expiry |
| F16 | Automation | NOT STARTED | Chưa có cron/webhook worker hiện hành | Job design, idempotency, authentication, monitoring và deployment |

## Quyết định sản phẩm/kiến trúc còn cần chốt

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
IMPLEMENTED — REMOTE RUN NOT VERIFIED. Stop at OWNER REVIEW GATE. The proposed
next task is HT-PROJ-P2-05; it is not started or automatically authorized. See
`documentation/HANDOVER.md`, `RBAC_DESIGN.md`, and `DECISION_LOG.md`.

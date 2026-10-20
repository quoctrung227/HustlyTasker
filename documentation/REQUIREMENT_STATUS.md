# HUSTLYTASKER REQUIREMENT STATUS

Last updated: 2026-10-21

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

## Tổng quan hiện tại

Dự án đang ở `PHASE 2.2 - API Architecture`. `HT-RBAC-DESIGN-P0-01` đã
`COMPLETE / ACCEPTED — APPROVED BY OWNER DELEGATION`; `HT-RBAC-P1-03` Tenant
Access Context and Scoped Service Foundation đã hoàn thành, sau đó Owner cho
phép triển khai `HT-API-P1-04`. Bốn Profile/Workspace read route, DRF tenant
permissions, scoped querysets và pagination đã hoàn thành. Owner đã mở
`HT-DB-P1-05` để rollout có kiểm soát migration hiện hữu trên development;
task đó đã hoàn thành với full PostgreSQL suite 101/101. Owner sau đó mở
`HT-WORK-P2-02`, rồi phê duyệt rollout `workspace.0003` qua `HT-DB-P1-06`.
Sau review gate đó, Owner mở `HT-TASK-P2-03`. Trạng thái hiện tại là
**HT-TASK-P2-03 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION
APPROVAL**.
Workspace write/membership, Profile/Workspace lifecycle, monthly period và
membership soft revoke/reactivate đã triển khai; `workspace.0003` đã được
backup/rehearsal và apply lên development. Direct smoke và full PostgreSQL
169/169 của gate trước PASS. Task/Deliverable/internal Review workflow mới đã
implement trong source; targeted PostgreSQL 33/33, regression 169/169 và full
202/202 đều PASS. `tasks.0002`/`reviews.0002` chưa apply development.
Invitation, activation/recovery, các business API còn lại, frontend và
deployment vẫn chưa hoàn thành.

## Nền tảng kỹ thuật

| Hạng mục | Trạng thái | Đã triển khai | Còn thiếu / vấn đề | Căn cứ |
|---|---|---|---|---|
| Dependency manifest | COMPLETE | Manifest UTF-8/pinned; Django 6.1.2 và DRF 3.18.3; current container runtime pass `pip check` | Owner host shell báo venv hoạt động, nhưng Codex managed context exit 103 và không thấy base interpreter path; cached Python 3.12 container là fallback đã kiểm chứng | `backend/requirements.txt`; xác minh HT-DB-P1-05 ngày 2026-10-19 |
| Django configuration | PARTIAL | Secret/debug/hosts/DB/CSRF/security/mailer lấy từ environment; development/production fail-fast; production-like deploy check sạch | Chưa có giá trị production thật, trusted-proxy/static/deploy contract; secret cũ cần rotate nếu từng dùng ngoài local | `backend/config/settings.py`; `.env.example`; kiểm chứng Docker 2026-10-13 |
| Database migrations | PARTIAL | 8 initial app migrations cùng additive `workspace.0002` và `workspace.0003` đã áp dụng trên development; source thêm additive `tasks.0002`/`reviews.0002` và migration rehearsal 33-test gate bảo toàn legacy Task/Deliverable/Review | Hai migration workflow chưa apply development/production; rollout phải inventory invalid enum, duplicate Review và legacy assignment, backup/plan/smoke riêng, không guessed cleanup/backfill | migration source; HT-DB-P1-05/P1-06 evidence; HT-TASK-P2-03 checkpoint 2026-10-21 |
| Business schema | PARTIAL | 16 concrete models gồm `Profile`/`ProfileMembership`; source harden Task/Assignment/Deliverable/Review bằng active assignment, revision, checks/indexes và protected actor references | Workspace Profile/legacy period và legacy Deliverable revision vẫn nullable để bảo toàn dữ liệu chưa mapping; Task soft delete chưa có; chưa migrate Client/Project/Finance/Audit, Invitation, links hay retention/purge | `backend/apps/{tasks,reviews,workspace}/models.py`; `documentation/DATABASE_SCHEMA.md` |
| Tenancy/ownership design | COMPLETE / ACCEPTED | Owner đã phê duyệt 11 nhóm quyết định; HT-TASK-P2-03 tiếp tục chốt internal workflow trong đúng tenant boundary | Billing, public-link capabilities, retention duration và các domain action chưa implement vẫn defer sang task tương ứng; Client/Guest review và Payroll tách khỏi internal approval | `documentation/DECISION_LOG.md`; owner approvals 2026-10-16 và 2026-10-21 |
| RBAC/access/invitation design | COMPLETE / ACCEPTED | 14 nền RBAC được chốt; HT-TASK-P2-03 cụ thể hóa internal Task manager/reviewer là Profile Owner/Admin hoặc Workspace Admin, Editor là active Profile Member + Workspace `MEMBER`, và cấm self-review | Invitation implementation, Client/Guest capabilities, payroll pricing/eligibility và các downstream domain details vẫn ở task riêng | `documentation/RBAC_DESIGN.md`; `DECISION_LOG.md`; HT-TASK-P2-03 checkpoint |
| Django Admin | PARTIAL | User, Workspace, WorkspaceMember, Task, TaskAssignment, TaskComment; Task domain hiện inspection-only; Workspace hard delete bị chặn để không cascade workflow history; mapped Profile/period và lifecycle/member fields vẫn protected/read-only | Profile/ProfileMembership và 8 model trước chưa register; chưa có tenant-scoped Admin; aggregate CASCADE vẫn tồn tại ở schema và chỉ được chặn trên current Admin/API surfaces | `backend/apps/{tasks,workspace}/admin.py`; source review 2026-10-21 |
| DRF/API foundation | PARTIAL | Nền SessionAuthentication/global `IsAuthenticated` giữ nguyên; Workspace APIs hiện hữu và nested Task/Deliverable/internal Review routes dùng strict input, no-PII attribution, pagination, CSRF và 400/403/404/409 boundary | Profile creation, Invitation, Comments, Task soft delete, Client/Guest/Finance/Payroll và media upload routes chưa có; workflow migrations chưa deploy development | `backend/api/`; `backend/apps/tasks/{views,urls,serializers,permissions}.py`; `API_DOCUMENTATION.md` |
| Authentication/RBAC | PARTIAL | Session auth giữ nguyên; tenant contexts/scoped selectors/locked services hỗ trợ Task read/manage/execute/review; only current active assignee start/submit; self-review fail closed | Activation/OTP/reset/logout-all, account lifecycle, Invitation, external review và RBAC cho domain chưa implement còn thiếu | `backend/apps/accounts/`; `backend/apps/{workspace,tasks}/access.py`; task permissions/services; `RBAC_DESIGN.md` |
| Automated tests | PARTIAL | HT-TASK-P2-03 PASS targeted PostgreSQL 33/33, existing regression 169/169 và full 202/202; dependency/system/migration-drift checks PASS, test DB destroyed | Chưa có CI hoặc one-command clean-checkout harness; workflow migrations chưa rollout development | task test sources; `PROGRESS.md`; evidence 2026-10-21 |
| Frontend | NOT STARTED | Chỉ có định hướng React/Next.js | Không có source hoặc package manifest; chưa chốt React SPA hay Next.js | `documentation/TECH_STACK_DECISION.md` |
| Docker/deployment/CI | PARTIAL | PostgreSQL Compose dùng environment bắt buộc, loopback bind mặc định và giữ named volume; setup local đã được tài liệu hóa | Chưa có backend image, active deploy config hoặc CI workflow | `docker/docker-compose.yml`; `README.md` |

## Trạng thái yêu cầu nghiệp vụ F01-F16

| ID | Module | Trạng thái | Đã triển khai | Còn thiếu / vấn đề |
|---|---|---|---|---|
| F01 | Authentication | PARTIAL | Custom `User`; session register/login/logout/me; CSRF; password validation/hash; inactive block; scoped throttle; 19 tests | Activation/OTP, password reset, logout-all và production shared-cache/proxy enforcement |
| F02 | Profile & Workspace | PARTIAL | Foundation cùng `workspace.0002`/`0003` trên development; monthly Workspace, Profile/Workspace archive/restore, Workspace create/update và member list/direct-add/role-update/soft-revoke/reactivate với locking/audit; current full PostgreSQL 169/169 | Chưa Profile creation, Invitation hay domain-wide RBAC; rollout mọi môi trường khác cần phê duyệt riêng |
| F03 | Membership Invitation | PARTIAL | Direct-add requires active same-Profile membership; invitation identity, role ceiling, TTL 7 days, rate limits and minimum 12-month terminal metadata retention are approved | Chưa có verified-email onboarding dependency, model, migration, delivery, service hoặc API implementation |
| F04 | Task Lifecycle | PARTIAL — IMPLEMENTATION COMPLETE; DEV MIGRATION PENDING | Manager create/update/assign; Editor start/submit; internal review approve/request changes; completion-after-approval invariant; locked services, audit, API; final full 202/202 PASS | Development migration approval còn pending; Task soft delete, cancel transition, Marketplace/claim và Client approval chưa có |
| F05 | Marketplace | NOT STARTED | Chưa có implementation | Publish/claim rules, concurrency guard, API và tests |
| F06 | Review Upload | PARTIAL | Revisioned Deliverable URL submission/history, uploader tenant attribution, status constraints và scoped API/service đã implement | Chỉ nhận `file_url`; actual upload/storage/media validation/processing chưa có; rollout migration còn pending |
| F07 | Team Review Status | PARTIAL — INTERNAL SLICE IMPLEMENTED | Internal manager approval/request-changes, one Review per Deliverable, no self-review, stale/repeat/concurrency guards và Task/Deliverable synchronization; full 202/202 PASS | Client/Guest approval độc lập chưa có; development migration còn pending |
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
không tự tạo Payroll/Payment”; account verification
và full deactivation/session-revocation flow; Invitation delivery/onboarding
implementation; Invoice numbering/billing;
Client Portal/Guest Review exact capabilities/default expiry; retention legal
hold/purge; và project-wide response/error convention ngoài các mapping hiện
có. Policy migration vẫn là kiểm kê từng môi trường, không tự gán tenant
cho dữ liệu không xác định.

`HT-API-P1-04`, `HT-DB-P1-05`, implementation `HT-WORK-P2-02` và rollout
`HT-DB-P1-06` đã hoàn thành.
`HT-DB-P1-06` đã backup/rehearse/apply `workspace.0003` đúng development,
post-check schema/data, smoke request stack và rerun full regressions đạt;
production không bị tác động. Owner đã mở `HT-TASK-P2-03`; source implementation,
targeted 33/33, regression 169/169, full 202/202, final code review và
development post-check đều đạt. Trạng thái hiện tại là **HT-TASK-P2-03 —
IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL**.

Bước tiếp theo chỉ là Owner review và, nếu được phê duyệt riêng, controlled
development migration; không mở Invitation hoặc feature task khác. Xem
`documentation/HANDOVER.md`, `RBAC_DESIGN.md` và `DECISION_LOG.md`.

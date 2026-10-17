# HUSTLYTASKER REQUIREMENT STATUS

Last updated: 2026-10-17

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

Dự án đang ở `PHASE 2.2 - API Architecture` và review gate của
`PROFILE/WORKSPACE SCHEMA FOUNDATION` đã hoàn tất implementation/verification.
`HT-RBAC-DESIGN-P0-01` hiện `DESIGN READY — PENDING OWNER APPROVAL`. Nền tảng Django, PostgreSQL,
authentication và API deny-by-default đã được kiểm chứng. `HT-DATA-P2-01` đã
được owner phê duyệt; Profile/Workspace foundation hiện có trong source và
migration test; full regression đã pass nhưng `0002` chưa apply development
database. Capability/scoping/invitation contract đã có để review nhưng
Workspace/RBAC/Invitation API, business APIs,
activation/recovery, frontend và deployment chưa hoàn thành.

## Nền tảng kỹ thuật

| Hạng mục | Trạng thái | Đã triển khai | Còn thiếu / vấn đề | Căn cứ |
|---|---|---|---|---|
| Dependency manifest | COMPLETE | Manifest UTF-8; Django 6.1.2; DRF 3.18.3; fresh install và `pip check` thành công | Virtualenv local cũ vẫn hỏng do mất base Python; cần tạo lại khi phát triển trên host | `backend/requirements.txt`; kiểm chứng Docker 2026-10-13 |
| Django configuration | PARTIAL | Secret/debug/hosts/DB/CSRF/security/mailer lấy từ environment; development/production fail-fast; production-like deploy check sạch | Chưa có giá trị production thật, trusted-proxy/static/deploy contract; secret cũ cần rotate nếu từng dùng ngoài local | `backend/config/settings.py`; `.env.example`; kiểm chứng Docker 2026-10-13 |
| Database migrations | PARTIAL | 8 initial app migrations đã áp dụng trên development PostgreSQL; additive `workspace/0002_profile_workspace_foundation.py` tồn tại và pass migration tests | `0002` chỉ chạy trên test DB tạm, chưa apply development; các tenant-domain migration khác chưa tạo | `backend/apps/workspace/migrations/0002_profile_workspace_foundation.py`; migration test reverified 2026-10-17 |
| Business schema | PARTIAL | 16 concrete models gồm `Profile`/`ProfileMembership`; Workspace có transitional Profile FK; foundation constraints/services đã thêm | Workspace Profile FK vẫn nullable; chưa migrate Client/Project/Finance/Audit, Invitation, links hay soft delete | `backend/apps/workspace/models.py`; `services.py`; `documentation/DATABASE_SCHEMA.md` |
| Tenancy/ownership design | COMPLETE / ACCEPTED | Owner đã phê duyệt 11 nhóm quyết định: Profile tenant root, monthly Workspace, multi-Profile/multi-Owner, ownership và isolation target | Các chi tiết billing, public-link capabilities, retention duration, action-level RBAC và detailed workflow được defer sang task tương ứng | `documentation/DECISION_LOG.md`; owner approval 2026-10-16 |
| RBAC/access/invitation design | DESIGN READY — PENDING APPROVAL | Capability matrix, scoped-query/service boundary, IDOR/error policy proposal, Profile Invitation contract, planned API, negative tests và dependency order đã hoàn tất | Owner chưa duyệt role vocabulary, Admin/Viewer authority, Task visibility, invitation/rejoin lifecycle, error/operator policy; chưa có implementation | `documentation/RBAC_DESIGN.md`; design checkpoint 2026-10-17 |
| Django Admin | PARTIAL | User, Workspace, WorkspaceMember, Task, TaskAssignment, TaskComment; Workspace Profile is read-only after mapping; WorkspaceMember is read-only; User auto-managed timestamps are readonly | Profile/ProfileMembership and 8 earlier domain models are not registered (10/16 total); current foundation adds no tenant-scoped admin authorization | `backend/apps/*/admin.py`; source review 2026-10-16 |
| DRF/API foundation | PARTIAL | HT-API-P0-03 đã COMPLETE: DRF dùng SessionAuthentication và global `IsAuthenticated`; toàn bộ route dưới `/api/` dùng DRF; public view nằm trong allowlist explicit `AllowAny`; `/api/health/` là liveness JSON-only không auth/throttle/DB; legacy `/api/test/` đã gỡ; 10 API policy tests pass | Nền API tổng thể vẫn PARTIAL vì chưa có `/api/v1/`, error/pagination convention hoặc business route | `backend/api/views.py`; `backend/api/urls.py`; `backend/api/tests.py`; `backend/config/settings.py`; kiểm chứng Docker 2026-10-15 |
| Authentication/RBAC | PARTIAL | Session register/login/logout/me, CSRF bootstrap, password validation/hash, neutral login errors, inactive block và throttle tests; RBAC/scoping/invitation design ready for review | Activation/OTP/reset/logout-all còn thiếu; RBAC/object scoping chưa được implement | `backend/apps/accounts/`; `documentation/API_DOCUMENTATION.md`; `documentation/RBAC_DESIGN.md` |
| Automated tests | PARTIAL | Targeted `apps.workspace` 32/32 và full PostgreSQL suite 61/61 pass; gồm model/service/concurrency, cross-Profile isolation, empty-schema apply, populated migration rehearsal, 19 Authentication và 10 API regressions | Chưa có CI; business-domain/API coverage chưa tồn tại | `backend/apps/workspace/tests.py`; `test_migrations.py`; kiểm chứng 2026-10-17 |
| Frontend | NOT STARTED | Chỉ có định hướng React/Next.js | Không có source hoặc package manifest; chưa chốt React SPA hay Next.js | `documentation/TECH_STACK_DECISION.md` |
| Docker/deployment/CI | PARTIAL | PostgreSQL Compose dùng environment bắt buộc, loopback bind mặc định và giữ named volume; setup local đã được tài liệu hóa | Chưa có backend image, active deploy config hoặc CI workflow | `docker/docker-compose.yml`; `README.md` |

## Trạng thái yêu cầu nghiệp vụ F01-F16

| ID | Module | Trạng thái | Đã triển khai | Còn thiếu / vấn đề |
|---|---|---|---|---|
| F01 | Authentication | PARTIAL | Custom `User`; session register/login/logout/me; CSRF; password validation/hash; inactive block; scoped throttle; 19 tests | Activation/OTP, password reset, logout-all và production shared-cache/proxy enforcement |
| F02 | Profile & Workspace | PARTIAL | Profile/ProfileMembership foundation; multi-Profile and multi-Owner services; transitional Workspace→Profile link with stale-save concurrency guard; approved architecture; action/scoping design ready for review | `0002` chưa apply development; role decisions chưa duyệt; chưa soft delete, API, tenant query scoping hoặc full RBAC |
| F03 | Membership Invitation | PARTIAL | WorkspaceMember; approved consent/direct-add rule; Profile Invitation state/token/concurrency/API contract ready for review | Owner còn phải chốt role ceiling, recipient onboarding, TTL/reinvite/throttle, rejoin/retention; chưa có model, migration, service hoặc API |
| F04 | Task Lifecycle | PARTIAL | Task, assignment, status/priority, admin CRUD | Transition service, invariants, API, RBAC và tests |
| F05 | Marketplace | NOT STARTED | Chưa có implementation | Publish/claim rules, concurrency guard, API và tests |
| F06 | Review Upload | PARTIAL | Deliverable và Review schema cơ bản | Upload/storage, versioning, processing states, permission và API |
| F07 | Team Review Status | PARTIAL | Review status choices cơ bản | Workflow đồng bộ Deliverable/Task, transition rules và tests |
| F08 | Guest Review Decision | NOT STARTED | Kiến trúc đã chốt GuestReviewLink tách khỏi Client Portal | Chưa có scoped hashed token, exact capabilities, expiry/revoke, decision flow hoặc throttle |
| F09 | Client Portal | NOT STARTED | Client/ShareLink hiện chỉ là schema primitive; target hỗ trợ account và secure link độc lập với internal membership | Chưa migrate Client→Profile, chưa có secure link replacement, portal/API/capabilities |
| F10 | Client Request Inbox | NOT STARTED | Chưa có model/code | Request intake, triage, conversion to task và permissions |
| F11 | Task Comments | PARTIAL | TaskComment model và admin | API, visibility rules, mentions, membership validation và tests |
| F12 | Notifications | PARTIAL | Notification model | Producers, delivery/read APIs, email integration và retention |
| F13 | Payroll | NOT STARTED | Chưa có model/code | Payroll calculation, lock, approval/payment workflow và audit |
| F14 | Finance Invoice | PARTIAL | Invoice và Payment models; approved target places Invoice in one Workspace, same-Profile Client, Payment under Invoice | Target ownership chưa migrate; numbering/billing workflow, positive amount constraints, service/API/tests còn thiếu |
| F15 | CRM Share Link | PARTIAL | Client và ShareLink models; approved target puts Client in Profile and separates portal/review credentials | Tenant ownership chưa migrate; token hiện plaintext/có thể lộ qua `__str__`; thiếu hash/revoke/capability/expiry |
| F16 | Automation | NOT STARTED | Chưa có cron/webhook worker hiện hành | Job design, idempotency, authentication, monitoring và deployment |

## Quyết định sản phẩm/kiến trúc còn cần chốt

1. Activation dùng email link hay OTP. Session-cookie đã được chọn cho foundation same-origin; cần đánh giá lại nếu frontend chuyển sang cross-site/native client.
2. Phê duyệt capability proposal trong `RBAC_DESIGN.md`: giữ Workspace Admin,
   deprecate Workspace Owner, Viewer scope, Profile Admin authority, Workspace
   lifecycle/membership authority và Task visibility.
3. Phê duyệt tenant boundary proposal: non-enumerating `404`/`403`/generic
   `400`, `409` conflict contract, platform-operator/Django Admin bypass và
   User deactivate/delete/session policy bảo vệ usable Owner.
4. Profile creation self-service eligibility/limits, initial-Owner bootstrap,
   voluntary leave/rejoin và historical Workspace-access behavior.
5. Invitation role/management ceiling, existing/unregistered recipient flow,
   existing-account email verification, TTL, revoke/reinvite/throttle, inviter
   revalidation, optional combined Workspace UX và terminal-record retention.
6. Invoice numbering/uniqueness và detailed billing workflow.
7. Client Portal/Guest Review visible fields, actions, account-linking flow và
   default link expiry/rotation policy.
8. Retention durations, legal hold/purge schedule và thẩm quyền hard delete.
9. Canonical Task/Review states, approver permissions và payroll trigger.
10. Explicit owner-provided mapping cho bất kỳ existing row nào không thể map
   tenant bằng verified evidence; không được tự gán.

Các chi tiết này chặn task nghiệp vụ tương ứng nhưng không phủ nhận 11 quyết
định kiến trúc đã được duyệt. Schema foundation đã qua full regression;
HT-RBAC-DESIGN-P0-01 dừng tại owner review trước Workspace API/RBAC. Xem
`documentation/RBAC_DESIGN.md` và `documentation/DECISION_LOG.md`.

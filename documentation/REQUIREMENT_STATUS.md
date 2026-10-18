# HUSTLYTASKER REQUIREMENT STATUS

Last updated: 2026-10-18

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
Access Context and Scoped Service Foundation cũng đã hoàn thành và dừng tại
Owner review gate. Nền tảng context/scoped selector và hai membership service
đã được kiểm chứng trên PostgreSQL, nhưng không có Workspace/Invitation API,
không có migration mới và `workspace.0002` vẫn chưa apply development database.
Activation/recovery, business APIs, frontend và deployment vẫn chưa hoàn thành.

## Nền tảng kỹ thuật

| Hạng mục | Trạng thái | Đã triển khai | Còn thiếu / vấn đề | Căn cứ |
|---|---|---|---|---|
| Dependency manifest | COMPLETE | Manifest UTF-8; local Python 3.12 virtualenv synchronized to Django 6.1.2 and DRF 3.18.3; `pip check` PASS | Cần tiếp tục tái kiểm chứng khi dependency thay đổi | `backend/requirements.txt`; kiểm chứng lại 2026-10-18 |
| Django configuration | PARTIAL | Secret/debug/hosts/DB/CSRF/security/mailer lấy từ environment; development/production fail-fast; production-like deploy check sạch | Chưa có giá trị production thật, trusted-proxy/static/deploy contract; secret cũ cần rotate nếu từng dùng ngoài local | `backend/config/settings.py`; `.env.example`; kiểm chứng Docker 2026-10-13 |
| Database migrations | PARTIAL | 8 initial app migrations đã áp dụng trên development PostgreSQL; additive `workspace/0002_profile_workspace_foundation.py` tồn tại và pass migration tests | `0002` chỉ chạy trên test DB tạm, chưa apply development; các tenant-domain migration khác chưa tạo | `backend/apps/workspace/migrations/0002_profile_workspace_foundation.py`; migration test reverified 2026-10-18 |
| Business schema | PARTIAL | 16 concrete models gồm `Profile`/`ProfileMembership`; Workspace có transitional Profile FK; foundation constraints/services đã thêm | Workspace Profile FK vẫn nullable; chưa migrate Client/Project/Finance/Audit, Invitation, links hay soft delete | `backend/apps/workspace/models.py`; `services.py`; `documentation/DATABASE_SCHEMA.md` |
| Tenancy/ownership design | COMPLETE / ACCEPTED | Owner đã phê duyệt 11 nhóm quyết định: Profile tenant root, monthly Workspace, multi-Profile/multi-Owner, ownership và isolation target | Các chi tiết billing, public-link capabilities, retention duration, domain-specific/DRF action enforcement và detailed workflow được defer sang task tương ứng | `documentation/DECISION_LOG.md`; owner approval 2026-10-16 |
| RBAC/access/invitation design | COMPLETE / ACCEPTED | 14 quyết định được chốt qua ủy quyền: capability matrix, compatibility roles, least-privilege ceilings, IDOR/error/operator policy và Invitation contract | Invitation implementation, reviewer role/states và downstream domain details vẫn ở task riêng | `documentation/RBAC_DESIGN.md`; `DECISION_LOG.md`; owner delegation 2026-10-17 |
| Django Admin | PARTIAL | User, Workspace, WorkspaceMember, Task, TaskAssignment, TaskComment; Workspace Profile is read-only after mapping; WorkspaceMember is read-only; User auto-managed timestamps are readonly | Profile/ProfileMembership and 8 earlier domain models are not registered (10/16 total); current foundation adds no tenant-scoped admin authorization | `backend/apps/*/admin.py`; source review 2026-10-16 |
| DRF/API foundation | PARTIAL | HT-API-P0-03 đã COMPLETE: DRF dùng SessionAuthentication và global `IsAuthenticated`; toàn bộ route dưới `/api/` dùng DRF; public view nằm trong allowlist explicit `AllowAny`; `/api/health/` là liveness JSON-only không auth/throttle/DB; legacy `/api/test/` đã gỡ; 10 API policy tests pass | Nền API tổng thể vẫn PARTIAL vì chưa có `/api/v1/`, error/pagination convention hoặc business route | `backend/api/views.py`; `backend/api/urls.py`; `backend/api/tests.py`; `backend/config/settings.py`; kiểm chứng Docker 2026-10-15 |
| Authentication/RBAC | PARTIAL | Session auth giữ nguyên; verified Profile/Workspace contexts, scoped selectors, capability checks và scoped membership services đã implement | Activation/OTP/reset/logout-all, DRF tenant permission/endpoints, account deactivation/session purge và domain-wide RBAC còn thiếu | `backend/apps/accounts/`; `backend/apps/workspace/access.py`; `services.py`; `RBAC_DESIGN.md` |
| Automated tests | PARTIAL | Final targeted `apps.workspace` 51/51 và full PostgreSQL suite 80/80 pass; gồm context-forgery/staleness, IDOR, role ceilings, duplicate concurrency, migration rehearsal, 19 Authentication và 10 API regressions | Chưa có CI; business-domain/API coverage chưa tồn tại | `backend/apps/workspace/tests.py`; `test_migrations.py`; kiểm chứng 2026-10-18 |
| Frontend | NOT STARTED | Chỉ có định hướng React/Next.js | Không có source hoặc package manifest; chưa chốt React SPA hay Next.js | `documentation/TECH_STACK_DECISION.md` |
| Docker/deployment/CI | PARTIAL | PostgreSQL Compose dùng environment bắt buộc, loopback bind mặc định và giữ named volume; setup local đã được tài liệu hóa | Chưa có backend image, active deploy config hoặc CI workflow | `docker/docker-compose.yml`; `README.md` |

## Trạng thái yêu cầu nghiệp vụ F01-F16

| ID | Module | Trạng thái | Đã triển khai | Còn thiếu / vấn đề |
|---|---|---|---|---|
| F01 | Authentication | PARTIAL | Custom `User`; session register/login/logout/me; CSRF; password validation/hash; inactive block; scoped throttle; 19 tests | Activation/OTP, password reset, logout-all và production shared-cache/proxy enforcement |
| F02 | Profile & Workspace | PARTIAL | Profile/ProfileMembership foundation; verified Profile/Workspace contexts; scoped selectors; audited tenant-scoped membership services; approved two-level role compatibility and ceilings | `0002` chưa apply development; chưa soft delete, DRF Workspace API/permissions hoặc domain-wide RBAC |
| F03 | Membership Invitation | PARTIAL | Direct-add requires active same-Profile membership; invitation identity, role ceiling, TTL 7 days, rate limits and minimum 12-month terminal metadata retention are approved | Chưa có verified-email onboarding dependency, model, migration, delivery, service hoặc API implementation |
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

Không còn câu hỏi nào của review gate `HT-RBAC-DESIGN-P0-01`; 14 quyết định đã
được chốt qua Owner delegation và không được yêu cầu quyết định lại.

Các task sau vẫn phải chốt contract riêng trước implementation: lựa chọn
reviewer cụ thể và trạng thái Task/Review/payroll trigger; account verification
và full deactivation/session-revocation flow; rejoin/history semantics;
Invitation delivery/onboarding implementation; Invoice numbering/billing;
Client Portal/Guest Review exact capabilities/default expiry; retention legal
hold/purge; và API response envelope/versioning. Policy migration vẫn là kiểm
kê từng môi trường, không tự gán tenant cho dữ liệu không xác định.

`HT-RBAC-P1-03` dừng tại Owner review trước khi áp dụng `workspace.0002`, mở
Workspace/Invitation API hoặc chuyển sang task tiếp theo. Xem
`documentation/RBAC_DESIGN.md` và `documentation/DECISION_LOG.md`.

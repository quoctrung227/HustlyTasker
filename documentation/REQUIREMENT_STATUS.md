# HUSTLYTASKER REQUIREMENT STATUS

Last updated: 2026-10-19

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
`HT-WORK-P2-02`. Phần schema-free hiện có Workspace create/update và nested
membership list/direct-add/role-update và đã qua full PostgreSQL suite 140/140.
Profile lifecycle, Workspace month/archive/restore và member revoke/deactivate
đang dừng tại `SCHEMA APPROVAL GATE`; không có migration mới và development vẫn
ở `workspace.0002`. Invitation, activation/recovery, các business API còn lại,
frontend và deployment vẫn chưa hoàn thành.

## Nền tảng kỹ thuật

| Hạng mục | Trạng thái | Đã triển khai | Còn thiếu / vấn đề | Căn cứ |
|---|---|---|---|---|
| Dependency manifest | COMPLETE | Manifest UTF-8/pinned; Django 6.1.2 và DRF 3.18.3; current container runtime pass `pip check` | Owner host shell báo venv hoạt động, nhưng Codex managed context exit 103 và không thấy base interpreter path; cached Python 3.12 container là fallback đã kiểm chứng | `backend/requirements.txt`; xác minh HT-DB-P1-05 ngày 2026-10-19 |
| Django configuration | PARTIAL | Secret/debug/hosts/DB/CSRF/security/mailer lấy từ environment; development/production fail-fast; production-like deploy check sạch | Chưa có giá trị production thật, trusted-proxy/static/deploy contract; secret cũ cần rotate nếu từng dùng ngoài local | `backend/config/settings.py`; `.env.example`; kiểm chứng Docker 2026-10-13 |
| Database migrations | PARTIAL | 8 initial app migrations và additive `workspace/0002_profile_workspace_foundation.py` đã áp dụng trên development sau inventory, backup, restore rehearsal và plan review; migration/test consistency PASS | Các tenant-domain migration khác chưa tạo; mọi target khác vẫn cần controlled rollout riêng | migration source; HT-DB-P1-05 completion evidence 2026-10-19 |
| Business schema | PARTIAL | 16 concrete models gồm `Profile`/`ProfileMembership`; Workspace có transitional Profile FK; foundation constraints/services đã thêm | Workspace Profile FK vẫn nullable; chưa migrate Client/Project/Finance/Audit, Invitation, links hay soft delete | `backend/apps/workspace/models.py`; `services.py`; `documentation/DATABASE_SCHEMA.md` |
| Tenancy/ownership design | COMPLETE / ACCEPTED | Owner đã phê duyệt 11 nhóm quyết định: Profile tenant root, monthly Workspace, multi-Profile/multi-Owner, ownership và isolation target | Các chi tiết billing, public-link capabilities, retention duration, domain-specific/DRF action enforcement và detailed workflow được defer sang task tương ứng | `documentation/DECISION_LOG.md`; owner approval 2026-10-16 |
| RBAC/access/invitation design | COMPLETE / ACCEPTED | 14 quyết định được chốt qua ủy quyền: capability matrix, compatibility roles, least-privilege ceilings, IDOR/error/operator policy và Invitation contract | Invitation implementation, reviewer role/states và downstream domain details vẫn ở task riêng | `documentation/RBAC_DESIGN.md`; `DECISION_LOG.md`; owner delegation 2026-10-17 |
| Django Admin | PARTIAL | User, Workspace, WorkspaceMember, Task, TaskAssignment, TaskComment; Workspace Profile is read-only after mapping; WorkspaceMember is read-only; User auto-managed timestamps are readonly | Profile/ProfileMembership and 8 earlier domain models are not registered (10/16 total); current foundation adds no tenant-scoped admin authorization | `backend/apps/*/admin.py`; source review 2026-10-16 |
| DRF/API foundation | PARTIAL | HT-API-P0-03 giữ SessionAuthentication/global `IsAuthenticated`, explicit public allowlist và health policy; Profile/Workspace read API đã kiểm chứng; HT-WORK-P2-02 thêm limited Workspace create/update và member list/add/role-update với strict inputs, no-PII output và 400/403/404/409 mapping; schema-free slice đã qua full regression | Archive/restore, member revoke/deactivate, Profile write, Invitation và downstream routes chưa có; `DELETE` vẫn 405 | `backend/api/`; `backend/apps/workspace/{views,urls,serializers,permissions,test_api,test_write_api}.py`; `API_DOCUMENTATION.md`; full PostgreSQL 140/140 ngày 2026-10-19 |
| Authentication/RBAC | PARTIAL | Session auth giữ nguyên; verified Profile/Workspace contexts, scoped selectors, capability checks và locked tenant-scoped services; write API áp role ceilings; roster selector actor-bound trong SQL và fail closed khi authority bị revoke trước lazy evaluation | Activation/OTP/reset/logout-all, account/session lifecycle, Profile/Workspace/member lifecycle và domain-wide RBAC còn thiếu | `backend/apps/accounts/`; `backend/apps/workspace/access.py`; `permissions.py`; `views.py`; `services.py`; `RBAC_DESIGN.md` |
| Automated tests | PARTIAL | HT-WORK gate: Workspace service/read/write/API 111/111 PASS (62.011s), Authentication/API Foundation 29/29 PASS (7.295s), full PostgreSQL 140/140 PASS (69.873s); `pip check`, system check và migration consistency PASS; isolated test DB destroyed | Chưa có CI hoặc one-command clean-checkout harness; blocked lifecycle schema chưa có tests/implementation | test sources; `PROGRESS.md`; evidence ngày 2026-10-19 |
| Frontend | NOT STARTED | Chỉ có định hướng React/Next.js | Không có source hoặc package manifest; chưa chốt React SPA hay Next.js | `documentation/TECH_STACK_DECISION.md` |
| Docker/deployment/CI | PARTIAL | PostgreSQL Compose dùng environment bắt buộc, loopback bind mặc định và giữ named volume; setup local đã được tài liệu hóa | Chưa có backend image, active deploy config hoặc CI workflow | `docker/docker-compose.yml`; `README.md` |

## Trạng thái yêu cầu nghiệp vụ F01-F16

| ID | Module | Trạng thái | Đã triển khai | Còn thiếu / vấn đề |
|---|---|---|---|---|
| F01 | Authentication | PARTIAL | Custom `User`; session register/login/logout/me; CSRF; password validation/hash; inactive block; scoped throttle; 19 tests | Activation/OTP, password reset, logout-all và production shared-cache/proxy enforcement |
| F02 | Profile & Workspace | PARTIAL | Foundation + `workspace.0002` trên development; verified access/scoping; read routes; Workspace create/update và member list/direct-add/role-update với role ceilings, transactions, actor-bound roster và audit; schema-free slice đã qua full PostgreSQL 140/140 | Cần duyệt Profile lifecycle, Workspace month/archive/restore và member deactivate/history/rejoin; chưa Profile write, Invitation hay domain-wide RBAC; rollout môi trường khác chưa được phê duyệt |
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

Các task sau vẫn phải chốt contract riêng trước implementation: lifecycle
state/month contract của Workspace; archive visibility/child-write/restore và
actor ceiling; WorkspaceMember deactivate/history/rejoin semantics; lựa chọn
reviewer cụ thể và trạng thái Task/Review/payroll trigger; account verification
và full deactivation/session-revocation flow; rejoin/history semantics;
Invitation delivery/onboarding implementation; Invoice numbering/billing;
Client Portal/Guest Review exact capabilities/default expiry; retention legal
hold/purge; và project-wide response/error convention ngoài các mapping hiện
có. Policy migration vẫn là kiểm kê từng môi trường, không tự gán tenant
cho dữ liệu không xác định.

`HT-API-P1-04` đã hoàn thành scope read-only. `HT-DB-P1-05` đã hoàn tất
development-only rollout với backup/restore rehearsal, apply, direct smoke và
full regressions đạt. `HT-WORK-P2-02` hiện `IN PROGRESS — SCHEMA APPROVAL
GATE`: phần schema-free đã qua full PostgreSQL 140/140; Owner phải duyệt Profile
lifecycle, Workspace month/archive/restore và WorkspaceMember deactivate/
history/rejoin trước mọi migration/DELETE/archive/revoke. Không mở Invitation
hoặc chuyển task. Xem `documentation/HANDOVER.md`, `RBAC_DESIGN.md` và
`DECISION_LOG.md`.

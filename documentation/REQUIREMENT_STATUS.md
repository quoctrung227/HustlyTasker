# HUSTLYTASKER REQUIREMENT STATUS

Last updated: 2026-10-20

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
`HT-WORK-P2-02`. Trạng thái hiện tại là **HT-WORK-P2-02 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL**.
Workspace write/membership, Profile/Workspace lifecycle, monthly period và
membership soft revoke/reactivate đã triển khai trong source;
full PostgreSQL suite PASS 169/169. Additive `workspace.0003` đã qua rehearsal
trên PostgreSQL cô lập nhưng chưa apply development, nên development vẫn ở
`workspace.0002`. Invitation, activation/recovery, các business API còn lại,
frontend và deployment vẫn chưa hoàn thành.

## Nền tảng kỹ thuật

| Hạng mục | Trạng thái | Đã triển khai | Còn thiếu / vấn đề | Căn cứ |
|---|---|---|---|---|
| Dependency manifest | COMPLETE | Manifest UTF-8/pinned; Django 6.1.2 và DRF 3.18.3; current container runtime pass `pip check` | Owner host shell báo venv hoạt động, nhưng Codex managed context exit 103 và không thấy base interpreter path; cached Python 3.12 container là fallback đã kiểm chứng | `backend/requirements.txt`; xác minh HT-DB-P1-05 ngày 2026-10-19 |
| Django configuration | PARTIAL | Secret/debug/hosts/DB/CSRF/security/mailer lấy từ environment; development/production fail-fast; production-like deploy check sạch | Chưa có giá trị production thật, trusted-proxy/static/deploy contract; secret cũ cần rotate nếu từng dùng ngoài local | `backend/config/settings.py`; `.env.example`; kiểm chứng Docker 2026-10-13 |
| Database migrations | PARTIAL | 8 initial app migrations và additive `workspace/0002_profile_workspace_foundation.py` đã áp dụng trên development; source `workspace.0003_workspace_lifecycle_and_period` là additive và đã rehearsal trên PostgreSQL cô lập, gồm bảo toàn Task/Deliverable/Review | `0003` chưa apply development và chưa được phép apply production; latest successful development inventory là 2026-10-19, container được thấy đang dừng ngày 2026-10-20 và không được khởi động; mọi rollout cần inventory/backup/plan/smoke riêng | migration source; HT-DB-P1-05 evidence 2026-10-19; HT-WORK-P2-02 evidence 2026-10-20 |
| Business schema | PARTIAL | 16 concrete models gồm `Profile`/`ProfileMembership`; source thêm Profile/Workspace lifecycle status, canonical Workspace monthly period constraints/indexes và WorkspaceMember active-history state | Development chưa có `0003`; Workspace Profile/legacy period vẫn nullable cho controlled rollout; chưa migrate Client/Project/Finance/Audit, Invitation, links hay retention/purge | `backend/apps/workspace/models.py`; `services.py`; `documentation/DATABASE_SCHEMA.md` |
| Tenancy/ownership design | COMPLETE / ACCEPTED | Owner đã phê duyệt 11 nhóm quyết định: Profile tenant root, monthly Workspace, multi-Profile/multi-Owner, ownership và isolation target | Các chi tiết billing, public-link capabilities, retention duration, domain-specific/DRF action enforcement và detailed workflow được defer sang task tương ứng | `documentation/DECISION_LOG.md`; owner approval 2026-10-16 |
| RBAC/access/invitation design | COMPLETE / ACCEPTED | 14 quyết định được chốt qua ủy quyền: capability matrix, compatibility roles, least-privilege ceilings, IDOR/error/operator policy và Invitation contract | Invitation implementation, reviewer role/states và downstream domain details vẫn ở task riêng | `documentation/RBAC_DESIGN.md`; `DECISION_LOG.md`; owner delegation 2026-10-17 |
| Django Admin | PARTIAL | User, Workspace, WorkspaceMember, Task, TaskAssignment, TaskComment; mapped Profile and non-null period are read-only on existing Workspace rows; lifecycle status and WorkspaceMember fields are read-only; User auto-managed timestamps are readonly | Profile/ProfileMembership and 8 earlier domain models are not registered (10/16 total); current foundation adds no tenant-scoped admin authorization | `backend/apps/*/admin.py`; source review updated 2026-10-20 |
| DRF/API foundation | PARTIAL | HT-API-P0-03 giữ SessionAuthentication/global `IsAuthenticated`, explicit public allowlist và health policy; HT-WORK-P2-02 thêm Workspace create/update, Profile/Workspace archive/restore, member list/add/role-update/soft-revoke/reactivate, strict inputs, no-PII output và 400/403/404/409 mapping | Profile creation, Invitation và downstream routes chưa có; Profile/Workspace hard delete không được expose | `backend/api/`; `backend/apps/workspace/{views,urls,serializers,permissions,test_api,test_write_api}.py`; `API_DOCUMENTATION.md`; full PostgreSQL 169/169 chạy 2026-10-19 |
| Authentication/RBAC | PARTIAL | Session auth giữ nguyên; verified tenant contexts, scoped selectors, role ceilings và locked services; archived Profile/Workspace chặn normal/member writes nhưng vẫn tenant-safe readable; soft-revoked Workspace member mất quyền ngay | Activation/OTP/reset/logout-all, account/session lifecycle, Invitation và domain-wide RBAC còn thiếu | `backend/apps/accounts/`; `backend/apps/workspace/access.py`; `permissions.py`; `views.py`; `services.py`; `RBAC_DESIGN.md` |
| Automated tests | PARTIAL | HT-WORK gate: Workspace PostgreSQL 140/140 PASS (79.278s), full PostgreSQL 169/169 PASS (82.920s); `pip check`, system check và migration drift check PASS; migration rehearsal bảo toàn Task/Deliverable/Review | Chưa có CI hoặc one-command clean-checkout harness; `0003` controlled development rollout/smoke chưa được phê duyệt | test sources; `PROGRESS.md`; test evidence 2026-10-19, docs checkpoint 2026-10-20 |
| Frontend | NOT STARTED | Chỉ có định hướng React/Next.js | Không có source hoặc package manifest; chưa chốt React SPA hay Next.js | `documentation/TECH_STACK_DECISION.md` |
| Docker/deployment/CI | PARTIAL | PostgreSQL Compose dùng environment bắt buộc, loopback bind mặc định và giữ named volume; setup local đã được tài liệu hóa | Chưa có backend image, active deploy config hoặc CI workflow | `docker/docker-compose.yml`; `README.md` |

## Trạng thái yêu cầu nghiệp vụ F01-F16

| ID | Module | Trạng thái | Đã triển khai | Còn thiếu / vấn đề |
|---|---|---|---|---|
| F01 | Authentication | PARTIAL | Custom `User`; session register/login/logout/me; CSRF; password validation/hash; inactive block; scoped throttle; 19 tests | Activation/OTP, password reset, logout-all và production shared-cache/proxy enforcement |
| F02 | Profile & Workspace | PARTIAL | Foundation + `workspace.0002` trên development; source thêm monthly Workspace, Profile/Workspace archive/restore, Workspace create/update và member list/direct-add/role-update/soft-revoke/reactivate với locking/audit; full PostgreSQL 169/169 | `workspace.0003` chưa apply development; chưa Profile creation, Invitation hay domain-wide RBAC; rollout mọi môi trường cần phê duyệt riêng |
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
và full deactivation/session-revocation flow; Invitation delivery/onboarding
implementation; Invoice numbering/billing;
Client Portal/Guest Review exact capabilities/default expiry; retention legal
hold/purge; và project-wide response/error convention ngoài các mapping hiện
có. Policy migration vẫn là kiểm kê từng môi trường, không tự gán tenant
cho dữ liệu không xác định.

`HT-API-P1-04` đã hoàn thành scope read-only. `HT-DB-P1-05` đã hoàn tất
development-only rollout với backup/restore rehearsal, apply, direct smoke và
full regressions đạt. Trạng thái hiện tại là **HT-WORK-P2-02 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL**.
Source và isolated PostgreSQL verification đã hoàn tất, còn development ở
`workspace.0002` và production không bị tác động.
Bước tiếp theo duy nhất là Owner review và quyết định controlled development
rollout của `workspace.0003`; không mở Invitation hoặc feature task khác. Xem
`documentation/HANDOVER.md`, `RBAC_DESIGN.md` và `DECISION_LOG.md`.

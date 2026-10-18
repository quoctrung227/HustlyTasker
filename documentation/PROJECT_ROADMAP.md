# HUSTLYTASKER DEVELOPMENT ROADMAP

Last updated: 2026-10-18

## Giai đoạn hiện tại

`PHASE 2.2 - API Architecture`

Nguyên tắc thực hiện: hoàn thành P0/P1 và test gate trước khi mở business API; không tạo frontend, migration nghiệp vụ lớn hoặc thay đổi business rule khi contract chưa được chốt.

`HT-DATA-P2-01` và `PROFILE/WORKSPACE SCHEMA FOUNDATION` đã hoàn tất.
`HT-RBAC-DESIGN-P0-01` đã được chốt qua ủy quyền của Owner. Slice
`HT-RBAC-P1-03 - Tenant Access Context and Scoped Service Foundation` đã hoàn
thành và đang dừng tại `OWNER REVIEW GATE`; chưa mở Workspace/Invitation API và
chưa áp dụng `workspace.0002` lên development database.

## P0 - An toàn và khả năng kiểm chứng

### HT-OPS-P0-01 - Đồng bộ dependency backend — COMPLETE

- **Mục tiêu:** tạo manifest có thể review/cài sạch và vá dependency bảo mật.
- **Phạm vi:** `backend/requirements.txt`.
- **Ảnh hưởng:** dependency runtime; không đổi schema hay API contract.
- **Dependencies:** không.
- **Acceptance criteria:** UTF-8 không BOM/NUL; Django 6.1.2 và DRF 3.18.3; fresh install, `pip check`, system check, version assertion và API smoke test thành công.
- **Kiểm thử:** Python 3.12 container cô lập; `makemigrations --check --dry-run`; `migrate --check`; Django test discovery.
- **Rủi ro:** DRF 3.18 thay đổi một số validation/error shape, nhưng rủi ro hiện tại thấp vì chưa có serializer/view DRF.
- **Kết quả:** hoàn thành và kiểm chứng ngày 2026-10-13; test discovery cho thấy hiện có 0 automated tests.

### HT-SEC-P0-02 - Baseline cấu hình an toàn — COMPLETE

- **Mục tiêu:** loại bỏ secret/credential khỏi tracked source và tách development/production behavior.
- **Phạm vi:** `backend/config/settings.py`, `docker/docker-compose.yml`, `.gitignore`, env template sạch và tài liệu setup.
- **Ảnh hưởng:** cách khởi động backend/PostgreSQL; không đổi business schema.
- **Dependencies:** HT-OPS-P0-01.
- **Acceptance criteria:** secret, debug, allowed hosts và DB config lấy từ environment; production thiếu biến bắt buộc phải fail rõ; `.env.example` được track; DB port không bind rộng mặc định; credential từng dùng ngoài local được rotate.
- **Kiểm thử:** compose config; development `manage.py check`; production-like `check --deploy`; kết nối PostgreSQL development; không chạm production.
- **Rủi ro:** có thể làm môi trường local không khởi động nếu env migration không được hướng dẫn đầy đủ.
- **Kết quả:** hoàn thành và kiểm chứng ngày 2026-10-13. Config bắt buộc fail-fast; template không chứa secret; Compose bind PostgreSQL vào loopback mặc định; production-like deploy check sạch. Secret/credential cũ vẫn có thể tồn tại trong Git history theo yêu cầu không rewrite và phải được rotate nếu từng dùng ngoài local.

### HT-AUTH-P0-01 - User Authentication Foundation — COMPLETE

- **Mục tiêu:** cung cấp nền authentication backend để frontend tích hợp sau này mà không kéo theo Workspace/RBAC.
- **Phạm vi:** session + CSRF, register/login/logout/me, serializer, URL, throttle cơ bản, admin User và tests.
- **Ảnh hưởng:** thêm contract `/api/auth/`; DRF chuyển sang SessionAuthentication và deny-by-default. Không đổi model/schema/migration.
- **Dependencies:** HT-SEC-P0-02; owner đã cho phép chọn session cho foundation ngày 2026-10-14.
- **Acceptance criteria:** password dùng Django validation/hash; login lỗi trung tính; inactive user bị chặn; logout revoke current session; CSRF và throttle được test; không tạo Profile/Workspace.
- **Kiểm thử:** 19 integration tests trên PostgreSQL; `check`, migration drift/applied checks và server/API smoke test.
- **Rủi ro còn lại:** activation/OTP/reset chưa triển khai; throttle LocMem chưa phải production distributed control; case-insensitive identity chưa có DB constraint race-proof.
- **Kết quả:** hoàn thành và kiểm chứng ngày 2026-10-14; dừng tại review gate theo yêu cầu owner.

### HT-API-P0-03 - API deny-by-default và health endpoint — COMPLETE

- **Mục tiêu:** ngăn business endpoint tương lai vô tình public.
- **Phạm vi:** DRF settings, `backend/api/`, health/policy tests và tài liệu API liên quan.
- **Ảnh hưởng:** permission mặc định; legacy `/api/test/` được gỡ và thay bằng `/api/health/`.
- **Dependencies:** HT-SEC-P0-02; phần global `IsAuthenticated` và public auth views đã được thiết lập trong HT-AUTH-P0-01.
- **Acceptance criteria:** global permission là `IsAuthenticated`; public endpoint phải khai báo `AllowAny` rõ ràng; mọi route trong API URL tree dùng DRF; health không auth/throttle/DB, hỗ trợ `GET`/`HEAD`/`OPTIONS`; mutation method và `TRACE` trả `405`; anonymous view dùng permission mặc định bị từ chối.
- **Kiểm thử:** 10 API health/policy tests; full suite 29/29 tests trên PostgreSQL cùng system/migration/startup smoke checks.
- **Rủi ro:** `/api/health/` chỉ là liveness của HTTP process, không chứng minh PostgreSQL hay external service sẵn sàng.
- **Kết quả:** hoàn thành và kiểm chứng ngày 2026-10-15; `/api/health/` có payload JSON tối thiểu, không cache và không query DB; `/api/test/` trả `404`; authentication regression tests vẫn pass.

## P1 - Hoàn thành Phase 2.2

### HT-TEST-P1-01 - Test baseline cô lập

- **Mục tiêu:** tạo regression gate trước auth và business API.
- **Phạm vi:** test settings/fixtures, smoke tests, migration/system checks.
- **Ảnh hưởng:** developer workflow và CI sau này.
- **Dependencies:** toàn bộ P0.
- **Acceptance criteria:** test không thể kết nối production; endpoint/schema nền tảng có tests; lệnh duy nhất chạy lặp lại được trên fresh checkout.
- **Kiểm thử:** full Django suite trên PostgreSQL test database.
- **Rủi ro:** SQLite nhanh hơn nhưng không phản ánh đầy đủ PostgreSQL; ưu tiên PostgreSQL container.

### HT-AUTH-P1-02 - Xác minh và khôi phục tài khoản

- **Mục tiêu:** hoàn tất activation và password recovery an toàn trên foundation hiện có.
- **Phạm vi:** email link hoặc OTP, token one-time/expiry, reset password, logout-all và production-grade abuse controls.
- **Ảnh hưởng:** email delivery, account lifecycle và khả năng revoke mọi session.
- **Dependencies:** owner phê duyệt activation link hay OTP; shared-cache/proxy deployment contract; HT-TEST-P1-01.
- **Acceptance criteria:** token hash-at-rest, one-time và hết hạn; không user enumeration; reset revoke session phù hợp; throttle production được kiểm chứng.
- **Kiểm thử:** activation/reset success-failure-expiry-replay, neutral response, session revocation và abuse controls.
- **Rủi ro:** tạo user inactive trước khi có đường activate sẽ khóa luồng onboarding; không triển khai rời rạc.

### HT-RBAC-DESIGN-P0-01 - Capability, tenant scope và invitation contract — COMPLETE / ACCEPTED BY OWNER DELEGATION

- **Mục tiêu:** chốt permission contract trước khi một endpoint tenant nào được mở.
- **Phạm vi:** action-level capability matrix hai tầng; request/query/service
  boundary; IDOR/error contract; ORM/Admin/bulk bypass controls; Profile
  Invitation lifecycle; planned API; negative/concurrency tests; dependency
  order. Chi tiết tại `documentation/RBAC_DESIGN.md`.
- **Ảnh hưởng:** chốt contract cho access context, role compatibility,
  invitation và operator boundary; không tự triển khai Invitation/API.
- **Dependencies:** 11 quyết định của HT-DATA-P2-01 và schema foundation đã
  kiểm chứng; source/reference/PostgreSQL inventory đã được đối chiếu.
- **Acceptance evidence:** matrix phân biệt approved/proposed/open; Profile
  scope và same-tenant rules đầy đủ; invitation token hash/state/concurrency
  contract; planned routes; isolation/negative tests; implementation order;
  bảng đối chiếu đủ 11 quyết định đã duyệt. Audit ban đầu ghi nhận nhóm 4 có
  xung đột nhãn và nhóm 6–9/11 thiếu nội dung; tài liệu đã sửa để cả 11 nhóm
  đều `MATCH` mà không yêu cầu owner phê duyệt lại.
- **Phát hiện bắt buộc trước implementation:** refactor membership update để
  scope membership trước lookup, và Workspace direct-add để scope cả Workspace
  lẫn target member/User; không expose Client/Finance/Audit khi chưa có tenant
  path; không dùng Workspace owner FK hay selected Profile làm quyền.
- **Kết quả:** 14 quyết định chi tiết được chốt với trạng thái
  `APPROVED BY OWNER DELEGATION`; role compatibility, least-privilege ceilings,
  non-enumeration, Invitation TTL/rate/retention và platform Admin boundary đã
  được ghi trong `RBAC_DESIGN.md`/`DECISION_LOG.md`. Reviewer role/states và
  các domain downstream vẫn dành cho task riêng.

### HT-RBAC-P1-03 - Tenant Access Context and Scoped Service Foundation — COMPLETE / OWNER REVIEW GATE

- **Mục tiêu:** tạo boundary dùng lại được để resolve Profile/Workspace từ User
  và membership thực tế, chống cross-tenant/IDOR trước khi mở business API.
- **Phạm vi đã hoàn thành:** immutable verified contexts; scoped Profile và
  Workspace selectors; read/edit/member-management capabilities; refactor
  `update_profile_membership()` và `add_workspace_member()`; role ceilings,
  duplicate/concurrency handling, audit atomicity và security regression tests.
- **Compatibility:** `WorkspaceMember.ADMIN` = Workspace Admin,
  `MEMBER` = Editor, `VIEWER` = read-only Viewer; legacy `OWNER` fail closed và
  không được cấp mới. Không đổi enum hay schema.
- **Kiểm thử:** final targeted Workspace 51/51 và full PostgreSQL 80/80 PASS;
  system check, dependency check và migration drift check PASS ngày 2026-10-18.
- **Không thuộc scope:** DRF permission classes/endpoints, Workspace API,
  Invitation model/API, Client/Finance/Audit selectors, Task/Review workflow,
  User deactivation/session-revocation lifecycle và áp dụng migration `0002`.
- **Rủi ro còn lại:** direct ORM/bulk/raw/Admin có thể bypass services; các
  domain chưa có tenant path chưa thể được expose an toàn.
- **Review gate / bước kế tiếp:** owner review foundation hiện tại. Sau khi được
  duyệt, mở một task riêng cho Profile/Workspace read API và DRF permission
  integration tối thiểu; Invitation vẫn để sau account/email verification.

### HT-API-P1-04 - API structure, serializers và versioning

- **Mục tiêu:** tạo convention thống nhất cho `/api/v1/`, serializers, errors và pagination.
- **Phạm vi:** API URL modules, base serializers/validators, response/error conventions, `API_DOCUMENTATION.md`.
- **Ảnh hưởng:** contract của mọi endpoint tiếp theo.
- **Dependencies:** HT-AUTH-P1-02, HT-RBAC-P1-03.
- **Acceptance criteria:** route versioned; field mutability rõ; UUID/date/decimal format thống nhất; validation không rò dữ liệu tenant; docs và tests khớp code.
- **Kiểm thử:** serializer unit tests và API contract tests.
- **Rủi ro:** không expose CRUD generic trước khi object permission hoàn chỉnh.

## P2 - Business domains tiếp theo

### HT-DATA-P2-01 - Chốt tenancy và schema gaps — COMPLETE / ACCEPTED

- **Mục tiêu:** quyết định Profile/Workspace ownership, public link scope và retention trước migration mới.
- **Phạm vi:** ADR/schema design; không tự động sửa migration trong bước quyết định.
- **Ảnh hưởng:** Client, ShareLink, Invoice, AuditLog, invitation và Profile.
- **Dependencies:** audit source/reference/documentation hoàn tất; 11 nhóm quyết định được owner phê duyệt ngày 2026-10-16.
- **Acceptance criteria:** mỗi business object có một ownership path; delete policy và backfill plan rõ; migration mới không sửa `0001_initial`.
- **Kiểm thử:** design được đối chiếu với source/model/migration và outsource; implementation và migration rehearsal thuộc task foundation riêng bên dưới.
- **Rủi ro:** quyết định sai có thể gây migration dữ liệu lớn hoặc lộ cross-tenant.
- **Quyết định:** Profile là tenant root; Workspace là scope vận hành theo tháng; User là identity global; Profile membership và Workspace membership tách lớp; Client/Project thuộc Profile; Invoice thuộc Workspace và Client cùng Profile; external Client/Guest dùng principal tách biệt.
- **Kết quả:** audit/ADR, ownership matrix, isolation invariants và kế hoạch migration/backfill hoàn tất; owner phê duyệt 11 nhóm quyết định ngày 2026-10-16. Chi tiết billing, link capabilities/default expiry, retention duration và Task/Review/payroll vẫn được defer đúng phạm vi.

### PROFILE/WORKSPACE SCHEMA FOUNDATION — COMPLETE

- **Mục tiêu:** hiện thực phần tenant foundation nhỏ nhất mà không mở Workspace API hay RBAC.
- **Phạm vi implemented in source:** `Profile`, `ProfileMembership`; Profile roles `OWNER/ADMIN/MEMBER`; partial unique active/check/index membership constraints; nullable transitional `Workspace.profile`; protected `Workspace.owner`; one-way tenant mapping guard including stale legacy-save locking; transactional Profile-owner service; audited direct Workspace add cho active Profile member; model persistence validators; additive migration `workspace/0002_profile_workspace_foundation.py`; model/migration tests.
- **Dữ liệu:** read-only inventory development PostgreSQL có 0 business rows và 3 User rows. Không tạo tenant mapping giả định.
- **Migration state:** `0002` chỉ chạy trên disposable PostgreSQL test databases, gồm empty schema và populated relationship fixture; chưa apply development database.
- **Verification:** rerun 2026-10-17; targeted `apps.workspace` 32/32 PASS; full PostgreSQL suite 61/61 PASS, gồm Authentication/API regressions; `pip check`, `manage.py check` và `makemigrations --check --dry-run` PASS.
- **Không thuộc task:** Invitation/API, Project/Client/Finance migrations, soft delete, full RBAC/query scoping, public-link flows, detailed Task/Review workflow hoặc frontend.
- **Review gate:** implementation/verification hoàn tất; owner đã cho phép đi
  tiếp sang thiết kế RBAC nhưng chưa cho phép apply development migration hay
  triển khai Workspace API/RBAC. Chỉ apply sau operational approval cùng
  inventory/backup policy phù hợp.

### HT-WORK-P2-02 - Workspace/membership API

- **Mục tiêu:** hoàn tất F02/F03 sau tenancy decision.
- **Phạm vi:** workspace CRUD có scope, invitation lifecycle và tests.
- **Dependencies:** `HT-RBAC-DESIGN-P0-01` đã được chấp thuận và
  `HT-RBAC-P1-03` đã hoàn tất; owner duyệt review gate hiện tại; schema
  foundation được áp dụng có kiểm soát ở môi trường đích sau inventory/backup.
  Trước phần Invitation API còn cần account/email verification và identity
  binding dù contract TTL/rate/retention đã được chốt.
- **Acceptance criteria:** invitation expiry/accept/decline/revoke an toàn; owner/admin policy rõ; concurrency không tạo membership trùng.
- **Kiểm thử:** role matrix, token expiry, duplicate/concurrent accept.
- **Rủi ro:** invitation token phải hash-at-rest và không log.

### HT-TASK-P2-03 - Task lifecycle/assignment/comments

- **Mục tiêu:** hoàn tất nền F04/F11 trước marketplace/review.
- **Phạm vi:** service transition, task API, assignment/comment validation và tests.
- **Dependencies:** canonical task states được phê duyệt; Workspace API/RBAC.
- **Acceptance criteria:** transition chạy transaction; invalid transition bị từ chối; membership được kiểm tra; history/audit không bị mất.
- **Kiểm thử:** state transition, concurrency, IDOR và regression tests.
- **Rủi ro:** task completion liên quan review/payroll, không được tự suy diễn business rule.

Các module Review/Guest/Client Portal, CRM/Finance/Payroll, Notification/Automation và frontend chỉ được xếp lịch sau các nền tảng trên theo thứ tự dependency trong `ORIGINAL_REQUIREMENTS.md`.

## P3 - Quality, delivery và mở rộng

- OpenAPI/schema publishing sau khi API contract ổn định.
- CI chạy dependency check, migration drift, system checks và tests trên PostgreSQL service.
- Backend container/deployment hardening, logging/monitoring và backup strategy.
- Frontend chỉ bắt đầu sau khi chủ dự án chốt React SPA hay Next.js và API/auth contract đã ổn định.

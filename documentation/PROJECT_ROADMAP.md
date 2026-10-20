# HUSTLYTASKER DEVELOPMENT ROADMAP

Last updated: 2026-10-21

## Giai đoạn hiện tại

`PHASE 2.2 - API Architecture`

Nguyên tắc thực hiện: hoàn thành P0/P1 và test gate trước khi mở business API; không tạo frontend, migration nghiệp vụ lớn hoặc thay đổi business rule khi contract chưa được chốt.

`HT-DATA-P2-01` và `PROFILE/WORKSPACE SCHEMA FOUNDATION` đã hoàn tất.
`HT-RBAC-DESIGN-P0-01` đã được chốt qua ủy quyền của Owner. Slice
`HT-RBAC-P1-03 - Tenant Access Context and Scoped Service Foundation` đã hoàn
thành và được Owner cho phép dùng làm nền cho `HT-API-P1-04`. Slice read-only
`HT-API-P1-04 - Profile/Workspace Read API & DRF Permission Integration` đã
hoàn thành. Owner sau đó phê duyệt có điều kiện task vận hành
`HT-DB-P1-05` để inventory, backup, áp dụng `workspace.0002` trên development
và smoke API. Task đã `COMPLETE / OWNER REVIEW GATE`: backup và restore
rehearsal đạt, migration đã áp dụng an toàn trên development, direct smoke đạt,
và full PostgreSQL suite PASS 101/101. Sau khi Owner review và mở task kế tiếp,
`HT-WORK-P2-02` đã hoàn tất cả write/membership foundation lẫn phần phụ thuộc
schema: lifecycle Profile/Workspace, monthly period, và soft revoke/reactivate
Workspace membership. Owner sau đó mở `HT-DB-P1-06`; additive migration
`workspace.0003` đã được backup/rehearsal rồi áp dụng an toàn lên đúng
development database. Direct development smoke, targeted suites và full
PostgreSQL 169/169 đều PASS. `HT-DB-P1-06` đã dừng đúng Owner review gate và
Owner sau đó mở `HT-TASK-P2-03`. Task/Deliverable/internal Review workflow hiện
đã implement trong source; targeted PostgreSQL 33/33, regression 169/169 và
full PostgreSQL 202/202 đều PASS. Trạng thái là `IMPLEMENTATION COMPLETE —
PENDING DEVELOPMENT MIGRATION APPROVAL`. Additive `tasks.0002`/
`reviews.0002` chưa apply development; production không bị tác động và
Invitation vẫn ngoài scope.

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

### HT-RBAC-P1-03 - Tenant Access Context and Scoped Service Foundation — COMPLETE

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
- **Không thuộc scope của P1-03:** DRF permission classes/endpoints, Workspace
  API, Invitation model/API, Client/Finance/Audit selectors, Task/Review
  workflow, User deactivation/session-revocation lifecycle và áp dụng migration
  `0002`. Slice P1-04 sau đó chỉ hiện thực phần read API/DRF permission tối thiểu.
- **Rủi ro còn lại:** direct ORM/bulk/raw/Admin có thể bypass services; các
  domain chưa có tenant path chưa thể được expose an toàn.
- **Kết quả review gate:** Owner đã cho phép mở task riêng P1-04 cho read API và
  DRF permission integration tối thiểu. Invitation vẫn để sau account/email
  verification và một task được phê duyệt riêng.

### HT-API-P1-04 - Profile/Workspace Read API & DRF Permission Integration — COMPLETE

- **Mục tiêu:** mở read-only Profile/Workspace API an toàn dưới `/api/v1/` và
  nối trực tiếp DRF với access context/scoped selector của P1-03.
- **Phạm vi hoàn thành:** bốn route Profile list/detail và nested Workspace
  list/detail; minimal read serializers; active-identity/Profile/Workspace read
  permissions; bounded pagination; stable ordering; non-cacheable responses;
  generic non-enumerating `404`; tài liệu API.
- **Access contract:** SessionAuthentication và global deny-by-default giữ
  nguyên; không `AllowAny`. Profile Owner/Admin đọc mọi mapped Workspace cùng
  Profile; ordinary Member chỉ đọc Workspace có effective `ADMIN`, `MEMBER`
  hoặc `VIEWER`; legacy `OWNER`, transitional owner FK và staff/superuser không
  bypass tenant scope.
- **Response contract:** Profile chỉ có `id/name/created_at/updated_at`;
  Workspace có `id/profile_id/name/description/created_at/updated_at`;
  UUID render thành chuỗi. List envelope dùng `count/next/previous/results`,
  page size mặc định 20 và tối đa 100.
- **Dependencies:** P1-03 đã hoàn thành và existing SessionAuthentication đang
  hoạt động. HT-AUTH-P1-02 không chặn authenticated read slice này nhưng vẫn là
  dependency của Invitation/onboarding production.
- **Kiểm thử:** targeted API 21/21; Authentication/API Foundation 29/29; final
  full PostgreSQL suite 101/101; system/dependency/compile/migration-drift
  checks PASS ngày 2026-10-18.
- **Không thuộc scope:** write/CRUD lifecycle, membership management,
  Invitation, Client/Project/Task/Finance, model/schema/migration và frontend.
- **Operational gate:** HT-DB-P1-05 đã hoàn tất rollout development-only: plan
  khớp migration additive, `workspace.0002` đã apply, direct smoke và current
  101-test PostgreSQL regression đều PASS. Việc này không mở write/membership/
  Invitation API hoặc tạo bằng chứng rollout cho môi trường khác.

### HT-DB-P1-05 - Controlled Development Migration & API Smoke Verification — COMPLETE / OWNER REVIEW GATE

- **Mục tiêu:** áp dụng an toàn migration đã có
  `workspace.0002_profile_workspace_foundation` lên đúng development database,
  sau đó smoke read API và chạy regression gate.
- **Authorization:** development database only; không production, không reset,
  delete, fake migration, auto-rollback, mapping giả định hay tạo hạ tầng mới.
- **Đã hoàn thành:** xác minh local Compose target; inventory/schema/relationship
  checks; review migration additive; Git-ignored backup với SHA-256/TOC/full
  read; restore rehearsal trên database tạm; target-specific plan; apply đúng
  `workspace.0002`; post-check schema/data/constraints; direct HTTP smoke; và
  full regression gate.
- **Inventory trước/sau:** trước apply có 3 active Users, 0 checked business
  rows, 26 migration rows và chưa có Profile schema. Sau apply có 27 migration
  rows, Profile/ProfileMembership và nullable `Workspace.profile_id`; business
  counts vẫn 0, không mapping giả định, orphan hoặc constraint chưa validate.
- **Environment:** không tạo `.env`; dùng secret development ngẫu nhiên chỉ
  trong process và runtime credential sẵn có, không log giá trị. Owner host
  shell báo venv hoạt động nhưng Codex managed context exit 103 và không thấy
  base path; vì vậy dùng cached Python 3.12 container tạm với source read-only
  và xóa sau khi chạy, không sửa venv.
- **Verification:** direct health `200`; bốn tenant route anonymous `403`;
  CSRF behavior đúng; targeted API 21/21, auth/API 29/29, full PostgreSQL
  101/101; system/migration consistency checks PASS; không còn database hoặc
  container tạm.
- **Review gate:** dừng để Owner review. Không tự động mở HT-WORK-P2-02 hoặc
  Workspace Write/Membership/Invitation; mọi môi trường khác vẫn cần inventory,
  backup và authorization riêng.

### HT-DB-P1-06 - Controlled Workspace 0003 Development Migration & Verification — COMPLETE / OWNER REVIEW GATE

- **Mục tiêu:** áp dụng an toàn migration hiện hữu
  `workspace.0003_workspace_lifecycle_and_period` lên đúng development database
  sau backup/rehearsal, rồi xác minh schema, API và regressions.
- **Authorization:** development database only; không production, reset,
  delete, fake/reverse migration, mapping giả định, business fixture hoặc module
  mới.
- **Đã hoàn thành:** xác minh local Compose PostgreSQL 16.14 target; inventory
  migration/schema/data; backup custom-format Git-ignored với SHA-256, TOC và
  full-read; full restore rehearsal; exact migration plan; apply `0003`; và
  post-check columns/constraints/indexes/data.
- **Inventory trước/sau:** migration rows tăng 27 → 28; 3 active Users, 2
  sessions và zero checked business rows không đổi. Không có invalid
  lifecycle/period, duplicate Profile/month, unvalidated constraint, orphan,
  test/rehearsal database hoặc guessed tenant/month mapping.
- **Verification:** dependency/system/migration checks PASS. **DEV SMOKE
  PASSED** không tạo fixture: health/CSRF đúng và toàn bộ tenant route từ chối
  anonymous, inventory không đổi. **ISOLATED INTEGRATION TEST PASSED:** targeted
  lifecycle/schema 17/17, Workspace 140/140, auth/API 29/29 và full PostgreSQL
  169/169. Test databases và runner tạm đã được hủy.
- **Review gate:** dừng để Owner review. Không tự mở Task, Invitation,
  Client/Project/Finance/Review hoặc frontend. Mọi persistent environment khác
  cần inventory, backup, risk review và authorization riêng.

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
- **Migration state:** `0002` đã được kiểm chứng trên disposable PostgreSQL test databases và được áp dụng có kiểm soát trên development ngày 2026-10-19 sau inventory, backup và restore rehearsal; chưa có authorization cho môi trường khác.
- **Verification:** rerun 2026-10-17; targeted `apps.workspace` 32/32 PASS; full PostgreSQL suite 61/61 PASS, gồm Authentication/API regressions; `pip check`, `manage.py check` và `makemigrations --check --dry-run` PASS.
- **Không thuộc task:** Invitation/API, Project/Client/Finance migrations, soft delete, full RBAC/query scoping, public-link flows, detailed Task/Review workflow hoặc frontend.
- **Review gate:** implementation/verification và controlled development apply
  qua HT-DB-P1-05 đã hoàn tất. Authorization này không mở Workspace write,
  membership, Invitation hoặc rollout sang môi trường khác.

### HT-WORK-P2-02 — COMPLETE — DEVELOPMENT ROLLOUT VERIFIED

- **Mục tiêu:** mở write surface nhỏ nhất cho Workspace và direct membership
  management sau tenancy/access foundation, không kéo theo Invitation hoặc
  business domain khác.
- **Đã implement trong source:** `POST` nested Workspace collection với
  canonical first-of-month `period`; `PATCH` Workspace detail cho
  `name`/`description`; Profile và Workspace archive/restore; `GET`/`POST`
  nested member collection; `PATCH` role; và `DELETE` member detail dưới dạng
  soft revoke. Strict input không cho mass assignment/re-parent; response
  member không có User PII.
- **Quyền:** Profile Owner/Admin tạo và sửa Workspace, quản lý membership cùng
  Profile; Workspace Admin chỉ sửa metadata Workspace được phân công và quản lý
  Editor/Viewer. Editor/Viewer bị deny; legacy Workspace `OWNER` fail closed.
- **Lifecycle/access:** Profile Owner archive/restore Profile; Profile
  Owner/Admin archive/restore Workspace. Archived tenant/workspace records vẫn
  đọc được trong tenant scope nhưng ordinary metadata, child và membership
  writes bị chặn. Không expose hard delete cho Profile/Workspace.
- **Membership history:** revoke đặt `WorkspaceMember.is_active=False`, mất
  effective access ngay và giữ row lịch sử; eligible re-add tái kích hoạt đúng
  row đó. Profile Owner/Admin và Workspace Admin tiếp tục bị giới hạn bởi role
  ceilings đã duyệt.
- **Service boundary:** resolve tenant trước target, revalidate dưới lock,
  transaction + AuditLog atomic; duplicate active member hoặc monthly period
  map `409`, invalid input `400`, thiếu action capability `403`, unknown/
  wrong-parent/cross-tenant `404`.
- **Schema source:** additive
  `workspace.0003_workspace_lifecycle_and_period` thêm lifecycle status,
  monthly period constraints/indexes và member active state. Uniqueness
  `(profile, period)` áp dụng cả Workspace archived; legacy `NULL` period được
  giữ để rollout an toàn, còn supported create bắt buộc first-of-month.
- **Late-revocation hardening:** roster selector gắn authority hiện tại của
  actor vào SQL và chỉ trả assignment có active same-Profile membership; revoke
  role sau permission check nhưng trước lazy evaluation sẽ fail closed.
- **Kiểm thử implementation:** `pip check`, Django check và
  `makemigrations --check --dry-run` PASS; Workspace PostgreSQL 140/140 và full
  PostgreSQL 169/169 PASS. Rehearsal migration `0002 -> 0003` trên PostgreSQL cô
  lập bảo toàn Task/Deliverable/Review.
- **Development evidence:** `HT-DB-P1-06` ngày 2026-10-20 đã backup/rehearse và
  apply `workspace.0003` lên local loopback Compose PostgreSQL 16.14. Sau apply
  có 28 migration rows, 3 active Users, 2 sessions và zero checked business
  rows; columns/constraints/indexes mới hợp lệ, không guessed mapping hay
  schema/data anomaly. Current direct smoke và full PostgreSQL 169/169 PASS;
  production không được truy cập.
- **Dependencies đã đạt:** `HT-RBAC-DESIGN-P0-01`, `HT-RBAC-P1-03`,
  `HT-API-P1-04`, và controlled development rollout `HT-DB-P1-05`.
- **Review gate:** development rollout đã hoàn tất qua `HT-DB-P1-06`; dừng tại
  Owner review. Không tự mở feature mới, Invitation, Profile creation,
  Client/Project/Task/Finance, Review workflow hay frontend.

### HT-TASK-P2-03 - Task Management & Internal Approval Workflow — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL

- **Mục tiêu:** hiện thực workflow backend từ Task assignment đến Deliverable
  và internal Review mà không kéo theo Client approval, Payroll/Payment,
  Marketplace, media pipeline hoặc Comments API.
- **Phạm vi đã implement trong source:** Task create/read/update/assign/start;
  Deliverable history/list/submit; approve/request changes; scoped DRF
  permissions; locked transactional services; audit; constraints/indexes;
  additive `tasks.0002` và `reviews.0002`; tests.
- **Workflow:** `PENDING -> ASSIGNED -> WORKING -> REVIEW`, sau đó
  `COMPLETED` chỉ khi latest submitted Deliverable được internal approve, hoặc
  trở lại `WORKING` khi request changes để revise/resubmit. Không có arbitrary
  status API; `CANCELLED` chưa có public transition.
- **RBAC:** Profile Owner/Admin và Workspace Admin manage/review trong active
  scope; active Profile `MEMBER` + Workspace `MEMBER` (Editor) chỉ start/submit
  khi là current active assignee; self-review bị cấm. Mọi effective Workspace
  reader có thể đọc Task và Deliverable history trong Workspace được cấp.
- **Security/API boundary:** SessionAuthentication + CSRF + deny-by-default;
  strict input; no User PII; nested tenant-scoped lookup; generic `404` cho
  malformed/wrong-parent/cross-tenant; không PUT/DELETE/Task status endpoint.
- **Schema/backfill:** legacy assignment được đặt inactive và legacy Deliverable
  revision để `NULL`; không đoán current assignee hay revision. Trước rollout
  phải inventory invalid enum, duplicate Review/Deliverable, assignment legacy,
  backup và review exact plan.
- **Verification:** dependency/system/migration-drift checks PASS; targeted
  service/API/migration PostgreSQL **33/33 PASS** trong 7.673s; existing
  Authentication/API/Workspace regressions **169/169 PASS** trong 87.783s; và
  final full PostgreSQL **202/202 PASS** trong 92.343s. Test databases đều được
  hủy; independent final code review PASS.
- **Development migration gate:** `tasks.0002` và `reviews.0002` chưa apply
  development và không được phép apply trong task implementation này.
  Read-only `showmigrations` xác nhận Workspace 0001-0003 applied nhưng Tasks/
  Reviews chỉ có 0001; `migrate --plan` chỉ liệt kê additive `tasks.0002` rồi
  `reviews.0002`. Dừng ở Owner review gate trước mọi apply.
- **Remaining product boundaries:** Task soft delete/retention, Client approval,
  actual file upload/storage, comments, payroll pricing/eligibility/trigger,
  and external review remain separate tasks. Internal approval không tạo
  Payroll/Payment hoặc tính tiền.

Các module Review/Guest/Client Portal, CRM/Finance/Payroll, Notification/Automation và frontend chỉ được xếp lịch sau các nền tảng trên theo thứ tự dependency trong `ORIGINAL_REQUIREMENTS.md`.

## P3 - Quality, delivery và mở rộng

- OpenAPI/schema publishing sau khi API contract ổn định.
- CI chạy dependency check, migration drift, system checks và tests trên PostgreSQL service.
- Backend container/deployment hardening, logging/monitoring và backup strategy.
- Frontend chỉ bắt đầu sau khi chủ dự án chốt React SPA hay Next.js và API/auth contract đã ổn định.

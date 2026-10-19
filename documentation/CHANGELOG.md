# CHANGELOG

Lịch sử thay đổi của dự án HustlyTasker.

## Unreleased - 2026-10-19

### Workspace Write API & Membership Management (HT-WORK-P2-02)

- Bổ sung `POST` cho Workspace collection và `PATCH` cho Workspace detail dưới
  nested Profile; chỉ nhận `name`/`description`, mọi field server-owned hoặc
  field lạ bị từ chối. Profile được lấy từ URL/context, không cho re-parent
  Workspace hoặc giả mạo owner.
- Bổ sung Workspace-member manager roster `GET`, direct-add `POST` bằng
  `target_profile_membership_id`, và role-update `PATCH`. Response chỉ gồm ID
  assignment, ProfileMembership ID, role và timestamps; không trả User ID,
  email, username hoặc PII.
- Áp dụng role ceilings đã duyệt: Profile Owner/Admin tạo/cập nhật Workspace và
  quản lý `ADMIN/MEMBER/VIEWER`; Workspace Admin chỉ sửa metadata Workspace của
  mình và quản lý `MEMBER/VIEWER`. Editor, Viewer, Profile Member chưa được gán,
  legacy Workspace `OWNER`, staff/superuser và cross-tenant input đều fail
  closed.
- Roster được ràng buộc với authority hiện tại của actor ngay trong queryset và
  chỉ trả assignment hiệu lực có active User + active same-Profile membership.
  Lookup nested sai tenant/wrong parent không làm lộ tồn tại; API chuẩn hóa
  validation/permission/not-found/conflict thành `400`/`403`/`404`/`409`.
- Các write service dùng transaction, Profile-first row locks, revalidation và
  AuditLog nguyên tử cho `workspace.created`, `workspace.updated`,
  `workspace.membership.created`, `workspace.membership.updated`; rollback cả
  mutation khi audit thất bại và xử lý duplicate/concurrency ổn định.
- Giữ SessionAuthentication, CSRF cho unsafe methods, DRF deny-by-default và
  không thêm `AllowAny`. Verification cuối: Workspace 111/111,
  Authentication/API Foundation 29/29, full PostgreSQL 140/140; Django system
  check và migration consistency đều PASS.
- Đây là schema-free slice: không đổi model, không tạo `workspace.0003`, không
  đổi development data; `workspace.0002` vẫn là migration mới nhất đã apply.
  Archive/restore Workspace và DELETE/revoke/deactivate WorkspaceMember vẫn
  trả `405` vì chưa có lifecycle/history schema và policy được Owner duyệt.

### Controlled development migration completed (HT-DB-P1-05)

- Khôi phục Django development runtime bằng biến môi trường chỉ tồn tại trong
  process và cached Python 3.12 container; không tạo `.env`, không ghi secret,
  không reset credential và không sửa venv/source.
- Xác minh lại backup trước migration và thực hiện restore rehearsal đầy đủ
  trên database tạm biệt lập; schema/data trước migration khớp archive và
  database rehearsal đã được dọn.
- Review `migrate --plan` và áp dụng đúng migration additive
  `workspace.0002_profile_workspace_foundation` lên development. Hậu kiểm xác
  nhận 27 migration rows, Profile/ProfileMembership tables,
  `Workspace.profile_id`, constraints/indexes hợp lệ; 3 User và toàn bộ
  business counts vẫn không đổi, không tạo tenant mapping giả định.
- Direct HTTP smoke đạt: health `200`; bốn Profile/Workspace route và
  `/api/auth/me/` anonymous `403`; CSRF bootstrap `200`; login giả thiếu token
  `403`, có token hợp lệ `400`; không có `500` hoặc session mới.
- Regression gate hiện thời PASS: targeted read API 21/21, Authentication/API
  Foundation 29/29, full PostgreSQL suite 101/101; dependency, Django system,
  migration drift/applied checks và cleanup checks đều đạt.
- Không thay đổi backend source, model, migration file, authentication hoặc API
  contract. Chỉ existing migration được apply trên development đã phê duyệt;
  không production, không business fixture, không write/membership/Invitation
  API.

### Pre-migration safety checkpoint (superseded historical evidence)

- Xác minh độc lập PostgreSQL development hiện hữu từ Compose của repository:
  `workspace.0001` đã apply, `workspace.0002` chưa apply; Profile tables và
  `Workspace.profile_id` chưa tồn tại.
- Kiểm kê trước migration ghi nhận 3 User đều active và 0 Workspace,
  WorkspaceMember, Task, Client, Invoice, Payment, AuditLog; không có orphan,
  foreign key chưa validate hoặc test database còn sót.
- Xác nhận migration `workspace.0002_profile_workspace_foundation` không đổi,
  chỉ gồm thay đổi additive và không có backfill/delete/drop/rename hay mapping
  tenant giả định.
- Tạo backup PostgreSQL custom-format trong `.local_backups/HT-DB-P1-05/`,
  thêm thư mục này vào `.gitignore`, và xác minh host/container SHA-256 khớp,
  TOC đọc được, toàn bộ archive stream qua `pg_restore` thành công. Không restore
  vào database nào.
- Dừng trước `migrate --plan` và apply vì repository không có `.env`, runtime
  không có `DJANGO_SECRET_KEY` development hợp lệ, còn Python/venv host không
  hoạt động. Không tự tạo secret, trích xuất/reset credential hay lách settings.
- Không thay đổi backend code, model, migration, API contract, authentication,
  development schema hoặc row. Smoke/regression mới chưa chạy; kết quả 101/101
  của P1-04 vẫn chỉ là bằng chứng lịch sử.

### Profile/Workspace read API and DRF tenant permissions

- Thêm bốn endpoint read-only dưới `/api/v1/`: Profile list/detail và nested
  Workspace list/detail. Giữ nguyên SessionAuthentication, global
  deny-by-default và không thêm `AllowAny`.
- Thêm minimal serializers chỉ trả metadata đã phê duyệt; không expose
  transitional owner, membership, role, email hoặc PII.
- Nối DRF permission trực tiếp với tenant access contexts và scoped selectors
  từ HT-RBAC-P1-03. Profile Owner/Admin đọc mapped Workspace cùng Profile;
  ordinary Member chỉ đọc Workspace có effective `ADMIN`, `MEMBER` hoặc
  `VIEWER`; legacy `OWNER`, Profile-null, transitional owner và platform flags
  không bypass scope.
- Chuẩn hóa list bằng page-number pagination bounded (20 mặc định, 100 tối đa)
  và stable ordering. Malformed, unknown, cross-tenant, wrong-parent và
  out-of-scope IDs cùng trả generic JSON `404`.
- Chỉ hỗ trợ `GET`/`HEAD`/`OPTIONS`, thêm no-cache boundary và xác nhận unsafe
  request phải qua auth/CSRF và tenant permission trước (`403`/`404` nếu fail);
  request đã được authorize với CSRF hợp lệ mới trả `405`. Không nhánh nào thay
  đổi dữ liệu hay AuditLog.
- Sửa race khi Profile membership bị revoke sau DRF permission nhưng trước lúc
  queryset được evaluate: late stale-context exception được map về cùng generic
  `404`; thêm regression cho Workspace list/detail.
- Thêm 21 PostgreSQL API tests cho session access/CSRF, multi-Profile, role matrix,
  revoke/inactive, IDOR, legacy/unmapped data, staff non-bypass, pagination và
  no-write contract. Final full suite PASS 101/101; Authentication/API
  Foundation regression PASS 29/29.
- Không đổi model, schema, migration, authentication, service business rule,
  Docker hoặc development data. `workspace.0002` vẫn chưa apply development;
  rollout và smoke test cần một operational approval riêng.

### Documentation and handover governance

- Thêm root `AGENTS.md` làm quy tắc bắt buộc cho mọi agent: đọc source/docs và
  Git trước khi code, bảo toàn dirty worktree, không scope creep, checkpoint
  task dài, verification trung thực và cập nhật tài liệu theo thay đổi thực tế.
- Thêm `documentation/HANDOVER.md` làm checkpoint bàn giao độc lập với lịch sử
  hội thoại, gồm trạng thái stack, task, Git, test, quyết định, setup và bước
  tiếp tục an toàn.
- README trỏ developer mới tới `AGENTS.md` và `HANDOVER.md`; không ghi secret
  hoặc credential vào tài liệu.

### Workspace architecture decision

- Hoàn tất audit thiết kế `HT-DATA-P2-01` dựa trên current Django source,
  migrations, requirement gốc và legacy discovery evidence.
- Ghi nhận tại thời điểm audit trước implementation: schema chưa có Profile;
  Workspace ownership có hai nguồn truth; Client/Finance/Audit chưa có tenant
  path; Task actors chưa được ràng buộc cùng Workspace.
- Owner phê duyệt Profile làm tenant root và Workspace làm operational scope
  theo tháng; tách Profile membership, Workspace participation và
  Client/Guest access principals.
- Bổ sung ownership matrix, data-isolation invariants, migration/backfill plan
  và test plan vào `DECISION_LOG.md` và `DATABASE_SCHEMA.md`.
- Chốt 11 nhóm quyết định: multi-Profile, multi-Owner, administrator
  inheritance, invitation consent/direct-add boundary, Client/Project,
  Workspace-scoped finance, separate public links, soft-delete target,
  migration safety và high-level Task/Review loop.
- HT-DATA-P2-01 design là `COMPLETE / ACCEPTED`; bản thân task design không
  thay đổi model, migration, User/authentication, API, dữ liệu hoặc frontend.

### RBAC, tenant access và invitation design

- Thêm `documentation/RBAC_DESIGN.md` cho `HT-RBAC-DESIGN-P0-01`; task hiện
  `COMPLETE / ACCEPTED — APPROVED BY OWNER DELEGATION`.
- Hoàn thiện capability matrix hai tầng Profile/Workspace, tách internal roles
  khỏi Client Portal/Guest Review và không coi enum hiện có là quyền đã duyệt.
- Đề xuất request context, tenant-scoped queryset, same-tenant input
  validation, non-enumerating IDOR/error behavior, service/transaction lock
  order và controls cho ORM/bulk/job/Django Admin bypass.
- Ghi nhận `update_profile_membership()` lookup membership globally, còn
  `add_workspace_member()` lookup Workspace globally và nhận target User đã
  resolve ngoài scope; chưa có API khai thác nhưng phải refactor trước exposure.
- Hoàn thiện Profile Invitation contract: recipient consent/binding, token
  hash-at-rest, state/expiry/replay, duplicate/concurrency, audit, planned API,
  negative tests và dependency-ordered rollout.
- Đối chiếu toàn bộ RBAC design với 11 nhóm quyết định đã duyệt: audit ban đầu
  xác định nhóm 4 bị mở rộng sai nhãn từ active Owner sang usable Owner và nhóm
  6–9/11 thiếu ghi nhận một phần/toàn bộ. Đã sửa tài liệu để cả 11 nhóm đều
  `MATCH`, không thay đổi quyết định nghiệp vụ đã duyệt.
- Owner ủy quyền Technical Advisor chốt 14 quyết định: role compatibility và
  action ceilings, last-owner/deactivation target, Invitation identity/TTL/rate/
  retention, non-enumeration và platform-superuser Admin boundary.
- Ghi rõ reviewer role/workflow states và các domain downstream vẫn cần contract
  riêng; Invitation chưa được triển khai và verified email là dependency trước
  production enablement.

### Tenant access context and scoped membership services

- Thêm `backend/apps/workspace/access.py` với immutable verified Profile/
  Workspace contexts, Profile/Workspace scoped selectors và capability checks
  revalidate active account/membership/role trước khi cấp read, edit hoặc member
  management.
- Giữ nguyên enum: `WorkspaceMember.ADMIN` = Workspace Admin, `MEMBER` = Editor,
  `VIEWER` = read-only Viewer; legacy `OWNER` fail closed và không được cấp mới.
- Refactor `update_profile_membership()` để scope actor/Profile trước target,
  áp dụng Profile Admin least privilege, giữ last-active-owner locking và audit.
- Refactor `add_workspace_member()` dùng scoped ProfileMembership target, cho
  Profile Owner/Admin cấp `ADMIN/MEMBER/VIEWER`, Workspace Admin chỉ cấp
  `MEMBER/VIEWER` trong Workspace của mình, và xử lý duplicate/concurrency bằng
  stable domain conflict.
- Harden context trước direct construction, `dataclasses.replace()` role
  forgery và stale User/Profile/Workspace role; denied mutation không tạo audit.
- Không đổi model, schema, migration, SessionAuthentication hoặc route/API.

### Profile/Workspace schema foundation

- Thêm `Profile` và `ProfileMembership` với role
  `OWNER`/`ADMIN`/`MEMBER`, active state, partial unique constraint for active
  Profile/User membership (inactive history is retained), role
  check và tenant lookup indexes.
- Thêm transitional nullable `Workspace.profile`; bảo vệ Workspace owner bằng
  `PROTECT`; thêm validation cho Workspace owner và Workspace member phải có
  active membership trong cùng Profile.
- Thêm transactional services để tạo Profile cùng initial Owner và cập nhật
  membership an toàn: hỗ trợ nhiều Owner, giữ ít nhất một active Owner, chặn
  Admin thay đổi Owner và ghi AuditLog cho thay đổi membership.
- Khóa Profile/Workspace theo thứ tự thống nhất cho normal persistence, chặn
  concurrent re-parent/mapping và yêu cầu reassign transitional Workspace owner
  trước khi bỏ Profile manager status.
- Khóa cả save của Workspace legacy hiện hữu trước khi chấp nhận Profile null,
  ngăn stale instance ghi đè một mapping Profile vừa commit; bổ sung regression
  concurrency test cho tình huống này.
- Thêm audited direct-add service: Profile Owner/Admin chỉ có thể thêm User đã
  có active Profile membership vào Workspace.
- Thêm negative tests xác nhận quyền quản lý ở một Profile không cấp quyền thay
  đổi membership hoặc direct-add Workspace ở Profile khác.
- Thêm additive migration
  `workspace/0002_profile_workspace_foundation.py`, model/service/concurrency
  tests và populated-data migration test. Không sửa `0001_initial.py`.
- Read-only development inventory ghi nhận 0 business rows và 3 User rows;
  không tạo mapping giả định. `0002` mới chạy trên disposable PostgreSQL test
  databases và chưa apply development database.
- Không thay đổi User/session authentication hoặc API contract. Không triển
  khai Invitation, Workspace API/full RBAC, Project/Client/Finance migration,
  public-link flows, soft delete hay detailed Task/Review workflow.

### Authentication

- Thêm session authentication API tại `/api/auth/`: CSRF bootstrap, register, login, logout và current user.
- Dùng Django password validators và `create_user()`; password chỉ write-only, login lỗi trung tính và user inactive bị chặn.
- Bảo vệ register/login/logout bằng CSRF đúng với session flow; logout chỉ dùng `POST` và revoke current session.
- Chuyển DRF sang explicit `SessionAuthentication` và permission mặc định `IsAuthenticated`; public auth endpoints khai báo `AllowAny`.
- Thêm scoped throttle (`10/minute` login, `5/hour` register), giới hạn password input 128 ký tự và mặc định `DRF_NUM_PROXIES=0` để không tin forwarding header chưa được kiểm soát.
- Sửa User admin bằng cách đặt `created_at`/`updated_at` readonly.
- Không thay đổi User model, Profile, Workspace, schema hoặc migration.

### API security baseline

- Hoàn tất implementation deny-by-default cho DRF và thêm regression guard để
  mọi route trong API URL tree đều là DRF view.
- Giới hạn explicit `AllowAny` vào public allowlist đã review; view dùng
  permission mặc định từ chối anonymous và chấp nhận authenticated user.
- Gỡ legacy `/api/test/` và thay bằng `/api/health/` public, không auth,
  throttle hoặc database query; payload chỉ gồm `{"status":"ok"}` và response
  không được cache.
- Health hỗ trợ `GET`, `HEAD`, `OPTIONS`; mutation method và `TRACE` trả `405`.
- Thêm 10 API health/policy tests; chưa thay đổi Workspace, RBAC, business
  models, schema hoặc migrations.

### Security and dependencies

- Chuẩn hóa `backend/requirements.txt` sang UTF-8 để Git và công cụ dependency đọc ổn định.
- Nâng Django từ 6.1 lên 6.1.2 để nhận các bản vá bảo mật hiện hành.
- Nâng Django REST Framework từ 3.15.0 lên 3.18.3 để dùng phiên bản hỗ trợ Django 6.1 và có các bản vá bảo mật mới.
- Externalize Django secret, debug, allowed hosts, PostgreSQL, CSRF, HTTPS/cookie/HSTS và Django 6.1 mailer configuration qua environment variables có validation fail-fast.
- Thêm `.env.example` sạch, giữ `.env` ngoài Git và tài liệu hóa đầy đủ quy trình local setup.
- Chuyển PostgreSQL Compose credential sang biến bắt buộc và bind port vào `127.0.0.1` mặc định mà không thay named volume.

### Verification

- Fresh install và `pip check` thành công trong Python 3.12 container.
- Django system check, migration drift check, applied-migration check và legacy `/api/test/` smoke test từng thành công; endpoint này sau đó được thay bằng `/api/health/`.
- Tại thời điểm HT-OPS-P0-01, test discovery chạy được nhưng dự án chưa có automated tests; các task Authentication/API sau đó đã bổ sung test suite.
- Các case thiếu/sai environment fail rõ; production-like `check --deploy --fail-level WARNING` thành công khi cung cấp HTTPS, secure-cookie, HSTS, host và SMTP values phù hợp.
- Tại checkpoint `HT-SEC-P0-02`, chưa có model/migration thay đổi; PostgreSQL
  development khi đó có 8 domain migrations và 23 public tables trên named
  volume hiện hữu.
- `pip check`, Django system check, migration drift/applied checks và full suite 19/19 tests đều thành công trên PostgreSQL.
- Development server khởi động thành công; `GET /api/auth/csrf/` trả `200` cùng CSRF cookie/token.
- `pip check`, Django system check, migration drift/applied checks và full suite 29/29 tests (19 authentication + 10 API health/policy) đều thành công trên PostgreSQL ngày 2026-10-15.
- Development server smoke thành công: `GET /api/health/` trả `200` JSON/no-store, `POST` trả `405`, legacy `/api/test/` trả `404`, và `/api/auth/csrf/` vẫn trả `200` cùng CSRF cookie.
- Sau audit thiết kế ngày 2026-10-16, chạy lại `pip check`, Django system
  check, migration drift/applied checks và toàn bộ 29/29 regression tests trên
  PostgreSQL: PASS; test database tạm được Django xóa, không có schema hay dữ
  liệu ứng dụng bị thay đổi.
- Verification cuối của schema foundation ngày 2026-10-17: targeted
  `apps.workspace` 32/32 và full PostgreSQL suite 61/61 PASS; `pip check`,
  `manage.py check` và `makemigrations --check --dry-run` PASS. Read-only
  inventory trước/sau test không đổi, và không còn test database tạm.
- Verification tài liệu cho HT-RBAC-DESIGN-P0-01 ngày 2026-10-17: required
  section/status check, UTF-8/no-NUL, secret-pattern scan và
  `git diff --check` PASS (chỉ có cảnh báo LF→CRLF hiện hữu). Không rerun backend
  tests vì task không đổi code và local Python/venv hiện không khả dụng; không
  tạo container hoặc môi trường thay thế mới.
- Verification cuối HT-RBAC-P1-03 ngày 2026-10-18 trên PostgreSQL 16: local
  Python 3.12 virtualenv được đồng bộ đúng Django 6.1.2/DRF 3.18.3; `pip check`,
  compile, `manage.py check` và `makemigrations --check --dry-run` PASS; targeted
  Workspace 51/51 và full suite 80/80 PASS, gồm 19 Authentication và 10 API
  Foundation regressions. Test database tạm được Django hủy; development
  `workspace.0002` vẫn unapplied và development data không đổi.
- Verification cuối HT-API-P1-04 ngày 2026-10-18 trên PostgreSQL 16: targeted
  read API 21/21, Authentication/API Foundation 29/29 và full suite 101/101
  PASS; `pip check`, compile, Django system check và migration drift check PASS.
  Test database tạm được hủy, không còn `test_%` database; development migration
  và data không đổi.


# Version 0.0-foundation

Date:
2026-08-08


## Completed

### Project Structure

- Created project folder structure.
- Created backend folder.
- Created frontend folder.
- Created docker folder.
- Created database folder.


### Documentation

Created:

- ORIGINAL_REQUIREMENTS.md
- DEVELOPER_PROFILE.md
- ARCHITECTURE.md
- TECH_STACK_DECISION.md
- DATABASE_SCHEMA.md
- API_DOCUMENTATION.md
- REQUIREMENT_STATUS.md
- PROJECT_ROADMAP.md
- PROGRESS.md
- DECISION_LOG.md
- AI_INSTRUCTION.md


### Reference Documents

Imported original system documents:

- Discovery documents.
- Architecture diagrams.
- State diagrams.
- Security documents.
- Account documents.


### Version Control

Completed:

- Git initialization.
- First commit.
- GitHub repository connection.


## Current Status

Project foundation completed.


## Next Phase

Phase 1:
Development Environment Setup

# CHANGELOG

Lịch sử thay đổi của dự án HustlyTasker.

## Unreleased - 2026-10-17

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

- Thêm `documentation/RBAC_DESIGN.md` cho `HT-RBAC-DESIGN-P0-01`, trạng thái
  `DESIGN READY — PENDING OWNER APPROVAL`.
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
- Ghi rõ các đề xuất và quyết định owner còn thiếu. Task chỉ thay đổi tài liệu;
  không sửa model, migration, API/authentication, dữ liệu hoặc frontend.

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

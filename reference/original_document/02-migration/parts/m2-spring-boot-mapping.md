# M2 — Mapping chi tiết hiện tại → Spring Boot (Phase 2 §3)

> Nguồn sự thật: `docs/system-audit/00-discovery/` (parts 01, 03, 04, 05, 06, 07, 09, 10) + verify trực tiếp code tại worktree `claude/cranky-austin`, ngày 2026-08-02. Mọi kết luận kèm `file:line` thật.
>
> Quy mô phải port: **102 API route** (39 core + 63 review) + **~190 server action** trong 55 file + **67 model Prisma / 15 enum** + **7 Vercel cron** + **4 Inngest function** + **2 webhook**. Stack đích giả định: Spring Boot 3.x (Java 21), Spring Security 6, Spring Data JPA/Hibernate 6, Flyway, chạy container long-lived (không serverless).

---

## 1. BẢNG MAPPING CHI TIẾT

### 1.0 Nguyên tắc chung (rút từ đặc thù repo, không phải sách giáo khoa)

| Đặc thù hiện tại | Hệ quả mapping |
|---|---|
| API route KHÔNG qua middleware — guard từng handler là tuyến phòng thủ duy nhất (`src/middleware.ts:9-16`, ghi chú `src/app/api/inngest/route.ts:3`) | Spring làm NGƯỢC lại: filter chain là tuyến 1, method-security là tuyến 2. Nhưng **không được bỏ** pattern service-layer tự re-derive `workspaceId` từ row rồi tự guard (mục 1.2) — đó là defense-in-depth có chủ đích của review module, phải giữ dạng code imperative trong `@Service`, KHÔNG thay bằng `@PreAuthorize` đơn thuần. |
| Server action = POST endpoint ẩn của Next, FE gọi qua RPC compile-time | Mỗi action phải "hiện hình" thành REST endpoint có URL + DTO thật. Đây là phần việc lớn nhất (mục 3.1). |
| 2 hệ token guest độc lập (`/share/[token]` portal + `/r/[slug]` review) không session | 2 filter chain `permitAll` riêng, authz nằm trọn trong service (token/slug là credential) — giữ nguyên hợp đồng gate 404/410/410/401 (`src/lib/review/share-auth.ts:93-109`). |
| DB là Neon Postgres, schema thật ≠ `schema.prisma` (3 partial unique index + 5 CHECK + 1 trigger chỉ có trong `prisma/migrations/manual/*.sql`) | Baseline Flyway phải sinh từ **pg_dump live DB**, không từ schema.prisma (mục 1.5.9). |

### 1.1 Mapping theo domain: route + action → `@RestController` / `@Service` / `@Repository`

Quy ước: mỗi nhóm dưới = 1 controller + 1-2 service + repository theo aggregate. Server action nào chỉ đọc (`get*`) gộp vào controller GET cùng nhóm.

#### Domain `auth`

| Hiện tại (file:line) | Spring Boot |
|---|---|
| 10 route `/api/auth/**` (`parts/04-api-core.md` §1): signup, forgot-password, verify-otp, reset-password, verify-email, migrate-email, google/authorize+callback, role, logout | `AuthController` (`/api/auth/**` giữ nguyên path) → `AuthService`, `PasswordResetService`, `EmailMigrationService`, `GoogleOAuthService`. Repo: `UserRepository`, `EmailVerificationTokenRepository`, `PasswordResetOtpRepository`, `LoginAttemptRepository`. |
| `loginAction` (`src/actions/auth-actions.ts:168`) — rate-limit IP + lockout 5-fail/15' + padding chống timing + anti-enumeration + validate `?next=` | `POST /api/auth/login` trong `AuthController`. Lockout/padding/anti-enum là logic service, PHẢI port nguyên văn (không có sẵn trong Spring Security form-login — đừng dùng form-login, tự viết endpoint). |
| `signupAction` (`src/actions/signup-actions.ts:107`) — honeypot, BotID, HIBP ≥12 ký tự, tx tạo Profile+User+Workspace+Member+ProfileAccess | `POST /api/auth/signup` — 1 `@Transactional` tạo đủ 5 bảng như tx hiện tại. BotID là Vercel-only → thay thế (mục 3.11). |
| `password-reset-actions.ts` (3 hàm `:65,:178,:293`), `email-migration-actions.ts` (`:57,:171`) | Gộp vào 2 service trên; OTP hash SHA-256 + attempt-cap là logic thuần, port 1-1. |
| Impersonation (`src/actions/impersonation-actions.ts:9-107`, cookie swap `src/lib/auth.ts:76-141`) | `ImpersonationController` + `ImpersonationService` — port tay 5 lớp chặn + cặp cookie `session`/`admin_session` TTL 2h. **KHÔNG dùng `SwitchUserFilter`** của Spring (semantics khác: không có cookie standby, không TTL riêng, không audit tùy biến). |

#### Domain `tenant` (profile / workspace / member / invitation / cross-team)

| Hiện tại | Spring Boot |
|---|---|
| `profile-actions.ts` (13 hàm), `admin-profile-actions.ts` (2 hàm sống), `profile-member-actions.ts` (7 hàm), `upload-actions.ts` banner/logo (`:210,:257`) | `ProfileController` → `ProfileService`, `ProfileMemberService`. `transferProfileOwnershipAction` (`profile-member-actions.ts:306`) có CAS transaction chống double-transfer → giữ bằng `UPDATE … WHERE role='OWNER'` + check affected-rows trong `@Transactional`. |
| `workspace-actions.ts` (8 hàm), `member-actions.ts` (11 hàm, 1380 dòng — file authz phức tạp nhất ngoài review), `cross-team-actions.ts` (4 hàm), `toggle-treasurer.ts` | `WorkspaceController`, `WorkspaceMemberController` → `WorkspaceService`, `MembershipService`, `InvitationService`, `CrossTeamService`. `removeWorkspaceMember`/`leaveWorkspace` dùng `FOR UPDATE` (`member-actions.ts:1217,1291`) → `@Lock(PESSIMISTIC_WRITE)` hoặc native `SELECT … FOR UPDATE`. Trigger last-owner ở DB (`prisma/migrations/manual/last_owner_constraint.sql:21-69`) giữ nguyên — Spring chỉ cần bắt lỗi trigger raise. |
| `/api/profile/select` (`src/app/api/profile/select/route.ts:6`) — re-sign JWT nhúng `sessionProfileId` | `POST /api/profile/select` trong `SessionController` — re-issue cookie cùng thuật toán (mục 1.3). Workaround "sessionToken trong body" (`route.ts:15-24`) là hack cho Vercel edge-cache — **bỏ khi sang Spring** (không còn edge cache). |
| `/api/workspace/first` (`route.ts:12`) | GET nhỏ trong `WorkspaceController`. |

#### Domain `task` (vận hành lõi)

| Hiện tại | Spring Boot |
|---|---|
| `task-actions.ts` `updateTaskStatus` (`:17`) — FSM `validateTransition` + whitelist status + optimistic-lock `version` + email GĐ3/GĐ4 | `TaskStatusService` — port NGUYÊN VĂN `VALID_TASK_STATUSES` (13 giá trị) + `STATUS_TRANSITIONS` + `isTerminalStatus` (`src/lib/task-statuses.ts:18-39,156,199-218`) thành 1 class hằng số duy nhất + **snapshot-test `SALARY_PENDING_STATUSES`** (ràng buộc tiền lương — quy tắc cứng của repo). Optimistic lock: `UPDATE … WHERE id=? AND version=?` (giữ CAS kiểu Prisma `updateMany`, xem mục 1.5.7). |
| `admin-actions.ts` (createTask `:85`, updateTaskManager `:347`), `task-management-actions.ts` (deleteTask/updateTask/assignTask), `update-task-details.ts` (`:22` — strip field theo role, chặn sửa tiền khi payroll PAID), `bulk-task-actions.ts` (7 hàm, 864 dòng), `velox-batch-actions.ts` (`:102` cap 500 row/1 tx), `velox-helpers-actions.ts`, `claim-actions.ts` (5 hàm marketplace, CAS `version` tại `:128`), `tag-actions.ts` (6 hàm), `raw-footage-actions.ts` (5 hàm Velox v4/HookGraph) | `TaskController`, `TaskBulkController`, `MarketplaceController`, `TagController`, `RawFootageController` → `TaskService`, `TaskBulkService`, `MarketplaceService` (CAS claim), `VeloxBatchService`, `RawFootageService`. Field-stripping theo role (`update-task-details.ts`, `price-template-actions.ts:9`, `pricing-rule-actions.ts:152` — kỷ luật jobPriceUSD không tới non-admin) chuyển thành **tầng DTO projection theo role** — Java có lợi thế: 2 DTO class riêng (AdminTaskDto / MemberTaskDto) thay vì strip động. |
| `schedule-actions.ts` (8 hàm) + `availability-actions.ts` (5 hàm — có helper authz cục bộ `ensureWorkspaceAccess` `availability-actions.ts:22`) | `ScheduleController` → `ScheduleService`. Cơ hội dọn nợ: hợp nhất helper cục bộ vào 1 evaluator chung (mục 1.2) — đây là 1 trong 2 phiên bản check membership song song đã ghi nhận. |
| `analytics-actions.ts` (5 hàm rank lỗi/hiệu suất), `task-comment-actions.ts` (12 hàm chat staff) | `AnalyticsController`, `TaskCommentController` → service tương ứng. Comment poll delta `?since=` giữ nguyên (không SSE — mục 3.12). |

#### Domain `review` (module video — 63 route, authz service-layer)

| Hiện tại | Spring Boot |
|---|---|
| Uploads 4 route (`parts/05-api-review.md` §1) + task-upload (`§3`) — presigned R2 multipart + Idempotency-Key + poll 3s | `ReviewUploadController` → `UploadService` (port `src/lib/review/upload-service.ts`). Flow client-side GIỮ NGUYÊN 100%: browser PUT thẳng lên R2 bằng presigned URL, backend chỉ initiate/complete/abort/status (mục 1.9). `UploadSession.idempotencyKey @unique` = bảng chống double đã có sẵn — Spring bắt `DataIntegrityViolationException` trả kết quả cũ. |
| Folders/Tree/Items/Trash 14 route (§2) — materialized path, optimistic lock `expectedRowVersion`, folder-scope FR-03 | `ReviewFolderController` → `FolderService` (port `folders.ts` ~1600 dòng), `FolderScopeService` (port `folder-scope.ts:32-120` — scope editor theo materialized path). Prefix-scan `LIKE` trên index `varchar_pattern_ops` (`prisma/schema.prisma:1678`) → native query giữ nguyên. |
| Assets/Versions/Stack 9 route (§3), Comments/Reactions/Attachments 9 route (§4) | `ReviewAssetController`, `ReviewCommentController` → `VersionService`, `CommentService`. Funnel `resolveVersionCtx`/`resolveCommentCtx` (`comments.ts:106-129`) port thành private method trong service — mọi entry đi qua. |
| Status/task-sync 7 route (§5) — trục F7-F10, gate admin/assignee per-endpoint (`task-sync.ts:274,300-301,381`) | `ReviewStatusController` → `TaskSyncService`. Các gate `isAdmin` **workspace-scoped** (không phải global role — `access.ts:56-61`) map vào evaluator mục 1.2, gọi imperative trong service. |
| Shares staff 7 route (§6) + Guest `/api/r/**` 19 route (§7) | `ShareAdminController` (staff, session) và `GuestShareController` (không session) TÁCH ĐÔI như hiện tại — 2 hệ auth không bao giờ chéo (`parts/05` §8.5). Gate chain + unlock JWT + GuestSession cookie port nguyên trong `ShareGateService` (mục 1.3 có chi tiết cookie). |
| `withReviewRoute`/`withShareRoute` error boundary (`src/lib/review/route-auth.ts:21-67`) | 2 `@RestControllerAdvice` (1 cho staff — message VN, 1 cho guest — message EN, internal-auth-error → 500 chung không leak) map exception `ReviewAccessException→401/403`, `MuxException→502`. |

#### Domain `portal` (client portal `/share/[token]` — token là credential)

| Hiện tại | Spring Boot |
|---|---|
| `share-portal-actions.ts` 21 action (1878 dòng — bề mặt authz lớn nhất, `parts/07` §16): snapshot, approve/bulk-approve, request-changes, rating, comment feed, sub-client, notify-email OTP, intake v2 | `PortalController` (`/api/portal/**`, token trong body/header — **không đưa token vào URL param mới**; URL hiện tại `/share/[token]` là page, giữ cho FE) → `PortalService`, `PortalNotifyService`. Chokepoint `resolveShareToken` (`src/lib/share-link-auth.ts:73-281`: SHA-256 hash-at-rest, uniform-404, rate-limit 2 tầng, scope theo name-path) port thành `ShareTokenResolver` — **1 class duy nhất**, mọi method portal gọi đầu tiên, như hiện tại. |
| `share-document-actions.ts` (2 hàm `:461,:466`) + 2 route `/api/share/[token]/**` (download-zip, invoice pdf) | Vào cùng `PortalController`; zip streaming xem mục 3.3. |
| `share-link-actions.ts` (3 hàm admin quản llink) | `ShareLinkAdminController` (session, gate `canManageShareLinks`). |
| `approveDeliverableViaToken` (`share-portal-actions.ts:765`) — `updateMany` pin toàn bộ state+tenancy đã đọc chống race | Port thành `UPDATE … WHERE id=? AND status=? AND clientId=? AND workspaceId=? …` + check affected-rows — đúng kỹ thuật pin-row hiện tại, không dùng entity-managed update. |

#### Domain `finance` (tiền thật — USD/VND)

| Hiện tại | Spring Boot |
|---|---|
| `invoice-actions.ts` (9 hàm — tx claim UNBILLED→INVOICED atomic `:314`, voidInvoice advisory-lock `:581/:615`), 2 route `/api/invoices/**` | `InvoiceController` → `InvoiceService`. Advisory lock → native `SELECT pg_advisory_xact_lock(?)` trong cùng `@Transactional` (mục 1.5.8). PDF puppeteer xem mục 3.6. |
| `payment-actions.ts` (4 hàm), `payroll-actions.ts` (3 hàm — chặn khi `PayrollLock.isLocked`), `bonus-actions.ts` (3 hàm — advisory lock `:336`), `bonus-config-actions.ts` (2 hàm) | `PaymentController`, `PayrollController`, `BonusController` → service tương ứng. `getPayrollLockStatus` hiện KHÔNG guard (finding G-1, `bonus-actions.ts:38`) — khi port, mặc định filter chain đòi session sẽ **tự vá lỗi này** (ghi nhận thay đổi hành vi có chủ đích). |
| `pricing-rule-actions.ts` (5 hàm), `price-template-actions.ts` (3 hàm) | `PricingController` — strip `*USD*` đệ quy cho non-admin (`pricing-rule-actions.ts:152`) thay bằng DTO projection theo role. |
| `/api/exports/monthly-tasks-xlsx` (`route.ts:86`, ExcelJS `route.ts:2,172`) | `ExportController` → Apache POI (SXSSF streaming) — mục 3.7. |

#### Domain `crm`

| Hiện tại | Spring Boot |
|---|---|
| `crm-actions.ts` (12 hàm — cây client parent/sub, merge/unmerge, trash, advisory name-lock `crm-actions.ts:107`) | `ClientController` → `ClientService`. Partial unique `Client(profileId, COALESCE(parentId,-1), lower(btrim(name)))` (`prisma/migrations/manual/client_profile_name_unique.sql:28-30`) chỉ tồn tại ở DDL — Hibernate không biết → service PHẢI tiếp tục bắt unique-violation (23505) trả lỗi nghiệp vụ như code hiện bắt P2002. |
| `client-request-actions.ts` (5 hàm intake — guard `verifyProfileAdminAccess`) | `ClientRequestController` → `ClientRequestService`. |
| `Rating` (submit qua portal, đọc ở crm detail) | Nằm trong `PortalService` (ghi) + `ClientService` (đọc). ⚠️ Bẫy tên cột khi viết entity: `Rating.clientId` là **String trỏ User**, còn `Task.clientId` là **Int trỏ Client** (`prisma/schema.prisma:934-949`) — đặt tên field Java khác đi (`ratedByUserId`) kèm `@Column(name="clientId")`. |

#### Domain `notification`

| Hiện tại | Spring Boot |
|---|---|
| `notification-actions.ts` (11 hàm; 3 hàm `*Internal` KHÔNG guard đang lộ thành public action — finding phần B `notification-actions.ts:24,70,86`) | `NotificationController` (8 hàm self-service) + `NotificationService` **internal bean** (3 hàm Internal thành method Java thường — sang Spring lỗi "internal-mà-public" **biến mất về mặt cấu trúc**, vì method service không phải endpoint). |
| `push-actions.ts` (3 hàm VAPID), `src/lib/web-push.ts` | `PushController` + `WebPushService` — Java: thư viện `nl.martijndwars:web-push` hoặc gọi REST endpoint push service; prune endpoint chết 404/410 giữ nguyên. |
| Email 2 hệ template (legacy `src/lib/email-templates.ts` + registry `src/lib/notification-emails/`, ~25 loại — `parts/10` §5) | `EmailService` (Resend REST — mục 1.10) + `EmailTemplateRegistry`. **Quyết định cần chốt khi port**: hợp nhất 2 hệ (nguy cơ double-email đã ghi nhận `parts/10` §7.4) — port là thời điểm rẻ nhất để hợp nhất. |
| `notification-broadcast.ts:19,46` (Supabase Realtime REST fire-and-forget) | Giữ nguyên: `RestClient` POST `/realtime/v1/api/broadcast`, timeout 3s, fire-and-forget qua `@Async` — không cần đổi kiến trúc realtime (mục 3.9). |
| `tracking-actions.ts` (7 hàm analytics/presence; `trackEvent :58` không auth) | `TrackingController` — quyết định lại guard `trackEvent` khi port (hiện là vector spam ghi DB). |

Các model lẻ ngoài 8 domain (`WikiPage`, `StudyPlaceProgress`, `Contact`, `UserPresence`, `Session`/`Event` tracking): xếp `WikiPage`+`StudyPlaceProgress` vào `tenant` (nội dung theo workspace), `Contact`+`UserPresence` vào `notification` (hệ chat/presence user-level), `Session`/`Event` vào `notification.tracking` — ghi rõ trong cây mục 2.

### 1.2 Guard hiện tại → Spring Security filter chain + method security (map từng guard)

Kiến trúc đích: **3 `SecurityFilterChain`** + 1 evaluator bean trung tâm.

```java
// Chain 1 — public/token-là-credential: KHÔNG session
//   /api/auth/** (login/signup/reset), /api/portal/**, /api/r/**, /api/webhooks/**
// Chain 2 — máy-với-máy: /internal/jobs/** (thay cron HTTP nếu giữ), HMAC/secret filter riêng
// Chain 3 — mặc định: SessionCookieAuthFilter (bắt buộc authenticated)
```

| Guard hiện tại (file:line) | Bản chất | Map sang Spring |
|---|---|---|
| `getSession()` — decrypt JWT cookie, KHÔNG chạm DB (`src/lib/auth.ts:65-74`) | Đọc claims rẻ | `SessionCookieAuthFilter extends OncePerRequestFilter`: đọc cookie `session`, verify HS256 (nimbus), dựng `Authentication` với principal = record `SessionUser(id, username, role, profileId, sessionProfileId, sessionVersion, restricted, isImpersonating…)`. Không chạm DB tại filter — GIỮ nguyên triết lý "decrypt rẻ, DB-check dồn về sau" nếu muốn tương thích chi phí; hoặc gộp liveness vào filter (xem dòng dưới) vì Spring không có ranh giới Edge/Node. |
| `getCurrentUser()` — React `cache` per-request, DB re-check LOCKED + `sessionVersion` (`src/lib/auth-guard.ts:21-59`) | Liveness + hydrate user | `CurrentUserService` là **`@RequestScope` bean** (đúng vai trò React cache: 1 lần DB/request). Method `require()` throw nếu LOCKED / `jwt.sessionVersion < db.sessionVersion`. |
| `verifyActiveSession()` (`src/lib/security.ts:217-280`) | Liveness cho READ path | Gộp vào `CurrentUserService` (cùng 1 query). Lưu ý field `isAdmin` của nó = **chỉ isTreasurer** (`security.ts:275-279`) — khi port đặt tên lại `isTreasurer` cho khỏi lừa người sau. |
| `verifyWorkspaceAccess(wsId, role)` (`src/lib/security.ts:38-165`) — chuỗi: LOCKED+sessionVersion → workspace tồn tại → `ProfileAccess`: OWNER⇒OWNER, ADMIN+cutoff `grantedAt`⇒ADMIN, **CLIENT⇒fail-closed** → `WorkspaceMember` row (type-guard String role) → profile-fallback MEMBER → so weight | Guard BOLA/IDOR trung tâm (dùng bởi ~50+ action) | Bean `WorkspaceAccessEvaluator` (`@Component("wsAccess")`) port NGUYÊN chuỗi logic — đây là file quan trọng nhất của migration authz. Dùng ở 2 dạng: (a) `@PreAuthorize("@wsAccess.hasAtLeast(#workspaceId, 'ADMIN')")` trên controller/service method cho case đơn giản; (b) gọi imperative `wsAccess.require(workspaceId, Role.ADMIN)` đầu service method cho case cần context trả về (role thật, profileId) — đa số action hiện dùng giá trị trả về, nên dạng (b) là chính. Type-guard role String lạ → throw như `security.ts:127-131`. |
| `verifyProfileAdminAccess(wsId)` (`src/lib/security.ts:180-191`) — predicate admin/finance DUY NHẤT: workspaceRole ∈ {OWNER,ADMIN} ∨ profileRole ∈ {OWNER,ADMIN} | Gate admin + finance | `@PreAuthorize("@wsAccess.isProfileAdmin(#workspaceId)")` hoặc `wsAccess.requireProfileAdmin(wsId)`. GIỮ bất biến "cố ý không dùng isTreasurer" (chống leak cross-tenant R7/R8). |
| `verifyFinanceAccess` (`src/lib/security.ts:203-207`) — alias 100% của trên | Finance VIEW=WRITE | KHÔNG tạo bean riêng — alias method `requireFinance()` gọi `requireProfileAdmin()`, giữ 1 nguồn sự thật. |
| `isSessionLive(session)` (`src/lib/profile-permissions.ts:46-56`) | Liveness cho action chỉ có getSession | Biến mất — mọi request qua Chain 3 đã liveness-check trong `CurrentUserService`. Ghi nhận: các action từng "quên" isSessionLive sẽ tự được vá. |
| Predicates profile (`src/lib/profile-permissions.ts:71-105`): `canCreateWorkspace`/`canInviteMember`/`canManageShareLinks` = OWNER∨ADMIN; `canRemove/canChangeRole/canTransfer` = OWNER-only | RBAC profile | Method trên `ProfileAccessEvaluator` bean, dùng trong `@PreAuthorize("@profileAccess.canInviteMember(#profileId)")`. |
| `requireReviewAccess(opts)` (`src/lib/review/access.ts:32-70`) — chặn LOCKED/CLIENT; `workspaceId` ⇒ delegate vWA; `isAdmin` trả về **workspace-scoped** | Guard riêng review, gọi TRONG service với wsId re-derive từ row | `ReviewAccessService.require(workspaceId)` — **giữ imperative trong từng service method** (không annotation), vì workspaceId chỉ biết sau khi load row (ví dụ `folders.ts:199,368,429…` — 30+ điểm gọi). Nhánh `opts.admin` (global role) hiện **0 caller** (`parts/05` §8.3) — KHÔNG port. |
| `requireShare(slug, cookies)` (`src/lib/review/share-auth.ts:93`) — gate 404→410→410→401, anti-enum | Gate guest | `ShareGateService.resolve(slug, cookies)` trong Chain 1; exception → `@RestControllerAdvice` guest giữ đúng mã lỗi + message EN trùng nhau cho not_found/revoked. |
| `resolveShareToken` (`src/lib/share-link-auth.ts:73-281`) — uniform-null → 404 | Chokepoint portal | `ShareTokenResolver.resolve(token)` trả `Optional<Scope>` — mọi nhánh fail trả empty → controller 404 đồng nhất. |
| Helper cục bộ `ensureWorkspaceAccess` (`src/actions/availability-actions.ts:22`) | Bản check membership thứ 2 song song | HỢP NHẤT vào `WorkspaceAccessEvaluator` (thêm mode `membershipOnly`) — xóa nợ trùng lặp khi port. |
| `CRON_SECRET` so sánh (6/7 route so `!==` thường, chỉ auth-cleanup `timingSafeEqual` — `parts/04` §2) | Guard cron HTTP | Biến mất nếu chuyển `@Scheduled` (mục 1.6). Nếu giữ endpoint HTTP cho electron: 1 filter duy nhất dùng `MessageDigest.isEqual` — hết luôn sự thiếu nhất quán. |

### 1.3 Session JWT jose HS256 cookie httpOnly → Spring Security JWT (nimbus), GIỮ NGUYÊN cookie contract

Yêu cầu bắt buộc cho thời kỳ chuyển tiếp (Next FE + Spring BE chạy song song): **cookie do bên nào phát, bên kia phải verify được**.

| Thuộc tính hiện tại (bằng chứng) | Spring giữ nguyên |
|---|---|
| Thuật toán HS256, lib `jose`, key `env.JWT_SECRET` (`src/lib/jwt.ts:2-4,16-21`) | Nimbus `MACSigner/MACVerifier` cùng `JWT_SECRET` (bytes UTF-8 y hệt). Viết **test vector chéo**: token do Next phát → Spring verify OK và ngược lại, TRƯỚC khi cutover. |
| Payload: `{ user: { id, username, role, profileId, sessionVersion, email, displayName, restricted, requiresEmailMigration [, sessionProfileId] }, expires }` (`src/actions/auth-actions.ts:344-357`) | Claim shape y hệt (object lồng `user` — không "chuẩn hóa" thành flat claims, sẽ vỡ tương thích). |
| Cookie `session`: httpOnly, `SameSite=Lax`, `Secure` khi prod, path `/`, TTL 30 ngày (`src/lib/auth.ts:6-7,23-29`) | `ResponseCookie.from("session", jwt).httpOnly(true).sameSite("Lax").secure(prod).path("/").maxAge(Duration.ofDays(30))`. |
| Thu hồi: so `sessionVersion` claim với DB tại DAL (`src/lib/auth-guard.ts:43-47` v.v.) | `CurrentUserService` (mục 1.2). |
| Rolling refresh khi còn <50% hạn, skip phiên impersonation (`src/middleware.ts:145-163`) | `OncePerRequestFilter` sau auth filter: nếu `exp - now < 15 ngày` và `!isImpersonating` → re-issue cookie. |
| Cookie phụ: `admin_session` (impersonation standby — `src/lib/auth.ts:101-107`), guest `rv_unlock_{slug}` (JWT HS256 ký `REVIEW_COOKIE_SECRET`, fingerprint passwordHash — `share-auth.ts:111-144`), `rv_guest_{slug}` (random 32B, DB giữ sha256 — `share-auth.ts:154-187`), `rv_t_{slug}` debounce | Port đủ 4, cùng tên + cùng thuật toán ký/hash — guest đang mở tab `/r/...` không bị văng khi cutover backend. |
| CHỐT: **KHÔNG dùng** `spring-security-oauth2-resource-server` mặc định (Bearer header) — session ở đây nằm trong cookie, không Authorization header | Tự viết filter như mục 1.2 (khoảng 100 dòng, kiểm soát được 100% contract). |

### 1.4 zod → Bean Validation

| Hiện tại | Spring |
|---|---|
| `zod ^3.23.8` (`package.json:116`) dùng rải rác: validate UUID taskId (`raw-footage-actions.ts:117`), input bulk, share-slug regex `^[A-Za-z0-9_-]{8,24}$` (`share-auth.ts:40`) | DTO + Jakarta Validation: `@NotNull`, `@Size`, `@Pattern(regexp="^[A-Za-z0-9_-]{8,24}$")`, `@UUID` (hibernate-validator), bật `@Valid` ở controller. |
| Schema có cấu trúc phức tạp: `velox-4.0` (URL validate chống `javascript:` — `raw-footage-actions.ts:215`) và `hookgraph-1` (cap 500 blocks / 2000 edges — `:351`) — JSON lồng, điều kiện chéo | Bean Validation KHÔNG diễn tả nổi — port thành **programmatic validator class** (`VeloxMapValidator`, `HookGraphValidator`) gọi trong service, y như vai trò zod `safeParse` hiện tại. Đừng cố nhét vào annotation. |
| Sanitize URI scheme chống stored-XSS `javascript:` (`update-task-details.ts` HT-031, `raw-footage-actions`) | 1 util chung `SafeUrl.parse()` (whitelist http/https) — port nguyên logic, đây là validation nghiệp vụ chứ không phải khung. |
| Phần lớn action hiện validate tay (if/throw) chứ không zod | Chuyển dần sang DTO annotation khi viết controller — nhưng giữ nguyên **thông điệp lỗi tiếng Việt** trả cho UI nội bộ. |

### 1.5 Prisma 67 model → JPA/Hibernate — CÁC BẪY THẬT (không lý thuyết)

| # | Bẫy (bằng chứng) | Cách xử lý JPA |
|---|---|---|
| 1 | **`Task.status` là String TỰ DO** default `"Đang thực hiện"` (`prisma/schema.prisma:336`), và ~16 model khác cũng String tự do (`Profile.status:25`, `Workspace.status:69`, `WorkspaceMember.role:114`, `Payroll.status:318`, `Client.status:546`, `MonthlyRank.rank:1061`, `Task.clientReview:385`, `ReviewActivity.type:1991`… — `parts/03` §3.1) | **KHÔNG map thành Java enum** — DB đang chứa giá trị tiếng Việt tự do và payroll đếm tiền theo chuỗi này. Map `String` + tập trung hằng số vào `TaskStatuses` class (mirror `src/lib/task-statuses.ts`) + type-guard runtime cho `WorkspaceMember.role` (mirror `src/lib/workspace-roles.ts:34-36`: role lạ → throw SECURITY_VIOLATION). Snapshot-test bộ `SALARY_PENDING_STATUSES`. |
| 2 | **Partial/expression unique index chỉ có trong SQL tay**: `ReviewFolder(parentId, lower(name)) WHERE deletedAt IS NULL…` + `ReviewAsset(folderId, lower(name)) WHERE deletedAt IS NULL` (`prisma/migrations/manual/p0_add_review_module.sql:13-16`), `Client(profileId, COALESCE(parentId,-1), lower(btrim(name))) WHERE status='ACTIVE'` (`client_profile_name_unique.sql:28-30`); + 5 CHECK constraint (`p0_add_review_module.sql:19-39`); + trigger last-owner (`last_owner_constraint.sql:21-69`) | Hibernate không diễn tả được → **DDL thủ công phải sống trong Flyway** (V1 baseline từ pg_dump). Tắt tuyệt đối `hibernate.hbm2ddl.auto` (chỉ `validate` — và validate cũng sẽ không thấy các index này, chấp nhận). Service bắt `DataIntegrityViolationException`/SQLState 23505 trả lỗi nghiệp vụ — đây chính là bài học "2 index ẩn từng gây 500 khi trùng tên folder" của repo. |
| 3 | **Kiểu id không đồng nhất**: `AuditLog.id` **BigInt autoincrement** (`prisma/schema.prisma:861`), `Client.id`/`Project.id` **Int autoincrement** (`:495,677`), còn lại cuid/uuid String | `AuditLog.id` → `Long` + `@GeneratedValue(IDENTITY)`; Client/Project → `Integer` + IDENTITY; model String-id → `@Id String` với **generator cuid phía app** (port cuid — id đang lưu là cuid, các scalar-FK cross-module so sánh chuỗi; row MỚI có thể dùng UUIDv7 string vì id là opaque, nhưng phải nhất quán 1 lựa chọn). ⚠️ Đừng để Hibernate tự sinh UUID kiểu `binary(16)`. |
| 4 | **15 model review dùng cross-module FK dạng scalar String CHỦ ĐÍCH, không constraint** (`prisma/schema.prisma:1607-1613`); tương tự `Payment` (`:799-804`), `PriceTemplate`, `TaskCommentReadState`, `ReviewActivity` (không FK để log sống lâu hơn row bị purge `:1988`) | Map **cột String thường, KHÔNG `@ManyToOne`** — nếu vẽ quan hệ JPA, schema-validate/DDL sẽ đòi FK constraint = đổi hành vi delete (điều P0 cố tránh). Hệ quả: không navigate quan hệ, viết join tay trong repository (JPQL join on hoặc native) — đúng như service TS hiện làm. |
| 5 | **Soft-delete 3 pattern song song** (`parts/03` §3.3): (a) `status+deletedAt+hardDeleteAfter` (Profile/Workspace/Client — cron hard-delete 30 ngày); (b) trash-batch `deletedAt+deleteBatchId+orphanedFromPurge` (ReviewFolder/Asset/Version); (c) `isDeleted` Boolean (TaskComment), `revokedAt` (2 loại ShareLink) | **KHÔNG dùng `@SQLDelete`/`@Where`/`@SoftDelete`** của Hibernate — filter toàn cục sẽ phá trash-listing, restore, cron hard-delete và purge (những luồng CẦN thấy row đã xóa). Giữ điều kiện `deletedAt IS NULL` **tường minh trong từng query** của repository, như service TS hiện viết. |
| 6 | **Json cột nhiều và nghiệp vụ nặng**: `TaskRawFootage.veloxMap/manualGraph`, `ReviewComment.annotation`, `AuditLog.beforeData/afterData`, `Invoice` snapshot, `PricingRule.config`, `DailyAvailability.schedule` | `jsonb` qua hypersistence-utils `@Type(JsonType)` → map vào record/JsonNode. Validate bằng validator mục 1.4, không tin cấu trúc. |
| 7 | **Optimistic lock kiểu CAS-từ-client**, không phải `@Version` server-side: `Task.version` (`updateTaskStatus` nhận `currentVersion?`), `ReviewFolder/ReviewAsset/ShareLink.rowVersion` (PATCH nhận `expectedRowVersion` — `folders.ts:654`), claim marketplace CAS (`claim-actions.ts:128`) | Dùng `UPDATE … SET version=version+1 WHERE id=? AND version=?` (native/JPQL) + check affected-rows — **không dùng `@Version`** cho các cột này (semantics `@Version` là so với giá trị lúc entity được đọc trong cùng persistence context, còn contract hiện tại là client gửi version lên). Enum vs hành vi phải giữ nguyên vì FE đang gửi `expectedRowVersion`. |
| 8 | **Advisory lock + FOR UPDATE**: `pg_advisory_xact_lock` tại `bonus-actions.ts:336`, `crm-actions.ts:107`, `invoice-actions.ts:615`, `share-portal-actions.ts:1460`; `FOR UPDATE` tại `member-actions.ts:1217,1291` | Native query `SELECT pg_advisory_xact_lock(:key)` NGAY SAU khi mở `@Transactional` (lock gắn tx, tự nhả) — chú ý key hiện tính từ profileId/tên, port đúng công thức hash. `FOR UPDATE` → `@Lock(PESSIMISTIC_WRITE)` hoặc native. |
| 9 | **`prisma db push` mỗi build + migrations folder đã DRIFT từ 2026-05-07** (`package.json:10`, `parts/03` §4.1) — schema.prisma không phải nguồn sự thật đầy đủ | Baseline Flyway = `pg_dump --schema-only` từ **Neon prod** (không phải từ schema.prisma, không phải từ folder migrations cũ). Từ đó về sau mọi DDL đi qua Flyway — đây là điểm migration CHỮA được nợ "db push không history". |
| 10 | **Postgres enum THẬT trong DB** cho 15 enum Prisma (Prisma tạo PG enum type); riêng `ClientTier` có giá trị lowercase `standard` lệch case (`prisma/schema.prisma:890`) | Hibernate 6: `@JdbcType(PostgreSQLEnumJdbcType.class)` + Java enum trùng TÊN Y HỆT từng giá trị — Java cho phép hằng enum thường `standard` (không đẹp nhưng hợp lệ); tuyệt đối không "sửa case cho đẹp" (DB đang chứa `standard`). |
| 11 | **Decimal tiền**: `jobPriceUSD/wageVND/profitVND/exchangeRate`, `depositBalance`, `bonusPercent` | `BigDecimal` + `@Column(precision, scale)` khớp DDL thật (đọc từ pg_dump). Mọi phép tính tiền server-side như hiện tại (`calculateInvoicePreview` `invoice-actions.ts:277` tính từ DB, không tin client). |
| 12 | **Index biểu thức** `ReviewFolder.path varchar_pattern_ops` (`prisma/schema.prisma:1678`) phục vụ prefix `LIKE 'path/%'` | Giữ trong baseline DDL; query prefix viết native để chắc chắn dùng index. |

### 1.6 7 Vercel cron → `@Scheduled` (không cần Quartz)

7 job đơn giản, không cần cluster-cron phức tạp → **`@Scheduled(cron, zone="UTC")` + ShedLock (JDBC provider trên chính Postgres)** nếu chạy ≥2 replica (Vercel cron hiện bảo đảm 1 invocation; Spring nhiều instance thì không — ShedLock thay thế bảo đảm đó). Quartz là oversize cho 7 job không có job-data động.

| Cron (`vercel.json:22-51`) | Lịch UTC | Spring method | Ghi chú port |
|---|---|---|---|
| `/api/cron/send-digest` | `0 * * * *` | `DigestJobs.hourly()` — `@Scheduled(cron="0 0 * * * *")`; nhánh DAILY khi `hour==1` giữ nguyên logic (`send-digest/route.ts:29-45`) | Gọi `EmailService.sendDigest(mode)` |
| `/api/cron/check-deadline` | `0 * * * *` | `DeadlineJobs.check()` | Cron DUY NHẤT ghi đè nghiệp vụ: `task.status='Quá hạn'` với whitelist `OVERDUE_ELIGIBLE_STATUSES` (`check-deadline/route.ts:8,156-159`) — port whitelist NGUYÊN VĂN, nếu thiếu sẽ đè 6 status video mới (đụng payroll). |
| `/api/cron/cleanup-notifications` | `0 2 * * *` | `NotificationJobs.cleanup()` | deleteMany 30d/90d |
| `/api/cron/hard-delete-workspaces` | `0 3 * * *` | `TenantJobs.hardDeleteWorkspaces()` | Audit TRƯỚC rồi delete cascade (`hard-delete-workspaces/route.ts:67-76`) — giữ thứ tự |
| `/api/cron/hard-delete-profiles` | `30 3 * * *` | `TenantJobs.hardDeleteProfiles()` | như trên |
| `/api/cron/auth-cleanup` | `0 4 * * *` | `AuthJobs.cleanup()` | token/OTP/LoginAttempt hết hạn |
| `/api/cron/review-janitor` | `0 20 * * *` | `ReviewJanitorJobs.run()` — gọi THẲNG janitor (mục 1.7), **bỏ bước cron→HTTP→Inngest event** (`review-janitor/route.ts:31`) | 1 hop biến mất |

Hệ quả: guard `CRON_SECRET` + sự thiếu nhất quán timingSafeEqual (`parts/10` §7.1) biến mất. **Ngoại lệ**: `electron/main/cron-scheduler.ts:19-26` đang gọi 6/7 endpoint HTTP local — nếu bản desktop còn sống sau migration thì giữ thêm `POST /internal/jobs/{name}` trong Chain 2 (1 filter `MessageDigest.isEqual`), còn không thì bỏ hẳn HTTP cron.

### 1.7 4 Inngest function → đề xuất cụ thể: **DB-backed job queue (JobRunr chạy trên Postgres)**, KHÔNG Redis queue

Vì sao chọn DB-backed cho quy mô này (không generic):

1. Repo ĐÃ tự xây nửa hệ queue trên Postgres: ledger idempotent `WebhookEvent` (id = event id Mux, `processedAt` null = chưa xử lý — `prisma/schema.prisma:2040`), janitor re-enqueue event chưa consume 1h-7d (`src/lib/review/inngest.ts:606-627`), reconcile hỏi thẳng Mux khi kẹt (`:463-516`), persist-then-claim `processedAt` (`:323-329`). Chuyển sang JobRunr (storage Postgres, retry, dashboard) là **hợp thức hóa pattern có sẵn**, không thêm hạ tầng mới.
2. Redis hiện chỉ dùng cho rate-limit auth (Upstash) — dựng Redis queue là thêm 1 hệ stateful mới cho đúng 4 function, oversize. Kafka/RabbitMQ càng không.
3. Khối lượng: 4 function, retry 4 (2 cho janitor), tần suất theo upload video của 1 agency — Postgres dư sức.

| Inngest function (`src/lib/review/inngest.ts`) | Spring |
|---|---|
| `reviewMuxWebhook` (`:259`, retries 4) — đọc ledger, `applyMuxReady`/`applyMuxErrored`, đánh dấu `processedAt` cuối | `MuxWebhookJob` — enqueue từ webhook controller (mục 1.8) với jobId = Mux event id (JobRunr dedup theo id = giữ idempotency 2 tầng). Logic `applyMuxReady` (`:64-206` — flip nguyên tử PROCESSING→READY, đổi stack-head, auto-flip task A2, thu hồi share khi `clientReview='AWAITING'` `:150-154`) port nguyên vào `MuxIngestService`. |
| `reviewProcessUpload` (`:341`, retries 4) — sniff magic-bytes từ R2, **retag colorspace BT.709 bằng ffmpeg** (`:417-419`, `src/lib/review/color-retag.ts:30`), tạo Mux asset | `ProcessUploadJob` — chạy trên **executor riêng cho job nặng** (ffmpeg stream có thể chạy nhiều phút; lý do `maxDuration=800` của `/api/inngest` — `src/app/api/inngest/route.ts:15`). Container phải có ffmpeg binary (hiện dùng `@ffmpeg-installer/ffmpeg` npm — sang Java cài ffmpeg vào image, gọi qua `ProcessBuilder`). JVM long-lived xóa luôn giới hạn 800s serverless. |
| `reviewJanitor` (`:526`, retries 2) — 5 sweep độc lập, batch cap 100/25 | `@Scheduled` gọi thẳng (mục 1.6), mỗi sweep 1 method `@Transactional` riêng để giữ tính "1 sweep fail không kéo sweep khác" (hiện là 5 step Inngest). |
| `reviewShareDecision` (`:657`, retries 4) — backup idempotent side-effects sau decision, guard "latest wins" (`:663-683`) | `ShareDecisionJob` — enqueue từ `submitGuestDecision` (thay `inngest.send` tại `share-decision.ts:375`). Guard latest-wins port nguyên. |

Bảng event → chỗ enqueue: `review/mux.event.received` → webhook controller; `review/upload.completed` → `UploadService.completeUpload` (thay `upload-service.ts:439`); `review/decision.recorded` → `ShareDecisionService`; `review/janitor.requested` → biến mất (gọi trực tiếp).

### 1.8 Webhook Mux HMAC → filter/controller

| Hiện tại (`src/app/api/webhooks/mux/route.ts`) | Spring |
|---|---|
| Đọc RAW body trước khi parse (`:51`); header `Mux-Signature: t=<unix>,v1=<hex>`; HMAC-SHA256 trên `"{t}.{rawBody}"` với `MUX_WEBHOOK_SECRET`, tolerance ±5', `timingSafeEqual`, fail-closed 401 (`:23-48,54-58`) | `MuxWebhookController` trong Chain 1 (`permitAll`, tự verify): nhận `@RequestBody byte[] raw` (KHÔNG để Jackson parse trước — chữ ký tính trên raw bytes), verify bằng `javax.crypto.Mac` + `MessageDigest.isEqual`, sai → 401 để Mux retry. |
| Ledger idempotent: insert `WebhookEvent` id = event id, bắt P2002 duplicate → ack (`:74-80`) | Insert JPA, bắt `DataIntegrityViolationException` → 200 ack không re-enqueue. |
| Fan-out Inngest, send-fail chỉ log (ledger là source of truth) (`:87-93`) | Enqueue `MuxWebhookJob` (mục 1.7); enqueue-fail chỉ log — janitor sweep (d) re-enqueue từ ledger, giữ nguyên độ bền. |
| `/api/webhooks/calendar` — STUB không xác thực (`calendar/route.ts:8-40`) | **KHÔNG PORT** — cơ hội khai tử endpoint mở (finding `parts/04` §11.1). |

### 1.9 S3 multipart R2 → `aws-sdk-java` v2 presigned — GIỮ NGUYÊN flow client-side

| Hiện tại (`src/lib/review/r2.ts:1-39`) | Spring |
|---|---|
| `S3Client` region `auto`, endpoint `https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com`, bucket `hustly-review`; browser PUT thẳng presigned part URL | `software.amazon.awssdk:s3` v2: `S3Client`/`S3Presigner` với `endpointOverride(URI)` + `Region.of("auto")` + path-style tùy R2. Flow không đổi 1 byte phía browser: `CreateMultipartUpload` → presign N `UploadPart` → client PUT → `CompleteMultipartUpload` / `AbortMultipartUpload`. |
| Presigned GET cho download/view (TTL 15', 6h theo ngữ cảnh — `share-auth.ts:371-378`) | `S3Presigner.presignGetObject` cùng TTL — công thức `min(6h, hạn share, floor 60s)` port nguyên. |
| Upload ảnh public: Vercel Blob mặc định, Supabase Storage dự phòng (`src/lib/storage.ts:23-31`) | Rời Vercel thì Blob không còn — seam driver đã có sẵn trong code: port interface `ImageStorage` với impl Supabase Storage (REST) hoặc gộp luôn về R2 (1 hệ storage thay 3 — quyết định kiến trúc nên chốt lúc port). |

### 1.10 Resend email → giữ REST call

| Hiện tại | Spring |
|---|---|
| SDK `resend` nhưng bản chất chỉ 1 hàm `sendEmail({to, subject, html, headers})` (`src/lib/email.ts:26`), from `EMAIL_SENDER_NAME <RESEND_FROM_EMAIL>`, thiếu key → warn không gửi (`:27-30`), hỗ trợ List-Unsubscribe RFC 8058 (`:16-18`) | `ResendClient` dùng Spring `RestClient` POST `https://api.resend.com/emails` — không cần SDK. Giữ nguyên: fallback warn khi thiếu key, header List-Unsubscribe/List-Unsubscribe-Post per-recipient (guest notices — `guest-notify.ts`). Template HTML: 2 hệ hiện tại là hàm TS trả string → port thành template engine tùy chọn (Thymeleaf string template hoặc text-block Java) — giữ nội dung VN/EN y hệt. |

### 1.11 Rate-limit Upstash → bucket4j/Redis + GIỮ limiter Postgres

Hiện có **2 hệ rate-limit chủ đích khác nhau** — không gộp làm một:

| Hệ | Hiện tại | Spring |
|---|---|---|
| Auth burst (signup/login/OTP) — **fail-CLOSED prod khi thiếu env** (`src/lib/rate-limit-upstash.ts:1-30`) | Upstash Redis (`@upstash/ratelimit`) | **bucket4j + Lettuce** trỏ chính Upstash Redis hiện có (đỡ đổi hạ tầng), giữ semantics fail-closed khi Redis unavailable ở prod. |
| Guest share (`/api/r/**`, portal download) — fixed-window trên Postgres `RateLimitBucket`, 1 upsert atomic; fail-open cho read, `failClosed:true` cho unlock; IP lấy `x-real-ip`→`x-vercel-forwarded-for`→XFF-phải (fix G1) (`src/lib/review/rate-limit-db.ts:17,44-45,59-70`) | `limitDb` tự viết | Port nguyên thành `DbRateLimiter` (JdbcTemplate upsert `ON CONFLICT`) — nó là 1 bảng + 1 câu SQL, KHÔNG thay bằng Redis (giữ tính chất "limiter sập thì unlock fail-closed" độc lập Redis). ⚠️ Chuỗi header IP phải viết lại theo proxy mới (hết `x-vercel-forwarded-for`) — quy tắc "lấy phần tử PHẢI nhất XFF từ proxy tin cậy" giữ nguyên. |

---

## 2. CẤU TRÚC PROJECT SPRING BOOT (package-by-feature theo 8 domain thật)

```
src/main/java/xyz/hustlytasker/
├── HustlyTaskerApplication.java
│
├── shared/                              # KHÔNG chứa business rule — chỉ hạ tầng dùng chung
│   ├── security/                        #   SessionCookieAuthFilter, SessionUser, RollingRefreshFilter,
│   │                                    #   WorkspaceAccessEvaluator, ProfileAccessEvaluator, CurrentUserService(@RequestScope)
│   ├── persistence/                     #   JsonType config, CuidGenerator, AdvisoryLock helper, Flyway baseline
│   ├── ratelimit/                       #   Bucket4jConfig (Redis/Upstash), DbRateLimiter (RateLimitBucket)
│   ├── audit/                           #   AuditLogService (append-only, id Long/BigInt, redact keys)
│   ├── email/                           #   ResendClient, EmailTemplateRegistry (hợp nhất 2 hệ template)
│   ├── storage/                         #   R2Client + R2Presigner, ImageStorage (Supabase/R2 impl)
│   ├── media/                           #   MuxClient (REST), MuxJwtSigner (RS256 nimbus), FfmpegColorRetag
│   ├── jobs/                            #   JobRunrConfig (Postgres storage), ShedLockConfig, heavy-job executor
│   ├── realtime/                        #   SupabaseBroadcastClient (fire-and-forget REST, timeout 3s)
│   └── web/                             #   2 RestControllerAdvice (staff VN / guest EN), request-id, uniform-404 helper
│
├── auth/                                # domain 1 — 10 route auth + login/signup/reset/migration + impersonation
│   ├── api/          AuthController, PasswordResetController, GoogleOAuthController, ImpersonationController
│   ├── service/      AuthService, SignupService, PasswordResetService, EmailMigrationService, ImpersonationService
│   └── repo/         UserRepository, EmailVerificationTokenRepository, PasswordResetOtpRepository, LoginAttemptRepository
│
├── tenant/                              # domain 2 — Profile/Workspace/Member/Invitation/CrossTeam (+ Wiki, StudyPlace)
│   ├── api/          ProfileController, WorkspaceController, WorkspaceMemberController, CrossTeamController,
│   │                 SessionController(/api/profile/select, /api/workspace/first), WikiController, StudyPlaceController
│   ├── service/      ProfileService, ProfileMemberService, WorkspaceService, MembershipService, InvitationService,
│   │                 CrossTeamService, WikiService, StudyPlaceService
│   └── repo/         ProfileRepository, ProfileAccessRepository, WorkspaceRepository, WorkspaceMemberRepository,
│                     WorkspaceInvitationRepository, WikiPageRepository, StudyPlaceProgressRepository
│
├── task/                                # domain 3 — trục xương sống Task.status
│   ├── api/          TaskController, TaskBulkController, MarketplaceController, TagController,
│   │                 RawFootageController, ScheduleController, AnalyticsController, TaskCommentController
│   ├── service/      TaskService, TaskStatusService (FSM + TaskStatuses hằng số), TaskBulkService,
│   │                 MarketplaceService (CAS claim), VeloxBatchService, RawFootageService,
│   │                 ScheduleService, AnalyticsService, TaskCommentService
│   ├── validation/   VeloxMapValidator, HookGraphValidator, SafeUrl
│   └── repo/         TaskRepository, TaskRawFootageRepository, TagCategoryRepository, TaskTagRepository,
│                     ScheduleRuleRepository, ScheduleExceptionRepository, DailyAvailabilityRepository,
│                     ErrorLogRepository, ErrorDictionaryRepository, TaskCommentRepository, TaskCommentReadStateRepository
│
├── review/                              # domain 4 — module video (63 route, service-layer authz)
│   ├── api/          ReviewUploadController, ReviewFolderController, ReviewAssetController,
│   │                 ReviewCommentController, ReviewStatusController, ShareAdminController, MuxWebhookController
│   ├── service/      ReviewAccessService, FolderService, FolderScopeService, UploadService, VersionService,
│   │                 CommentService, StatusService, TaskSyncService, ShareService, PurgeService, DownloadZipService
│   ├── jobs/         MuxWebhookJob, ProcessUploadJob, ShareDecisionJob, ReviewJanitorJobs(@Scheduled 5 sweeps)
│   └── repo/         ReviewFolderRepository, ReviewAssetRepository, ReviewVersionRepository, ReviewCommentRepository,
│                     ShareLinkRepository, ShareLinkItemRepository, GuestSessionRepository, GuestSubscriptionRepository,
│                     GuestEmailVerificationRepository, UploadSessionRepository, WebhookEventRepository, ReviewActivityRepository
│
├── portal/                              # domain 5 — 2 bề mặt guest, token là credential, KHÔNG session
│   ├── client/       # /share/[token] — ClientShareLink
│   │   ├── api/      PortalController, PortalDownloadController(zip/pdf), PortalNotifyController
│   │   └── service/  ShareTokenResolver (chokepoint), PortalService, PortalDocumentService, PortalNotifyService
│   ├── guest/        # /r/[slug] — ShareLink review
│   │   ├── api/      GuestShareController, GuestCommentController, GuestDecisionController, GuestSubscribeController
│   │   └── service/  ShareGateService (404→410→410→401), GuestIdentityService, GuestDecisionService, GuestSubscribeService
│   └── repo/         ClientShareLinkRepository (+ dùng lại repo của review/crm qua service)
│
├── finance/                             # domain 6 — tiền thật, mọi guard = requireProfileAdmin
│   ├── api/          InvoiceController, PaymentController, PayrollController, BonusController,
│   │                 PricingController, ExportController(xlsx)
│   ├── service/      InvoiceService, InvoicePdfService, PaymentService, PayrollService, BonusService,
│   │                 PricingRuleService, PriceTemplateService, MonthlyTasksExportService
│   └── repo/         InvoiceRepository, InvoiceItemRepository, PaymentRepository, PayrollRepository,
│                     PayrollLockRepository, MonthlyBonusRepository, MonthlyRankRepository, BonusConfigRepository,
│                     PricingRuleRepository, PriceTemplateRepository, BillingProfileRepository, PerformanceMetricRepository
│
├── crm/                                 # domain 7 — cây Client, intake, rating
│   ├── api/          ClientController, ClientRequestController, ShareLinkAdminController
│   ├── service/      ClientService (merge/unmerge/trash + advisory name-lock), ClientRequestService,
│   │                 ClientShareLinkAdminService, RatingService
│   └── repo/         ClientRepository, ProjectRepository, ClientTaskRequestRepository, RatingRepository
│
└── notification/                        # domain 8 — notify/push/email-digest/presence/tracking/contact
    ├── api/          NotificationController, PushController, TrackingController, ContactController,
    │                 UnsubscribeController (2 luồng unsubscribe nội bộ + portal)
    ├── service/      NotificationService (internal — thay 3 action *Internal không guard),
    │                 NotificationPreferenceService, WebPushService, DigestService, PresenceService, ContactService
    ├── jobs/         DigestJobs, DeadlineJobs, NotificationJobs, TenantJobs, AuthJobs   # 7 @Scheduled (mục 1.6)
    └── repo/         NotificationRepository, NotificationPreferenceRepository, PushSubscriptionRepository,
                      ContactRepository, UserPresenceRepository, SessionRepository, EventRepository
```

Ghi chú bố trí (quyết định thật, không mặc định):

- **Entity đặt cạnh repo trong từng feature** (không gom `entities/` chung) — trừ `User`, `Task`, `Client`, `Workspace`, `Profile` là aggregate chéo domain: đặt ở feature "chủ sở hữu" (`auth`→User, `task`→Task, `crm`→Client, `tenant`→Workspace/Profile), domain khác tham chiếu qua repository — mirror đúng cách review module hiện tham chiếu Task/User bằng scalar id.
- Cron nghiệp vụ nào thuộc domain nào thì `jobs/` nằm trong domain đó (review-janitor ở `review`, digest/deadline ở `notification`) — không có "cron package" trung tâm.
- `portal` tách 2 sub-package `client`/`guest` vì 2 hệ token dễ nhầm tên (`ClientShareLink` vs `ShareLink` — ghi nhận `parts/09` §7.6).
- 2 Python function `api/*.py` (orphan, `vdownloader.py` public không auth — `parts/01` §5.1): **không port, xóa** — migration là điểm khai tử tự nhiên.

---

## 3. ĐIỂM KHÓ / RỦI RO KHI PORT (chỉ những thứ TỒN TẠI THẬT trong code)

| # | Rủi ro | Bằng chứng | Mức độ | Hướng xử lý |
|---|---|---|---|---|
| 3.1 | **Server actions gắn chặt React/RSC** — 55 file / ~190 hàm là RPC compile-time của Next; **208 lần `revalidatePath`/`revalidateTag` trong 38 file** (grep toàn `src/`, đậm nhất: `bulk-task-actions.ts` 21, `schedule-actions.ts` 17, `member-actions.ts` 14, `crm-actions.ts` 12, `share-portal-actions.ts` 11). `revalidatePath` KHÔNG có tương đương Spring — nó purge cache RSC của chính Next | `src/actions/**` (38 file); ví dụ `src/actions/member-actions.ts`, `src/actions/bulk-task-actions.ts` | **CAO NHẤT** — quyết định cả chiến lược | Nếu giữ Next làm FE (khuyến nghị giai đoạn 1): mọi action → REST call + FE tự refetch (React Query/SWR hoặc `router.refresh()`); mất cache-invalidation server-side là mất có chủ đích. Nếu bỏ Next: viết lại FE — ngoài phạm vi backend port. Không có đường "port dần từng action" mà không đụng FE, vì call-site là import trực tiếp. |
| 3.2 | **Tương thích session cookie thời kỳ chuyển tiếp** — payload JWT lồng object `user`, cookie `session` 30 ngày + rolling refresh <50% + cặp cookie impersonation TTL 2h + 3 cookie guest per-slug | payload `src/actions/auth-actions.ts:344-357`; cookie attrs `src/lib/auth.ts:23-29`; rolling `src/middleware.ts:145-163`; impersonation `src/lib/auth.ts:76-141`; guest `src/lib/review/share-auth.ts:111-187` | **Cao** | Mục 1.3: cùng `JWT_SECRET`, cùng claim shape, test vector chéo Next↔Spring. Nếu Next FE vẫn đứng trước (BFF), middleware Next tiếp tục rolling-refresh — Spring chỉ verify; chọn 1 bên duy nhất được re-issue để tránh 2 bên đua set-cookie. |
| 3.3 | **Streaming zip 2 route** — archiver STORE mode, stream thẳng từ R2, backpressure theo tốc độ client, `maxDuration=300`, tối đa 1000 file/20GB | `src/app/api/review/download-zip/route.ts:16,35,61`; `src/app/api/share/[token]/download-zip/route.ts:34,254,360`; sanitize path chống `../` trong tên entry `src/lib/review/download-zip.ts:105` | **Trung** | `StreamingResponseBody` + `ZipOutputStream` với `setMethod(STORED)` (STORED đòi size+CRC biết trước — hiện có size trong DB, CRC phải tính khi stream → dùng `ZipArchiveOutputStream` của commons-compress hỗ trợ STORED streaming, hoặc chấp nhận DEFLATED level 0). Chạy trên executor riêng (client chậm giữ thread hàng giờ — cấu hình async timeout Tomcat thay cho `maxDuration`). Port cả sanitize path entry. |
| 3.4 | **Upload multipart flow + Idempotency-Key + poll** — browser PUT thẳng R2 (không qua server), server chỉ presign/complete; FE poll 3s trạng thái | `src/lib/review/upload-service.ts:127-560`; `UploadSession.idempotencyKey @unique` `prisma/schema.prisma:2021` | **Thấp** (flow giữ nguyên) | Chỉ port presign endpoints (mục 1.9). Idempotency = bắt unique-violation trả session cũ. Poll giữ nguyên — không cần WebSocket. |
| 3.5 | **Mux JWT RS256 tự ký, không SDK** — playback/thumbnail/storyboard token, key PEM từ env | `src/lib/review/mux-jwt.ts:1-9`; REST 3 endpoint `src/lib/review/mux.ts:1-8` | **Thấp** | Nimbus `RSASSASigner` + `RestClient` — ~2 file nhỏ. Giữ công thức TTL `min(6h, hạn share)` (`share-auth.ts:371-378`). |
| 3.6 | **PDF invoice bằng puppeteer-core + @sparticuz/chromium + handlebars template inline** — Java không chạy được puppeteer | `src/lib/invoice-generator.ts:1-4` (template HTML inline từ dòng 7); `nixpacks.toml` cài Chromium; portal cho khách tải PDF gốc `parts/04` §5 | **Trung** | 2 lựa chọn thật: (a) render HTML template (đơn giản, CSS thuần — không JS) bằng **openhtmltopdf** thuần Java — khả thi vì template hiện chỉ là HTML+CSS tĩnh; (b) giữ 1 sidecar Chromium (Playwright-Java/Browserless) nếu muốn pixel-perfect. Khách hàng THẬT đang nhận PDF này — phải diff bản render trước cutover. Lưu ý invoice cũ đã lưu PDF trong DB (`/api/invoices/[id]/download` ưu tiên file gốc) → PDF cũ không cần re-render. |
| 3.7 | **Excel export ExcelJS** — xuất task theo tháng, múi giờ VN | `src/app/api/exports/monthly-tasks-xlsx/route.ts:2,172` | **Thấp** | Apache POI (SXSSF nếu file lớn). Giữ logic timezone VN (`Asia/Ho_Chi_Minh`) khi group theo tháng. |
| 3.8 | **i18n server-side (next-intl)** — 5 locale static-import, locale lấy từ header `x-portal-locale` do middleware inject; dùng cho trang portal/share render server-side. Backend Spring chỉ cần i18n cho **email + message lỗi** (UI do FE render) | `src/i18n/request.ts:17-21,35-44`; `next.config.ts:2,5`; `messages/` 5 json | **Thấp–Trung** | Nếu Next FE ở lại: next-intl ở nguyên FE, Spring không đụng. Phần backend cần: email guest/portal đang là template EN cứng trong code (`src/lib/review/guest-emails/`) — port nguyên; message lỗi VN/EN theo 2 advice (mục 1.1 review). KHÔNG cần MessageSource đầy đủ 5 locale ở backend. |
| 3.9 | **Supabase Realtime** — client-side subscribe; server chỉ POST REST broadcast fire-and-forget timeout 3s; degrade-gracefully khi thiếu env (app vẫn chạy, mất realtime) | `src/lib/supabase.ts:18-43`; `src/lib/notification-broadcast.ts:19,46` | **Thấp** | Giữ nguyên kiến trúc: Spring `SupabaseBroadcastClient` POST cùng endpoint (`@Async`, swallow lỗi). FE không đổi. Không dựng WebSocket server ở giai đoạn port. |
| 3.10 | **Impersonation** — 5 lớp chặn (target không OWNER, ADMIN cần OWNER, chặn target có quyền admin tenant khác vì cookie GLOBAL, chặn global ADMIN, audit đủ 2 chiều) + cookie swap standby + middleware bỏ rolling-refresh phiên impersonation | `src/actions/impersonation-actions.ts:9-107,113-122`; `src/lib/auth.ts:76-141`; `src/middleware.ts:145` | **Trung** | Port tay như mục 1.1 auth — nhấn mạnh: `SwitchUserFilter` của Spring KHÔNG có khái niệm cookie standby + TTL 2h + guard cross-tenant → dùng sẽ tạo lỗ hổng đã từng vá (HT-019). Test lại đủ 5 guard sau port. |
| 3.11 | **Vercel BotID bảo vệ signup** — passive signal phía client + `checkBotId()` server; chỉ hoạt động trên Vercel | `src/instrumentation-client.ts:13-20`; `src/actions/signup-actions.ts:178`; `next.config.ts:159-165` (tắt off-Vercel) | **Trung** | Rời Vercel là mất lớp này. Còn lại: honeypot + rate-limit Upstash 5/h IP + HIBP (đã có trong `signupAction`). Bù bằng Turnstile/hCaptcha nếu spam signup tăng — env `TURNSTILE_*` mồ côi trong `.env` cho thấy đã từng cân nhắc (`parts/01` §6.1). |
| 3.12 | **SSE/WebSocket server-side: KHÔNG TỒN TẠI** — đã verify: realtime = polling (comments 5s, upload 3s, task-assets 3s) + Supabase channel client-side; không có route SSE/stream text nào ngoài 2 zip route | grep `ReadableStream` toàn `src/` chỉ ra 2 route zip; `parts/05` (poll 3s/5s ghi tại từng route) | **— (tin tốt)** | Không phải port hạ tầng push nào. Giữ polling interval y nguyên để FE không đổi. |
| 3.13 | **React `cache()` per-request cho guard** — `getCurrentUser`/`verifyActiveSession` memo trong 1 request; layout + page + nhiều action cùng gọi | `src/lib/auth-guard.ts:21` (React cache), `src/lib/security.ts:217` (cached DAL) | **Thấp** (perf trap) | `@RequestScope` bean (mục 1.2) — nếu quên, mỗi request sẽ bắn 3-5 query liveness lặp. |
| 3.14 | **ffmpeg trong pipeline nền** — retag colorspace BT.709 stream từ R2 trước khi đẩy Mux; binary từ npm installer | `src/lib/review/color-retag.ts:30`; `src/lib/review/inngest.ts:417-419`; `@ffmpeg-installer/ffmpeg` `package.json:35` | **Thấp–Trung** | Cài ffmpeg vào Docker image, gọi `ProcessBuilder` stream stdin/stdout như hiện stream qua node. Test bằng đúng file mẫu untagged (đã có tiền sử bug màu — memory `video-review-color-shift`). |
| 3.15 | **Hai sub-project phụ thuộc kiến trúc hiện tại**: `electron/` wrap Next standalone + node-cron gọi HTTP cron (thiếu review-janitor); `mcp-server/` nói chuyện THẲNG DB qua Prisma client riêng | `electron/main/cron-scheduler.ts:19-26`; `mcp-server/src/index.ts:9-11` (`parts/01` §5) | **Trung** (quyết định sản phẩm) | `mcp-server` KHÔNG vỡ khi đổi backend (bypass app, đi thẳng Neon) — nhưng sẽ lệch business-rule nếu Spring thêm invariant mới; nên chuyển nó sang gọi REST của Spring về sau. `electron` vỡ hoàn toàn (wrap Next) — chốt trước: giữ (cần endpoint cron HTTP ở Chain 2) hay khai tử. |
| 3.16 | **`prisma db push` trong postinstall + drift migrations** — đổi sang Flyway phải cắt được thói quen "build là tự push schema" | `package.json:10`; `parts/03` §4.1 | **Trung** | Baseline pg_dump (mục 1.5.9); từ thời điểm cutover, CI chặn mọi DDL ngoài Flyway. Trong thời kỳ song song Next+Spring cùng DB: **đóng băng schema** (không db push, không Flyway migration đổi cấu trúc) trừ additive đã thỏa thuận. |
| 3.17 | **3 server action lộ public không guard sẽ đổi hành vi khi port** — `createNotificationInternal` & 2 bạn (public hiện tại → method nội bộ), `getPayrollLockStatus` (không guard → có guard), `trackEvent` (không auth) | `src/actions/notification-actions.ts:24,70,86`; `src/actions/bonus-actions.ts:38`; `src/actions/tracking-actions.ts:58` | **Thấp** (nhưng phải chủ đích) | Đây là các fix bảo mật "miễn phí" nhờ port — ghi vào changelog migration để không ai tưởng regression (đặc biệt nếu có client nào đang gọi action-id trực tiếp). |
| 3.18 | **Uniform-404/anti-enumeration là hợp đồng bảo mật, dễ vỡ khi map sang exception-handler mặc định của Spring** — portal trả 404 đồng nhất mọi nhánh fail; guest gate 404/410/410/401 với message not_found=revoked; PIN/OTP luôn 200 neutral | `src/lib/share-link-auth.ts:10-14,103`; `src/lib/review/share-auth.ts:101-103`; `request-pin/route.ts:47` (luôn `{status:'pin_sent'}`) | **Trung** | Spring mặc định trả 403/500 với body khác nhau theo exception → 2 `@RestControllerAdvice` (mục 1.1) phải là nơi DUY NHẤT sinh response lỗi cho 2 chain public; viết contract-test cho từng mã lỗi/message trước khi port. |

---

## 4. Tóm tắt ưu tiên thứ tự port (rút từ phụ thuộc thật)

1. `shared/security` + `shared/persistence` (filter chain, evaluator, baseline Flyway từ pg_dump) — mọi thứ khác đứng trên nó.
2. `auth` + `tenant` (session contract, guard trung tâm) — có test vector chéo cookie mới được đi tiếp.
3. `task` (FSM status + snapshot-test SALARY_PENDING_STATUSES trước khi đụng bất kỳ luồng nào ghi status — cùng nguyên tắc dự án review-fixes).
4. `finance` + `crm` (phụ thuộc task/tenant; advisory lock + partial unique phải có từ baseline).
5. `review` + `portal` (nặng nhất: 63 route + jobs + Mux/R2; nhưng độc lập tương đối nhờ scalar-FK).
6. `notification` + 7 `@Scheduled` cuối cùng (cần mọi service nghiệp vụ đã có).

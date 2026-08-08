# 03 — Inventory Model Prisma (schema.prisma)

> Nguồn: `prisma/schema.prisma` (2056 dòng). Đếm thật: **67 model, 15 enum**. Mọi số dòng dưới đây là số dòng thật trong file tại thời điểm audit (branch `claude/cranky-austin`).

## 1. Bảng inventory 67 model

### 1.1. Nhóm Core tenancy & Auth (10 model)

| # | Model | Dòng | Mục đích (1 câu) | Quan hệ chính (FK) | Field trạng thái / enum quan trọng |
|---|-------|------|------------------|--------------------|-------------------------------------|
| 1 | `Profile` | `prisma/schema.prisma:11` | Đơn vị "team/agency" cấp cao nhất (tenant gốc), chứa mọi workspace/user/client/finance | 1-N tới hầu hết model (User, Workspace, Task, Client, Invoice, Payroll…); `bonusConfig` 1-1 | `status` **String** `"ACTIVE"\|"SOFT_DELETED"`, soft-delete `deletedAt` + `hardDeleteAfter` (cron hard-delete 30 ngày) |
| 2 | `Workspace` | `prisma/schema.prisma:57` | Không gian làm việc theo tháng (multi-tenancy cấp 2), chứa task/payroll/CRM của 1 kỳ | `profileId → Profile?`; 1-N tới Task, WorkspaceMember, Invitation, Payroll, WikiPage… | `status` **String** `ACTIVE\|SUSPENDED\|SOFT_DELETED` (comment ghi "see WorkspaceRole enum" nhưng vẫn là String), `deletedAt`, `hardDeleteAfter`, `marketplaceOpen` Boolean |
| 3 | `WorkspaceMember` | `prisma/schema.prisma:110` | Thành viên của 1 workspace kèm vai trò | `userId → User` (Cascade), `workspaceId → Workspace` (Cascade) | `role` **String** default `"MEMBER"` (comment: "kept as String until migration applied"); `@@unique([userId, workspaceId])` |
| 4 | `User` | `prisma/schema.prisma:125` | Tài khoản người dùng (editor/admin/client) + toàn bộ auth state | `agencyId → Agency?`, `profileId → Profile?`, `clientId → Client?` (SetNull, portal); ~30 reverse relations | `role` **enum `UserRole`** default USER; lockout (`failedLoginAttempts`, `lockedUntil`), `sessionVersion` Int (invalidate JWT), `emailVerified`, `googleId @unique`, `username @unique`, `authProvider` String |
| 5 | `PushSubscription` | `prisma/schema.prisma:253` | Đăng ký Web Push của 1 trình duyệt/thiết bị | `userId → User` (Cascade) | `endpoint @unique` |
| 6 | `ProfileAccess` | `prisma/schema.prisma:266` | Quyền truy cập của user vào 1 profile (RBAC cấp profile) | `userId → User`, `profileId → Profile` (Cascade cả 2), `clientId → Client?` (SetNull, role CLIENT) | `role` **enum `ProfileRole`** default USER; `grantedAt` = cutoff cho ADMIN thấy workspace mới; `@@unique([userId, profileId])` |
| 7 | `ProfileAccessRequest` | `prisma/schema.prisma:292` | Yêu cầu xin truy cập profile chờ duyệt | `userId`, `targetProfileId → Profile`, `requestedById`, `approvedById → User` | `status` **String** `PENDING\|APPROVED\|REJECTED`; `@@unique([userId, targetProfileId])` |
| 8 | `EmailVerificationToken` | `prisma/schema.prisma:1305` | Token (hash SHA-256) xác thực email / reset password qua link | `userId → User` (Cascade) | `purpose` **String** `EMAIL_VERIFICATION\|PASSWORD_RESET\|EMAIL_MIGRATION`, `tokenHash @unique`, `usedAt` |
| 9 | `PasswordResetOTP` | `prisma/schema.prisma:1327` | OTP 6 số (hash) cho quên mật khẩu / migration email | `userId → User` (Cascade) | `purpose` **String** `PASSWORD_RESET\|EMAIL_MIGRATION`, `attemptCount` (≥5 → invalidate), `consumedAt`, `invalidatedAt` |
| 10 | `LoginAttempt` | `prisma/schema.prisma:1351` | Log mọi lần login (thành công/thất bại) phục vụ lockout + audit | `userId → User?` (SetNull) | `success` Boolean, `failReason` **String** (`invalid_password`/`user_not_found`/`account_locked`/…) |

### 1.2. Nhóm Task & vận hành (8 model)

| # | Model | Dòng | Mục đích | Quan hệ chính (FK) | Field trạng thái / enum |
|---|-------|------|----------|--------------------|--------------------------|
| 11 | `Task` | `prisma/schema.prisma:331` | Đơn vị công việc trung tâm (1 video job) kèm tiền tệ, deadline, frame info | `assigneeId → User`, `assignedById → User?` (SetNull), `clientId → Client?` (**SetNull** — xoá client không mất task), `projectId → Project?`, `invoiceId → Invoice?`, `workspaceId → Workspace?`, `profileId → Profile?`, `assignedAgencyId → Agency?`, `clientUserId → User?` | `status` **String TỰ DO** default `"Đang thực hiện"` (KHÔNG enum — điểm đặc biệt số 1 của repo); `invoiceStatus` **enum `InvoiceTaskStatus`**; `claimSource` **enum `ClaimSource`**; `clientReview` **String?** (`AWAITING/APPROVED/CHANGES`); `isArchived`, `isPenalized` Boolean; tiền: `jobPriceUSD/wageVND/profitVND/exchangeRate` Decimal; `currentVersionId` String? = **cột legacy Stream experiment, giữ nguyên, luôn null** (`prisma/schema.prisma:405-409`) |
| 12 | `TaskRawFootage` | `prisma/schema.prisma:432` | Bản đồ Multi-Hook Map / batch footage của 1 task (Velox v4) | `taskId @unique → Task` (Cascade) | `displayType` **enum `RawFootageDisplayType`**; `veloxMap` Json (auto-scan), `manualGraph` Json (whiteboard node graph) |
| 13 | `TagCategory` | `prisma/schema.prisma:1170` | Danh mục tag do user tạo trong workspace | `profileId/userId/workspaceId` (Cascade cả 3) | — |
| 14 | `TaskTag` | `prisma/schema.prisma:1189` | Gắn tag ↔ task (N-N) | `taskId → Task`, `tagCategoryId → TagCategory` (Cascade) | `@@unique([taskId, tagCategoryId])` |
| 15 | `PriceTemplate` | `prisma/schema.prisma:1149` | Template giá (USD/wage VND) cho Add-Task, theo workspace | **Không có relation Prisma** — chỉ scalar `workspaceId` | — |
| 16 | `PricingRule` | `prisma/schema.prisma:1404` | Rule tính giá tự động (flat/per-minute/tiered) theo client hoặc workspace-default | `clientId → Client?` (SetNull), `workspaceId → Workspace` (Cascade); `profileId` scalar | `ruleType` **String** `flat\|per_minute\|tiered_duration\|custom`, `config` Json, `isDefault` |
| 17 | `IntegrationToken` | `prisma/schema.prisma:1374` | OAuth token Dropbox/Google Drive (AES-256-GCM encrypted) theo user × workspace | `userId → User`, `workspaceId → Workspace` (Cascade) | `provider` **String** `dropbox\|google_drive`; `@@unique([userId, workspaceId, provider])` |
| 18 | `ClientTaskRequest` | `prisma/schema.prisma:632` | Yêu cầu công việc do CLIENT tự gửi qua portal (intake, KHÔNG phải Task) | `clientId → Client?` (SetNull), `taskId → Task?` (SetNull khi accept spawn task); `profileId/workspaceId` scalar **required** | `status` **enum `ClientRequestStatus`** default NEW; `submittedVia` String `SHARE_LINK\|ACCOUNT`; không chứa field tiền/assignee (leak discipline) |

### 1.3. Nhóm CRM & Finance (10 model)

| # | Model | Dòng | Mục đích | Quan hệ chính (FK) | Field trạng thái / enum |
|---|-------|------|----------|--------------------|--------------------------|
| 19 | `Client` | `prisma/schema.prisma:494` | Khách hàng (id **Int autoincrement**), có cây parent/sub-brand, scope theo PROFILE (canonical) | self-FK `parentId → Client` (Cascade), `profileId → Profile?`, `workspaceId → Workspace?` (**LEGACY read-only**, `prisma/schema.prisma:511-516`), `mergedIntoId → Client?` (SetNull) | `tier` **enum `ClientTier`** default `standard`; `status` **String** `ACTIVE\|SOFT_DELETED\|MERGED` + `deletedAt/hardDeleteAfter`; `depositBalance` Decimal |
| 20 | `ClientShareLink` | `prisma/schema.prisma:572` | Link công khai token-hoá (SHA-256, hiện raw đúng 1 lần) cho client xem toàn bộ lịch sử không cần account | `clientId → Client`, `profileId → Profile` (Cascade), `createdById → User?` (SetNull) | `tokenHash @unique`, `revokedAt/expiresAt`; toggle `allowVideoComments/allowDownload/showAllVersions/canApprove`, `passphraseHash`; notify-email OTP fields (`notifyEmail*`), `notifyEmailUnsubToken @unique` |
| 21 | `Project` | `prisma/schema.prisma:676` | Dự án nhóm task theo client (id Int autoincrement) | `clientId → Client` (Cascade), `workspaceId/profileId/clientUserId` optional | — (không có status) |
| 22 | `Invoice` | `prisma/schema.prisma:752` | Hoá đơn cho client, snapshot billing/client dạng Json | `clientId → Client`, `workspaceId/profileId/clientUserId` optional | `status` **enum `InvoiceStatus`** default DRAFT; `invoiceNumber @unique`; `clientDepositDeducted` Decimal? (audit HT-030/024 — refund đúng số đã trừ) |
| 23 | `InvoiceItem` | `prisma/schema.prisma:787` | Dòng chi tiết hoá đơn | `invoiceId → Invoice` (Cascade), `taskId → Task?` | — |
| 24 | `Payment` | `prisma/schema.prisma:805` | Sổ thu tiền — ghi nhận client trả tiền thật (kể cả không có invoice), nhiều dòng = trả góp | **Không có relation Prisma** — scalar `clientId/workspaceId/profileId/invoiceId/recordedById` (chủ đích, action layer tự enforce scope — `prisma/schema.prisma:799-804`) | `method` String tự do |
| 25 | `BillingProfile` | `prisma/schema.prisma:735` | Thông tin tài khoản ngân hàng thụ hưởng dùng khi xuất invoice | `profileId → Profile?` | `isDefault` Boolean |
| 26 | `Payroll` | `prisma/schema.prisma:310` | Bảng lương user theo tháng/năm/workspace | `userId → User`, `workspaceId → Workspace`, `profileId → Profile?` | `status` **String** default `"UNPAID"`; `@@unique([userId, month, year, workspaceId])` |
| 27 | `MonthlyBonus` | `prisma/schema.prisma:457` | Thưởng xếp hạng doanh thu tháng (top 1/2/3) | `userId`, `workspaceId`, `profileId?` | `bonusPercent` Decimal (snapshot config); `@@unique([userId, month, year, workspaceId])` |
| 28 | `PayrollLock` | `prisma/schema.prisma:478` | Khoá kỳ lương tháng (chốt sổ) | `workspaceId`, `profileId?`; 1-N `MonthlyRank` | `isLocked` Boolean; `@@unique([month, year, workspaceId])` |
| 29 | `BonusConfig` | `prisma/schema.prisma:1499` | Cấu hình % thưởng top 1/2/3 — đúng 1 config / profile | `profileId @unique → Profile` (Cascade) | `top1..3Enabled/Percent` — không qua `getWorkspacePrisma` (comment `prisma/schema.prisma:1496-1497`) |

### 1.4. Nhóm chất lượng, hiệu suất, lịch (8 model)

| # | Model | Dòng | Mục đích | Quan hệ chính (FK) | Field trạng thái / enum |
|---|-------|------|----------|--------------------|--------------------------|
| 30 | `PerformanceMetric` | `prisma/schema.prisma:697` | Chỉ số hiệu suất user theo tháng (doanh thu, on-time, revision) | `userId`, `workspaceId`, `profileId?` | `classification` **String** default `"NORMAL"`; `@@unique([userId, month, year, workspaceId])` |
| 31 | `ErrorDictionary` | `prisma/schema.prisma:1014` | Từ điển mã lỗi + trọng số phạt | 1-N `ErrorLog` | `severity` Int 1-3, `penalty` Int, `isActive`; `code @unique`. **KHÔNG có workspaceId/profileId → global toàn hệ thống** |
| 32 | `ErrorLog` | `prisma/schema.prisma:1027` | Ghi nhận lỗi editor mắc trong 1 task (manager bắt) | `taskId → Task`, `userId → User`, `errorId → ErrorDictionary`, `detectedById → User`, `workspaceId → Workspace` (Cascade), `profileId?` | `frequency`, `calculatedScore` Int |
| 33 | `MonthlyRank` | `prisma/schema.prisma:1052` | Xếp hạng lỗi tháng của user (S/A/B/C/D) | `userId`, `workspaceId` (Cascade), `payrollLockId → PayrollLock?`, `profileId?` | `rank` **String** `S\|A\|B\|C\|D\|UNRANKED`, `isLocked`; `@@unique([userId, month, year, workspaceId])` |
| 34 | `Rating` | `prisma/schema.prisma:928` | Đánh giá của client cho 1 task (3 tiêu chí Decimal) | `taskId @unique → Task`, `clientId → User?` (⚠️ **String, trỏ User** — khác `Client.id` Int), `staffId → User`, `workspaceId?`, `shareLinkId → ClientShareLink?` (SetNull) | `ratedVia` **String** `ACCOUNT\|SHARE_LINK` |
| 35 | `ScheduleRule` | `prisma/schema.prisma:1077` | Lịch làm việc lặp theo thứ trong tuần | `userId` (Cascade), `workspaceId`, `profileId` (required) | `isActive`, `version` Int (optimistic lock); `@@unique([userId, dayOfWeek, workspaceId, profileId])` |
| 36 | `ScheduleException` | `prisma/schema.prisma:1101` | Ngoại lệ lịch 1 ngày cụ thể (block/thêm giờ) | `userId` (Cascade), `workspaceId`, `profileId` | `type` **enum `ScheduleExceptionType`** |
| 37 | `DailyAvailability` | `prisma/schema.prisma:1125` | Snapshot availability 24h/ngày (Json 24 string) | `userId` (Cascade), `workspaceId`, `profileId` | `@@unique([userId, date, workspaceId, profileId])` |

### 1.5. Nhóm Agency, invite, audit, tracking (8 model)

| # | Model | Dòng | Mục đích | Quan hệ chính (FK) | Field trạng thái / enum |
|---|-------|------|----------|--------------------|--------------------------|
| 38 | `Agency` | `prisma/schema.prisma:719` | Agency ngoài nhận task outsource | `ownerId → User?`, `profileId → Profile?`; N-N `members` User | `status` **String** default `"ACTIVE"`; `code @unique` |
| 39 | `WorkspaceInvitation` | `prisma/schema.prisma:826` | Lời mời vào workspace (in-app + token link) | `workspaceId` (Cascade), `invitedUserId → User?`, `invitedById → User` (Cascade) | `status` **String** `PENDING\|ACCEPTED\|DECLINED\|EXPIRED\|REVOKED`; `role` String; `token @unique`; `isClientInvite/clientId` **DEPRECATED** (`prisma/schema.prisma:832-835`); `@@unique([workspaceId, invitedUserId, status])` |
| 40 | `AuditLog` | `prisma/schema.prisma:861` | Audit trail append-only (id **BigInt autoincrement**) cho event bảo mật + auth | `workspaceId → Workspace?` (Cascade), `actorUserId/userId → User?` (SetNull) | `action/targetType` **String tự do** (`workspace.created`, `auth.signup`…); `beforeData/afterData` Json |
| 41 | `Session` | `prisma/schema.prisma:963` | Phiên analytics (IP, geo, thời lượng) | `userId → User?`, `workspaceId?`; 1-N Event | `durationSec` |
| 42 | `Event` | `prisma/schema.prisma:984` | Event tracking (PAGE_VIEW, BUTTON_CLICK…) trong 1 session | `sessionId → Session` (Cascade), `userId → User?` | `eventType/featureName` **String tự do**, `metadata` Json |
| 43 | `UserPresence` | `prisma/schema.prisma:1000` | Trạng thái online hiện tại (PK = userId) | `userId @id → User` (Cascade) | `status` **String** `ONLINE\|OFFLINE\|AWAY`, `lastHeartbeat` |
| 44 | `Contact` | `prisma/schema.prisma:1279` | Kết bạn/danh bạ giữa 2 user (chat) | `requesterId/receiverId → User` (Cascade) | `status` **enum `ContactStatus`**; `@@unique([requesterId, receiverId])` |
| 45 | `Notification` | `prisma/schema.prisma:1241` | Thông báo in-app cho user | `userId → User` (Cascade); `taskId/actorId` scalar | `type` **enum `NotificationType`** (17 giá trị); `isRead/isArchived`; `pushSentAt/emailSentAt` |

### 1.6. Nhóm Wiki, học tập, tiện ích (4 model)

| # | Model | Dòng | Mục đích | Quan hệ chính (FK) | Field trạng thái / enum |
|---|-------|------|----------|--------------------|--------------------------|
| 46 | `WikiPage` | `prisma/schema.prisma:1424` | Trang tài liệu dạng Notion (cây parent/child, Tiptap HTML) | `workspaceId` (Cascade), self-FK `parentId` (SetNull), `authorId → User`; `profileId` scalar | `position` Int |
| 47 | `StudyPlaceProgress` | `prisma/schema.prisma:1447` | Tiến độ spaced-repetition (SM-2: easeFactor/interval) theo user × câu hỏi | `workspaceId`, `userId` (Cascade cả 2) | `@@unique([workspaceId, userId, studySetId, questionId])` |
| 48 | `Attachment` | `prisma/schema.prisma:1475` | File đính kèm wiki (ảnh, metadata kích thước) | `wikiPageId → WikiPage?` (Cascade); `workspaceId/profileId` scalar | — |
| 49 | `NotificationPreference` | `prisma/schema.prisma:1266` | Tuỳ chọn nhận email notification per-user | `userId @unique → User` (Cascade) | `emailDigestMode` **String** `REALTIME\|HOURLY\|DAILY\|OFF`, `quietHoursStart/End` |

### 1.7. Nhóm Task Comments — chat ClickUp-style (3 model)

| # | Model | Dòng | Mục đích | Quan hệ chính (FK) | Field trạng thái / enum |
|---|-------|------|----------|--------------------|--------------------------|
| 50 | `TaskComment` | `prisma/schema.prisma:1530` | Comment thảo luận trên task (staff + client), có reply thread, action-item, pin | `taskId → Task` (Cascade), self-FK `parentId` (Cascade); `authorUserId/viaShareLinkId/clientId/actionAssigned*/pinnedById/spawnedTaskId` đều **scalar** | `visibility` **enum `CommentVisibility`** default CLIENT (INTERNAL không bao giờ ra portal); `authorType` String `STAFF\|CLIENT`; `isDeleted` Boolean (soft-delete); `mentions String[]` |
| 51 | `TaskCommentReadState` | `prisma/schema.prisma:1579` | Con trỏ đã-đọc per (user, task) để đếm unread | **Không relation** — scalar `userId/taskId` | `@@unique([userId, taskId])` |
| 52 | `TaskCommentReaction` | `prisma/schema.prisma:1592` | Reaction emoji trên TaskComment (staff = userId, client = viaShareLinkId) | `commentId → TaskComment` (Cascade) | Toggle enforce ở action layer, **không** unique DB (comment `prisma/schema.prisma:1589-1591`) |

### 1.8. Nhóm Review module — Mux + R2 (15 model)

> Toàn bộ nhóm này: cross-module FK (Task/User/Client/Workspace) là **SCALAR STRING chủ đích, không FK constraint** — quyết định P0 để không đổi hành vi delete cũ (`prisma/schema.prisma:1607-1613`).

| # | Model | Dòng | Mục đích | Quan hệ chính (FK) | Field trạng thái / enum |
|---|-------|------|----------|--------------------|--------------------------|
| 53 | `ReviewFolder` | `prisma/schema.prisma:1640` | Cây thư mục vô hạn cấp của module Tệp (materialized path) | self-FK `parentId` (**Restrict**); `workspaceId/clientId/taskId/createdById` scalar | Soft-delete trash 30d: `deletedAt/deletedById/deleteBatchId/orphanedFromPurge`; `path` + index `varchar_pattern_ops` (`prisma/schema.prisma:1678`); `systemKey @unique` (idempotency auto-folder); `rowVersion` optimistic lock; counter `itemCount/totalSizeBytes` BigInt |
| 54 | `ReviewAsset` | `prisma/schema.prisma:1684` | Version stack — "card" file mà user thấy | `folderId → ReviewFolder` (**Restrict**), `currentVersionId @unique → ReviewVersion?` (SetNull); `workspaceId/taskId/clientId/createdById` scalar | `mediaKind` **enum `ReviewMediaKind`**; `statusId` String? = chuỗi status task HustlyTasker đọc động; soft-delete + `deleteBatchId`; `rowVersion` |
| 55 | `ReviewVersion` | `prisma/schema.prisma:1721` | 1 file vật lý = 1 version trong stack (pipeline upload → Mux) | `assetId → ReviewAsset` (Cascade); `workspaceId/uploaderId` scalar | `pipelineStatus` **enum `ReviewPipelineStatus`** default UPLOADING; `reviewState` **enum `ReviewState`** default DRAFT; `muxAssetId @unique`; `@@unique([assetId, versionNumber])` (race-safe versioning); metadata fps rational/codec; soft-delete |
| 56 | `ReviewComment` | `prisma/schema.prisma:1781` | Comment review trên 1 VERSION (timecode, range, annotation vẽ SVG Json) | `versionId → ReviewVersion` (Cascade), self-FK `parentId` (Cascade), `guestSessionId → GuestSession?` (SetNull); `authorId/resolvedById/shareLinkId` scalar | `isInternal` Boolean default **true**; XOR author (CHECK trong manual SQL); `timecodeMs/durationMs/annotation` Json; `resolvedAt`, soft-delete `deletedAt` |
| 57 | `CommentAttachment` | `prisma/schema.prisma:1827` | Ảnh đính kèm comment review (chỉ image/*, CHECK SQL) | `commentId → ReviewComment` (Cascade) | — |
| 58 | `CommentReaction` | `prisma/schema.prisma:1846` | Reaction emoji trên ReviewComment (user XOR guest) | `commentId → ReviewComment`, `guestSessionId → GuestSession` (Cascade) | `reactorKey` = `"u:{userId}"\|"g:{guestSessionId}"`; `@@unique([commentId, reactorKey, emoji])` |
| 59 | `ShareLink` | `prisma/schema.prisma:1867` | Link share cho guest `/r/{slug}` (module review — KHÁC `ClientShareLink` của portal) | 1-N `ShareLinkItem`, `GuestSession`; `workspaceId/taskId/createdById` scalar | `slug @unique` nanoid(12); toggle `allowComments/allowDownload/downloadOnlyWhenApproved/showAllVersions`; `passwordHash` bcrypt, `expiresAt/revokedAt`; `rowVersion` |
| 60 | `ShareLinkItem` | `prisma/schema.prisma:1905` | Nội dung 1 link share: đúng 1 trong folderId XOR assetId (CHECK SQL) | `shareLinkId → ShareLink`, `folderId → ReviewFolder?`, `assetId → ReviewAsset?` (Cascade cả 3) | `@@unique([shareLinkId, folderId])`, `@@unique([shareLinkId, assetId])` |
| 61 | `GuestSession` | `prisma/schema.prisma:1926` | 1 trình duyệt guest × 1 share link (cookie giữ raw token, DB giữ hash) | `shareLinkId → ShareLink` (Cascade) | `tokenHash @unique`; `name/email` required; `emailVerifiedAt` (PIN double-opt-in FR-11) |
| 62 | `GuestEmailVerification` | `prisma/schema.prisma:1951` | 1 mã PIN 6 số đang chờ cho double-opt-in email guest | **Không relation** — scalar `email/shareLinkId` | `attempts` (khoá tại 5), `expiresAt` (+10m), `consumedAt` |
| 63 | `GuestSubscription` | `prisma/schema.prisma:1968` | Đăng ký email của guest theo dõi 1 asset (sống sót khi rotate slug) | `assetId → ReviewAsset` (Cascade); còn lại scalar | `@@unique([email, assetId])`; `unsubscribedAt` (soft), `unsubscribeToken @unique` |
| 64 | `ReviewActivity` | `prisma/schema.prisma:1989` | Event log append-only của module review (nuôi task activity + audit) | **KHÔNG FK chủ đích** — log phải sống lâu hơn row bị purge (`prisma/schema.prisma:1988`) | `type` **String tự do** (mở rộng không cần migration); `meta` Json |
| 65 | `UploadSession` | `prisma/schema.prisma:2016` | Sổ theo dõi multipart upload R2 (resume/abort, janitor 24h) | `versionId → ReviewVersion` (Cascade) | `idempotencyKey @unique`; `partsDone/partsTotal`; `expiresAt/completedAt/abortedAt` |
| 66 | `WebhookEvent` | `prisma/schema.prisma:2040` | Sổ cái webhook Mux (idempotency — id = event id của provider) | Không relation | `provider/type` String; `processedAt` null = Inngest chưa xong |
| 67 | `RateLimitBucket` | `prisma/schema.prisma:2052` | Rate limit fixed-window trên Postgres cho route guest share | Không relation; PK = `key` String | `windowStart`, `count` |

## 2. Toàn bộ 15 enum + giá trị

| Enum | Dòng | Giá trị | Dùng ở |
|------|------|---------|--------|
| `RawFootageDisplayType` | `prisma/schema.prisma:426` | `PER_LINK`, `BATCH`, `MULTI_HOOK_MAP` | `TaskRawFootage.displayType` |
| `ClientRequestStatus` | `prisma/schema.prisma:625` | `NEW`, `REVIEWING`, `ACCEPTED`, `REJECTED` | `ClientTaskRequest.status` |
| `ClientTier` | `prisma/schema.prisma:890` | `DIAMOND`, `GOLD`, `SILVER`, `WARNING`, `standard` (⚠️ lowercase lệch case với 4 giá trị còn lại) | `Client.tier` |
| `UserRole` | `prisma/schema.prisma:898` | `ADMIN`, `USER`, `AGENCY_ADMIN`, `CLIENT`, `LOCKED` | `User.role` |
| `ProfileRole` | `prisma/schema.prisma:908` | `OWNER`, `ADMIN`, `USER`, `CLIENT` | `ProfileAccess.role` |
| `InvoiceStatus` | `prisma/schema.prisma:915` | `DRAFT`, `SENT`, `PAID`, `OVERDUE`, `VOID` | `Invoice.status` |
| `InvoiceTaskStatus` | `prisma/schema.prisma:923` | `UNBILLED`, `INVOICED` | `Task.invoiceStatus` |
| `ScheduleExceptionType` | `prisma/schema.prisma:1144` | `BLOCK`, `ADD` | `ScheduleException.type` |
| `ClaimSource` | `prisma/schema.prisma:1165` | `ADMIN`, `MARKET` | `Task.claimSource` |
| `ContactStatus` | `prisma/schema.prisma:1206` | `PENDING`, `ACCEPTED`, `DECLINED`, `BLOCKED` | `Contact.status` |
| `NotificationType` | `prisma/schema.prisma:1213` | **18 giá trị**: `TASK_ASSIGNED`, `TASK_UNASSIGNED`, `TASK_STATUS_CHANGED`, `TASK_DEADLINE_APPROACHING`, `TASK_OVERDUE`, `TASK_COMMENT`, `TASK_STARTED`, `TASK_DELIVERED`, `WORKSPACE_INVITATION_ACCEPTED`, `WORKSPACE_INVITATION_DECLINED`, `WORKSPACE_INVITATION_RECEIVED`, `VIDEO_VERSION_UPLOADED`, `VIDEO_COMMENT_NEW`, `VIDEO_REVIEW_APPROVED`, `VIDEO_CHANGES_REQUESTED`, `TASK_CLIENT_SUBMITTED`, `COMMENT_ASSIGNED`, `COMMENT_RESOLVED` | `Notification.type` |
| `CommentVisibility` | `prisma/schema.prisma:1519` | `INTERNAL`, `CLIENT` | `TaskComment.visibility` (enum được GIỮ lại khi drop Stream experiment — `prisma/migrations/manual/p0pre_drop_stream_review_experiment.sql:19`) |
| `ReviewMediaKind` | `prisma/schema.prisma:1616` | `IMAGE`, `VIDEO` | `ReviewAsset.mediaKind`, `ReviewVersion.mediaKind` |
| `ReviewPipelineStatus` | `prisma/schema.prisma:1623` | `UPLOADING`, `UPLOADED`, `PROCESSING`, `READY`, `FAILED` | `ReviewVersion.pipelineStatus` |
| `ReviewState` | `prisma/schema.prisma:1631` | `DRAFT`, `AWAITING_REVIEW`, `CHANGES_REQUESTED`, `APPROVED` | `ReviewVersion.reviewState` (per-VERSION, tách khỏi task status) |

## 3. Điểm đặc biệt

### 3.1. Status: String tự do vs enum

- **`Task.status` là String TỰ DO**, default `"Đang thực hiện"` (`prisma/schema.prisma:336`) — KHÔNG enum. Đây là nền của rủi ro payroll `SALARY_PENDING_STATUSES` mà dự án review-fixes phải snapshot-test.
- Các model khác cũng dùng String tự do cho trạng thái: `Profile.status:25`, `Workspace.status:69`, `WorkspaceMember.role:114`, `ProfileAccessRequest.status:298`, `Payroll.status:318`, `Client.status:546`, `Agency.status:724`, `WorkspaceInvitation.status:838` + `role:831`, `UserPresence.status:1002`, `PerformanceMetric.classification:708`, `MonthlyRank.rank:1061`, `NotificationPreference.emailDigestMode:1270`, `TaskComment.authorType:1534`, `Task.clientReview:385` (`AWAITING/APPROVED/CHANGES`), `ReviewActivity.type:1991`.
- Enum thật sự chỉ áp cho 15 enum ở mục 2. Ghi chú tại `prisma/schema.prisma:114`: role của WorkspaceMember "kept as String until migration applied" — enum `WorkspaceRole`/`WorkspaceStatus` được comment nhắc tới nhưng **không tồn tại** trong schema.

### 3.2. Multi-tenancy

- **2 tầng**: `profileId` (tenant gốc) + `workspaceId` (workspace tháng). Hầu hết model nghiệp vụ mang cả 2, đa số nullable (backfill dần).
- `workspaceId` **required**: WorkspaceMember, Payroll, MonthlyBonus, PayrollLock, PerformanceMetric, ErrorLog, MonthlyRank, ScheduleRule/Exception, DailyAvailability, PriceTemplate, TagCategory, IntegrationToken, PricingRule, WikiPage, StudyPlaceProgress, Attachment, ClientTaskRequest, Payment, WorkspaceInvitation, và toàn bộ review module (scalar).
- `workspaceId` **nullable**: Task:378, Client:516 (legacy), Project, Invoice, Rating, Session, AuditLog (auth events).
- **Model KHÔNG có tenant nào (global)**: `ErrorDictionary:1014` (từ điển lỗi dùng chung mọi profile — đáng chú ý cho SaaS isolation), `WebhookEvent:2040`, `RateLimitBucket:2052`, `TaskCommentReadState:1579` (chỉ userId+taskId), `GuestEmailVerification:1951`, các bảng auth (EmailVerificationToken, PasswordResetOTP, LoginAttempt, PushSubscription — theo user), `Contact`, `Notification`, `NotificationPreference`, `UserPresence`, `BonusConfig` (theo profile duy nhất).

### 3.3. Soft-delete

- Pattern 3 cột `status + deletedAt + hardDeleteAfter`: `Profile:25-27`, `Workspace:69-71`, `Client:546-548` (+ trạng thái `MERGED` riêng với `mergedIntoId:552`).
- Pattern trash-batch review module (`deletedAt + deletedById + deleteBatchId + orphanedFromPurge`): `ReviewFolder:1667-1669`, `ReviewAsset:1702-1705`, `ReviewVersion:1762-1764`.
- Soft khác: `ReviewComment.deletedAt:1813`, `TaskComment.isDeleted:1543` (Boolean), `ShareLink.revokedAt:1885`, `ClientShareLink.revokedAt:579`, `GuestSubscription.unsubscribedAt:1976`.

### 3.4. Unique constraint & index đáng chú ý (trong schema)

- Chu kỳ lương: `@@unique([userId, month, year, workspaceId])` lặp lại ở Payroll:328, MonthlyBonus:475, PerformanceMetric:716, MonthlyRank:1073; `PayrollLock @@unique([month, year, workspaceId]):491`.
- Race-safe versioning: `ReviewVersion @@unique([assetId, versionNumber]):1773`.
- Chống trùng invite: `WorkspaceInvitation @@unique([workspaceId, invitedUserId, status]):850` (⚠️ unique có cột status — 2 invite cùng user khác status vẫn tồn tại song song, đây là chủ đích "prevent duplicate pending").
- Token hash unique: `ClientShareLink.tokenHash:574`, `GuestSession.tokenHash:1931`, `EmailVerificationToken.tokenHash:1309`, `WorkspaceInvitation.token:837`, `ShareLink.slug:1869`, `ReviewFolder.systemKey:1653`, `UploadSession.idempotencyKey:2021`, `GuestSubscription.unsubscribeToken:1977`.
- Index biểu thức Prisma-expressible duy nhất: `ReviewFolder @@index([path(ops: raw("varchar_pattern_ops"))]):1678` cho prefix scan LIKE.
- Optimistic locking bằng `rowVersion`/`version` Int: Task:360, ScheduleRule:1088, ScheduleException:1113, ReviewFolder:1651, ReviewAsset:1695, ShareLink:1874.

### 3.5. Kiểu id không đồng nhất

- `Client.id` và `Project.id` là **Int autoincrement** (`prisma/schema.prisma:495,677`); `AuditLog.id` là **BigInt**; phần còn lại uuid/cuid String. ⚠️ Bẫy đặt tên: `Rating.clientId` là **String trỏ User** (`prisma/schema.prisma:934-949`), trong khi `Task.clientId`/`ProfileAccess.clientId` là Int trỏ `Client`.

### 3.6. Cột legacy / dead-schema có chủ đích (không phải bug)

- `Task.currentVersionId:409` — cột sót từ Stream experiment đã drop, verified all-null, giữ vì luật additive-only.
- `Client.workspaceId:516` — legacy pre profile-scope, chỉ read-only forensics, sẽ drop sau.
- `WorkspaceInvitation.isClientInvite + clientId:835-836` — deprecated, client giờ vào bằng ClientShareLink.
- Model `Feedback` + enum `FeedbackSource` đã xoá hẳn (comment `prisma/schema.prisma:693-695,888`).

## 4. Cơ chế migrate thật + SQL thủ công

### 4.1. Cơ chế: `prisma db push` (KHÔNG dùng `prisma migrate`)

- **Bằng chứng trực tiếp**: `package.json:10` → `"postinstall": "prisma generate && prisma db push"` — mỗi build Vercel tự đẩy schema.
- Thư mục `prisma/migrations/` chỉ còn 5 migration hình thức, **mới nhất 2026-05-07** (`prisma/migrations/20260507000000_workspace_security_phase1/migration.sql`) — lịch sử migrate đã **DRIFT** khỏi Neon thật; chạy `migrate dev` bây giờ sẽ đề nghị RESET database. Convention của repo được ghi rõ tại `prisma/migrations/manual/chat_gd3_task_comment_actions.sql:18-25`: schema additive đi qua `db push`, kèm file SQL tay làm artifact forward/rollback.
- 5 migration hình thức: `20260124104017_init_postgres`, `20260124143947_add_product_link`, `20260315121500_remove_plain_password`, `20260315123000_add_daily_availability`, `20260507000000_workspace_security_phase1`.

### 4.2. SQL thủ công trong `prisma/migrations/manual/` (6 file)

| File | Nội dung | Vì sao phải SQL tay |
|------|----------|---------------------|
| `p0_add_review_module.sql` | **2 partial unique index case-insensitive**: `review_folder_name_per_parent` trên `ReviewFolder(parentId, lower(name)) WHERE deletedAt IS NULL AND parentId IS NOT NULL` (dòng 13-14) và `review_asset_name_per_folder` trên `ReviewAsset(folderId, lower(name)) WHERE deletedAt IS NULL` (dòng 15-16); **5 CHECK constraint**: `comment_author_xor` (19-21), `reaction_actor_xor` (22-24), `comment_range_needs_timecode` (27-29), `share_item_scope_xor` (32-34), `attachment_image_only` (37-39) | Prisma không diễn tả được partial/expression index + CHECK; diff engine của `db push` bỏ qua nên chúng sống sót qua mọi build (ghi chú dòng 5-8). ⚠️ Đây chính là 2 index "ẩn" từng gây 500 khi trùng tên folder — app code phải tự bắt lỗi unique-violation |
| `client_profile_name_unique.sql` | Partial unique `client_profile_path_unique` trên `Client(profileId, COALESCE(parentId,-1), lower(btrim(name))) WHERE status='ACTIVE' AND profileId IS NOT NULL` (dòng 28-30), tạo CONCURRENTLY | NULL parentId không đụng nhau trong unique thường; row MERGED phải được miễn |
| `last_owner_constraint.sql` | Trigger DB `ensure_workspace_owner_exists` + function `enforce_workspace_owner_count()` trên `WorkspaceMember` (dòng 21-69) — chặn race 2 OWNER demote nhau làm workspace mồ côi 0 OWNER | Chỉ DB-level trigger mới atomic; app check trong `src/lib/workspace-guards.ts` là defense-in-depth |
| `chat_gd3_task_comment_actions.sql` | Cột additive TaskComment (action-item, pin, spawnedTaskId), bảng `TaskCommentReadState`, 2 enum value mới `COMMENT_ASSIGNED/COMMENT_RESOLVED` (dòng 33-65) | Artifact forward mirror của `db push` + tài liệu hoá drift (dòng 18-25) |
| `chat_gd3_task_comment_actions_rollback.sql` | Rollback cặp với file trên | — |
| `p0pre_drop_stream_review_experiment.sql` | Audit record DDL drop 4 bảng + 2 enum của Stream experiment (dòng 13-18); GIỮ enum `CommentVisibility` (dòng 19) và cột `Task.currentVersionId` | Bản ghi kiểm chứng zero-data-loss (mọi bảng đếm = 0 trước khi drop) |

### 4.3. Hệ quả cho audit

1. **Constraint thật của DB ≠ schema.prisma**: muốn biết đầy đủ ràng buộc phải đọc cả `prisma/migrations/manual/*.sql` — schema.prisma thiếu 3 partial unique index, 5 CHECK, 1 trigger.
2. Vì `db push` không có history, các file manual là **nguồn sự thật duy nhất** về những gì đã chạy tay trên Neon; không có gì bảo đảm chúng đã được apply trên mọi môi trường (file `client_profile_name_unique.sql:14-17` còn ghi rõ "ONLY AFTER merge script").
3. Luật bất thành văn của repo (được lặp lại trong comment schema): **chỉ THÊM, không ALTER/DROP bảng cũ** — thấy nhất quán ở các cột legacy giữ nguyên (mục 3.6).

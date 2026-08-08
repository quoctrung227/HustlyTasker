# 07 — Inventory Server Actions (Phần B: n→z + inline "use server" ngoài src/actions)

> Phạm vi: mọi file `src/actions/*.ts` tên bắt đầu n→z. Danh sách giao việc dừng ở `upload-actions`,
> nhưng theo đúng định nghĩa "n→z" còn 5 file nữa (`user-actions`, `username-actions`,
> `velox-batch-actions`, `velox-helpers-actions`, `workspace-actions`) — **đã đưa vào đây để không sót**
> (nếu phần khác đã cover thì trùng lặp vô hại). Cộng kết quả grep `'use server'` toàn `src/`:
> ngoài `src/actions/` chỉ còn **3 inline action** trong 3 layout (bảng cuối).
> `src/lib/integration-tokens.ts` chỉ *nhắc tới* 'use server' trong comment — file thật là `import 'server-only'`
> (`src/lib/integration-tokens.ts:1`), KHÔNG phải action module.

**Chú giải cột guard:**
- `WS:MEMBER` / `WS:ADMIN` / `WS:OWNER` = `verifyWorkspaceAccess(workspaceId, role)` (src/lib/security.ts)
- `ProfileAdmin` = `verifyProfileAdminAccess(workspaceId)`
- `session` = `getSession()` / `getCurrentUser()` (JWT), tự ràng về caller
- `token` = share-link token là credential (`resolveShareToken` — hash-at-rest, revoke, expiry, rate-limit) — KHÔNG có session
- `live` = có kiểm `isSessionLive` (chặn LOCKED / sessionVersion cũ)
- **KHÔNG guard** = gọi được không cần bất kỳ xác thực nào

---

## 1. notification-actions.ts (304 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `createNotificationInternal` | src/actions/notification-actions.ts:24 | ⚠️ **KHÔNG guard** | `CreateNotificationParams` (userId đích tuỳ ý) | Tạo 1 notification + fire-and-forget email (`maybeSendNotificationEmail`) + web push | Notification, User (read) |
| `createBulkNotificationsInternal` | src/actions/notification-actions.ts:70 | ⚠️ **KHÔNG guard** | `userIds[]`, params | Fan-out tạo N notification | Notification |
| `createAndBroadcastNotifications` | src/actions/notification-actions.ts:86 | ⚠️ **KHÔNG guard** | `userIds[]`, params | Như trên + realtime broadcast từng cái | Notification |
| `getNotifications` | src/actions/notification-actions.ts:112 | session (self) | cursor/limit/unreadOnly/type | Phân trang notification của chính mình + unreadCount | Notification |
| `getUnreadNotificationCount` | src/actions/notification-actions.ts:165 | session (self) | — | Đếm chưa đọc | Notification |
| `markNotificationRead` | src/actions/notification-actions.ts:176 | session + ownership check | notificationId | Đánh dấu đã đọc (chặn Forbidden nếu không phải chủ) | Notification |
| `markAllNotificationsRead` | src/actions/notification-actions.ts:197 | session (self) | — | Đánh dấu tất cả đã đọc | Notification |
| `archiveNotification` | src/actions/notification-actions.ts:209 | session + ownership | notificationId | Archive + read | Notification |
| `clearAllArchived` | src/actions/notification-actions.ts:228 | session (self) | — | Xoá cứng mọi notification đã archive của mình | Notification |
| `getMyNotificationPreferences` | src/actions/notification-actions.ts:243 | session (self) | — | Đọc (auto-create default) preference | NotificationPreference |
| `updateMyNotificationPreferences` | src/actions/notification-actions.ts:264 | session (self) | emailEnabled/digestMode/quietHours (validate range) | Upsert preference | NotificationPreference |

⚠️ **Ghi chú:** 3 helper `*Internal`/`createAndBroadcastNotifications` là export trong file `'use server'` → được Next đăng ký thành **public Server Action endpoint** dù tên là "Internal". Không có bất kỳ check session nào — kẻ biết action-id có thể tạo notification (kèm gửi email + web push) tới **bất kỳ userId nào**. Cùng lớp lỗi mà `integration-tokens.ts` từng vá (AUDIT R4, src/lib/integration-tokens.ts:7-15) — nên chuyển sang module `server-only`.

## 2. password-reset-actions.ts (405 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `requestPasswordResetOtp` | src/actions/password-reset-actions.ts:65 | Public **by design**: rate-limit IP 10/h + email 3/h (Upstash), cooldown 60s, anti-enumeration (response đồng nhất + padding CSPRNG 100-300ms) | email | Gửi OTP reset (hash SHA-256, TTL 10') qua email; audit `auth.password_reset_requested` | User, PasswordResetOTP, AuditLog |
| `verifyPasswordResetOtp` | src/actions/password-reset-actions.ts:178 | Public by design: max 5 attempts (optimistic-lock atomic), purpose-scoped | email, otp 6 số | Verify OTP → mint reset token 32-byte (TTL 5', single-use) | User, PasswordResetOTP, EmailVerificationToken |
| `resetPasswordWithToken` | src/actions/password-reset-actions.ts:293 | Public by design: token single-use (CAS trong transaction), HIBP + ≥12 ký tự | rawToken, newPassword | Đổi password (bcrypt 12), bump `sessionVersion` (đá mọi JWT), reset lockout, email cảnh báo, audit | EmailVerificationToken, User, AuditLog |

## 3. payment-actions.ts (193 dòng) — "Sổ thu tiền"

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `recordPayment` | src/actions/payment-actions.ts:44 | WS:ADMIN + client phải ACTIVE cùng profile + invoice cùng workspace/client | clientId, amount>0, paidAt, method, note, invoiceId? | Ghi 1 khoản thanh toán; nếu link invoice → set invoice PAID; audit `payment.recorded` | Payment, Client, Workspace, Invoice, AuditLog |
| `deletePayment` | src/actions/payment-actions.ts:110 | WS:ADMIN + scoped workspace | paymentId | Xoá bản ghi thanh toán; audit `payment.deleted` | Payment, AuditLog |
| `getPaymentLedger` | src/actions/payment-actions.ts:139 | WS:ADMIN | workspaceId | Tổng đã trả theo từng client | Payment |
| `getClientPayments` | src/actions/payment-actions.ts:164 | WS:ADMIN | clientId | Lịch sử thanh toán 1 client + tên người ghi | Payment, User |

## 4. payroll-actions.ts (234 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `confirmPayment` | src/actions/payroll-actions.ts:22 | WS:ADMIN + **chặn nếu PayrollLock.isLocked** + validate tổng = base+bonus, không âm; cycle resolve server-side từ workspace.name (không tin month/year client) | userId, month/year (bị bỏ qua), baseSalary, bonus, totalAmount | Upsert Payroll → PAID; audit `payroll.locked` | Workspace, PayrollLock, Payroll, AuditLog |
| `getPayrollData` | src/actions/payroll-actions.ts:129 | WS:ADMIN | month, year | User role=USER là member workspace + payroll của cycle | User, Payroll |
| `revertPayment` | src/actions/payroll-actions.ts:165 | WS:ADMIN + **chặn nếu cycle locked** (anti-fraud) | userId (month/year client bị bỏ qua) | Xoá record Payroll (revert); audit `payroll.unlocked` | Workspace, PayrollLock, Payroll, AuditLog |

## 5. price-template-actions.ts (87 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getTemplates` | src/actions/price-template-actions.ts:9 | WS:MEMBER; **non-admin bị strip `priceUSD`** (AUDIT R12) | workspaceId | Danh sách mẫu giá (≤15) | PriceTemplate |
| `createTemplate` | src/actions/price-template-actions.ts:37 | WS:ADMIN + cap 15 | name, priceUSD, wageVND | Tạo mẫu giá | PriceTemplate |
| `deleteTemplate` | src/actions/price-template-actions.ts:68 | WS:ADMIN + `deleteMany({id, workspaceId})` chống IDOR cross-tenant (HT-011/012) | id | Xoá mẫu giá | PriceTemplate |

## 6. pricing-rule-actions.ts (449 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `listPricingRules` | src/actions/pricing-rule-actions.ts:152 | WS:MEMBER; non-admin bị **strip đệ quy mọi field `*USD*`** trong config (AUDIT R11) | workspaceId | Danh sách rule + client scope | PricingRule, Client |
| `createPricingRule` | src/actions/pricing-rule-actions.ts:189 | WS:ADMIN + validate config theo ruleType + client thuộc profile | name, clientId?, ruleType, config, isDefault | Tạo rule (tx unflag default cũ); audit | PricingRule, Workspace, Client, AuditLog |
| `updatePricingRule` | src/actions/pricing-rule-actions.ts:278 | WS:ADMIN + rule thuộc workspace + validate config | ruleId, partial input | Cập nhật rule; audit | PricingRule, Workspace, Client, AuditLog |
| `deletePricingRule` | src/actions/pricing-rule-actions.ts:365 | WS:ADMIN + rule thuộc workspace | ruleId | Xoá rule; audit | PricingRule, AuditLog |
| `setDefaultPricingRule` | src/actions/pricing-rule-actions.ts:406 | WS:ADMIN | ruleId | Set default (tx unflag cũ); audit | PricingRule, AuditLog |

## 7. profile-actions.ts (579 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `checkProfileAccess` | src/actions/profile-actions.ts:12 | session + ProfileAccess row | profileId | Kiểm quyền vào profile | User, ProfileAccess |
| `selectProfile` | src/actions/profile-actions.ts:36 | qua `checkProfileAccess` | profileId | Set cookie `current_profile_id` (httpOnly) | — (cookie) |
| `getAvailableProfiles` | src/actions/profile-actions.ts:53 | session | — | Profile caller có access | ProfileAccess, Profile |
| `getMyProfilesAndWorkspaces` | src/actions/profile-actions.ts:94 | session | — | Profiles + workspaces theo role (OWNER/ADMIN/USER/CLIENT đều thấy hết workspace của profile hiện tại — hotfix 2026-06-29) | ProfileAccess, Workspace |
| `updateProfile` | src/actions/profile-actions.ts:183 | session, **bỏ qua userId client** (AUDIT R2); email KHÔNG writable (HT-013 — phải qua OTP email-migration) | nickname, phoneNumber | Sửa hồ sơ chính mình | User |
| `createProfileForUser` | src/actions/profile-actions.ts:232 | session + cap 5 profile/user | name (2-50 ký tự) | Tạo Profile + ProfileAccess(OWNER) trong tx | Profile, ProfileAccess |
| `getProfileSettings` | src/actions/profile-actions.ts:286 | session + getProfileRole (mọi role) | profileId | Đọc settings (name/banner/logo/soft-delete state) | Profile |
| `updateProfileSettings` | src/actions/profile-actions.ts:319 | session + live + **OWNER** | name/bannerUrl/logoUrl/portalAccent (#hex validate, merge settings JSON) | Cập nhật brand profile; audit | Profile, AuditLog |
| `deleteProfileAction` | src/actions/profile-actions.ts:385 | session + live + **OWNER** | profileId | Soft-delete profile (grace 30 ngày); audit | Profile, AuditLog |
| `restoreProfileAction` | src/actions/profile-actions.ts:429 | session + live + **OWNER** | profileId | Khôi phục profile; audit | Profile, AuditLog |
| `getMyTrashedProfiles` | src/actions/profile-actions.ts:470 | session (chỉ row role=OWNER) | — | Profile đã soft-delete của mình | ProfileAccess, Profile |
| `changePassword` | src/actions/profile-actions.ts:508 | session (bind self, bỏ userId client — R3/R4) + **chặn impersonation** (R14) + verify mật khẩu cũ + bump sessionVersion + re-login | userId (ignored), currentPass, newPass | Đổi mật khẩu; audit `auth.password_changed` | User, AuditLog |

## 8. profile-member-actions.ts (471 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getProfileMembers` | src/actions/profile-member-actions.ts:49 | session + live (SI-1/SI-2) + role ≠ CLIENT; email bị mask với role USER | profileId | Roster nội bộ (loại CLIENT khỏi danh sách) | ProfileAccess, User |
| `inviteToProfileAction` | src/actions/profile-member-actions.ts:113 | session + live + `canInviteMember` (OWNER/ADMIN); **chỉ OWNER cấp được ADMIN** (R5) | profileId, workspaceId, usernameOrEmail, role | Uỷ quyền toàn bộ cho `inviteToWorkspace` (member-actions — luồng PENDING+accept, đủ guard R1-R14) | (qua member-actions) WorkspaceInvitation… |
| `removeFromProfileAction` | src/actions/profile-member-actions.ts:161 | session + live + **OWNER** + không tự xoá + không xoá OWNER | profileId, targetUserId | Tx: xoá WorkspaceMember + **hard-delete mọi WorkspaceInvitation** (chống replay R1+R3) + xoá ProfileAccess (chỉ non-OWNER — chống race IR-2); audit | WorkspaceMember, WorkspaceInvitation, ProfileAccess, Workspace, AuditLog |
| `changeProfileRoleAction` | src/actions/profile-member-actions.ts:236 | session + live + **OWNER**; chặn self/OWNER/CLIENT-promote (R4) | profileId, targetUserId, newRole | Đổi role (reset grantedAt khi USER→ADMIN); audit | ProfileAccess, AuditLog |
| `transferProfileOwnershipAction` | src/actions/profile-member-actions.ts:306 | session + live + **OWNER**; chặn transfer cho CLIENT; **CAS transaction** chống double-transfer (IR-1) | profileId, newOwnerUserId | Hoán quyền OWNER↔ADMIN nguyên tử; audit | ProfileAccess, AuditLog |
| `grantWorkspaceAccessToAdmin` | src/actions/profile-member-actions.ts:376 | session + live + **OWNER**; target phải là ADMIN; workspace thuộc profile & cũ hơn grantedAt | profileId, targetUserId, workspaceId | Upsert WorkspaceMember(ADMIN) cho workspace cũ; audit | ProfileAccess, Workspace, WorkspaceMember, AuditLog |
| `getOldWorkspacesForAdmin` | src/actions/profile-member-actions.ts:434 | session + live + **OWNER** | profileId, targetUserId | Workspace cũ hơn grantedAt của 1 admin (cho grant UI) | Workspace, ProfileAccess |

## 9. push-actions.ts (56 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getVapidPublicKey` | src/actions/push-actions.ts:14 | KHÔNG guard (chỉ trả public key env — vô hại) | — | VAPID public key hoặc null | — |
| `savePushSubscription` | src/actions/push-actions.ts:18 | session | endpoint/p256dh/auth (validate + cap độ dài) | Upsert push subscription (rebind theo endpoint unique) | PushSubscription |
| `deletePushSubscription` | src/actions/push-actions.ts:49 | session; delete scoped `{endpoint, userId}` | endpoint | Huỷ đăng ký push của chính mình | PushSubscription |

## 10. raw-footage-actions.ts (397 dòng) — Velox v4 / Hook Graph

Tất cả đi qua helper `loadTaskOrFail` (src/actions/raw-footage-actions.ts:117): session → validate UUID (Zod) → task tồn tại → `WS:MEMBER` trên workspace **của task**.

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getRawFootageMap` | src/actions/raw-footage-actions.ts:146 | loadTaskOrFail (MEMBER) | taskId | Đọc row TaskRawFootage | Task, TaskRawFootage |
| `setRawFootageDisplayType` | src/actions/raw-footage-actions.ts:159 | loadTaskOrFail + enum whitelist | taskId, PER_LINK/BATCH/MULTI_HOOK_MAP | Upsert displayType; audit khi đổi | TaskRawFootage, AuditLog |
| `saveRawFootageMap` | src/actions/raw-footage-actions.ts:215 | loadTaskOrFail + **Zod schema velox-4.0** (URL validate chống `javascript:`) | taskId, veloxMap, sourceFolderUrl, scannedAt | Upsert veloxMap; audit | TaskRawFootage, AuditLog |
| `getHookGraph` | src/actions/raw-footage-actions.ts:326 | loadTaskOrFail | taskId | Đọc manualGraph (normalize) + veloxMap seed | TaskRawFootage |
| `saveHookGraph` | src/actions/raw-footage-actions.ts:351 | loadTaskOrFail + **Zod hookgraph-1** (cap 500 blocks/2000 edges) | taskId, graph | Upsert manualGraph; audit | TaskRawFootage, AuditLog |

## 11. reputation-actions.ts (7 dòng) — STUB vô hiệu

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `checkOverdueTasks` | src/actions/reputation-actions.ts:3 | KHÔNG guard (vô hại — no-op) | workspaceId | Disabled by product rule — trả rỗng, không đụng DB | — |

## 12. retry-translation-action.ts (8 dòng) — STUB deprecated

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `retryTaskTranslation` | src/actions/retry-translation-action.ts:6 | KHÔNG guard (vô hại — luôn trả error) | taskId, workspaceId | Deprecated — dịch tự động đã gỡ | — |

## 13. schedule-actions.ts (324 dòng)

Guard chung `validateAccess` (src/actions/schedule-actions.ts:12): WS:MEMBER bắt buộc; ADMIN/OWNER sửa lịch bất kỳ, MEMBER chỉ sửa lịch chính mình (so userId + profileId).

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `upsertScheduleRule` | src/actions/schedule-actions.ts:37 | validateAccess; updaterId fallback = caller | userId, dayOfWeek, startTime, endTime, timezone | Tạo/sửa lịch lặp tuần (version++) | ScheduleRule |
| `deleteScheduleRule` | src/actions/schedule-actions.ts:97 | validateAccess trên **owner của rule** | ruleId | Xoá rule | ScheduleRule |
| `createScheduleException` | src/actions/schedule-actions.ts:119 | validateAccess; attribution bind caller (R5) | userId, dateStr YYYY-MM-DD, times, BLOCK/ADD, reason | Tạo exception 1 ngày (UTC-midnight) | ScheduleException |
| `createBatchScheduleExceptions` | src/actions/schedule-actions.ts:165 | validateAccess | entries[] | Tạo nhiều exception trong 1 tx | ScheduleException |
| `deleteScheduleException` | src/actions/schedule-actions.ts:204 | validateAccess trên owner của row | exceptionId | Xoá 1 exception | ScheduleException |
| `getEffectiveAvailability` | src/actions/schedule-actions.ts:227 | WS:MEMBER (R1 fix #18 — trước đây KHÔNG auth) | userId, targetDate | Base rule + ADD − BLOCK của 1 ngày | ScheduleRule, ScheduleException |
| `deleteScheduleExceptionsByIds` | src/actions/schedule-actions.ts:272 | validateAccess trên **mọi distinct owner** (R3 fix — trước chỉ check row đầu) | exceptionIds[] | Xoá nhiều exception | ScheduleException |
| `deleteScheduleExceptionsForDay` | src/actions/schedule-actions.ts:307 | validateAccess | userId, dateStr | Xoá mọi exception của 1 user/ngày | ScheduleException |

## 14. share-document-actions.ts (533 dòng) — "Files & masters" portal khách

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getDocumentsViaToken` | src/actions/share-document-actions.ts:461 | **token** (resolveShareToken) | token | Snapshot thư viện file đã giao: cây folder (lọc tên folder client khác khỏi path — chống leak tên brand đối thủ), asset READY + processing/inProgress count | Task, ReviewAsset, ReviewVersion, ReviewFolder, ReviewComment, Workspace, Client, ShareLink (qua shares helper) |
| `downloadDocumentsViaToken` | src/actions/share-document-actions.ts:466 | **token** + `limitDb` 60/h **fail-closed** keyed theo shareLinkId (chặn XFF spoof), cheap-checks-first | token, versionIds[] (≤100) | Presign R2 GET URL (TTL 15') cho từng file; audit `share_link.accessed` | như trên + presign R2, AuditLog |

## 15. share-link-actions.ts (152 dòng) — quản trị link chia sẻ (phía admin)

Guard chung `gateShareLinkAdmin` (src/actions/share-link-actions.ts:25): session + **live** (HT-025) + `canManageShareLinks` = profile OWNER/ADMIN.

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `createClientShareLink` | src/actions/share-link-actions.ts:46 | gate + client ACTIVE thuộc profile | clientId, workspaceId | Mint token 72-bit base64url, chỉ lưu SHA-256 hash, URL raw trả đúng 1 lần; audit | Client, ClientShareLink, AuditLog |
| `revokeClientShareLink` | src/actions/share-link-actions.ts:91 | gate + link thuộc profile | linkId | Set revokedAt (hiệu lực tức thì); audit | ClientShareLink, AuditLog |
| `listClientShareLinks` | src/actions/share-link-actions.ts:121 | gate | clientId | Metadata link (KHÔNG bao giờ select tokenHash) | ClientShareLink |

## 16. share-portal-actions.ts (1878 dòng) — portal khách PUBLIC, token là credential

Không có session; mọi action re-resolve token qua `resolveShareToken`, authz = `clientId ∈ scope.clientIds` + `workspaceId ∈ scope.workspaceIds` (helper `findScopedTask` :480, kèm `isArchived:false`).

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `ensureScreeningIdentity` | src/actions/share-portal-actions.ts:71 | token + share slug thuộc client trong scope + notifyEmail đã verify | token, slug | Mint guest-session cookie cho screening room từ email đã OTP-verify | ShareLink, ClientShareLink, (guest session qua share-auth) |
| `getShareSnapshot` | src/actions/share-portal-actions.ts:165 | token | token | Snapshot toàn cục: tasks (kể cả tombstone archived đã APPROVED/CHANGES) + invoices + brand. Whitelist nghiêm: **jobPriceUSD CÓ** (quyết định owner — khách trả giá này), `status` nội bộ/`assignee`/`notes_vi`/frame credentials **bị strip**; mint `/r/{slug}` review board cho task client-phase; bank block whitelist từ billingSnapshot | Task, Invoice, Workspace, ReviewAsset, ShareLink, Profile, Rating (select 4 field) |
| `getPortalNotifyEmail` | src/actions/share-portal-actions.ts:565 | token | token | Trạng thái email nhận thông báo | ClientShareLink |
| `requestPortalNotifyEmail` | src/actions/share-portal-actions.ts:582 | token + `limitDb` **3/h theo inbox thật** (normalize +tag/gmail dots — chống email-bomb HT-015) + rateLimit 5/h/link+ip | token, email | Lưu pending + gửi OTP 6 số (TTL 15') | ClientShareLink |
| `verifyPortalNotifyEmail` | src/actions/share-portal-actions.ts:626 | token + rateLimit 10 attempts/link+ip | token, code | Promote pending → verified + mint unsub token | ClientShareLink |
| `removePortalNotifyEmail` | src/actions/share-portal-actions.ts:665 | token | token | Xoá notify email | ClientShareLink |
| `unsubscribePortalNotify` | src/actions/share-portal-actions.ts:684 | **unsub-token riêng** (20-128 ký tự) | unsubToken | One-click unsubscribe | ClientShareLink |
| `approveDeliverableViaToken` | src/actions/share-portal-actions.ts:765 | token + `isClientFacingPhase` gate (HT-014/HT-006) + **updateMany pin toàn bộ state+tenancy đã đọc** (chống race admin-cancel / re-upload) | token, taskId | Task → 'Hoàn tất' + clientReview APPROVED (= tín hiệu payroll editor); notify staff; audit `task.client_approved` | Task, Notification, AuditLog |
| `approveDeliverablesViaToken` | src/actions/share-portal-actions.ts:855 | token + cap 50 + cùng phase-gate, tx interactive (timeout 20s) pin từng row, audit **awaited** | token, taskIds[] | Bulk approve; notification gộp theo người nhận; báo approved/skipped thật | Task, Notification, AuditLog |
| `requestChangesViaToken` | src/actions/share-portal-actions.ts:1011 | token + phase gate + sanitize feedback + updateMany pin | token, taskId, feedback | Task → 'Revision' + clientReview CHANGES + feedback; notify; audit | Task, Notification, AuditLog |
| `submitRatingViaToken` | src/actions/share-portal-actions.ts:1082 | token + task completed/APPROVED + Rating.taskId unique + sao 1-5 integer | token, taskId, 3 sao, feedback? | Tạo Rating (ratedVia=SHARE_LINK, staffId=assignee) | Task, Rating |
| `getSubmitOptionsViaToken` | src/actions/share-portal-actions.ts:1151 | token | token | Dropdown workspace ACTIVE + brand trong scope | Workspace, Client |
| `createTaskViaToken` | src/actions/share-portal-actions.ts:1182 | token + rateLimit 20/h/link + scope check + sanitize/URL validate | token, {workspaceId, clientId, title, rawLink, brollLink?, notes?} | Tạo Task 'Đang đợi giao' type 'Khách gửi' — **retained but unused** (v2 thay thế, xem :1267) | Workspace, Task, Notification, AuditLog |
| `submitClientRequestViaToken` | src/actions/share-portal-actions.ts:1350 | token + rateLimit 20/h + scope + sanitize mọi link | token, SubmitClientRequestInput | Tạo **ClientTaskRequest** (NEW) — luồng intake v2; notify admins (TASK_CLIENT_SUBMITTED); audit | ClientTaskRequest, Workspace, Notification, AuditLog |
| `createSubClientViaToken` | src/actions/share-portal-actions.ts:1460 | token + `limitDb` 10/h + **pg_advisory_xact_lock theo profileId** + re-resolve token TRONG tx (skipRateLimit) + depth ≤4 + cap 20 sibling + dedup tên NFC | token, {name, parentId} | Tạo sub-brand (Client con) an toàn concurrency; audit | Client, AuditLog |
| `getActivityViaToken` | src/actions/share-portal-actions.ts:1609 | token (findScopedTask) | token, taskId | Timeline hoạt động — tên staff bị ẩn thành 'Nhóm biên tập' | AuditLog |
| `getCommentFeedViaToken` | src/actions/share-portal-actions.ts:1651 | token; **hard-filter visibility=CLIENT** | token, taskId | Feed comment + event + reactions (mine theo shareLink) | TaskComment, AuditLog, TaskCommentReaction |
| `postCommentViaToken` | src/actions/share-portal-actions.ts:1703 | token + rateLimit 30/h + parent phải CLIENT-visible cùng task | token, taskId, body, parentId? | Comment authorType=CLIENT, visibility **forced CLIENT**; notify manager; audit | TaskComment, Notification, AuditLog |
| `toggleReactionViaToken` | src/actions/share-portal-actions.ts:1777 | token + rateLimit 120/h + comment CLIENT-visible + task trong scope | token, commentId, emoji (whitelist) | Toggle reaction keyed theo shareLink | TaskComment, TaskCommentReaction |
| `getClientRequestsViaToken` | src/actions/share-portal-actions.ts:1828 | token; select whitelist (không reviewedById/profileId…) | token | Danh sách yêu cầu của khách + phản hồi studio (chỉ sau quyết định) | ClientTaskRequest, Workspace |

## 17. signup-actions.ts (357 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `signupAction` | src/actions/signup-actions.ts:107 | Public **by design**: honeypot → ToS → validate displayName/username/email → Vercel BotID → rate-limit IP 5/h + email 3/h → HIBP ≥12 ký tự → anti-enum (padding ~600ms constant-time) | SignupInput | Tx tạo Profile + User(role=USER, bcrypt 12) + Workspace mặc định + WorkspaceMember(OWNER) + ProfileAccess(OWNER) + EmailVerificationToken (24h); gửi mail verify; audit `auth.signup` | Profile, User, Workspace, WorkspaceMember, ProfileAccess, EmailVerificationToken, AuditLog |

## 18. study-place-actions.ts (226 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getStudyPlaceProgress` | src/actions/study-place-actions.ts:50 | ProfileAdmin; row scoped theo caller | workspaceId, studySetId? | Tiến độ SRS của chính caller | StudyPlaceProgress |
| `reviewStudyPlaceQuestionAction` | src/actions/study-place-actions.ts:78 | ProfileAdmin + questionId whitelist | StudyPlaceReviewInput | Upsert tiến độ SM-2 | StudyPlaceProgress |
| `toggleStudyPlaceBookmarkAction` | src/actions/study-place-actions.ts:148 | ProfileAdmin + whitelist | workspaceId, questionId, bookmarked | Toggle bookmark | StudyPlaceProgress |
| `resetStudyPlaceProgressAction` | src/actions/study-place-actions.ts:201 | ProfileAdmin | workspaceId, questionId? | Reset tiến độ (1 câu hoặc cả set) | StudyPlaceProgress |

## 19. tag-actions.ts (205 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getTagsForUser` | src/actions/tag-actions.ts:12 | WS:MEMBER; scoped userId+profileId+workspaceId | workspaceId | Tag của caller trong workspace | TagCategory, User |
| `createTag` | src/actions/tag-actions.ts:47 | WS:ADMIN + cap 15 + dedup case-insensitive | name (≤30) | Tạo tag cá nhân | TagCategory |
| `updateTag` | src/actions/tag-actions.ts:94 | WS:ADMIN + **owner của tag** | tagId, name | Đổi tên tag | TagCategory |
| `deleteTag` | src/actions/tag-actions.ts:120 | WS:ADMIN + owner | tagId | Xoá tag (cascade TaskTag) | TagCategory |
| `setTaskTags` | src/actions/tag-actions.ts:140 | WS:ADMIN + mọi tag phải thuộc caller | taskId, tagCategoryIds[] | Replace toàn bộ tag của task | Task, TagCategory, TaskTag |
| `getTaskTags` | src/actions/tag-actions.ts:181 | session + WS:MEMBER trên workspace của task (R1 fix #19) | taskId | Tag của 1 task | Task, TaskTag |

## 20. task-actions.ts (596 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `updateTaskStatus` | src/actions/task-actions.ts:17 | getCurrentUser + WS:MEMBER; non-admin chỉ task của mình; **non-admin bị chặn vào/ra terminal status + vào client-phase** (H3 + HT-016); status whitelist; FSM validateTransition; optimistic lock version | id, newStatus, workspaceId, newNotes?, currentVersion? | Đổi status (kèm invariant deadline-null, pool-reset khi 'Đang đợi giao', auto-archive khi 'Đã hủy'); email routing GĐ3/GĐ4 + notif; audit started/delivered/completed | Task, User, Notification, AuditLog |
| `getCancelledTasks` | src/actions/task-actions.ts:509 | WS:ADMIN | workspaceId | Danh sách task archived (projection scalar, không leak giá) | Task |
| `restoreCancelledTask` | src/actions/task-actions.ts:553 | WS:ADMIN | taskId | Un-archive + status theo invariant assignee; audit `task.restored` | Task, AuditLog |

(`notifyTaskStatusChanged` :439 không export — helper nội bộ, không phải action.)

## 21. task-comment-actions.ts (572 dòng) — comment staff

Guard chung `staffCtx` (src/actions/task-comment-actions.ts:150) = WS:MEMBER (+cờ isAdmin); `taskInWorkspace` chống id-spoof.

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getTaskActivityFeed` | src/actions/task-comment-actions.ts:163 | staffCtx + taskInWorkspace | taskId, workspaceId | Feed comment (INTERNAL+CLIENT) + activity + reactions + action-item state | TaskComment, AuditLog, TaskCommentReaction, User, Client |
| `createTaskComment` | src/actions/task-comment-actions.ts:244 | staffCtx; sanitize; parent cùng task; **mention notify lọc bỏ tài khoản CLIENT khi INTERNAL** (HT-026) | taskId, {body, visibility, parentId?} | Tạo comment STAFF + notify @mention + broadcast + audit | TaskComment, User, Notification, AuditLog |
| `editTaskComment` | src/actions/task-comment-actions.ts:302 | staffCtx + **chỉ tác giả** | commentId, body | Sửa comment (editedAt) | TaskComment |
| `deleteTaskComment` | src/actions/task-comment-actions.ts:318 | staffCtx + tác giả hoặc admin | commentId | Soft-delete comment | TaskComment |
| `toggleTaskCommentReaction` | src/actions/task-comment-actions.ts:333 | staffCtx + emoji whitelist | commentId, emoji | Toggle reaction của caller | TaskCommentReaction |
| `assignTaskComment` | src/actions/task-comment-actions.ts:369 | staffCtx + assignee phải là **workspace member** | commentId, assigneeUserId\|null | Gán/huỷ action-item từ comment; notify; audit | TaskComment, WorkspaceMember, Notification, AuditLog |
| `resolveTaskComment` | src/actions/task-comment-actions.ts:427 | staffCtx | commentId | Đánh dấu resolved; notify người giao | TaskComment, Notification, AuditLog |
| `reopenTaskComment` | src/actions/task-comment-actions.ts:464 | staffCtx | commentId | Mở lại action-item | TaskComment, AuditLog |
| `markTaskCommentsRead` | src/actions/task-comment-actions.ts:482 | staffCtx | taskId | Upsert read-marker | TaskCommentReadState |
| `getTaskUnreadCounts` | src/actions/task-comment-actions.ts:500 | staffCtx + lọc taskIds thuộc workspace | workspaceId, taskIds[] | Đếm 💬 total/unread per task | Task, TaskComment, TaskCommentReadState |
| `searchWorkspaceMembers` | src/actions/task-comment-actions.ts:541 | staffCtx | workspaceId, q | Autocomplete member (≤8) | WorkspaceMember, User |
| `getTaskMentionTargets` | src/actions/task-comment-actions.ts:561 | staffCtx + taskInWorkspace | taskId, q | @mention scope theo task (editor/manager/client/member) | Task, User, ProfileAccess |

## 22. task-management-actions.ts (298 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `deleteTask` | src/actions/task-management-actions.ts:12 | WS:ADMIN (R1 fix #8) | id, workspaceId | **HARD delete** task | Task |
| `updateTask` | src/actions/task-management-actions.ts:35 | WS:MEMBER; admin sửa mọi task, non-admin chỉ task của mình + **bị strip mọi field tiền/tenancy/status/lifecycle** (R3/R5); tenancy fields (id/workspaceId/profileId) bị khoá với **mọi** caller (HT-007); invariant assignee↔status + status↔deadline | id, data (any), workspaceId | Generic update task | Task |
| `assignTask` | src/actions/task-management-actions.ts:118 | WS:ADMIN + chặn Rank D + **assignee phải thuộc profile của workspace** (R14) | taskId, assignmentId\|null\|'sys:revoke' | Giao/thu hồi task (status 'Nhận task'/'Đang đợi giao'); notify assigned/unassigned | Task, MonthlyRank, User, Notification |

## 23. toggle-treasurer.ts (33 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `toggleTreasurer` | src/actions/toggle-treasurer.ts:7 | **WS:OWNER** (không cho ADMIN self-grant) + cấm tự toggle + target phải là member (R1 BLOCKER + R14) | userId, currentStatus, workspaceId | Bật/tắt cờ `isTreasurer` (quyền tài chính) | WorkspaceMember, User |

## 24. tracking-actions.ts (354 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `forceFlush` | src/actions/tracking-actions.ts:29 | ⚠️ **KHÔNG guard** (chỉ flush buffer in-memory — rủi ro thấp) | — | Ghi buffer event xuống DB | Event |
| `trackEvent` | src/actions/tracking-actions.ts:58 | ⚠️ **KHÔNG session guard** — chỉ cần cookie `tracking_session_id` (tự set phía client) | eventType, featureName, metadata | Buffer + batch-insert event analytics (userId luôn null) — vector spam ghi DB không xác thực | Event |
| `pingHeartbeat` | src/actions/tracking-actions.ts:91 | session (R1 fix #16 — bỏ userId client) | status | Upsert presence + upsert Session (ip/country từ header) | UserPresence, Session |
| `getSessionTrends` | src/actions/tracking-actions.ts:166 | session + sessionProfileId + **chặn CLIENT** (HT-034) | — | Session theo giờ 24h (scoped profile) | Session |
| `getRecentEventLogs` | src/actions/tracking-actions.ts:217 | session + profile + chặn CLIENT | limit | Event log gần nhất (kèm user) | Event, User |
| `getFrictionData` | src/actions/tracking-actions.ts:260 | session + profile + chặn CLIENT | — | Ma trận friction 7 ngày × 24h | Event |
| `getLivePresence` | src/actions/tracking-actions.ts:311 | session + profile + chặn CLIENT | — | Presence 5 phút gần nhất | UserPresence, User |

## 25. ui-actions.ts (28 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `toggleMobileView` | src/actions/ui-actions.ts:6 | KHÔNG guard (cookie cá nhân — vô hại) | forceMobile | Set cookie `view-mode` 1 năm | — |
| `setUiPref` | src/actions/ui-actions.ts:22 | KHÔNG guard (cookie cá nhân — vô hại) | 'mc'\|'admin' | Set cookie `ui-pref` (Mission Control opt-in) | — |

## 26. update-task-details.ts (138 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `updateTaskDetails` | src/actions/update-task-details.ts:22 | WS:MEMBER; admin sửa đủ field; non-admin **chỉ task được giao** (R1 fix #10) và chỉ `productLink`+`notes_en`; **sanitize URI scheme chống stored-XSS `javascript:`** (HT-031); sửa tiền/deadline ADMIN-only + **chặn khi payroll cycle PAID** | id, data{resources, references, notes, title, productLink, deadline, jobPriceUSD, value, …} | Cập nhật chi tiết task; sync `wageVND=value`, tính lại `profitVND`; deadline mới reset createdAt + isPenalized | Task, Payroll |

## 27. upload-actions.ts (297 dòng)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `uploadPaymentQr` | src/actions/upload-actions.ts:53 | session (**bỏ qua userId client** — R1 BLOCKER IDOR fix); MIME whitelist + ≤4MB + Sharp re-encode webp lossless | userId (ignored), FormData(file, bankName, accountNum) | Upload QR thanh toán lên Vercel Blob + lưu bank info | User |
| `uploadAvatar` | src/actions/upload-actions.ts:120 | session (bỏ userId client); ≤10MB; Sharp 512² webp | userId (ignored), FormData(file) | Upload avatar | User |
| `uploadProfileBanner` | src/actions/upload-actions.ts:210 | `verifyProfileOwner` (**profile OWNER**) | profileId, FormData(file ≤10MB) | Banner 1500×500 webp | Profile |
| `uploadProfileLogo` | src/actions/upload-actions.ts:257 | verifyProfileOwner | profileId, FormData(file ≤5MB) | Logo 512² webp | Profile |

## 28. user-actions.ts (518 dòng) — ngoài danh sách đề bài nhưng thuộc n→z

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `changePassword` | src/actions/user-actions.ts:11 | session + **chặn impersonation** + verify mật khẩu hiện tại + bump sessionVersion + re-login (R14) | FormData(currentPassword, newPassword ≥6) | Đổi mật khẩu chính mình; audit | User, AuditLog |
| `updateUserRole` | src/actions/user-actions.ts:78 | WS:ADMIN + **role whitelist USER/AGENCY_ADMIN** (không mint global ADMIN — R2) + cấm self + positive-tenancy check (R11) | userId, newRole, workspaceId | Đổi `User.role` global (trong tenant); audit | User, Workspace, WorkspaceMember, ProfileAccess, AuditLog |
| `deleteUser` | src/actions/user-actions.ts:169 | (deprecated → gọi deactivateUser) | userId, workspaceId | Alias PDPL-compliant | (qua deactivateUser) |
| `deactivateUser` | src/actions/user-actions.ts:181 | WS:ADMIN + cross-profile check + **positive-tenancy** (R10) + **OWNER chỉ bị OWNER deactivate** (R13 CRITICAL) + native-member guard | userId, workspaceId | role→LOCKED + bump sessionVersion (force logout), giữ data; audit | User, Workspace, WorkspaceMember, ProfileAccess, AuditLog |
| `reactivateUser` | src/actions/user-actions.ts:337 | WS:ADMIN + tenancy (R10) + OWNER-symmetric guard (R13) | userId, newRole, workspaceId | LOCKED → role mới; audit | User, …, AuditLog |
| `adminResetPassword` | src/actions/user-actions.ts:423 | (vô hiệu hoá — luôn trả error) | — | Deprecated vì bảo mật | — |
| `triggerForcePasswordReset` | src/actions/user-actions.ts:442 | WS:ADMIN + positive-tenancy (R12) + target có email + không LOCKED | userId, workspaceId | Gửi OTP reset qua luồng public (`requestPasswordResetOtp`); admin không bao giờ thấy password; audit | User, Workspace, WorkspaceMember, ProfileAccess, AuditLog (+ PasswordResetOTP qua reuse) |

## 29. username-actions.ts (240 dòng) — ngoài danh sách đề bài nhưng thuộc n→z

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `checkUsernameAvailable` | src/actions/username-actions.ts:34 | ⚠️ **KHÔNG guard** — public by design (form signup); là oracle liệt kê username (không rate-limit tại đây) | rawUsername | Check trùng username | User |
| `completeUsernameMigration` | src/actions/username-actions.ts:73 | session; validate + uniqueness + idempotent | newUsername | Set username + usernameSetByUser=true; audit | User, AuditLog |
| `updateMyUsername` | src/actions/username-actions.ts:142 | (delegate hàm trên) | newUsername | Đổi username từ settings | User |
| `searchInviteCandidates` | src/actions/username-actions.ts:158 | session + **WS:ADMIN** (chống enumeration cross-org); scope profile; exclude member hiện tại + CLIENT/LOCKED; nhánh exact-email cross-profile đã bị GỠ (invite-flow R1) | workspaceId, query | Autocomplete ứng viên mời (≤10) | Workspace, WorkspaceMember, User |

## 30. velox-batch-actions.ts (340 dòng) — ngoài danh sách đề bài nhưng thuộc n→z

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `createTasksFromBatch` | src/actions/velox-batch-actions.ts:102 | WS:ADMIN + cap 500 row + validate exchangeRate/per-row + assignee tồn tại & **thuộc profile workspace** (R14) + clientId **thuộc profile** (R14) | rows[], exchangeRate, skipInvalid?, managerId? | Tạo hàng loạt Task trong 1 tx (giá/lương/profit tính server); ensureWorkspaceMembership cho assignee; audit bulk + per-task; notify per-assignee | User, Client, Task, WorkspaceMember (qua helper), Notification, AuditLog |

## 31. velox-helpers-actions.ts (230 dòng) — ngoài danh sách đề bài nhưng thuộc n→z

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getLastClientNote` | src/actions/velox-helpers-actions.ts:85 | WS:ADMIN + scope profile của session | clientId, workspaceId | Kế thừa note gần nhất của cùng client theo **name-path** (clientPathKey) xuyên workspace | Workspace, Client, Task |
| `suggestRoundRobinAssignee` | src/actions/velox-helpers-actions.ts:179 | WS:ADMIN | workspaceId | Đề xuất editor ít việc nhất (orphan-user guard) | WorkspaceMember, Task |

## 32. workspace-actions.ts (530 dòng) — ngoài danh sách đề bài nhưng thuộc n→z

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `createWorkspaceAction` | src/actions/workspace-actions.ts:12 | session + `canCreateWorkspace` (profile OWNER/ADMIN) + cap 10 owned | FormData(name ≤50, description ≤200) | Tx tạo Workspace + WorkspaceMember(OWNER); audit | Workspace, WorkspaceMember, AuditLog |
| `renameWorkspaceAction` | src/actions/workspace-actions.ts:93 | WS:ADMIN | workspaceId, newName | Đổi tên; audit | Workspace, AuditLog |
| `getWorkspacesForProfile` | src/actions/workspace-actions.ts:134 | ⚠️ **session CHỈ** — KHÔNG kiểm caller có access profileId → user đăng nhập bất kỳ liệt kê được id/name/description workspace ACTIVE của **profile bất kỳ** (metadata leak nhẹ, không leak nội dung) | profileId | Danh sách workspace ACTIVE của profile | Workspace |
| `transferWorkspaceOwnership` | src/actions/workspace-actions.ts:175 | (deprecated stub — luôn trả error, chuyển sang transfer Profile) | — | Dead-code candidate | — |
| `deleteWorkspaceAction` | src/actions/workspace-actions.ts:181 | WS:ADMIN + **phải OWNER** (hoặc isGlobalAdmin) | workspaceId | Soft-delete (grace 30 ngày); fallback hard-delete nếu thiếu cột migration (kèm audit forensics) | Workspace, AuditLog |
| `getMyTrashedWorkspaces` | src/actions/workspace-actions.ts:279 | session (chỉ membership OWNER của caller) | — | Workspace soft-deleted để restore | WorkspaceMember, Workspace |
| `restoreWorkspaceAction` | src/actions/workspace-actions.ts:327 | WS:ADMIN + phải OWNER | workspaceId | Khôi phục ACTIVE; audit | Workspace, AuditLog |
| `createNextMonthWithRollover` | src/actions/workspace-actions.ts:383 | WS:ADMIN (workspace nguồn) + chống trùng tên tháng + cap 10 owned | currentWorkspaceId | Tạo workspace "Tháng N+1/YYYY" + copy mọi task chưa xong (reset status/delivery/invoice; **copy cả frameUsername/framePassword/frameNote** sang task mới — :490-492); audit | Workspace, WorkspaceMember, Task, AuditLog |

---

## 33. Inline `'use server'` NGOÀI src/actions (kết quả grep toàn src/)

| Function | file:line | Guard | Input | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `handleLogout` (closure) | src/app/[workspaceId]/team/(browser)/layout.tsx:47 (directive :48) | Không cần (logout chính mình) | — | `logout()` + redirect /login | — |
| `handleLogout` (closure) | src/app/[workspaceId]/dashboard/layout.tsx:55 (directive :56) | Không cần | — | logout + redirect | — |
| `handleLogout` (closure) | src/app/[workspaceId]/admin/layout.tsx:70 (directive :71) | Không cần | — | logout + redirect | — |

Ngoài ra: `src/lib/integration-tokens.ts:1` là `import 'server-only'` — comment dòng 7-15 chỉ ghi lại việc hàm `refreshTokenIfNeeded` từng bị lộ thành Server Action và đã được dời ra. **Không phải action module** — không đưa vào inventory.

---

## Tổng hợp function KHÔNG guard / guard yếu (phạm vi phần B)

| Mức | Function | Vị trí | Rủi ro |
|---|---|---|---|
| ⚠️ Cao | `createNotificationInternal` / `createBulkNotificationsInternal` / `createAndBroadcastNotifications` | src/actions/notification-actions.ts:24, :70, :86 | Export từ file `'use server'` → endpoint public, KHÔNG session check: tạo notification + email + web push tới userId bất kỳ. Nên tách sang module `server-only` (đúng pattern integration-tokens R4). |
| ⚠️ Trung | `trackEvent` | src/actions/tracking-actions.ts:58 | Không auth (chỉ cookie tự set) → ghi Event tuỳ ý vào DB (spam/poison analytics). |
| ⚠️ Trung | `getWorkspacesForProfile` | src/actions/workspace-actions.ts:134 | Chỉ getSession, không kiểm access vào profileId → leak metadata workspace (id/tên/mô tả) cross-tenant cho user đăng nhập bất kỳ. |
| ⚠️ Thấp | `checkUsernameAvailable` | src/actions/username-actions.ts:34 | Public by design (signup) nhưng không rate-limit tại action → oracle liệt kê username. |
| ⚠️ Thấp | `forceFlush` | src/actions/tracking-actions.ts:29 | Không guard; chỉ flush buffer — rủi ro thấp. |
| ℹ️ By design | `getVapidPublicKey`, `toggleMobileView`, `setUiPref`, `checkOverdueTasks` (stub), `retryTaskTranslation` (stub) | push-actions.ts:14; ui-actions.ts:6, :22; reputation-actions.ts:3; retry-translation-action.ts:6 | Vô hại (public key / cookie cá nhân / no-op). |
| ℹ️ By design | Toàn bộ password-reset (3), `signupAction`, 21 action share-portal, 2 action share-document, `unsubscribePortalNotify` | các bảng 2, 14, 16, 17 | Public có chủ đích — credential là OTP/token/unsub-token + rate-limit + anti-enumeration. |

## Dead-code / stub candidates (phần B)

- `checkOverdueTasks` — src/actions/reputation-actions.ts:3 (no-op theo product rule).
- `retryTaskTranslation` — src/actions/retry-translation-action.ts:6 (deprecated, luôn error).
- `adminResetPassword` — src/actions/user-actions.ts:423 (vô hiệu hoá, trỏ sang triggerForcePasswordReset).
- `transferWorkspaceOwnership` — src/actions/workspace-actions.ts:175 (deprecated, chuyển sang Profile-level).
- `createTaskViaToken` — src/actions/share-portal-actions.ts:1182 ("retained but unused" — bị thay bởi `submitClientRequestViaToken`, xem comment :1267-1272).
- `deleteUser` — src/actions/user-actions.ts:169 (alias backward-compat của deactivateUser).

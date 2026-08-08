# 06 — Inventory Server Actions PHẦN A (`src/actions/` a→m)

> Phạm vi: 23 file từ `admin-actions.ts` → `mc-task-drawer-actions.ts` + `member-actions.ts` (được giao kèm). Tổng ~7.569 dòng.
> Mỗi bảng liệt kê MỌI exported async function: tên | vị trí | guard thật gọi đầu hàm | input chính | tác dụng | model Prisma đụng tới.
> Chú thích guard: `vWA(X)` = `verifyWorkspaceAccess(workspaceId, X)` (src/lib/security), `vPAA` = `verifyProfileAdminAccess`, `vFA` = `verifyFinanceAccess`, `vAS` = `verifyActiveSession`.

## Tổng quan taxonomy guard (đếm thật trong 23 file)

| Guard | Số function dùng | Ghi chú |
|---|---|---|
| `verifyWorkspaceAccess(…, 'ADMIN')` | 33 | chuẩn cho mutation admin |
| `verifyWorkspaceAccess(…, 'MEMBER')` | 9 | trong đó 3 hàm analytics tự thêm check `user.id === userId` |
| `verifyFinanceAccess` | 8 | mọi đường đọc/ghi số tiền USD (crm + invoice) |
| `verifyProfileAdminAccess` | 7 | client-request (5), create-user (1), mc-drawer (1) |
| `getSession`/`getCurrentUser` (tự quản, không role) | 17 | contact (8), member tự phục vụ (3), email-migration (2), cross-team dùng thêm `isSessionLive`+`getProfileRole` (4) |
| `getProfileRole === 'OWNER'` | 2 | updateProfile / deleteProfile |
| `verifyActiveSession` | 2 | global-settings (xem finding G-2) |
| Local helper `ensureWorkspaceAccess` (availability) | 3 | WorkspaceMember HOẶC cùng profile — KHÔNG dùng vWA |
| **KHÔNG có guard** | 4 | xem mục "Function KHÔNG có guard" cuối file |

---

## 1. `src/actions/admin-actions.ts` (386 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `updateUserRole` | src/actions/admin-actions.ts:14 | `vWA('ADMIN')` (dòng 18) + whitelist role USER/AGENCY_ADMIN + chặn tự đổi + check tenancy | `userId, newRole, workspaceId` | Đổi `User.role` cho user thuộc đúng tenant | User, Workspace, WorkspaceMember, ProfileAccess |
| `createTask` | src/actions/admin-actions.ts:85 | `vWA('ADMIN')` (dòng 89, gọi lại dòng 140) | `formData, workspaceId` | Tạo Task mới (validate client/assignee/manager thuộc profile), notify + email assignee | Task, Client, User, WorkspaceMember (ensureWorkspaceMembership), Notification, AuditLog |
| `updateTaskManager` | src/actions/admin-actions.ts:347 | `vWA('ADMIN')` (dòng 349) | `taskId, managerId, workspaceId` | Đổi "Người quản lý" (`Task.assignedById`) | Task, AuditLog |

## 2. `src/actions/admin-profile-actions.ts` (95 dòng) — file DEPRECATED một nửa

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `createProfile` | src/actions/admin-profile-actions.ts:24 | — (throw ngay) | `_data` | **Stub deprecated** — luôn throw, hướng sang `createProfileForUser` | — |
| `updateProfile` | src/actions/admin-profile-actions.ts:28 | `getSession` + `getProfileRole === 'OWNER'` (dòng 29–36) | `id, {name,bannerUrl,logoUrl}` | Owner cập nhật tên/banner/logo Profile | Profile |
| `deleteProfile` | src/actions/admin-profile-actions.ts:55 | `getSession` + `getProfileRole === 'OWNER'` (dòng 56–63) | `id` | Xoá Profile trống (chặn nếu còn user/workspace/task; null hoá FK 10 bảng) | Profile, User, Workspace, Task, Client, Project, Invoice, Payroll, MonthlyBonus, PayrollLock, PerformanceMetric |
| `changeUserProfile` | src/actions/admin-profile-actions.ts:93 | — (throw ngay) | `_userId, _newProfileId` | **Stub deprecated** — luôn throw | — |

## 3. `src/actions/analytics-actions.ts` (282 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getAnalyticsData` | src/actions/analytics-actions.ts:7 | `vWA('ADMIN')` (dòng 9) | `workspaceId` | Bảng xếp hạng lỗi/task hoàn tất từng editor (rank S→D) | Task, ErrorLog, User |
| `getUserErrorDetails` | src/actions/analytics-actions.ts:97 | `vWA('MEMBER')` + chỉ xem chính mình trừ khi globalAdmin (dòng 99–100) | `workspaceId, userId` | Chi tiết lỗi theo từ điển lỗi của 1 user | ErrorDictionary, ErrorLog |
| `getUserPerformanceScore` | src/actions/analytics-actions.ts:145 | `vWA('MEMBER')` + self-check (dòng 147–148) | `workspaceId, userId` | Tính điểm/rank hiệu suất 1 user | Task, ErrorLog |
| `getStaffErrorLogsDetail` | src/actions/analytics-actions.ts:201 | `vWA('MEMBER')` + self-check (dòng 203–204) | `workspaceId, userId` | Log lỗi nhóm theo task (kèm client/project) | ErrorLog (join Task, Client, Project, User) |
| `removeErrorLog` | src/actions/analytics-actions.ts:261 | `vWA('ADMIN')` (dòng 263) | `workspaceId, errorLogId` | Xoá 1 dòng ErrorLog | ErrorLog |

## 4. `src/actions/audit-actions.ts` (203 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getWorkspaceAuditLogs` | src/actions/audit-actions.ts:49 | `vWA('ADMIN')` (dòng 55) | `workspaceId, filters, page, pageSize` | Đọc audit log phân trang, redact key nhạy cảm (password/token…) | AuditLog (join User actor) |
| `getAuditLogActionTypes` | src/actions/audit-actions.ts:163 | `vWA('ADMIN')` (dòng 164) | `workspaceId` | Danh sách distinct action cho dropdown filter | AuditLog |
| `getAuditLogActors` | src/actions/audit-actions.ts:180 | `vWA('ADMIN')` (dòng 181) | `workspaceId` | Danh sách distinct actor cho dropdown filter | AuditLog (join User) |

## 5. `src/actions/auth-actions.ts` (420 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `loginAction` | src/actions/auth-actions.ts:168 | **Public by design** — thay guard bằng: rate-limit IP (`checkLoginIp`, dòng 210), lockout 5-fail/15' (dòng 253), padding delay chống timing, anti-enumeration, chặn role LOCKED/CLIENT, validate `?next=` chống open-redirect | `formData(emailOrUsername, password, rememberMe, next)` | Đăng nhập email/username → set JWT session + redirect vào workspace | User, LoginAttempt, AuditLog, ProfileAccess, Workspace |
| `logoutAction` | src/actions/auth-actions.ts:404 | `getSession` (best-effort) | — | Bump `sessionVersion` (revoke JWT ở thiết bị khác) + clear cookie + redirect /login | User |

## 6. `src/actions/availability-actions.ts` (279 dòng)

⚠️ 3 hàm self-service dùng **helper cục bộ** `ensureWorkspaceAccess` (dòng 22: WorkspaceMember row HOẶC cùng profileId) thay vì `verifyWorkspaceAccess` — một phiên bản check membership thứ hai tồn tại song song trong repo.

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getMyAvailability` | src/actions/availability-actions.ts:44 | `getCurrentUser` + local `ensureWorkspaceAccess` (dòng 49) | `dateKey, workspaceId` | Đọc lịch rảnh 24h của chính mình | DailyAvailability, WorkspaceMember, Workspace |
| `getMyAvailabilityWeek` | src/actions/availability-actions.ts:73 | như trên (dòng 78) | `dateKey, workspaceId` | Đọc lịch rảnh cả tuần của chính mình | DailyAvailability |
| `saveMyAvailability` | src/actions/availability-actions.ts:111 | như trên (dòng 117) + chặn sửa quá khứ | `dateKey, schedule[24], workspaceId` | Upsert lịch rảnh ngày (chỉ của chính mình) | DailyAvailability, User |
| `getAdminAvailabilityMatrix` | src/actions/availability-actions.ts:163 | `vWA('ADMIN')` (dòng 166) | `dateKey, workspaceId` | Ma trận lịch rảnh mọi user trong profile (1 ngày) | Workspace, User, DailyAvailability |
| `getAdminAvailabilityWeek` | src/actions/availability-actions.ts:216 | `vWA('ADMIN')` (dòng 219) | `dateKey, workspaceId` | Ma trận lịch rảnh mọi user (cả tuần) | Workspace, User, DailyAvailability |

## 7. `src/actions/bonus-actions.ts` (452 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getPayrollLockStatus` | src/actions/bonus-actions.ts:38 | **KHÔNG CÓ GUARD** — vào thẳng `getWorkspacePrisma(workspaceId)` không session/role check | `workspaceId` | Đọc trạng thái khoá kỳ lương (`isLocked`) | Workspace, PayrollLock |
| `revertMonthlyBonus` | src/actions/bonus-actions.ts:63 | `vWA('ADMIN')` (dòng 66) | `workspaceId` | Hoàn tác thưởng: xoá MonthlyBonus/MonthlyRank/PayrollLock của kỳ | Workspace, MonthlyBonus, MonthlyRank, PayrollLock, AuditLog |
| `calculateMonthlyBonus` | src/actions/bonus-actions.ts:118 | `vWA('ADMIN')` (dòng 123) | `workspaceId` | Tính xếp hạng + thưởng Top1-3 theo BonusConfig, ghi bonus/rank + khoá kỳ (advisory lock + tx) | Workspace, Task, ErrorLog, User, BonusConfig, MonthlyBonus, MonthlyRank, PayrollLock, AuditLog |

## 8. `src/actions/bonus-config-actions.ts` (134 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getBonusConfig` | src/actions/bonus-config-actions.ts:44 | `vWA('ADMIN')` (dòng 48) | `workspaceId` | Đọc cấu hình % thưởng Top1-3 của team (default nếu chưa lưu) | Workspace, BonusConfig |
| `updateBonusConfig` | src/actions/bonus-config-actions.ts:72 | `vWA('ADMIN')` (dòng 78) | `workspaceId, BonusConfigDTO` | Validate + upsert BonusConfig theo profile | Workspace, BonusConfig, AuditLog |

## 9. `src/actions/bulk-task-actions.ts` (864 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `createBatchTasks` | src/actions/bulk-task-actions.ts:37 | `vWA('ADMIN')` (dòng 66 — sau vài validate thuần input) | `BatchTaskInput{titles[],…}, workspaceId` | Tạo N task trong 1 transaction (validate assignee/client thuộc profile) + notify | Task, TaskTag, User, Client, Notification |
| `bulkDeleteTasks` | src/actions/bulk-task-actions.ts:225 | `vWA('ADMIN')` (dòng 229) | `taskIds[], workspaceId` | Xoá cứng nhiều task (deleteMany, scope workspaceId) | Task |
| `bulkUpdateTaskDetails` | src/actions/bulk-task-actions.ts:252 | `vWA('ADMIN')` (dòng 256) | `taskIds[], data, workspaceId` | Sửa hàng loạt field có mặt trong `data` (dirty-tracking) + invariant assignee↔status, status↔deadline | Task, AuditLog |
| `bulkUpdateTaskResourceSubfields` | src/actions/bulk-task-actions.ts:369 | `vWA('ADMIN')` (dòng 377) | `taskIds[], subfields, workspaceId` | Merge từng subfield trong chuỗi packed `resources`/`references` per-task | Task, AuditLog |
| `bulkUpdateTaskStatus` | src/actions/bulk-task-actions.ts:483 | `vWA('ADMIN')` (dòng 502) + validate status + FSM per-task | `taskIds[], newStatus, workspaceId` | Đổi status hàng loạt (skip task fail FSM) + digest email 1/người nhận | Task, User, AuditLog |
| `bulkAssignTasks` | src/actions/bulk-task-actions.ts:667 | `vWA('ADMIN')` (dòng 671, gọi lại dòng 736) | `taskIds[], assigneeId, workspaceId` | Giao/bỏ giao hàng loạt (chặn Rank D, validate assignee thuộc profile) + notify | Task, MonthlyRank, User, Notification |
| `bulkUpdateStatus` | src/actions/bulk-task-actions.ts:788 | `vWA('ADMIN')` (dòng 802) + validate status | `taskIds[], newStatus, workspaceId` | Đổi status hàng loạt cho drag-and-drop board (KHÔNG check FSM — khác `bulkUpdateTaskStatus`) | Task, AuditLog |

## 10. `src/actions/claim-actions.ts` (260 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getMarketplaceStatus` | src/actions/claim-actions.ts:16 | `vWA('MEMBER')` (dòng 22, fail → trả `false`) | `workspaceId` | Đọc cờ mở/đóng phiên chợ | Workspace |
| `toggleMarketplace` | src/actions/claim-actions.ts:34 | `vWA('ADMIN')` (dòng 40) | `workspaceId` | Bật/tắt phiên chợ | Workspace |
| `getMarketplaceTasks` | src/actions/claim-actions.ts:67 | `vWA('MEMBER')` (dòng 70) | `workspaceId` | List task chưa giao (serialize CÓ CHỦ ĐÍCH bỏ jobPriceUSD — chỉ trả wage) | Task, Client, TaskTag |
| `claimTask` | src/actions/claim-actions.ts:128 | `getSession` (dòng 129) + `vWA('MEMBER')` (dòng 142) | `taskId, workspaceId` | Nhận task từ chợ — CAS theo `version` + re-check chợ mở trong tx | Workspace, Task |
| `returnTask` | src/actions/claim-actions.ts:213 | `vWA('MEMBER')` (dòng 217) + phải là người nhận + trong 10 phút | `taskId, workspaceId` | Hoàn task về pool trong 10 phút | Task |

## 11. `src/actions/client-request-actions.ts` (221 dòng)

Mọi hàm đi qua helper `adminCtx(workspaceId)` (dòng 18) → `verifyProfileAdminAccess` + resolve profileId.

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getClientRequests` | src/actions/client-request-actions.ts:48 | `vPAA` (qua adminCtx dòng 49) | `workspaceId, opts.includeResolved` | List yêu cầu của khách trong Hộp thư (mặc định NEW+REVIEWING) | ClientTaskRequest, Client |
| `getUnreadRequestCount` | src/actions/client-request-actions.ts:87 | `vPAA` (fail-soft trả 0) | `workspaceId` | Đếm request NEW cho badge sidebar | ClientTaskRequest |
| `acceptClientRequest` | src/actions/client-request-actions.ts:102 | `vPAA` (dòng 103) | `requestId, workspaceId` | Duyệt request → tạo Task thật (Đang đợi giao) + link ngược | ClientTaskRequest, Task, AuditLog |
| `rejectClientRequest` | src/actions/client-request-actions.ts:171 | `vPAA` (dòng 172) | `requestId, workspaceId, note?` | Từ chối request kèm note (sanitize) | ClientTaskRequest, AuditLog |
| `markRequestAccepted` | src/actions/client-request-actions.ts:200 | `vPAA` (dòng 201) | `requestId, workspaceId` | Đánh dấu ACCEPTED không tạo task (luồng Velox tự tạo N task) | ClientTaskRequest, AuditLog |

## 12. `src/actions/contact-actions.ts` (274 dòng)

Toàn bộ dùng helper `getAuthSession` (dòng 6: `getSession` + đòi `sessionProfileId`) — **không có role/workspace guard** (hệ contact là user-level, cross-profile theo thiết kế).

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `searchContacts` | src/actions/contact-actions.ts:14 | `getAuthSession` | `query` | Tìm user **TOÀN HỆ THỐNG** (mọi profile) theo username/nickname/**email**; response chứa email thật (dòng 44) | User, Contact, Profile |
| `sendContactRequest` | src/actions/contact-actions.ts:78 | `getAuthSession` | `receiverId` | Gửi lời mời kết bạn (PENDING) | Contact |
| `respondToContactRequest` | src/actions/contact-actions.ts:113 | `getAuthSession` + phải là receiver | `contactId, accept` | Chấp nhận/từ chối lời mời | Contact |
| `getContactRequests` | src/actions/contact-actions.ts:131 | `getAuthSession` | — | List lời mời PENDING đến mình | Contact, User, Profile |
| `getContacts` | src/actions/contact-actions.ts:161 | `getAuthSession` | — | List bạn bè ACCEPTED + presence | Contact, User, UserPresence |
| `getBlockedContacts` | src/actions/contact-actions.ts:199 | `getAuthSession` | — | List user mình đã block | Contact, User |
| `unblockContact` | src/actions/contact-actions.ts:228 | `getAuthSession` | `targetUserId` | Xoá record BLOCKED | Contact |
| `blockContact` | src/actions/contact-actions.ts:248 | `getAuthSession` | `targetUserId` | Set/tạo BLOCKED | Contact |

## 13. `src/actions/create-user.ts` (108 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `createUser` | src/actions/create-user.ts:17 | `vPAA` (dòng 24) + whitelist role USER/AGENCY_ADMIN + rate-limit `checkInviteCallerRate` khi có email (chống email-enumeration) | `formData(username,password,email?,displayName?,role), workspaceId` | Admin tạo user invite-only vào profile của creator (bcrypt hash) | User |

## 14. `src/actions/crm-actions.ts` (644 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getClients` | src/actions/crm-actions.ts:14 | `vFA` (dòng 23) | `workspaceId` | List client ACTIVE (kèm task/project count có finance scalar) | Client, Project, Task |
| `createClient` | src/actions/crm-actions.ts:113 | `vWA('ADMIN')` (dòng 116) | `{name, parentId?}, workspaceId` | Tạo client — dup-guard NFC + advisory lock per-profile | Client |
| `updateClient` | src/actions/crm-actions.ts:145 | `vWA('ADMIN')` (dòng 147) | `id, {name}, workspaceId` | Đổi tên client (dup-guard + lock) | Client |
| `createProject` | src/actions/crm-actions.ts:172 | `vWA('ADMIN')` (dòng 174) | `{name, clientId, code?}, workspaceId` | Tạo project gắn client (validate client thuộc profile) | Project, Client |
| `createFeedback` | src/actions/crm-actions.ts:211 | — (stub) | `_data` | **Stub deprecated** — trả error "Feature removed" | — |
| `deleteClient` | src/actions/crm-actions.ts:260 | `vWA('ADMIN')` (dòng 262) | `id, workspaceId` | Soft-delete cả subtree client vào Thùng rác (lock) | Client, AuditLog |
| `restoreClient` | src/actions/crm-actions.ts:297 | `vWA('ADMIN')` (dòng 299) | `id, workspaceId` | Khôi phục subtree từ Thùng rác (check trùng tên từng node trong lock) | Client, AuditLog |
| `getTrashedClients` | src/actions/crm-actions.ts:384 | `vWA('ADMIN')` (dòng 386) | `workspaceId` | List root soft-deleted cho Thùng rác | Client |
| `permanentlyDeleteClient` | src/actions/crm-actions.ts:417 | `vWA('ADMIN')` (dòng 419) | `id, workspaceId` | Xoá vĩnh viễn (chặn nếu còn invoice GLOBAL; project cascade, task detach) | Client, Invoice, AuditLog |
| `mergeClientIntoParent` | src/actions/crm-actions.ts:461 | `vWA('ADMIN')` (dòng 463) | `childId, parentId, workspaceId` | Gộp client root thành sub-client (dup-guard + re-read trong lock) | Client |
| `unmergeClient` | src/actions/crm-actions.ts:522 | `vWA('ADMIN')` (dòng 524) | `clientId, workspaceId` | Tách sub-client về root (dup-guard + lock — bảo vệ scope share-token theo name-path) | Client |
| `getClientDetail` | src/actions/crm-actions.ts:570 | `vFA` (dòng 577) | `clientId, workspaceId` | Chi tiết client đầy đủ finance (task, invoice, rating, donut) scope theo workspace | Client, Task, Invoice, Project, Rating, User |

## 15. `src/actions/cross-team-actions.ts` (240 dòng)

Cả 4 hàm dùng pattern: `getSession` + `isSessionLive` (chặn LOCKED/stale JWT) + `getProfileRole` làm authority check — không dùng vWA.

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `requestCrossTeamAccess` | src/actions/cross-team-actions.ts:11 | `getSession` + `isSessionLive` (dòng 19) + `getProfileRole(origin) ∈ {OWNER,ADMIN}` (dòng 43–45) | `userId, targetProfileId, workspaceId` | Admin team gốc gửi yêu cầu "du học" cho user (max 5 profile/user) | Profile, User, ProfileAccess, ProfileAccessRequest |
| `approveCrossTeamAccess` | src/actions/cross-team-actions.ts:94 | `getSession` + `isSessionLive` (dòng 100) + `getProfileRole(target) ∈ {OWNER,ADMIN}` (dòng 109–111) | `requestId, workspaceId` | Duyệt yêu cầu → upsert ProfileAccess vào team đích | ProfileAccessRequest, ProfileAccess |
| `rejectCrossTeamAccess` | src/actions/cross-team-actions.ts:137 | như approve (dòng 143, 149–151) | `requestId, workspaceId` | Từ chối yêu cầu du học | ProfileAccessRequest |
| `removeCrossTeamAccess` | src/actions/cross-team-actions.ts:169 | `getSession` + `isSessionLive` (dòng 178) + (profile OWNER/ADMIN HOẶC tự gỡ mình); chặn gỡ OWNER; ADMIN gỡ ADMIN phải là OWNER | `userId, profileId, workspaceId` | Gỡ quyền du học + xoá WorkspaceMember/invitation "ma" trong cùng tx | ProfileAccess, ProfileAccessRequest, WorkspaceMember, WorkspaceInvitation, Workspace |

## 16. `src/actions/email-migration-actions.ts` (288 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `requestEmailMigrationOtp` | src/actions/email-migration-actions.ts:57 | `getCurrentUser` (dòng 59) + chặn user đã migrate (dòng 68–75) + rate-limit `checkOtpIp`/`checkOtpEmail` | `newEmailRaw` | Gửi OTP 6 số tới email mới (purpose=EMAIL_MIGRATION, TTL 10') | User, PasswordResetOTP, AuditLog |
| `verifyEmailMigrationOtp` | src/actions/email-migration-actions.ts:171 | `getCurrentUser` (dòng 172) + verify OTP hash + max 5 attempt | `newEmailRaw, otpInput` | Atomic: check email không trùng → gán email + `emailVerified` + bump `sessionVersion` (force re-login) | PasswordResetOTP, User, AuditLog |

## 17. `src/actions/global-settings.ts` (84 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getFrameAccount` | src/actions/global-settings.ts:8 | `vAS` (dòng 13) + đòi WorkspaceMember role OWNER/ADMIN bất kỳ workspace HOẶC `sess.isAdmin` (dòng 22–28) | — | Đọc credential Frame.io dùng chung (lưu JSON trong Task ma `global-system-settings`.notes_vi) | WorkspaceMember, Task |
| `updateFrameAccount` | src/actions/global-settings.ts:54 | **CHỈ `vAS`** (dòng 57) — KHÔNG check role admin | `account, password` | Ghi đè credential Frame.io dùng chung toàn hệ thống | Task |

> ⚠️ **G-2 — Guard bất đối xứng:** đọc credential đòi OWNER/ADMIN (`global-settings.ts:22-28`) nhưng **ghi đè** chỉ cần một session active bất kỳ (`global-settings.ts:57`) — mọi user đăng nhập (kể cả USER thường không thuộc workspace nào) có thể overwrite/phá credential Frame.io chung. Credential lưu **plaintext JSON** trong bảng Task.

## 18. `src/actions/impersonation-actions.ts` (126 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `startImpersonation` | src/actions/impersonation-actions.ts:9 | `vWA('ADMIN')` (dòng 14) + target phải là member workspace này, không được OWNER, ADMIN chỉ OWNER mới đóng vai, chặn target có quyền admin ở tenant khác (dòng 41–74) | `targetUserId, workspaceId` | Tạo session đóng vai (cookie global) + audit + redirect | WorkspaceMember, Workspace, ProfileAccess, User, AuditLog |
| `stopImpersonation` | src/actions/impersonation-actions.ts:109 | `getSession` (tự thao tác trên session của mình) | `workspaceId` | Dừng đóng vai + audit + redirect về analytics | AuditLog |

## 19. `src/actions/integration-actions.ts` (125 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getConnectedIntegrations` | src/actions/integration-actions.ts:35 | `getSession` (dòng 37) — chỉ rows của chính mình, không trả token | `workspaceId` | List metadata OAuth integration (Dropbox/GDrive) của user | IntegrationToken |
| `disconnectIntegration` | src/actions/integration-actions.ts:74 | `vWA('MEMBER')` (dòng 76) — token key theo (userId, workspaceId, provider) | `workspaceId, provider` | Revoke token phía provider (best-effort) + xoá row | IntegrationToken |

Ghi chú: `refreshTokenIfNeeded` đã được DỜI sang `src/lib/integration-tokens.ts` (server-only, không còn là server action) — comment tại src/actions/integration-actions.ts:122-126.

## 20. `src/actions/invoice-actions.ts` (666 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getBillingProfiles` | src/actions/invoice-actions.ts:22 | `vFA` (dòng 36); từ chối nếu thiếu workspaceId | `workspaceId?` | List hồ sơ thanh toán (số TK ngân hàng, SWIFT) theo profile | BillingProfile, Workspace |
| `createBillingProfile` | src/actions/invoice-actions.ts:64 | `vWA('ADMIN')` (dòng 82) | `data{beneficiary, bank, accountNumber…}` | Tạo billing profile (auto unset default cũ) | BillingProfile, Workspace |
| `updateBillingProfile` | src/actions/invoice-actions.ts:127 | `vWA('ADMIN')` (dòng 145) + scope theo profile của workspace | `id, data, workspaceId?` | Sửa billing profile (chỉ trong profile mình) | BillingProfile, Workspace |
| `deleteBillingProfile` | src/actions/invoice-actions.ts:186 | `vWA('ADMIN')` (dòng 190) | `id, workspaceId?` | deleteMany scope profile (id lạ → no-op) | BillingProfile, Workspace |
| `getUnbilledTasks` | src/actions/invoice-actions.ts:215 | `vFA` (dòng 226) | `clientId, workspaceId` | List task UNBILLED của client + sub-clients (CÓ jobPriceUSD) | Client, Task |
| `calculateInvoicePreview` | src/actions/invoice-actions.ts:277 | `vFA` (dòng 285, fail → trả số 0) | `taskIds[], taxRate, depositCurrent, workspaceId` | Tính subtotal/tax/totalDue từ jobPriceUSD server-side | Task |
| `createInvoiceRecord` | src/actions/invoice-actions.ts:314 | `vFA` (dòng 361) | `data{invoiceNumber, items, taskIds…}, workspaceId` | Tx: tạo Invoice + claim task UNBILLED→INVOICED (atomic, chống double-billing) + trừ deposit (clamp) + email | Invoice, InvoiceItem, Task, Client, User |
| `getClientInvoices` | src/actions/invoice-actions.ts:536 | `vFA` (dòng 543) | `clientId, workspaceId` | List invoice của client + subs | Client, Invoice |
| `voidInvoice` | src/actions/invoice-actions.ts:581 | `vFA` (dòng 592) | `invoiceId, workspaceId` | Void invoice (advisory lock chống double-refund) + revert task + refund đúng phần deposit đã trừ | Invoice, Task, Client |

## 21. `src/actions/leaderboard-actions.ts` (9 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `refreshLeaderboardAction` | src/actions/leaderboard-actions.ts:5 | **KHÔNG CÓ GUARD** | — | `revalidateTag('leaderboard')` — chỉ purge cache, không đụng DB | — |

## 22. `src/actions/mc-task-drawer-actions.ts` (29 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `loadMcTaskDrawer` | src/actions/mc-task-drawer-actions.ts:12 | `vPAA` (dòng 17, fail-closed trả FORBIDDEN) | `workspaceId, taskId` | Load payload task drawer cho board Mission Control (qua builder chung `buildMcTaskDrawerData`) | Task + liên quan (qua `src/lib/mc-task-drawer-data`) |

## 23. `src/actions/member-actions.ts` (1380 dòng)

| Function | Vị trí | Guard | Input chính | Tác dụng | Model Prisma |
|---|---|---|---|---|---|
| `getWorkspaceMembers` | src/actions/member-actions.ts:127 | `vWA('MEMBER')` (dòng 128); email bị mask nếu caller không phải ADMIN+ (dòng 224–240) | `workspaceId` | List member = WorkspaceMember explicit ∪ user cùng profile (loại CLIENT/LOCKED) | Workspace, WorkspaceMember, User, ProfileAccess |
| `getWorkspaceInvitations` | src/actions/member-actions.ts:246 | `vWA('ADMIN')` (dòng 247) | `workspaceId` | List lời mời PENDING chưa hết hạn | WorkspaceInvitation, User |
| `getMyPendingInvitations` | src/actions/member-actions.ts:276 | `getSession` (dòng 278) | — | List lời mời PENDING của chính mình | WorkspaceInvitation, Workspace, User |
| `inviteToWorkspace` | src/actions/member-actions.ts:303 | `vWA('ADMIN')` (dòng 309) + rate-limit caller 40/h + per-target 5/24h + chặn mời ADMIN nếu không phải OWNER (dòng 335) + chặn LOCKED/CLIENT + consent `allowExternalInvites` | `workspaceId, targetUsername, role, message?` | Cùng profile → direct-add WorkspaceMember; khác profile → tạo/refresh WorkspaceInvitation + notify/email | User, Workspace, WorkspaceMember, WorkspaceInvitation, ProfileAccess, Notification, AuditLog |
| `acceptWorkspaceInvitation` | src/actions/member-actions.ts:617 | `getSession` (dòng 619) + re-assert account live: chặn LOCKED/CLIENT + sessionVersion (dòng 628–637) | `invitationId` | CAS accept (chống TOCTOU) → mint WorkspaceMember + ProfileAccess(USER/ADMIN theo lời mời); smart-fallback lời mời stale; idempotent khi đã là member | WorkspaceInvitation, WorkspaceMember, ProfileAccess, User, Notification, AuditLog |
| `declineWorkspaceInvitation` | src/actions/member-actions.ts:937 | `getSession` + re-assert live (dòng 946–955) + phải là invitee | `invitationId` | Đánh dấu DECLINED + notify inviter | WorkspaceInvitation, User, Notification |
| `revokeWorkspaceInvitation` | src/actions/member-actions.ts:1019 | `vWA('ADMIN')` (dòng 1020) | `workspaceId, invitationId` | Thu hồi lời mời PENDING | WorkspaceInvitation, AuditLog |
| `changeWorkspaceMemberRole` | src/actions/member-actions.ts:1054 | `vWA('ADMIN')` (dòng 1059–1060); đụng ADMIN/OWNER thì phải OWNER; chặn tự đổi; last-owner protection | `workspaceId, targetUserId, newRole` | Đổi role WorkspaceMember (OWNER phải qua transferOwnership) | WorkspaceMember, AuditLog |
| `removeWorkspaceMember` | src/actions/member-actions.ts:1132 | `vWA('ADMIN')` (dòng 1133–1134); gỡ OWNER/ADMIN cần OWNER; last-owner protection | `workspaceId, targetUserId` | Tx serialized (FOR UPDATE): xoá member + hard-delete invitation + revoke PA(USER) nếu cross-profile hết membership | WorkspaceMember, WorkspaceInvitation, ProfileAccess, Workspace, AuditLog |
| `leaveWorkspace` | src/actions/member-actions.ts:1247 | `vWA('MEMBER')` (dòng 1248) + last-owner protection | `workspaceId` | Tự rời workspace (mirror removeWorkspaceMember: xoá invitation + revoke PA cross-profile) | WorkspaceMember, WorkspaceInvitation, ProfileAccess, Workspace, AuditLog |
| `getAvailableUsersForInvite` | src/actions/member-actions.ts:1321 | `vWA('ADMIN')` (dòng 1322) | `workspaceId` | List user trong profile chưa là member (kèm email — caller đã là ADMIN) | Workspace, WorkspaceMember, User |

---

## Function KHÔNG có guard (hoặc guard yếu bất thường)

| # | Function | Vị trí | Mức độ | Chi tiết |
|---|---|---|---|---|
| G-1 | `getPayrollLockStatus` | src/actions/bonus-actions.ts:38 | Thấp-Trung | Không có bất kỳ session/role check nào — caller bất kỳ (kể cả chưa đăng nhập, vì server action là POST endpoint public) probe được trạng thái khoá kỳ lương của MỌI workspaceId. Chỉ lộ boolean `isLocked` nhưng là cross-tenant read không guard. |
| G-2 | `updateFrameAccount` | src/actions/global-settings.ts:54 | **Cao** | Chỉ `verifyActiveSession` — user đăng nhập BẤT KỲ ghi đè được credential Frame.io dùng chung toàn hệ thống (bất đối xứng với `getFrameAccount` vốn đòi OWNER/ADMIN ở dòng 22–28). Credential lưu plaintext JSON trong `Task.notes_vi` (row ma `global-system-settings`). |
| G-3 | `refreshLeaderboardAction` | src/actions/leaderboard-actions.ts:5 | Rất thấp | Không guard — chỉ `revalidateTag('leaderboard')`, không đọc/ghi dữ liệu; tối đa bị lạm dụng làm cache-bust spam. |
| G-4 | `createProfile` / `changeUserProfile` (stubs) | src/actions/admin-profile-actions.ts:24, :93 | — | Không guard nhưng throw ngay dòng đầu (deprecated stub Sprint Z) — dead-code candidate, nên xoá cùng `createFeedback` (src/actions/crm-actions.ts:211). |

## Ghi chú khác cho phase sau

1. **Hai phiên bản check membership tồn tại song song**: `verifyWorkspaceAccess` (src/lib/security) vs helper cục bộ `ensureWorkspaceAccess` tại src/actions/availability-actions.ts:22 (WorkspaceMember row HOẶC cùng profileId, không phân biệt role) — bản cục bộ chỉ dùng cho 3 hàm self-service availability, nhưng là logic authz trùng lặp cần hợp nhất.
2. **`searchContacts` (src/actions/contact-actions.ts:14) trả email thật của MỌI user toàn hệ thống** cho bất kỳ user đăng nhập nào (select `email: true` dòng 44, tìm cross-profile theo thiết kế hệ contact) — điểm enumeration email cần cân nhắc khi audit privacy.
3. **Hai luồng bulk-status khác mức kiểm soát**: `bulkUpdateTaskStatus` (src/actions/bulk-task-actions.ts:483) có FSM validate per-task; `bulkUpdateStatus` cho drag-drop (src/actions/bulk-task-actions.ts:788) chỉ validate status hợp lệ, KHÔNG check FSM transition — cùng chức năng, 2 mức chặt khác nhau.
4. `loginAction` public là chủ đích (endpoint đăng nhập) — bù bằng rate-limit Upstash + lockout + anti-enumeration + open-redirect guard (src/actions/auth-actions.ts:160-166, 210, 253).
5. Nhiều mutation quan trọng dùng **advisory lock Postgres** (`pg_advisory_xact_lock`) chống race: calculateMonthlyBonus (bonus-actions.ts:336), CRM name-lock (crm-actions.ts:107), voidInvoice (invoice-actions.ts:615), và `FOR UPDATE` trong remove/leave member (member-actions.ts:1217, :1291).
6. File deprecated một nửa: `admin-profile-actions.ts` (2/4 hàm là stub throw) — cần xác minh caller ở phase inventory UI trước khi xoá.

# §2 — Authorization / RBAC: Guard thật + Ma trận Role × Endpoint

> Phase 4 audit BẢO MẬT. Mọi kết luận kèm `file:line` đã **mở code thật xác minh** (không lấy nguyên từ discovery). Ngày audit: 2026-08-02, worktree `cranky-austin`.
> Nguồn bản đồ: `00-discovery/parts/04,05,06,07,09,10`. Guard cốt lõi đã đọc trực tiếp: `src/lib/security.ts`, `src/lib/review/access.ts`, `src/lib/review/share-auth.ts`, `src/lib/profile-permissions.ts`.

---

## PHẦN A — Các guard THẬT (chặn gì, ở đâu)

Hệ thống KHÔNG có bảng `Permission`. Toàn bộ phân quyền là **role-check trong code** qua 3 tầng role (Global `UserRole`, Profile `ProfileRole`, Workspace `WorkspaceRole` String) + 2 hệ token khách. Middleware **không** enforce role (chỉ auth-gate `/admin`+`/dashboard`, đá CLIENT — `src/middleware.ts:71-100`); mọi authz thật nằm ở **layout + DAL guard bên trong handler/action** (chống CVE-2025-29927 vì `/api` không qua middleware).

| Guard | File:line | Chặn gì / logic đã verify |
|---|---|---|
| `getSession()` | `src/lib/auth.ts:65-74` | Decrypt cookie `session` (JWT HS256 `jose`). **Không chạm DB, không check sessionVersion** (Edge-cheap). Chỉ xác nhận "có JWT hợp lệ" — KHÔNG phải authz. |
| `verifyActiveSession()` | `src/lib/security.ts:217-280` | DAL gate cho READ/layout (React `cache`). DB re-check: `role==='LOCKED'`→`locked`; `tokenVersion < dbVersion`→`locked`; else `active`. **`isAdmin` trả về = CHỈ `isTreasurer`** (`:278`) — super-admin đã gỡ. Không scope theo workspace. |
| `verifyWorkspaceAccess(wsId, role='MEMBER')` | `src/lib/security.ts:38-165` | Guard mutation chống BOLA/IDOR. Chuỗi verify: session (`:56`) → DB user LOCKED (`:67`) → **sessionVersion** (`:79`, chặn token cũ sau reset/logout-all) → workspace tồn tại (`:88`) → ProfileAccess: `OWNER`⇒workspaceRole OWNER (`:103`); `ADMIN` **chỉ nếu `workspace.createdAt >= grantedAt`**⇒ADMIN (`:106`), ngược lại rơi xuống fallback MEMBER; **`CLIENT`⇒fail-closed TRƯỚC WorkspaceMember** (`:109-119`, fix PE-1 HIGH); else explicit `WorkspaceMember` row (type-guard `isWorkspaceRole` `:127`, role lạ→throw); else profile-member fallback `MEMBER` (`:132-142`). So `hasAtLeastRole(role,required)` (`:150`). `isGlobalAdmin` **luôn false** (`:163`). |
| `verifyProfileAdminAccess(wsId)` | `src/lib/security.ts:180-191` | Predicate CHUẨN & DUY NHẤT cho admin/finance. `ok = workspaceRole∈{OWNER,ADMIN} OR profileRole∈{OWNER,ADMIN}` (`:184-186`). Cố ý KHÔNG dùng `isTreasurer` (chống leak cross-tenant R7/R8). **Khác biệt tinh tế:** profile-ADMIN trên workspace CŨ (created < grantedAt) chỉ được `verifyWorkspaceAccess('ADMIN')` từ chối (xuống MEMBER) nhưng **vẫn pass** hàm này vì check `profileRole==='ADMIN'`. |
| `verifyFinanceAccess(wsId)` | `src/lib/security.ts:203-207` | Alias delegate 100% sang `verifyProfileAdminAccess` — thống nhất finance VIEW = WRITE trên 1 predicate profile-scoped. |
| `isSessionLive(session)` | `src/lib/profile-permissions.ts:46-56` | Liveness re-check nhẹ (DB: LOCKED + sessionVersion) cho các action chỉ auth bằng `getSession()` mà KHÔNG qua `verifyWorkspaceAccess` (profile-member, cross-team, share-link admin). |
| `requireReviewAccess(opts)` | `src/lib/review/access.ts:32-70` | Guard module review (staff). `getSession()`→401 nếu chưa login (`:38`); chặn `LOCKED`/`CLIENT`→403 (`:41`); `opts.admin`⇒đòi **GLOBAL** `role==='ADMIN'` (`:44`); `opts.workspaceId`⇒delegate `verifyWorkspaceAccess(wsId,'MEMBER')` và **`isAdmin` trả về là WORKSPACE-scoped** (OWNER/ADMIN của workspace/profile — KHÔNG phải JWT role, `:56-61`). Guest KHÔNG BAO GIỜ qua hàm này. |
| `requireShare(slug, cookies)` | `src/lib/review/share-auth.ts:93-109` | Gate `/api/r/*`. Chuỗi hợp đồng: `not_found`→404, `revoked`→410, `expired`→410, `password`→401; **message not_found ≡ revoked** (anti-enumeration `:99-103`). Slug regex `^[A-Za-z0-9_-]{8,24}$` trước khi chạm DB (`resolveShareGate:77`). Password: cookie `rv_unlock_{slug}` JWT bind fingerprint passwordHash (`:82-84`). |
| `resolveShareToken(token)` | `src/lib/share-link-auth.ts:73-281` | Chokepoint `/share/*` + mọi `share-portal-actions`. Token = credential DUY NHẤT (không session/password). SHA-256 hash-at-rest; **uniform 404** mọi nhánh từ chối (chống enumeration); rate-limit 2 tầng (per-IP 240/min trước lookup, per-token-hash 2000/min sau). Scope = client theo **name-path segments** trong profile + mọi workspace của profile. |
| Predicates profile | `src/lib/profile-permissions.ts:71-105` | `canCreateWorkspace`/`canInviteMember`/`canManageShareLinks` = OWNER∨ADMIN; `canRemoveMember`/`canChangeMemberRole`/`canTransferOwnership` = **OWNER-only**. Dùng bởi CREATE gates thay vì workspaceRole. |
| `startImpersonation` guard | `src/actions/impersonation-actions.ts:9-107` | 5 lớp: caller ≥ workspace-ADMIN; target là member đúng workspace; cấm impersonate OWNER; impersonate ADMIN thì caller phải OWNER; chặn target có OWNER/ADMIN ở tenant khác; cấm impersonate global `ADMIN`; TTL 2h; luôn audit. |

**Nhận xét cấu trúc quan trọng:**
1. Global `UserRole.ADMIN` **gần như chết** — `isGlobalAdmin` hard-code false (`security.ts:163`); chỉ còn 2 điểm dùng thật: `requireReviewAccess({admin:true})` (`access.ts:44`, **hiện KHÔNG có caller nào** — grep `admin:true` = 0 trong 63 route) và guard cấm-impersonate. Một global-ADMIN không có ProfileAccess/WorkspaceMember trên workspace đích bị chặn **y như USER**.
2. `isTreasurer` **không còn cấp quyền finance** (R7→R8) — `verifyFinanceAccess === verifyProfileAdminAccess`. Flag chỉ còn lộ ra `verifyActiveSession().isAdmin` (dùng cho vài UI + fallback đọc Frame credential).
3. Tồn tại **2 helper membership song song**: `verifyWorkspaceAccess` (chuẩn) và helper cục bộ `ensureWorkspaceAccess` (`src/actions/availability-actions.ts:22`, WorkspaceMember-row-HOẶC-cùng-profile, không phân role) — nợ hợp nhất.

---

## PHẦN B — Ma trận ROLE × ENDPOINT

**Cột role** (đánh giá theo *workspace/profile ĐÍCH* của request):

| Ký hiệu | Nghĩa |
|---|---|
| **G-ADM** | Global `UserRole.ADMIN` (không có ProfileAccess tới workspace đích) — thực tế ≈ USER vì `isGlobalAdmin=false` |
| **P-OWN** | Profile OWNER của profile chứa workspace đích |
| **P-ADM** | Profile ADMIN (workspace mới hơn grantedAt ⇒ full; cũ hơn ⇒ chỉ pass các gate dùng `verifyProfileAdminAccess`, KHÔNG pass `vWA('ADMIN')`) |
| **USER** | Profile USER / workspace MEMBER thường (staff-editor) |
| **WS-GST** | WorkspaceMember role `GUEST` (weight thấp nhất < MEMBER) |
| **CLIENT** | Khách qua token `/share/[token]` (ClientShareLink) |
| **GUEST** | Khách qua token `/r/[slug]` (ShareLink review) |
| **CRON** | Vercel Cron mang `CRON_SECRET` |
| **PUB** | Không xác thực (không cookie, không token) |

**Ký hiệu ô:** ✓ gọi được · ✗ bị guard chặn · — không áp dụng/không phải bề mặt của role đó · ⚠ gọi được nhưng có lỗ hổng (xem Phần C).

### B1. Auth (`/api/auth/*`, `auth-actions`) — public by design + credential-là-guard

| Endpoint | G-ADM | P-OWN | P-ADM | USER | WS-GST | CLIENT | GUEST | CRON | PUB | Guard thật |
|---|---|---|---|---|---|---|---|---|---|---|
| POST `/api/auth/signup` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | BotID+rate+honeypot, luôn 200 (`signup-actions.ts:107`) |
| POST `/api/auth/forgot-password` · verify-otp · reset-password | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | OTP/token là credential, rate-limit (`password-reset-actions.ts`) |
| GET/POST `/api/auth/verify-email` | — | — | — | — | — | — | — | — | ✓ | token hash one-time (`verify-email/route.ts:38-48`) |
| GET `/api/auth/google/authorize`·callback | — | — | — | — | — | — | — | — | ✓ | CSRF state cookie + email verified + chặn LOCKED/CLIENT (`callback:38,49,66`) |
| GET `/api/auth/role` · logout | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(CLIENT đá) | — | — | ✗ | decrypt session của chính mình |
| `loginAction` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ (role CLIENT/LOCKED bị chặn) | — | — | ✓ | rate-limit IP+lockout+anti-enum (`auth-actions.ts:168`) |

### B2. Cron (`/api/cron/*`) — chỉ CRON_SECRET

| Endpoint | CRON | PUB / mọi role người dùng | Guard thật |
|---|---|---|---|
| `auth-cleanup` | ✓ | ✗ | **`timingSafeEqual`** (`auth-cleanup/route.ts:37`) — chuẩn duy nhất đúng |
| `check-deadline` (ghi `status='Quá hạn'`) | ✓ | ✗ | `key !== secret` **thường** (`check-deadline/route.ts:28`) ⚠ SEC2-07 |
| `send-digest` · `cleanup-notifications` · `hard-delete-workspaces` · `hard-delete-profiles` · `review-janitor` | ✓ | ✗ | `key !== secret` thường ⚠ SEC2-07 |

> Cả 7 cron chặn PUB/mọi role (không có CRON_SECRET → 401). Chỉ khác nhau ở cách so sánh secret. `check-deadline` là cron DUY NHẤT ghi đè dữ liệu nghiệp vụ.

### B3. Webhooks / Inngest / integrations

| Endpoint | Guard thật | PUB | Ghi chú |
|---|---|---|---|
| POST `/api/webhooks/mux` | HMAC-SHA256 `Mux-Signature` ±5' `timingSafeEqual`, fail-closed 401 (`mux/route.ts:23-58`) + ledger idempotent | ✗ | Đúng chuẩn |
| POST `/api/webhooks/calendar` | **KHÔNG verify** (comment out `:10-11`), log payload, trả success (`calendar/route.ts:8-45`) | ⚠✓ | SEC2-05 — cửa mở (hiện inert, không ghi DB) |
| GET/POST/PUT `/api/inngest` | Inngest tự verify `INNGEST_SIGNING_KEY` | ✗ | |
| GET `/api/integrations/{dropbox,google-drive}/authorize`·callback | `getSession()` + callback so `state.userId===session.user.id` (`dropbox/callback:61-67`) | ✗ | state base64url không ký (comment sai "encrypted") nhưng callback ràng session |
| POST `/api/integrations/scan-folder` | `getSession()`+`vWA('MEMBER')`+limitDb 10/60s (`scan-folder/route.ts:62,101,116`) | ✗ | |

Role người dùng cho integrations: bất kỳ session sống (không LOCKED) đều `authorize`/`scan-folder` được (scan cần MEMBER trên workspace đó). CLIENT bị `vWA` chặn.

### B4. Share khách `/api/share/*` + portal-notify + notifications (token/credential)

| Endpoint | CLIENT (token đúng) | PUB (không token) | USER/staff | Guard thật |
|---|---|---|---|---|
| GET `/api/share/[token]/download-zip` | ✓ | ✗ (404) | — | `resolveShareToken`+limitDb 12/600s fail-closed (`download-zip/route.ts:91,98`) |
| GET `/api/share/[token]/invoices/[id]/pdf` | ✓ (nếu invoice ∈ scope) | ✗ | — | `resolveShareToken`+predicate clientId∈scope∧workspaceId∈scope (`:76-83`), fail 404 đồng nhất |
| GET `/api/notifications/unsubscribe?token=` | — | ⚠✓ (token đúng) | ✓ | `verifyUnsubscribeToken`; **GET MUTATE** (`route.ts:70-80`) ⚠ SEC2-10 |
| POST/GET `/api/portal-notify/unsubscribe` | — | ✓ (token) | ✓ | GET không mutate (đã vá P4-R4); token verify trong action |

### B5. Invoices / Exports (staff finance)

| Endpoint / Action | G-ADM | P-OWN | P-ADM | USER | WS-GST | CLIENT | Guard thật |
|---|---|---|---|---|---|---|---|
| POST `/api/invoices/generate` | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | `verifyFinanceAccess` (`generate/route.ts:17`) |
| GET `/api/invoices/[id]/download` | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | `verifyFinanceAccess`+IDOR workspaceId (`download/route.ts:23,49-52`) |
| GET `/api/exports/monthly-tasks-xlsx` | ✗ | ✓ | ✓* | ✗ | ✗ | ✗ | `vWA('ADMIN')`+chặn cross-profile (`route.ts:103,120`) — *P-ADM chỉ workspace mới hơn grantedAt |

### B6. Server actions — Task lifecycle (trục xương sống)

| Action | G-ADM | P-OWN | P-ADM | USER | WS-GST | CLIENT | Guard thật |
|---|---|---|---|---|---|---|---|
| `createTask` (`admin-actions.ts:85`) | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | `vWA('ADMIN')` |
| `updateTaskStatus` (`task-actions.ts:17`) | ✗ | ✓ | ✓ | ✓ (chỉ task của mình, chặn terminal/client-phase) | ✗ | ✗ | `getCurrentUser`+`vWA('MEMBER')`+FSM+optimistic lock |
| `assignTask` (`task-management-actions.ts:118`) | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | `vWA('ADMIN')`+assignee∈profile (R14) |
| `updateTask` (generic `task-management-actions.ts:35`) | ✗ | ✓ | ✓ | ✓ (chỉ task mình + strip money/tenancy/status) | ✗ | ✗ | `vWA('MEMBER')`+field-strip R3/R5/HT-007 |
| `updateTaskDetails` (`update-task-details.ts:22`) | ✗ | ✓ | ✓ | ✓ (chỉ task được giao, chỉ productLink+notes_en) | ✗ | ✗ | `vWA('MEMBER')`+sanitize URI+money ADMIN-only+chặn payroll PAID |
| `deleteTask` HARD (`task-management-actions.ts:12`) | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | `vWA('ADMIN')` |
| `bulkDeleteTasks`·`bulkUpdateTaskStatus`·`bulkAssignTasks`·`createBatchTasks`·`createTasksFromBatch` | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | `vWA('ADMIN')` (`bulk-task-actions.ts`, `velox-batch-actions.ts:102`) |
| `claimTask`·`returnTask`·`getMarketplaceTasks` | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | `vWA('MEMBER')` + CAS version (`claim-actions.ts`) |
| `getCancelledTasks`·`restoreCancelledTask` | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | `vWA('ADMIN')` |

### B7. Payroll / Bonus / Payment / Finance-config

| Action | P-OWN | P-ADM | USER | PUB/anon | Guard thật |
|---|---|---|---|---|---|
| `confirmPayment`·`revertPayment`·`getPayrollData` (`payroll-actions.ts`) | ✓ | ✓ | ✗ | ✗ | `vWA('ADMIN')`+PayrollLock guard |
| `calculateMonthlyBonus`·`revertMonthlyBonus`·`getBonusConfig`·`updateBonusConfig` | ✓ | ✓ | ✗ | ✗ | `vWA('ADMIN')` (`bonus-actions.ts`, `bonus-config-actions.ts`) |
| **`getPayrollLockStatus`** (`bonus-actions.ts:38`) | ✓ | ✓ | ✓ | ⚠✓ | **KHÔNG guard** — `getWorkspacePrisma` thẳng, cross-tenant read boolean ⚠ SEC2-08 |
| `recordPayment`·`deletePayment`·`getPaymentLedger`·`getClientPayments` (`payment-actions.ts`) | ✓ | ✓ | ✗ | ✗ | `vWA('ADMIN')`+scope |
| `getClients`·`getClientDetail`·`getUnbilledTasks`·`calculateInvoicePreview`·`createInvoiceRecord`·`voidInvoice`·`getBillingProfiles` | ✓ | ✓ | ✗ | ✗ | `verifyFinanceAccess` (`crm-actions`, `invoice-actions`) |
| `createBillingProfile`·`updateBillingProfile`·`deleteBillingProfile` | ✓ | ✓ | ✗ | ✗ | `vWA('ADMIN')` |
| `getTemplates`/`listPricingRules` | ✓ | ✓ | ✓ (strip `*USD*`) | ✗ | `vWA('MEMBER')`+strip giá non-admin (R11/R12) |
| `create/update/delete PricingRule`·`PriceTemplate` | ✓ | ✓ | ✗ | ✗ | `vWA('ADMIN')` |

### B8. Member / Invite / Profile-member / Impersonation

| Action | P-OWN | P-ADM | USER | Guard thật |
|---|---|---|---|---|
| `inviteToWorkspace` (`member-actions.ts:303`) | ✓ | ✓ (chỉ OWNER mới mời được ADMIN) | ✗ | `vWA('ADMIN')`+rate+consent |
| `changeWorkspaceMemberRole`·`removeWorkspaceMember` | ✓ | ✓ (đụng OWNER/ADMIN cần OWNER) | ✗ | `vWA('ADMIN')`+last-owner protection |
| `revokeWorkspaceInvitation`·`getWorkspaceInvitations`·`getAvailableUsersForInvite` | ✓ | ✓ | ✗ | `vWA('ADMIN')` |
| `acceptWorkspaceInvitation`·`declineWorkspaceInvitation`·`leaveWorkspace` | ✓ | ✓ | ✓ (self, re-assert live) | `getSession`+live |
| `inviteToProfileAction`·`removeFromProfileAction`·`changeProfileRoleAction`·`transferProfileOwnershipAction`·`grantWorkspaceAccessToAdmin` | ✓ (OWNER-only cho các thao tác nhạy cảm) | phần lớn ✗ (OWNER-only) | ✗ | `getSession`+`isSessionLive`+OWNER predicate (`profile-member-actions.ts`) |
| `createUser` (`create-user.ts:17`) | ✓ | ✓ | ✗ | `verifyProfileAdminAccess`+whitelist role USER/AGENCY_ADMIN |
| `updateUserRole`·`deactivateUser`·`reactivateUser`·`triggerForcePasswordReset` (`user-actions`) | ✓ | ✓ | ✗ | `vWA('ADMIN')`+tenancy+OWNER-symmetric (R10-R13) |
| `startImpersonation` (`impersonation-actions.ts:9`) | ✓ | ✓ (ADMIN chỉ impersonate được khi caller OWNER) | ✗ | `vWA('ADMIN')`+5 lớp chặn+audit |
| `toggleTreasurer` (`toggle-treasurer.ts:7`) | ✓ | ✗ (**WS:OWNER-only**) | ✗ | `vWA('OWNER')`+cấm self |
| `requestCrossTeamAccess`·`approveCrossTeamAccess`·`removeCrossTeamAccess` | ✓ | ✓ | ✗ (trừ tự-gỡ mình) | `getSession`+`isSessionLive`+`getProfileRole∈{OWNER,ADMIN}` |

### B9. Review module — staff `/api/review/*` (63 route, auth ở service-layer)

Mọi route: `withReviewRoute` (error-boundary) → service tự re-derive `workspaceId` từ row → `requireReviewAccess({workspaceId})`. Cột: quyền theo workspace đích.

| Nhóm route (đại diện) | G-ADM | P-OWN | P-ADM | USER | CLIENT | GUEST | Guard thật |
|---|---|---|---|---|---|---|---|
| tree·folders·items·assets·versions·comments (đa số) | ✗ | ✓ | ✓ | ✓ (folder-scope FR-03: chỉ task được giao / folder mình tạo) | ✗ (role CLIENT bị `requireReviewAccess` chặn) | ✗ | `requireReviewAccess({workspaceId})` + `assertVersionInScope` |
| POST `items/delete` (creator guard FR-B07) | ✗ | ✓ | ✓ | ✓ (chỉ item mình tạo trừ khi admin) | ✗ | ✗ | +`isAdmin` workspace-scoped (`folders.ts:829`) |
| POST `trash/purge` (xoá vĩnh viễn) | ✗ | ✓ | ✓ | ✗ (**admin-only**) | ✗ | ✗ | `purgeItemsAuthorized` chặn non-admin (`purge.ts:389-390`) |
| PUT `assets/[id]/status` | ✗ | ✓ | ✓ | ✓ (folder-scope write) | ✗ | ✗ | `setAssetStatus` (`status.ts:44-47`) |
| POST `assets/[id]/feedback-done` (F8) | ✗ | ✓ | ✓ | ✗ (**admin-only**) | ✗ | ✗ | `markFeedbackDone` (`task-sync.ts:274`) |
| POST `assets/[id]/confirm-fix` (F9) | ✗ | ✓ | ✓ | ✓ (admin HOẶC assignee) | ✗ | ✗ | `confirmFixDone` (`task-sync.ts:300-301`) |
| POST `assets/[id]/approve-send` (F10, gửi khách) | ✗ | ✓ | ✓ | ✗ (**admin-only**) | ✗ | ✗ | `approveInternalAndSendToClient` (`task-sync.ts:381`) |
| GET/POST `shares*` (tạo/list/detail) | ✗ | ✓ | ✓ | ✓ (list chỉ thấy link mình tạo / task mình) | ✗ | ✗ | `requireReviewAccess`+scope (`shares.ts:198,562`) |
| PATCH/DELETE/revoke `shares/[id]` | ✗ | ✓ | ✓ | ✓ (chỉ creator) / ✗ (delete = admin-only) | ✗ | ✗ | `requireShareManageAccess`: creator∨workspace-admin (`shares.ts:737,773`) |
| GET `/api/review/statuses` (dropdown) | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | session-only (chưa có tài nguyên đích, `status.ts:23`) |
| POST `comment-attachments/initiate` | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | session-only (chưa gắn version, `comments.ts:558`) |

> `requireReviewAccess({admin:true})` (gate theo GLOBAL `UserRole.ADMIN`) **không có caller nào** trong 63 route. 3 gate admin thật đều dùng `isAdmin` **workspace-scoped**.

### B10. Review module — guest `/api/r/*` (19 route, token slug + gate chain)

Mọi route (trừ `unsubscribe`): `withShareRoute` + `limitDb(slug+IP)` + `requireShare(slug,cookies)` TRƯỚC. Cột GUEST = có slug hợp lệ + qua gate.

| Route | GUEST | PUB (slug sai/revoked) | Staff/CLIENT | Guard thật |
|---|---|---|---|---|
| GET `/api/r/[slug]` (nội dung DTO) | ✓ | ✗ (404/410) | — | `requireShare`; DTO cắt gọt (không workspace/task/email) |
| POST `/api/r/[slug]/unlock` | ✓ | ✗ | — | 5/60s **failClosed**+bcrypt (`unlock/route.ts:25,44`) |
| POST `/api/r/[slug]/identity` | ✓ | ✗ | — | tạo GuestSession, cookie chỉ trả name |
| POST `/api/r/[slug]/playback-token`·view-url·download-url | ✓ (∈ScopeItem) | ✗ | — | `assertVersionInShare`; download gate `allowDownload && (!downloadOnlyWhenApproved‖APPROVED)` (`download-url:30,44`) |
| GET/POST comments·reactions·attachments | ✓ (isInternal=false ép SQL; write cần `resolveGuestForWrite`) | ✗ | — | `requireShare`+identity; comment nội bộ KHÔNG BAO GIỜ lộ |
| PATCH/DELETE `/api/r/[slug]/comments/[id]` | ✓ (chỉ comment CỦA guest đó, `getGuestSession` bắt buộc) | ✗ | — | 401 nếu cookie chết; service so khớp GuestSession sở hữu |
| POST `/api/r/[slug]/decision` (approve/request-changes) | ✓ (identity bắt buộc; asset phải có taskId ở client-facing phase) | ✗ | — | `submitGuestDecision` (`share-decision.ts:127,137-186`); PIN được waive (chủ dự án), synthetic email không tính verified |
| POST `notifications/request-pin`·verify-pin | ✓ | ✗ | — | luôn 200 neutral, rate-limit đa tầng, cap 5 sai |
| POST/GET `/api/r/unsubscribe?token=` | — | ✓ (token là auth) | — | opaque unsub-token; GET không mutate |

### B11. Client portal actions `share-portal-actions.ts` (21 action, token = credential)

Không session. Mọi action re-resolve `resolveShareToken`; authz = `clientId∈scope.clientIds ∧ workspaceId∈scope.workspaceIds` (`findScopedTask:480`).

| Action (đại diện) | CLIENT (token) | PUB (không token) | Staff | Guard/note |
|---|---|---|---|---|
| `getShareSnapshot`·`getSubmitOptionsViaToken`·`getActivityViaToken`·`getCommentFeedViaToken` (đọc) | ✓ | ✗ | — | token+scope; **jobPriceUSD CÓ** (chủ đích owner), status nội bộ/assignee/notes_vi/frame credential bị strip |
| `approveDeliverableViaToken`·`approveDeliverablesViaToken`·`requestChangesViaToken` | ✓ (task ∈ scope + `isClientFacingPhase` gate) | ✗ | — | updateMany pin toàn bộ state+tenancy chống race (HT-006/014) |
| `submitRatingViaToken` | ✓ (task completed/APPROVED) | ✗ | — | Rating.taskId unique |
| `postCommentViaToken`·`toggleReactionViaToken` | ✓ (rate-limit) | ✗ | — | visibility **forced CLIENT** server-side |
| `submitClientRequestViaToken`·`createSubClientViaToken` | ✓ (rate-limit+advisory lock) | ✗ | — | tạo ClientTaskRequest / sub-brand an toàn concurrency |
| `requestPortalNotifyEmail`·`verifyPortalNotifyEmail`·`unsubscribePortalNotify` | ✓ (OTP/unsub-token) | ✗ | — | rate-limit theo inbox canonical |
| `createTaskViaToken` | ✓ | ✗ | — | **retained-but-unused** (v2 thay bằng submitClientRequest) — dead candidate |

### B12. Notifications / Tracking / Push / Misc actions

| Action | Session-user | PUB/anon | Guard thật |
|---|---|---|---|
| `getNotifications`·`markNotificationRead`·`archiveNotification`·`updateMyNotificationPreferences` | ✓ (self+ownership) | ✗ | session + ownership check |
| **`createNotificationInternal`·`createBulkNotificationsInternal`·`createAndBroadcastNotifications`** | ✓ | ⚠✓ | **KHÔNG session check** — export từ `'use server'`⇒public endpoint ⚠ SEC2-03 |
| `savePushSubscription`·`deletePushSubscription` | ✓ (self) | ✗ | session; `getVapidPublicKey` public vô hại |
| **`trackEvent`** (`tracking-actions.ts:58`) | ✓ | ⚠✓ | chỉ cần cookie `tracking_session_id` (client tự set) — unauth DB write ⚠ SEC2-06 |
| `forceFlush` (`tracking-actions.ts:29`) | ✓ | ⚠✓ | KHÔNG guard — chỉ flush buffer (rủi ro thấp) |
| `pingHeartbeat`·`getSessionTrends`·`getRecentEventLogs`·`getLivePresence` | ✓ (+chặn CLIENT) | ✗ | session+profile (R1 fix #16, HT-034) |
| `getFrameAccount` (`global-settings.ts:8`) | ✓ (OWNER/ADMIN membership HOẶC isTreasurer) | ✗ | `verifyActiveSession`+membership check |
| **`updateFrameAccount`** (`global-settings.ts:54`) | ⚠✓ (BẤT KỲ session active) | ✗ | **CHỈ `verifyActiveSession`** — không check admin ⚠ SEC2-02 |
| `searchContacts` (`contact-actions.ts:14`) | ✓ | ✗ | `getAuthSession` — trả **email thật MỌI user toàn hệ thống** ⚠ SEC2-12 |
| `getWorkspacesForProfile` (`workspace-actions.ts:134`) | ⚠✓ (bất kỳ profileId) | ✗ | chỉ `getSession` — không kiểm access profile ⚠ SEC2-09 |
| `createWorkspaceAction`·`renameWorkspaceAction`·`deleteWorkspaceAction`·`restoreWorkspaceAction` | ✓ (OWNER/admin theo hàm) | ✗ | `canCreateWorkspace`/`vWA('ADMIN')`+OWNER |
| `toggleMobileView`·`setUiPref`·`refreshLeaderboardAction` | ✓ | ✓ | KHÔNG guard — cookie cá nhân / cache purge, vô hại |

### B13. Python orphan functions `api/*.py` (Vercel deploy qua `vercel.json:3-5`)

| Endpoint | CRON/auth | PUB | Guard thật |
|---|---|---|---|
| POST `/api/scoring` | ✓ (Bearer CRON_SECRET) | ✗ | `do_POST` check `Authorization: Bearer {CRON_SECRET}` (`api/scoring.py:11-19`) |
| GET `/api/vdownloader` | — | ⚠✓ | **`do_GET` KHÔNG có auth** (`api/vdownloader.py:45`) ⚠ SEC2-01 |

---

## PHẦN C — Findings: endpoint/action THIẾU guard hoặc guard yếu

| ID | Severity | Vị trí | Vấn đề |
|---|---|---|---|
| **SEC2-01** | **High** | `api/vdownloader.py:45` (+`vercel.json:3-5`) | `do_GET` không có bất kỳ xác thực nào (trái ngược `scoring.py:11-19` có Bearer CRON_SECRET). Bất kỳ ai `GET /api/vdownloader?url=<bất kỳ>` khiến server chạy `yt-dlp`+`subprocess`/ffmpeg tải URL tuỳ ý; nếu `YOUTUBE_COOKIES` được cấu hình thì cookie được ghi ra `/tmp` và gửi kèm request tới host do attacker chọn (rò rỉ credential / SSRF). `?diagnostic=true` lộ `os.getcwd()`+phiên bản Python (`:71-76`). Lạm dụng compute/bandwidth vô danh. |
| **SEC2-02** | **High** | `src/actions/global-settings.ts:54-84` | `updateFrameAccount` chỉ đòi `verifyActiveSession()` status `active` — KHÔNG check role. Mọi user đăng nhập (kể cả USER tự-signup không thuộc workspace nào) ghi đè được credential Frame.io **dùng chung toàn hệ thống**, lưu **plaintext JSON** trong `Task.notes_vi`. Bất đối xứng với `getFrameAccount` (đòi OWNER/ADMIN membership HOẶC isTreasurer, `:22-28`) — đọc thì siết, ghi thì mở. Vector phá hoại/chiếm credential. |
| **SEC2-03** | **Medium** | `src/actions/notification-actions.ts:24,70,86` | `createNotificationInternal`/`createBulkNotificationsInternal`/`createAndBroadcastNotifications` export từ file `'use server'` ⇒ Next đăng ký thành **Server Action endpoint public**, KHÔNG session check. Kẻ có action-id tạo được notification + **gửi email (Resend) + web-push** tới `userId` bất kỳ ⇒ spam/phishing qua kênh chính danh của hệ thống. Cùng lớp lỗi `integration-tokens.ts` đã vá (R4) — nên tách sang module `server-only`. |
| **SEC2-04** | **Medium** | `src/app/api/test-email/route.ts:17,28-34` | Guard CRON_SECRET nhưng chấp nhận secret qua **query string `?secret=`** ⇒ lọt vào access log / browser history / referrer. Response (kể cả trước khi gửi mail) lộ `RESEND_API_KEY` 6 ký tự đầu + trạng thái set/not-set của `JWT_SECRET`, `ADMIN_EMAIL`, v.v. File tự ghi "DELETE after debugging" (`:3`) nhưng vẫn deploy. |
| **SEC2-05** | **Medium** | `src/app/api/webhooks/calendar/route.ts:8-45` | Không có verification (dòng verify comment out `:10-11`). Nhận POST từ bất kỳ ai, `console.log` toàn bộ payload (`:21`), trả `{success:true}`. Hiện **inert** (logic tạo `ScheduleException` còn trong block comment TODO), nên tác động thực tế thấp — nhưng là cửa mở sẵn: ai hoàn thiện TODO mà quên guard sẽ cho attacker tạo `ScheduleException` tuỳ ý. Không file nào trong `src/` tham chiếu URL này ⇒ nên gỡ hoặc hoàn thiện kèm verify. |
| **SEC2-06** | **Medium** | `src/actions/tracking-actions.ts:58-86` | `trackEvent` không kiểm session — chỉ cần cookie `tracking_session_id` (client tự set). `userId` luôn null. Cho phép **ghi hàng loạt row `Event` vào DB không xác thực** ⇒ đầu độc analytics + phình bảng (DoS chi phí lưu trữ). `forceFlush` (`:29`) cũng không guard nhưng chỉ flush buffer (thấp hơn). |
| **SEC2-07** | **Low** | `check-deadline/route.ts:28`, `send-digest`, `cleanup-notifications`, `hard-delete-workspaces`, `hard-delete-profiles`, `review-janitor` | 6/7 cron so sánh `key !== secret` **chuỗi thường** (không timing-safe); chỉ `auth-cleanup/route.ts:37` dùng `timingSafeEqual`. Cùng một secret, hai chuẩn so sánh — timing side-channel trên CRON_SECRET (khó khai thác qua mạng nhưng là bất nhất nên đồng bộ theo "H1 fix"). |
| **SEC2-08** | **Low** | `src/actions/bonus-actions.ts:38-61` | `getPayrollLockStatus` không có session/role check nào — vào thẳng `getWorkspacePrisma(workspaceId)`. Vì server action là POST endpoint public, caller bất kỳ (kể cả chưa đăng nhập) probe được cờ `isLocked` của MỌI `workspaceId`. Chỉ lộ 1 boolean nhưng là cross-tenant read không guard. |
| **SEC2-09** | **Low** | `src/actions/workspace-actions.ts:134-162` | `getWorkspacesForProfile` chỉ `getSession()`, không kiểm caller có ProfileAccess tới `profileId`. User đăng nhập bất kỳ liệt kê được `id/name/description` mọi workspace ACTIVE của **profile bất kỳ** (metadata leak cross-tenant; không leak nội dung). |
| **SEC2-10** | **Low** | `src/app/api/notifications/unsubscribe/route.ts:70-80` | GET **mutate** (upsert `emailEnabled:false`) ngay khi có token hợp lệ. Mail-scanner/prefetch bấm hộ link (token nhúng trong email) ⇒ tự unsubscribe nhầm user. Chính repo đã vá lỗi P4-R4 cho `portal-notify/unsubscribe` (GET không mutate) nhưng **bỏ sót** route nội bộ này. |
| **SEC2-11** | **Low** | `src/app/api/log-client-error/route.ts:17` | Không auth + không rate-limit (tự thừa nhận trade-off `:12-15`). Vector spam/flood Vercel logs (chi phí quan sát + có thể đẩy log thật ra khỏi cửa sổ giữ). Chỉ `console.error`, không ghi DB nên tác động giới hạn. |
| **SEC2-12** | **Low** | `src/actions/contact-actions.ts:14,44` | `searchContacts` (guard chỉ `getAuthSession`) trả **email thật của MỌI user toàn hệ thống** (select `email:true`, tìm cross-profile theo username/nickname/email) cho bất kỳ user đăng nhập. Là oracle liệt kê email + username xuyên tenant (hệ contact cross-profile theo thiết kế, nhưng lộ PII). Cân nhắc mask email / giới hạn scope. |

**Đã verify là AN TOÀN (finding cũ đã fix — bằng chứng):**
- `verifyFinanceAccess` không còn dùng `isTreasurer` (R7→R8) — `security.ts:203-207` delegate `verifyProfileAdminAccess`. ✅
- CLIENT fail-closed TRƯỚC WorkspaceMember trong `verifyWorkspaceAccess` (PE-1 HIGH) — `security.ts:109-119`. ✅
- `verifyWorkspaceAccess` đã enforce `sessionVersion` trên write-path (R3) — `security.ts:79`. ✅
- `getFrameAccount` đã siết OWNER/ADMIN (HT-022) — `global-settings.ts:22-28` (nhưng **write path SEC2-02 vẫn hở**). ⚠ một nửa.
- `webhooks/mux` HMAC fail-closed + idempotent ledger — `mux/route.ts:23-58`. ✅
- `scoring.py` có Bearer CRON_SECRET trên `do_POST` (`api/scoring.py:11-19`) — chỉ `vdownloader.py` hở. ✅/⚠

---

## Kết luận §2

Kiến trúc RBAC **về tổng thể chắc**: 1 predicate chuẩn (`verifyProfileAdminAccess`) cho admin/finance, defense-in-depth ở service-layer review, 2 hệ token khách tách bạch với anti-enumeration + rate-limit, và hàng loạt finding cross-tenant/IDOR đã được vá qua nhiều vòng audit (PE-1, R3, R7/R8, HT-022…). **Rủi ro còn lại tập trung ở rìa hệ thống, không ở lõi**: 2 High là endpoint "quên gỡ/quên siết" (`vdownloader.py` unauth, `updateFrameAccount` bất đối xứng) chứ không phải sai mô hình phân quyền; các Medium/Low là server-action `'use server'` lộ endpoint (SEC2-03/06/08/09) và bất nhất cron/GET-mutate. Hai ưu tiên xử lý ngay: **SEC2-01** (xoá `api/vdownloader.py` + `scoring.py` nếu không dùng, hoặc thêm auth) và **SEC2-02** (thêm `verifyProfileAdminAccess`/OWNER cho `updateFrameAccount` + đưa credential ra khỏi plaintext Task row).

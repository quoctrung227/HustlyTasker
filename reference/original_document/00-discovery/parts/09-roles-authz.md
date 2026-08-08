# 09 — Mô hình Role / Permission THẬT (discovery)

> Phạm vi: mô hình role, session/JWT, middleware, guard chuẩn, impersonation, guest access. KHÔNG bao gồm ma trận endpoint (phase 4). Mọi số dòng lấy từ code thật tại thời điểm audit.

## 1. Danh sách role có thật ở từng tầng

Hệ thống có **3 tầng role + 1 flag boolean**, KHÔNG có bảng `Permission` riêng — tất cả là role-check trực tiếp trong code.

| Tầng | Model / cột | Giá trị | Bằng chứng | Ghi chú |
|---|---|---|---|---|
| **Global (account)** | `User.role` — enum `UserRole` | `ADMIN`, `USER`, `AGENCY_ADMIN`, `CLIENT`, `LOCKED` | `prisma/schema.prisma:898-904`, field tại `prisma/schema.prisma:152` | `ADMIN` = super-admin legacy đã bị VÔ HIỆU làm bypass (`isGlobalAdmin` luôn `false` — `src/lib/security.ts:161-163`); điểm dùng thật còn lại: gate `admin:true` của review module (`src/lib/review/access.ts:44`) + cấm impersonate (`src/actions/impersonation-actions.ts:88`). `LOCKED` = banned. |
| **Profile (tenant)** | `ProfileAccess.role` — enum `ProfileRole` | `OWNER`, `ADMIN`, `USER`, `CLIENT` | `prisma/schema.prisma:908-913`, field tại `prisma/schema.prisma:274` | Đây là tầng RBAC CHÍNH (SaaS multi-tenant, "Sprint Z"). `ADMIN` có cutoff `grantedAt`: chỉ tự-thấy workspace tạo SAU khi được cấp (`prisma/schema.prisma:275-278`, enforce `src/lib/security.ts:106-108`). `CLIENT` = fail-closed, không bao giờ vào nội bộ (`src/lib/security.ts:109-119`, `src/lib/profile-permissions.ts:128-129`). |
| **Workspace** | `WorkspaceMember.role` — **String tự do trong DB** (chưa migrate enum) | `OWNER`, `ADMIN`, `MEMBER`, `GUEST` (định nghĩa TS) | `prisma/schema.prisma:110-114`; TS const `src/lib/workspace-roles.ts:10`; weight OWNER>ADMIN>MEMBER>GUEST `src/lib/workspace-roles.ts:15-20` | Vì cột là String, code phải type-guard `isWorkspaceRole` (`src/lib/workspace-roles.ts:34-36`) — role lạ trong DB → throw SECURITY_VIOLATION (`src/lib/security.ts:127-130`). `WorkspaceInvitation.role` cũng String default "MEMBER" (`prisma/schema.prisma:831`). |
| **Flag tài chính** | `User.isTreasurer` — Boolean | true/false | `prisma/schema.prisma:141` | "Thủ quỹ" KHÔNG phải role enum (không tồn tại `TREASURER` ở đâu). Sau audit R7→R8, flag này **KHÔNG còn cấp quyền finance** — `verifyFinanceAccess` = `verifyProfileAdminAccess` (`src/lib/security.ts:203-207`). Chỉ workspace-OWNER toggle được, và cấm tự-toggle (`src/actions/toggle-treasurer.ts:13-15`). Còn lộ ra UI qua `verifyActiveSession().isAdmin = isTreasurer` (`src/lib/security.ts:275-279`). |

Ghi chú thêm về từng giá trị global:
- `AGENCY_ADMIN`: gần như legacy — chỉ xuất hiện trong danh sách role được phép GÁN (`src/actions/admin-actions.ts:28`, `src/actions/create-user.ts:42`, `src/actions/user-actions.ts:89`, `src/actions/user-actions.ts:337`). Không có guard nào phân nhánh theo nó.
- `CLIENT` (global): tài khoản client đã bị khai tử — chặn ngay tại login (`src/actions/auth-actions.ts:363-365`), middleware đá session CLIENT còn sót về `/login` (`src/middleware.ts:88-90`), review module từ chối (`src/lib/review/access.ts:41-43`). Khách giờ đi qua share-link công khai (mục 6).
- `LOCKED`: chặn tập trung tại `getCurrentUser` (`src/lib/auth-guard.ts:40-42`), `verifyWorkspaceAccess` (`src/lib/security.ts:67-69`), `verifyActiveSession` (`src/lib/security.ts:241-243`), `isSessionLive` (`src/lib/profile-permissions.ts:53`).

## 2. Session / JWT

| Thuộc tính | Giá trị thật | Bằng chứng |
|---|---|---|
| Thuật toán | JWT HS256, thư viện `jose`, key = `env.JWT_SECRET` | `src/lib/jwt.ts:2-4`, `src/lib/jwt.ts:16-21` |
| TTL | Cookie session 30 ngày (`SESSION_MAX_AGE = 2_592_000s`); `encrypt()` mặc định "1 week" nếu không truyền ttl | `src/lib/jwt.ts:8`, `src/lib/jwt.ts:16`; login dùng 30 ngày `src/lib/auth.ts:6-7,17-20` |
| Cookie | `session` — **httpOnly**, `sameSite: 'lax'`, `secure` khi production (tắt nếu `ELECTRON_DESKTOP`), path `/` | `src/lib/auth.ts:23-29` |
| Payload JWT | `{ user: { id, username, role, profileId, sessionVersion, email, displayName, restricted, requiresEmailMigration [, sessionProfileId] }, expires }` | build tại `src/actions/auth-actions.ts:344-357`; `sessionProfileId` embed qua `loginWithProfile` `src/lib/auth.ts:36-38`; Google OAuth cùng payload `src/app/api/auth/google/callback/route.ts:94-98` |
| Verify ở đâu | `getSession()` chỉ decrypt, **CỐ Ý không check sessionVersion** (Edge-cheap); cross-check DB dồn về DAL | `src/lib/auth.ts:56-74` (comment nêu rõ pattern chống CVE-2025-29927) |
| Thu hồi phiên | `User.sessionVersion` (bump khi reset password / logout-all) so với claim JWT tại: `getCurrentUser` (`src/lib/auth-guard.ts:43-47`), `verifyActiveSession` (`src/lib/security.ts:257-269`), `verifyWorkspaceAccess` (`src/lib/security.ts:77-81`), `isSessionLive` (`src/lib/profile-permissions.ts:54`) | field `prisma/schema.prisma:170` |
| Rolling refresh | Middleware re-issue cookie khi còn <50% hạn (<15 ngày); BỎ QUA phiên impersonation | `src/middleware.ts:145-163` |
| Cookie phụ | `admin_session` (standby khi impersonation, httpOnly — `src/lib/auth.ts:101-107`); `tracking_session_id` (httpOnly, 30 phút — `src/middleware.ts:129-136`); `view-mode` (toggle mobile/desktop — `src/middleware.ts:28`); guest: `rv_unlock_{slug}`, `rv_guest_{slug}`, `rv_t_{slug}` (đều httpOnly qua `guestCookieAttrs` — `src/lib/review/share-auth.ts:33-36,359-367`) | |

## 3. middleware.ts chặn gì (src/middleware.ts)

| # | Hành vi | Dòng |
|---|---|---|
| 1 | Bỏ qua `/_next`, `/api`, path chứa `.`, favicon; matcher cũng exclude `api` → **API route KHÔNG qua middleware, tự verify trong handler** | `src/middleware.ts:9-16`, `src/middleware.ts:168-170` |
| 2 | Set header `x-device-type` (mobile/desktop) từ cookie `view-mode` hoặc userAgent | `src/middleware.ts:28-36` |
| 3 | Chặn path deprecated `/download`, `/extract` → rewrite 404 | `src/middleware.ts:40-42` |
| 4 | `/share/*` PUBLIC — early-return + `X-Robots-Tag: noindex` + `Referrer-Policy: no-referrer` (token trong URL là credential) | `src/middleware.ts:44-55` |
| 5 | `/r/*` PUBLIC — như trên + `x-request-id` (access control thật ở server-side resolveShare) | `src/middleware.ts:57-68` |
| 6 | Không có cookie: chỉ chặn `/admin` + `/dashboard` → redirect `/login` | `src/middleware.ts:71-75` |
| 7 | Có cookie: decrypt; role `CLIENT` → đá về `/login` (trừ /api, /login) | `src/middleware.ts:76-90` |
| 8 | Thiếu `sessionProfileId` khi vào `/admin` hoặc `/dashboard` → `/login` | `src/middleware.ts:94-100` |
| 9 | Decrypt lỗi: transient (`JWSSignatureVerificationFailed`) giữ cookie; hỏng thật → xóa cookie, trang bảo vệ redirect `/login?next=` (pathname-only, chống open-redirect) | `src/middleware.ts:101-122` |
| 10 | Rolling refresh phiên (mục 2) | `src/middleware.ts:145-163` |

**Quan trọng:** middleware **KHÔNG phân quyền theo role nội bộ** (USER vẫn qua được `/[wsId]/admin` ở tầng middleware). Việc chặn admin thật nằm ở layout: `src/app/[workspaceId]/admin/layout.tsx:56-66` gọi `verifyProfileAdminAccess`, fail → redirect `/{wsId}/dashboard`.

## 4. Các hàm guard chuẩn

| Hàm | File:line | Làm gì |
|---|---|---|
| `getSession()` | `src/lib/auth.ts:65-74` | Decrypt cookie `session` → payload JWT. Không chạm DB, không check sessionVersion. |
| `getCurrentUser()` | `src/lib/auth-guard.ts:21-59` | React `cache` per-request. Session → DB user; throw nếu LOCKED hoặc `sessionVersion` JWT < DB. Trả `AuthContext` (`isSuperAdmin = role==='ADMIN'`, `isTreasurer`). |
| `verifyActiveSession()` | `src/lib/security.ts:217-280` | Cached DAL gate cho READ path/layout. DB re-check LOCKED + sessionVersion → status `active/locked/unauthorized`. `isAdmin` trả về = **chỉ isTreasurer** (super-admin removed — `src/lib/security.ts:275-279`). |
| `verifyWorkspaceAccess(wsId, requiredRole)` | `src/lib/security.ts:38-165` | Guard chống BOLA/IDOR cho mutation. Chuỗi: session → DB user (LOCKED + sessionVersion `:63-81`) → workspace tồn tại → `ProfileAccess`: OWNER⇒workspace-OWNER; ADMIN + cutoff `grantedAt`⇒ADMIN; **CLIENT⇒fail-closed trước cả WorkspaceMember** (`:109-119`) → explicit `WorkspaceMember` row (type-guard role `:126-131`) → profile member fallback MEMBER (`:132-142`) → so `hasAtLeastRole` (`:150-153`). `isGlobalAdmin` luôn false (`:161-163`). |
| `verifyProfileAdminAccess(wsId)` | `src/lib/security.ts:180-191` | Predicate CHUẨN duy nhất cho admin/finance: `workspaceRole ∈ {OWNER,ADMIN}` HOẶC `profileRole ∈ {OWNER,ADMIN}`. Cố ý KHÔNG dùng `isTreasurer` (chống leak cross-tenant R7/R8). |
| `verifyFinanceAccess(wsId)` | `src/lib/security.ts:203-207` | Alias delegate 100% sang `verifyProfileAdminAccess` (thống nhất finance VIEW = WRITE). |
| `isSessionLive(session)` | `src/lib/profile-permissions.ts:46-56` | Liveness re-check (LOCKED + sessionVersion) cho các action chỉ auth bằng `getSession()` mà không đi qua `verifyWorkspaceAccess` (profile-member/cross-team/share-link actions). |
| `getProfileRole` / `getProfileAccess` | `src/lib/profile-permissions.ts:24-31,58-67` | Đọc `ProfileAccess.role` (+`grantedAt`). |
| Predicates profile | `src/lib/profile-permissions.ts:71-105` | `canCreateWorkspace`/`canInviteMember`/`canManageShareLinks` = OWNER∨ADMIN; `canRemoveMember`/`canChangeMemberRole`/`canTransferOwnership` = OWNER-only. Ma trận comment tại `:7-14`. |
| `canAccessWorkspace(userId, wsId)` | `src/lib/profile-permissions.ts:118-139` | Bản boolean của logic workspace-access (CLIENT⇒false `:129`). |
| `hasAtLeastRole` / `isWorkspaceRole` | `src/lib/workspace-roles.ts:27-36` | So sánh weight + type-guard cho cột String. |
| `requireReviewAccess(opts)` | `src/lib/review/access.ts:32-70` | Guard nội bộ module review: từ chối LOCKED/CLIENT (`:41-43`); `opts.admin` ⇒ đòi **global** `role==='ADMIN'` (`:44-46`); `opts.workspaceId` ⇒ delegate `verifyWorkspaceAccess`, `isAdmin` trả về là **workspace-scoped** (OWNER/ADMIN của workspace/profile, KHÔNG phải JWT role — `:48-61`). Guest KHÔNG BAO GIỜ qua hàm này. |
| `withReviewRoute` / `withShareRoute` | `src/lib/review/route-auth.ts:21-42,49-67` | Error-boundary map lỗi → envelope chuẩn (401/403/502/500). Không phải authz — handler vẫn tự gọi `requireReviewAccess`. |

## 5. Impersonation ("đóng vai")

Có thật, tại `src/actions/impersonation-actions.ts` + `src/lib/auth.ts`:

- `startImpersonation(targetUserId, workspaceId)` — `src/actions/impersonation-actions.ts:9-107`. Điều kiện (đã qua nhiều vòng audit fix):
  1. Caller phải là workspace **ADMIN** trở lên (`:14`), target phải là member của ĐÚNG workspace đó (`:18-22`).
  2. Cấm impersonate OWNER (`:41-43`); impersonate ADMIN thì caller phải là OWNER (`:44`).
  3. Cấm impersonate người có quyền OWNER/ADMIN ở **profile/workspace khác** (chống cross-tenant takeover vì cookie impersonation là GLOBAL — `:47-74`).
  4. Cấm impersonate tài khoản global `ADMIN` (`:88`).
  5. Luôn ghi audit log `auth.impersonation_started` (`:93-100`) / `auth.impersonation_ended` (`:113-122`).
- Cơ chế cookie — `createImpersonationSession` `src/lib/auth.ts:76-117`: session gốc của admin cất vào cookie `admin_session` (httpOnly), cookie `session` bị ghi đè bằng JWT của target kèm claims `isImpersonating`, `originalAdminId`, `impersonationExpiresAt`; **TTL 2h cho cả cookie lẫn `exp` của JWT** (fix HT-019 `:80-83,96`). Middleware không rolling-refresh phiên impersonation (`src/middleware.ts:145`).
- `stopImpersonationSession` — `src/lib/auth.ts:119-141`: restore `admin_session` → `session`, xóa standby.

## 6. Khách / guest — 2 hệ share-token ĐỘC LẬP

### 6a. `/share/[token]` — portal khách hàng (model `ClientShareLink`)

- **Token là credential duy nhất, không có session/password/PIN để mở.** Middleware cố ý để public (`src/middleware.ts:44-55`); mọi read/write đều re-resolve qua chokepoint `resolveShareToken` (`src/lib/share-link-auth.ts:73-281`), mount tại page `src/app/share/[token]/page.tsx:21`.
- Token: 12-char base64url mới (link 43-char cũ vẫn nhận, regex `:38`), lưu **SHA-256 hash-at-rest** (`src/lib/share-link-auth.ts:40-42`, cột unique `prisma/schema.prisma:574`).
- **Uniform failure**: mọi nhánh từ chối (sai format, không tồn tại, revoked, expired, client/profile chết, rate-limited) đều trả `null` → 404 giống nhau, chống enumeration (`src/lib/share-link-auth.ts:10-14,103,148-157`).
- Rate limit 2 tầng, fail-OPEN: per-IP-tin-cậy 240/min TRƯỚC lookup; per-token-hash 2000/min SAU khi token proven real (`src/lib/share-link-auth.ts:106-134,170-173`). IP lấy theo thứ tự header tin cậy, chống spoof XFF trái (`:44-66`).
- Scope: toàn bộ lịch sử client theo **name-path segments** trong profile (sub-brand ăn theo, chống conflate tên chứa "/", chống re-root khi ancestor mất — `src/lib/share-link-auth.ts:190-251`); mọi workspace của profile (`:253-260`).
- `ClientShareLink.passphraseHash` tồn tại trong schema (`prisma/schema.prisma:595`) nhưng **grep toàn `src/` không có chỗ nào đọc/ghi → dead-field candidate** (di sản thời Cloudflare Stream). `notifyEmail` + OTP 6 số chỉ dùng để đăng ký email nhận thông báo (`prisma/schema.prisma:597-602`).

### 6b. `/r/[slug]` — trang review guest (model `ShareLink` của module review)

- Slug nanoid(12) public; **gate chain hợp đồng**: `not_found(404)` → `revoked(410)` → `expired(410)` → `password(401)`, message của not_found/revoked giống hệt nhau (anti-enumeration) — `src/lib/review/share-auth.ts:63-109`. Page dùng `resolveShareGate` (`src/app/r/[slug]/page.tsx:25`), mọi `/api/r/*` gọi `requireShare` đầu tiên.
- **Password (tùy chọn per-link)**: `ShareLink.passwordHash` bcrypt, null = link mở (`prisma/schema.prisma:1883`). Nhập đúng → mint cookie `rv_unlock_{slug}` (JWT HS256 ký bằng `REVIEW_COOKIE_SECRET`, TTL min(24h, hạn link), **bind fingerprint của password hiện tại** — đổi password là mọi unlock cookie chết — `src/lib/review/share-auth.ts:111-144`).
- **Identity modal Name+Email** (guest-only, kiểu Frame.io): tạo `GuestSession`, cookie `rv_guest_{slug}` = token random 32-byte, DB chỉ lưu sha256, TTL 30 ngày (`src/lib/review/share-auth.ts:154-187`; model `prisma/schema.prisma:1926-1947`).
- **Known-client auto-identity**: share gắn task của client ACTIVE → tự mint GuestSession mang tên client (walk lên client gốc), email synthetic `noreply+client-{id}@review.invalid` — client của agency KHÔNG thấy modal (`src/lib/review/share-auth.ts:189-221,309-327`). Email synthetic **không bao giờ** được tính là verified cho quyết định sign-off (chống mạo danh approve — `:53-61`). Resolve thứ tự cho write: cookie có sẵn → input modal → auto-client → 401 (`resolveGuestForWrite`, `:336-356`).
- **PIN 6 số double-opt-in** chỉ dành cho subscribe email thông báo (FR-11), TTL 10 phút, khóa sau 5 lần sai; route luôn trả 200 chống enumeration (`src/lib/review/guest-subscribe.ts:1-17`; model `GuestEmailVerification` `prisma/schema.prisma:1949-1956`).
- Nội dung guest đi qua DTO trimmed duy nhất — không bao giờ mang workspaceId/taskId/uploader/tiền/email guest khác (`src/lib/review/share-guest.ts:1-19`); token playback Mux/R2 TTL min(6h, hạn link) (`src/lib/review/share-auth.ts:369-378`).

## 7. Điểm đáng chú ý / legacy & dead-code candidates

| # | Phát hiện | Bằng chứng |
|---|---|---|
| 1 | `isGlobalAdmin` deprecated, hard-code `false` — super-admin model đã gỡ nhưng field vẫn trả về cho backward-compat | `src/lib/security.ts:48-52,161-163` |
| 2 | `UserRole.ADMIN` (global) gần như chết: không cấp workspace/finance access; còn 2 điểm dùng thật: `requireReviewAccess({admin:true})` (`src/lib/review/access.ts:44`) và guard cấm-impersonate (`src/actions/impersonation-actions.ts:88`). `getCurrentUser().isSuperAdmin` vẫn tính từ nó (`src/lib/auth-guard.ts:52`). | như cột trái |
| 3 | `AGENCY_ADMIN` chỉ còn trong danh sách role gán được — không guard nào phân nhánh theo nó | `src/actions/admin-actions.ts:28`, `src/actions/user-actions.ts:337` |
| 4 | `ClientShareLink.passphraseHash` không có code sử dụng trong `src/` → dead field candidate | `prisma/schema.prisma:595` (schema-only) |
| 5 | `WorkspaceMember.role` + `WorkspaceInvitation.role` là String tự do (chưa enum DB) — an toàn nhờ type-guard runtime, nhưng là nợ migration được chính schema ghi chú | `prisma/schema.prisma:114,831`; `src/lib/workspace-roles.ts:1-8` |
| 6 | 2 hệ guest token trùng tên khái niệm nhưng khác model/luồng: `ClientShareLink` (/share, portal khách) vs `ShareLink` (/r, review) — dễ nhầm khi đọc code | mục 6a vs 6b |
| 7 | Middleware không enforce role — mọi phân quyền thật nằm ở layout + DAL (`verifyActiveSession`/`verifyWorkspaceAccess`), đúng thiết kế chống CVE-2025-29927 | `src/lib/auth.ts:56-63`, `src/middleware.ts:142-144`, `src/app/[workspaceId]/admin/layout.tsx:56-66` |

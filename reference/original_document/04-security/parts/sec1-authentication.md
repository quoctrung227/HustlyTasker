# §1 — Authentication (cơ chế xác thực THẬT)

> Phase 4 audit bảo mật HustlyTasker. Mọi kết luận kèm `file:line` đã mở code xác minh ngày 2026-08-02. Phần này CHỈ mô tả tầng authentication (đăng nhập, session, mật khẩu, OTP, OAuth, thu hồi phiên) — authorization/endpoint-matrix nằm ở các part khác. KHÔNG sửa code, chỉ mô tả + đề xuất.

---

## 1. Tổng quan cơ chế

| Hạng mục | Giá trị THẬT | Bằng chứng |
|---|---|---|
| Kiểu session | **JWT tự-quản (stateless)**, KHÔNG server-side session store. Thư viện `jose`, thuật toán **HS256** (symmetric), ký bằng `env.JWT_SECRET` | `src/lib/jwt.ts:2-4,16-21` |
| Nơi lưu | Cookie **`session`** httpOnly. Không dùng localStorage cho token | `src/lib/auth.ts:23-29` |
| Đăng nhập | Password (email/username + bcrypt) HOẶC Google OAuth. Tài khoản `CLIENT` bị khai tử — chặn ngay tại login | `src/actions/auth-actions.ts:168,363-365`; `src/app/api/auth/google/callback/route.ts:27` |
| Đăng ký | Public signup có honeypot + Vercel BotID + rate-limit + HIBP; và luồng admin-invite (`createUser`) | `src/actions/signup-actions.ts:107`; `src/actions/create-user.ts:17` |
| Password hash | **bcryptjs** — cost **12** cho signup + password-reset; cost **10** cho admin-tạo-user + share password | `src/actions/signup-actions.ts:39,236`; `src/actions/password-reset-actions.ts:37,331`; `src/actions/create-user.ts:87`; `src/lib/review/shares.ts:23,786` |
| Chống brute-force | 2 tầng: rate-limit Upstash (login 10/phút/IP) + account lockout (5 fail/15 phút, khóa 15 phút, atomic Serializable) | `src/lib/rate-limit-upstash.ts:86`; `src/actions/auth-actions.ts:14-16,76-126` |
| Email verify | Token 32-byte hex, lưu SHA-256, TTL 24h, single-use (optimistic lock) | `src/actions/signup-actions.ts:299-310`; `src/app/api/auth/verify-email/route.ts:14-77` |
| Reset mật khẩu | 3 bước OTP: OTP 6 số (TTL 10ph, 5 attempt) → resetToken 32-byte (TTL 5ph, single-use) → đổi pass + bump sessionVersion | `src/actions/password-reset-actions.ts:65-405` |
| Thu hồi phiên | `User.sessionVersion` so JWT-claim vs DB tại **DAL** (chống CVE-2025-29927) | `src/lib/security.ts:77-81`; `src/lib/auth-guard.ts:43-47`; `src/lib/profile-permissions.ts:54` |
| TTL session | **30 ngày** + rolling refresh khi còn <15 ngày → phiên user active gần như vô hạn | `src/lib/auth.ts:6-7,17-20`; `src/lib/jwt.ts:8`; `src/middleware.ts:145-163` |

---

## 2. (a) Session / JWT — chi tiết

### 2.1 Thuật toán & ký
- `encrypt(payload, ttl='1 week')` — `SignJWT` alg **HS256**, `setIssuedAt()`, `setExpirationTime(ttl)`, ký bằng `key = TextEncoder().encode(env.JWT_SECRET)` (`src/lib/jwt.ts:16-22`).
- `decrypt(input)` — `jwtVerify(input, key, { algorithms: ['HS256'] })`; **đã pin algorithm** → chống alg-confusion (`none`/RS↔HS) (`src/lib/jwt.ts:24-29`). ✅
- `JWT_SECRET` validate `z.string().min(10)` với default placeholder `"temporary-build-secret-key-change-me"`. Production **fail-closed**: nếu secret = placeholder và không phải build-phase → `throw` từ chối boot (`src/lib/env.ts:3,7,31-42`). ✅ (finding CRITICAL cũ R1 đã fix — verify: dòng 37-42 vẫn còn).
  - Lưu ý: `min(10)` chỉ đảm bảo độ dài ≥10 ký tự; không ép entropy. HS256 an toàn khi secret ≥32 byte ngẫu nhiên — đây là kỳ vọng vận hành, code không enforce (chỉ chặn đúng chuỗi placeholder).

### 2.2 Cookie `session`
| Flag | Giá trị | Bằng chứng |
|---|---|---|
| `httpOnly` | ✅ true | `src/lib/auth.ts:25` |
| `secure` | `NODE_ENV==='production' && !ELECTRON_DESKTOP` → ✅ bật trên web prod, tắt cho Electron (http local) | `src/lib/auth.ts:26` |
| `sameSite` | `'lax'` | `src/lib/auth.ts:27` |
| `path` | `/` | `src/lib/auth.ts:28` |
| `expires` | 30 ngày (hoặc rememberMe 30 ngày — hằng số bằng nhau) | `src/lib/auth.ts:6-7,17-18` |

Payload JWT: `{ user: { id, username, role, profileId, sessionVersion, email, displayName, restricted, requiresEmailMigration [, sessionProfileId] }, expires }` (`src/actions/auth-actions.ts:344-357`; embed `sessionProfileId` qua `loginWithProfile` `src/lib/auth.ts:36-38`).

### 2.3 TTL & rolling refresh
- `SESSION_MAX_AGE = 2_592_000s` (30 ngày) (`src/lib/jwt.ts:8`).
- Middleware re-issue cookie khi thời gian còn lại < 50% TTL (< 15 ngày) → sliding window: user active không bao giờ hết hạn (`src/middleware.ts:145-163`).
- Rolling refresh **BỎ QUA** phiên impersonation (giữ nguyên TTL 2h) (`src/middleware.ts:145`). ✅
- ⚠️ Refresh chỉ gia hạn cookie ở Edge, **KHÔNG** enforce sessionVersion (Edge không có DB) — cổng thu hồi thật ở DAL. Comment code ghi rõ (`src/middleware.ts:142-144`).

### 2.4 Logout — 2 đường KHÔNG đồng nhất
| Đường | Bump sessionVersion? | Bằng chứng |
|---|---|---|
| Server action `logoutAction()` | ✅ CÓ (`sessionVersion: { increment: 1 }`) → thu hồi mọi token khác | `src/actions/auth-actions.ts:404-420` |
| Route `GET /api/auth/logout` | ❌ KHÔNG — chỉ `logout()` xóa cookie | `src/app/api/auth/logout/route.ts:14-46`; `src/lib/auth.ts:51-54` |

→ Logout qua route GET để lại token ở thiết bị khác / token bị copy còn sống tới hết `exp` (tối đa 30 ngày). Xem finding **AUTH-03**.

### 2.5 Cookie phụ
`admin_session` (standby impersonation, httpOnly, TTL 2h — `src/lib/auth.ts:101-107`); `tracking_session_id` (httpOnly 30ph — `src/middleware.ts:129-136`); `current_profile_id` (httpOnly, backward-compat — `src/app/api/profile/select/route.ts:92`); guest: `rv_unlock_{slug}` / `rv_guest_{slug}` / `rv_t_{slug}` (`src/lib/review/share-auth.ts:33-36`).

---

## 3. (b) Password hashing

| Đường tạo/đổi mật khẩu | Thuật toán + cost | Chính sách độ mạnh | Bằng chứng |
|---|---|---|---|
| Public signup | bcrypt cost **12** | ≥12 ký tự + HIBP k-anonymity (fail-open) + disposable-email check | `src/actions/signup-actions.ts:39,212-220,236` |
| Password reset | bcrypt cost **12** | `validatePasswordFull` (≥12 + HIBP) | `src/actions/password-reset-actions.ts:37,299-301,331` |
| Admin tạo user (`createUser`) | bcrypt cost **10** | ❌ **KHÔNG** check độ mạnh/HIBP — chỉ kiểm tra "không rỗng" | `src/actions/create-user.ts:38,87` |
| Share password (`/r`) | bcrypt cost **10** | 4–72 ký tự | `src/lib/review/shares.ts:23,780-787` |

- `validatePasswordStrength`: `MIN_LENGTH=12`, `MAX_LENGTH=128`, KHÔNG bắt buộc composition (theo NIST 800-63B-4). HIBP dùng SHA-1 prefix 5 ký tự + `Add-Padding`, timeout 3s, **fail-open** nếu HIBP down (`src/lib/password-validator.ts:20-21,67-102`).
- bcryptjs cap input 72 byte — code giới hạn UI 128 (`src/lib/password-validator.ts:7`). Không truncation lỗi vì MAX_LENGTH chỉ để chặn DoS.
- ⚠️ Bất nhất cost (10 vs 12) + admin-path bỏ qua chính sách mật khẩu → finding **AUTH-04**.

---

## 4. (c) Chống brute-force

### 4.1 Rate-limit (Upstash Redis, persistent qua cold-start)
| Limiter | Ngưỡng | Bằng chứng |
|---|---|---|
| login/IP | 10 / 1 phút | `src/lib/rate-limit-upstash.ts:86,200-211` |
| signup/IP | 5 / 1 giờ | `:64,167-178` |
| signup/email | 3 / 1 giờ | `:75,183-194` |
| OTP/email | 3 / 1 giờ + cooldown 60s | `:97,217-228`; cooldown `src/actions/password-reset-actions.ts:105-122` |
| OTP/IP | 10 / 1 giờ | `:108,233-244` |
| invite/(ws,user) | 5 / 24h; invite/caller 40 / 1h | `:121-143` |

- Fallback: env Upstash thiếu → **fail-CLOSED trong production** (`noLimiterResult` trả `success:false`), fail-open ở dev (`src/lib/rate-limit-upstash.ts:159-162`). ✅
- ⚠️ Nhưng `loginAction` bọc `checkLoginIp` trong `try { } catch { /* fail-open */ }` (`src/actions/auth-actions.ts:209-224`) — nếu `limiter.limit()` **ném exception runtime** (Upstash timeout/network, không phải missing-env) thì login **fail-OPEN kể cả prod**. Signup/OTP KHÔNG bọc catch → sẽ 500 (fail-closed hơn). → finding **AUTH-05**.

### 4.2 Account lockout
- Cấu hình: `LOCKOUT_THRESHOLD=5`, `WINDOW=15` phút, `DURATION=15` phút (`src/actions/auth-actions.ts:14-16`).
- `checkAndUpdateLockout` kiểm tra `lockedUntil > now` TRƯỚC khi bcrypt (tiết kiệm CPU) (`:55-69,252-266`).
- `bumpFailedAttempts` chạy trong `$transaction` **isolationLevel Serializable** → 2 request concurrent không bypass được counter (fix HIGH #4) (`:83-109`). ✅
- Đếm fail theo `loginAttempt` trong window + ghi `auditLog auth.account_locked` (`:85-124`).
- Reset lockout khi login thành công + khi reset password (`:128-138`; `password-reset-actions.ts:356-358`).

### 4.3 Anti-enumeration login
- Mọi nhánh fail (user_not_found / invalid_password / account_locked / role_locked / google-only-no-password) trả **cùng** `GENERIC_AUTH_ERROR` (`src/actions/auth-actions.ts:186,239-314`).
- Padding response 100–300ms bằng `crypto.randomInt` CSPRNG (`:21-26,221`).
- Google-only account (không password) bị bump attempt + generic error, `compare()` không chạy trên null-hash (`:268-284`). ✅
- IP cho login lấy **theo thứ tự header tin cậy**: `x-real-ip` → `x-vercel-forwarded-for` (right-most) → xff **right-most** (never left-most) — fix HT-002 chống spoof XFF (`:191-204`). ✅

---

## 5. (d) Email verification + OTP reset

### 5.1 Email verification (signup)
- Token `randomBytes(32).hex` (64 char), DB lưu `hashToken` = SHA-256, TTL 24h, `purpose='EMAIL_VERIFICATION'` (`src/actions/signup-actions.ts:300-310`; `src/lib/otp.ts:53-62`).
- Verify: `$transaction` tìm token chưa `usedAt` + chưa hết hạn → `updateMany usedAt` optimistic lock → set `emailVerified` (single-use, chống replay) (`src/app/api/auth/verify-email/route.ts:22-71`).
- GET redirect dùng `req.nextUrl.origin` (same-origin) → chống open-redirect (fix L2) (`:82-87`). Token nằm trong query-string URL (email link) — chuẩn ngành, single-use + TTL 24h.

### 5.2 OTP reset password (3 bước)
| Bước | Cơ chế chống replay/brute | Bằng chứng |
|---|---|---|
| 1. requestOtp | OTP 6 số CSPRNG, lưu SHA-256 (`hashOtp`), TTL 10ph; invalidate OTP cũ chưa dùng; cooldown 60s; audit log | `password-reset-actions.ts:65-174`; `otp.ts:19-30` |
| 2. verifyOtp | `verifyOtp` constant-time; sai → tăng `attemptCount` **optimistic-lock** (fix CRITICAL #1); ≥5 → `invalidatedAt`; đúng → tạo resetToken + `consumedAt` trong `$transaction` | `:178-289` |
| 3. resetWithToken | resetToken 32-byte, lưu SHA-256, TTL 5ph, `usedAt` optimistic-lock single-use (fix CRITICAL #2 dùng `purpose=PASSWORD_RESET`); đổi pass + **bump sessionVersion** + reset lockout; alert email | `:293-405` |

- Anti-enumeration: request luôn trả `GENERIC_OTP_RESPONSE` dù email tồn tại/không/locked/cooldown (fix HT-010) (`:41-44,100-122,173`).
- verify trả `GENERIC_INVALID` không kèm `attemptsRemaining` (fix HIGH #3 chống leak user-exists) (`:183-186`).
- Token confusion phòng ngừa: OTP + resetToken đều filter `purpose='PASSWORD_RESET'`, tách biệt migration OTP (`:206,255,309`).
- ⚠️ `getRequestMeta` ở reset/signup lấy IP = `x-forwarded-for.split(',')[0]` (**LEFT-most, do client chọn**) — KHÁC với login đã hardened → rate-limit theo IP của signup + OTP có thể bị bypass bằng spoof XFF. → finding **AUTH-02**.
- ℹ️ OTP 6 số hash SHA-256 **không salt**: keyspace chỉ 10^6, về lý thuyết precompute được nếu DB bị lộ; giảm nhẹ bởi TTL 10ph + single-use + 5-attempt. Chấp nhận được theo OWASP MFA (comment `otp.ts:6-10`), ghi nhận là dư nợ nhẹ.

### 5.3 Email migration OTP
- Endpoint authenticated `POST /api/auth/migrate-email` (step request_otp/verify_otp) cho user cũ chưa có email (`src/app/api/auth/migrate-email/route.ts:16-42`; logic `src/actions/email-migration-actions.ts`).

---

## 6. (e) Google OAuth

| Kiểm soát | Trạng thái | Bằng chứng |
|---|---|---|
| CSRF `state` | ✅ `randomBytes(32).base64url`, lưu cookie `g_oauth_state` httpOnly + secure(prod) + sameSite lax + TTL 5ph; callback so khớp + **single-use** (clear ngay) | `src/app/api/auth/google/authorize/route.ts:21,32-38`; `src/app/api/auth/google/callback/route.ts:33-40` |
| Email verified | ✅ Chỉ link/tạo khi `info.verifiedEmail && info.email` (chống account-takeover) | `callback/route.ts:48-49` |
| Chặn LOCKED / CLIENT | ✅ Mirror password-path: reject `role==='LOCKED'`/`'CLIENT'` (fix R14) — không cho ban-bypass qua OAuth | `callback/route.ts:60-67` |
| Scope | `openid email profile`, `prompt=select_account` | `authorize/route.ts:27,29` |
| Set session | Dùng `login`/`loginWithProfile` (cùng cookie flags), `restricted:false` (Google email đã verified) | `callback/route.ts:71-98` |

→ Luồng OAuth là điểm mạnh: state CSRF + verified-email + ban-check đều đủ. Không có finding riêng.

---

## 7. (f) sessionVersion revocation (phòng thủ CVE-2025-29927)

Thiết kế: middleware **KHÔNG** phân quyền/không tin JWT đơn lẻ; thu hồi enforce ở DAL bằng cách so `sessionVersion` claim (JWT) với DB.

| Chokepoint | Check LOCKED + sessionVersion | Bằng chứng |
|---|---|---|
| `getSession()` | ❌ chỉ decrypt (cố ý Edge-cheap) | `src/lib/auth.ts:56-74` |
| `getCurrentUser()` | ✅ | `src/lib/auth-guard.ts:40-47` |
| `verifyActiveSession()` (read path/layout) | ✅ | `src/lib/security.ts:241-269` |
| `verifyWorkspaceAccess()` (write/mutation) | ✅ (fix R3) | `src/lib/security.ts:63-81` |
| `isSessionLive()` (share/profile actions) | ✅ | `src/lib/profile-permissions.ts:46-56` |

`sessionVersion` được bump khi: reset password (`password-reset-actions.ts:354`), logoutAction (`auth-actions.ts:412-415`), (và email-migration). Coerce `null→0` cho session legacy (`security.ts:77-78`). ✅

⚠️ **NGOẠI LỆ — 2 route bypass tầng DAL này**:
1. `POST /api/profile/select` — decrypt trực tiếp + fallback decrypt token từ **request body**, chỉ `findUnique` user, KHÔNG check LOCKED/sessionVersion, rồi **re-sign session cookie mới** (`src/app/api/profile/select/route.ts:15-24,30-88`). → finding **AUTH-01**.
2. `GET /api/auth/role` — `decrypt` cookie + trả `role`+`isTreasurer`, KHÔNG check LOCKED/sessionVersion (`src/app/api/auth/role/route.ts:15-29`). → finding **AUTH-06**.

---

## 8. Findings (tầng authentication)

| ID | Severity | Tiêu đề | File:line |
|---|---|---|---|
| AUTH-01 | Medium | `/api/profile/select` nhận session-token trong body + không kiểm sessionVersion/LOCKED, re-sign cookie mới | `src/app/api/profile/select/route.ts:15-24,86-88` |
| AUTH-02 | Medium | Rate-limit IP của signup + OTP dùng XFF **left-most** (client tự đặt) → bypass throttle | `src/actions/signup-actions.ts:78`; `src/actions/password-reset-actions.ts:57` |
| AUTH-03 | Low | `GET /api/auth/logout` không bump sessionVersion → token thiết bị khác/bị copy còn sống tới 30 ngày | `src/app/api/auth/logout/route.ts:45`; đối chiếu `src/actions/auth-actions.ts:412-415` |
| AUTH-04 | Low | `createUser` (admin) hash bcrypt cost 10 + KHÔNG enforce độ mạnh/HIBP → account nội bộ mật khẩu yếu | `src/actions/create-user.ts:38,87` |
| AUTH-05 | Low | `loginAction` fail-OPEN khi Upstash ném exception runtime (kể cả prod) — chỉ còn lockout per-user | `src/actions/auth-actions.ts:209-224` |
| AUTH-06 | Low | `GET /api/auth/role` trả role/isTreasurer không check LOCKED/sessionVersion (liveness) | `src/app/api/auth/role/route.ts:15-29` |
| AUTH-07 | Low | Session TTL 30 ngày + rolling refresh → phiên active gần như vô hạn; thu hồi chỉ ở DAL | `src/lib/auth.ts:6-7`; `src/middleware.ts:145-163` |

### Chi tiết + đề xuất

**AUTH-01 (Medium) — `/api/profile/select` fallback decrypt token từ body**
`src/app/api/profile/select/route.ts:18-24`: nếu `getSession()` (cookie) rỗng nhưng body có `sessionToken` → `decrypt(sessionToken)` và tiếp tục. Vấn đề:
- Chấp nhận JWT phiên qua **request body** phá vỡ ranh giới httpOnly cookie (token có thể bị log ở proxy/CDN/access-log, hoặc do client-side JS nắm giữ). Comment tự nhận là "Vercel Edge Cache Workaround" (`:17`).
- Sau decrypt chỉ `findUnique` user rồi kiểm `profileId`/`ProfileAccess`; **KHÔNG** kiểm `role==='LOCKED'` và **KHÔNG** so sessionVersion → user đã bị ban (LOCKED) hoặc token đã bị thu hồi (đổi mật khẩu/logout-all) vẫn được endpoint xử lý 200 và **re-sign một cookie `session` mới** (`:66-88`).
- Cookie re-sign giữ nguyên `sessionVersion` cũ trong claim nên DAL downstream vẫn chặn — nhưng bản thân endpoint là hành động có side-effect (đổi active profile + phát cookie) chạy trên phiên chết. Ngoài ra `encrypt(newPayload)` gọi KHÔNG có `ttl` → `exp` JWT mặc định **1 tuần**, lệch với `expires` 30 ngày nhét trong payload (`:79-80`, đối chiếu `jwt.ts:16`).
- Đề xuất: bỏ nhánh fallback decrypt-from-body (chỉ tin cookie); thêm `isSessionLive()`/check LOCKED+sessionVersion trước khi re-sign; truyền TTL đúng cho `encrypt`.

**AUTH-02 (Medium) — XFF left-most trong signup/OTP rate-limit**
`signup-actions.ts:73-82` và `password-reset-actions.ts:52-61` lấy `ip = h.get('x-forwarded-for')?.split(',')[0]` — token trái của XFF là do **client tự đặt** (chính codebase thừa nhận điều này ở fix HT-002 của login, `auth-actions.ts:192-203`). Kẻ tấn công xoay giá trị XFF trái → mỗi request một "IP" khác → vượt hoàn toàn giới hạn signup 5/h/IP và OTP 10/h/IP. Giới hạn theo email (3/h) không bị ảnh hưởng nên enumeration-per-email vẫn bị chặn, nhưng bảo vệ flood/abuse theo IP bị vô hiệu. Đề xuất: dùng cùng helper hardened như login (`x-real-ip` → `x-vercel-forwarded-for`/xff **right-most**).

**AUTH-03 (Low) — logout GET không thu hồi token khác**
`auth-actions.ts:404-420` (server action) bump sessionVersion; nhưng `GET /api/auth/logout` chỉ `logout()` xóa cookie (`route.ts:45`). Nếu UI/link nào gọi đường GET, token trên thiết bị khác hoặc token bị đánh cắp vẫn hợp lệ tới hết `exp` (tới 30 ngày). Đề xuất: bump sessionVersion trong route GET giống server action.

**AUTH-04 (Low) — admin-created account mật khẩu yếu + cost thấp**
`create-user.ts:38` chỉ chặn rỗng; `:87` hash cost 10. Không gọi `validatePasswordFull` → admin có thể đặt mật khẩu <12 ký tự / đã lộ trong breach cho nhân sự, và hash yếu hơn signup (cost 12). Đề xuất: dùng `validatePasswordFull` + cost 12 thống nhất.

**AUTH-05 (Low) — login rate-limit fail-open khi Upstash lỗi runtime**
`auth-actions.ts:224` `catch { }` nuốt lỗi và tiếp tục login. Missing-env đã fail-closed (RL-1), nhưng exception runtime (timeout/network) làm bỏ qua throttle IP kể cả prod. Lockout per-user (5/15ph) vẫn là tuyến 2. Đề xuất: trong prod, fail-closed khi `checkLoginIp` ném lỗi.

**AUTH-06 (Low) — `/api/auth/role` không check liveness**
`route.ts:15-29` decrypt cookie + trả `role`/`isTreasurer` sau `findUnique` mà không kiểm LOCKED/sessionVersion. Chỉ lộ role của chính user (blast-radius thấp) nhưng lệch pattern DAL. Đề xuất: gọi `getCurrentUser()`/`isSessionLive()`.

**AUTH-07 (Low) — session sống lâu**
TTL 30 ngày + rolling refresh (`middleware.ts:145-163`) khiến phiên user active gần như không hết hạn; thu hồi chỉ hiệu lực ở DAL sau khi bump sessionVersion. Đây là đánh đổi UX có chủ đích (QĐ-13) nhưng nới cửa sổ token bị đánh cắp. Đề xuất: cân nhắc absolute-max-lifetime hoặc idle-timeout ngắn hơn cho tài khoản admin/finance.

---

## 9. Điểm mạnh đã xác minh (không phải finding)

- JWT **pin algorithm HS256** khi verify → chống alg-confusion (`jwt.ts:24-29`).
- `JWT_SECRET` fail-closed ở prod nếu là placeholder (`env.ts:31-42`) — CRITICAL R1 cũ đã fix.
- Account lockout atomic Serializable chống race (`auth-actions.ts:83-109`).
- OTP + reset/verify token: hash-at-rest SHA-256, optimistic-lock single-use, TTL ngắn, constant-time compare (`otp.ts:37-46,67-76`; `password-reset-actions.ts:229-277,336-360`).
- Anti-enumeration đồng bộ (generic error + padding CSPRNG) ở login/signup/forgot/verify (`auth-actions.ts:186,221`; `signup-actions.ts:44-66,228-232`).
- Google OAuth: state CSRF single-use + verified-email + ban-check (`callback/route.ts:38-67`).
- sessionVersion revocation phủ đủ 4 chokepoint DAL (write + read + share) — CVE-2025-29927 mitigation (`security.ts:63-81,241-269`; `auth-guard.ts:40-47`; `profile-permissions.ts:46-56`), trừ 2 route ngoại lệ AUTH-01/06.
- Password policy theo NIST 800-63B-4 (≥12, no-composition, HIBP) (`password-validator.ts:1-16`).
- HStl..: impersonation TTL 2h khớp cả cookie lẫn JWT exp (fix HT-019), không rolling-refresh (`auth.ts:76-117`; `middleware.ts:145`).

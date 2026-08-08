# PHASE 4 — KIẾN TRÚC BẢO MẬT HỆ THỐNG HIỆN TẠI

> Mô tả bảo mật ĐANG CÓ THẬT trong code (không lý thuyết), mọi mục kèm file:line. Chi tiết đầy đủ trong `parts/sec1`→`sec6`; sơ đồ trong `diagrams/`. Ngày audit: 2026-08-02.
> **Phase này chỉ mô tả + đề xuất — không sửa code.** Một số finding CRITICAL/High đã được audit-orchestrator **verify độc lập** (đánh dấu ✅).

## 0. Tóm tắt điều hành

Kiến trúc RBAC lõi **về tổng thể chắc**: 1 predicate admin/finance chuẩn (`verifyProfileAdminAccess` — `src/lib/security.ts:180`), defense-in-depth ở service-layer review (workspaceId re-derive từ row), 2 hệ token khách tách bạch + anti-enumeration + rate-limit, và nhiều IDOR/cross-tenant cũ đã vá qua nhiều vòng audit. **Rủi ro còn lại tập trung ở RÌA hệ thống, không ở lõi phân quyền**: secret lọt git history, file dead-code Python còn deploy, endpoint "quên gỡ/quên siết", và server action `'use server'` vô tình thành endpoint public.

**Việc GẤP NHẤT (làm ngay, không cần chờ):** xoay khóa DB Neon (C1) — credential prod đang đọc được từ git history của bất kỳ ai clone repo.

## 1. Authentication (chi tiết: `parts/sec1-authentication.md`)

- Session = **JWT tự-quản HS256 (jose)** trong cookie httpOnly `session` (secure ở prod, sameSite=Lax, TTL **30 ngày** + rolling refresh khi còn <15 ngày); KHÔNG session store. `src/lib/auth.ts:23-29`, `src/lib/jwt.ts:16-29`.
- Thu hồi phiên bằng `User.sessionVersion` so tại DAL (phòng CVE-2025-29927) phủ 4 chokepoint (`verifyWorkspaceAccess`/`verifyActiveSession`/`getCurrentUser`/`isSessionLive`); `getSession()` cố ý không check (Edge-cheap).
- Password: **bcryptjs cost 12** (signup/reset), **cost 10** (admin createUser + share password) — bất nhất. Chính sách ≥12 ký tự + HIBP k-anonymity (NIST 800-63B-4) áp cho signup/reset nhưng KHÔNG áp cho admin createUser.
- Chống brute-force 2 tầng: Upstash rate-limit (login 10/phút/IP) + account lockout 5 fail/15 phút (atomic Serializable), fail-closed ở prod khi thiếu env.
- Email verify = LINK token 32-byte SHA-256 TTL 24h single-use; reset = OTP 6 số → resetToken, optimistic-lock chống replay, anti-enumeration.
- Google OAuth (điểm mạnh): state CSRF single-use + verified-email + ban-check (reject LOCKED/CLIENT).
- **Đã verify là đã fix**: JWT_SECRET fail-closed (R1), XFF login hardening (HT-002), sessionVersion write-path (R3), OAuth ban (R14), impersonation TTL 2h (HT-019).

## 2. Authorization / RBAC (chi tiết + MA TRẬN ĐẦY ĐỦ: `parts/sec2-rbac-matrix.md`)

- 11 guard thật được mô tả (Phần A): `verifyWorkspaceAccess` (BOLA/IDOR, CLIENT fail-closed), `verifyProfileAdminAccess` = `verifyFinanceAccess` (predicate admin/finance duy nhất, KHÔNG dùng isTreasurer), `requireReviewAccess` (imperative service-layer, workspaceId re-derive từ row), `requireShare`/`resolveShareToken`, `isSessionLive`, impersonation.
- **Ma trận Role × Endpoint đầy đủ** (Phần B, 13 nhóm B1-B13): mỗi nhóm domain × 9 cột role (Global-ADMIN, Profile-OWNER/ADMIN, Staff-USER, WS-GUEST, CLIENT-token, Guest-token, Cron, Public) — đánh dấu ✓/✗/—. Lấy mẫu dày các endpoint nhạy cảm (payroll, invoice, payment, member/invite, impersonation, review status, portal approve, share link) + đầy đủ cho API routes.
- Kết luận: rủi ro không ở mô hình phân quyền mà ở endpoint rìa (Phần C = 12 finding).

## 3. Input validation & data layer (chi tiết: `parts/sec3-input-data.md`)

- **SQL injection: AN TOÀN** — cả 21 site `$queryRaw/$executeRaw` đều parametrized (tagged-template / `Prisma.sql` / `Prisma.join`), 0 `$queryRawUnsafe/$executeRawUnsafe`.
- **Tenant isolation mạnh ở data-layer**: `getWorkspacePrisma` (`src/lib/workspace.ts:105-221`) tự inject `workspaceId` vào where/data cho mọi model non-bypass, fail-closed cho Client thiếu profileId → BOLA cross-tenant bị chặn ngay cả khi quên filter.
- **Mass assignment**: `updateTask` (`task-management-actions.ts:35-107`) đưa `data:any` vào `task.update` qua DENYLIST — non-admin denylist BỎ SÓT `clientReview`/`clientFeedback`/`clientReviewedAt`/`clientUserId` (finding S3-01). Pattern đúng là allowlist (`update-task-details.ts:59-80`).
- Validation không nhất quán: zod chỉ ở review-module routes + 1 file action; ~55 action classic validate thủ công.

## 4. Web security (chi tiết: `parts/sec4-websec.md`)

- **CORS không mở** (0 header Access-Control, same-origin mặc định). **CSRF**: Server Actions dùng origin-check built-in của Next; cookie SameSite=Lax.
- **CSP** (`next.config.ts:48-151`) 3 khối, nhưng script-src có `'unsafe-inline'`+`'unsafe-eval'` (vô hiệu vai trò chống XSS); `/r/` guest gần như không CSP (chỉ frame-ancestors). **Thiếu HSTS** toàn app.
- **Rate-limit** 3 hệ (Upstash fail-closed prod / DB fixed-window / share-link per-IP); staff `/api/review/**` không có rate-limit.
- **Upload**: chặn SVG + cap size + re-check size sau upload; R2 presigned TTL ngắn. **XSS**: hầu hết sink dùng DOMPurify; 1 chỗ raw (`AddTaskModal.tsx:1450`); guest comment render escaped-text (không có sink guest).
- **SSRF**: `api/vdownloader.py` (High — xem H2).

## 5. Secrets & hạ tầng (chi tiết: `parts/sec5-secrets.md`)

- `.env` **gitignore đúng, chưa từng bị commit**; các secret app-level (Resend/Mux/R2/Upstash/Supabase service-role/INTEGRATION_TOKEN_SECRET/REVIEW_COOKIE_SECRET) 0 commit trong history.
- **NHƯNG connection string DB đã lọt history và chưa xoay** (C1 — verified). `env.ts` chỉ validate 3 biến; ~40 secret còn lại đọc ad-hoc.
- Secret của service chết/mồ côi (LiveKit, Cloudflare Stream, Turnstile) vẫn nằm trong `.env` — nên thu hồi khỏi provider.
- 6/7 cron so sánh CRON_SECRET không timing-safe (chỉ auth-cleanup dùng `timingSafeEqual`).

## 6. Sơ đồ kiến trúc bảo mật (chi tiết: `parts/sec6-diagram.md`)

- `diagrams/auth-flow.png` — luồng xác thực 5 nhánh: login → mint JWT HS256 cookie → middleware Edge auth-gate + rolling refresh → DAL verify sessionVersion → guard admin; + 2 nhánh khách `/share` (SHA-256 hash-at-rest, uniform 404) và `/r` (gate chain password bcrypt → unlock JWT → identity → GuestSession).
- `diagrams/trust-boundaries.png` — 5 trust boundary (Public → Edge middleware → Server actions/API → DAL guard → Neon DB) + external services (Mux HMAC/Inngest/R2/Resend/Upstash) là boundary riêng; **vùng ĐỎ** đánh dấu 4 điểm vào không/yếu xác thực đang live.

---

## 7. FINDINGS — xếp hạng (đã dedupe giữa 6 agent)

> Nhiều finding được nhiều agent phát hiện độc lập (ghi mã chéo). ✅ = orchestrator đã verify trực tiếp.

### 🔴 CRITICAL

| ID | Finding | File | Fix |
|---|---|---|---|
| **C1** ✅ | **Connection string Neon prod (role `neondb_owner` full-priv) bị commit vào git history và CHƯA xoay khóa.** Commit `ed46780`+`2c7e226` (reachable từ `main`) thêm `check-user.ts`/`test-neon.ts` hardcode `postgresql://neondb_owner:npg_…@ep-autumn-flower-…`; file đã xoá khỏi HEAD nhưng `git show ed46780:check-user.ts` vẫn đọc được. **Hash mật khẩu khớp `.env` hiện hành** (verify: `20e1a20faa12` = `20e1a20faa12`) → ai đọc được repo GitHub lấy được credential prod còn sống. | `git history` (SEC5-01) | (1) **XOAY NGAY** password Neon `neondb_owner` + cập nhật Vercel env; (2) purge history (BFG/filter-repo); (3) không hardcode connection string vào script |

### 🟠 HIGH

| ID | Finding | File | Fix |
|---|---|---|---|
| **H1** ✅ | `prisma/dev.db` (SQLite) **đang tracked** (verify: `git ls-files` khớp, 5 User rows) — chứa user thật + bcrypt hash + (theo sec5) 2 mật khẩu plaintext. Prod là Neon Postgres nên file này thuần là rò rỉ. | `prisma/dev.db` (SEC5-02) | Xoá khỏi git + gitignore; coi các credential trong đó như đã lộ |
| **H2** ✅ | `api/vdownloader.py` **public không xác thực** — `GET ?url=` đưa thẳng vào yt-dlp `subprocess` (`--no-check-certificate`) = SSRF + open-proxy; `?diagnostic=true` lộ cwd/version. Dead-code (0 caller trong src) nhưng **vẫn deploy sống** (`vercel.json:3-5`). | `api/vdownloader.py:44-46,84,138-161` (SEC2-01/WS-01/SEC5-04) | Xoá file (dead code); nếu giữ: bắt buộc auth + allowlist host |
| **H3** | `updateFrameAccount` guard bất đối xứng — mọi user đăng nhập (kể cả không thuộc workspace) ghi đè credential Frame.io **dùng chung**, lưu plaintext JSON trong `Task.notes_vi`. `getFrameAccount` đòi OWNER/ADMIN nhưng ghi thì mở. | `src/actions/global-settings.ts:54-84` (SEC2-02/S3-02) | Đối xứng guard (đòi OWNER/ADMIN) + mã hóa credential |
| **H4** | `api/scoring.py` auth **fail-open** khi thiếu CRON_SECRET (`if cron_secret and …`) + so sánh không timing-safe; nối thẳng prod DB, batch UPDATE `aiScore/tier` mọi Client. Orphan nhưng POST-able. | `api/scoring.py:12-19,111-115` (SEC5-03/WS-05) | Fail-closed khi thiếu secret; `hmac.compare_digest`; xoá nếu không dùng |
| **H5** | `createNotificationInternal`/`createBulkNotificationsInternal`/`createAndBroadcastNotifications` export từ file `'use server'` → **Server Action public không auth** → tạo notification + gửi email (Resend) + web-push tới userId bất kỳ = phishing qua kênh chính danh. (sec2 xếp Medium, sec3 xếp High — lấy High vì có email+push tới nạn nhân tùy ý.) | `src/actions/notification-actions.ts:24,70,86` (S3-03/SEC2-03) | Tách sang module `server-only` hoặc thêm session gate + kiểm quyền |

### 🟡 MEDIUM

| ID | Finding | File |
|---|---|---|
| **M1** | `/api/profile/select` nhận session-token trong request body (bypass httpOnly) + không check LOCKED/sessionVersion, re-sign cookie mới | `src/app/api/profile/select/route.ts:18-24,66-88` (AUTH-01) |
| **M2** | Rate-limit IP của signup + OTP dùng XFF left-most (client tự đặt) → bypass throttle (login đã hardened nhưng 2 chỗ này sót) | `src/actions/signup-actions.ts:78`, `password-reset-actions.ts:57` (AUTH-02) |
| **M3** | CSP `script-src` bật `'unsafe-inline'`+`'unsafe-eval'` → vô hiệu CSP chống XSS; còn liệt kê host dead-dep | `next.config.ts:92-93` (WS-02) |
| **M4** | `/api/webhooks/calendar` nhận POST không xác thực (verify bị comment) — hiện inert nhưng là cửa mở sẵn | `src/app/api/webhooks/calendar/route.ts:8-45` (SEC2-05/WS-03) |
| **M5** | Thiếu HSTS (Strict-Transport-Security) toàn app | `next.config.ts:48-151` (WS-04) |
| **M6** | `/api/test-email` nhận CRON_SECRET qua query string + lộ prefix RESEND_API_KEY & trạng thái env; tự ghi "DELETE after debugging" nhưng vẫn deploy | `src/app/api/test-email/route.ts:17,28-34` (SEC2-04/WS-06/SEC5-09) |
| **M7** | App kết nối DB bằng role owner `neondb_owner` (full quyền) — không least-privilege | `.env:10` (SEC5-06) |
| **M8** | `JWT_SECRET` là chuỗi yếu/đoán được; guard fail-closed chỉ bắt đúng 1 placeholder (`z.string().min(10)` không ép entropy) | `src/lib/env.ts:31-42` (SEC5-07) |
| **M9** | `updateTask` denylist bỏ sót `clientReview` → mass assignment giả mạo client-approval, qua cổng R5 lộ cut nội bộ ra /r | `src/actions/task-management-actions.ts:35-107` (S3-01) |
| **M10** | `trackEvent` ghi Event vào DB không auth → poison/spam analytics (DoS lưu trữ) | `src/actions/tracking-actions.ts:58-86` (SEC2-06/S3-06) |
| **M11** | `searchContacts` trả email thật của MỌI user toàn hệ thống cho user đăng nhập bất kỳ (oracle liệt kê PII cross-tenant) | `src/actions/contact-actions.ts:14,44` (SEC2-12) |

### 🟢 LOW

| ID | Finding | File |
|---|---|---|
| L1 | 6/7 cron so sánh CRON_SECRET không timing-safe | 6 cron route (SEC2-07/SEC5-08) |
| L2 | GET `/api/auth/logout` không bump sessionVersion → token thiết bị khác sống tới 30 ngày | `logout/route.ts:45` (AUTH-03) |
| L3 | admin `createUser` hash cost 10 + không enforce độ mạnh/HIBP | `create-user.ts:38,87` (AUTH-04) |
| L4 | `loginAction` fail-OPEN khi Upstash ném exception runtime (kể cả prod) | `auth-actions.ts:209-224` (AUTH-05) |
| L5 | GET `/api/auth/role` không check liveness (sessionVersion/LOCKED) | `auth/role/route.ts:15-29` (AUTH-06) |
| L6 | Session TTL 30 ngày dài | `src/lib/auth.ts:6-7` (AUTH-07) |
| L7 | `getPayrollLockStatus` không guard — cross-tenant read boolean isLocked | `bonus-actions.ts:38-61` (SEC2-08/S3-04) |
| L8 | `getWorkspacesForProfile` chỉ getSession — leak metadata workspace cross-tenant | `workspace-actions.ts:134-162` (SEC2-09/S3-05) |
| L9 | GET `/api/notifications/unsubscribe` mutate ngay (mail-scanner prefetch tự huỷ đăng ký) — portal-notify đã fix, route này sót | `notifications/unsubscribe/route.ts:70-80` (SEC2-10/WS-07) |
| L10 | `/api/log-client-error` không auth + không rate-limit (log-flood) | `log-client-error/route.ts:17` (SEC2-11/WS-10) |
| L11 | `/r/[slug]` guest gần như không CSP (chỉ frame-ancestors) | `next.config.ts:145-147` (WS-08) |
| L12 | `AddTaskModal` preview render TipTap HTML RAW thiếu DOMPurify (self-XSS, lệch chuẩn) | `AddTaskModal.tsx:1450` (WS-09) |
| L13 | Comment-attachment Content-Type do client khai, không sniff magic-byte | `comments.ts:562-572` (WS-11) |

## 8. Mapping sang Spring Security khi migrate (nối Phase 2)

| Cơ chế hiện tại | Spring Security |
|---|---|
| JWT jose HS256 cookie httpOnly + sessionVersion | `OncePerRequestFilter` verify nimbus JWT + claim check DB sessionVersion (giữ nguyên cookie contract; migrate HS256→RS256 khi tách BE) |
| `verifyWorkspaceAccess` / `verifyProfileAdminAccess` | `WorkspaceAccessEvaluator` bean (@PreAuthorize + imperative); `requireReviewAccess` giữ imperative trong service |
| Rate-limit Upstash + lockout | bucket4j/Redis + `AuthenticationFailureHandler` đếm lockout |
| CSP/headers `next.config` | `HttpSecurity.headers()` — thêm HSTS, bỏ unsafe-inline (fix M3/M5) |
| Guest token `/share` + `/r` | Filter chain riêng cho anonymous token auth (tách khỏi user JWT chain) |
| Fix trước khi/khi port | C1 (xoay khóa), H2/H4 (bỏ Python function), H3/H5 (siết action) — làm sạch trước để không mang lỗ hổng sang BE mới |

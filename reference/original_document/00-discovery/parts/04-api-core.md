# 04 — Inventory API Core (`src/app/api/**` TRỪ `review/**` và `r/**`)

> Phạm vi: 39 file `route.ts` (Glob `src/app/api/**/route.ts` loại `api/review/**` + `api/r/**`).
> Mỗi route đã được ĐỌC trực tiếp để xác định method export thật và guard thật sự được gọi trong handler (hoặc bên trong server action mà handler ủy quyền — có ghi rõ).
> Chú thích guard: `CRON_SECRET` = so khớp header `x-cron-secret`/`x-cron-key`/`Authorization: Bearer` với `process.env.CRON_SECRET`.

## 1. Domain: auth (10 routes)

| Method | Path | Handler | Guard thật sự | Mục đích |
|---|---|---|---|---|
| POST | `/api/auth/signup` | `src/app/api/auth/signup/route.ts:16` | KHÔNG session (pre-auth, đúng thiết kế) — chống bot bằng Vercel BotID `checkBotId()` trong action (`src/actions/signup-actions.ts:178`) + rate limit + honeypot | Đăng ký tài khoản mới, anti-enumeration (luôn 200) |
| POST | `/api/auth/forgot-password` | `src/app/api/auth/forgot-password/route.ts:12` | KHÔNG session (pre-auth) — rate limit nội bộ 3/email/h, 10/IP/h, cooldown 60s trong `requestPasswordResetOtp` (`src/actions/password-reset-actions.ts:15`) | Gửi OTP reset mật khẩu, anti-enumeration |
| POST | `/api/auth/verify-otp` | `src/app/api/auth/verify-otp/route.ts:11` | OTP là credential — hash SHA-256, TTL 10 phút, max 5 attempts (`src/actions/password-reset-actions.ts:13`) | Đổi OTP lấy resetToken |
| POST | `/api/auth/reset-password` | `src/app/api/auth/reset-password/route.ts:12` | resetToken là credential (verify trong `resetPasswordWithToken`); HIBP + ≥12 ký tự; bump sessionVersion | Đặt mật khẩu mới bằng resetToken |
| GET, POST | `/api/auth/verify-email` | GET `src/app/api/auth/verify-email/route.ts:79`, POST `:90` | Token là credential — hash lookup, one-time (`usedAt` optimistic lock `:38-48`), expiry check `:29` | Xác thực email; GET redirect về /login, POST trả JSON |
| POST | `/api/auth/migrate-email` | `src/app/api/auth/migrate-email/route.ts:16` | `getSession()` BÊN TRONG action (`src/actions/email-migration-actions.ts:67`) — route tự nó không check | Đổi email tài khoản legacy (request OTP / verify OTP) |
| GET | `/api/auth/google/authorize` | `src/app/api/auth/google/authorize/route.ts:14` | KHÔNG (pre-auth, đúng thiết kế) — set CSRF `g_oauth_state` cookie httpOnly 5 phút (`:32-38`) | Bắt đầu Google Sign-In (redirect sang Google) |
| GET | `/api/auth/google/callback` | `src/app/api/auth/google/callback/route.ts:27` | CSRF state cookie so khớp param (`:38`), chỉ nhận email đã verified (`:49`), chặn role LOCKED/CLIENT (`:66-67`) | Callback Google Sign-In → tạo/link user → set session |
| GET | `/api/auth/role` | `src/app/api/auth/role/route.ts:6` | Decrypt session cookie trực tiếp (`:9-18`) → 401 nếu không có | Trả role + isTreasurer của user hiện tại |
| GET | `/api/auth/logout` | `src/app/api/auth/logout/route.ts:14` | Không cần guard (chỉ xoá session của chính mình); đọc session để ghi audit `auth.logout` trước khi clear | Logout + audit log |

## 2. Domain: cron (7 routes — cả 7 đều có lịch trong `vercel.json:22-49`)

| Method | Path | Handler | Guard thật sự | Mục đích |
|---|---|---|---|---|
| GET | `/api/cron/auth-cleanup` | `src/app/api/cron/auth-cleanup/route.ts:27` | CRON_SECRET — **duy nhất route dùng `timingSafeEqual`** (`:37`) | Xoá token verify-email hết hạn, OTP cũ, LoginAttempt >90 ngày |
| GET | `/api/cron/check-deadline` | `src/app/api/cron/check-deadline/route.ts:14` | CRON_SECRET (so sánh `!==` thường, `:28`) | Notify deadline 1h/24h + đánh dấu task `Quá hạn` |
| GET | `/api/cron/cleanup-notifications` | `src/app/api/cron/cleanup-notifications/route.ts:11` | CRON_SECRET (`:25`) | Xoá notification archived >30d, read >90d |
| GET | `/api/cron/hard-delete-profiles` | `src/app/api/cron/hard-delete-profiles/route.ts:20` | CRON_SECRET (`:34`) | Hard-delete profile SOFT_DELETED quá 30 ngày grace (cascade) |
| GET | `/api/cron/hard-delete-workspaces` | `src/app/api/cron/hard-delete-workspaces/route.ts:20` | CRON_SECRET (`:34`) | Hard-delete workspace SOFT_DELETED quá grace window (cascade) |
| GET | `/api/cron/review-janitor` | `src/app/api/cron/review-janitor/route.ts:13` | CRON_SECRET (`:26`) | Bắn 1 event Inngest `JANITOR_REQUESTED` (dọn dẹp review module chạy trong Inngest) |
| GET | `/api/cron/send-digest` | `src/app/api/cron/send-digest/route.ts:11` | CRON_SECRET (`:25`) | Gửi email digest HOURLY mỗi giờ; DAILY lúc 01:00 UTC |

Ghi chú: 6/7 route so sánh secret bằng `!==` thường; chỉ `auth-cleanup` dùng `timingSafeEqual` (chính comment trong file gọi đó là "H1 fix" chống timing side-channel) — các route còn lại chưa đồng bộ theo. Rủi ro thực tế thấp nhưng là sự thiếu nhất quán.

## 3. Domain: webhooks (2 routes)

| Method | Path | Handler | Guard thật sự | Mục đích |
|---|---|---|---|---|
| POST | `/api/webhooks/mux` | `src/app/api/webhooks/mux/route.ts:50` | HMAC-SHA256 chữ ký `Mux-Signature` ±5 phút, fail-closed 401 (`:54`, verify `:23-48` dùng `timingSafeEqual`); idempotent qua ledger `WebhookEvent` (`:74-79`) | Nhận webhook Mux → ghi ledger → bắn Inngest event |
| POST | `/api/webhooks/calendar` | `src/app/api/webhooks/calendar/route.ts:8` | **KHÔNG** — verify bị comment out (`:10-11`), body được `console.log` (`:21`), toàn bộ logic xử lý là TODO/comment (`:23-40`) | Stub nhận push notification Google Calendar / Microsoft Graph (chưa hoàn thiện) |

## 4. Domain: integrations (5 routes)

| Method | Path | Handler | Guard thật sự | Mục đích |
|---|---|---|---|---|
| GET | `/api/integrations/dropbox/authorize` | `src/app/api/integrations/dropbox/authorize/route.ts:5` | `getSession()` (`:6-9`) | Bắt đầu OAuth Dropbox — state = base64url {userId, workspaceId, nonce} |
| GET | `/api/integrations/dropbox/callback` | `src/app/api/integrations/dropbox/callback/route.ts:19` | `getSession()` + so khớp `session.user.id === state.userId` (`:61-67`) | Đổi code lấy token Dropbox, mã hoá AES-256-GCM, upsert IntegrationToken |
| GET | `/api/integrations/google-drive/authorize` | `src/app/api/integrations/google-drive/authorize/route.ts:5` | `getSession()` (`:6-9`) | Bắt đầu OAuth Google Drive (drive.readonly) |
| GET | `/api/integrations/google-drive/callback` | `src/app/api/integrations/google-drive/callback/route.ts:23` | `getSession()` + so khớp `state.userId` (`:63-66`) | Đổi code lấy token Drive, mã hoá, upsert IntegrationToken |
| POST | `/api/integrations/scan-folder` | `src/app/api/integrations/scan-folder/route.ts:58` | `getSession()` (`:62`) + `verifyWorkspaceAccess(workspaceId,'MEMBER')` (`:101`) + `limitDb` 10 lần/60s (`:116`); `maxDuration=300` | Scan folder Dropbox/Drive → danh sách video (Velox Quick Create, có engine v4 opt-in) |

Ghi chú: 2 route `authorize` của integrations dùng state **base64url KHÔNG ký/không mã hoá** (comment trong dropbox/authorize `:22` nói "encrypted to prevent tampering" nhưng code chỉ base64 — `route.ts:28`); bù lại callback bắt buộc session hiện tại phải trùng `state.userId` nên không dẫn tới chiếm quyền, chỉ là comment sai với thực tế.

## 5. Domain: share (2 routes — token là credential, không session)

| Method | Path | Handler | Guard thật sự | Mục đích |
|---|---|---|---|---|
| GET, HEAD | `/api/share/[token]/download-zip` | GET `src/app/api/share/[token]/download-zip/route.ts:87`, HEAD `:83` (405) | `resolveShareToken()` (`:91` — hash-at-rest, revocation, expiry, per-IP limit) + `limitDb` 12/600s fail-closed (`:98`); file set lấy từ snapshot đã authorize `getDocumentsViaToken()` | Client tải cả folder deliverables thành 1 zip streaming (STORE mode, max 1000 file / 20 GB) |
| GET, HEAD | `/api/share/[token]/invoices/[id]/pdf` | GET `src/app/api/share/[token]/invoices/[id]/pdf/route.ts:51`, HEAD `:47` (405) | `resolveShareToken()` (`:60`) + `limitDb` 10/300s fail-closed (`:68`) + predicate `clientId ∈ scope.clientIds AND workspaceId ∈ scope.workspaceIds` (`:76-83`); mọi fail đều 404 đồng nhất | Client tải PDF invoice qua share link (ưu tiên file PDF gốc đã upload) |

## 6. Domain: invoices (2 routes — staff)

| Method | Path | Handler | Guard thật sự | Mục đích |
|---|---|---|---|---|
| POST | `/api/invoices/generate` | `src/app/api/invoices/generate/route.ts:5` | `verifyFinanceAccess(workspaceId)` (`:17`) | Sinh PDF invoice từ data trong body (staff finance) |
| GET | `/api/invoices/[id]/download` | `src/app/api/invoices/[id]/download/route.ts:6` | `verifyFinanceAccess(workspaceId)` (`:23`) + check IDOR workspaceId của invoice (`:49-52`) | Tải lại PDF invoice đã lưu trong DB (staff finance) |

## 7. Domain: exports (1 route)

| Method | Path | Handler | Guard thật sự | Mục đích |
|---|---|---|---|---|
| GET | `/api/exports/monthly-tasks-xlsx` | `src/app/api/exports/monthly-tasks-xlsx/route.ts:86` | `getCurrentUser()` (`:95`) + `verifyWorkspaceAccess(workspaceId,'ADMIN')` (`:103`) + chặn cross-profile (`:120-122`) | Xuất Excel task theo tháng (múi giờ VN) cho 1 workspace |

## 8. Domain: notifications / portal-notify (2 routes — token unsubscribe)

| Method | Path | Handler | Guard thật sự | Mục đích |
|---|---|---|---|---|
| GET | `/api/notifications/unsubscribe` | `src/app/api/notifications/unsubscribe/route.ts:41` | JWT unsubscribe token là credential (`verifyUnsubscribeToken` `:56`) | One-click unsubscribe email notify nội bộ → tắt `emailEnabled`, render trang HTML xác nhận |
| POST, GET | `/api/portal-notify/unsubscribe` | POST `src/app/api/portal-notify/unsubscribe/route.ts:10`, GET `:16` | Token verify trong `unsubscribePortalNotify`; **GET không mutate** — chỉ redirect sang trang confirm (chống mail-scanner prefetch, finding P4-R4) | RFC 8058 one-click unsubscribe cho email notify portal khách |

Ghi chú nhất quán: `notifications/unsubscribe` **GET mutate trực tiếp** (upsert tắt email ngay tại `:70-80`) trong khi `portal-notify/unsubscribe` đã sửa đúng chuẩn GET-không-mutate. Mail scanner prefetch GET có thể tự unsubscribe user nội bộ — cùng lỗi P4-R4 đã vá ở portal nhưng chưa vá ở đây.

## 9. Domain: inngest (1 route)

| Method | Path | Handler | Guard thật sự | Mục đích |
|---|---|---|---|---|
| GET, POST, PUT | `/api/inngest` | `src/app/api/inngest/route.ts:17` | Inngest tự verify request bằng `INNGEST_SIGNING_KEY` (comment `:2-3`); `maxDuration=800` | Serve endpoint host toàn bộ Inngest functions của review module |

## 10. Domain: misc (7 routes)

| Method | Path | Handler | Guard thật sự | Mục đích |
|---|---|---|---|---|
| POST | `/api/profile/select` | `src/app/api/profile/select/route.ts:6` | `getSession()` HOẶC decrypt `sessionToken` từ body (`:15-24`, workaround Vercel edge cache) + check membership profile / `ProfileAccess` (`:43-55`) | Chuyển team: re-sign JWT session nhúng `sessionProfileId` |
| GET | `/api/workspace/first` | `src/app/api/workspace/first/route.ts:12` | `getSession()` (`:13-16`) | Trả workspace đầu tiên + view (admin/dashboard) cho 1 profileId |
| GET | `/api/exchange-rate` | `src/app/api/exchange-rate/route.ts:4` | KHÔNG (public read-only, fallback 26300) | Trả tỷ giá USD/VND |
| GET | `/api/time` | `src/app/api/time/route.ts:5` | KHÔNG (public read-only) | Trả `Date.now()` server (đồng bộ clock client) |
| POST | `/api/log-client-error` | `src/app/api/log-client-error/route.ts:17` | **KHÔNG** — chủ đích (phải log được cả khi /login crash); KHÔNG rate limit (tự nhận trong comment `:15`) | Nhận báo lỗi client-side từ `global-error.tsx` → console.error lên Vercel logs |
| GET | `/api/test-email` | `src/app/api/test-email/route.ts:11` | CRON_SECRET — nhưng nhận cả qua **query param `?secret=`** (`:17`) | Endpoint chẩn đoán pipeline email (Resend); comment tự ghi "DELETE after debugging" (`:3`) |
| GET | `/api/import-jan-2026` | `src/app/api/import-jan-2026/route.ts:13` | KHÔNG — nhưng đã FROZEN, luôn trả 410 | Importer Excel một lần (Jan-2026) đã đóng băng; implementation gốc chỉ còn trong git history |

## 11. Routes NGHI VẤN / THIẾU guard — tổng hợp

| # | Route | Vấn đề | Mức độ |
|---|---|---|---|
| 1 | `/api/webhooks/calendar` (`src/app/api/webhooks/calendar/route.ts:8`) | **Không có bất kỳ verification nào** — dòng verify bị comment out (`:10-11`), ai cũng POST được; hiện chỉ log payload + trả success (logic thật là TODO), nhưng nếu ai hoàn thiện TODO mà quên guard thì attacker tạo được `ScheduleException` tùy ý. Không có file nào trong `src/` tham chiếu URL này (grep `webhooks/calendar` → 0 kết quả) → **dead-code candidate / stub bỏ quên** | Trung bình (hiện vô hại, nhưng là cửa mở sẵn) |
| 2 | `/api/test-email` (`src/app/api/test-email/route.ts:17`) | Có CRON_SECRET nhưng chấp nhận secret qua **query string** → secret có thể lộ vào access log / browser history / referrer; file tự ghi chú "DELETE after debugging" mà vẫn còn deploy; response lộ prefix 6 ký tự của `RESEND_API_KEY` + toàn bộ trạng thái env (`:28-34`) | Trung bình |
| 3 | `/api/notifications/unsubscribe` (`src/app/api/notifications/unsubscribe/route.ts:41`) | GET mutate (tắt email notify ngay) — mail-scanner prefetch có thể unsubscribe nhầm; chính repo đã nhận diện lỗi này (finding P4-R4) và sửa cho `portal-notify` nhưng bỏ sót route này | Thấp–Trung bình |
| 4 | `/api/log-client-error` (`src/app/api/log-client-error/route.ts:17`) | Không auth + không rate limit → vector spam/flood Vercel logs (đã có comment thừa nhận trade-off) | Thấp |
| 5 | `/api/profile/select` (`src/app/api/profile/select/route.ts:18-24`) | Pattern bất thường: chấp nhận `sessionToken` trong **body** làm fallback (workaround Vercel). Token vẫn phải decrypt hợp lệ bằng JWT secret nên không phải bypass, nhưng mở surface cho token replay từ nguồn khác cookie (không bị SameSite/httpOnly bảo vệ) | Thấp |
| 6 | 6/7 cron route so sánh CRON_SECRET bằng `!==` thường | Chỉ `auth-cleanup` dùng `timingSafeEqual` (`src/app/api/cron/auth-cleanup/route.ts:37`); các route khác (vd `check-deadline:28`, `send-digest:25`) chưa đồng bộ theo "H1 fix" | Thấp |
| 7 | `/api/import-jan-2026` | Dead-code candidate — luôn 410, giữ lại chỉ để trả thông báo frozen | Thông tin |
| 8 | `/api/exchange-rate`, `/api/time` | Public không guard — read-only, không lộ dữ liệu tenant | Chấp nhận được |
| 9 | Comment sai thực tế ở `src/app/api/integrations/dropbox/authorize/route.ts:22` | Ghi "encrypted to prevent tampering" nhưng state chỉ là base64url (không ký, không mã hoá — `:28`); an toàn thực tế nhờ callback so khớp session (`callback/route.ts:62`), song comment gây hiểu nhầm cho maintainer | Thông tin |

## 12. Ghi chú kiểm chứng

- Tổng route trong scope: **39** (auth 10, cron 7, webhooks 2, integrations 5, share 2, invoices 2, exports 1, notifications 1, portal-notify 1, inngest 1, misc 7).
- Cả 7 cron route đều có lịch thật trong `vercel.json:22-49` — không có cron mồ côi.
- Không phát hiện 2 phiên bản trùng chức năng trong scope này, trừ cặp unsubscribe (notifications vs portal-notify) là 2 hệ email khác nhau (nội bộ vs portal khách) — cả 2 đều đang được dùng, không phải dead code; khác biệt nằm ở chuẩn GET-mutate (mục 11.3).
- `middleware` không cover `/api` (ghi nhận tại `src/app/api/inngest/route.ts:3`: "middleware already excludes /api entirely") → guard của từng route là **tuyến phòng thủ duy nhất**.

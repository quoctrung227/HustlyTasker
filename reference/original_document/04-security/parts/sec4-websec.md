# 04 — Bảo mật Web (§4): CORS · CSRF · CSP/Headers · Rate-limit · Upload · XSS · SSRF

> Phạm vi: bảo mật tầng web ĐANG CÓ THẬT trong code (không lý thuyết). Mọi kết luận + finding kèm `file:line`. Ngày audit 2026-08-02, worktree `cranky-austin`. KHÔNG sửa code — chỉ mô tả + đề xuất.
> Đã tự verify trên code hiện tại (không tin audit cũ nguyên trạng). Các file build-mirror trong `electron/release/win-unpacked/**` bị loại trừ (bản sao đóng gói, không phải nguồn deploy).

---

## 0. Tóm tắt điều hành

| # | Finding | Mức | File chính |
|---|---|---|---|
| WS-01 | `api/vdownloader.py` — SSRF + open-proxy, KHÔNG xác thực | **High** | `api/vdownloader.py:44-46,84,138-161` |
| WS-02 | CSP `script-src` bật `'unsafe-inline'` + `'unsafe-eval'` (vô hiệu CSP chống XSS) | **Medium** | `next.config.ts:92-93` |
| WS-03 | `/api/webhooks/calendar` nhận POST không xác thực (verify bị comment) | **Medium** | `src/app/api/webhooks/calendar/route.ts:8,11,21` |
| WS-04 | Thiếu HSTS (`Strict-Transport-Security`) toàn app | **Medium** | `next.config.ts:48-151` |
| WS-05 | `api/scoring.py` — auth fail-OPEN khi thiếu secret + so sánh không timing-safe | **Medium** | `api/scoring.py:12-19` |
| WS-06 | `/api/test-email` nhận CRON_SECRET qua query string + lộ trạng thái env | **Medium** | `src/app/api/test-email/route.ts:3,17,28-34` |
| WS-07 | `/api/notifications/unsubscribe` GET mutate (mail-scanner prefetch tự huỷ đăng ký) | **Low** | `src/app/api/notifications/unsubscribe/route.ts:41,70-80` |
| WS-08 | `/r/[slug]` guest gần như KHÔNG có CSP (chỉ `frame-ancestors`) | **Low** | `next.config.ts:145-147` |
| WS-09 | `AddTaskModal` preview render TipTap HTML RAW (thiếu DOMPurify, lệch chuẩn) | **Low** | `src/components/dashboard/AddTaskModal.tsx:1450` |
| WS-10 | `/api/log-client-error` không auth + không rate-limit | **Low** | `src/app/api/log-client-error/route.ts:15,17` |
| WS-11 | Comment-attachment Content-Type do client khai, không verify nội dung | **Low** | `src/lib/review/comments.ts:562-572` |

**Điểm mạnh đã verify (không phải finding):** CORS không cấu hình → mặc định same-origin, không header `Access-Control-*` nào (grep toàn repo = 0); Server Actions dựa vào origin-check built-in của Next (không disable, không set `allowedOrigins` → mặc định an toàn); cookie `session` httpOnly + SameSite=Lax + Secure(prod); rate-limit auth fail-CLOSED trong production; webhook Mux verify HMAC timing-safe fail-closed; upload chặn SVG + cap size + tái kiểm size sau upload; guest comment render escaped-text (React).

---

## (a) CORS — cấu hình thật

| Câu hỏi | Kết luận | Bằng chứng |
|---|---|---|
| `next.config` có set CORS header? | **KHÔNG** — `headers()` chỉ set CSP/XCTO/Referrer/Permissions/X-Frame-Options; không có `Access-Control-*` | `next.config.ts:48-151` |
| Route nào trả `Access-Control-Allow-*`? | **KHÔNG có route nào** — grep `Access-Control` toàn repo (kể cả build-mirror) = 0 kết quả | grep repo-wide |
| Hệ quả | Mặc định Next = **same-origin**. Không có endpoint nào mở CORS cho origin ngoài → không lộ API cho site khác qua CORS. **Không finding.** | — |

CSRF-liên-quan: vì không có CORS cho phép cross-origin, cộng SameSite=Lax, bề mặt tấn công CSRF chỉ còn ở các endpoint **GET-mutate** (xem WS-07).

---

## (b) CSRF

| Cơ chế | Trạng thái thật | Bằng chứng |
|---|---|---|
| Server Actions (Next) | Dựa vào **origin-check built-in** của Next (so Origin vs Host). `next.config.ts` KHÔNG set `experimental.serverActions.allowedOrigins` và KHÔNG disable → mặc định bật (grep `serverActions`/`allowedOrigins` = 0). Mutation chính của app đi qua server actions → được bảo vệ mặc định. | `next.config.ts` (không có override); grep repo |
| Cookie session | `httpOnly:true`, `sameSite:'lax'`, `secure` (prod, không Electron), `path:'/'` | `src/lib/auth.ts:23-29,42-45` |
| Đủ SameSite=Lax cho endpoint nhạy cảm? | Lax chặn POST cross-site nhưng **KHÔNG** chặn GET top-level cross-site (trình duyệt vẫn gửi cookie). Các POST route nhạy cảm auth bằng session vẫn an toàn nhờ POST+Lax; điểm yếu là các **GET có side-effect** | (xem WS-07) |
| POST route thủ công chống CSRF | Phần lớn dùng token-là-credential (webhook HMAC, share token, unsubscribe token, OTP) → không phụ thuộc cookie nên CSRF không áp dụng. Ngoại lệ cần chú ý: `/api/profile/select` chấp nhận `sessionToken` trong **body** (`route.ts:15-24`) — vẫn phải decrypt hợp lệ nên không bypass, nhưng mở surface token-replay ngoài cookie | `src/app/api/profile/select/route.ts:15-24` |

**Finding CSRF: WS-07** — GET-mutate `/api/notifications/unsubscribe` (chi tiết mục dưới).

---

## (c) CSP + security headers

Toàn bộ trong `next.config.ts` `async headers()` (`:48-151`). Ba khối rule:

### Khối 1 — `source: '/(.*)'` (áp mọi route, kể cả /share)
| Header | Giá trị thật | Ghi chú |
|---|---|---|
| Content-Security-Policy | `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' *.vercel-scripts.com; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data: *.vercel-storage.com … *.supabase.co images.unsplash.com https://*.mux.com https://*.r2.cloudflarestorage.com; font-src 'self' data:; connect-src 'self' *.vercel-storage.com wss://*.livekit.cloud https://*.livekit.cloud https://*.r2.cloudflarestorage.com https://*.mux.com; media-src 'self' blob: https://*.mux.com; frame-src 'self' *.frame.io https://*.r2.cloudflarestorage.com; upgrade-insecure-requests;` | `next.config.ts:93`. **`'unsafe-inline'`+`'unsafe-eval'` → WS-02.** `wss/https *.livekit.cloud` + `*.frame.io` là host **dead-dep** (LiveKit gỡ, frame.io bị thay) — nợ vệ sinh CSP |
| X-Content-Type-Options | `nosniff` | `next.config.ts:96-98` — OK |
| Referrer-Policy | `origin-when-cross-origin` | `next.config.ts:100-102`; riêng /share + /r middleware set `no-referrer` (token trong URL) `src/middleware.ts:48,63` |
| Permissions-Policy | `camera=(self), microphone=(self), display-capture=(self), geolocation=()` | `next.config.ts:104-106` — OK |
| Strict-Transport-Security | **KHÔNG có** (grep toàn repo = 0) | **→ WS-04** |

### Khối 2 — `source: '/((?!r/).*)'` → `X-Frame-Options: DENY` (mọi route TRỪ /r/)
`next.config.ts:128-136`. Chống clickjacking cho staff + /share.

### Khối 3 — `source: '/r/:path*'` → `X-Frame-Options: SAMEORIGIN` + CSP `frame-ancestors 'self';`
`next.config.ts:138-149`. **Rule này GHI ĐÈ (replace) CSP toàn cục cho /r/** (Next overwrite header trùng key từ rule khớp sau) — nên trang guest /r/ **chỉ có `frame-ancestors 'self'`, KHÔNG có default-src/script-src/media-src** (chủ đích để hls.js dùng blob: worker). Đây là bề mặt public lớn nhất mà lại không có CSP backstop → **WS-08**. Comment trong file mô tả đúng hành vi replace (`:116-124`).

CSP cho /r/ **KHÁC** staff/share: staff+share = policy đầy đủ (khối 1); /r/ = chỉ frame-ancestors. Có phân biệt, nhưng phân biệt theo hướng /r/ **lỏng hơn**.

---

## (d) Rate limiting

Ba hệ rate-limit song song:

| Hệ | File | Backend | Fail-open/closed | Dùng ở đâu |
|---|---|---|---|---|
| Upstash Redis | `src/lib/rate-limit-upstash.ts` | Upstash (persistent, chống cold-start reset) | **fail-CLOSED trong production**, fail-open dev (`:38,159-162`) | auth: signup IP/email (5/h, 3/h), login IP (10/m), OTP email/IP (3/h,10/h), invite (5/24h) + caller (40/h) `:167-279` |
| DB fixed-window | `src/lib/review/rate-limit-db.ts` | Postgres `RateLimitBucket` (upsert atomic) | fail-OPEN cho read, `failClosed:true` cho unlock (`:44-45`); IP lấy `x-real-ip`→`x-vercel-forwarded-for`→phần PHẢI nhất XFF (fix G1) | toàn bộ guest `/api/r/**`; `scan-folder` 10/60s `route.ts:116`; share download-zip/invoice-pdf |
| Share-link per-IP/per-token | `src/lib/share-link-auth.ts` | Postgres | **fail-OPEN** (240/min IP trước lookup, 2000/min token-hash sau) `:106-134` | `/share/[token]` portal khách |

**Endpoint nhạy cảm KHÔNG có rate-limit:**
- **Staff `/api/review/**` (44 route): KHÔNG có rate-limit nào** (grep `limitDb` trong `src/app/api/review/**` = 0) — chỉ session-gated. Chấp nhận được cho nội bộ nhưng là gap nếu tài khoản nhân viên bị chiếm.
- `/api/log-client-error`: không auth + không rate-limit → **WS-10**.
- `/api/webhooks/calendar`: không auth (stub) → **WS-03**.
- `GET /api/r/[slug]/notifications`: guest route duy nhất không limitDb (chỉ đọc own-session) — chấp nhận được.

Guest unlock (brute-force mật khẩu share) fail-CLOSED đúng (`unlock/route.ts:25` 5/60s `failClosed:true`). OTP/PIN đều có cap sai + cooldown + neutral response chống enumeration.

---

## (e) File upload

| Loại | Validate mime/size ở đâu | Lưu / truy cập | Bằng chứng |
|---|---|---|---|
| Video/asset (review) | `initiateUpload`: `sizeBytes>0`, `mediaKindFromMime`, `sizeBytes ≤ capForKind(kind)` (`:132-135`). **Presigned PUT/parts KHÔNG pin Content-Length** → object thật có thể vượt cap; `completeUpload` tái kiểm size thật → 413 `FILE_TOO_LARGE` (`:527-536`). Magic-byte sniff video ở Inngest `reviewProcessUpload` (non-video → FAILED) | R2 (multipart). Truy cập nội bộ qua presigned GET (`getVersionDownloadUrl`, auth workspace); guest qua Mux signed token / presigned R2 TTL min(6h, hạn share) | `src/lib/review/upload-service.ts:132-135,527-536`; `src/lib/review/inngest.ts:379-411` |
| Comment attachment | `initiateAttachment`: ép `^image/` **và chặn SVG** (HT-020, SVG có thể chứa `<script>`) `:562-564`; size ≤ `MAX_ATTACH_BYTES` (10MB) `:565-568` | R2 key nhúng `userId` (claim-by-prefix) `:548-550`; PUT TTL 1h `:571`; GET presigned 15' re-check qua comment→version→asset→workspace `:577-583` | `src/lib/review/comments.ts:548-583` |
| Presigned TTL R2 | `presignGetObject`/`presignPutObject` default 24h (`r2.ts:66,81,141`) nhưng caller override ngắn (attachment 1h PUT / 15' GET; guest media min(6h)). Endpoint R2 **pin cứng** `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com` (không r2.dev escape) — khớp lý do wildcard CSP an toàn | `src/lib/review/r2.ts:25-28,66,81,130-141` |

**Gap còn lại → WS-11:** mimeType comment-attachment do **client khai** và trở thành Content-Type của object R2; không verify magic-byte cho ảnh. Giảm nhẹ bởi: chặn SVG + `nosniff` toàn cục + render qua `<img>` (không execute HTML). Rủi ro Low.

Ai truy cập file: mọi presigned đều re-check quyền trước khi cấp URL; guest chỉ thấy version trong `ShareLinkItem` scope; download gốc bản khách có gate `allowDownload && (!downloadOnlyWhenApproved || APPROVED)` (`r/[slug]/download-url/route.ts:30,44-46`); ảnh preview guest bị downscale+watermark (fix B1).

---

## (f) XSS — điểm render HTML thô

6 chỗ `dangerouslySetInnerHTML` (grep `src/`):

| File:line | Nội dung inject | Sanitize? | Đánh giá |
|---|---|---|---|
| `src/components/tasks/TaskDetailModal.tsx:753` | `form.notes` | `DOMPurify.sanitize()` | An toàn |
| `src/components/tasks/TaskDetailMobile.tsx:448` | `form.notes` | `DOMPurify.sanitize()` | An toàn |
| `src/components/mobile/TaskDrawer.tsx:199-206` | `task.notes_vi/notes_en` | `ensureExternalLinks(DOMPurify.sanitize(...))` | An toàn |
| `src/components/tasks/TaskCommentThread.tsx:263` | `renderCommentMarkdown(t)` | Renderer escape-first + tag cố định + DOMPurify (browser) | An toàn — xem dưới |
| `src/components/landing/LandingPage.tsx:232-237` | hằng chuỗi JS tĩnh (thêm class `js`) | Không cần (không có dữ liệu user) | An toàn |
| `src/components/dashboard/AddTaskModal.tsx:1450` | `form.notes` (TipTap HTML) **RAW** | **KHÔNG** (component không import DOMPurify) | **→ WS-09** |

**`renderCommentMarkdown` (`src/lib/comment-markdown.ts`):** thiết kế đúng — `escapeHtml` TRƯỚC (`:20-26,44`), sau đó chỉ THÊM tag từ tập cố định `ALLOWED_TAGS` với href validate `safeHref` (chỉ http(s)/mailto, `:29-33`), DOMPurify defense-in-depth khi có `window` (`:84-88`). An toàn cả SSR (trả escaped) lẫn client.

**Guest review (/r/):** comment body render **plain-text** qua React `{comment.body}` (`src/components/review/player/CommentItem.tsx:221`) → React auto-escape → **không có sink dangerouslySetInnerHTML nào cho nội dung guest**. Đây là lý do việc /r/ thiếu CSP (WS-08) chưa thành XSS thực tế, nhưng vẫn mất lớp phòng thủ.

---

## (g) SSRF

| Bề mặt | URL/host đến từ đâu | Kiểm soát | Kết luận |
|---|---|---|---|
| `api/vdownloader.py` | **`?url=` tuỳ ý từ client, KHÔNG auth** → `yt_dlp.extract_info(url)` + subprocess `yt-dlp … url` với `--no-check-certificate` | Không allowlist host, không verify TLS, không auth | **SSRF + open-proxy → WS-01** |
| `api/integrations/scan-folder` | `body.url` | `parseCloudLink(url)` chỉ nhận link Dropbox/Drive (khác → 400 `:127-136`); request đi tới **API provider** với OAuth token của caller, KHÔNG fetch URL thô; có session + `verifyWorkspaceAccess('MEMBER')` + limitDb 10/60s | **An toàn** |
| `api/exchange-rate` | Không nhận input (GET rỗng); `getExchangeRate()` gọi FX API cố định server-side | Không có input user | **An toàn** |
| `api/time` | Trả `Date.now()` server, không fetch ngoài | — | **An toàn** |
| `api/webhooks/calendar` | Không fetch ngoài (stub log payload) | Không auth (WS-03) — nhưng không phải SSRF | Xem WS-03 |
| Integration OAuth callback | `state` base64url không ký (comment `dropbox/authorize:22` sai — chỉ base64 `:28`), nhưng callback bắt `session.user.id === state.userId` (`callback:61-67`) → không chiếm quyền, không SSRF | Có ràng buộc session | An toàn (comment gây hiểu nhầm) |

---

## Chi tiết finding

### WS-01 (High) — `api/vdownloader.py`: SSRF + open-proxy, không xác thực
- **Bằng chứng:** `do_GET` không có bất kỳ auth check nào (`api/vdownloader.py:45`). `video_url = params.get('url')` (`:84`) → `yt_dlp.YoutubeDL(...).extract_info(video_url)` (`:138-139`) và subprocess `["yt-dlp", …, video_url]` với `--no-check-certificate` (`:151-161`). Deploy sống trên Vercel (`vercel.json:3-5` `api/*.py`, maxDuration 10). Chế độ `?diagnostic=true` lộ `python version`, `cwd`, `ffmpeg version` (`:71-76`).
- **Rủi ro:** yt-dlp generic-extractor có thể fetch URL http(s) tuỳ ý → SSRF tới dịch vụ nội bộ / cloud metadata; dùng server làm proxy tải nội dung tuỳ ý (lạm dụng băng thông/compute, chi phí); info-disclosure qua diagnostic. Endpoint là dead-code (grep `vdownloader` trong `src/` = 0) nhưng vẫn là function sống.
- **Fix:** Xoá `api/vdownloader.py` (dead code, ưu tiên cao nhất). Nếu giữ: bắt buộc auth (session hoặc header CRON_SECRET timing-safe), allowlist host về YouTube/nhà cung cấp đã biết, bỏ `--no-check-certificate`, gỡ nhánh diagnostic.

### WS-02 (Medium) — CSP cho phép `'unsafe-inline'` + `'unsafe-eval'`
- **Bằng chứng:** `next.config.ts:93` `script-src 'self' 'unsafe-inline' 'unsafe-eval' *.vercel-scripts.com`.
- **Rủi ro:** `'unsafe-inline'` vô hiệu CSP như lớp chống XSS (script inject inline vẫn chạy); `'unsafe-eval'` mở rộng bề mặt. Kết hợp WS-08 (/r/ không CSP), CSP hiện gần như không đóng vai trò mitigation.
- **Fix:** chuyển sang nonce/hash-based `script-src`, bỏ `'unsafe-inline'`; xác minh lib nào cần `'unsafe-eval'` rồi loại nếu không cần.

### WS-03 (Medium) — `/api/webhooks/calendar` nhận POST không xác thực
- **Bằng chứng:** `src/app/api/webhooks/calendar/route.ts:8` handler POST; verify bị comment (`:10-11`); `console.log` payload (`:21`); xử lý thật là TODO (`:23-40`). Không file `src/` nào tham chiếu URL này.
- **Rủi ro:** hiện vô hại (chỉ log + trả success), nhưng là cửa mở sẵn — ai hoàn thiện TODO tạo `ScheduleException` mà quên guard là thành lỗ hổng ghi dữ liệu; đồng thời là vector log-flood.
- **Fix:** gỡ stub, hoặc thêm verify (Graph clientState / signature) trước khi hoàn thiện.

### WS-04 (Medium) — Thiếu HSTS
- **Bằng chứng:** `next.config.ts headers()` (`:48-151`) không có `Strict-Transport-Security`; grep toàn repo = 0. `upgrade-insecure-requests` chỉ ở CSP khối 1, vắng ở /r/ (WS-08).
- **Rủi ro:** không ép HTTPS ở tầng app → cửa sổ SSL-strip/downgrade cho lần truy cập đầu. (Vercel CÓ THỂ tự thêm HSTS ở edge cho custom domain — cần verify trên `hustlytasker.xyz`.)
- **Fix:** thêm `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` trong `headers()`.

### WS-05 (Medium) — `api/scoring.py`: auth fail-OPEN + so sánh không timing-safe
- **Bằng chứng:** `api/scoring.py:15` `if cron_secret and auth_header != f"Bearer {cron_secret}":` → nếu `CRON_SECRET` env rỗng/thiếu, toàn bộ check bị BỎ QUA (fail-open); so sánh `!=` không constant-time. Endpoint kết nối thẳng Postgres, batch UPDATE `aiScore/frictionIndex/tier` cho MỌI `Client` (`:111-115`). Không nằm trong `vercel.json` crons (orphan) nhưng vẫn POST-able.
- **Rủi ro:** khi thiếu secret (misconfig/preview env), bất kỳ ai POST cũng ghi đè điểm/tier toàn bộ client; timing side-channel dò secret.
- **Fix:** fail-CLOSED khi thiếu secret; dùng `hmac.compare_digest`; xoá nếu không dùng.

### WS-06 (Medium) — `/api/test-email`: secret qua query string + lộ env
- **Bằng chứng:** `src/app/api/test-email/route.ts:17` nhận `?secret=`; `:28-34` trả prefix `RESEND_API_KEY` + trạng thái các env; file tự ghi "DELETE after debugging" (`:3`).
- **Rủi ro:** secret lọt vào access log / referrer / lịch sử trình duyệt; response là info-disclosure hạ tầng email.
- **Fix:** xoá endpoint; nếu giữ, chỉ nhận secret qua header timing-safe và bỏ mọi disclosure env/key.

### WS-07 (Low) — `/api/notifications/unsubscribe` GET mutate
- **Bằng chứng:** GET (`route.ts:41`) upsert `emailEnabled=false` ngay (`:70-80`). Token là credential (`verifyUnsubscribeToken :56`) nên không huỷ được của người khác, nhưng mail-scanner / trình duyệt prefetch link GET có thể tự huỷ đăng ký của chính người nhận.
- **Đối chiếu:** `/api/portal-notify/unsubscribe` đã sửa đúng chuẩn (GET→redirect confirm, POST mới mutate — finding P4-R4) nhưng route này bị bỏ sót.
- **Fix:** GET render trang xác nhận, chỉ mutate ở POST (RFC 8058 List-Unsubscribe-Post) — mirror portal-notify.

### WS-08 (Low) — `/r/[slug]` guest gần như không có CSP
- **Bằng chứng:** `next.config.ts:145-147` rule /r/ set CSP `frame-ancestors 'self';` — Next **replace** header trùng key → trang /r/ mất default-src/script-src/media-src (chủ đích cho hls.js blob worker, comment `:116-124`).
- **Rủi ro:** bề mặt public lớn nhất, render nội dung guest, không có CSP backstop. Chưa thành XSS vì comment render escaped-text (`CommentItem.tsx:221`), nhưng mất lớp phòng thủ chiều sâu.
- **Fix:** đặt CSP scoped cho /r/ giữ blob worker (vd `default-src 'self'; script-src 'self' 'unsafe-inline'; worker-src blob:; media-src 'self' blob: https://*.mux.com; frame-ancestors 'self'`) thay vì bỏ trắng policy.

### WS-09 (Low) — `AddTaskModal` render notes RAW (lệch chuẩn sanitize)
- **Bằng chứng:** `src/components/dashboard/AddTaskModal.tsx:1450` `dangerouslySetInnerHTML={{ __html: form.notes }}` — component KHÔNG import DOMPurify; `form.notes` là TipTap HTML (`:67-68,1367-1368`). Mọi sink notes khác đều sanitize (TaskDetailModal:753, TaskDetailMobile:448, TaskDrawer:200).
- **Phạm vi:** đây là preview trong wizard tạo task — tác giả xem chính output editor của mình (self-XSS). Nội dung cũng có thể đến từ draft/Velox prefill (`:571,833-837`). Rủi ro thực tế Low, nhưng là bất nhất và mầm stored-XSS nếu component sau này render notes của user khác.
- **Fix:** bọc `DOMPurify.sanitize(form.notes)` như các sibling.

### WS-10 (Low) — `/api/log-client-error` không auth + không rate-limit
- **Bằng chứng:** `route.ts:17` POST không guard; comment thừa nhận không rate-limit (`:15`). Input đã cap độ dài (`:20-24`) nên không injection log.
- **Rủi ro:** flood Vercel logs (chi phí/nhiễu). Chủ đích không auth để log được cả khi /login crash.
- **Fix:** thêm rate-limit nhẹ (Upstash) theo IP.

### WS-11 (Low) — Content-Type comment-attachment do client khai
- **Bằng chứng:** `src/lib/review/comments.ts:562-572` chỉ check prefix `image/` + chặn SVG + cap 10MB; mimeType client → Content-Type object R2 (presign PUT `:572`), không verify magic-byte.
- **Rủi ro:** client PUT nội dung khác kèm Content-Type ảnh. Giảm nhẹ mạnh: chặn SVG + `nosniff` toàn cục + render qua `<img>` (không execute).
- **Fix (tuỳ chọn):** sniff magic-byte ở đường raw, hoặc re-encode thumbnail server-side.

---

## Ghi chú kiểm chứng
- Đã tự đọc code: `next.config.ts`, `vercel.json`, `api/vdownloader.py`, `api/scoring.py`, `src/lib/rate-limit-upstash.ts`, `src/lib/review/rate-limit-db.ts` (qua discovery), `src/lib/auth.ts`, `src/lib/comment-markdown.ts`, `src/components/review/player/CommentItem.tsx`, `src/lib/review/comments.ts`, `src/lib/review/r2.ts`, `src/app/api/integrations/scan-folder/route.ts`, `src/app/api/exchange-rate/route.ts`, `src/app/api/notifications/unsubscribe/route.ts`, `src/app/api/log-client-error/route.ts`, `AddTaskModal.tsx`.
- Loại trừ mirror `electron/release/win-unpacked/**` khỏi mọi kết luận.
- Đối chiếu audit cũ: `notifications/unsubscribe` GET-mutate (P4-R4) **vẫn CHƯA fix** ở route này (đã fix ở portal-notify) — verify lại trên code hiện tại đúng như báo cáo cũ. HT-020 (chặn SVG attachment) **đã fix** (`comments.ts:562-564`). RL-1 (rate-limit fail-closed prod) **đã fix** (`rate-limit-upstash.ts:159-162`). G1 (XFF spoof) **đã fix** (`rate-limit-db.ts` IP order).

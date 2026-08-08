# Frontend (Next.js trên Vercel) phải đổi gì khi backend rời sang VPS

> Bối cảnh: backend chuyển thành Spring Boot chạy tại `api.hustlytasker.xyz` (VPS — bộ file mẫu cùng thư mục). Frontend Next.js **vẫn ở Vercel** tại `hustlytasker.xyz`. File này liệt kê CHÍNH XÁC các thay đổi wiring phía frontend + phần cấu hình Spring đối ứng, kèm `file:line` của code hiện tại.

## 0. Phạm vi thật — đọc trước khi ước lượng công

Repo hiện là **full-stack một khối**: mutations chính KHÔNG đi qua `/api/**` mà qua **55 file server actions / ~190 hàm `"use server"`** (`src/actions/*` — parts/06, parts/07), cộng 102 `route.ts`. "Đổi base URL" chỉ đúng với phần `fetch('/api/...')`; còn server actions là RPC nội bộ của Next — khi logic dời sang Spring, **mỗi action phải viết lại thành lời gọi REST** (từ server component/route handler của Next gọi sang Spring, hoặc từ client). Đó là khối lượng chính của dự án migration, nằm ngoài file này. Các mục dưới đây là phần wiring bắt buộc và đủ dùng cho mọi phương án.

## 1. Env mới: `NEXT_PUBLIC_API_BASE_URL`

| Việc | Chi tiết |
|---|---|
| Thêm env trên Vercel | `NEXT_PUBLIC_API_BASE_URL=https://api.hustlytasker.xyz` (Production). Preview: cũng trỏ prod API hoặc một VPS staging — quyết định ở mục 4. |
| Helper duy nhất | Tạo `src/lib/api-base.ts` export `apiUrl(path)` — mọi `fetch` đi qua đây, cấm rải chuỗi domain khắp code (bài học từ `NEXT_PUBLIC_APP_URL` đang được fallback-hardcode `'https://hustlytasker.xyz'` ở ≥12 chỗ: `src/lib/review/shares.ts:105`, `src/lib/google-auth.ts:47`, `src/actions/signup-actions.ts:343`…). |
| PHÂN BIỆT với `NEXT_PUBLIC_APP_URL` | `NEXT_PUBLIC_APP_URL` là **base URL của frontend** — dùng để build link trong email (`src/lib/notification-email.ts:33`, `src/lib/email-templates.ts:58…219`), OAuth redirect (`src/app/api/integrations/dropbox/authorize/route.ts:30`), share link (`src/actions/share-link-actions.ts:82`), guest URL (`src/lib/review/guest-emails/wrap.ts:53-54`). Nó **GIỮ NGUYÊN** `https://hustlytasker.xyz`. Backend Spring cần bản sao của nó (`APP_BASE_URL` trong `.env.example`) vì email giờ do Spring gửi nhưng link vẫn trỏ về frontend. |

## 2. Rewrite/proxy trong `next.config.ts` (phương án PA-1 — khuyến nghị)

`next.config.ts` hiện **không có `rewrites()`** (chỉ có `redirects()` `next.config.ts:34-47` và `headers()` `:48-151`). Thêm:

```ts
// next.config.ts — thêm vào nextConfig
async rewrites() {
  return {
    // beforeFiles: chặn trước khi Next match src/app/api/** cũ trong giai đoạn
    // chuyển tiếp (route nào đã dời sang Spring thì proxy đè lên route cũ)
    beforeFiles: [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/:path*`,
      },
    ],
  }
},
```

Lưu ý đã kiểm tra với code thật:

- **Migrate dần theo prefix**: không cần chuyển 1 phát 102 route. Liệt kê `source` hẹp (vd `'/api/review/:path*'` trước) — phần chưa dời vẫn rơi xuống route handlers cũ của Next.
- **Middleware không cản**: `src/middleware.ts:9-16,168-170` bỏ qua toàn bộ `/api` (matcher exclude `api`) — proxy không đụng logic session của middleware.
- **`withBotId` cũng inject rewrites** (`next.config.ts:154-165` — wrapper outermost khi chạy trên Vercel): sau khi thêm `rewrites()`, phải smoke-test lại signup (path được BotID protect là `POST /api/auth/signup` — `src/instrumentation-client.ts`) để chắc 2 nguồn rewrites merge đúng.
- **Giới hạn của proxy Vercel**: 2 route nặng `download-zip` từng cần `maxDuration: 300` (`vercel.json:15-20`) — đi qua rewrite là streaming proxy nên thường ổn, nhưng nếu gặp timeout ở edge thì chuyển riêng 2 đường download sang gọi thẳng PA-2 (mục 4).
- Khi route đã dời hết: xoá block `functions` cho `src/app/api/**` trong `vercel.json:2-21` và xoá dần route handlers cũ.

## 3. Vì sao PA-1 là mặc định: cookie session giữ nguyên tuyệt đối

Cookie hiện tại (parts/09 §2): `session` — **httpOnly, `SameSite=Lax`, `Secure` ở prod, KHÔNG set `Domain` (host-only), TTL 30 ngày**, JWT HS256 ký `JWT_SECRET` (`src/lib/auth.ts:23-29`, `src/lib/jwt.ts:2-21`), rolling-refresh ở middleware khi còn <15 ngày (`src/middleware.ts:145-163`).

Với PA-1 (mọi request `/api/*` vẫn đánh vào `hustlytasker.xyz`, Vercel proxy sang VPS):

- Trình duyệt chỉ thấy **first-party same-origin** → cookie đi kèm như cũ, `Set-Cookie` từ Spring đi ngược qua proxy cũng như cũ. **Không CORS, không đổi thuộc tính cookie, không đụng middleware.**
- Spring chỉ cần verify được JWT HS256 hiện hành: dùng **cùng `JWT_SECRET`** (đã ghi trong `.env.example` — "SAME_VALUE_AS_VERCEL"), đọc claim `user.id / role / profileId / sessionVersion / sessionProfileId` (payload build tại `src/actions/auth-actions.ts:344-357`) và port đúng chuỗi guard `sessionVersion`-so-DB (`src/lib/security.ts:77-81,257-269`) — user **không bị logout** khi cutover.
- Preview deployments hoạt động y hệt prod (preview cũng proxy qua chính origin của nó).

## 4. Phương án PA-2 — gọi thẳng `api.hustlytasker.xyz`: CORS + cookie phân tích kỹ

Chỉ dùng khi muốn bỏ hop Vercel (đường download nặng, hoặc về sau bỏ hẳn Vercel). Phải làm đủ 3 việc:

### 4.1 CORS phía Spring — danh sách origin THẬT

| Origin | Nguồn |
|---|---|
| `https://hustlytasker.xyz` | domain prod (`src/lib/email.ts:5`, fallback khắp code) |
| `https://www.hustlytasker.xyz` | chỉ thêm nếu Vercel có gắn alias www — kiểm tra dashboard trước, đừng khai thừa |
| `https://*.vercel.app` | preview deployments (project Vercel tên "tasker" → URL dạng `tasker-git-<branch>-<team>.vercel.app`); Spring phải dùng `allowedOriginPatterns` vì `allowCredentials(true)` **cấm** wildcard `*` trần |
| `http://localhost:3000` | dev |

```java
// CorsConfig.java — đọc từ env CORS_ALLOWED_ORIGIN_PATTERNS (.env.example)
registry.addMapping("/api/**")
    .allowedOriginPatterns(patterns)          // KHÔNG dùng allowedOrigins("*") vì có credentials
    .allowedMethods("GET","POST","PUT","PATCH","DELETE","OPTIONS")
    .allowedHeaders("Content-Type","Authorization","Idempotency-Key")
    .allowCredentials(true)
    .maxAge(3600);
```

`Idempotency-Key` bắt buộc có trong `allowedHeaders`: upload initiate đang gửi header này (`src/app/api/review/uploads/initiate/route.ts:28` — parts/05 dòng 46).

### 4.2 Cookie cross-origin — điểm hay bị hiểu sai

- `api.hustlytasker.xyz` và `hustlytasker.xyz` là **same-site** (cùng eTLD+1) → `SameSite=Lax` **vẫn gửi cookie**, KHÔNG cần `SameSite=None` cho cặp domain này. Cái thiếu là **`Domain`**: cookie hiện host-only (`src/lib/auth.ts:23-29` không set domain) nên không bay sang subdomain. Spring phải set lại cookie với `Domain=.hustlytasker.xyz` (một lần re-login hoặc endpoint re-mint), và fetch phía client phải thêm `credentials: 'include'` ở **mọi** call.
- **Preview `*.vercel.app` là CROSS-site với api.hustlytasker.xyz** → cookie Lax không đi → **preview chết** với PA-2. Muốn cứu preview phải `SameSite=None; Secure` — mở lại bề mặt CSRF (Lax đang là một lớp chắn; Spring khi đó bắt buộc bật CSRF protection hoặc double-submit token), và Safari/ITP có thể vẫn khó chịu. Đây là lý do chính khuyến nghị PA-1.
- **Không chuyển sang Bearer token trong localStorage**: thiết kế hiện tại cố ý httpOnly để XSS không đọc được session (parts/09 §2); hạ xuống localStorage là một bước lùi bảo mật thật, không phải "hiện đại hoá".

### 4.3 CSP trong `next.config.ts` phải nới

- `connect-src` (`next.config.ts:93`) hiện chỉ có `'self'` + vercel-storage + livekit(dead) + R2 + Mux → **thêm `https://api.hustlytasker.xyz`**, nếu không mọi `fetch` cross-origin bị chặn ngay tại trình duyệt.
- `img-src`: ảnh comment-attachment render qua route same-origin 302 → presigned R2 (`/api/review/comment-attachments/:id/raw` — comment dài tại `next.config.ts:62-78`). Nếu route đó dời sang api-subdomain thì `<img>` trỏ cross-origin: **`img-src` phải thêm `https://api.hustlytasker.xyz`** (R2 đã có sẵn trong danh sách cho đích redirect).

## 5. Webhook ngoài đổi URL về VPS

| Webhook | Hiện tại | Sau migration | Việc phải làm |
|---|---|---|---|
| **Mux** | `https://hustlytasker.xyz/api/webhooks/mux` — verify HMAC-SHA256 ±5', ledger `WebhookEvent` idempotent (`src/app/api/webhooks/mux/route.ts:23-48,74-80`) | `https://api.hustlytasker.xyz/api/webhooks/mux` (Spring port cùng verify + ledger) | Đổi URL trong Mux dashboard; `MUX_WEBHOOK_SECRET` sang `.env` VPS. Mux cho phép **nhiều** webhook endpoint — giai đoạn chuyển tiếp cứ để cả 2 nhận song song, ledger unique theo Mux event id chống xử lý đúp (chính pattern `P2002`-ack hiện tại). Webhook này **KHÔNG đi qua rewrite của frontend** — Mux gọi thẳng, nên phải cutover ở dashboard Mux, không phải ở Next. |
| **Inngest** | Inngest Cloud gọi `https://hustlytasker.xyz/api/inngest` (serve 4 function — `src/lib/review/inngest.ts:259,341,526,657`; maxDuration 800 `src/app/api/inngest/route.ts:15`) | **Inngest KHÔNG có Java SDK** → 4 function reimplement trong Spring: `reviewJanitor` → `@Scheduled` (mục 6); `reviewMuxWebhook`/`reviewProcessUpload`/`reviewShareDecision` → worker nội bộ (outbox table + `@Async`/queue), giữ nguyên chuỗi idempotency ledger→claim (parts/10 §2.3) | Chừng nào review-pipeline chưa port xong: **giữ Next làm host Inngest** (URL không đổi) — đây là ranh giới cutover tự nhiên. Khi port xong: gỡ app khỏi Inngest Cloud dashboard, xoá env `INNGEST_*`, xoá guard `INNGEST_DEV` (`src/lib/env.ts:56-63`). |
| **Calendar (stub)** | `/api/webhooks/calendar` nhận POST **không xác thực**, không làm gì thật (`src/app/api/webhooks/calendar/route.ts:11,21`) | Không mang sang | Cơ hội khai tử luôn trong đợt migration — đừng port stub. |

## 6. 7 Vercel cron → Spring `@Scheduled`

Nguồn: `vercel.json:22-51` + handlers `src/app/api/cron/*/route.ts` (parts/10 §1). Spring cron có **6 trường (thêm giây)** và phải khai `zone = "UTC"` (lịch Vercel là UTC; đừng để server TZ quyết định — compose đã set `TZ: UTC` nhưng khai tường minh vẫn hơn).

| Cron cũ | Lịch Vercel (UTC) | `@Scheduled(cron = "...", zone = "UTC")` | Ghi chú port |
|---|---|---|---|
| `/api/cron/send-digest` | `0 * * * *` | `0 0 * * * *` | Giữ logic "giờ UTC 1 chạy thêm DAILY" (`send-digest/route.ts:29-45`) |
| `/api/cron/check-deadline` | `0 * * * *` | `0 0 * * * *` | Cron DUY NHẤT ghi đè nghiệp vụ: `task.status='Quá hạn'` (`check-deadline/route.ts:156-159`) — port kèm whitelist `OVERDUE_ELIGIBLE_STATUSES` (`route.ts:5-8`), sai là payroll đếm sai (F13) |
| `/api/cron/cleanup-notifications` | `0 2 * * *` | `0 0 2 * * *` | |
| `/api/cron/hard-delete-workspaces` | `0 3 * * *` | `0 0 3 * * *` | Delete cascade — audit TRƯỚC delete (`hard-delete-workspaces/route.ts:67-76`) |
| `/api/cron/hard-delete-profiles` | `30 3 * * *` | `0 30 3 * * *` | |
| `/api/cron/auth-cleanup` | `0 4 * * *` | `0 0 4 * * *` | |
| `/api/cron/review-janitor` | `0 20 * * *` | `0 0 20 * * *` | Hiện chỉ bắn event Inngest (`review-janitor/route.ts:31`) — trên Spring gọi thẳng janitor service, bỏ tầng event |

Việc phía frontend/Vercel:

- **Xoá block `crons` khỏi `vercel.json:22-51`** ngay khi Spring `@Scheduled` chạy — 2 hệ cron chạy song song thì `check-deadline` có thể ghi status 2 lần (vô hại về data vì cùng giá trị, nhưng bắn notification đúp).
- `CRON_SECRET` không còn cần cho lịch chạy (nội bộ JVM) — giữ lại chỉ để bảo vệ endpoint trigger-tay nếu muốn giữ. Nhân tiện khai tử `api/test-email` (nhận secret qua query param — `src/app/api/test-email/route.ts:17`, tự ghi "DELETE after debugging").
- **Electron desktop lệch chuẩn**: `electron/main/cron-scheduler.ts:19-26` đang tự chạy node-cron gọi API local (6/7 job, thiếu review-janitor). Khi cron về Spring, desktop build phải tắt scheduler này (không thì máy user bắn cron trùng vào VPS).

## 7. Upload R2 presign — đổi base URL 4 endpoint, còn lại giữ nguyên

Kiến trúc hiện tại (parts/05 dòng 46-49): browser **PUT thẳng lên R2 presigned URL** (S3 multipart — `src/lib/review/r2.ts:1-39`), server chỉ cấp phát URL:

| Endpoint | Hiện tại | Sau migration |
|---|---|---|
| `POST /api/review/uploads/initiate` (+ header `Idempotency-Key`) | Next route (`initiate/route.ts:28`) | Spring, qua `apiUrl()` (PA-1: URL không đổi vì proxy; PA-2: đổi origin + CORS mục 4.1) |
| `GET /api/review/uploads/[id]` — client poll 3s | Next route | Spring — không còn trần `maxDuration: 60` (`vercel.json:12-14`) |
| `POST .../complete`, `POST .../abort` | Next route | Spring (presigner dùng cùng AWS SDK v2 Java, R2 endpoint pin `https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com` y hệt `r2.ts`) |
| PUT part lên R2 | Browser → R2 trực tiếp | **KHÔNG đổi** — CSP `connect-src` đã có `https://*.r2.cloudflarestorage.com` (`next.config.ts:93`) |

## 8. Những thứ cố tình KHÔNG đổi (đỡ dò lại)

| Thành phần | Vì sao không đổi |
|---|---|
| `NEXT_PUBLIC_APP_URL` | vẫn là frontend `https://hustlytasker.xyz` (mục 1) |
| Supabase Realtime | client nói thẳng với Supabase (`src/lib/supabase.ts`), không qua backend; phía gửi broadcast chuyển sang Spring gọi cùng REST endpoint Supabase (`src/lib/notification-broadcast.ts:19,46`) |
| Service worker push `public/sw.js` | push-only, không intercept fetch (parts/10 §4) — VAPID key sang `.env` VPS là xong |
| Trang `/share/[token]` + `/r/[slug]` | vẫn là page Next SSR trên Vercel; chỉ nguồn data đổi sang Spring. Cookie guest `rv_unlock_/rv_guest_` là host-only của frontend — với PA-1 không đổi gì; PA-2 thì các API `/api/r/**` (19 route — parts/05) kéo theo đúng bài toán cookie mục 4.2 |
| Playback Mux | signed JWT RS256 do backend ký (`src/lib/review/mux-jwt.ts`) — chỉ là code dời chỗ, URL stream.mux.com và CSP giữ nguyên |
| **BotID signup** | `initBotId` protect `POST /api/auth/signup` (`src/instrumentation-client.ts:13-20`) — `checkBotId()` chỉ chạy trên hạ tầng Vercel. Signup dời sang Spring là **mất lớp BotID** (không phải "không đổi" mà là *mất*, ghi vào đây để không ai đi tìm): bù bằng rate-limit Upstash hiện có (fail-closed — `src/lib/rate-limit-upstash.ts`) + disposable-email guard sẵn trong signup; cân nhắc Turnstile nếu spam tăng (env `TURNSTILE_*` từng có trong `.env` nhưng chưa từng có code) |

## 9. Trình tự cutover khuyến nghị (rút từ toàn bộ phân tích trên)

1. Dựng VPS (vps-setup.md) — DB **phương án (b) giữ Neon** để bước đầu không kèm migration data.
2. Port nhóm route ít rủi ro trước (đọc-only / cron) → bật `@Scheduled`, xoá `crons` khỏi `vercel.json` (mục 6).
3. Thêm rewrite PA-1 theo prefix từng nhóm route (mục 2) — cookie & preview không đổi gì (mục 3).
4. Cutover Mux webhook ở dashboard (dual-fire an toàn nhờ ledger — mục 5).
5. Port review-pipeline + thay Inngest bằng worker nội bộ — bước dài nhất, làm cuối (mục 5).
6. Khi `/api/**` của Next rỗng: cân nhắc PA-2 cho đường nặng, hoặc giữ PA-1 vĩnh viễn (đơn giản > tối ưu vài chục ms).

# 01 — Stack & Deploy hiện tại (HustlyTasker)

> Phạm vi: ngôn ngữ/framework, ORM/DB/driver, nơi deploy frontend/backend/DB, cron, sub-project (electron, mcp-server, api/*.py), và toàn bộ service ngoài khai báo trong dependencies. Mọi kết luận kèm bằng chứng `file:line` (đường dẫn tương đối từ repo root). KHÔNG sửa file nguồn nào.

---

## 1. Ngôn ngữ / Framework / Version

| Thành phần | Kết luận | Bằng chứng |
|---|---|---|
| Framework chính | **Next.js 16.1.6** (App Router, thư mục `src/app/`) | `package.json:97`, `src/app/` tồn tại |
| React | **19.2.3** (react + react-dom pinned) | `package.json:103-104` |
| Ngôn ngữ | **TypeScript ^5**, strict, path alias `@/* → ./src/*` | `package.json:137`, `tsconfig.json:7`, `tsconfig.json:21-23` |
| Bundler build | **Webpack, KHÔNG Turbopack** — script build là `next build --webpack` | `package.json:7` |
| CSS | Tailwind CSS **3.4.17** + tailwindcss-animate + @tailwindcss/typography | `package.json:136`, `package.json:112`, `package.json:57` |
| Package manager | **npm** — lockfile là `package-lock.json` ở root; `electron/` và `mcp-server/` có `package-lock.json` riêng | `package-lock.json`, `electron/package-lock.json`, `mcp-server/package-lock.json` (ls root/electron/mcp-server) |
| Node version pin | **Không có** `.nvmrc` / `.node-version` / trường `engines` | `package.json` không có `engines`; ls root không thấy `.nvmrc` |
| Ngôn ngữ phụ | **Python 3** cho 2 Vercel Function: `api/scoring.py`, `api/vdownloader.py`; deps Python ở `requirements.txt` root (`pg8000`, `yt-dlp`, `requests`, `static-ffmpeg`) | `api/scoring.py:1`, `api/vdownloader.py:41`, `requirements.txt:1-4` |
| i18n | **next-intl ^4.8.3**, plugin bọc config; messages `en/it/ru/vi/zh` | `package.json:98`, `next.config.ts:2,5`, `src/i18n/request.ts`, `messages/` (5 file json) |
| Validation | zod ^3.23.8 | `package.json:116` |
| Auth | JWT tự quản bằng **jose** (`src/lib/jwt.ts`), session cookie xử lý ở middleware (skip toàn bộ `/api`) | `package.json:92`, `src/middleware.ts:3-15` |

---

## 2. ORM + Database + Driver

| Câu hỏi | Kết luận | Bằng chứng |
|---|---|---|
| ORM | **Prisma 5.22** (`prisma` + `@prisma/client` cùng ^5.22.0) | `package.json:41`, `package.json:101` |
| Datasource | `provider = "postgresql"`, `url = env("DATABASE_URL")`; generator có `previewFeatures = ["driverAdapters"]` | `prisma/schema.prisma:6-9`, `prisma/schema.prisma:3` |
| Neon adapter có dùng thật không? | **KHÔNG dùng ở runtime.** `src/lib/db.ts` tạo `new PrismaClient({...})` chuẩn qua connection string, comment nói rõ *"We avoid @neondatabase/serverless Pool here to prevent hangs"*. `@prisma/adapter-neon` + `@neondatabase/serverless` được khai báo trong deps nhưng **không có import nào trong `src/`** → **dead-dep candidate** (chỉ còn trong comment và vài script probe: `scripts/probe-b5-justin-portal.ts`, `scripts/probe-download-original.ts`, `scripts/probe-new-active-profiles.ts`) | `src/lib/db.ts:16-25`, `package.json:39-40` |
| Connection string lấy ở đâu | `src/lib/env.ts` map `POSTGRES_URL \|\| DATABASE_URL` (ưu tiên biến Vercel `POSTGRES_URL`), clean quote copy-paste | `src/lib/env.ts:19` |
| DB host | **Neon Postgres** (managed, ngoài Vercel). Bằng chứng trong repo: kế hoạch migration mở đầu bằng *"Chuyển từ Vercel + Neon → Railway"* (lịch sử — đối chiếu, chưa thực hiện) + CLAUDE.md ghi "Prisma+Neon khớp" | `RAILWAY_MIGRATION.md:1`, `CLAUDE.md` (mục review-module, điểm 2) |
| Migration strategy | **`prisma db push` chạy trong `postinstall`** (mỗi lần `npm install` trên Vercel build) — KHÔNG dùng `prisma migrate`; seed qua `prisma/seed.ts` | `package.json:10`, `package.json:24-26` |
| Truy cập DB ngoài app chính | `mcp-server` dùng `@prisma/client` trực tiếp (kết nối thẳng DB); `electron` dùng driver `pg` thô + `api/scoring.py` dùng `pg8000` (Python) | `mcp-server/package.json:15`, `electron/package.json:18`, `api/scoring.py:5,30-37` |

---

## 3. Deploy ở đâu

### 3.1 Frontend + Backend: **một app Next.js duy nhất trên Vercel**

- Không tách frontend/backend — toàn bộ API là Next route handlers dưới `src/app/api/**` + server actions; cấu hình `maxDuration` per-route trong `vercel.json:6-20`.
- BotId (Vercel Edge) chỉ bật khi `process.env.VERCEL` set — xác nhận Vercel là môi trường chạy chính: `next.config.ts:159-165`.
- Python functions `api/*.py` là **Vercel Python Functions** (`vercel.json:3-5`, `maxDuration: 10`).
- Domain prod: **hustlytasker.xyz** — default from-email `notification@hustlytasker.xyz` (`src/lib/email.ts:5`).
- `maxDuration` đáng chú ý: `api/*.py` 10s; API chung 30s; invoices + review/uploads 60s; 2 route download-zip 300s (`vercel.json:2-21`); riêng `/api/inngest` tự set `maxDuration = 800` trong code (`src/app/api/inngest/route.ts:16`).

### 3.2 Railway: **chỉ là kế hoạch dự phòng, CHƯA phải deploy hiện tại**

- `RAILWAY_MIGRATION.md:1-10` là hướng dẫn migrate (Vercel+Neon → Railway+Supabase Storage) — trạng thái "code đã chuẩn bị sẵn", chưa cutover.
- Seam đã cài sẵn trong code: `nixpacks.toml:1-11` (cài Chromium cho PDF, ghi rõ *"Vercel ignores this file entirely"*), `src/lib/storage.ts:23-31` (chọn backend ảnh theo env), `next.config.ts:159-165` (tắt BotId off-Vercel).

### 3.3 Database: **Neon Postgres** (mục 2). Storage media: Cloudflare R2 (review) + Vercel Blob (ảnh public, mặc định hiện tại) + Supabase Storage (dự phòng Railway) — chi tiết mục 6.

---

## 4. Cron đang chạy

### 4.1 Vercel Cron — 7 job (`vercel.json:22-51`), khớp 1-1 với 7 thư mục `src/app/api/cron/`

| Path | Lịch (UTC) | Route tồn tại |
|---|---|---|
| `/api/cron/send-digest` | `0 * * * *` (mỗi giờ) | `src/app/api/cron/send-digest/` |
| `/api/cron/check-deadline` | `0 * * * *` (mỗi giờ) | `src/app/api/cron/check-deadline/` |
| `/api/cron/cleanup-notifications` | `0 2 * * *` | `src/app/api/cron/cleanup-notifications/` |
| `/api/cron/hard-delete-workspaces` | `0 3 * * *` | `src/app/api/cron/hard-delete-workspaces/` |
| `/api/cron/hard-delete-profiles` | `30 3 * * *` | `src/app/api/cron/hard-delete-profiles/` |
| `/api/cron/auth-cleanup` | `0 4 * * *` | `src/app/api/cron/auth-cleanup/` |
| `/api/cron/review-janitor` | `0 20 * * *` | `src/app/api/cron/review-janitor/` |

- Xác thực: header `Authorization: Bearer $CRON_SECRET`, fail 500 nếu chưa cấu hình secret — ví dụ `src/app/api/cron/send-digest/route.ts:19-22`.

### 4.2 Background jobs KHÔNG phải cron: **Inngest**

- Serve endpoint `/api/inngest` host toàn bộ `reviewFunctions` (pipeline upload → Mux → notify + janitor con) — `src/app/api/inngest/route.ts:5-6,18-21`; client id `hustlytasker-review` (`src/lib/review/inngest.ts:29`).
- Guard prod: `INNGEST_DEV` truthy trong production → **throw, refuse to start** (`src/lib/env.ts:56-63`).

### 4.3 Electron cron (desktop, local) — **lệch với vercel.json**

- `electron/main/cron-scheduler.ts:19-26` tự chạy node-cron gọi API local, mirror vercel.json **nhưng chỉ có 6 job — THIẾU `review-janitor`** (vercel.json có 7, `vercel.json:47-50`). → drift đáng ghi nhận cho bản desktop.

---

## 5. Sub-project: vai trò & có deploy không

| Sub-project | Vai trò | Deploy? | Bằng chứng |
|---|---|---|---|
| `mcp-server/` | **MCP server stdio** cho AI (Claude Desktop): tool CRUD/assign/status/marketplace/bulk cho Task, nói chuyện **trực tiếp với DB qua @prisma/client** (không qua API app) | **KHÔNG deploy** — chạy local qua stdio transport, cấu hình mẫu `claude_desktop_config.example.json` | `mcp-server/src/index.ts:9-11,23-26`, `mcp-server/package.json:13-17` |
| `electron/` | **Desktop wrapper Windows**: chạy Next.js standalone local (`output: 'standalone'` chỉ bật khi `ELECTRON_DESKTOP=1`), tray, node-cron thay Vercel cron, kết nối DB bằng `pg`, auto-update qua `electron-updater`, đóng gói `electron-builder` | **KHÔNG deploy server** — build ra app cài đặt (`build:desktop`, `electron-builder --win`) | `electron/main/index.ts:9-16`, `next.config.ts:32`, `electron/package.json:13-19`, `electron/builder.config.js:1-11`, `package.json:13` |
| `api/` (root, Python) | 2 Vercel Python Function — xem mục 5.1 | **CÓ deploy** (vercel.json khai `functions` cho `api/*.py`) nhưng **orphan** — không code nào trong `src/` gọi tới | `vercel.json:3-5` |

### 5.1 Chi tiết `api/*.py` (folder CÓ THẬT ở root)

| File | Nội dung | Auth | Có ai gọi không? |
|---|---|---|---|
| `api/scoring.py` | POST — kết nối Postgres qua `pg8000` (`POSTGRES_URL`/`DATABASE_URL`), tính điểm Client (revenue/friction từ bảng `Client`, `Task`, `Feedback`) rồi update ngược vào DB | Bearer `CRON_SECRET` (`api/scoring.py:12-18`) | **Không** — không có cron nào trong `vercel.json:22-51` trỏ tới, grep `"/api/scoring"` toàn `src/` = 0 kết quả → chỉ có thể được gọi bằng cron ngoài/thủ công. **Dead-code candidate (nhưng vẫn được deploy).** |
| `api/vdownloader.py` | GET — downloader video qua `yt-dlp` + `static-ffmpeg`, có `?diagnostic=true` trả version ffmpeg/python | **KHÔNG có auth** (`api/vdownloader.py:44-45` — `do_GET` xử lý thẳng query) | **Không** — grep `vdownloader` toàn `src/` = 0 kết quả. **Dead-code candidate nhưng đang là endpoint PUBLIC không xác thực trên prod** — nên gỡ hoặc khoá (điểm rủi ro chuyển tiếp cho phần audit security). |

- Không đụng độ route: `src/app/api/` không có route `scoring`/`vdownloader` nên Python function chiếm path đó trên Vercel.

---

## 6. Service ngoài — khai báo trong dependencies: dùng thật hay chết?

| Service | Package (evidence) | Cách dùng thật | Kết luận |
|---|---|---|---|
| **Mux** (video encode/stream) | **KHÔNG có SDK `@mux/mux-node`** | REST thuần tự viết bằng `fetch` (3 endpoint create/get/delete asset): `src/lib/review/mux.ts:1-8`; signed playback JWT RS256 tự ký bằng `node:crypto`: `src/lib/review/mux-jwt.ts:1-9`; webhook HMAC-SHA256 ±5 phút fail-closed: `src/app/api/webhooks/mux/route.ts:1-31`. Env `MUX_TOKEN_ID/SECRET/WEBHOOK_SECRET/SIGNING_*` (`.env.example:10-15`) | **DÙNG THẬT** (cố ý không thêm dep — comment: dep mới re-run `prisma db push` mỗi build) |
| **Cloudflare R2** (S3 API) | `@aws-sdk/client-s3` + `@aws-sdk/s3-request-presigner` (`package.json:28-29`) | `S3Client` region `auto`, endpoint pin `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`, bucket mặc định `hustly-review`; multipart trình duyệt PUT thẳng presigned URL: `src/lib/review/r2.ts:1-39` | **DÙNG THẬT** |
| **Inngest** | `inngest` ^4.11.0 (`package.json:91`) | Client + toàn bộ review pipeline functions: `src/lib/review/inngest.ts:5,29`; serve `/api/inngest`: `src/app/api/inngest/route.ts:5-6` | **DÙNG THẬT** |
| **Resend** (email) | `resend` ^6.12.3 (`package.json:107`) | `src/lib/email.ts:1-9` — from `notification@hustlytasker.xyz` | **DÙNG THẬT** |
| **Upstash Redis** | `@upstash/ratelimit` + `@upstash/redis` (`package.json:70-71`) | Rate-limit auth (signup/login/OTP), fail-CLOSED prod khi thiếu env: `src/lib/rate-limit-upstash.ts:1-30` | **DÙNG THẬT** |
| **Vercel Blob** | `@vercel/blob` ^2.0.1 (`package.json:72`) | Dynamic import trong uploader ảnh public; là driver mặc định khi `BLOB_READ_WRITE_TOKEN` tồn tại: `src/lib/storage.ts:23-31,63` | **DÙNG THẬT** (backend ảnh hiện tại) |
| **Supabase** | `@supabase/supabase-js` ^2.105.3 (`package.json:56`) | (1) **Realtime** client-side (notification): `src/lib/supabase.ts:1-33`; (2) **Storage** backend ảnh dự phòng Railway: `src/lib/storage.ts:5-31`; (3) remotePatterns `*.supabase.co`: `next.config.ts:19-22` | **DÙNG THẬT** — không phải chỉ remotePatterns |
| **web-push** (VAPID) | `web-push` ^3.6.7 (`package.json:114`) | Dynamic import, no-op nếu thiếu VAPID env: `src/lib/web-push.ts:1-20` | **DÙNG THẬT** (gated bằng env) |
| **LiveKit** | `@livekit/components-react`, `@livekit/components-styles`, `livekit-client`, `livekit-server-sdk` (`package.json:37-38,93-94`) | Grep `livekit` (case-insensitive) toàn `src/` = **0 file**; chỉ còn CSP `wss://*.livekit.cloud` trong `next.config.ts:92-93` + env `LIVEKIT_*` trong `.env` | **DEAD-DEP** — 4 package không được import (feature huddle/call đã gỡ); CSP + env là dư âm |
| **Google OAuth** | không SDK — REST thuần | (1) Sign-in Google: `src/lib/google-auth.ts:1-24` + `src/app/api/auth/google/*`; (2) Google Drive integration: `src/app/api/integrations/google-drive/`; (3) Calendar sync scaffolding: `src/lib/calendar-sync.ts:9-15` | **DÙNG THẬT** (chung `GOOGLE_CLIENT_ID/SECRET`) |
| **Dropbox OAuth** | không SDK — REST thuần | `src/app/api/integrations/dropbox/authorize/route.ts`, `.../callback/route.ts`, token mã hoá qua `src/lib/integration-tokens.ts` | **DÙNG THẬT** |
| **OpenAI** | `openai` ^6.27.0 (`package.json:99`) | Dịch ghi chú task VI→EN bằng GPT-4, key từ env `GPT4_API_KEY`: `src/lib/gemini-translator.ts:1-6` — **tên file gây hiểu lầm, thực chất gọi OpenAI, không Gemini** | **DÙNG THẬT** |
| **Gemini** | `@google/generative-ai` ^0.24.1 (`package.json:36`) | Grep `generative-ai\|GoogleGenerativeAI` toàn `src/` = **0 file** | **DEAD-DEP** |
| **BotId (Vercel)** | `botid` ^1.5.11 (`package.json:78`) | Wrapper outermost chỉ khi on-Vercel: `next.config.ts:3,163-165`; check signup: `src/actions/signup-actions.ts`, `src/instrumentation-client.ts` | **DÙNG THẬT** (chỉ trên Vercel) |
| **Puppeteer + Chromium** | `puppeteer-core` + `@sparticuz/chromium` (`package.json:55,102`) | PDF hoá đơn: `src/lib/invoice-generator.ts:1-2`; `serverExternalPackages`: `next.config.ts:33` | **DÙNG THẬT** |
| **ffmpeg** | `@ffmpeg-installer/ffmpeg` (`package.json:35`) | Re-tag colorspace video trước khi Mux ingest: `src/lib/review/color-retag.ts:30`; `serverExternalPackages`: `next.config.ts:33` | **DÙNG THẬT** |
| **hls.js** | `hls.js` ^1.6.16 (`package.json:90`) | Player review: `src/components/review/player/useHlsPlayer.ts` (+ CompareSide/CompareView/PlayerControls/ReviewPlayerShell) | **DÙNG THẬT** (đúng quyết định "hls.js, không Vidstack") |
| **ws** | `ws` ^8.19.0 + `@types/ws` (`package.json:69,115`) | Grep `from 'ws'` toàn `src/` = 0 | **DEAD-DEP candidate** (khả năng là tàn dư config Neon websocket/LiveKit) |

### 6.1 Env mồ côi (có key trong `.env` nhưng 0 reference trong code)

| Nhóm env | Kết luận | Bằng chứng |
|---|---|---|
| `CLOUDFLARE_STREAM_*` (4 key) | Code Cloudflare Stream đã gỡ (thử nghiệm P0-pre) — grep `CLOUDFLARE_STREAM` toàn `src/` = 0 | tên key trong `.env`; grep 0 kết quả |
| `NEXT_PUBLIC_TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY` | Grep `TURNSTILE` toàn `src/` + `scripts/` = 0 → không có Turnstile trong code | tên key trong `.env`; grep 0 kết quả |
| `LIVEKIT_API_KEY/SECRET`, `NEXT_PUBLIC_LIVEKIT_URL` | Đi cùng dead-dep LiveKit ở bảng trên | tên key trong `.env`; grep 0 kết quả trong `src/` |

*(Ghi chú phương pháp: chỉ liệt kê TÊN biến từ `.env` — không đọc/ghi lại giá trị. File env hiện có: `.env`, `.env.example` (chỉ khối review-module Mux/R2/Inngest), `.env.test` (chỉ `DATABASE_URL` cho DB test).)*

---

## 7. Bức tranh deploy tổng (tóm tắt)

```
Vercel (hustlytasker.xyz) ── Next.js 16 (webpack build, npm)
 ├─ SSR + API routes (src/app/api/**, maxDuration 30-300s)
 ├─ api/*.py — 2 Python Functions (10s) [orphan, vdownloader KHÔNG auth]
 ├─ 7 Vercel Cron → /api/cron/* (Bearer CRON_SECRET)
 ├─ /api/inngest ← Inngest Cloud (signed, maxDuration 800)
 └─ /api/webhooks/mux ← Mux webhook (HMAC)
DB: Neon Postgres (POSTGRES_URL/DATABASE_URL, prisma db push ở postinstall)
Storage: Vercel Blob (ảnh public, mặc định) · Cloudflare R2 (video/file review) · Supabase Storage (dự phòng Railway)
Realtime: Supabase Realtime (client-side)
Email: Resend · Rate-limit: Upstash Redis · Push: web-push (VAPID)
AI: OpenAI GPT-4 (dịch VI→EN)
Local-only: electron/ (desktop wrapper + node-cron 6/7 job) · mcp-server/ (MCP stdio, Prisma trực tiếp)
Dự phòng chưa dùng: Railway (RAILWAY_MIGRATION.md + nixpacks.toml — "Vercel ignores this file")
```

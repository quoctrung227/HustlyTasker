# PHASE 0 — SYSTEM INVENTORY: HustlyTasker

> Tài liệu tổng hợp. Chi tiết đầy đủ (bảng từng endpoint/action/model) nằm trong `parts/01` → `parts/12` cùng thư mục — mọi kết luận trong đó đều kèm `file:line` thật. Ngày audit: 2026-08-02.

## 1. Kết luận tổng quan

| Câu hỏi | Kết luận | Bằng chứng |
|---|---|---|
| Kiến trúc repo | **Multi-package repo, KHÔNG phải npm-workspaces monorepo**: 1 app Next.js full-stack ở root + 3 package con độc lập (`mcp-server/`, `electron/`, `website/`) build bằng script `cd` thủ công | `package.json:11-14`, chi tiết `parts/02-tree.md` |
| Frontend + Backend | **Cùng 1 app Next.js 16.1.6** (App Router, build webpack, React 19.2.3, TypeScript 5) — không tách FE/BE | `package.json:97,7`, `parts/01-stack-deploy.md` |
| Database | **Neon Postgres**, Prisma 5.22 qua `PrismaClient` chuẩn (`POSTGRES_URL \|\| DATABASE_URL`). `@prisma/adapter-neon` + `@neondatabase/serverless` khai báo nhưng **KHÔNG dùng** (dead-dep) | `src/lib/db.ts:16-25`, `src/lib/env.ts:19` |
| Migration | **`prisma db push` chạy trong `postinstall` mỗi lần build** — không dùng `prisma migrate`; folder `prisma/migrations/` đã DRIFT khỏi DB thật từ 2026-05-07; constraint thật nằm thêm ở 6 file SQL thủ công (`prisma/migrations/manual/`) | `package.json:10`, `parts/03-models.md` |
| Deploy hiện tại | **Vercel** (domain prod `hustlytasker.xyz`): serverless functions + 7 Vercel Cron + Inngest; **không có CI/CD workflow nào trong repo** (không có `.github/workflows`); Railway chỉ là kế hoạch dự phòng chưa cutover (`nixpacks.toml` tự ghi "Vercel ignores this file") | `vercel.json`, `src/lib/email.ts:5`, `RAILWAY_MIGRATION.md` |
| Sub-project | `electron/` = desktop wrapper local (standalone build, mirror 6/7 cron — thiếu review-janitor `electron/main/cron-scheduler.ts:19-26`); `mcp-server/` = MCP stdio nói chuyện **thẳng DB** qua `@prisma/client`; `website/` = landing tĩnh. Không cái nào deploy web | `parts/01-stack-deploy.md` |
| Quy mô code sống | `src/` **780 file .ts/.tsx**: app 208 (68 page + 102 route.ts + 7 layout), components 330 (27 domain), lib 172, actions 55, hooks 6. Prisma **67 model + 15 enum** (2.056 dòng) | `parts/02-tree.md` |

## 2. Stack & services ngoài (dùng THẬT — đã verify import)

| Service | Vai trò | Bằng chứng |
|---|---|---|
| Mux | Encode + playback video review — gọi **REST thuần tự viết + JWT RS256 tự ký, không SDK** | `src/lib/review/mux.ts:1-8`, `src/lib/review/mux-jwt.ts:1-9` |
| Cloudflare R2 | Object storage (S3 multipart qua `@aws-sdk/client-s3`) cho bản dựng video + attachment | `src/lib/review/r2.ts` |
| Inngest | 4 background function của review module, serve `/api/inngest` maxDuration 800 | `src/lib/review/inngest.ts:259,341,526,657` |
| Resend | Toàn bộ email (2 hệ template song song — xem §6) | `src/lib/email.ts` |
| Upstash Redis | Rate-limit | `@upstash/ratelimit` |
| Vercel Blob | Ảnh public mặc định (khi có `BLOB_READ_WRITE_TOKEN`) | `src/lib/storage.ts` |
| Supabase | 2 vai trò thật: realtime notification client-side + Storage ảnh dự phòng (seam hosting-portable) | `src/lib/supabase.ts`, `src/lib/storage.ts:23-31` |
| web-push | Push notification VAPID | `src/actions/push-actions.ts` |
| Google/Dropbox OAuth | Scan folder footage (Velox V4) | `src/app/api/integrations/**` |
| OpenAI GPT-4 | Dịch thuật — file tên `gemini-translator.ts` nhưng ruột gọi OpenAI (`GPT4_API_KEY`) | `src/lib/gemini-translator.ts` |

**Dead-dependency đã verify (grep 0 import):** 4 gói LiveKit, `@google/generative-ai`, `ws`, `@prisma/adapter-neon`, `@neondatabase/serverless`. **Env mồ côi trong `.env`:** `CLOUDFLARE_STREAM_*`, `TURNSTILE_*`, `LIVEKIT_*`.

## 3. Database (chi tiết: `parts/03-models.md`)

- 67 model / 15 enum, chia 8 nhóm domain; multi-tenancy 2 tầng `profileId` + `workspaceId` (riêng `ErrorDictionary` là bảng GLOBAL không tenant — `prisma/schema.prisma:1014`).
- **`Task.status` là String TỰ DO** default `"Đang thực hiện"` (`prisma/schema.prisma:336`) — không enum; tương tự `Workspace:69`, `WorkspaceMember:114`, `Payroll:318`, `Client:546`, `MonthlyRank:1061`.
- Constraint thật của DB ≠ schema.prisma: 3 partial unique index (2 cái `lower(name)` trên ReviewFolder/ReviewAsset — `prisma/migrations/manual/p0_add_review_module.sql:13-16`; 1 cái Client(profileId, COALESCE(parentId,-1), lower(btrim(name)))), 5 CHECK constraint, 1 trigger last-owner.
- 15 model review module (`schema.prisma:1640-2056`) dùng cross-module FK dạng **scalar string chủ đích** (không FK constraint tới Task/User/Client/Workspace).
- Soft-delete 3 pattern: `status+deletedAt+hardDeleteAfter` (Profile/Workspace/Client), trash-batch `deleteBatchId` (Review*), `isDeleted` (TaskComment).
- Bẫy kiểu id: `Client.id`/`Project.id` là Int autoincrement, `AuditLog.id` BigInt, còn lại uuid/cuid; `Rating.clientId` là String trỏ **User** trong khi `Task.clientId` là Int trỏ **Client**.

## 4. API surface (chi tiết: `parts/04-api-core.md`, `parts/05-api-review.md`, `parts/06-actions-a.md`, `parts/07-actions-b.md`)

| Lớp | Số lượng | Ghi chú |
|---|---|---|
| API routes ngoài review | 39 route | 10 domain: auth 10, cron 7, webhooks 2, integrations 5, share 2, invoices 2, exports 1, notifications 1, portal-notify 1, inngest 1, misc |
| API routes review module | 63 route (44 staff `/api/review/**` + 19 guest `/api/r/**`) | Staff qua `requireReviewAccess`; guest qua share-slug + gate chain |
| Server actions | 55 file / ~190 exported functions | Mutations chính của app đi đường này, guard `verifyWorkspaceAccess` / `verifyProfileAdminAccess` |
| Pages | 56 page + 9 layout | public 8, account 2, `/[workspaceId]` 33 (admin 18 + team 5 + dashboard 6...), `/mc` 21, share 1, r 1, preview/dead 3 |

Route đáng chú ý (chi tiết trong parts): `api/test-email` còn sống nhận secret qua query param (tự ghi "DELETE after debugging"); `api/import-jan-2026` one-off FROZEN; **`api/` (root) chứa 2 Python function orphan vẫn được Vercel deploy** — `api/vdownloader.py` GET không xác thực (`vercel.json:3-5`).

## 5. Role & authz (chi tiết: `parts/09-roles-authz.md`)

- **3 tầng role**: `UserRole` global (ADMIN/USER/AGENCY_ADMIN/CLIENT/LOCKED — `schema.prisma:898`); `ProfileRole` (OWNER/ADMIN/USER/CLIENT — `schema.prisma:908`) là **tầng RBAC chính**; `WorkspaceRole` (OWNER/ADMIN/MEMBER/GUEST) lưu String tự do (`schema.prisma:114`). Cộng flag `isTreasurer` (giờ chỉ là UI flag).
- Session = **JWT HS256 (jose) trong cookie httpOnly `session`, TTL 30 ngày**, rolling-refresh ở middleware; thu hồi qua `sessionVersion` so DB tại DAL (`verifyActiveSession`, `verifyWorkspaceAccess`, `getCurrentUser`, `isSessionLive`).
- Middleware **không phân quyền role** — chỉ auth-gate `/admin`+`/dashboard` và đá CLIENT về `/login` (`src/middleware.ts:71-100`); chặn admin thật ở `admin/layout.tsx:56-66` qua `verifyProfileAdminAccess` (predicate admin/finance DUY NHẤT — `src/lib/security.ts:180`).
- CLIENT bị fail-closed khỏi toàn bộ `/[workspaceId]/**` (`src/app/[workspaceId]/layout.tsx:128-131`) — khách chỉ có 2 bề mặt token: `/share/[token]` (ClientShareLink SHA-256 hash-at-rest, uniform 404, không password) và `/r/[slug]` (gate chain password bcrypt → unlock JWT → identity modal → GuestSession cookie).
- Impersonation: workspace-ADMIN nhập vai user, TTL 2h, 5 lớp chặn + audit log (`src/actions/impersonation-actions.ts:9`).

## 6. Background jobs & automation (chi tiết: `parts/10-jobs-webhooks.md`)

- **7 Vercel cron** (`vercel.json:22-51`) đều guard CRON_SECRET nhưng không đồng nhất: chỉ `auth-cleanup` dùng `timingSafeEqual`, 6 cron còn lại so sánh chuỗi thường. `check-deadline` là cron duy nhất ghi đè dữ liệu nghiệp vụ (`task.status='Quá hạn'`).
- **4 Inngest function** (`src/lib/review/inngest.ts`): reviewMuxWebhook, reviewProcessUpload, reviewJanitor, reviewShareDecision.
- Webhook Mux verify HMAC-SHA256 ±5 phút timingSafeEqual, ledger idempotent (`src/app/api/webhooks/mux/route.ts:23-48`). **Webhook calendar là STUB không xác thực** (`src/app/api/webhooks/calendar/route.ts:11`).
- Email: **2 hệ template song song đều đang dùng thật** (legacy `src/lib/email-templates.ts` + registry `src/lib/notification-emails/`) — nguy cơ double-email cùng biến cố giao task. ~25 loại email qua Resend.
- `src/lib/TimerWorker.ts` = dead code; `src/instrumentation-client.ts` chỉ init Vercel BotID cho POST `/api/auth/signup`.

## 7. User flows (chi tiết + bảng đầy đủ: `parts/12-user-flows.md`)

5 actor: Admin, Staff-editor, Client portal (`/share/[token]`), Guest reviewer (`/r/[slug]`), Hệ thống. **16 flow chính (F01–F16) + 8 flow phụ (P1–P8)**; 5 flow quan trọng nhất: F04 Task lifecycle (trục xương sống — mọi module đọc/ghi `Task.status` string tự do), F08 Guest `/r/` decision (pipeline bất đồng bộ dài nhất), F07 Team review status machine, F09 Client portal (~20 action qua 1 token — bề mặt authz lớn nhất), F13 Payroll (`SALARY_PENDING_STATUSES` đếm theo status → đụng tiền thật).

Đặc thù kiến trúc: **2 shell admin song song cùng mounted** — `/[workspaceId]/admin/*` (GĐ1, 18 trang) và `/[workspaceId]/mc/*` (Mission Control, 21 trang) — dùng chung actions, không phải dead code.

## 8. Dead code / file rác đã loại trừ (danh sách đầy đủ + bằng chứng: `parts/11-deadcode.md`)

Nhóm chính (mỗi mục đã verify grep 0-hit + git log):
1. **`api/` root (scoring.py + vdownloader.py)** — dead code NHƯNG vẫn deploy thành endpoint Vercel sống; `vdownloader.py` không xác thực → ưu tiên xoá cao nhất.
2. **~55 file one-off ở root đang tracked**: 15 `check-*.js`, `debug-*`, `cleanup-tasks.js` (gọi `prisma.task.deleteMany`!), `restore_*`, 5 phiên bản `search_missing_tasks`, dump `all_users_output.txt`/`all_tasks_kcd.txt` (chứa dữ liệu thật), 6 file .docx/.pptx đặc tả cũ.
3. **Trong src/**: `DesktopTaskTable.tsx` 53KB import-nhưng-không-render (vẫn vào bundle), cụm `TaskCreationManager` + 2 form, `RoleSwitcher`, `TreasurerToggle`, `DeleteUserButton`, `ResetPasswordButton`, lib `TimerWorker.ts`, `calendar-sync.ts`; dependency `@google/generative-ai` chết.
4. **File nhạy cảm cần xoá local**: `.tmp/video-report/chrome-*-history.sqlite` (44MB lịch sử trình duyệt), `.codex-studyplace-dev.log` (135MB), `prisma/dev.db` (SQLite prototype còn tracked).
5. **Trang preview có gate** (`desk-preview`, `velox-v4-preview` — notFound() ở prod) giữ làm dev-harness; `diagnostic` là stub không gate — xoá được.
6. **Phản-ví dụ phải GIỮ**: `scripts/test-*.ts` (regression harness trong `package.json:15-22`), `messages/` i18n, `smart-qr.ts` (dynamic import), `/welcome` (post-login), `mcp-server/`+`electron/` (build target), `assets/` (media nguồn landing).

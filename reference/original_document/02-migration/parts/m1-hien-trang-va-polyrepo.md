# M1 — Hiện trạng deploy & Kế hoạch tách Polyrepo (FE Next.js / BE Spring Boot)

> Phase 2 §1–2 của system-audit. Nguồn số liệu: `00-discovery/system-inventory.md` + `00-discovery/parts/01-stack-deploy.md`, `02-tree.md`, `06-actions-a.md`, `07-actions-b.md` — mọi kết luận hiện trạng đều kèm `file:line` thật (đường dẫn tương đối repo root). Phần kế hoạch (§2) là ĐỀ XUẤT, đánh dấu rõ đâu là quyết định cần chốt.

---

## §1. HIỆN TRẠNG DEPLOY (recap chính xác từ `parts/01-stack-deploy.md`)

### 1.1 Bảng tóm tắt

| Thành phần | Hiện trạng | Bằng chứng |
|---|---|---|
| App | **1 app Next.js 16.1.6 full-stack duy nhất** (App Router, React 19.2.3, TS 5) — FE + BE + jobs cùng một deployment | `package.json:97`, `package.json:103-104` |
| Bundler | **Webpack, không Turbopack** — script build là `next build --webpack` | `package.json:7` |
| Hosting | **Vercel serverless** (domain prod `hustlytasker.xyz`); BotId chỉ bật khi `process.env.VERCEL` | `next.config.ts:159-165`, `src/lib/email.ts:5` |
| API surface | 102 `route.ts` dưới `src/app/api/**` + **55 file server actions (~190 exported function)** + 2 Python Function `api/*.py` (orphan, `vdownloader.py` KHÔNG auth) | `parts/02-tree.md` §4, `vercel.json:3-5`, `api/vdownloader.py:44-45` |
| maxDuration | Python 10s; API chung 30s; invoices + review/uploads 60s; 2 route download-zip 300s; `/api/inngest` tự set **800s** trong code | `vercel.json:2-21`, `src/app/api/inngest/route.ts:16` |
| Cron | **7 Vercel Cron** trỏ `/api/cron/*`, guard `Authorization: Bearer $CRON_SECRET` (chỉ `auth-cleanup` dùng `timingSafeEqual`, 6 cron còn lại so sánh chuỗi thường) | `vercel.json:22-51`, `src/app/api/cron/send-digest/route.ts:19-22`, `parts/10-jobs-webhooks.md` |
| Background jobs | **Inngest Cloud** gọi ngược vào `/api/inngest` — 4 function của review module (processUpload, muxWebhook, janitor, shareDecision) | `src/app/api/inngest/route.ts:5-6,18-21`, `src/lib/review/inngest.ts:259,341,526,657` |
| DB | **Neon Postgres** ngoài Vercel; Prisma 5.22, `PrismaClient` chuẩn qua connection string `POSTGRES_URL \|\| DATABASE_URL` (adapter Neon là dead-dep) | `src/lib/db.ts:16-25`, `src/lib/env.ts:19`, `package.json:39-41` |
| Migration | **`prisma db push` chạy trong `postinstall`** — không dùng `prisma migrate`; folder `prisma/migrations/` đã DRIFT khỏi DB thật từ 2026-05-07; constraint thật nằm thêm ở SQL thủ công | `package.json:10`, `prisma/migrations/manual/p0_add_review_module.sql:13-16`, `system-inventory.md` §1 |
| CI/CD | **KHÔNG có workflow nào trong repo** — không có `.github/workflows/`; không test gate, không lint gate, không build gate trước khi merge. Deploy = Vercel Git integration thuần | `system-inventory.md` §1 (đã verify không tồn tại `.github/workflows`) |
| Node pin | Không có `.nvmrc` / `engines` — version Node do Vercel quyết | `package.json` không có `engines` |
| Sub-package | `mcp-server/` (MCP stdio, **nói thẳng DB qua @prisma/client**), `electron/` (desktop wrapper, driver `pg` thô + node-cron mirror 6/7 job — thiếu `review-janitor`), `website/` (landing Vite tĩnh, không import gì từ `src/`) — cả 3 build bằng `cd` thủ công, không cái nào deploy web | `package.json:11-13`, `mcp-server/src/index.ts:9-11`, `electron/package.json:18`, `electron/main/cron-scheduler.ts:19-26`, `website/vite.config.js` |
| Railway | Chỉ là kế hoạch dự phòng chưa cutover (`nixpacks.toml` tự ghi *"Vercel ignores this file"*) | `RAILWAY_MIGRATION.md:1-10`, `nixpacks.toml:1-11` |

### 1.2 Workflow build/deploy THỰC TẾ (không có CI trung gian)

```
git push (nhánh bất kỳ)
   │
   ▼
Vercel Git integration tự trigger build
   │  1. clone + npm install
   │  2. ── postinstall: "prisma generate && prisma db push"  (package.json:10)
   │        ⚠️ SCHEMA ĐƯỢC ÁP VÀO NEON NGAY TẠI BƯỚC NÀY —
   │        trước khi build xong, trước khi deployment được promote
   │  3. next build --webpack                                  (package.json:7)
   ▼
Nhánh thường  → Preview deployment
Merge → main  → Production deployment (hustlytasker.xyz)
```

Ba hệ quả vận hành đã ghi nhận (làm căn cứ cho kế hoạch tách ở §2):

1. **DDL chạy ở build-time, không phải deploy-time.** Mọi build — kể cả build PREVIEW của nhánh chưa merge — đều `prisma db push` vào cùng `DATABASE_URL`. Schema mới có thể nằm trên DB prod trong khi code prod vẫn là bản cũ (giữa bước 2 và lúc promote), và nhánh thử nghiệm cũng đẩy được schema lên prod DB. Đây là lý do quy trình thủ công hiện tại phải kiêng: *"destructive DDL chỉ chạy SAU khi deploy main READY"* (`RAILWAY_MIGRATION.md` + quy ước vận hành đã ghi trong memory dự án).
2. **`prisma db push` không có lịch sử migration** — `prisma/migrations/` đã drift từ 2026-05-07, và 3 partial unique index + 5 CHECK + 1 trigger chỉ tồn tại trong `prisma/migrations/manual/*.sql` áp tay (`parts/03-models.md`). Nghĩa là **schema.prisma KHÔNG phải nguồn sự thật đầy đủ của DB thật** — điểm phải xử lý khi Prisma rời sang bất kỳ stack nào khác.
3. **Không có cổng chất lượng nào trước prod**: 8 script `test:*` trong `package.json:15-22` là harness chạy tay bằng `tsx`, không được gọi trong build. Merge main = deploy prod, không điều kiện.

---

## §2. KẾ HOẠCH TÁCH POLYREPO

> Mục tiêu: 2 repo — **`hustlytasker-api`** (Java Spring Boot, sở hữu DB + toàn bộ business logic + jobs) và **`hustlytasker-web`** (Next.js thuần UI). Nguyên tắc phân chia: *"cái gì đụng Prisma/secret/side-effect ngoài (email, R2, Mux, push) → BE; cái gì đụng DOM/React/format hiển thị → FE; cái gì cả hai cần → thành API contract, KHÔNG thành shared code"*.

### 2.1 Cấu trúc 2 repo đề xuất

#### Repo A — `hustlytasker-api` (Spring Boot 3.x, Java 21, Gradle)

```
hustlytasker-api/
├─ src/main/java/xyz/hustlytasker/
│  ├─ auth/          # thay src/lib/{auth,jwt,auth-guard,security,otp,password-validator}.ts
│  │                 #   JWT HS256 "session" → Spring Security filter (xem 2.1.1)
│  ├─ task/          # thay src/actions/{task,bulk-task,task-management,update-task-details,
│  │                 #   claim,tag,task-comment}-actions + src/lib/{task-state-machine,
│  │                 #   task-statuses,task-invariants,fsm-config}
│  ├─ workspace/     # workspace/member/profile/invitation/cross-team/impersonation actions
│  ├─ finance/       # payroll, bonus, payment, invoice, pricing-rule, price-template actions
│  │                 #   + src/lib/{payroll-cycle,pricing-engine,finance-helpers,invoice-generator}
│  ├─ crm/           # crm-actions + client-request-actions + src/lib/{client-dedupe,client-hierarchy}
│  ├─ review/        # 63 route /api/review/** + /api/r/** + src/lib/review (57 file:
│  │                 #   mux, mux-jwt, r2, upload-engine, share-*, status, notify, access…)
│  ├─ portal/        # 21 action share-portal + 2 share-document + share-link (token là credential)
│  ├─ notify/        # notification-actions + email (Resend) + web-push + 2 hệ template email
│  ├─ velox/         # src/lib/velox (11 file engine) + velox-batch/raw-footage actions
│  │                 #   + integrations Google Drive/Dropbox (OAuth server-side)
│  ├─ jobs/          # 7 cron (Spring @Scheduled) + 4 pipeline Inngest (outbox + poller — xem 2.1.2)
│  ├─ webhook/       # Mux HMAC webhook; calendar stub (quyết định giữ/xoá)
│  └─ common/        # audit-log, sanitize, rate-limit (Bucket4j + Redis), serialization→DTO
├─ src/main/resources/db/migration/   # Flyway — baseline dump từ NEON THẬT, không từ schema.prisma (2.3)
├─ tools/mcp-server/                  # package TS dời từ mcp-server/ — đổi Prisma-direct → REST client sinh từ spec (2.1.3)
└─ build.gradle                       # springdoc-openapi → CI xuất openapi.json làm artifact có version
```

#### Repo B — `hustlytasker-web` (Next.js, giữ Vercel)

```
hustlytasker-web/
├─ src/app/           # 56 page + 9 layout GIỮ NGUYÊN — nhưng KHÔNG còn src/app/api/** (trừ 2-3
│  │                  #   route handler mỏng: set/clear cookie session, OAuth callback redirect)
│  ├─ [workspaceId]/  # dashboard, admin (18 trang), mc (21 trang), team, task — 2 shell admin
│  │                  #   dùng CHUNG endpoint BE nên tách repo không nhân đôi backend
│  ├─ share/[token]/  # portal khách — data từ nhóm API public /v1/portal/**
│  └─ r/[slug]/       # guest review — data từ /v1/r/**
├─ src/components/    # 330 file giữ nguyên
├─ src/hooks/         # 6 hook giữ nguyên (usePresence/useSupabaseChannel là client-side)
├─ src/lib/           # CHỈ giữ nhóm FE (bảng 2.2.3): utils, date-utils, format-*, display-*,
│  │                  #   status-colors, comment-markdown, notification-sound, supabase (realtime client), device
├─ src/api/generated/ # client TS sinh bởi orval từ openapi.json của repo A — KHÔNG viết tay
├─ src/i18n/ + messages/  # next-intl 5 locale
├─ electron/          # desktop wrapper dời về đây (wrap UI; XOÁ node-cron mirror + driver pg — 2.1.3)
├─ website/           # landing Vite tĩnh dời về đây (không import src/, deploy riêng như hiện tại)
└─ src/middleware.ts  # giữ auth-gate nhưng đổi verify HS256→RS256 public key (2.1.1)
```

#### 2.1.1 Quyết định thiết kế ràng buộc 2 repo — Auth

Hiện tại session = JWT **HS256** ký bằng `JWT_SECRET`, cookie httpOnly `session`, **rolling-refresh ngay trong `src/middleware.ts`** (`parts/09-roles-authz.md`). HS256 là đối xứng — nếu FE middleware còn giữ secret để verify thì FE cũng *ký được* token → FE bị kéo vào trust boundary của BE, phá mục đích tách.

Đề xuất: khi tách, BE chuyển sang **RS256** — BE giữ private key và là nơi DUY NHẤT mint/refresh token (endpoint `POST /v1/auth/refresh`); FE middleware chỉ verify bằng public key (jose hỗ trợ sẵn — `package.json:92`) để auth-gate `/admin`+`/dashboard` như logic hiện có (`src/middleware.ts:71-100`). Kiểm tra `sessionVersion` so DB (thu hồi phiên) vốn đã nằm ở DAL (`verifyActiveSession` — `src/lib/security.ts`) → về BE tự nhiên. Repo có tiền lệ RS256 tự ký rồi: Mux playback JWT (`src/lib/review/mux-jwt.ts:1-9`).

#### 2.1.2 Cron + Inngest về BE

| Hiện tại | Sau tách | Ghi chú |
|---|---|---|
| 7 Vercel Cron (`vercel.json:22-51`) | 7 method `@Scheduled(cron=...)` trong `jobs/` — giữ nguyên lịch UTC | Bỏ hẳn `CRON_SECRET` (không còn endpoint HTTP public); sửa luôn lỗi 6/7 cron so sánh secret thường (`parts/10-jobs-webhooks.md`) |
| 4 Inngest function, maxDuration 800s (`src/lib/review/inngest.ts:259,341,526,657`) | **Outbox table + Quartz/`@Scheduled` poller** trong BE. Inngest KHÔNG có SDK Java (chỉ TS/Python/Go) → giữ Inngest nghĩa là nuôi thêm 1 worker TS riêng — không đáng cho đúng 4 function | BE chạy process thường (không serverless) nên giới hạn 800s biến mất; retry/step của Inngest thay bằng cột `attempts`+`status` trên outbox — pipeline hiện tại đã idempotent qua ledger webhook Mux (`src/app/api/webhooks/mux/route.ts:23-48`) |
| Electron node-cron mirror 6/7 job (`electron/main/cron-scheduler.ts:19-26`) | **XOÁ** — BE sở hữu jobs, desktop không tự chạy cron nữa | Đồng thời khép luôn drift "thiếu review-janitor" đã ghi nhận |

#### 2.1.3 Ba package con đi đâu

| Package | Về repo | Lý do + việc phải làm |
|---|---|---|
| `mcp-server/` | **A (api)** — `tools/mcp-server/` | Hiện nói **thẳng DB** qua `@prisma/client` (`mcp-server/src/index.ts:9-11`) — sau tách DB chỉ BE được chạm. Phải viết lại data layer: Prisma-direct → gọi REST bằng chính client TS sinh từ openapi.json + service-account token. Nó version lock-step với API nên ở repo A (dù là TS — chấp nhận 1 package npm trong repo Gradle) |
| `electron/` | **B (web)** | Là wrapper của UI (`electron/main/index.ts:9-16`); sau tách chỉ còn wrap Next standalone/URL, trỏ API hosted. Xoá node-cron + driver `pg` (`electron/package.json:18`) |
| `website/` | **B (web)** | Landing tĩnh không import `src/` (`website/vite.config.js`, `parts/02-tree.md` §3.4) — đi cùng repo FE để chung brand asset + Vercel, deploy như một project Vercel riêng |
| `api/*.py` (root) | **KHÔNG migrate — XOÁ** | Orphan đã verify grep 0-hit, `vdownloader.py` là endpoint public không auth (`api/vdownloader.py:44-45`, `parts/01` §5.1). Tách repo là thời điểm khai tử |

### 2.2 ~190 server actions → REST endpoints

#### 2.2.1 Con số thật và phân loại

`src/actions/` = 55 file / **~190 exported async function** (`parts/06`, `parts/07`). Server action là code FE+BE trộn: Next đăng ký mỗi export thành POST endpoint ẩn, body có thể gọi `cookies()`/`revalidatePath()`/`redirect()`. Khi tách, PHẢI phân loại — không phải 190 hàm đều thành REST:

| Nhóm | Số lượng (ước từ inventory) | Xử lý |
|---|---|---|
| Action nghiệp vụ có guard (vWA/vPAA/vFA/session) | **~155** | → REST endpoint trong repo A, guard → Spring Security (bảng 2.2.2) |
| Action public-by-design dùng **token làm credential** (21 share-portal + 2 share-document + password-reset 3 + signup 1 + unsubscribe) | **~28** | → nhóm controller public `/v1/portal/**`, `/v1/auth/**` với filter chain riêng (resolve token hash-at-rest như `resolveShareToken` hiện tại) — KHÔNG session |
| Helper "Internal" đang lộ thành endpoint không guard: `createNotificationInternal`/`createBulkNotificationsInternal`/`createAndBroadcastNotifications` (`src/actions/notification-actions.ts:24,70,86`), `forceFlush` (`tracking-actions.ts:29`) | 4 | → **method nội bộ của NotificationService/TrackingService trong BE, KHÔNG expose HTTP**. Tách repo tự động vá lớp lỗi này (cùng lớp G-2 `updateFrameAccount` — `global-settings.ts:54` — về BE phải thêm `@PreAuthorize` admin cho cân với `getFrameAccount`) |
| Action thuần side-effect FE — cookie/cache: `selectProfile` (cookie `current_profile_id` — `profile-actions.ts:36`), `toggleMobileView`/`setUiPref` (`ui-actions.ts:6,22`), `refreshLeaderboardAction` (`revalidateTag` — `leaderboard-actions.ts:5`), 3 inline `handleLogout` trong 3 layout (`parts/07` §33) | ~7 | → **Ở LẠI repo B** (route handler / server action mỏng). Logout gọi thêm `POST /v1/auth/logout` để BE bump `sessionVersion` |
| Stub/deprecated: `createProfile`, `changeUserProfile`, `createFeedback`, `checkOverdueTasks`, `retryTaskTranslation`, `adminResetPassword`, `transferWorkspaceOwnership`, `deleteUser` (alias), `createTaskViaToken` ("retained but unused" — `share-portal-actions.ts:1182`) | ~9 | → **KHÔNG migrate** — chết luôn ở lần tách |

Cộng 102 `route.ts` hiện có (39 core + 63 review — `system-inventory.md` §4) cũng dời về A → spec cuối cùng ~**250–270 operations**, gom ~25–30 tag/controller.

#### 2.2.2 Mapping guard → Spring Security (giữ nguyên ngữ nghĩa 3 tầng role)

Ba tầng role hiện tại (UserRole global / ProfileRole / WorkspaceRole string — `parts/09-roles-authz.md`) giữ nguyên trong DB; chỉ đổi cách thực thi:

| Guard hiện tại (TS) | Bản Spring đề xuất |
|---|---|
| `verifyWorkspaceAccess(wsId,'ADMIN'\|'MEMBER')` — 33+9 chỗ chỉ riêng phần A (`parts/06` §Tổng quan) | `@PreAuthorize("@ws.hasRole(#workspaceId,'ADMIN')")` — bean `ws` port logic `src/lib/security.ts` |
| `verifyProfileAdminAccess` (predicate admin DUY NHẤT — `src/lib/security.ts:180`) | `@ws.profileAdmin(#workspaceId)` — vẫn là MỘT predicate duy nhất, không rải logic |
| `verifyFinanceAccess` (8 chỗ, mọi đường đọc/ghi USD) | `@ws.finance(...)` + **DTO tách quyền** (xem dưới) |
| Token share-portal (`resolveShareToken`) | `OncePerRequestFilter` cho `/v1/portal/**`: SHA-256 hash lookup, revoke/expiry/rate-limit như hiện tại |
| Helper cục bộ `ensureWorkspaceAccess` (availability-actions.ts:22 — bản check membership thứ 2 song song) | **Hợp nhất về bean `ws`** — tách repo là dịp khử bản trùng này |

**Điểm sống còn khi chuyển từ "serialize tay" sang DTO:** kỷ luật *jobPriceUSD không bao giờ tới non-admin* hiện thực thi bằng strip thủ công từng chỗ (`claim-actions.ts:67` bỏ jobPriceUSD, `price-template-actions.ts:9` strip R12, `pricing-rule-actions.ts:152` strip đệ quy `*USD*`, `share-portal-actions.ts:165` whitelist riêng cho khách). Ở Spring, mã hoá kỷ luật này thành **type**: `TaskAdminDto` (có USD) / `TaskStaffDto` (không USD) / `TaskPortalDto` (whitelist khách — có jobPriceUSD theo quyết định owner, không status nội bộ/assignee) — compiler + spec OpenAPI trở thành chỗ enforce, hết lệ thuộc nhớ-strip-tay từng action.

#### 2.2.3 `src/lib` (172 file) — cái nào theo BE, cái nào ở lại FE

| Về **BE (repo A)** — đụng DB/secret/side-effect | Ở lại **FE (repo B)** — thuần hiển thị/client | Thành **contract** (không share code) |
|---|---|---|
| `db.ts`, `env.ts`, `auth.ts`, `jwt.ts`, `auth-guard.ts`, `security.ts`, `otp.ts`, `password-validator.ts`, `token-encryption.ts`, `integration-tokens.ts` (đã `server-only` — `integration-tokens.ts:1`), `rate-limit*.ts`, `audit-log.ts`, `sanitize.ts`/`task-sanitize.ts`, `email.ts` + `email-templates.ts` + `notification-emails/` + `notification-email.ts` (hợp nhất 2 hệ template khi port — cơ hội khử nguy cơ double-email đã ghi ở inventory §6), `web-push.ts`, `payroll-cycle.ts`, `pricing-engine.ts`, `finance-helpers.ts`, `invoice-generator.ts` (Puppeteer→ Playwright-Java hoặc openhtmltopdf), `storage.ts` (Blob/Supabase/R2), `exchange-rate.ts`, `google-auth.ts`, `smart-qr.ts` (Sharp→ Thumbnailator), toàn bộ `lib/review/` 57 file (Mux REST + R2 + share-auth + status machine + notify; `color-retag.ts:30` exec ffmpeg — Java exec binary tương đương), `lib/velox/` 11 file (engine chạy cạnh scan API; nếu wizard FE cần preview phân loại → thêm endpoint `POST /v1/velox/classify:dry-run` thay vì share code), `workspace-*.ts`, `client-dedupe.ts`, `client-hierarchy.ts`, `task-invariants.ts`, `task-state-machine.ts`, `mc-task-drawer-data.ts`, `portal-derive.ts`, `serialization.ts` (→ DTO) | `utils.ts` (cn), `date-utils.ts`, `format-compact.ts`, `format-user.ts`, `display-labels.ts`, `display-name.ts`, `presence-format.ts`, `status-colors.ts`, `comment-markdown.ts`, `comment-reactions.ts` (phần render), `notification-sound.ts`, `supabase.ts` (realtime CLIENT — `src/lib/supabase.ts:1-33`; BE publish event qua REST Supabase), `device.ts`, `duration-parser.ts`, `task-resource-format.ts`, toàn bộ `src/hooks/` 6 hook | `task-statuses.ts` + `fsm-config.ts` + `status-colors` mapping + `SALARY_PENDING_STATUSES`: danh mục status và transition phải xuất hiện trong **OpenAPI spec** (schema + endpoint `GET /v1/meta/statuses` trả STATUS_META), FE sinh type từ spec. **KHÔNG** model thành enum cứng trong spec ngay — `Task.status` là String tự do (`prisma/schema.prisma:336`) và payroll đếm tiền theo danh sách status (bài học F2 review-fixes): spec để `type: string` + server validate theo STATUS_META, chỉ đóng băng thành enum sau khi audit status kết thúc |
| Dead code KHÔNG port: `TimerWorker.ts`, `calendar-sync.ts` (`parts/11-deadcode.md`) | | |

#### 2.2.4 Ví dụ mapping cụ thể (đại diện mỗi nhóm)

| Server action (file:line) | Guard | REST đề xuất |
|---|---|---|
| `updateTaskStatus` (`src/actions/task-actions.ts:17`) | WS:MEMBER + FSM + optimistic lock `version` | `PATCH /v1/workspaces/{wsId}/tasks/{id}/status` — body `{newStatus, expectedVersion}`, 409 khi lệch version |
| `createTask` (`admin-actions.ts:85`) | WS:ADMIN | `POST /v1/workspaces/{wsId}/tasks` |
| `bulkAssignTasks` (`bulk-task-actions.ts:667`) | WS:ADMIN | `POST /v1/workspaces/{wsId}/tasks:bulk-assign` (giữ semantics skip-per-task, trả danh sách skipped) |
| `confirmPayment` (`payroll-actions.ts:22`) | WS:ADMIN + PayrollLock | `POST /v1/workspaces/{wsId}/payroll/{userId}:confirm` — 423 Locked khi kỳ đã khoá |
| `getShareSnapshot` (`share-portal-actions.ts:165`) | token | `GET /v1/portal/{token}/snapshot` — filter chain public, trả `TaskPortalDto` |
| `approveDeliverableViaToken` (`share-portal-actions.ts:765`) | token + phase-gate | `POST /v1/portal/{token}/tasks/{taskId}:approve` |
| `loginAction` (`auth-actions.ts:168`) | public + rate-limit + lockout | `POST /v1/auth/login` → BE trả JWT + Set-Cookie (hoặc FE route handler set cookie từ response) — redirect/`?next=` validation ở FE |
| `createNotificationInternal` (`notification-actions.ts:24`) | KHÔNG guard (lỗi) | **Không expose** — thành `NotificationService.create()` nội bộ |
| `selectProfile` (`profile-actions.ts:36`) | cookie | **Ở lại FE** (route handler set cookie), gọi `GET /v1/profiles/{id}/access-check` trước khi set |

### 2.3 Prisma đi đâu — chiến lược schema khi BE là Java

- **`prisma/schema.prisma` (67 model, 2.056 dòng) dừng vai trò nguồn sự thật.** Baseline Flyway của repo A phải sinh từ **`pg_dump --schema-only` trên Neon THẬT**, không phải từ schema.prisma — vì DB thật đang hơn schema: 3 partial unique index (2 cái `lower(name)` trên ReviewFolder/ReviewAsset — `prisma/migrations/manual/p0_add_review_module.sql:13-16`), 5 CHECK constraint, 1 trigger last-owner (`parts/03-models.md`), còn `prisma/migrations/` thì drift từ 2026-05-07.
- ORM phía Java: **JPA/Hibernate cho CRUD + jOOQ hoặc native query cho các chỗ đang dùng SQL đặc thù** — repo có nhiều `pg_advisory_xact_lock` (`bonus-actions.ts:336`, `crm-actions.ts:107`, `invoice-actions.ts:615`) và `FOR UPDATE` (`member-actions.ts:1217`) mà JPA thuần diễn đạt kém. Bẫy kiểu id phải giữ nguyên khi map entity: `Client.id`/`Project.id` là Int autoincrement, `AuditLog.id` BigInt, còn lại uuid/cuid; `Rating.clientId` String trỏ **User** trong khi `Task.clientId` Int trỏ **Client** (`system-inventory.md` §3).
- **Khai tử `postinstall: prisma db push`**: repo B (FE) không còn phụ thuộc DB — build FE không đụng schema nữa (giải luôn hệ quả 1.2-1). Repo A chạy `flyway migrate` như một BƯỚC DEPLOY tách khỏi build, theo kỷ luật expand→code→contract.
- `mcp-server` và `electron` mất đường DB-direct (2.1.3) — sau tách, **chỉ duy nhất repo A cầm connection string**.

### 2.4 Shared types / API contract: OpenAPI + codegen vs shared package — CHỌN OpenAPI

| Tiêu chí | Shared package (npm `@hustly/contracts`) | **OpenAPI spec + codegen** |
|---|---|---|
| Ranh giới ngôn ngữ | **Loại ngay từ vòng gửi xe**: BE là Java — package TS không import được vào Spring; sẽ phải duy trì DTO Java song song bằng tay → 2 nguồn sự thật, drift chắc chắn | Spec JSON trung lập ngôn ngữ. BE: **springdoc-openapi** sinh spec từ controller + annotation (code-first). FE: **orval** sinh TS client + TanStack Query hooks + (tuỳ chọn) zod schema — zod đã có sẵn trong stack (`package.json:116`) |
| Nguồn sự thật | 2 (types TS + DTO Java) | 1 — controller Java; spec là artifact build |
| Phát hiện breaking change | Không có gì tự động giữa 2 repo | `openapi-diff` chạy trong CI repo A: so spec mới vs spec release gần nhất, fail khi breaking |
| Khối lượng | ~250–270 operations (2.2.1) — viết tay 2 bản DTO là không tưởng cho team 1 người | Máy sinh toàn bộ; FE chỉ viết logic gọi hook |
| Kết luận | ❌ | ✅ **OpenAPI code-first (springdoc) + orval phía FE** |

Chọn **code-first** (annotation trên controller) thay vì spec-first vì đội hình thực tế là 1 owner + agent: spec-first thêm một vòng design ceremony và một generator server-stub phải nuôi; code-first + cổng `openapi-diff` cho cùng độ an toàn với ít nghi thức hơn. Quy trình phân phối spec giữa 2 repo:

1. CI repo A build → springdoc xuất `openapi.json` → publish thành **artifact có version semver** (GitHub Release/Package của repo A). Version quy ước: MINOR = additive, MAJOR = breaking (được phép chỉ khi có RFC kèm kế hoạch expand-contract).
2. Repo B pin version spec trong `orval.config.ts` (URL artifact theo tag). Nâng version = 1 PR ở repo B: regenerate client → TypeScript compile lỗi CHÍNH LÀ danh sách chỗ FE phải sửa.
3. `mcp-server` (nằm trong repo A) dùng cùng artifact — cùng cơ chế, không thêm kênh phân phối nào khác.

### 2.5 Versioning API + quy trình phối hợp release 2 repo

**Versioning:** prefix **`/api/v1`** cố định; KHÔNG mở `/v2` cho tới khi có breaking thật sự không thể expand-contract. Với 1 FE + 1 MCP client đều do mình kiểm soát, versioning nặng (per-resource, header-based) là over-engineering — semver của spec artifact (2.4) mới là công cụ điều phối chính.

**Quy tắc backward-compat (bắt buộc, ghi vào CONTRIBUTING của repo A):**

| # | Quy tắc | Lý do gắn với repo này |
|---|---|---|
| 1 | Chỉ THÊM field (additive); không đổi nghĩa/đổi kiểu field đang có; field bỏ đi phải deprecated ≥1 release trước khi xoá | FE là tolerant-reader mặc định (TS bỏ qua field lạ) |
| 2 | `Task.status` truyền qua wire là string mở + validate server theo STATUS_META, KHÔNG enum cứng trong spec (cho tới khi audit status chốt) | 6 status video mới + `SALARY_PENDING_STATUSES` đếm tiền editor — enum cứng phía FE sẽ gãy khi BE thêm status (bài học F2 `docs/review-fixes/`) |
| 3 | Response DTO theo quyền (Admin/Staff/Portal — 2.2.2) là 3 schema RIÊNG trong spec, không dùng 1 schema optional-field | Chống tái diễn leak jobPriceUSD kiểu marketplace |
| 4 | Endpoint mutation giữ optimistic-lock/idempotency semantics đã có (version CAS của claimTask/updateTaskStatus, ledger webhook Mux) — mã hoá vào spec bằng 409/423 + header `Idempotency-Key` cho bulk | Các race đã từng vá (TOCTOU invitation, double-billing invoice) không được tái sinh qua REST |

**Thứ tự deploy (expand–contract, lặp lại mỗi release có đổi contract):**

```
1. DB expand    — Flyway migration additive (cột/bảng mới, chưa xoá gì)     [repo A]
2. BE deploy    — code mới đọc-ghi được CẢ dạng cũ lẫn mới; spec MINOR mới  [repo A]
3. FE deploy    — bump spec artifact, regenerate orval client, dùng field mới [repo B]
4. DB contract  — dọn cột/bảng cũ SAU khi xác nhận không còn traffic dạng cũ [repo A, release sau]
```

Rollback: vì BE luôn tương thích N-1, **FE rollback được độc lập bất kỳ lúc nào**; BE rollback chỉ an toàn trước bước 4 — đó là lý do bước 4 luôn để sang release sau. (So với hiện trạng: `prisma db push` trong build TRỘN cả 4 bước vào 1 lần push — đây chính là cái polyrepo phải thoát.)

**Contract test — chọn mức nhẹ, đúng quy mô 1 consumer:**

- **Cổng 1 (bắt buộc, repo A):** `openapi-diff` spec-mới vs spec-release trong CI — fail merge khi breaking mà version không nhảy MAJOR.
- **Cổng 2 (bắt buộc, repo B):** regenerate orval client từ spec pin + `tsc --noEmit` trong CI — compile pass = FE tương thích spec đã pin.
- **Cổng 3 (khuyến nghị):** smoke Schemathesis chạy spec chống BE staging (fuzz response conformance) trước promote prod.
- **KHÔNG dùng** Pact/Spring Cloud Contract: broker + provider-state ceremony chỉ trả lãi khi nhiều consumer độc lập; ở đây chỉ có FE + mcp-server, cả hai cùng sinh từ một spec.

Lưu ý cuối: cả hai repo đều PHẢI có CI ngay từ ngày tách (hiện trạng là **zero CI** — §1.1). Tối thiểu: repo A = build + test + openapi-diff; repo B = lint + tsc + build + 8 harness `test:*` nào còn áp dụng được sau khi actions dời đi (phần lớn harness test invariant DB → dời theo về repo A thành integration test chạy trên DB test — tiền lệ đã có: `.env.test` + Neon test branch, `parts/01` §6.1 ghi chú).

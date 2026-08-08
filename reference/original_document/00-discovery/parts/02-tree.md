# 02 — Cây thư mục & Bố cục repo (Discovery)

> Phạm vi: vẽ cây thư mục mức cao (2–3 cấp, chỉ thư mục "sống"), xác định monorepo, phân vùng frontend/backend/db/shared, đếm số liệu. Mọi số liệu đếm bằng `find`/`grep` trên repo thật, bỏ qua `node_modules`, `.next`, `dist`, `build`, `.git`, `__pycache__`.

## 1. Kết luận kiến trúc tổng

| Câu hỏi | Kết luận | Bằng chứng |
|---|---|---|
| Monorepo? | **Multi-package repo, KHÔNG phải npm-workspaces monorepo.** Root là 1 app Next.js (`blazing-station`), không có field `workspaces` trong `package.json`; 3 package con có `package.json` + `node_modules` riêng, build bằng script `cd` thủ công. | `package.json:11` (`"build:mcp": "cd mcp-server && npm run build"`), `package.json:12` (`build:electron`), `mcp-server/package.json:2` (`hustly-tasker-mcp`), `electron/package.json:2` (`hustly-tasker-desktop`), `website/package.json:2` (`hustlytasker-landing`) |
| Frontend ở đâu? | `src/app/**` (App Router pages, 68 `page.tsx`) + `src/components/**` (330 file) + `src/styles`, `src/hooks`. Landing marketing tách riêng ở `website/` (Vite, không dính Next). | đếm mục 4; `website/vite.config.js` |
| Backend ở đâu? | Cùng app Next.js: `src/app/api/**` (102 `route.ts`) + `src/actions/**` (55 file server actions) + `src/middleware.ts` (session JWT + device detection). Backend phụ: `mcp-server/src` (18 file — MCP tools thao tác task qua Prisma). | `src/middleware.ts:3` (import `decrypt/encrypt` từ `@/lib/jwt`), `src/middleware.ts:24-31` (device detection mobile/desktop) |
| DB ở đâu? | `prisma/schema.prisma` — **67 model** (từ `Profile` dòng 11 tới `RateLimitBucket` dòng 2052). Repo dùng `prisma db push` ngay trong `postinstall` (không migrate). | `prisma/schema.prisma:11`, `prisma/schema.prisma:2052`, `package.json:10` (`"postinstall": "prisma generate && prisma db push"`) |
| Shared ở đâu? | `src/lib/**` (172 file — dùng chung cho pages/actions/api), `src/types`, `src/config`, `src/i18n` + `messages/` (next-intl, 5 locale). | `package.json:98` (`next-intl`), `src/i18n/request.ts`, `messages/` (en/vi/ru/it/zh) |

## 2. Cây thư mục mức cao (chỉ thư mục "sống")

```
cranky-austin/  (root = app Next.js 15 "blazing-station")
├── src/                        # TOÀN BỘ app chính (780 file .ts/.tsx)
│   ├── app/                    # App Router: pages + API routes (208 file)
│   │   ├── [workspaceId]/      #   vùng app sau đăng nhập (per-workspace)
│   │   │   ├── dashboard/      #     UI staff/editor (tasks, salary, schedule, profile, errors)
│   │   │   ├── admin/          #     UI admin (18 page: finance, payroll, crm, members, queue, settings…)
│   │   │   ├── mc/             #     "Mission Control" — UI admin desktop song song (21 page)
│   │   │   ├── team/           #     Review module: file browser "Tệp" (route group (browser): folder/shares/trash) + asset/[assetId]
│   │   │   ├── task/[taskId]/  #     trang chi tiết task
│   │   │   └── @modal/(.)task/ #     parallel route — task mở dạng modal intercept
│   │   ├── api/                #   backend REST (102 route.ts) — chi tiết mục 3
│   │   ├── share/[token]/      #   portal khách (public, token-based)
│   │   ├── r/[slug]/           #   trang guest review video (public) + unsubscribe
│   │   ├── login|signup|forgot-password|welcome|account|legal/   # auth + public
│   │   ├── portal-notify/      #   unsubscribe email portal
│   │   └── desk-preview|velox-v4-preview|diagnostic/             # trang preview/dev harness
│   ├── actions/                # 55 file server actions (task, payroll, invoice, crm, velox…)
│   ├── components/             # 330 file, 27 nhóm domain (bảng mục 5)
│   ├── lib/                    # 172 file logic dùng chung (82 root + lib/review 57 + lib/velox 11 …)
│   ├── hooks/                  # 6 hook
│   ├── i18n/                   # request.ts + routing.ts (next-intl)
│   ├── config/                 # brand.ts, mobile-nav.ts, velox.roles.json
│   ├── types/                  # 3 file (admin, notification, index)
│   ├── styles/                 # portal-calm.css, portal-desk.css
│   └── middleware.ts           # session JWT rolling-refresh + device detection
├── prisma/                     # schema.prisma (67 model), seed.ts, migrations{,-manual}, dev.db (SQLite sót lại)
├── mcp-server/                 # package riêng: MCP server (src/ 18 file: tools/ + services/)
├── electron/                   # package riêng: desktop wrapper (main/ 9 file: window, tray, cron, next-server)
├── website/                    # package riêng: landing Vite (index.html, src/, public/)
├── messages/                   # i18n JSON: en, vi, ru, it, zh
├── public/                     # PWA (manifest.json, sw.js, icons), sounds/, media/, video-assets/
├── scripts/                    # 151 file script vận hành/backfill/audit + test:* harness
├── tests/                      # 9 unit test (chỉ velox-v4)
├── docs/                       # ~11MB đặc tả + audit (review-module, review-fixes, mobile-redesign, security-audit…)
├── api/                        # 2 file Python rời (scoring.py, vdownloader.py) — không thuộc app Next
├── agency-agents/              # thư viện agent vendored (có LICENSE/README riêng) — không phải code app
├── design-system/, assets/, copy/, presentation/, market-research/   # tài liệu/asset thiết kế & pitch
└── (root rác: ~40 file check-*.js/debug-*.js, .codex-studyplace-dev.log 135MB, tmp/, .tmp/, test-results/)
```

## 3. Vai trò thư mục cấp 1 & cấp 2 quan trọng

### 3.1 `src/app` — route groups

| Nhóm route | Vai trò | Ghi chú |
|---|---|---|
| `src/app/[workspaceId]/dashboard` | App của staff/editor (tasks, salary, schedule) | 1 trong 7 `layout.tsx` toàn app |
| `src/app/[workspaceId]/admin` | UI admin gốc — 18 `page.tsx` (analytics, audit-log, crm, finance, members, payroll, queue, requests, schedule, settings…) | `src/app/[workspaceId]/admin/layout.tsx` có guard riêng |
| `src/app/[workspaceId]/mc` | "Mission Control" — bộ UI admin desktop SONG SONG, 21 `page.tsx` (add, board, crm, finance, tep, tien, lich, ho-so…) | 2 UI admin cùng tồn tại (admin vs mc) — cần theo dõi trùng chức năng |
| `src/app/[workspaceId]/team` | Review module phía nội bộ: file browser "Tệp" (route group `(browser)`: `folder/[folderId]`, `shares`, `trash`) + player `asset/[assetId]` | |
| `src/app/[workspaceId]/task/[taskId]` + `@modal/(.)task/[taskId]` | Chi tiết task, kèm parallel route intercept để mở modal | `src/app/[workspaceId]/@modal/default.tsx` |
| `src/app/share/[token]` | Portal khách public (token) — mount `SharePortalClient` | `src/app/share/[token]/page.tsx:6` |
| `src/app/r/[slug]` | Trang guest review video public + `r/unsubscribe` | |
| `login`, `signup`, `forgot-password`, `welcome`, `account/trash`, `legal/{privacy,terms}` | Auth + trang public | |
| `desk-preview`, `velox-v4-preview`, `diagnostic` | Trang preview/dev harness (mount trực tiếp component nội bộ) | `src/app/desk-preview/DeskHarness.tsx` |

### 3.2 `src/app/api` — backend groups (102 `route.ts`)

| Nhóm | Vai trò |
|---|---|
| `api/review/*` | 15 nhóm con của review module (assets, comments, folders, shares, statuses, task-upload, tree, uploads, versions, trash…) |
| `api/r/[slug]/*` | API cho guest review (comments, decision, download-url, events, identity, notifications…) |
| `api/cron/*` | 7 cron job: auth-cleanup, check-deadline, cleanup-notifications, hard-delete-profiles, hard-delete-workspaces, review-janitor, send-digest |
| `api/auth`, `api/profile`, `api/workspace`, `api/notifications`, `api/invoices`, `api/share/[token]`, `api/exports`, `api/integrations`, `api/webhooks`, `api/inngest`, `api/time`, `api/exchange-rate`, `api/portal-notify`, `api/log-client-error`, `api/test-email`, `api/import-jan-2026` | Các nhóm còn lại; `api/inngest/route.ts` là endpoint background jobs (Inngest, `package.json:91`) |

### 3.3 Các thư mục `src` còn lại

| Thư mục | Số file | Vai trò |
|---|---|---|
| `src/actions` | 55 | Server actions theo domain: task/bulk-task/task-comment, payroll/payment/bonus, invoice, crm/client-request, member/profile, share-portal/share-link, velox-batch, study-place… |
| `src/lib` (root) | 82 | Hạ tầng chung: `db.ts`, `auth.ts`/`jwt.ts`/`auth-guard.ts`, `email.ts`+`notification-*`, `pricing-engine.ts`, `payroll-cycle.ts`, `task-state-machine.ts`/`task-statuses.ts`, `workspace-*` guards, `rate-limit*.ts`, `serialization.ts` |
| `src/lib/review` | 57 | **Domain lớn nhất trong lib** — toàn bộ logic review module: `mux.ts`/`mux-jwt.ts`, `r2.ts`, `upload-engine/service/store`, `share-*` (auth/comments/decision/guest/tracking), `status.ts`/`status-map.ts`, `notify.ts`, `inngest.ts`, `route-auth.ts`, `access.ts` |
| `src/lib/velox` | 11 | Engine phân loại footage Velox v4 (tokenizer, grouper, role-classifier, hook-graph) |
| `src/lib/notification-emails`, `src/lib/store` | — | Template email + zustand store (`useStudyStore.ts`) |
| `src/hooks` | 6 | `useAutoSaveDraft`, `useHistoryBackClose`, `useKeyboardInset`, `usePresence`, `useScrollDirection`, `useSupabaseChannel` |
| `src/i18n` | 2 | `request.ts`, `routing.ts` — cấu hình next-intl (`package.json:98`), locale JSON ở `messages/` (en/vi/ru/it/zh) |
| `src/config` | 3 | `brand.ts`, `mobile-nav.ts`, `velox.roles.json` |
| `src/types` | 3 | `admin.ts`, `notification.ts`, `index.ts` |
| `src/styles` | 2 | CSS 2 skin portal: `portal-calm.css`, `portal-desk.css` |

### 3.4 Ngoài `src`

| Thư mục | Vai trò | Bằng chứng |
|---|---|---|
| `prisma/` | Schema 67 model + `seed.ts` (`package.json:25`) + `migrations/`, `migrations-manual/`. ⚠️ có `prisma/dev.db` (SQLite) sót lại dù prod là Neon Postgres | `prisma/schema.prisma:11-2052` |
| `mcp-server/` | MCP server cho Claude thao tác task (18 file: `src/tools/` 6 file, `src/services/` 8 file, auth-context, workspace-scoping) | `mcp-server/src/index.ts` |
| `electron/` | Desktop wrapper: `main/` 9 file (window-manager, tray, cron-scheduler, next-server, setup-wizard, ipc-handlers, preload) | `electron/main/index.ts` |
| `website/` | Landing microsite Vite riêng biệt, KHÔNG import gì từ `src/` | `website/vite.config.js` |
| `messages/` | 5 file locale next-intl: `en.json`, `vi.json`, `ru.json`, `it.json`, `zh.json` | |
| `public/` | PWA assets: `manifest.json`, `sw.js`, icons 192/512/maskable, `sounds/`, `media/`, `video-assets/` | |
| `scripts/` | 151 file — backfill/audit/ops một-lần + test harness chạy qua `tsx` (`test:invite-security`… `package.json:15-22`) | |
| `tests/` | 9 unit test, CHỈ cho engine velox-v4 (`tests/velox-v4/*.test.ts`) — phần còn lại của app không có unit test trong thư mục này | |
| `docs/` | ~11MB đặc tả: `review-module/`, `review-fixes/`, `mobile-redesign/`, `security-audit/`, `system-audit/` (audit này), chat/, pricing/, testing/ | |
| `api/` (root) | 2 script Python rời (`scoring.py`, `vdownloader.py`) — không được app import, orphan-candidate | `api/scoring.py`, `api/vdownloader.py` |
| `agency-agents/`, `design-system/`, `assets/`, `copy/`, `presentation/`, `market-research/` | Vendored agent library / tài liệu thiết kế / asset pitch — không phải runtime code | `agency-agents/LICENSE` |
| Root rác | ~40 file `check-*.js`/`debug-*.js` một-lần nằm ngay root, log 135MB `.codex-studyplace-dev.log`, `tmp/`, `.tmp/`, `test-results/` | `check-admin.js`, `check_vincent.js`… |

## 4. Số liệu đếm (find/grep, loại trừ node_modules/.next/dist)

| Chỉ số | Số | Cách đếm |
|---|---|---|
| Tổng `.ts/.tsx` trong `src/` | **780** (421 `.tsx` + 359 `.ts`) | `find src -name "*.ts" -o -name "*.tsx"` |
| File trong `src/components` | **330** (315 `.tsx`) | 27 thư mục domain + 17 file lẻ ở root components |
| File trong `src/app` | **208** — gồm **68 `page.tsx`**, **102 `route.ts`**, **7 `layout.tsx`** | |
| Server actions (`src/actions`) | **55** | |
| File lib (`src/lib`) | **172** (82 root + 57 `review/` + 11 `velox/` + còn lại) | |
| Hooks (`src/hooks`) | **6** | |
| Prisma models | **67** | `grep -c "^model " prisma/schema.prisma` |
| API `route.ts` cron | 7 job | `src/app/api/cron/` |
| `mcp-server/src` | 18 file `.ts` | |
| `electron/main` | 9 file `.ts` | |
| `scripts/` | 151 file | |
| `tests/` | 9 file test (chỉ velox-v4) | |
| Locale i18n | 5 (`messages/`) | |

### 4.1 `src/components` — 330 file, phân theo domain (đếm `.ts/.tsx` từng thư mục)

| Domain | Số file | Domain | Số file |
|---|---|---|---|
| `review/` | 41 | `profile/` | 10 |
| `dashboard/` | 38 | `schedule/` | 8 |
| `portal/` | 33 (calm 20 + desk 12 + share 1) | `workspace/` | 7 |
| `ui/` | 28 | `radial-nav/`, `notifications/`, `mobile/`, `marketplace/` | 6 mỗi cái |
| `admin/` | 28 | `auth/` | 5 |
| `tasks/` | 18 | `invoice/` | 4 |
| `mission-control/` | 18 | `tags/`, `study-place/` | 3 mỗi cái |
| `crm/` | 14 | `tracking/`, `settings/` | 2 mỗi cái |
| `velox/` | 12 | `tiptap/`, `landing/`, `brand/`, `account/` | 1 mỗi cái |
| `layout/` | 11 | (root components, file lẻ) | 17 |

## 5. Phát hiện 2+ phiên bản cùng chức năng

| Chức năng | Bản ĐANG dùng (được import) | Bản dead-code candidate | Bằng chứng |
|---|---|---|---|
| Bảng task desktop | `src/components/NewDesktopTaskTable.tsx` — import bởi `src/components/TaskTable.tsx`, `src/components/dashboard/DashboardActionWrapper.tsx`; `TaskTable` mount ở `src/app/[workspaceId]/admin/queue/page.tsx` | **`src/components/DesktopTaskTable.tsx`** — grep toàn `src/` không có import nào | `grep -rln "components/DesktopTaskTable" src` → 0 kết quả |
| UI admin | `[workspaceId]/admin` (18 page) **và** `[workspaceId]/mc` (21 page) đều mount song song — KHÔNG phải dead code, là 2 UI thay thế nhau có chủ đích ("Mission Control"), nhưng là điểm trùng chức năng lớn nhất repo | — | mục 3.1 |
| Skin portal khách | `share/[token]` mount `portal/share/SharePortalClient` (bản này lại import cả `portal/desk` + `portal/calm` như sub-view) — cả 3 cây đều sống | — | `src/app/share/[token]/page.tsx:6`; `grep -rln "portal/desk" src` |

## 6. Ghi chú cho các agent audit sau

1. Repo là **1 app Next.js full-stack** (UI + API + actions cùng chỗ) — ranh giới frontend/backend nằm ở `src/app/api` + `src/actions` chứ không phải theo package.
2. `src/lib/review` (57 file) + `src/components/review` (41 file) + `api/review` + `api/r` + `[workspaceId]/team` + `r/[slug]` là **một domain review xuyên suốt 5 tầng** — audit domain này phải quét đủ cả 5 chỗ.
3. Test tự động chính thức chỉ có 9 file (velox-v4); phần còn lại kiểm bằng script harness trong `scripts/` (chạy `tsx`, khai báo ở `package.json:15-22`).
4. Root repo ô nhiễm nặng: ~40 script `check-*/debug-*` một-lần, log 135MB, `prisma/dev.db` — ứng viên dọn dẹp, không ảnh hưởng runtime.

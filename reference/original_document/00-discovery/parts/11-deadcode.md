# 11 — Dead code / File rác đã loại trừ (có bằng chứng)

> Phạm vi: file rác root, folder nghi vấn (đặc biệt `api/` deploy lên Vercel), trang preview, spot-check `src/components` + `src/lib`, và danh sách "trông rác nhưng PHẢI GIỮ".
> Phương pháp: `git ls-files` (tracked hay không) + grep import/reference trong `src/`, `mcp-server/src`, `electron/main`, `scripts/`, `package.json` + `git log -1 --format=%ci` (ngày commit cuối). "0 hit" = không có bất kỳ file sống nào import/gọi tới.

---

## 1. File rác ở ROOT (đang bị Git TRACK — tức là vẫn được đẩy lên repo/deploy)

Tất cả các file dưới đây **đều tracked trong git** (`git ls-files` xác nhận) nhưng **0 hit** khi grep tên file trong `src/`, `package.json` (scripts), `mcp-server/src`, `electron/main`. Lệnh grep gộp toàn bộ tên (check-admin|check-all|…|audit-confirmed) trả về **không một dòng nào**.

### 1.1. Script debug DB một-lần (Prisma one-off, chạy tay bằng `node`)

| File | Lý do loại | Bằng chứng |
|---|---|---|
| `check-admin.js`, `check-all-tasks.js`, `check-all.js`, `check-bonuses.js`, `check-clients.js`, `check-db.js`, `check-phuc.js`, `check-phuc2.js`, `check-profiles-users.js`, `check-recent-invoices.js`, `check-roles.js`, `check-task.js`, `check-tasks.js`, `check-user-linh.js`, `check-users.js` (15 file) | Script điều tra DB một-lần thời kỳ đầu (`new PrismaClient()` rồi query tay — xem `check-admin.js:1`). Không nằm trong `package.json` scripts, không import từ đâu | grep 0 hit; commit cuối `check-admin.js` = **2026-03-14** |
| `check_all.js`, `check_all_tasks.js`, `check_db.ts`, `check_vincent.js`, `check_vincent_global.js` | Cùng loại, đặt tên snake_case | grep 0 hit; `check_vincent.js` commit cuối **2026-04-02** |
| `debug-action.js`, `debug-leaderboard.js` | Debug một-lần | grep 0 hit; `debug-action.js` commit cuối **2026-03-14** |
| `cleanup-tasks.js` | **NGUY HIỂM**: gọi `prisma.task.deleteMany` (`cleanup-tasks.js:5`) — script xoá dữ liệu prod nằm chỏng chơ ở root, ai chạy nhầm là mất task | grep 0 hit; commit cuối **2026-03-14** |
| `fix-production-db.js`, `restore_final.js`, `restore_salary.js` | Script sửa/khôi phục dữ liệu prod một-lần (sự cố cũ) | grep 0 hit; `fix-production-db.js` = **2026-03-01**, `restore_salary.js` = **2026-04-01** |
| `search_missing_tasks.ts`, `_v2.ts`, `_v3.ts`, `search_missing_tasks_v4.js`, `_v5.js` | 5 phiên bản cùng một cuộc điều tra "task mất tích" (v1→v5) — điển hình file rác lặp phiên bản | grep 0 hit; tracked (`git ls-files`) |
| `reset-daniel.ts`, `find-ids.js`, `find_hustly.js`, `list-all-users.js`, `list-billing-profiles.js`, `list-phuc-tasks.js`, `count-null-profile-tasks.js` | One-off theo tên người/khách cụ thể | grep 0 hit |

### 1.2. File data dump / output điều tra

| File | Lý do loại | Bằng chứng |
|---|---|---|
| `all_tasks_kcd.txt`, `all_users_output.txt` | Output console của các script check-* ở trên (dump dữ liệu THẬT của user/task lên repo) | grep 0 hit; commit cuối **2026-04-02**; tracked |
| `missing_task_findings.txt` | File **0 byte** | `ls -la` size = 0; tracked |
| `pending_tasks_export.md` | Dump export task cũ | commit cuối **2026-03-04**; tracked |
| `rebuild.txt` | Nội dung đúng 1 dòng `"force rebuild"` (mẹo trigger deploy cũ) | đọc file; commit cuối **2026-03-10** |
| `audit-confirmed.json` (284KB) | Output audit cũ; **đã được thêm vào `.gitignore` (dòng cuối)** nên hiện untracked — chỉ còn rác local | `.gitignore` dòng cuối; `git log` trống |
| `.codex-studyplace-dev.log` (**135MB!**) | Log dev của Codex, untracked, chiếm 135MB ổ đĩa | `ls -la` = 135.123.488 bytes |
| `scratch-stream-test.mp4` | Video test upload còn sót, untracked | `git status` `??` |
| `C:UsersDareu.claudeplanskind-gliding-wren-agent-*.md` | File sinh ra do lỗi ghi đường dẫn Windows (tên file chứa nguyên path), untracked | `git status` hiển thị tên bị escape `"C\357\200\272Users..."` |

### 1.3. Đặc tả/di sản .docx/.pptx/.md ở root (tài liệu, không phải code — nhưng đang tracked)

| File | Lý do loại | Bằng chứng |
|---|---|---|
| `BlazingStation_SRS.docx`, `BlazingStation_SRS.md`, `AgencyManager_SRS.docx`, `AgencyManager_PRD_Phase2.docx`, `AgencyManager_SiteMap.pptx` (590KB), `AgencyManager_UserFlow.pptx` (879KB) | Đặc tả thời "BlazingStation/AgencyManager" (tên cũ của sản phẩm — nay là Velox/HustlyTasker). Không code nào đọc | tracked; commit cuối cả cụm **2026-06-04** (commit dọn, không phải cập nhật nội dung) |
| `AUDIT_REPORT.md`, `QA_REPORT.md`, `INVITE_SECURITY_AUDIT.md`, `RAILWAY_MIGRATION.md`, `IMPLEMENTATION-NOTES.md` (98KB), `CLIENTS-MANAGER-UI-UX.md`, `Client_Manager_Sitemap.md`, `Client_Manager_Workflow.md`, `Dashboard_Sitemap.md`, `TONG-QUAN-HE-THONG.md`, `VELOX.md`, `VELOX-OPERATIONS.md`, `HUSTLYTASKER-VIDEO-BRIEF.md` | Báo cáo/đặc tả các đợt làm việc cũ nằm root thay vì `docs/` | tracked (`git ls-files`); grep 0 hit từ code |
| `AUDIT.md`, `MIGRATION_ANALYSIS.md`, `MIGRATION_VERIFY.md`, `PHASE2_EXPORT_PLAN.md`, `ADD_TASK_VELOX_SPEC.md`, `HUSTLYTASKER_LANDING_PROMPTS.md` (93KB), `p3_plan_digest.md` | Cùng loại nhưng **untracked** (`git status ??`) — rác local | `git status` `??` |

### 1.4. Pipeline sinh dữ liệu study-place (một-lần nhưng CÓ GIÁ TRỊ tái tạo)

| File | Phân loại | Bằng chứng |
|---|---|---|
| `extract.ps1` → `extracted_questions.txt` (70KB) → `parse.js` | One-off, untracked, NHƯNG `parse.js` là generator của `src/lib/study-place-data.json` (file dữ liệu ĐANG SỐNG trong app) — nếu xoá thì mất cách tái tạo data. Đề nghị: dời vào `scripts/` kèm README thay vì xoá mù | `parse.js:4-5`: `inputPath = extracted_questions.txt`, `outputPath = src/lib/study-place-data.json`; `src/lib/study-place-data.json` tồn tại trong `ls src/lib/` |

---

## 2. Folder nghi vấn

### 2.1. `api/` ở root — **QUAN TRỌNG NHẤT: dead code NHƯNG VẪN ĐANG ĐƯỢC DEPLOY**

| Mục | Kết quả |
|---|---|
| Tồn tại thật? | CÓ — chứa đúng 2 file: `api/scoring.py` (5.3KB), `api/vdownloader.py` (6.9KB), commit cuối lần lượt **2026-01-30** và **2026-03-05** |
| Có được deploy? | **CÓ** — cả 2 file **tracked trong git** (`git ls-files` ra `api/scoring.py`, `api/vdownloader.py`) và `vercel.json:3-5` khai báo block `"functions": { "api/*.py": { "maxDuration": 10 } }` → Vercel build chúng thành Python serverless function tại `/api/scoring`, `/api/vdownloader` |
| Có ai gọi không? | **KHÔNG** — grep `vdownloader|api/scoring` trong `src/`, `mcp-server/src`, `electron/main`, `scripts/` = 0 hit; 7 cron trong `vercel.json` không có path nào trỏ tới |
| Nội dung | `scoring.py`: kết nối thẳng Postgres bằng `pg8000` + check `CRON_SECRET` (`api/scoring.py:5,13`) — logic "AI scoring" cũ. `vdownloader.py`: tải video YouTube bằng `yt_dlp` + `YOUTUBE_COOKIES` (`api/vdownloader.py:3,33`) |
| Rủi ro | Đây là **attack surface sống không ai canh**: endpoint Python có quyền đọc `DATABASE_URL` (scoring.py chỉ chặn khi `CRON_SECRET` được set — fail-open nếu env thiếu, xem `api/scoring.py:15`) + endpoint tải video tuỳ ý. Đề nghị xoá cả folder + block `api/*.py` trong `vercel.json` + `requirements.txt` |
| File ăn theo | `requirements.txt` root (`pg8000, yt-dlp, requests, static-ffmpeg`) chỉ tồn tại để phục vụ 2 function này — chết theo. Commit cuối **2026-03-05** (cùng ngày vdownloader) |

### 2.2. Các folder còn lại

| Folder | Kết luận | Bằng chứng |
|---|---|---|
| `agency-agents/` (9.3MB) | RÁC — bản clone repo mẫu agent bên ngoài (có `CONTRIBUTING.md`, `LICENSE`, `SECURITY.md`, `divisions.json`, thư mục `academic/`, `game-development/`…), untracked, không liên quan app | `git status` `??`; `ls agency-agents/` |
| `copy/` | RÁC nhẹ — chỉ 1 file `copy/brand-kit.md` (brand kit cho landing), untracked, không code nào đọc | `ls copy/`; `git status` `??` |
| `assets/` (42MB) | **GIỮ** (media nguồn của landing microsite `website/`) — skill `hustlytasker-landing` quy định "Uses ONLY pre-generated media already saved under assets/" và quy trình copy `assets/videos/` → `website/public/media/` | `.agents/skills/hustlytasker-landing/SKILL.md:3,11,69`; `assets/videos/htl-scroll-background*.mp4` tồn tại |
| `.codex-workbook-analysis/` (4MB) | RÁC — phân tích workbook một-lần của Codex (có cả `node_modules/` riêng, `workbook_dump.json`, contact-sheet PNG), untracked | `ls .codex-workbook-analysis/`; `git status` `??` |
| `.tmp/` (~45MB) | RÁC + **NHẠY CẢM**: `.tmp/video-report/` chứa `chrome-default-history.sqlite` (**36MB**) và `chrome-profile7-history.sqlite` (8MB) — bản copy LỊCH SỬ TRÌNH DUYỆT thật nằm trong repo folder (untracked, nhưng nên xoá ngay) | `ls -la .tmp/video-report` |
| `docs/` (11MB) | TÀI LIỆU, không phải code — 4 dự án đặc tả (review-module, review-fixes, mobile-redesign, security-audit…) + báo cáo audit. Không file nào được import từ `src/`. Phần lớn untracked | `ls docs/`; `git status` `??` hàng loạt `docs/...` |
| `prisma/dev.db` (40KB) | RÁC — SQLite thời prototype, trong khi datasource thật là **PostgreSQL/Neon** (`prisma/schema.prisma:6-8`: `provider = "postgresql"`). Vẫn đang tracked! Commit cuối **2026-01-24** (cổ nhất repo) | `git ls-files` có `prisma/dev.db`; schema.prisma:7 |
| `prisma/seed-errors.js` | RÁC — seed "ERROR_DICTIONARY" cũ; seed chính thức là `prisma/seed.ts` (khai báo tại `package.json:25` `"seed": "npx tsx prisma/seed.ts"`). grep `seed-errors` trong package.json/src/scripts = 0 hit | `package.json:24-26`; commit cuối **2026-03-25** |
| `market-research/` | Deliverable nghiên cứu thị trường (HTML/PDF pitch), untracked, không phải code app | `ls market-research/`; `git status` `??` |
| `design-system/` | GIỮ — `design-system/agencymanager/MASTER.md` tracked, được rule `.claude/rules/ui-ux-standards.md` tham chiếu ("Lấy thông báo từ MASTER.md") | `git ls-files` có `design-system/agencymanager/MASTER.md` |

---

## 3. Trang preview trong `src/app/`

| Route | Kết luận | Bằng chứng |
|---|---|---|
| `src/app/welcome/` | **SỐNG — KHÔNG PHẢI dead code.** Là đích redirect chính khi profile 0 workspace | `src/lib/post-login.ts:25,33` (`return '/welcome'`); `src/components/dashboard/DashboardTopBar.tsx:74,332`; `UserHomeTopBar.tsx:110,459`; `DeleteProfileModal.tsx:34` |
| `src/app/desk-preview/` | GIỮ (dev harness CÓ CHỦ ĐÍCH, đã tự khoá prod) — preview portal "The Desk" với mock data; `notFound()` khi chạy production thật | `src/app/desk-preview/page.tsx:18`: `if (NODE_ENV === 'production' && VERCEL_ENV !== 'preview') notFound()`; không link nào trỏ tới (grep `desk-preview` = 0 hit ngoài chính nó) |
| `src/app/velox-v4-preview/` | GIỮ (dev harness, khoá bằng env) — preview engine Velox v4, `notFound()` trừ khi `NEXT_PUBLIC_ENABLE_VELOX_V4_PREVIEW=1` | `src/app/velox-v4-preview/page.tsx:21-22`; grep chỉ ra self-reference trong comment `page.tsx:4` |
| `src/app/diagnostic/` | **DEAD-CODE CANDIDATE** — chỉ còn stub 7 dòng in chữ "Công cụ chẩn đoán hiện đang bị tắt vì lý do bảo mật", không gate, không ai link tới (grep `/diagnostic` href/redirect = 0 hit). Route public vô nghĩa → xoá được | `src/app/diagnostic/page.tsx:1-7`; commit cuối **2026-06-23** |

---

## 4. Spot-check dead code trong `src/components` + `src/lib`

Cách kiểm: grep `from '.../<TênFile>'` + grep tên trần (bắt dynamic import / `new Worker`) toàn `src/`.

| File | Tình trạng | Bằng chứng |
|---|---|---|
| `src/components/DesktopTaskTable.tsx` (**53KB**) | **Import nhưng KHÔNG BAO GIỜ render** — `TaskTable.tsx` import cả 2 bản, comment thẳng "Keeping for reference if needed", nhưng chỉ return `NewDesktopTaskTable`. Hệ quả: 53KB code chết **vẫn bị bundle** vì import không bị tree-shake ở mức file page | `src/components/TaskTable.tsx:9` (import + comment), `TaskTable.tsx:33` (chỉ render `NewDesktopTaskTable`); commit cuối 2026-07-11 |
| `src/components/TaskCreationManager.tsx` | **0 importer** — cụm chết dây chuyền: nó là importer DUY NHẤT của `CreateTaskForm.tsx` và `BulkCreateTaskForm.tsx` → cả 3 file chết cùng nhau | grep import `TaskCreationManager` = 0 hit; `TaskCreationManager.tsx:4-5` là nơi duy nhất import 2 form kia; commit cuối **2026-03-30** |
| `src/components/RoleSwitcher.tsx` | 0 importer, 0 reference trần | grep = 0 hit; commit cuối 2026-06-23 |
| `src/components/TreasurerToggle.tsx` | 0 importer | grep = 0 hit; commit cuối **2026-03-02** |
| `src/components/DeleteUserButton.tsx`, `src/components/ResetPasswordButton.tsx` | 0 importer | grep = 0 hit |
| `src/lib/TimerWorker.ts` | 0 reference (kể cả pattern `new Worker`/tên trần) — web worker timer sidebar cũ | grep tên trần = 0 hit ngoài chính file; commit cuối **2026-02-06** |
| `src/lib/calendar-sync.ts` | 0 importer — scaffold OAuth Google/Outlook Calendar chưa bao giờ nối vào đâu | grep = 0 hit; commit cuối 2026-03-19 |
| `src/lib/gemini-translator.ts` | 0 importer. Tên là "gemini" nhưng ruột dùng **OpenAI** (`gemini-translator.ts:1-5`) | grep = 0 hit; commit cuối 2026-03-09 |
| Dependency `@google/generative-ai` (`package.json:36`) | **DEPENDENCY CHẾT** — không một file nào trong `src/`, `scripts/`, `mcp-server/src`, `electron/` import `generative-ai`/`GoogleGenerativeAI` (chỉ xuất hiện trong package.json và bản copy trong artifact `electron/release/` vốn đã gitignore) | grep toàn repo (trừ node_modules) = 0 hit code |

**Phản-ví dụ (trông chết nhưng SỐNG — không được xoá):** `src/lib/smart-qr.ts` grep import tĩnh = 0 hit, nhưng sống qua **dynamic import** tại `src/components/profile/PaymentQrUpload.tsx:38`: `await import('@/lib/smart-qr')`. Bài học: mọi kết luận dead-code ở repo này phải grep cả tên trần, không chỉ `from '...'`.

---

## 5. GIỮ LẠI dù trông nghi vấn (harness/hạ tầng sống)

| File/Folder | Vì sao GIỮ | Bằng chứng |
|---|---|---|
| `scripts/test-*.ts` (8 file: invite-security, client-invariant, status-meta, portal-derive, auto-transition, folder-scope, folder-scope-db, portal-notify) | Là regression harness chính thức, gắn trong npm scripts | `package.json:15-22` (`"test:invite-security": "tsx scripts/test-invite-security.ts"`, …) |
| `scripts/probe-*.ts`, `scripts/backfill-*.ts`, `scripts/rollback-*.json` | One-off NHƯNG là bằng chứng/rollback của các đợt sửa dữ liệu prod (kèm file rollback JSON có timestamp) — giữ trong `scripts/` là đúng chỗ | `git status` `??` `scripts/rollback-invoice-ws-backfill-2026-06-30...json` |
| `messages/` (en/vi/zh/it/ru.json) | i18n ĐANG SỐNG — được import tĩnh | `src/i18n/request.ts:17-21` |
| `mcp-server/`, `electron/` | Build target chính thức | `package.json:11-14` (`build:mcp`, `build:electron`, `build:desktop`, `dev:electron`) |
| `website/` | Landing microsite Vite (tracked, có README, `vite.config.js`) | `git ls-files` có `website/README.md`; `ls website/` |
| `assets/` | Media nguồn của `website/` (xem mục 2.2) | SKILL.md hustlytasker-landing dòng 3, 11, 69 |
| `prisma/seed.ts` | Seed chính thức | `package.json:24-26` |
| `src/app/desk-preview/`, `src/app/velox-v4-preview/` | Dev-harness có gate chống lộ prod (xem mục 3) | `desk-preview/page.tsx:18`; `velox-v4-preview/page.tsx:21-22` |
| `design-system/agencymanager/MASTER.md` | Được `.claude/rules/ui-ux-standards.md` tham chiếu làm nguồn style | rule file mục 3 "Lấy thông báo từ MASTER.md" |
| `scripts/check-db.js` | Trùng tên với `check-db.js` root nhưng là bản trong scripts/ (2026-03-10); cả 2 đều one-off — bản root chắc chắn rác, bản scripts/ giữ tuỳ chính sách folder scripts | `git log`: root = 2026-03-13, scripts/ = 2026-03-10 |

---

## 6. Tóm tắt số liệu

- **~55 file rác đang TRACKED ở root** (check-*/debug-*/restore-*/dump txt/docx/pptx) — tất cả 0 hit import, commit cuối tập trung **01→04/2026** (4 tháng không ai đụng).
- **`api/` root = dead code ĐANG DEPLOY**: 2 Python function không ai gọi nhưng vẫn là endpoint sống trên Vercel (`vercel.json:3`), kéo theo `requirements.txt`. `scoring.py` fail-open nếu thiếu `CRON_SECRET` (`api/scoring.py:15`). Ưu tiên xử lý cao nhất mục này.
- **Cụm dead-code trong `src/`**: `DesktopTaskTable.tsx` (53KB, import-nhưng-không-render, vẫn vào bundle), cụm `TaskCreationManager`+2 form, 4 component lẻ, 3 lib file, 1 dependency chết (`@google/generative-ai`).
- **File nhạy cảm cần xoá local ngay**: `.tmp/video-report/chrome-*-history.sqlite` (44MB lịch sử trình duyệt), `.codex-studyplace-dev.log` (135MB), `all_users_output.txt`/`all_tasks_kcd.txt` (dump dữ liệu thật, đang tracked).
- **KHÔNG đụng**: `/welcome` (route sống), `messages/`, `scripts/test-*.ts`, `mcp-server/`, `electron/`, `website/`+`assets/`, `smart-qr.ts` (sống qua dynamic import).

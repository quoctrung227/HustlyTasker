# PROGRESS — System Audit HustlyTasker

> Checkpoint sau mỗi phase. Nếu phiên bị ngắt: đọc file này để biết đã xong gì, output ở đâu, còn gì dở dang.

| Phase | Trạng thái | Output | Ghi chú |
|---|---|---|---|
| 0 — Discovery | **XONG** (2026-08-02) | `00-discovery/system-inventory.md` + 12 file `00-discovery/parts/` (2.229 dòng) | 12 agent, mọi kết luận kèm file:line; flows chốt ở `parts/12-user-flows.md` (16 chính + 8 phụ) |
| 1 — Diagrams | **XONG** (2026-08-02) | `01-diagrams/` — 83 .mmd + 83 .png + `README.md` + `system-overview.pdf` (9 trang, 12 ảnh) | 24 flow × 3 (class/sequence/state) + 11 diagram hệ thống (architecture, deploy-topology, erd-full, 8 erd-domain). Pipeline PDF: HTML+base64 → Chrome headless --print-to-pdf; verify bằng PyMuPDF (tiếng Việt OK) |
| 2 — Migration | **XONG** (2026-08-02) | `02-migration/migration-analysis.md` + `parts/m1,m2,m4` + `samples/` (7 file) | Strangler + Spring Modulith 8 module; samples chạy được (Docker/compose/GH Actions/Caddy/vps-setup/frontend-changes) |
| 3 — States | **XONG** (2026-08-02) | `03-states/states.md` + `parts/s1,s2,s3` | s1 domain (Task 13 status + review 3 trục), s2 34 component, s3 buttons |
| 4 — Security | **XONG** (2026-08-02) | `04-security/security-architecture.md` + `parts/sec1-6` + `diagrams/` (auth-flow, trust-boundaries) | 6 agent; findings dedupe: **1 CRITICAL** (C1 leak DB creds git history — VERIFIED) + 5 High + 11 Medium + 13 Low; ma trận role×endpoint đầy đủ ở parts/sec2 |
| 5 — Accounts | **XONG** (2026-08-02) | `05-accounts/accounts.md` + `seed-test-accounts.ts` | Đã seed 8 account đủ mọi role vào Neon TEST branch (frosty-forest) — KHÔNG đụng prod; bcryptjs 10 rounds đúng hệ thống; guard cứng trong script |
| 6 — PDF tổng hợp | **XONG** (2026-08-02) | `HustlyTasker-System-Audit.pdf` (150 trang, 19MB, 85 ảnh nhúng) | Bìa + mục lục + executive summary (10 phát hiện) + Phase 0-5 + phụ lục (models/api/role×endpoint/dead-code/flows); verify PyMuPDF: 150 trang, 85 ảnh, tiếng Việt OK |

## ✅ HOÀN TẤT TOÀN BỘ 7 PHASE (2026-08-02)
Deliverable cuối: `docs/system-audit/HustlyTasker-System-Audit.pdf`. Tất cả checklist nghiệm thu đạt (xem cuối file).

## Bổ sung 2026-08-02 — diagram vector zoom-được (phản hồi: PNG trong PDF bị vỡ pixel)
- Xuất lại **83 diagram sang SVG vector** (`**/*.svg`) từ chính `.mmd`.
- **HTML Explorer** `01-diagrams/diagram-explorer.html` — 1 file offline, 83 diagram, pan/zoom như bản đồ, vector nét mọi mức zoom (đã verify Browser: ERD 67 model + ERD Task đọc được từng field khi phóng). Deliverable chính cho việc xem/trình chiếu.
- **FigJam board** https://www.figma.com/board/k0UeSomu03oaqyhNY2tz5z — 9 map native editable (8 ERD domain + kiến trúc), tự tách vùng không chồng. FigJam KHÔNG hỗ trợ class diagram → class + sequence/state theo flow xem trong Explorer, hoặc import SVG thủ công.
- Hướng dẫn: `01-diagrams/DIAGRAM-FORMATS.md`.
- Còn 1 board test "AUDIT test — connectivity check" trong Figma drafts (tạo lúc test kết nối) — user có thể xoá.

## Bổ sung 2 (2026-08-02) — làm rõ diagram + khôi phục dấu tiếng Việt
- Phản hồi: (1) một số vector nối chồng chéo khó đọc; (2) nhiều từ tiếng Việt bị mất dấu.
- Rà soát cả **83 `.mmd`** (workflow 15 agent): khôi phục **dấu tiếng Việt** (chỉ từ Việt, giữ nguyên thuật ngữ/định danh tiếng Anh, enum, path, tên hàm) + thêm **layout ELK** (đường nối góc vuông, ít chồng chéo) cho erDiagram/flowchart/classDiagram/stateDiagram-v2; sequenceDiagram giữ renderer mặc định.
- Re-render **83 SVG + 83 PNG**; dựng lại `diagram-explorer.html`, `system-overview.pdf`, `HustlyTasker-System-Audit.pdf`. Verify Browser: ELK gọn hơn hẳn; grep SVG xác nhận dấu ("công việc trung tâm", "giá khách - chỉ admin thấy", "VÙNG CLIENT"), 0 mojibake.
- Ngoại lệ kỹ thuật: `F15/state.mmd` + ELK render SVG OK nhưng lỗi đường PNG ở mọi scale → PNG của riêng file này render bằng dagre (vẫn đủ dấu); SVG (Explorer dùng) vẫn ELK.
- Figma board CHƯA cập nhật dấu (generate_diagram chỉ append, tránh làm loạn board cũ) — nếu cần bản Figma có dấu thì tạo board mới.

## Ghi chú kỹ thuật đã chốt khi trinh sát (2026-08-02)
- Repo = monorepo 1 app Next.js 16.1.6 App Router (`package.json:97`), kèm 2 sub-project: `mcp-server/` và `electron/` (desktop wrapper, `next.config.ts` output standalone khi `ELECTRON_DESKTOP=1`).
- DB: Prisma 5.22 + `@prisma/adapter-neon` (Neon Postgres). Schema 2056 dòng, 67 model. Migration bằng `prisma db push` (script `postinstall`, `package.json:10`).
- Deploy: Vercel (`vercel.json` — functions maxDuration + 7 cron). Có `RAILWAY_MIGRATION.md` (tham khảo lịch sử).
- API: 102 `route.ts` dưới `src/app/api/`; mutations chủ yếu qua ~59 file server actions (`src/actions/*`, `"use server"`).
- Auth: `jose` JWT + bcryptjs; guard tại `src/lib/auth-guard.ts`, `src/middleware.ts`.
- Services ngoài: Mux (webhook `api/webhooks/mux`), Cloudflare R2 (S3 SDK), Inngest, Resend, Upstash Redis/Ratelimit, LiveKit, Vercel Blob, Google Drive/Dropbox OAuth, Gemini/OpenAI translator, web-push.
- File rác ứng viên ở root: hàng chục `check-*.js`, `debug-*.js`, `*.docx/pptx`, `all_tasks_kcd.txt`… — Phase 0 sẽ chốt danh sách loại trừ.

## Checklist nghiệm thu (đã tự kiểm)
- [x] Mọi kết luận có trích dẫn `file:line` (parts + master docs).
- [x] Không phân tích trên file dead-code; danh sách loại trừ ở `00-discovery/parts/11-deadcode.md` + phụ lục PDF.
- [x] Mỗi user flow đủ 3 diagram (class/sequence/state) — 24 flow × 3 = 72; + architecture + deploy-topology + erd-full + 8 erd-domain = 11 hệ thống; tất cả render PNG (83/83).
- [x] Kết luận rõ deploy = Vercel + `prisma db push` postinstall, có bằng chứng (`vercel.json`, `package.json:10`, không `.github/workflows`).
- [x] Migration đủ: tách polyrepo + mapping Spring Boot + lộ trình strangler + samples chạy được (Dockerfile/compose/GH Actions/Caddy/vps-setup/frontend-changes).
- [x] Recommendation kiến trúc cụ thể: Spring Modulith 8 module (chính) + package-by-feature (dự phòng), có so sánh + lý do bám repo.
- [x] Security: ma trận role×endpoint đầy đủ (`parts/sec2`) + findings xếp hạng (1C/5H/11M/13L) + 2 security diagram.
- [x] Account đủ mọi role (8 account), không password plaintext trong DB (bcryptjs 10 rounds), seed vào TEST branch.
- [x] Đúng 1 file `HustlyTasker-System-Audit.pdf`, ảnh hiển thị đầy đủ (verify PyMuPDF: 150 trang / 85 ảnh).
- [x] `PROGRESS.md` phản ánh đúng trạng thái.

## Lưu ý pipeline (để tái tạo)
- Render Mermaid: `mmdc` (cài ở scratchpad `mmd/`) + Chrome local qua `puppeteer.json` (`executablePath` = Chrome), `-b white -s 2`.
- PDF: builder node `pdftools/build-*.js` (marked → HTML + base64 ảnh) → Chrome `--headless --print-to-pdf`; verify bằng PyMuPDF (py). Font Segoe UI render tiếng Việt OK.
- ⚠️ **VIỆC GẤP tách khỏi audit**: xoay khóa DB Neon `neondb_owner` (finding C1) — credential prod đọc được từ git history commit `ed46780`/`2c7e226`.

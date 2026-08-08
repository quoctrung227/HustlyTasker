# PHASE 2 — PHÂN TÍCH MIGRATION: Polyrepo + Java Spring Boot + Docker + VPS

> Tài liệu master. Chi tiết đầy đủ trong `parts/` và file mẫu chạy được trong `samples/`. Mọi kết luận đều bám số liệu thật của repo (Phase 0) kèm file:line.

## 1. Hiện trạng deploy (chi tiết: `parts/m1-hien-trang-va-polyrepo.md` §1)

- 1 app Next.js 16.1.6 full-stack duy nhất trên **Vercel** (`hustlytasker.xyz`), build webpack (`package.json:7`).
- **`prisma db push` chạy trong `postinstall` của MỌI build — kể cả preview nhánh chưa merge** (`package.json:10`): DDL áp thẳng vào Neon prod tại build-time. `schema.prisma` không còn là nguồn sự thật đầy đủ — DB có thêm 3 partial unique index, 5 CHECK, 1 trigger chỉ tồn tại trong `prisma/migrations/manual/*.sql` (drift từ 2026-05-07).
- **ZERO CI/CD trong repo** (không `.github/workflows`): merge main = deploy prod không điều kiện; 8 harness `test:*` (`package.json:15-22`) chạy tay, không gate build.
- Background: 7 Vercel Cron (`vercel.json:22-51`) + 4 Inngest function (`src/lib/review/inngest.ts`).

## 2. Tách polyrepo (chi tiết: `parts/m1-hien-trang-va-polyrepo.md` §2)

- 2 repo: **hustlytasker-api** (Spring Boot: 102 route + ~155 action-có-guard thành REST; Flyway baseline **từ pg_dump Neon thật** chứ không từ schema.prisma; 7 cron → `@Scheduled`; 4 Inngest → outbox + poller; `mcp-server` dời vào `tools/` đổi Prisma-direct → REST client) và **hustlytasker-web** (pages/components/hooks/i18n + electron + website; TS client sinh bởi orval).
- ~190 server action phân 5 nhóm: ~155 → REST có guard; ~28 public-by-design theo token (portal); 4 helper internal → service nội bộ KHÔNG expose HTTP; ~7 cookie/cache ở lại FE; ~9 stub bỏ.
- **API contract: OpenAPI code-first (springdoc) + orval codegen cho FE** — loại phương án shared npm package (BE Java không tiêu thụ TS types → 2 nguồn sự thật chắc chắn drift). Spec ~250-270 operations, publish artifact semver, versioning `/api/v1`.
- Auth khi tách: **HS256 → RS256** (BE giữ private key; FE middleware chỉ verify bằng public key — giữ auth-gate `src/middleware.ts:71-100`).
- Release: expand-contract 4 bước (DB expand → BE → FE → DB contract release sau); contract test 3 cổng nhẹ (openapi-diff gate + orval regenerate/tsc + Schemathesis smoke; không Pact vì chỉ 1 consumer).

## 3. Mapping sang Spring Boot (chi tiết: `parts/m2-spring-boot-mapping.md`)

Bảng mapping đầy đủ theo 8 domain (controller/service/repository cụ thể) + các quyết định then chốt:

| Hiện tại | Spring Boot | Ghi chú then chốt |
|---|---|---|
| Guard `verifyWorkspaceAccess` (`security.ts:38-165`) | Bean `WorkspaceAccessEvaluator` (@PreAuthorize + imperative) | `requireReviewAccess` PHẢI giữ imperative trong service (workspaceId re-derive từ row, 30+ điểm gọi) |
| JWT jose HS256 cookie `session` | Nimbus, **GIỮ NGUYÊN cookie contract** (cùng JWT_SECRET, claim lồng `{user:{...}}`, rolling refresh) | Cần test vector chéo Next↔Spring trong thời kỳ chuyển tiếp |
| zod | Bean Validation + 2 programmatic validator | |
| Prisma 67 model | JPA/Hibernate với **12 bẫy thật** | `Task.status` String tự do tiếng Việt — KHÔNG map enum; scalar-FK review — KHÔNG @ManyToOne; soft-delete 3 pattern — KHÔNG @SQLDelete; CAS `expectedRowVersion` — không @Version; BigInt AuditLog |
| 7 Vercel cron | `@Scheduled` + ShedLock | `check-deadline` ghi đè `Task.status` — port kèm whitelist |
| 4 Inngest | **JobRunr trên Postgres** | Repo đã có nửa hệ DB-queue sẵn (ledger WebhookEvent + janitor re-enqueue) |
| Webhook Mux HMAC | Filter raw-body + timingSafeEqual | |
| R2 S3 multipart | aws-sdk-java v2 presigned — **giữ nguyên flow client-side** | Chỉ 4 endpoint initiate/complete/abort/status đổi origin |
| PDF invoice (puppeteer) | openhtmltopdf hoặc sidecar Chromium | Diff bản render trước cutover |
| Zip streaming (archiver STORE) | StreamingResponseBody + commons-compress STORED | |

Rủi ro số 1: **~190 server action là RPC compile-time của Next với 208 lần `revalidatePath`/`revalidateTag` trong 38 file** — không có tương đương Spring; mọi action phải thành REST + FE refetch. Xác nhận KHÔNG có SSE/WebSocket server-side (polling + Supabase Realtime client-side — giữ nguyên). Đủ 18 điểm rủi ro kèm file:line trong parts/m2.

## 4. Docker + GitHub Actions + VPS (file chạy được: `samples/`)

| File | Nội dung |
|---|---|
| [`samples/Dockerfile`](samples/Dockerfile) | Multi-stage maven→JRE 21 alpine, non-root, HEALTHCHECK |
| [`samples/docker-compose.yml`](samples/docker-compose.yml) | api + postgres16 + caddy; Postgres bind 127.0.0.1 (né bẫy Docker-bypass-ufw); healthcheck chuỗi |
| [`samples/Caddyfile`](samples/Caddyfile) | Auto-SSL Let's Encrypt `api.hustlytasker.xyz`, timeout 300s cho download-zip |
| [`samples/deploy.yml`](samples/deploy.yml) | GH Actions: mvn verify → GHCR → SSH `docker compose pull && up -d`; concurrency group chống deploy chồng |
| [`samples/.env.example`](samples/.env.example) | Đúng danh sách service thật, loại env mồ côi; cảnh báo JWT_SECRET + REVIEW_COOKIE_SECRET phải GIỮ NGUYÊN giá trị Vercel (user không bị logout khi cutover) |
| [`samples/vps-setup.md`](samples/vps-setup.md) | Ubuntu 24.04: ufw/fail2ban/Docker, pg_dump -Fc 19:30 UTC + rclone lên R2 bucket riêng, restore-test, phân tích vì sao KHÔNG dùng watchtower |
| [`samples/frontend-changes.md`](samples/frontend-changes.md) | Danh sách chính xác FE phải đổi: NEXT_PUBLIC_API_BASE_URL, `rewrites()` beforeFiles (hiện next.config KHÔNG có rewrites — cảnh báo withBotId cũng inject rewrites), CORS origin thật, **2 phương án cookie: PA-1 proxy same-origin (khuyến nghị) vs PA-2 subdomain**, webhook/Inngest URL, 7 cron, 4 endpoint presign |

## 5. Lựa chọn kiến trúc (chi tiết: `parts/m4-lua-chon-kien-truc.md`)

Số liệu thật làm căn cứ: 67 model, ≈240–260 REST endpoint sau port, 8 domain, **team thực tế 1 dev** (git shortlog 2026: 2 danh tính đều là 1 chủ dự án).

- **Khuyến nghị chính: Spring Modulith — modular monolith 8 module** (core, task, crm-billing, payroll, schedule, collab, review, portal) + hexagonal cục bộ chỉ cho 6 client ngoài (Mux/Storage/Mail/Push/RateLimit/Translator). Căn cứ đặc thù repo: review module ĐÃ tách sẵn bằng scalar-FK (`schema.prisma:1607-1613`) — ranh giới module có thật duy nhất; payroll KHÔNG tách service được vì đếm `Task.status` trong cùng transaction (`SALARY_PENDING_STATUSES` đọc ở ≥10 điểm) — giải bằng named interface trong cùng JVM.
- Dự phòng: package-by-feature + ArchUnit (cùng cấu trúc package → chuyển qua lại được). Microservices bị LOẠI ngay từ tiêu chí team 1-2 dev.
- **Lộ trình: STRANGLER (không big-bang)** vì đủ 3 điều kiện có sẵn: chung DB Neon, JWT HS256 verify được từ Spring bằng JWT_SECRET chia sẻ, cookie host-only proxy được qua Next rewrites. Checklist 8 giai đoạn GĐ0→GĐ7 theo dependency thật; GĐ0 bắt buộc: **bỏ `prisma db push` khỏi postinstall + baseline Flyway từ DB thật**; task + payroll + cron check-deadline port CÙNG một giai đoạn; review port SAU CÙNG (Inngest/Mux/R2 nặng nhất nhưng không chặn ai).

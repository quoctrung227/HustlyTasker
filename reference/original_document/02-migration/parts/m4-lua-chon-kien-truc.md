# M4 — Lựa chọn kiến trúc backend Spring Boot (Phase 2 §5) + Chiến lược chuyển đổi (Phase 2 §3)

> Phạm vi: so sánh 5 phương án kiến trúc cho backend Spring Boot **của đúng hệ thống HustlyTasker này**, chốt 1 recommendation + 1 dự phòng + tiêu chí nâng cấp; sau đó so sánh strangler vs big-bang và checklist giai đoạn port theo dependency thật. Mọi số liệu lấy từ `docs/system-audit/00-discovery/` (đã verify file:line) + lệnh git chạy thật ngày 2026-08-02.

---

## 0. Số liệu đầu vào (dữ liệu thật, không ước lượng)

| Chỉ số | Giá trị | Nguồn |
|---|---|---|
| Model DB | **67 model + 15 enum** (schema 2.056 dòng) | `prisma/schema.prisma`, `parts/03-models.md` |
| API routes | **102 route.ts** = 39 core + 63 review (44 staff `/api/review/**` + 19 guest `/api/r/**`) | `parts/04-api-core.md`, `parts/05-api-review.md` |
| Server actions | **55 file / ~190 exported functions** | `parts/06-actions-a.md`, `parts/07-actions-b.md` |
| Bề mặt REST sau port | **≈ 240–260 endpoint** (102 route + ~190 action, trừ helper nội bộ, cộng tách vài action đa nhiệm) | suy từ 2 dòng trên |
| Nhóm domain | **8 nhóm**: core tenancy/auth (10 model), task & vận hành (8), CRM & finance (10), chất lượng/lịch (8), agency/invite/audit/tracking (8), wiki/học tập (4), task comments (3), review module (15) | `parts/03-models.md` §1.1–1.8 |
| Team size thật | `git shortlog -sn --since=2026-01-01 HEAD` → **Agency Admin 1.307 + phucmetlamroi 221** (branch `--all`: 1.425 + 224 + Vercel bot 1). Hai danh tính đều là **một chủ dự án** (git user local vs tài khoản GitHub), tốc độ ~200 commit/tháng nhờ AI agent. **Năng lực quy hoạch: 1 dev chủ lực, tối đa 2.** | lệnh chạy thật 2026-08-02 |
| Người dùng | 1 agency nội bộ (Admin + Staff-editor) + portal khách `/share/[token]` + guest reviewer `/r/[slug]` — **không có tenant ngoài trả tiền** tại thời điểm audit | `parts/12-user-flows.md` §0 |
| Hạ tầng chạy nền | 7 Vercel cron (`vercel.json:22-51`), 4 Inngest function (`src/lib/review/inngest.ts:751`), webhook Mux HMAC (`src/app/api/webhooks/mux/route.ts:23-48`) | `parts/10-jobs-webhooks.md` |
| Truy cập DB ngoài app | `mcp-server/` nói **thẳng DB** qua `@prisma/client` (`mcp-server/package.json:15`); `electron/` dùng driver `pg` thô | `parts/01-stack-deploy.md` §5 |

Ba **đặc thù kiến trúc** chi phối mọi lựa chọn dưới đây:

1. **Review module đã tách biệt sẵn bằng scalar-FK chủ đích**: 15 model (`prisma/schema.prisma:1640-2056`) tham chiếu Task/User/Client/Workspace bằng **string scalar, không FK constraint** (comment thiết kế tại `prisma/schema.prisma:1607-1613`), có event log riêng `ReviewActivity` không FK (`:1988-1989`), giao tiếp ngược về Task qua lớp task-sync + Inngest (`src/lib/review/inngest.ts:150-154,691-725`). Đây là **ranh giới module có thật duy nhất** trong repo — mọi phương án phải tận dụng, không phá.
2. **Payroll phụ thuộc trực tiếp `Task.status` (String tự do)**: `SALARY_PENDING_STATUSES` derive từ `TASK_STATUS_META` (`src/lib/task-statuses.ts:116`) và được đọc ở **≥10 điểm** trải cả action lẫn UI: `src/actions/bonus-actions.ts:178`, `src/app/[workspaceId]/admin/payroll/page.tsx:55,85`, `src/app/[workspaceId]/mc/tien/page.tsx:58`, `src/components/admin/PayrollCard.tsx:34`, `src/app/[workspaceId]/dashboard/salary/page.tsx:38`, `src/components/dashboard/Leaderboard.tsx:29`… Tiền lương editor = đếm task theo status trong **cùng một DB, cùng một transaction view**. Tách task và payroll thành 2 service = phải stream status ra ngoài (event-sourcing/CDC) mới giữ được số tiền đúng — chi phí đó không có người trả ở team 1 dev.
3. **2 shell admin song song dùng chung actions**: GĐ1 `/[workspaceId]/admin/*` (18 trang) và Mission Control `/[workspaceId]/mc/*` (21 trang) cùng mounted, cùng gọi 1 bộ action (`src/components/dashboard/DashboardActionWrapper.tsx:8` import cả `McAddTaskModal`; `mc/tep/page.tsx:11` bọc lại `TeamBrowser` thật) — hệ quả: **port theo action/domain, không port theo trang**; 1 action REST-hoá xong là cả 2 shell chuyển cùng lúc.

---

## 1. Tiêu chí đánh giá (rút từ đặc thù repo, không phải sách)

| # | Tiêu chí | Vì sao là tiêu chí của RIÊNG repo này |
|---|---|---|
| T1 | Giữ nguyên bất biến payroll-đếm-status trong 1 transaction | Đặc thù #2 — rủi ro số 1 được chính CLAUDE.md review-fixes ghi ("payroll đếm thiếu tiền editor") |
| T2 | Vận hành được bởi 1–2 dev (1 deployable, 1 DB, không thêm hạ tầng mới) | Team size thật ở §0 |
| T3 | Port dần được từng domain trong khi prod Vercel vẫn chạy | Prod `hustlytasker.xyz` đang phục vụ khách thật (`parts/01` §3.1) |
| T4 | Khớp ranh giới có thật: review scalar-FK là module; phần còn lại là khối liên kết chặt | Đặc thù #1 |
| T5 | Chịu được đặc sản của DB: `Task.status` String tự do, id không đồng nhất (Client/Project Int, AuditLog BigInt, còn lại uuid/cuid), constraint thật nằm ngoài schema.prisma (3 partial unique + 5 CHECK + 1 trigger trong `prisma/migrations/manual/`) | `parts/03-models.md` §3.1, §3.5, §4.2 |
| T6 | Không phá 2 bề mặt token công khai (portal `/share`, guest `/r`) vốn có chuỗi authz tự viết dày (uniform-404, gate chain, rate-limit Postgres) | `parts/09-roles-authz.md` §6 |

---

## 2. So sánh 5 phương án

### 2.1 Layered n-layer toàn cục (`controller/` – `service/` – `repository/` chia theo tầng kỹ thuật)

| Phù hợp với repo này | Không phù hợp với repo này |
|---|---|
| Đơn giản nhất để bắt đầu; mọi tutorial Spring đều dạy; 1 dev không phải nghĩ về ranh giới. | Với **67 model / ~250 endpoint / 8 domain**, một package `service/` phẳng sẽ chứa 60–80 class không ranh giới. Repo đã có bằng chứng sống về hậu quả của "không ranh giới": `src/actions/share-portal-actions.ts` phình quá **1.700 dòng** (~20 action từ approve tiền tới tạo task — `parts/12` F09), và `SALARY_PENDING_STATUSES` bị import thẳng vào cả page UI lẫn component (§0 đặc thù #2). Layered không có cơ chế nào ngăn `PayrollService` khỏi bị gọi từ 15 chỗ, cũng không ngăn ai đó query `TaskRepository` trực tiếp để đếm lương — tức là **tái tạo đúng vấn đề hiện tại bằng ngôn ngữ khác**. |
| | Layered cũng vứt bỏ tài sản quý nhất: ranh giới review module scalar-FK sẵn có (đặc thù #1) sẽ tan vào `repository/` chung. |

**Kết luận: LOẠI.** Không tận dụng được gì của repo, tái tạo nợ cũ.

### 2.2 Package-by-feature (chia package theo domain, không enforcement)

| Phù hợp với repo này | Không phù hợp với repo này |
|---|---|
| **Map gần 1-1 với cấu trúc hiện tại**: 55 file action đã chia theo feature (`payroll-actions.ts`, `crm-actions.ts`, `invoice-actions.ts`, `claim-actions.ts`, `share-portal-actions.ts`…) và `src/lib/review/` đã là một package feature hoàn chỉnh — dịch cấu trúc gần như cơ học, giảm rủi ro dịch sai. | **Không có enforcement** — ranh giới chỉ là quy ước. Repo này có tiền sử vi phạm quy ước ngay khi thiếu gate (UI đọc thẳng hằng lương; 2 hệ email template song song cùng sống — `parts/10` §5.2). Với 1 dev + AI agent sinh code tốc độ ~200 commit/tháng (§0), quy ước không tự bảo vệ được — cần máy kiểm tra. |
| Zero dependency thêm; 1 deployable; port từng feature được (T2, T3 đạt). | Không có khái niệm "module API公开 vs internal" → cross-feature import sẽ mọc lại trong 6 tháng. |

**Kết luận: KHÔNG chọn làm chính, nhưng là NỀN của phương án dự phòng** (§3.2) — chỉ cần cộng thêm ArchUnit test là vá được điểm yếu chính.

### 2.3 Clean / Hexagonal architecture (ports & adapters toàn hệ thống)

| Phù hợp với repo này | Không phù hợp với repo này |
|---|---|
| Cô lập được các dịch vụ ngoài — repo có thật 8 dịch vụ: Mux (REST tự viết + JWT RS256 tự ký — `src/lib/review/mux.ts:1-8`, `mux-jwt.ts:1-9`), R2 (`src/lib/review/r2.ts`), Resend, Upstash, Vercel Blob, Supabase, web-push, OpenAI (`parts/01` §6). Interface hoá các client này là **cần thiết** để test và để thoát Vercel. | Áp **toàn hệ thống** thì mỗi flow cần usecase + port + adapter + 2 lớp DTO. Nhân với ~250 endpoint và 67 entity = hàng nghìn file ceremony cho **1 dev**. Trong khi đó phần lớn code của repo là CRUD + authz-guard + status-write (nhìn bảng action `parts/06/07`: đa số là verify → prisma query → revalidate) — không có tầng domain logic thuần đủ dày để hưởng lợi từ việc cô lập domain. Chỗ phức tạp thật sự (chuỗi share-auth `src/lib/review/share-auth.ts`, state machine review, pipeline Inngest idempotent) **đã tự cô lập thành lib module** — port nguyên khối là đủ, không cần đập ra thành port/adapter. |
| | Hexagonal cũng không giải quyết được 2 vấn đề riêng của repo: bất biến payroll (T1 — nằm ở DB/transaction, không phải ở port) và thứ tự port dần (T3). |

**Kết luận: LOẠI ở quy mô toàn hệ thống; GIỮ ở quy mô "hexagonal cục bộ"** — chỉ interface hoá đúng 6 client ngoài: `MuxClient`, `ObjectStorage` (R2/Blob/Supabase — repo đã có seam chọn backend theo env tại `src/lib/storage.ts:23-31`, bê nguyên ý tưởng), `MailSender` (Resend), `PushSender`, `RateLimiter` (Upstash), `Translator` (OpenAI). Đây là phần rẻ nhất của hexagonal và là phần duy nhất repo cần.

### 2.4 Modular monolith — Spring Modulith ⭐ (khuyến nghị chính)

| Phù hợp với repo này | Không phù hợp / rủi ro |
|---|---|
| **Khớp chính xác trạng thái đã có**: review module là modular-monolith-trong-thực-tế rồi — scalar-FK chủ đích, event log riêng, giao tiếp về Task qua lớp sync hẹp (đặc thù #1). Modulith chỉ **hợp thức hoá bằng máy** cái ranh giới đang được giữ bằng tay. | Modulith đòi kỷ luật package (`module/internal/` không được import chéo). Một số quan hệ hiện tại là **2 chiều**: review→task (auto-flip status khi Mux READY — `inngest.ts:150-154`) và task→review (revoke share khi re-open). Phải quy ước 1 chiều compile-time (review phụ thuộc task-API) + chiều ngược đi bằng **application event** — có công thiết kế ban đầu. |
| **T1 đạt mà không cần event-sourcing**: payroll và task là 2 module trong **cùng JVM, cùng DataSource, cùng transaction**. Payroll đếm lương qua named interface `TaskStatusQuery` do module task export — vẫn 1 câu SQL `WHERE status IN (...)` như `bonus-actions.ts:178` hiện tại, nhưng chỉ 1 nơi được phép gọi thay vì 10+ nơi. | `ApplicationModuleTest` + event publication registry là khái niệm mới với người chưa dùng Modulith — learning curve ~vài ngày cho 1 dev. |
| **T2 đạt**: 1 deployable, 1 DB — vận hành y như hiện tại (1 app Next trên Vercel → 1 app Spring trên VPS). Không service discovery, không message broker (Modulith event dùng chính Postgres làm event publication log — hợp với repo vốn đã dùng Postgres làm cả rate-limit bucket `RateLimitBucket` và webhook ledger `WebhookEvent`). | |
| **Thay thế tự nhiên cho các fire-and-forget hiện tại**: `createNotificationInternal` đang được mọi action gọi trực tiếp + web-push + email fire-and-forget (`parts/10` §4-5). Trong Modulith: module phát `TaskAssigned`/`ReviewDecisionRecorded` event, module `collab` lắng nghe và lo notification/email/push — cắt đứt việc mọi domain phải biết về Resend/VAPID. Điểm này còn sửa được luôn bug tiềm ẩn "2 hệ email song song double-send" (`parts/10` §7.4) vì chỉ còn 1 listener. | |
| **Verify được bằng test**: `ApplicationModules.verify()` chạy trong CI chặn import chéo — chính là cái mà codebase TS hiện tại thiếu (không gì ngăn UI import hằng payroll). | |

**Đề xuất cắt module (8 module, map từ 8 nhóm model §0):**

| Module | Model chính (từ `parts/03`) | Named interface export | Ghi chú |
|---|---|---|---|
| `core` | User, Profile, Workspace, WorkspaceMember, ProfileAccess(+Request), WorkspaceInvitation, token auth (4 model), AuditLog | `AuthGuard` (dịch từ `verifyWorkspaceAccess`/`verifyProfileAdminAccess` — `src/lib/security.ts:38-191`), `AuditWriter` | Tầng mọi module phụ thuộc; **không phụ thuộc ngược ai** |
| `task` | Task, TaskRawFootage, TagCategory/TaskTag, PriceTemplate, PricingRule, IntegrationToken | `TaskStatusQuery` (hằng `TASK_STATUS_META` port sang đây — 1 nguồn sự thật), `TaskCommand` | Marketplace (claim/return) nằm trong đây — cùng ghi `Task` |
| `crm-billing` | Client (cây), Project, Invoice(+Item), Payment, BillingProfile, ClientShareLink, ClientTaskRequest | `ClientQuery`, `InvoiceQuery` | Payment cố ý không FK (`prisma/schema.prisma:799-804`) — giữ nguyên, enforce scope ở service như hiện tại |
| `payroll` | Payroll, MonthlyBonus, PayrollLock, BonusConfig, PerformanceMetric, MonthlyRank, ErrorLog, ErrorDictionary | — (consumer thuần) | Chỉ được đọc task qua `TaskStatusQuery` (T1); ErrorDictionary là bảng global không tenant (`schema.prisma:1014`) — giữ nguyên hành vi |
| `schedule` | ScheduleRule, ScheduleException, DailyAvailability | `AvailabilityQuery` | Module "lá" — ứng viên port đầu tiên (§5) |
| `collab` | TaskComment(+ReadState/Reaction), Notification, NotificationPreference, PushSubscription, Contact, WikiPage, Attachment, StudyPlaceProgress | `Notifier` (listener event) | Nơi duy nhất biết Resend/VAPID/Supabase-realtime |
| `review` | 15 model review (`schema.prisma:1640-2056`) | `ReviewTaskSync` events | Giữ nguyên scalar-reference sang task — trong JPA cũng **không khai báo relation** sang Task, đúng như thiết kế P0 |
| `portal` | (không model riêng) | — | Facade cho `/share` + `/r`: dịch `share-link-auth.ts` + `share-auth.ts` (chuỗi uniform-404, gate chain, rate-limit) — gom 1 chỗ vì đây là bề mặt authz nguy hiểm nhất (F09, ~20 action/1 token) |

### 2.5 Microservices

| Phù hợp với repo này | Không phù hợp với repo này |
|---|---|
| Duy nhất 1 ứng viên có thật: **review module** — đã scalar-FK, đã async (Inngest + webhook), đã có event log riêng, tải I/O khác hẳn phần còn lại (multipart R2, stream ffmpeg cần `maxDuration 800` — `src/app/api/inngest/route.ts:15`). | **Mọi thứ khác chống lại**: (a) team 1–2 dev không vận hành nổi N deploy + N pipeline; (b) T1 vỡ ngay — tách payroll khỏi task đòi status event stream + exactly-once consumer, tức event-sourcing/CDC cho một hệ **1 agency nội bộ dùng**; (c) per-service DB là ảo tưởng ở đây: `mcp-server` và `electron` đang nói **thẳng vào DB chung** (`parts/01` §5) — chia DB là gãy 2 client đó; (d) chi phí hạ tầng (broker, discovery, tracing) phục vụ đúng... 1 khách hàng nội bộ + portal token. |

**Kết luận: LOẠI cho hiện tại.** Review module là "microservice tương lai" duy nhất và chỉ khi chạm trigger ở §3.3.

---

## 3. KẾT LUẬN

### 3.1 Khuyến nghị chính

> **Spring Modulith modular monolith** — 8 module như bảng §2.4, bên trong mỗi module tổ chức package-by-feature phẳng (không chia tầng kỹ thuật sâu), **hexagonal cục bộ** chỉ cho 6 client ngoài (Mux/Storage/Mail/Push/RateLimit/Translator), JPA map nguyên bảng hiện có (không đổi schema), Postgres-backed Modulith events thay cho các fire-and-forget notify.

Vì sao đây không phải kết luận generic: nó ăn khớp từng đặc thù — review scalar-FK trở thành module đúng nghĩa mà **không thêm FK constraint nào** (giữ luật additive-only của repo), payroll giữ nguyên câu đếm `status IN (SALARY_PENDING)` trong 1 transaction nhưng bị ép đi qua 1 named interface duy nhất (sửa tận gốc việc 10+ điểm đọc rải rác), và ~190 action REST-hoá được theo domain nên 2 shell admin chuyển cùng nhịp.

### 3.2 Phương án dự phòng

> **Package-by-feature thuần + ArchUnit rules** (không dependency Modulith): cùng cấu trúc package 8 module y hệt §2.4, ranh giới enforce bằng ~10 ArchUnit test (`noClasses().that().resideOutsideOfPackage("..payroll..").should().accessClassesThat().resideInPackage("..task.internal..")`), event nội bộ dùng thẳng `ApplicationEventPublisher` của Spring (mất event publication registry — chấp nhận vì webhook ledger `WebhookEvent` + janitor re-enqueue đã là cơ chế chống mất event của riêng review, port nguyên).

Dùng khi nào: nếu sau 2 tuần pilot (GĐ0–GĐ1 ở §5) thấy Modulith gây ma sát (verify fail liên tục vì các quan hệ 2 chiều task↔review, hoặc dev không theo kịp convention). **Chuyển qua lại được vì cùng cấu trúc package** — chỉ thêm/bớt dependency + test, không đảo code.

### 3.3 Tiêu chí nâng cấp (khi nào rời modular monolith)

| Trigger đo được | Hành động | Vì sao ngưỡng này |
|---|---|---|
| Encode/upload pipeline nghẽn app chính: p95 upload-complete → Mux READY vượt xa hiện tại, hoặc job nền chiếm >50% CPU app | Tách **duy nhất `review`** ra process riêng (vẫn chung DB — scalar-FK cho phép điều này mà không đổi schema) | Review là module duy nhất có ranh giới dữ liệu sẵn (đặc thù #1) |
| Có tenant ngoài trả tiền (SaaS thật, theo `docs/pricing/`) và cần SLA riêng cho portal khách | Tách `portal` (read-mostly) thành app riêng scale ngang | Portal là bề mặt public token, stateless-friendly |
| Team ≥ 3 dev backend làm song song và tranh chấp release | Cân nhắc tách theo module đã có ranh giới verify sẵn | Trước ngưỡng đó, chi phí phối hợp < chi phí hạ tầng |
| Cần audit tài chính độc lập / payroll đa nguồn dữ liệu | Lúc đó mới bàn event-sourcing cho `Task.status` — kèm CDC (Debezium) chứ không tự chế | Đây là điều kiện DUY NHẤT khiến "payroll đọc status trực tiếp" phải chết; hiện không tồn tại |

---

## 4. Strangler vs Big-bang cho bối cảnh này

Bối cảnh ràng buộc (thật, từ inventory): prod `hustlytasker.xyz` đang chạy trên Vercel phục vụ khách thật; 1–2 dev; DB Neon Postgres; session là **JWT HS256 (jose) trong cookie httpOnly `session`** không set `Domain` → **host-only cookie** (`src/lib/auth.ts:23-29`, `src/lib/jwt.ts:2-4`); revoke qua `sessionVersion` so DB tại DAL (`src/lib/security.ts:257-269`); schema được `prisma db push` đè mỗi build (`package.json:10`) và folder migrations đã drift từ 2026-05-07 (`parts/03` §4).

| Tiêu chí | Big-bang (viết xong Spring rồi cutover 1 lần) | Strangler (port dần, 2 backend chạy song song trên cùng DB) |
|---|---|---|
| Khối lượng phải xong trước khi có giá trị | ~250 endpoint + 67 entity + dịch nguyên chuỗi authz tự viết (uniform-404, gate chain, impersonation 5 lớp) + 4 Inngest function + 7 cron — **tất cả** trước release đầu | 1 domain lá (~10 endpoint) là release được |
| Rủi ro regression | Payroll (tiền thật), portal khách, guest decision — không có test server tự động nào ngoài script harness (`scripts/test-*.ts`, `package.json:15-22`); big-bang = đặt cược toàn bộ vào 1 đêm cutover | Mỗi giai đoạn chỉ 1 domain đổi đường đi; rollback = trỏ route ngược lại |
| Khớp năng lực 1–2 dev | 4–6 tháng không ship gì cho sản phẩm đang sống (trong khi repo này ship ~200 commit/tháng — nghiệp vụ sẽ không đứng yên chờ) | Port xen kẽ với vận hành |
| Điều kiện kỹ thuật để chạy song song | — | **Có đủ cả 3**: (a) cùng DB Neon — 2 backend cùng connection string (`src/lib/env.ts:19`), bất biến payroll giữ nguyên vì vẫn 1 DB; (b) session verify được từ Spring: HS256 + secret chia sẻ `JWT_SECRET` → Spring Security đọc cùng cookie, decode cùng payload `{user:{id, sessionVersion,...}}`, re-check `sessionVersion` so DB đúng như DAL hiện tại; (c) cookie host-only → chỉ cần **reverse-proxy cùng host**: Next.js `rewrites()` forward `/api/v2/**` sang Spring trên VPS — Vercel làm được ngay, không đổi domain, không đổi cookie |
| Điểm yếu riêng của strangler Ở REPO NÀY | — | ~190 server action **không phải URL REST** (POST về chính page với header `Next-Action`) → không proxy per-path được. Phải đổi **call-site**: mỗi action port xong thì các component gọi nó chuyển sang `fetch('/api/v2/...')`. Nhờ đặc thù #3 (2 shell dùng chung action), mỗi lần đổi call-site là cả 2 shell chuyển — không phải làm 2 lần |

> **CHỌN: STRANGLER.** Big-bang chỉ hợp khi có test coverage dày và team đủ đông để đóng băng nghiệp vụ — repo này không có cả hai. Điều kiện tiên quyết của strangler (chung DB + chung session + chung host) đều đã thoả sẵn nhờ chính thiết kế hiện tại (JWT HS256 chia sẻ được, cookie host-only proxy được, DB duy nhất).

**Quyết định DB đi kèm:** GIỮ Neon nguyên trạng suốt thời kỳ chuyển tiếp. Không gộp "đổi runtime" với "đổi DB host" (Neon → Postgres VPS) vào cùng một cuộc di cư — đổi DB là việc 1 buổi (`pg_dump`/logical replication) làm **sau** khi Spring đã là backend duy nhất; làm trước hoặc làm giữa chừng là nhân đôi biến số khi debug lệch dữ liệu. Lý do phụ: `mcp-server` và `electron` trỏ thẳng DB — đổi host DB là phải cập nhật 2 client đó cùng lúc, để sau cùng cho gọn.

---

## 5. Checklist giai đoạn (thứ tự port theo dependency THẬT)

Nguyên tắc thứ tự: (1) cái mọi domain phụ thuộc đi trước (guard/authz); (2) domain "lá" đi sớm để chứng minh pipeline; (3) **task + payroll + cron deadline đi CÙNG một giai đoạn** (bất biến T1 + cron `check-deadline` là process duy nhất ghi đè `Task.status` — `src/app/api/cron/check-deadline/route.ts:156-159` — không được để 2 codebase cùng định nghĩa hằng lương/whitelist quá 1 giai đoạn); (4) **review đi SAU CÙNG** vì gánh nặng hạ tầng (Inngest/Mux/R2) lớn nhất trong khi ranh giới scalar-FK khiến nó không chặn ai.

| GĐ | Nội dung | Việc cụ thể | Điều kiện xong (gate) |
|---|---|---|---|
| **0. Nền** | Skeleton + đóng băng schema | Bỏ `prisma db push` khỏi `postinstall` (`package.json:10`) → schema freeze; **baseline Flyway từ DB Neon thật** (KHÔNG generate từ `schema.prisma` — nó thiếu 3 partial unique index, 5 CHECK, 1 trigger nằm trong `prisma/migrations/manual/*.sql`, `parts/03` §4.2); sinh JPA entity từ information_schema, giữ đúng bẫy kiểu id (§0-T5) và `Task.status` là `String`; dựng VPS + reverse-proxy `/api/v2/**` qua Next `rewrites()`; CI chạy `ApplicationModules.verify()` | Spring đọc được 1 bảng thật qua proxy trên prod; snapshot-test `SALARY_PENDING_STATUSES` port sang JUnit và **xanh với đúng bộ giá trị hiện tại** (`scripts/test-status-meta-snapshot.ts` là mẫu) |
| **1. Auth-verify (KHÔNG phải login)** | Spring verify session hiện có | Filter đọc cookie `session`, HS256 với `JWT_SECRET` chia sẻ, decode payload, re-check `sessionVersion` + LOCKED so DB (dịch `verifyWorkspaceAccess` chain — `src/lib/security.ts:38-165` — và `verifyProfileAdminAccess:180-191` thành `AuthGuard`); login/signup/OTP/Google **ở lại Next** đến GĐ7 | Endpoint thử `/api/v2/me` trả đúng user cho session đang login ở Next; impersonation cookie (`admin_session`, TTL 2h) vẫn hoạt động xuyên qua |
| **2. Domain lá** | schedule + wiki/study + tags | Port `schedule` (P1), WikiPage/StudyPlace/Tag — ít quan hệ, chỉ cần AuthGuard + workspace scope; chuyển call-site các action tương ứng (`availability-actions.ts`, `schedule-actions.ts`, `study-place-actions.ts`, `tag-actions.ts`) sang fetch | 2 shell admin + dashboard staff dùng lịch/wiki bình thường; đo độ trễ qua proxy chấp nhận được |
| **3. CRM + Finance** | Client tree, Invoice, Payment | Port `crm-billing`: cây client + merge (`crm-actions.ts:461`), invoice PDF (cần Chromium trên VPS — seam `nixpacks.toml` đã ghi cách cài), payment ledger; **chưa** đụng ClientShareLink resolve (ở GĐ5) | Số dư invoice/payment đối chiếu khớp trước/sau bằng script probe read-only |
| **4. Task + Payroll + Marketplace + cron (MỘT giai đoạn, không tách)** | Trục xương sống | Port `task` (create/assign/status/velox-batch/claim) + `payroll` (đếm qua `TaskStatusQuery`) + `TASK_STATUS_META` sang Java (xoá bản TS khi xong — kể cả bản copy `mcp-server/src/services/statuses.ts` phải trỏ về nguồn mới); chuyển 2 cron `check-deadline` + `send-digest` từ Vercel cron sang Spring `@Scheduled` **cùng commit** với port task để chỉ 1 process ghi `'Quá hạn'` | Regression K1-K9 của repo (salary snapshot, cron, task flow) pass; đối chiếu bảng lương 1 tháng cũ ra số **giống hệt** bản Next |
| **5. Portal + Collab** | Bề mặt token + comment/notification | Port `portal` (`share-link-auth.ts` → resolver Java: SHA-256 hash-at-rest, uniform-404, rate-limit 2 tầng) + ~20 action `share-portal-actions.ts` + `collab` (TaskComment 2 visibility, Notification qua Modulith event, web-push); cần GĐ3+4 xong vì portal đọc Task/Invoice/Client | Khách mở link `/share` cũ (token không đổi — hash trong DB) hoạt động nguyên; email notify không double-send (chỉ còn 1 hệ template) |
| **6. Review module (SAU CÙNG)** | Nặng hạ tầng nhất | Port 63 route review + upload engine server-side (S3 multipart R2 presigned — SDK Java AWS tương đương), Mux REST + JWT RS256 (tự viết như TS — không SDK), webhook HMAC verify; **thay Inngest** bằng Spring Scheduler + bảng `WebhookEvent` làm outbox (pattern ledger + janitor re-enqueue + reconcile đã idempotent sẵn — `parts/10` §7.6 — dịch nguyên, không sáng tạo lại); 4 cron dọn dẹp còn lại chuyển nốt | Upload → Mux READY → auto-flip task status chạy đúng chuỗi; janitor 5 sweep chạy đêm; guest `/r` decision đồng bộ về task như cũ |
| **7. Cutover** | Login + gỡ giàn giáo | Port login/signup/OTP/Google OAuth + phát hành cookie từ Spring (giữ nguyên tên `session`, HS256, payload — session đang sống **không bị logout**); Next.js rút về pure-frontend (hoặc giữ SSR gọi Spring); quyết định số phận `mcp-server` (chuyển sang gọi REST thay vì Prisma thẳng) + `electron` (freeze hay build lại); sau khi ổn định N tuần → di cư Neon → Postgres VPS nếu vẫn muốn (§4) | Vercel chỉ còn serve static/SSR; toàn bộ 7 cron + webhook trỏ VPS; tắt `postinstall` prisma hoàn toàn |

**Việc cấm làm trong suốt strangler** (rút từ chính rủi ro repo): không sửa schema từ phía Spring khi Next còn ghi (Flyway chỉ được thêm bảng/cột mới — đúng luật additive-only sẵn có của repo); không để 2 process cùng chạy cron ghi status (mỗi cron thuộc đúng 1 bên tại mọi thời điểm — bảng GĐ4/6); không port "theo trang" (đặc thù #3 — port theo action/domain).

---

*File này thuộc Phase 2 audit. Nguồn đối chiếu: `docs/system-audit/00-discovery/system-inventory.md` + `parts/01,03,04,05,09,10,12`. Số committer lấy từ `git shortlog -sn --since=2026-01-01` chạy ngày 2026-08-02.*

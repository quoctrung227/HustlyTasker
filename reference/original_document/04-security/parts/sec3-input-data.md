# §3 — Input Validation & Data Layer (Phase 4 Security)

> Phạm vi: (a) cơ chế validate input, chỗ nào không validate; (b) SQL injection quanh `$queryRaw`/`$executeRaw`; (c) mass assignment; (d) IDOR/BOLA; (e) tenant isolation.
> Nguyên tắc: mọi kết luận đã MỞ CODE THẬT xác minh, kèm `file:line`. Không sửa code. Ngày audit: 2026-08-02 (worktree `cranky-austin`).
> Đối chiếu audit cũ: các finding cũ được verify lại trên code hiện tại; ghi rõ "đã fix" hoặc "còn sống".

---

## 0. Tóm tắt điều hành

| Hạng mục | Kết luận | Mức |
|---|---|---|
| SQL injection | **AN TOÀN** — 21 chỗ `$queryRaw`/`$executeRaw` đều parametrized qua tagged-template / `Prisma.sql` / `Prisma.join`; **0 chỗ `$queryRawUnsafe`/`$executeRawUnsafe`**; không có nội suy chuỗi user vào SQL text | — |
| Tenant isolation (data layer) | **VỮNG** cho call-site dùng `getWorkspacePrisma` — inject `workspaceId` vào `where`/`data` mọi model không-bypass; fail-closed (throw) cho `Client` khi thiếu `profileId` | — |
| IDOR review-module | **VỮNG** — service re-derive `workspaceId` TỪ ROW rồi `requireReviewAccess` (client không tự khai workspaceId) | — |
| Validation | **KHÔNG NHẤT QUÁN** — zod chỉ ở review-routes + 1 action; ~55 action classic dùng validate thủ công; `updateTask` dùng denylist | Low |
| Mass assignment | **1 chỗ thật**: `updateTask` denylist bỏ sót `clientReview` (+4 field) | Medium |
| Broken access control (ghi) | `updateFrameAccount` bất đối xứng guard; 3 hàm `notification *Internal` public không auth | High/Medium |

Findings: **S3-01…S3-07** (1 High, 1 Medium-High, 1 Medium, 4 Low/Info).

---

## (a) Input validation — validate bằng gì, chỗ nào KHÔNG validate

### Cơ chế đang dùng THẬT

| Lớp | Cơ chế validate | Bằng chứng |
|---|---|---|
| Review-module routes (`/api/review/**`, `/api/r/**`) | **zod** `z.object(...).parse/safeParse` trong route trước khi gọi service | vd `src/app/api/review/uploads/initiate/route.ts`, `folders/route.ts`, `shares/route.ts`, `items/move|delete|copy/route.ts`, `r/[slug]/unlock/route.ts`, `assets/[id]/status/route.ts` (grep `z.object` = 39 file) |
| Velox v4 (action) | **zod schema** velox-4.0 + hookgraph-1 (cap 500 block/2000 edge; URL chống `javascript:`) | `src/actions/raw-footage-actions.ts:18` (import `zod`) — **file action DUY NHẤT dùng zod** |
| ~55 action classic (`src/actions/*`) | **Validate thủ công**: `typeof`/`trim()`/whitelist/`safeNumber`/regex hex/enum-list — KHÔNG schema | vd `createTask` `src/actions/admin-actions.ts:92-136`; `updateBonusConfig` `src/actions/bonus-config-actions.ts:88-99`; status whitelist `src/actions/task-actions.ts` |
| Env | zod | `src/lib/env.ts:3` |

### Chỗ nhận input raw / validate yếu (không phải lỗ hổng tự thân, nhưng là nợ nhất quán)

| # | Vị trí | Quan sát |
|---|---|---|
| 1 | `createTask` `src/actions/admin-actions.ts:85-136` | Đọc `formData.get(...) as string` cho ~15 field text (`references`, `resources`, `notes_vi`, `frameUsername`, `framePassword`…), lưu thẳng, **không cap độ dài, không sanitize**. `title` có `trim()`+required (`:92-95`), số dùng `safeNumber` chặn NaN (`:99-103`) → payload create là **allowlist named-field** nên KHÔNG mass-assignment. Admin-only → rủi ro thấp. |
| 2 | `updateTask` `src/actions/task-management-actions.ts:35` | Nhận `data: any`, KHÔNG schema — chỉ denylist (xem mục (c) S3-01). |
| 3 | `bulkUpdateStatus` (drag-drop) `src/actions/bulk-task-actions.ts:788` | Chỉ validate status hợp lệ, **KHÔNG check FSM** (khác `bulkUpdateTaskStatus:483` có FSM) — cùng chức năng 2 mức chặt. |

**Kết luận (a):** Validation nghiêng về thủ công ngoài review-module; không có lỗ hổng injection do thiếu validate (Prisma chặn SQLi, xem (b)), nhưng thiếu schema/allowlist ở `updateTask` là gốc của S3-01.

---

## (b) SQL injection — `$queryRaw` / `$executeRaw`

**KẾT LUẬN: AN TOÀN. Không tìm thấy SQL injection.**

- Grep `$queryRawUnsafe` / `$executeRawUnsafe` toàn `src/` = **0 kết quả**.
- 21 chỗ raw SQL đều dùng **tagged-template** (`prisma.$queryRaw\`…${x}…\``) hoặc **`Prisma.sql`/`Prisma.join`** → Prisma bind tham số, không ghép chuỗi.

| Nhóm | Vị trí | Dạng | An toàn vì |
|---|---|---|---|
| Advisory lock | `bonus-actions.ts:336`, `invoice-actions.ts:615`, `crm-actions.ts:107`, `share-portal-actions.ts:1500`, `folders.ts:717`, `guest-subscribe.ts:188`, `shares.ts:317`, `versions.ts:153,222`, `upload-service.ts:696` | tagged-template `pg_advisory_xact_lock(hashtextextended(${key},0))` | `${key}` là bound param |
| `FOR UPDATE` row-lock | `member-actions.ts:1217,1291` | tagged-template, `${targetUserId}`/`${profileId}` bound | bound param |
| Update path/bytes (materialized path) | `folders.ts:118-120,766-768,1071-1073,1543-1545` | `Prisma.sql\`… ${newPrefix} … ${Prisma.join(ids)} …\`` | `Prisma.sql`+`Prisma.join`; `substring(... from ${n})` với `n` là số |
| Aggregate/mosaic (report) | `folders.ts:518-531,553-564` | tagged-template, `IN (${Prisma.join(aggIds)})` | id là cuid từ DB, `Prisma.join` bind từng phần tử |
| Rate-limit upsert | `rate-limit-db.ts:25-32` | tagged-template, `${key}`,`${cutoff}` bound | bound param |
| Touch updatedAt | `comments.ts:530,539` | tagged-template `${commentId}` | bound param |

> Không có SQL nào nội suy tên bảng/cột từ input người dùng. Không có nhánh string-concat trước khi đưa vào `$queryRaw`.

---

## (c) Mass assignment

### S3-01 (Medium) — `updateTask` denylist bỏ sót `clientReview` (+ `clientFeedback`, `clientReviewedAt`, `clientUserId`, `createdAt`)

`src/actions/task-management-actions.ts:35-107`. Đây là action `updateTask(id, data: any, workspaceId)` — nhận **object tuỳ ý** rồi `workspacePrisma.task.update({ where:{id}, data })` (`:107`). Phòng thủ là **DENYLIST** (`delete data.X`), không phải allowlist/schema:

- Với **mọi caller**: chỉ xoá `id`/`workspaceId`/`profileId` (`:52-54`).
- Với **non-admin** (assignee sở hữu task, `:59`): xoá thêm `wageVND,value,jobPriceUSD,profitVND,exchangeRate,invoiceStatus,invoiceId,status,assignedById,clientId,projectId,isArchived,claimSource,claimedAt,version,deadline,assigneeId,assignedAgencyId,isPenalized` (`:65-90`).

Đối chiếu model `Task` (`prisma/schema.prisma:331-421`), các field **KHÔNG bị strip** mà non-admin GHI ĐƯỢC trên task của chính mình:
- **`clientReview`** (`schema:385`) ← nghiêm trọng nhất
- `clientFeedback` (`:386`), `clientReviewedAt` (`:387`), `clientUserId` (`:374`), `createdAt` (`:344`)

**Tác động của `clientReview` self-write** (verify tại `src/lib/portal-derive.ts`):
1. `deriveClientStatus` trả **"Completed"** khi `clientReview==='APPROVED'` (`portal-derive.ts:42`) → portal khách hiển thị task đã được khách duyệt (giả mạo sign-off của khách).
2. `isClientFacingPhase(status, clientReview)` = `clientReview != null || /khách/` (`portal-derive.ts:77-78`) → chỉ cần set `clientReview` khác null là **qua cổng R5/P4** vốn được ghi chú là BLOCKER ("an unreviewed new cut is never surfaced as a live review link", `portal-derive.ts:70-79,89-92`) → **lộ bản dựng nội bộ chưa duyệt ra review-board `/r` / portal khách**.

**Giới hạn tác động:** (i) không đụng tiền trực tiếp — lương đếm theo `status` (`SALARY_PENDING_STATUSES`/`SALARY_COMPLETED_STATUS`, `dashboard/salary/page.tsx:37-40`) mà `status` ĐÃ bị strip cho non-admin; (ii) không cross-tenant — data-layer `getWorkspacePrisma` inject `workspaceId` vào `where` của `update`/`findUnique` (mục (e)) nên chỉ tác động trong workspace + task của chính assignee.

**Bản chất lỗi:** denylist vốn dễ vỡ — mỗi cột `Task` nhạy cảm thêm mới về sau sẽ **tự động ghi được** nếu không bổ sung `delete`. Đề xuất: chuyển `updateTask` sang **allowlist theo field** như `update-task-details.ts:59-80` (đã dựng `updateData` từ field có tên rõ) hoặc zod schema. Trước mắt strip thêm `clientReview,clientFeedback,clientReviewedAt,clientUserId,createdAt` cho non-admin (và cân nhắc cho cả admin — `clientReview` nên chỉ đổi qua luồng review/portal chuyên trách).

### Đã kiểm — KHÔNG phải mass assignment

| Vị trí | Vì sao an toàn |
|---|---|
| `bonus-config-actions.ts:114` (`create:{ ...data }`) | `data` là object **whitelist tự dựng** (`top1..top3` đã round/validate `:102-109`), không phải input raw |
| `update-task-details.ts:59-80` | **Allowlist chuẩn** — dựng `updateData` từ field có tên; non-admin chỉ `productLink`+`notes_en`; tiền/deadline admin-only + chặn payroll PAID (`:100-102`); sanitize URI `javascript:` (`:13-20`) |
| `createTask` / `assignTask` / bulk-task | build payload từ field có tên (allowlist) |

---

## (d) IDOR / BOLA

### Điểm VỮNG (verify code)

| Cơ chế | Bằng chứng |
|---|---|
| Review-module re-derive workspaceId từ row | `setAssetStatus`: fetch asset by id → `requireReviewAccess({ workspaceId: asset.workspaceId })` → `assertAssetInScope` (`src/lib/review/status.ts:42-47`). Client KHÔNG tự khai workspaceId. Mẫu này lặp ở folders/versions/comments/shares/upload-service (part 05 §0.1). |
| Task update/detail chống BOLA | `updateTask` non-admin phải `task.assigneeId===user.id` (`task-management-actions.ts:59`); `updateTaskDetails` tương tự (`update-task-details.ts:74-76`, R1 fix #10). Cross-tenant chặn bởi data-layer inject `workspaceId` (mục e). |
| Invoice download IDOR | `invoices/[id]/download` check `invoice.workspaceId` khớp (`route.ts:49-52`) |
| Share portal | authz = `clientId ∈ scope.clientIds` + `workspaceId ∈ scope.workspaceIds` qua `findScopedTask` (`share-portal-actions.ts:480`) |
| Template/tag/schedule scoped delete | `deleteTemplate` `deleteMany({id, workspaceId})` (`price-template-actions.ts:68`); tag/schedule check owner |

### Điểm YẾU (không guard / cross-tenant read)

### S3-04 (Low) — `getPayrollLockStatus` không có bất kỳ guard nào
`src/actions/bonus-actions.ts:38-61`. Vào thẳng `getWorkspacePrisma(workspaceId)` — **không session/role check**. Server action = endpoint POST public → caller bất kỳ (kể cả chưa đăng nhập) probe được `isLocked` của **mọi `workspaceId`**. Chỉ lộ 1 boolean nhưng là cross-tenant read không guard. Fix: thêm `verifyWorkspaceAccess(workspaceId,'MEMBER')`.

### S3-05 (Low) — `getWorkspacesForProfile` chỉ `getSession`, leak metadata cross-tenant
`src/actions/workspace-actions.ts:134`. Không kiểm caller có access `profileId` → user đăng nhập bất kỳ liệt kê được `id/name/description` mọi workspace ACTIVE của **profile bất kỳ**. Leak metadata (không leak nội dung task). Fix: kiểm `ProfileAccess(userId, profileId)` trước khi list.

---

## (e) Tenant isolation

### Cơ chế nền — `getWorkspacePrisma` (verify `src/lib/prisma-workspace.ts:105-221`)

- Extension inject `where.workspaceId = currentWorkspaceId` cho **mọi model không thuộc `bypassModels`** trên read/update/delete (`:138-141`); inject vào `data` khi create/createMany/upsert (`:171-214`). Task/Invoice KHÔNG bypass → **luôn bị khoá theo workspace**, kể cả khi call-site KHÔNG truyền `profileId`.
- `Client` bypass workspaceId nhưng **fail-closed**: gọi thiếu `profileId` → **throw** (`:128-135`) chống rò cross-profile.
- Dùng được Prisma `extendedWhereUnique` nên `update({where:{id}})` → `{id, workspaceId}` → **cross-tenant BOLA trên task-id bị chặn ngay tại data-layer** (một task của workspace khác → `findUnique`/`update` trả rỗng).

> Lưu ý phạm vi: bảo vệ này CHỈ áp cho call-site dùng `getWorkspacePrisma`. Nhiều action dùng `prisma` global trực tiếp (notification, member, share-portal…) phải tự scope thủ công — đã được các guard `verifyWorkspaceAccess`/token-scope bao (part 06/07). Không phát hiện query Task/Invoice thiếu filter tenant.

### S3-02 (High) — `updateFrameAccount`: broken access control (guard bất đối xứng) + credential plaintext
`src/actions/global-settings.ts:54-84`. `getFrameAccount` đã được vá HT-022 để đòi WorkspaceMember OWNER/ADMIN (hoặc `isAdmin`) mới đọc credential (`:16-28`), **NHƯNG `updateFrameAccount` chỉ đòi `verifyActiveSession().status==='active'`** (`:57-60`) — **KHÔNG check role**. Hệ quả: bất kỳ user đăng nhập nào (kể cả USER tự signup không thuộc workspace nào) **ghi đè được credential Frame.io dùng chung toàn hệ thống**. Credential lưu **plaintext JSON** trong `Task.notes_vi` (row ma `global-system-settings`, `:64-77`). Đây là finding cũ G-2 (part 06) — **còn sống, chưa fix**. Fix: đối xứng guard với `getFrameAccount` (đòi OWNER/ADMIN) + mã hoá credential.

### S3-03 (High) — `createNotificationInternal` / `createBulkNotificationsInternal` / `createAndBroadcastNotifications`: server action public, không auth
`src/actions/notification-actions.ts:24, 70, 86`. Ba hàm export từ file `'use server'` → Next đăng ký thành **endpoint Server Action public**. Helper `getAuthUserId` có định nghĩa (`:11-14`) nhưng **KHÔNG được gọi** trong 3 hàm này. Kẻ biết action-id (bind trong client bundle) **tạo được notification + gửi email (`maybeSendNotificationEmail`, `:49`) + web push (`sendWebPushToUser`, `:58`) tới `userId` bất kỳ**, với `title`/`body`/`metadata.url` **do attacker kiểm soát** → vector phishing (email/push mang link tuỳ ý) + lạm dụng tài nguyên gửi thư. Cùng lớp lỗi đã vá cho `integration-tokens.ts` (AUDIT R4 — dời sang `server-only`). Fix: tách 3 hàm sang module `import 'server-only'` (không export qua action), hoặc thêm gate session + kiểm quyền tạo-notify tới target.

### S3-06 (Low) — `trackEvent` ghi DB không auth
`src/actions/tracking-actions.ts:58`. Không session guard — chỉ dựa cookie `tracking_session_id` (client tự set) → ghi `Event` tuỳ ý (spam/poison analytics; `userId` luôn null). `forceFlush` (`:29`) không guard nhưng chỉ flush buffer. Fix: gắn session hoặc rate-limit + validate.

### S3-07 (Info) — Validation không nhất quán (không schema ở action classic)
Xem mục (a). zod chỉ ở review-routes + `raw-footage-actions.ts`; `updateTask` denylist; `createTask` lưu text raw không cap. Nợ kỹ thuật, không phải vuln độc lập nhưng khuếch đại rủi ro S3-01.

---

## Bảng tổng hợp finding §3

| ID | Tiêu đề | Mức | File:line |
|---|---|---|---|
| S3-01 | `updateTask` denylist bỏ sót `clientReview` (+4 field) → giả mạo client-approval + qua cổng R5 lộ cut nội bộ | Medium | `src/actions/task-management-actions.ts:35-107` (+`prisma/schema.prisma:385`, `src/lib/portal-derive.ts:42,77`) |
| S3-02 | `updateFrameAccount` guard bất đối xứng — mọi user ghi đè credential chung (plaintext) | High | `src/actions/global-settings.ts:54-84` |
| S3-03 | `notification *Internal` là server action public không auth → phishing email/push tới userId bất kỳ | High | `src/actions/notification-actions.ts:24,70,86` |
| S3-04 | `getPayrollLockStatus` không guard — cross-tenant read `isLocked` | Low | `src/actions/bonus-actions.ts:38-61` |
| S3-05 | `getWorkspacesForProfile` session-only — leak metadata workspace cross-tenant | Low | `src/actions/workspace-actions.ts:134` |
| S3-06 | `trackEvent` ghi DB không auth — poison analytics | Low | `src/actions/tracking-actions.ts:58` |
| S3-07 | Validation không nhất quán / thiếu schema ở action classic | Info | `src/actions/*` (đối chiếu `raw-footage-actions.ts:18`) |

## Điểm tích cực đã xác minh (không phải finding)
- **SQL injection = 0** (Prisma parametrized toàn bộ; không `*Unsafe`).
- Data-layer tenant isolation `getWorkspacePrisma` vững + fail-closed cho Client.
- Review-module IDOR: re-derive workspaceId từ row + `requireReviewAccess` + folder-scope.
- `update-task-details.ts` = allowlist chuẩn (mẫu nên áp cho `updateTask`).

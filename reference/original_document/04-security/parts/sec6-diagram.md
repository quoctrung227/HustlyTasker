# §7 — Sơ đồ kiến trúc bảo mật (Security architecture diagrams)

> Phase 4 — Security audit HustlyTasker. Ngày: 2026-08-02.
> Mô tả 2 sơ đồ Mermaid vẽ đúng cơ chế **đang có thật trong code** (không lý thuyết). Mọi mũi tên/nút đều truy vết được về `file:line` đã verify trực tiếp trên source hiện tại.
>
> **File sơ đồ** (thư mục `docs/system-audit/04-security/diagrams/`):
> | File nguồn | Ảnh render | Loại |
> |---|---|---|
> | `auth-flow.mmd` | `auth-flow.png` | `sequenceDiagram` |
> | `trust-boundaries.mmd` | `trust-boundaries.png` | `flowchart` |
>
> Nguồn code đã đọc & verify: `src/lib/auth.ts`, `src/lib/jwt.ts`, `src/lib/security.ts`, `src/middleware.ts`, `src/lib/auth-guard.ts`, `src/lib/review/access.ts`, `src/lib/review/share-auth.ts`, `src/lib/share-link-auth.ts`, `src/actions/auth-actions.ts`; bản đồ tham chiếu `00-discovery/parts/09-roles-authz.md` + `parts/10-jobs-webhooks.md`.

---

## 1. `auth-flow.mmd` — Luồng xác thực đầy đủ

`sequenceDiagram` gồm **5 nhánh** (A→E) bám sát 10 actor/participant: Người dùng/Khách, Trình duyệt (cookie store), `middleware.ts` (Edge), `loginAction`, `jwt.ts`, DAL guards, `admin/layout.tsx`, `share-link-auth.ts`, `review/share-auth.ts`, Neon Postgres.

### Nhánh A — Đăng nhập nội bộ → mint JWT cookie
- `loginAction` (`src/actions/auth-actions.ts`) rate-limit IP (Upstash 10/phút), lookup User, so bcrypt. Nhánh từ chối trả **`GENERIC_AUTH_ERROR`** đồng nhất + padding delay (chống enumeration) — LOCKED (`auth-actions.ts:303`), CLIENT (`auth-actions.ts:363`).
- Thành công → `loginWithProfile` (`src/lib/auth.ts:32`) → `encrypt()` (`src/lib/jwt.ts:16`, **jose HS256**, key = `env.JWT_SECRET`) đóng payload `{ user: { id, role, sessionVersion, sessionProfileId, email, displayName, restricted, requiresEmailMigration } }` TTL **30 ngày**.
- Set-Cookie `session`: **httpOnly**, `sameSite: lax`, `secure` (prod, tắt khi `ELECTRON_DESKTOP`), `path: /` (`src/lib/auth.ts:42-48`).

### Nhánh B — Mỗi request đi qua middleware (Edge)
- `middleware.ts` **skip** `/_next`, `/api`, path chứa dấu chấm; set header `x-device-type` (`middleware.ts:9-36`). Vì matcher loại `api` → **API route KHÔNG qua middleware, tự verify trong handler** (`middleware.ts:168-170`).
- Không cookie + path `/admin`|`/dashboard` → redirect `/login` (`middleware.ts:71-75`).
- Có cookie → `decrypt()` — **CỐ Ý không check `sessionVersion`** (giữ Edge async-cheap, đúng pattern chống CVE-2025-29927 mô tả tại `auth.ts:56-63`).
- role `CLIENT` → đá `/login` (`middleware.ts:88-90`); thiếu `sessionProfileId` khi vào `/admin`|`/dashboard` → `/login` (`middleware.ts:94-100`).
- **Rolling refresh**: re-issue cookie khi còn <15 ngày (<50% hạn), **BỎ QUA phiên impersonation** (`middleware.ts:145-163`).

### Nhánh C — DAL verify là CỔNG THU HỒI THẬT (điểm mấu chốt)
- `admin/layout.tsx` gọi `verifyProfileAdminAccess(wsId)` → `verifyWorkspaceAccess` (`security.ts:180,38`).
- DB re-check: user **LOCKED** → throw (`security.ts:67-69`); **`JWT.sessionVersion < DB.sessionVersion`** → throw "phiên hết hiệu lực" (`security.ts:79-81`) — đây là nơi "logout tất cả thiết bị"/reset-password thực sự chặn được token cũ trên đường WRITE (Edge không làm được vì không có DB).
- Tính `workspaceRole` theo `ProfileAccess`: OWNER ⇒ OWNER; ADMIN + `workspace.createdAt >= grantedAt` ⇒ ADMIN; **CLIENT ⇒ fail-closed TRƯỚC cả `WorkspaceMember`** (`security.ts:109-119`); còn lại fallback MEMBER (`security.ts:132-142`). Không đủ quyền → `SECURITY_VIOLATION — IDOR Blocked` (`security.ts:145-153`).
- `verifyProfileAdminAccess` fail → layout redirect `/wsId/dashboard` (`admin/layout.tsx:56-66`).

### Nhánh D — Khách portal `/share/[token]` (token = credential, KHÔNG session)
- Middleware để **PUBLIC** early-return + `X-Robots-Tag: noindex` + `Referrer-Policy: no-referrer` (`middleware.ts:44-55`).
- Mọi read/write re-resolve qua chokepoint `resolveShareToken` (`share-link-auth.ts:73`): `TOKEN_RX` 10–128 ký tự; **tier-1 rate-limit per trusted-IP 240/min (fail-OPEN)**; lookup `ClientShareLink` theo **SHA-256 hash-at-rest** (`share-link-auth.ts:136`).
- Mọi nhánh từ chối (sai format / không tồn tại / revoked / expired / client|profile chết / rate-limited) → trả **`null` → 404 đồng nhất** (chống enumeration, `share-link-auth.ts:103,148-157`).
- Token thật → **tier-2 rate-limit per token-hash 2000/min (fail-OPEN)** → gom scope theo **name-path segments** trong profile + mọi workspace (`share-link-auth.ts:190-260`). Khách chỉ VIEW.

### Nhánh E — Guest review `/r/[slug]` (gate chain hợp đồng)
- Middleware PUBLIC + `noindex` + `x-request-id` (`middleware.ts:57-68`).
- `resolveShareGate` (`review/share-auth.ts:76`): chuỗi **`not_found`(404) → `revoked`(410) → `expired`(410) → `password`(401)**; message not_found ≡ revoked (chống enumeration, `:98-108`).
- Nếu có `passwordHash`: `verifyUnlockCookie(rv_unlock_{slug})` — JWT HS256 ký bằng `REVIEW_COOKIE_SECRET`, **bind fingerprint password hiện tại** (đổi pass ⇒ mọi unlock cookie chết); nhập pass đúng → mint unlock JWT TTL min(24h, hạn link) (`:120-144`).
- Identity: cookie `rv_guest_{slug}` → `getGuestSession` (DB chỉ lưu **sha256** token random 32-byte, `:154-165`); hoặc modal Name+Email → `createGuestSession` (`:172-187`); hoặc **known-client auto-identity** → `createLinkClientGuestSession` email synthetic `@review.invalid` **KHÔNG BAO GIỜ tính verified cho sign-off** (chống mạo danh approve, `:309-327`). Vô danh + link không client → **401** (`:355`).

---

## 2. `trust-boundaries.mmd` — Các ranh giới tin cậy

`flowchart` chia hệ thống thành **5 boundary xếp tầng** + 1 vùng dịch vụ ngoài + 1 vùng cảnh báo. Màu: xanh dương = Edge, xanh lá = DAL guard, tím = DB, vàng = dịch vụ ngoài, **đỏ = điểm vào KHÔNG xác thực**.

| Boundary | Nội dung | Điểm bảo mật cốt lõi |
|---|---|---|
| **B0 — Public Internet (untrusted)** | Staff/Admin browser (cookie JWT), Client `/share` (token=credential), Guest `/r` (bcrypt tuỳ chọn + GuestSession), Anonymous/bot | Mọi input từ đây là **không tin cậy** — kể cả `workspaceId`/`token`/`slug` trên URL |
| **B1 — Edge middleware** (`middleware.ts`) | Chỉ **auth-GATE**: decrypt JWT (jose HS256), **KHÔNG check sessionVersion, KHÔNG phân role, KHÔNG chạm DB** | `/share`+`/r` PUBLIC early-return; **`/api`+`/_next` SKIP hẳn middleware** → API tự verify. Thiết kế chủ đích chống CVE-2025-29927 |
| **B2 — Server Actions / API** (authenticated) | 55 file action (~190 fn), 39 route core, 44 route staff `/api/review`, 19 route guest `/api/r`, ~20 portal action | Mỗi lớp **tự gọi DAL** — không tin layout/middleware. `requireReviewAccess`, `requireShare`, `resolveShareToken` là cửa đầu tiên |
| **B3 — DAL guard** (`security.ts` / `profile-permissions.ts` / `review/access.ts`) | `verifyWorkspaceAccess` (LOCKED+sessionVersion+ProfileAccess/WorkspaceMember, IDOR block), `verifyProfileAdminAccess`=`verifyFinanceAccess` (OWNER/ADMIN, **không** isTreasurer), `verifyActiveSession`, `requireReviewAccess`, `resolveShareGate`, `resolveShareToken` | **Cổng thu hồi phiên thật** (so sessionVersion vs DB). Là predicate admin/finance DUY NHẤT — chống leak cross-tenant R7/R8 |
| **B4 — Data** | Neon Postgres qua Prisma | Giữ **`sessionVersion` = source of truth** cho thu hồi phiên |
| **External services** (boundary riêng, secret riêng) | Mux webhook (**HMAC-SHA256 ±5′ timingSafeEqual, fail-closed 401**), Inngest (`INNGEST_SIGNING_KEY`), R2, Resend, Upstash | Webhook Mux là đường vào-ngoài được xác thực chặt nhất; ghi ledger `WebhookEvent` idempotent |

### Vùng ĐỎ — Điểm vào KHÔNG xác thực (deployed & live)
Được đánh dấu cảnh báo đỏ trong sơ đồ vì đang chạy thật trên production mà không có (hoặc yếu) xác thực — đây là các điểm audit §7 cần soi:

| Nút | Vấn đề | Bằng chứng |
|---|---|---|
| `/api/webhooks/calendar` | Verify auth **bị comment**; nhận POST từ bất kỳ ai, `console.log` payload, không ghi DB | `src/app/api/webhooks/calendar/route.ts:11,21` |
| `api/vdownloader.py` | Python Function orphan vẫn deploy; **GET không auth**, nối `pg8000` thẳng Neon → **bypass toàn bộ guard B1–B3** | `vercel.json:3-5`, `api/vdownloader.py:44-45` |
| `/api/test-email` | Guard CRON_SECRET nhưng **nhận secret qua query param** `?secret=` → lọt access log; file tự ghi "DELETE after debugging" | `src/app/api/test-email/route.ts:3,17` |
| 6/7 cron | So sánh CRON_SECRET bằng **chuỗi thường** (không `timingSafeEqual`); chỉ `auth-cleanup` timing-safe | `parts/10-jobs-webhooks.md §1`, `auth-cleanup/route.ts:19-25` |

---

## 3. Nhận xét kiến trúc (theo bằng chứng, không phải finding)

1. **Phòng thủ nhiều tầng đúng thiết kế**: xác thực (Edge, rẻ) tách khỏi phân quyền/thu hồi (DAL, có DB). Middleware KHÔNG là điểm quyết định authz — mọi cửa thật nằm ở layout + DAL. Đây là mitigation CVE-2025-29927 được ghi rõ trong code (`auth.ts:56-63`).
2. **`sessionVersion` là trục thu hồi phiên**: enforce đồng thời ở `getCurrentUser` (`auth-guard.ts:43-47`), `verifyActiveSession` (`security.ts:257-269`), `verifyWorkspaceAccess` (`security.ts:79-81`), `isSessionLive`. Edge chỉ gia hạn cookie, không thu hồi — chấp nhận cửa sổ trễ tới khi request chạm DAL.
3. **Hai hệ guest token độc lập** (`/share` = `ClientShareLink` SHA-256 no-password vs `/r` = `ShareLink` gate-chain bcrypt) đều: hash-at-rest, uniform failure chống enumeration, rate-limit fail-OPEN (ưu tiên availability của link khách hơn brute-force protection — hợp lý với token 256-bit nhưng cần lưu ý).
4. **Bề mặt rủi ro rõ nhất** không nằm ở lõi auth (khá chắc) mà ở **vùng đỏ**: `vdownloader.py` là đường thẳng tới DB bỏ qua mọi guard — ưu tiên cao nhất trong §7.

---

*Agent §7 chỉ vẽ + mô tả sơ đồ — không phát sinh finding (findings=[]). Các điểm vùng đỏ ở trên được các agent finding khác của Phase 4 xử lý chi tiết.*

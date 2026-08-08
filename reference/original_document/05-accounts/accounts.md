# PHASE 5 — Account test cho từng role

> ⚠️ **CẢNH BÁO: CHỈ DÙNG CHO DEV/TEST.** Các account dưới đây được seed vào **Neon TEST branch** (`ep-frosty-forest-…`), **KHÔNG phải production**. Nếu có ai chạy seed này vào môi trường khác: đổi hoặc xoá toàn bộ account `test-audit-*` trước khi lên production. Password hiển thị plaintext ở đây chỉ vì là tài liệu test — trong DB chỉ lưu bcrypt hash.

## 1. Cách tạo (đã thực thi 2026-08-02)

- Seed script có sẵn của repo (`prisma/seed.ts`) là **no-op chủ đích** (SaaS public signup — `prisma/seed.ts:6-14`) → viết seed script mới: [`seed-test-accounts.ts`](seed-test-accounts.ts).
- Hash password dùng **đúng thuật toán của hệ thống: bcryptjs, 10 rounds** — giống `src/actions/create-user.ts:87` và luồng signup. **Không insert plaintext vào DB.**
- Guard an toàn trong script: từ chối chạy nếu `DATABASE_URL` không chứa `frosty-forest` (TEST branch) hoặc chứa `autumn-flower` (PROD). Đã `prisma db push` đồng bộ schema TEST branch trước khi seed.
- Idempotent: upsert theo `username` — chạy lại không tạo trùng (nhưng password random lại mỗi lần chạy).
- Chạy lại khi cần:

```bash
npx tsx docs/system-audit/05-accounts/seed-test-accounts.ts
```

## 2. Danh sách role THẬT (từ code — Phase 0 `parts/09-roles-authz.md`)

| Tầng | Giá trị | Nguồn |
|---|---|---|
| `UserRole` (global, enum) | ADMIN, USER, AGENCY_ADMIN, CLIENT, LOCKED | `prisma/schema.prisma` enum UserRole |
| `ProfileRole` (RBAC chính, qua `ProfileAccess.role`) | OWNER, ADMIN, USER, CLIENT | `prisma/schema.prisma` enum ProfileRole |
| `WorkspaceRole` (String trên `WorkspaceMember.role`) | OWNER, ADMIN, MEMBER, GUEST | `prisma/schema.prisma:114` |
| Flag | `isTreasurer` (boolean, chỉ còn là UI flag) | `src/actions/toggle-treasurer.ts:13` |

2 actor khách (**Client portal `/share/[token]`** và **Guest reviewer `/r/[slug]`**) hoạt động hoàn toàn bằng **token, không có account** — không thể (và không cần) seed user cho 2 actor này; token test tạo qua UI admin (CRM → share link) hoặc `src/actions/share-link-actions.ts:46`.

## 3. Bảng account đã tạo (TEST branch)

Tenant test: Profile `AUDIT-TEST Team` (`676c651b-8bb6-4316-a329-22d6b9b16340`) · Workspace `AUDIT-TEST 2026-08` (`83988af4-6790-4820-95d3-84fd3544267f`) · Client `AUDIT-TEST Client` (id 329).

| Role | Username | Email | Password | Ghi chú |
|---|---|---|---|---|
| User:ADMIN / Profile:OWNER / WS:OWNER | `test-audit-global-admin` | test+global-admin@example.com | `PWXmCevJ1uCeezPdpB!A9` | Global admin |
| User:USER / Profile:OWNER / WS:OWNER | `test-audit-profile-owner` | test+profile-owner@example.com | `4C8LxoNNuo9ODqqrwf!A9` | Chủ team |
| User:USER / Profile:ADMIN / WS:ADMIN | `test-audit-profile-admin` | test+profile-admin@example.com | `A4WDaW_lgprOIGaohd!A9` | Quản trị được mời |
| User:USER / Profile:USER / WS:MEMBER | `test-audit-editor` | test+editor@example.com | `N1awELUz18Vtjn1_w8!A9` | Staff/editor thường |
| User:USER / Profile:USER / WS:GUEST | `test-audit-ws-guest` | test+ws-guest@example.com | `P7j3F9isCnSF4PcPuO!A9` | Workspace guest |
| User:AGENCY_ADMIN / Profile:USER / WS:MEMBER | `test-audit-agency-admin` | test+agency-admin@example.com | `I6rd-gabczCRIQY3CP!A9` | Role legacy còn trong enum |
| User:CLIENT / Profile:CLIENT (+clientId) | `test-audit-client` | test+client@example.com | `0kzrnQsym7HSw4dNUG!A9` | **Login bị chặn by design** (`src/actions/auth-actions.ts:361-363`) — chứng minh cơ chế chặn CLIENT |
| User:LOCKED | `test-audit-locked` | test+locked@example.com | `M-ik72lorouBheyrwV!A9` | **Login bị chặn** — trạng thái ban (`src/actions/auth-actions.ts:302-303`) |

## 4. Vì sao KHÔNG seed vào production

`.env` của repo trỏ prod Neon (`ep-autumn-flower-…`) đang phục vụ người dùng thật — tạo account test vào đó sẽ hiện trong danh sách member/switcher thật. Theo nguyên tắc audit không đụng dữ liệu prod, seed chỉ thực thi trên TEST branch (`.env.test`, host `ep-frosty-forest-…` — đúng harness QA sẵn có của repo). Muốn có account test trên môi trường khác: chạy lại script với DATABASE_URL của môi trường đó **và sửa guard có chủ ý** (guard là tấm chắn cuối chống chạy nhầm).

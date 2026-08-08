# PHASE 1 — DIAGRAMS

> 83 diagram Mermaid (source `.mmd` + ảnh `.png` render bằng `@mermaid-js/mermaid-cli` + Chrome local, scale ×2). Mỗi flow có đủ **3 loại**: class · sequence · state. Mọi diagram vẽ theo CODE THẬT (tên hàm/endpoint/status đúng file:line, có ghi chú nguồn trong `%%` comment cuối mỗi `.mmd`).

## Cách render lại (nếu sửa .mmd)

```bash
node <scratchpad>/mmd/node_modules/@mermaid-js/mermaid-cli/src/cli.js -i <file>.mmd -o <file>.png -p <scratchpad>/mmd/puppeteer.json -b white -s 2
```

`puppeteer.json` trỏ `executablePath` tới Chrome đã cài (`C:/Program Files/Google/Chrome/Application/chrome.exe`).

## Diagram cấp hệ thống — `system/`

| File | Loại | Mô tả |
|---|---|---|
| `architecture.png` | flowchart | Kiến trúc client → Vercel (Next.js) → Neon + external services (Mux/R2/Inngest/Resend/Upstash/Supabase/Blob/web-push/OAuth/OpenAI) + 7 cron |
| `deploy-topology.png` | flowchart | Nguồn code → Vercel build (postinstall `prisma db push` áp DDL vào Neon lúc build) → prod `hustlytasker.xyz`; nhánh electron/mcp-server local + TEST branch |
| `erd-full.png` | erDiagram | ERD toàn bộ 67 model + quan hệ (scalar-FK review vẽ nét đứt) |
| `erd-{auth,tenant,task,crm,finance,review,notify,misc}.png` | erDiagram | 8 ERD chia theo domain, field chi tiết hơn erd-full |

## Diagram theo flow — 24 folder

16 flow chính (F01–F16) + 8 flow phụ (P1–P8). ⭐ = 5 flow quan trọng nhất.

| Folder | Flow | 3 diagram |
|---|---|---|
| `F01-auth` | Auth: signup → verify email (LINK token, không phải OTP) → login password/Google → forgot (OTP) | class · sequence · state |
| `F02-profile-workspace` | Chọn/switch Profile & Workspace + tạo tháng mới rollover | class · sequence · state |
| `F03-membership-invite` | Mời member + cross-team access | class · sequence · state |
| `F04-task-lifecycle` ⭐ | Task: tạo (đơn/Velox) → giao → editor làm → duyệt → hoàn thành | class · sequence · state |
| `F05-marketplace` | Editor claim/return task | class · sequence · state |
| `F06-review-upload` ⭐ | Upload bản dựng multipart R2 → Mux encode → Inngest | class · sequence · state |
| `F07-team-review-status` ⭐ | Team player + status machine + approve-send | class · sequence · state |
| `F08-guest-review-decision` ⭐ | Guest /r/ gate → xem → comment → approve/request-changes → Inngest sync task | class · sequence · state |
| `F09-client-portal` ⭐ | Portal /share: theo dõi task, duyệt deliverable, request, invoice | class · sequence · state |
| `F10-client-request-inbox` | Client request → admin inbox → accept thành task | class · sequence · state |
| `F11-task-comments` | Task comments & mentions (INTERNAL/CLIENT) | class · sequence · state |
| `F12-notifications` | Notification in-app + email digest + web push | class · sequence · state |
| `F13-payroll` ⭐ | Chốt lương editor theo status task + bonus + khoá sổ | class · sequence · state |
| `F14-finance-invoice` | Gom task chưa bill → invoice PDF → record payment | class · sequence · state |
| `F15-crm-sharelink` | Cây client/sub-client + phát hành/thu hồi ClientShareLink | class · sequence · state |
| `F16-system-cron-webhook` | 7 cron + webhook Mux/calendar + 4 Inngest function | class · sequence · state |
| `P1-availability-schedule` | Editor khai lịch rảnh, admin xem matrix | class · sequence · state |
| `P2-integrations-scan` | Drive/Dropbox OAuth + scan folder footage | class · sequence · state |
| `P3-study-place` | Flashcard/quiz nội bộ + tiến độ | class · sequence · state |
| `P4-leaderboard-analytics` | Leaderboard/reputation/analytics + presence | class · sequence · state |
| `P5-impersonation` | Admin nhập vai user, TTL 2h, audit | class · sequence · state |
| `P6-trash-restore` | Trash & restore đa tầng + cron hard-delete | class · sequence · state |
| `P7-audit-log` | Audit log & error dictionary/error log | class · sequence · state |
| `P8-profile-settings` | Cài đặt profile/user: avatar, mật khẩu, tags, global settings | class · sequence · state |

## Ghi chú đúng-theo-code quan trọng (phát hiện khi vẽ)

- **F01**: tên flow trong inventory ghi "verify OTP email" nhưng CODE thật verify email bằng **LINK token** (GET `/api/auth/verify-email`, `EmailVerificationToken` TTL 24h); `/api/auth/verify-otp` là bước của luồng **QUÊN MẬT KHẨU** (`PasswordResetOTP`). Diagram vẽ theo code.
- **Auth session**: model `Session` (`schema.prisma:963`) là session analytics/thời lượng; phiên đăng nhập THẬT là cookie JWT httpOnly TTL 30 ngày do `src/lib/auth.ts` set.
- **P7**: `/api/log-client-error` **không auth và KHÔNG ghi DB** (chỉ `console.error` ra Vercel logs — `route.ts:12-15`), khác giả định ban đầu.
- **Enum chết**: `Workspace.SUSPENDED`, `Invoice.DRAFT/OVERDUE`, `Client.MERGED` (trong app), `ClientRequestStatus.REVIEWING` khai báo nhưng không code path nào set — không vẽ vào state.
- **State suy từ field**: nhiều model không có cột status enum (AuditLog, ErrorLog, OTP/token) → state diagram dùng trạng thái suy từ field thật (consumedAt/invalidatedAt/usedAt/expiresAt) kèm nguồn dòng.

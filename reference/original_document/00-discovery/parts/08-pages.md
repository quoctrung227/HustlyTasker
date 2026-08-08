# 08 — Inventory Pages/Screens (tất cả route frontend)

> Phạm vi: mọi `src/app/**/page.tsx` + các `layout.tsx` quan trọng. Nguồn: glob thực tế trên worktree, 76 file (56 `page.tsx` + 9 `layout.tsx` + 1 `default.tsx` + `global-error.tsx`).
> Ghi chú cột "Client/Server": xét đúng file `page.tsx` (có `'use client'` hay không). Đa số page là **Server Component mỏng** (guard + fetch) rồi mount client component nặng — cột "Mục đích" ghi component chính được mount.

## 0. Cây layout (khung cha) — ai gate cái gì

| Layout | File | Guard / vai trò |
|---|---|---|
| Root | `src/app/layout.tsx:47` | Không guard. Font Plus Jakarta, `notranslate`, Toaster, ConfirmProvider, RadialNavProvider — áp cho TOÀN BỘ app. |
| Workspace | `src/app/[workspaceId]/layout.tsx:12` | Bắt login (`:23-26`), backfill profileId (`:33-50`), verify workspace tồn tại (`:64-67`), **đá CLIENT role về /login** (fail-closed, `:117-131`), chứa slot `@modal` (`:181`), MarketplaceProvider, NotificationProvider, UsernameMigrationModal. |
| Admin | `src/app/[workspaceId]/admin/layout.tsx:17` | `verifyActiveSession` + **`verifyProfileAdminAccess`** (`:56-66`) — non-admin bị redirect về `/dashboard`. Dựng `AppShell` (desktop/mobile tự chọn), RoleWatcher, EmailMigrationModal, ImpersonationBanner. |
| Dashboard (staff) | `src/app/[workspaceId]/dashboard/layout.tsx:19` | `verifyActiveSession` (không cần admin). `AppShell viewRole="USER"` (`:77`). |
| Team (review) | `src/app/[workspaceId]/team/layout.tsx:13` | **Chỉ gate membership** qua `requireReviewAccess` (`:26-31`) — editor (USER) vào được; CLIENT/LOCKED/non-member bị đá. KHÔNG dựng chrome. |
| Team (browser) | `src/app/[workspaceId]/team/(browser)/layout.tsx:14` | Dựng `AppShell`, viewRole = ADMIN/USER theo `verifyProfileAdminAccess` (`:36-43`). Route group `(browser)` → KHÔNG áp cho player `asset/[assetId]` (full-bleed, fix B9). |
| Share portal | `src/app/share/[token]/layout.tsx:53` | PUBLIC. Theme "The Desk" (light, Fraunces/Hanken/Space Mono), `robots noindex` + `referrer no-referrer` (`:48-56`). |
| Modal slot | `src/app/[workspaceId]/@modal/default.tsx` | Render null khi không có intercepting route. |
| Global error | `src/app/global-error.tsx` | Trang lỗi toàn cục (diagnostic fallback). |

Lưu ý: **khu `/mc/**` KHÔNG có layout riêng** — từng page tự dựng shell Mission Control và tự gate admin (nhất quán fail-closed từng file).

## 1. Khu PUBLIC (không cần đăng nhập)

| URL | File | Layout cha | Đối tượng | Mục đích | Client/Server |
|---|---|---|---|---|---|
| `/` | `src/app/page.tsx:49` | Root | Public/guest | Landing marketing HustlyTasker (`LandingPage`); đã login thì redirect thẳng vào app qua `resolveHomeDestination` (`:52-54`). | Server |
| `/login` | `src/app/login/page.tsx:9` | Root | Public | Form đăng nhập (password + Google), hỗ trợ `?next=` returnTo. | **Client** |
| `/signup` | `src/app/signup/page.tsx:24` | Root | Public | Đăng ký tài khoản (displayName/username/email/password, HIBP, honeypot, BotID). | **Client** |
| `/forgot-password` | `src/app/forgot-password/page.tsx:19` | Root | Public | Quên mật khẩu 3 bước: email → OTP 6 số → đặt mật khẩu mới. | **Client** |
| `/legal/privacy` | `src/app/legal/privacy/page.tsx:9` | Root | Public | Chính sách bảo mật (tiếng Việt, link từ /signup). | Server |
| `/legal/terms` | `src/app/legal/terms/page.tsx:9` | Root | Public | Điều khoản dịch vụ (tiếng Việt, link từ /signup). | Server |
| `/portal-notify/unsubscribe?token=` | `src/app/portal-notify/unsubscribe/page.tsx:10` | Root | Khách (client của agency) | Trang xác nhận hủy nhận email thông báo portal — GET không mutate, bấm nút mới gọi server action. Link từ footer email (`src/lib/review/guest-notify.ts:233`). | **Client** |
| `/r/unsubscribe?token=` | `src/app/r/unsubscribe/page.tsx:10` | Root | Guest reviewer | Xác nhận hủy nhận email review-update (chống mail-scanner tự GET unsubscribe); mount `UnsubscribeConfirm`. | Server (mount client) |

## 2. Khu tài khoản (đăng nhập, NGOÀI workspace)

| URL | File | Layout cha | Đối tượng | Mục đích | Client/Server |
|---|---|---|---|---|---|
| `/welcome` | `src/app/welcome/page.tsx:20` | Root | Staff/admin mới | Màn hình sau khi tạo profile chưa có workspace; có workspace rồi thì auto-redirect (`:47-55`); mount `WelcomeClient`. Được nhảy tới từ `src/lib/post-login.ts:25,33` + switcher (`DashboardTopBar.tsx:74`). | Server |
| `/account/trash` | `src/app/account/trash/page.tsx:14` | Root | User đã login | Thùng rác workspace của tôi (khôi phục trong 30 ngày) — `getMyTrashedWorkspaces` + `RestoreWorkspaceButton`. ⚠️ **Orphan-candidate: không tìm thấy link nội bộ nào trỏ tới `/account/trash`** (grep toàn `src/` chỉ match chính file này) — chỉ vào được bằng gõ URL. | Server |

## 3. App nội bộ `/[workspaceId]/**`

### 3.1 Gốc workspace + task detail

| URL | File | Layout cha | Đối tượng | Mục đích | Client/Server |
|---|---|---|---|---|---|
| `/[workspaceId]` | `src/app/[workspaceId]/page.tsx:10` | Workspace | Staff/admin | Redirect thuần về `/[workspaceId]/dashboard` (`:28`); regex chặn path rác kiểu `/icon.png` (`:8,18-20`). | Server |
| `/[workspaceId]/task/[taskId]` | `src/app/[workspaceId]/task/[taskId]/page.tsx:10` | Workspace | Staff/admin | Trang task-detail full-screen (deep-link / hard refresh / mobile "Xem đầy đủ") — `loadTaskDetail` sanitize tiền, mount `TaskDetailRoute`. | Server |
| `/[workspaceId]/task/[taskId]` (soft-nav) | `src/app/[workspaceId]/@modal/(.)task/[taskId]/page.tsx` | Workspace (slot `@modal`) | Staff/admin | Intercepting parallel route: cùng URL nhưng render thành **modal đè trang hiện tại** khi soft-navigation. Ghi chú trong file (`:11-14`): hiện chỉ fire từ link mobile "Xem đầy đủ" — desktop vẫn dùng state-modal in-memory. | Server |

### 3.2 `/dashboard/**` — khu STAFF (editor, viewRole USER)

| URL | File | Layout cha | Đối tượng | Mục đích | Client/Server |
|---|---|---|---|---|---|
| `/[workspaceId]/dashboard` | `src/app/[workspaceId]/dashboard/page.tsx` | Workspace → Dashboard | Staff | Trang chủ editor: task của tôi (sanitize `sanitizeTaskListForUser`), widget lương (SALARY_* constants), profile switcher. | Server |
| `/[workspaceId]/dashboard/tasks` | `src/app/[workspaceId]/dashboard/tasks/page.tsx:1-4` | Workspace → Dashboard | Staff | Bảng task đầy đủ "Xem tất cả" (`UserWorkflowTabs`), field tài chính bị strip. | Server |
| `/[workspaceId]/dashboard/salary` | `src/app/[workspaceId]/dashboard/salary/page.tsx:1-4` | Workspace → Dashboard | Staff | Tab "Lương" (BottomNav mobile): `WidgetNetSalary` — earned/pending + thưởng, đúng công thức dashboard. | Server |
| `/[workspaceId]/dashboard/schedule` | `src/app/[workspaceId]/dashboard/schedule/page.tsx` | Workspace → Dashboard | Staff | Lịch rảnh/bận cá nhân theo tuần (`OptimisticGrid`). | Server |
| `/[workspaceId]/dashboard/errors` | `src/app/[workspaceId]/dashboard/errors/page.tsx:8` | Workspace → Dashboard | Staff | Hồ sơ lỗi của CHÍNH user (performance score + error logs, `StaffErrorDetail`). | Server |
| `/[workspaceId]/dashboard/profile` | `src/app/[workspaceId]/dashboard/profile/page.tsx:12` | Workspace → Dashboard | Staff | Hồ sơ cá nhân: avatar, thông tin, QR thanh toán, cài đặt thông báo. | Server |

### 3.3 `/admin/**` — khu ADMIN (Giao diện 1)

| URL | File | Layout cha | Đối tượng | Mục đích | Client/Server |
|---|---|---|---|---|---|
| `/[workspaceId]/admin` | `src/app/[workspaceId]/admin/page.tsx:33` | Workspace → Admin | Admin | Dashboard admin: KPI + finance widgets, Leaderboard, hàng khách, board `TaskWorkflowTabs` 6 cột; mobile render `AdminMobileHome`. | Server |
| `/[workspaceId]/admin/queue` | `src/app/[workspaceId]/admin/queue/page.tsx` | Workspace → Admin | Admin | Kho task đợi giao (`TaskTable`/`MobileTaskView`) + check overdue. | Server |
| `/[workspaceId]/admin/requests` | `src/app/[workspaceId]/admin/requests/page.tsx:5` | Workspace → Admin | Admin | Hộp thư yêu cầu từ khách (`RequestsInbox` — tạo task prefill / từ chối / Velox). | Server |
| `/[workspaceId]/admin/crm` | `src/app/[workspaceId]/admin/crm/page.tsx` | Workspace → Admin | Admin | Danh sách khách hàng (`ClientList`/`MobileClientList`, tạo khách). | Server |
| `/[workspaceId]/admin/crm/[id]` | `src/app/[workspaceId]/admin/crm/[id]/page.tsx` | Workspace → Admin | Admin | Chi tiết 1 khách: analytics, sub-client, hóa đơn. | Server |
| `/[workspaceId]/admin/finance` | `src/app/[workspaceId]/admin/finance/page.tsx` | Workspace → Admin | Admin (treasurer) | Dashboard tài chính (`computeWorkspaceFinance` → `FinanceDashboardClient`). | Server |
| `/[workspaceId]/admin/payroll` | `src/app/[workspaceId]/admin/payroll/page.tsx` | Workspace → Admin | Admin | Bảng lương theo chu kỳ (`PayrollCard`, `BonusCalculator`, gate `verifyProfileAdminAccess`). | Server |
| `/[workspaceId]/admin/analytics` | `src/app/[workspaceId]/admin/analytics/page.tsx` | Workspace → Admin | Admin | Phân tích hiệu suất team (`AnalyticsTable` rank S–D, `LivePresenceBoard` + impersonate). | Server |
| `/[workspaceId]/admin/analytics/staff/[userId]` | `src/app/[workspaceId]/admin/analytics/staff/[userId]/page.tsx` | Workspace → Admin | Admin | Drill-down hồ sơ lỗi/điểm của 1 nhân sự (`StaffErrorDetail`). | Server |
| `/[workspaceId]/admin/schedule` | `src/app/[workspaceId]/admin/schedule/page.tsx` | Workspace → Admin | Admin | Lịch rảnh/bận cả team (`OptimisticGrid`/`MobileScheduleView`). | Server |
| `/[workspaceId]/admin/profile-members` | `src/app/[workspaceId]/admin/profile-members/page.tsx` | Workspace → Admin | Admin | Roster thành viên cấp TỔ CHỨC (ProfileAccess) + mời thành viên. | Server |
| `/[workspaceId]/admin/members` | `src/app/[workspaceId]/admin/members/page.tsx:11-14` | Workspace → Admin | Admin | **Redirect stub** → `/admin/profile-members` (giữ bookmark cũ + revalidatePath; không phải dead-code, là chủ đích). | Server |
| `/[workspaceId]/admin/settings` | `src/app/[workspaceId]/admin/settings/page.tsx` | Workspace → Admin | Admin | Cài đặt workspace 4 tab (`WorkspaceSettingsPanel`: tổng quan · OAuth · bảng giá · StudyPlace). | Server |
| `/[workspaceId]/admin/audit-log` | `src/app/[workspaceId]/admin/audit-log/page.tsx` | Workspace → Admin | Admin | Nhật ký hoạt động (`AuditLogViewer` — filter, diff before/after, redact secret). | Server |
| `/[workspaceId]/admin/cancelled` | `src/app/[workspaceId]/admin/cancelled/page.tsx` | Workspace → Admin | Admin | Task đã hủy/lưu trữ + khôi phục (link duy nhất từ cuối admin dashboard, `admin/page.tsx:420`). | Server |
| `/[workspaceId]/admin/client-trash` | `src/app/[workspaceId]/admin/client-trash/page.tsx` | Workspace → Admin | Admin | Thùng rác khách hàng (`ClientTrashClient`). | Server |
| `/[workspaceId]/admin/profile-trash` | `src/app/[workspaceId]/admin/profile-trash/page.tsx` | Workspace → Admin | Owner | Thùng rác tổ chức/profile (`ProfileTrashClient`, OWNER-only qua action). | Server |
| `/[workspaceId]/admin/menu` | `src/app/[workspaceId]/admin/menu/page.tsx:1-3` | Workspace → Admin | Admin (mobile) | Menu hub mobile — section-list các khu quản trị không nằm trên BottomNav; lọc "Tài chính" theo isTreasurer. | Server |

### 3.4 `/team/**` — Module Video Review "Tệp" (staff + admin đều vào)

| URL | File | Layout cha | Đối tượng | Mục đích | Client/Server |
|---|---|---|---|---|---|
| `/[workspaceId]/team` | `src/app/[workspaceId]/team/(browser)/page.tsx:1-4` | Workspace → Team → (browser) | Staff + admin | Trình duyệt file review gốc (`TeamBrowser`) — folder/asset, data client-fetch qua `/api/review/*`. | Server |
| `/[workspaceId]/team/folder/[folderId]` | `src/app/[workspaceId]/team/(browser)/folder/[folderId]/page.tsx:1-4` | Workspace → Team → (browser) | Staff + admin | Deep-link vào 1 folder cụ thể (seed `TeamBrowser`). | Server |
| `/[workspaceId]/team/shares` | `src/app/[workspaceId]/team/(browser)/shares/page.tsx:1-3` | Workspace → Team → (browser) | Staff + admin | Quản lý link chia sẻ review (`SharesTable`; USER chỉ thấy link của mình + task được giao). | Server |
| `/[workspaceId]/team/trash` | `src/app/[workspaceId]/team/(browser)/trash/page.tsx:1-4` | Workspace → Team → (browser) | Staff + admin | Recently Deleted của module review (`TeamTrash`; purge = workspace ADMIN). | Server |
| `/[workspaceId]/team/asset/[assetId]?v=&comment=` | `src/app/[workspaceId]/team/asset/[assetId]/page.tsx:1-3` | Workspace → Team (KHÔNG qua `(browser)` → full-bleed) | Staff + admin | Player review full-page (`ReviewPlayerShell`: scrubber, range-loop, comment timecode, versions, gửi khách duyệt). | Server |

### 3.5 `/mc/**` — "Giao diện 2 · Mission Control" (alternate ADMIN desktop UI, 100% admin-gated từng page)

Vào từ nút "Giao diện 2 · Mission Control" trong sidebar (`src/components/layout/AppSidebar.tsx:427`). Mỗi page tự gọi `verifyProfileAdminAccess` fail-closed (vd `mc/page.tsx:61`). Không có layout chung — mỗi màn tự dựng `McShell`/rail.

| URL | File | Đối tượng | Mục đích | Client/Server |
|---|---|---|---|---|
| `/[workspaceId]/mc` | `src/app/[workspaceId]/mc/page.tsx:55` | Admin | M1 Tổng quan: board 6 cột + finance KPI + leaderboard (cùng data /admin). | Server |
| `/[workspaceId]/mc/queue` | `src/app/[workspaceId]/mc/queue/page.tsx:1-4` | Admin | M2 Kho task đợi / triage giao việc. | Server |
| `/[workspaceId]/mc/task/[taskId]` | `src/app/[workspaceId]/mc/task/[taskId]/page.tsx:1-6` | Admin | M3 Task drawer deep-link (refresh/share URL). | Server |
| `/[workspaceId]/mc/tien` | `src/app/[workspaceId]/mc/tien/page.tsx:1-5` | Admin | M4 Payroll (Thực nhận, mark-paid/revert). | Server |
| `/[workspaceId]/mc/finance` | `src/app/[workspaceId]/mc/finance/page.tsx:1-3` | Admin | M5 Tài chính (THỰC TẾ vs DỰ KIẾN + nhật ký giao dịch). | Server |
| `/[workspaceId]/mc/lich` | `src/app/[workspaceId]/mc/lich/page.tsx:1-3` | Admin | M6 Lịch 2 chế độ: nhân sự rảnh/bận + deadline. | Server |
| `/[workspaceId]/mc/requests` | `src/app/[workspaceId]/mc/requests/page.tsx:1-3` | Admin | M7 Hộp thư yêu cầu khách (wrap `RequestsInbox`). | Server |
| `/[workspaceId]/mc/tep` | `src/app/[workspaceId]/mc/tep/page.tsx:1-6` | Admin | M8 Tệp/Review (wrap `TeamBrowser`, player mở sang /mc/asset). | Server |
| `/[workspaceId]/mc/members` | `src/app/[workspaceId]/mc/members/page.tsx:1-5` | Admin | M9 Thành viên (roster + metrics, lương gộp server-side). | Server |
| `/[workspaceId]/mc/add` | `src/app/[workspaceId]/mc/add/page.tsx:1-4` | Admin | M10 Add Task standalone (host `AddTaskModal` thật). | Server |
| `/[workspaceId]/mc/asset/[assetId]` | `src/app/[workspaceId]/mc/asset/[assetId]/page.tsx:1-5` | Admin | M11 Review player trong namespace MC (cùng `ReviewPlayerShell`). | Server |
| `/[workspaceId]/mc/crm` | `src/app/[workspaceId]/mc/crm/page.tsx:1-7` | Admin | M12 Quản lý khách hàng (wrap `ClientsManagerPanel`). | Server |
| `/[workspaceId]/mc/hoa-don` | `src/app/[workspaceId]/mc/hoa-don/page.tsx:1-5` | Admin | M13 Tạo hóa đơn full-bleed (embed `InvoiceModal`). | Server |
| `/[workspaceId]/mc/ho-so-thanh-toan` | `src/app/[workspaceId]/mc/ho-so-thanh-toan/page.tsx:1-4` | Admin | M14 Quản lý hồ sơ thanh toán (`BillingProfileManager`). | Server |
| `/[workspaceId]/mc/ho-so` | `src/app/[workspaceId]/mc/ho-so/page.tsx:1-7` | Admin | M15 Hồ sơ cá nhân (vỏ MC) + chỉ số cá nhân read-only. | Server |
| `/[workspaceId]/mc/board` | `src/app/[workspaceId]/mc/board/page.tsx:1-8` | Admin | M16 Bảng vận hành task đầy đủ (wrap `TaskWorkflowTabs`). | Server |
| `/[workspaceId]/mc/shares` | `src/app/[workspaceId]/mc/shares/page.tsx:1-6` | Admin | M21 Link chia sẻ review (wrap `SharesTable`). | Server |
| `/[workspaceId]/mc/trash` | `src/app/[workspaceId]/mc/trash/page.tsx:1-7` | Admin | M26 Thùng rác hợp nhất 4 tab (Tệp · Khách · Task hủy · Tổ chức). | Server |
| `/[workspaceId]/mc/analytics` | `src/app/[workspaceId]/mc/analytics/page.tsx:1-5` | Admin | M28 Phân tích hiệu suất (wrap `AnalyticsTable` + `LivePresenceBoard`). | Server |
| `/[workspaceId]/mc/audit` | `src/app/[workspaceId]/mc/audit/page.tsx:1-5` | Admin | M29 Nhật ký hoạt động (wrap `AuditLogViewer`). | Server |
| `/[workspaceId]/mc/settings` | `src/app/[workspaceId]/mc/settings/page.tsx:1-6` | Admin | M30 Cài đặt workspace (wrap `WorkspaceSettingsPanel`). | Server |

## 4. `/share/[token]` — Client portal công khai (token = credential)

| URL | File | Layout cha | Đối tượng | Mục đích | Client/Server |
|---|---|---|---|---|---|
| `/share/[token]` | `src/app/share/[token]/page.tsx:16` | Share layout ("The Desk", light) | **Khách của agency** (không session) | Portal tiến độ dự án: deliverables, invoices, workspaces — `resolveShareToken` (`:21-23`, mọi lỗi đều 404 đồng nhất) + audit access (`:30-40`); mount `SharePortalClient`. Middleware early-return để không dính session guard (`src/middleware.ts` mục 1.6). | Server (mount client) |

## 5. `/r/[slug]` — Guest review công khai (module video review)

| URL | File | Layout cha | Đối tượng | Mục đích | Client/Server |
|---|---|---|---|---|---|
| `/r/[slug]` | `src/app/r/[slug]/page.tsx:22` | Root | **Guest reviewer** (không session, tiếng Anh, dark) | Trang duyệt video qua link chia sẻ: gate chain server-side (`:27-38`: not_found/revoked → "unavailable", expired, password) rồi mount `GuestReviewApp` (comment timecode, approve, annotation). Guest identity qua modal Name/Email (`:41-52`). | Server (mount client) |
| `/r/unsubscribe` | (đã liệt kê ở mục 1) | Root | Guest | Hủy nhận email review-update. | Server |

## 6. Trang nghi DEAD / PREVIEW — kết quả kiểm tra link

Grep toàn `src/` cho `desk-preview|velox-v4-preview|diagnostic`: **không có bất kỳ link/import nào từ code khác trỏ tới 3 route này** (chỉ match chính file của chúng + các chuỗi "diagnostics" không liên quan trong lib Velox).

| URL | File | Trạng thái | Bằng chứng |
|---|---|---|---|
| `/diagnostic` | `src/app/diagnostic/page.tsx:1-8` | **Dead stub chủ đích** — 8 dòng, chỉ in "Công cụ chẩn đoán hiện đang bị tắt vì lý do bảo mật". Không ai link tới. Ứng viên XÓA. | Nội dung file + grep 0 inbound link |
| `/desk-preview` | `src/app/desk-preview/page.tsx:18` | **Preview-only, tự gate**: `notFound()` khi `NODE_ENV==='production' && VERCEL_ENV!=='preview'` — mock-data harness của portal "The Desk". Không link nội bộ. Giữ được (dev tool) nhưng là dead-weight với end-user. | `:16-18` + grep 0 inbound |
| `/velox-v4-preview` | `src/app/velox-v4-preview/page.tsx:21-23` | **Preview-only, gate bằng env** `NEXT_PUBLIC_ENABLE_VELOX_V4_PREVIEW !== '1'` → `notFound()`. Fixture LGR/OBJ tổng hợp cho engine Velox v4. Không link nội bộ. | `:21-23` + grep 0 inbound |
| `/account/trash` | `src/app/account/trash/page.tsx` | **Orphan-candidate (sống nhưng không ai trỏ tới)**: page hoạt động thật (restore workspace 30 ngày) nhưng grep toàn `src/` không thấy href nào tới `/account/trash`. Cần thêm entry-point hoặc xác nhận chủ đích. | grep `account/trash` chỉ match chính page |
| `/[workspaceId]/admin/members` | `src/app/[workspaceId]/admin/members/page.tsx:13` | Không dead — **redirect stub chủ đích** sang `profile-members` (giữ bookmark + revalidatePath). | Comment `:4-10` |
| `/workspace`, `/workspaces`, `/profile`, `/profile-selection` | `next.config.ts:34-47` | ⚠️ Redirect config trỏ `/workspaces → /workspace` và `/profile-selection → /profile` nhưng **không tồn tại page `/workspace` hay `/profile` nào trong `src/app`** → đích redirect là 404. `WorkspaceSettingsPanel` sau khi xóa workspace còn `router.push('/workspace')` (ghi chú tại `src/app/[workspaceId]/mc/settings/page.tsx:7-8`) → user rơi vào 404. | next.config + glob không có 2 page đó |
| `/download/*`, `/extract/*` | `src/middleware.ts:40-42` | Path cũ bị chặn chủ đích: middleware rewrite về 404. | `:40-42` |

## 7. Ghi chú tổng hợp

- **56 page routes** chia 5 khu: public (8) · account (2) · app nội bộ `/[workspaceId]` (dashboard 6, admin 18, team 5, mc 21, gốc + task 3) · share portal (1) · guest review (1) — cộng 3 route preview/dead.
- Chỉ **4 page là Client Component** thực thụ: `/login`, `/signup`, `/forgot-password`, `/portal-notify/unsubscribe`. Toàn bộ còn lại là server component mỏng mount client component.
- Hai "phiên bản UI" song song có chủ đích: `/admin/**` (Giao diện 1) và `/mc/**` (Giao diện 2 Mission Control) — cả hai đều live, `/mc` được link từ `AppSidebar.tsx:427`; KHÔNG phải dead-code, nhưng là 21 màn duplicate về chức năng (đã reuse component gốc).
- Route review nằm ở `/[workspaceId]/team/**` (đã dời KHỎI `/admin` theo review-fixes P1 — `team/layout.tsx:1-6`), gate membership chứ không gate admin.
- CLIENT role (ProfileAccess) bị đá khỏi TOÀN BỘ `/[workspaceId]/**` tại `src/app/[workspaceId]/layout.tsx:128-131` — khách chỉ dùng `/share/[token]` và `/r/[slug]`.

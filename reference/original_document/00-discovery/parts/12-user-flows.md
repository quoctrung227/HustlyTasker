# 12 — Danh sách User Flows toàn hệ thống (Discovery cho Phase 1 vẽ diagram)

> Nguồn: đọc trực tiếp `src/app/**` (67 page.tsx, 102 route.ts), `src/actions/*` (57 file action), `prisma/schema.prisma`. Mọi vị trí đều là đường dẫn tương đối từ repo root + số dòng thật tại thời điểm audit.

## 0. Actor của hệ thống

| Actor | Cách vào | Ghi chú |
|---|---|---|
| **Admin** (OWNER/ADMIN profile) | `/[workspaceId]/admin/*` (GĐ1) hoặc `/[workspaceId]/mc/*` (Mission Control) | Cả 2 shell cùng mounted, dùng chung actions; MC tự gate bằng `verifyProfileAdminAccess` (`src/app/[workspaceId]/mc/page.tsx:61`) |
| **Staff / Editor** (USER) | `/[workspaceId]/dashboard/*`, `/[workspaceId]/team/*`, `/[workspaceId]/task/[taskId]` | Middleware chặn session thiếu profile (`src/middleware.ts:96-98`) |
| **Client portal** | `/share/[token]` — token, không cần account | `src/app/share/[token]/page.tsx:24` |
| **Guest reviewer** | `/r/[slug]` — share link review, không cần account | `src/app/r/[slug]/page.tsx:9-12` |
| **Hệ thống** | Vercel Cron (`src/app/api/cron/*`), webhook Mux (`src/app/api/webhooks/mux/route.ts:50`), Inngest (`src/app/api/inngest/route.ts`, `src/lib/review/inngest.ts:751`) | Không có UI |

---

## 1. DANH SÁCH 16 FLOW CHÍNH

⭐ = thuộc nhóm 5 flow QUAN TRỌNG NHẤT (mục 3).

### F01 — Auth: signup → verify OTP email → login (password / Google) → forgot password
| Mục | Nội dung |
|---|---|
| Actor | Tất cả user nội bộ |
| Entry UI | `src/app/signup/page.tsx`, `src/app/login/page.tsx` (gọi `loginAction` — `src/app/login/page.tsx:4`), `src/app/forgot-password/page.tsx` |
| Endpoint/Action | `src/app/api/auth/signup/route.ts:16` · `src/app/api/auth/verify-otp/route.ts:11` · `src/actions/auth-actions.ts:168` (loginAction), `:404` (logoutAction) · Google OAuth: `src/app/api/auth/google/authorize/route.ts:14` + `callback/route.ts:27` · Forgot: `src/app/api/auth/forgot-password/route.ts:12`, `src/app/api/auth/reset-password/route.ts:12`, `src/actions/password-reset-actions.ts:65,178,293` |
| Model chính | `User`, `Session`, `EmailVerificationToken`, `PasswordResetOTP`, `LoginAttempt` |
| Mô tả | User đăng ký, xác thực email bằng OTP, đăng nhập bằng mật khẩu hoặc Google, và tự reset mật khẩu qua OTP email. |

### F02 — Chọn / switch Profile & Workspace (+ tạo workspace tháng mới)
| Mục | Nội dung |
|---|---|
| Actor | Admin, Staff |
| Entry UI | `src/app/welcome/page.tsx` (first-time profile — `src/app/welcome/WelcomeClient.tsx:18`), switcher `src/components/layout/ProfileWorkspaceSwitcher.tsx`, redirect gốc `src/app/[workspaceId]/page.tsx:29` |
| Endpoint/Action | `src/actions/profile-actions.ts:36` (selectProfile), `:53`, `:94` · `src/app/api/profile/select/route.ts:6` · `src/app/api/workspace/first/route.ts` · `src/actions/workspace-actions.ts:12` (createWorkspaceAction), `:134`, `:383` (createNextMonthWithRollover) |
| Model chính | `Profile`, `Workspace`, `WorkspaceMember`, `ProfileAccess` |
| Mô tả | Sau login user chọn profile (team) rồi workspace (tháng); admin tạo workspace tháng mới có rollover task từ tháng cũ. |

### F03 — Mời thành viên vào workspace + cross-team access
| Mục | Nội dung |
|---|---|
| Actor | Admin (mời/duyệt), Staff (nhận/chấp nhận) |
| Entry UI | `src/app/[workspaceId]/admin/members/page.tsx`, `src/app/[workspaceId]/admin/profile-members/page.tsx` |
| Endpoint/Action | `src/actions/member-actions.ts:303` (inviteToWorkspace), `:617` (accept), `:937` (decline), `:1054` (changeRole), `:1132` (remove), `:1247` (leave) · `src/actions/create-user.ts:17` (createUser) · `src/actions/cross-team-actions.ts:11` (requestCrossTeamAccess), `:94` (approve), `:137` (reject) |
| Model chính | `WorkspaceInvitation`, `WorkspaceMember`, `ProfileAccess`, `ProfileAccessRequest` |
| Mô tả | Admin mời user (có sẵn hoặc tạo mới) vào workspace; user cross-team xin quyền vào profile khác và admin duyệt. |

### F04 ⭐ — Task lifecycle: tạo (đơn / Velox batch) → giao → editor làm → duyệt → hoàn thành
| Mục | Nội dung |
|---|---|
| Actor | Admin (tạo/giao/duyệt), Staff-editor (nhận/làm/nộp) |
| Entry UI | Admin dashboard `src/app/[workspaceId]/admin/page.tsx:360` (DashboardActionWrapper → AddTaskModal) và MC `src/app/[workspaceId]/mc/add/page.tsx:12` (McAddScreen); editor: `src/app/[workspaceId]/dashboard/tasks/page.tsx`; chi tiết task: `src/app/[workspaceId]/task/[taskId]/page.tsx` (+ modal chặn `src/app/[workspaceId]/@modal/(.)task/[taskId]/page.tsx`) |
| Endpoint/Action | Tạo đơn: `src/actions/admin-actions.ts:85` (createTask, gọi từ `src/components/dashboard/DashboardActionWrapper.tsx:384`) · Velox batch: `src/actions/velox-batch-actions.ts:102` (createTasksFromBatch, gọi từ `DashboardActionWrapper.tsx:290,353`) + Multi-Hook Map `src/actions/raw-footage-actions.ts:215` (saveRawFootageMap), `:351` (saveHookGraph) · Giao: `src/actions/task-management-actions.ts:118` (assignTask), sửa `:35`, xoá `:12` · Đổi trạng thái: `src/actions/task-actions.ts:17` (updateTaskStatus) · Sửa chi tiết: `src/actions/update-task-details.ts` |
| Model chính | `Task`, `TaskRawFootage`, `PerformanceMetric` |
| Mô tả | Vòng đời cốt lõi: admin tạo task (1 task hoặc batch Velox từ scan folder), giao editor, editor đổi trạng thái theo pipeline tự do (string status), admin duyệt tới hoàn thành — là nguồn dữ liệu cho payroll. |

### F05 — Marketplace: editor tự claim task
| Mục | Nội dung |
|---|---|
| Actor | Staff-editor (claim/return), Admin (bật/tắt chợ) |
| Entry UI | `MarketplaceProvider` mounted toàn app tại `src/app/[workspaceId]/layout.tsx`; panel `src/components/marketplace/TaskMarketplace.tsx:216` (gọi claimTask) |
| Endpoint/Action | `src/actions/claim-actions.ts:34` (toggleMarketplace), `:67` (getMarketplaceTasks), `:128` (claimTask), `:213` (returnTask) |
| Model chính | `Task` |
| Mô tả | Admin thả task chưa giao lên "chợ", editor tự claim nhận việc hoặc trả lại. |

### F06 ⭐ — Review module: upload bản dựng (Tệp/Team browser + trong task)
| Mục | Nội dung |
|---|---|
| Actor | Staff-editor, Admin |
| Entry UI | Browser Tệp: `src/app/[workspaceId]/team/(browser)/page.tsx` + `folder/[folderId]/page.tsx` (TeamBrowser — `src/components/review/TeamBrowser.tsx:60` dùng uploadEngine); trong task: `src/components/review/TaskReviewUploadSection.tsx:32` (mounted qua `src/components/tasks/detail-sections/TaskMainSection.tsx`) |
| Endpoint/Action | `src/app/api/review/uploads/initiate/route.ts:28` → S3 multipart R2 → `.../[uploadSessionId]/complete/route.ts:22` (abort `:15`) · upload gắn task: `src/app/api/review/task-upload/initiate/route.ts:22` (client engine: `src/lib/review/upload-engine.ts:46`) · encode: webhook Mux `src/app/api/webhooks/mux/route.ts:50` → Inngest `src/lib/review/inngest.ts:341` (reviewProcessUpload), `:259` (reviewMuxWebhook), serve tại `src/app/api/inngest/route.ts` |
| Model chính | `ReviewFolder`, `ReviewAsset`, `ReviewVersion`, `UploadSession`, `WebhookEvent` |
| Mô tả | Editor upload bản dựng (multipart lên R2), hệ thống đẩy qua Mux encode và Inngest cập nhật trạng thái playback — thay thế frame.io. |

### F07 ⭐ — Review module: team review player + status machine + gửi khách
| Mục | Nội dung |
|---|---|
| Actor | Admin, Staff-editor |
| Entry UI | Player: `src/app/[workspaceId]/team/asset/[assetId]/page.tsx:4` (ReviewPlayerShell); bản MC: `src/app/[workspaceId]/mc/asset/[assetId]/page.tsx`, `mc/tep/page.tsx:11` (bọc lại TeamBrowser thật) |
| Endpoint/Action | Đổi status: `src/app/api/review/assets/[id]/status/route.ts:18` (PUT) · duyệt gửi khách: `.../approve-send/route.ts:15` · xác nhận sửa xong: `.../confirm-fix/route.ts:15` · chốt feedback: `.../feedback-done/route.ts:13` · comment theo timecode: `src/app/api/review/versions/[id]/comments/route.ts:13,30` · resolve: `src/app/api/review/comments/[id]/resolve/route.ts:13` · tạo share link: `src/app/api/review/assets/[id]/share/route.ts:14`, `src/app/api/review/shares/route.ts:32` (revoke `shares/[id]/revoke/route.ts:18`) · chốt hoàn tất task: `src/app/api/review/tasks/[taskId]/confirm-complete/route.ts:13` |
| Model chính | `ReviewAsset` (status machine), `ReviewComment`, `ShareLink`, `ReviewActivity` |
| Mô tả | Team xem bản dựng trong player nội bộ, comment theo timecode + annotation, chạy state machine trạng thái video, rồi phát hành link `/r/` cho khách. |

### F08 ⭐ — Guest reviewer `/r/[slug]`: xem → comment → approve / request-changes → đồng bộ task
| Mục | Nội dung |
|---|---|
| Actor | Guest reviewer (khách, không account) |
| Entry UI | `src/app/r/[slug]/page.tsx` (gate password/identity: `GateScreens`, app: `GuestReviewApp`) |
| Endpoint/Action | Snapshot: `src/app/api/r/[slug]/route.ts:18` · unlock password: `.../unlock/route.ts:21` · khai danh tính: `.../identity/route.ts:35` · comment + attachment: `.../comments/route.ts:36`, `comment-attachments/initiate/route.ts:24` · playback: `.../playback-token/route.ts:29`, `versions/[versionId]/view-url/route.ts:23` · **quyết định approve/request-changes: `.../decision/route.ts:34`** → Inngest `src/lib/review/inngest.ts:657` (reviewShareDecision — đồng bộ status asset + task + email) · đăng ký notify qua PIN email: `.../notifications/request-pin/route.ts:47`, `verify-pin/route.ts:25`, unsubscribe `src/app/api/r/unsubscribe/route.ts:17` |
| Model chính | `ShareLink`, `GuestSession`, `ReviewComment`, `GuestEmailVerification`, `GuestSubscription` |
| Mô tả | Khách mở link, xem video, comment theo timecode/vẽ annotation, bấm Approve hoặc Request changes — quyết định được Inngest lan truyền về status asset + task + email cho team. |

### F09 ⭐ — Client portal `/share/[token]`: theo dõi task, duyệt deliverable, gửi yêu cầu, xem invoice
| Mục | Nội dung |
|---|---|
| Actor | Client portal (khách theo token) |
| Entry UI | `src/app/share/[token]/page.tsx:24` (getShareSnapshot → `SharePortalClient` — `src/components/portal/share/SharePortalClient.tsx:49` gọi approve) |
| Endpoint/Action | Snapshot: `src/actions/share-portal-actions.ts:165` · duyệt deliverable: `:765` (approveDeliverableViaToken), `:855` (bulk) · yêu cầu sửa: `:1011` (requestChangesViaToken) · chấm sao: `:1082` (submitRatingViaToken) · tạo task trực tiếp: `:1182` (createTaskViaToken) · gửi request intake: `:1350` (submitClientRequestViaToken) · comment 2 chiều: `:1703` (postCommentViaToken), feed `:1651` · notify email: `:582`, `:626`, unsubscribe `:684` (+ `src/app/api/portal-notify/unsubscribe/route.ts`) · tài liệu: `src/actions/share-document-actions.ts:461,466` · invoice PDF: `src/app/api/share/[token]/invoices/[id]/pdf/route.ts:51` · tải zip: `src/app/api/share/[token]/download-zip/route.ts` |
| Model chính | `ClientShareLink`, `Task`, `ClientTaskRequest`, `Rating`, `TaskComment`, `Invoice` |
| Mô tả | Khách xem tiến độ toàn bộ task của mình, approve/request-changes deliverable, tạo yêu cầu mới, chat với team và tải invoice — tất cả qua 1 token không cần account. |

### F10 — Client request → Admin inbox → chuyển thành task
| Mục | Nội dung |
|---|---|
| Actor | Client portal (gửi), Admin (xử lý) |
| Entry UI | Khách: form trong `/share/[token]`; Admin: `src/app/[workspaceId]/admin/requests/page.tsx:1-2` (RequestsInbox), MC: `mc/requests/page.tsx` |
| Endpoint/Action | Gửi: `src/actions/share-portal-actions.ts:1350` · Admin: `src/actions/client-request-actions.ts:102` (acceptClientRequest → tạo task), `:171` (reject), đếm chưa đọc `:87` |
| Model chính | `ClientTaskRequest`, `Task` |
| Mô tả | Yêu cầu khách gửi từ portal rơi vào inbox admin; admin accept sẽ sinh task thật hoặc reject kèm ghi chú. |

### F11 — Task comments & mentions (nội bộ ↔ CLIENT visibility)
| Mục | Nội dung |
|---|---|
| Actor | Admin, Staff-editor (INTERNAL/CLIENT), Client portal (qua F09) |
| Entry UI | Task detail `src/app/[workspaceId]/task/[taskId]/page.tsx` (TaskDetailRoute) |
| Endpoint/Action | `src/actions/task-comment-actions.ts:244` (createTaskComment, visibility INTERNAL/CLIENT), `:302` (edit), `:333` (reaction), `:369` (assign comment), `:427` (resolve), `:482` (markRead), mention `:561` |
| Model chính | `TaskComment`, `TaskCommentReadState`, `TaskCommentReaction` |
| Mô tả | Chat ClickUp-style trong task: comment 2 tầng visibility, mention, giao comment như mini-task, resolve và đếm chưa đọc. |

### F12 — Notification: in-app + email digest + web push
| Mục | Nội dung |
|---|---|
| Actor | Tất cả user nội bộ (nhận), Hệ thống (phát) |
| Entry UI | `src/components/notifications/NotificationBell.tsx` (mounted trong `src/components/layout/AppHeader.tsx`, `DashboardTopBar.tsx`), panel gọi action tại `src/components/notifications/NotificationPanel.tsx:34` |
| Endpoint/Action | Phát: `src/actions/notification-actions.ts:24` (createNotificationInternal), `:86` (broadcast) · đọc: `:112`, `:176`, `:197` · preference: `:264` · push: `src/actions/push-actions.ts:18` (savePushSubscription) · email digest: `src/app/api/cron/send-digest/route.ts:11` · nhắc deadline: `src/app/api/cron/check-deadline/route.ts:14` · unsubscribe email: `src/app/api/notifications/unsubscribe/route.ts` |
| Model chính | `Notification`, `NotificationPreference`, `PushSubscription` |
| Mô tả | Mọi sự kiện (giao task, comment, review, deadline) sinh notification in-app, đẩy web push và gộp digest email theo giờ/ngày. |

### F13 ⭐ — Payroll: chốt lương editor + bonus tháng
| Mục | Nội dung |
|---|---|
| Actor | Admin (chốt/chi), Staff-editor (xem lương của mình) |
| Entry UI | `src/app/[workspaceId]/admin/payroll/page.tsx`; editor xem: `src/app/[workspaceId]/dashboard/salary/page.tsx`; MC: `mc/ho-so-thanh-toan`, `mc/tien` |
| Endpoint/Action | `src/actions/payroll-actions.ts:129` (getPayrollData), `:22` (confirmPayment), `:165` (revertPayment) · bonus: `src/actions/bonus-actions.ts:118` (calculateMonthlyBonus), `:63` (revert), lock `:38` · cấu hình: `src/actions/bonus-config-actions.ts` · QR nhận tiền: `src/actions/upload-actions.ts:53` (uploadPaymentQr) |
| Model chính | `Payroll`, `MonthlyBonus`, `PayrollLock`, `BonusConfig`, `Task` (đếm theo status) |
| Mô tả | Cuối tháng admin tính lương editor từ task hoàn thành (status-dependent — rủi ro số 1 của review-fixes), tính bonus, xác nhận đã chi và khoá sổ. |

### F14 — Finance: invoice khách + ghi nhận payment
| Mục | Nội dung |
|---|---|
| Actor | Admin |
| Entry UI | `src/app/[workspaceId]/admin/finance/page.tsx`; MC: `mc/hoa-don/page.tsx`, `mc/finance/page.tsx`, `mc/ho-so/page.tsx` (billing profile) |
| Endpoint/Action | `src/actions/invoice-actions.ts:215` (getUnbilledTasks), `:277` (preview), `:314` (createInvoiceRecord), `:581` (voidInvoice), billing profile `:64` · render PDF: `src/app/api/invoices/generate/route.ts:5`, tải `src/app/api/invoices/[id]/download/route.ts` · payment: `src/actions/payment-actions.ts:44` (recordPayment), `:139` (ledger) · xuất Excel: `src/app/api/exports/monthly-tasks-xlsx/route.ts` |
| Model chính | `Invoice`, `InvoiceItem`, `Payment`, `BillingProfile`, `Client` |
| Mô tả | Admin gom task chưa bill của 1 client thành invoice (PDF tiếng Anh), void khi cần, và ghi sổ payment thu từ khách. |

### F15 — CRM: quản lý client/sub-client + phát hành share link portal
| Mục | Nội dung |
|---|---|
| Actor | Admin |
| Entry UI | `src/app/[workspaceId]/admin/crm/page.tsx`, chi tiết `crm/[id]/page.tsx`; MC: `mc/crm/page.tsx`, quản lý link `mc/shares/page.tsx` |
| Endpoint/Action | `src/actions/crm-actions.ts:113` (createClient), `:172` (createProject), `:461` (mergeClientIntoParent), `:260` (delete→trash), `:297` (restore) · share link: `src/actions/share-link-actions.ts:46` (createClientShareLink), `:91` (revoke) · contact: `src/actions/contact-actions.ts` · giá: `src/actions/price-template-actions.ts`, `src/actions/pricing-rule-actions.ts` |
| Model chính | `Client` (cây parent/sub), `Project`, `ClientShareLink`, `Contact`, `PriceTemplate`, `PricingRule` |
| Mô tả | Admin quản lý cây client/sub-client, hồ sơ giá, và cấp/thu hồi token portal `/share` cho từng client. |

### F16 — Hệ thống: cron + webhook + Inngest pipeline
| Mục | Nội dung |
|---|---|
| Actor | Hệ thống |
| Entry UI | Không có (Vercel Cron / webhook / Inngest) |
| Endpoint/Action | `src/app/api/cron/check-deadline/route.ts:14` (nhắc quá hạn) · `send-digest/route.ts:11` (digest email hàng giờ/ngày) · `auth-cleanup/route.ts:27` · `cleanup-notifications/route.ts:11` · `hard-delete-profiles/route.ts:20` + `hard-delete-workspaces/route.ts:20` (xoá cứng sau trash) · `review-janitor/route.ts:13` (+ Inngest `src/lib/review/inngest.ts:526`) · webhook Mux `src/app/api/webhooks/mux/route.ts:50`, webhook calendar `src/app/api/webhooks/calendar/route.ts` · 4 Inngest functions: `src/lib/review/inngest.ts:751` |
| Model chính | `Notification`, `ReviewVersion`, `WebhookEvent`, `Workspace`, `Profile`, `RateLimitBucket` |
| Mô tả | Nền tự động: encode video, gửi email/digest, nhắc deadline, dọn rác trash/OTP/notification theo lịch. |

---

## 2. FLOW PHỤ (có thật trong code, vẽ diagram mức phụ)

| # | Flow | Actor | Entry UI | Endpoint/Action chính | Model | Mô tả |
|---|---|---|---|---|---|---|
| P1 | Availability / lịch rảnh | Staff (khai), Admin (xem matrix) | `src/app/[workspaceId]/dashboard/schedule/page.tsx`, `admin/schedule/page.tsx`, `mc/lich/page.tsx` | `src/actions/availability-actions.ts:111` (saveMyAvailability), `:163` (matrix); rule: `src/actions/schedule-actions.ts:37`, exception `:119` | `ScheduleRule`, `ScheduleException`, `DailyAvailability` | Editor khai giờ rảnh theo tuần, admin xem matrix cả team để giao việc. |
| P2 | Integrations Drive/Dropbox scan (Velox V4) | Admin | Nút scan trong AddTaskModal / settings | OAuth: `src/app/api/integrations/google-drive/authorize/route.ts:5` + `callback/route.ts:23`, `dropbox/authorize/route.ts:5` + `callback/route.ts:19`; scan: `src/app/api/integrations/scan-folder/route.ts:58`; quản lý: `src/actions/integration-actions.ts:35,74` | `IntegrationToken` | Kết nối Drive/Dropbox rồi scan cây folder footage để prefill Velox batch. |
| P3 | Study Place (học/quiz nội bộ) | Staff, Admin | `src/app/[workspaceId]/admin/settings/page.tsx:102` → `src/components/workspace/WorkspaceSettingsPanel.tsx:194` (StudyPlaceBoard) | `src/actions/study-place-actions.ts:78` (review câu hỏi), `:148` (bookmark), `:201` (reset) | `StudyPlaceProgress` | Flashcard/quiz đào tạo nội bộ, lưu tiến độ từng user. |
| P4 | Leaderboard / reputation / analytics + presence | Admin (analytics), Staff (xem rank) | `src/app/[workspaceId]/dashboard/page.tsx` (Leaderboard), `admin/analytics/page.tsx` (+ `staff/[userId]`), `mc/analytics/page.tsx` | `src/actions/leaderboard-actions.ts:5`; `src/actions/reputation-actions.ts:3` (checkOverdueTasks); `src/actions/analytics-actions.ts:7,145`; tracking `src/actions/tracking-actions.ts:58,91,311` | `MonthlyRank`, `PerformanceMetric`, `ErrorLog`, `Event`, `UserPresence` | Xếp hạng editor theo tháng, chấm điểm lỗi/quá hạn, theo dõi presence realtime. |
| P5 | Impersonation admin | Admin | `src/components/admin/analytics/LivePresenceBoard.tsx` (admin analytics + `mc/analytics/page.tsx`) | `src/actions/impersonation-actions.ts:9` (startImpersonation), `:109` (stop) | `Session` | Admin "nhập vai" user để xem đúng những gì user thấy, có audit. |
| P6 | Trash & restore (task/client/workspace/profile) | Admin | `admin/cancelled/page.tsx`, `admin/client-trash/page.tsx`, `admin/profile-trash/page.tsx`, `mc/trash/page.tsx`, `src/app/account/trash/page.tsx`; review trash: `team/(browser)/trash/page.tsx` | `src/actions/task-actions.ts:509,553`; `src/actions/crm-actions.ts:297,417`; `src/actions/workspace-actions.ts:279,327`; `src/actions/profile-actions.ts:429`; review: `src/app/api/review/trash/restore/route.ts:18`, `purge/route.ts:18` | `Task`, `Client`, `Workspace`, `Profile`, `ReviewFolder/Asset` | Xoá mềm mọi thực thể chính, restore trong hạn, cron xoá cứng (F16). |
| P7 | Audit log & error dictionary | Admin | `admin/audit-log/page.tsx`, `mc/audit/page.tsx`, `dashboard/errors/page.tsx` | `src/actions/audit-actions.ts`; log lỗi client: `src/app/api/log-client-error/route.ts` | `AuditLog`, `ErrorDictionary`, `ErrorLog` | Tra vết hành động nhạy cảm và từ điển lỗi editor. |
| P8 | Cài đặt profile/user (avatar, đổi mật khẩu, tags, global settings) | Admin, Staff | `dashboard/profile/page.tsx`, `admin/settings/page.tsx`, `admin/menu/page.tsx`, `mc/settings/page.tsx` | `src/actions/profile-actions.ts:183,319,508`; `src/actions/upload-actions.ts:120,210,257`; `src/actions/tag-actions.ts`; `src/actions/global-settings.ts` | `Profile`, `User`, `TagCategory`, `TaskTag` | Quản lý hồ sơ cá nhân, branding profile, tag và cài đặt chung. |

---

## 3. CHỐT: 5 FLOW QUAN TRỌNG NHẤT (ưu tiên vẽ + audit sâu ở Phase 1)

| Ưu tiên | Flow | Lý do (theo code) |
|---|---|---|
| 1 | **F04 Task lifecycle** | Trục xương sống: mọi module khác (payroll F13, portal F09, review F06-F08, marketplace F05) đều đọc/ghi `Task.status` — status là string tự do (`src/actions/task-actions.ts:17`), sai 1 status là lệch tiền lương. |
| 2 | **F08 Guest `/r/` decision** | Điểm chốt doanh thu với khách: `decision/route.ts:34` → Inngest `reviewShareDecision` (`src/lib/review/inngest.ts:657`) lan truyền ngược về asset + task + email — flow bất đồng bộ nhiều bước nhất hệ thống. |
| 3 | **F07 Team review + status machine** | State machine `ReviewAsset` (status/approve-send/confirm-fix/feedback-done) là "nguồn sự thật" hợp nhất 2 luồng approve (quyết định review-fixes), portal chỉ là view. |
| 4 | **F09 Client portal `/share`** | Bề mặt public token-based lớn nhất (~20 action trong `share-portal-actions.ts`, từ approve tiền tới tạo task), không cần account → rủi ro authz cao nhất. |
| 5 | **F13 Payroll** | Đụng tiền thật của editor; `SALARY_PENDING_STATUSES` phụ thuộc tập status task (quy tắc cứng trong CLAUDE.md review-fixes: đếm thiếu = trả thiếu lương). |

*(F06 upload + F16 hệ thống là hạ tầng của #2-#3, vẽ chung trong cụm diagram review.)*

---

## 4. GHI CHÚ 2 PHIÊN BẢN / DEAD-CODE CANDIDATES

| Hiện tượng | Bằng chứng | Kết luận |
|---|---|---|
| **2 shell admin song song**: GĐ1 `/[workspaceId]/admin/*` và Mission Control `/[workspaceId]/mc/*` (21 trang) | `src/app/[workspaceId]/mc/page.tsx:61` tự gate admin; `mc/tep/page.tsx:1,11` bọc lại `TeamBrowser` thật; `DashboardActionWrapper.tsx:8` import cả `McAddTaskModal` | CẢ HAI đang mounted và routable — không phải dead code; MC tái dùng chung actions/components với GĐ1. Diagram Phase 1 chỉ cần vẽ 1 lần theo action, ghi chú 2 entry UI. |
| Trang preview dev | `src/app/desk-preview/page.tsx:6-7` ("DEV-ONLY... Gated out of production"), `src/app/velox-v4-preview/page.tsx:1-7` ("Dev-only preview"), `src/app/diagnostic/page.tsx` | Không phải user flow production — loại khỏi diagram. |
| Route one-off / debug | `src/app/api/import-jan-2026/route.ts:5-6` ("FROZEN... one-off importer"), `src/app/api/test-email/route.ts:1-5` ("DELETE after debugging") | Dead-code candidate — đánh dấu để dọn. |
| 2 đường comment cho khách | Task-comment CLIENT visibility (`task-comment-actions.ts:244`) và portal comment (`share-portal-actions.ts:1703`) cùng ghi `TaskComment` | Cùng 1 model, 2 entry — không phải trùng lặp code nhưng cần vẽ chung 1 luồng. |
| 2 luồng approve của khách | Portal `approveDeliverableViaToken` (`share-portal-actions.ts:765`) và review `/r/` decision (`api/r/[slug]/decision/route.ts:34`) | Theo docs/review-fixes: hợp nhất về review module làm nguồn sự thật, portal là VIEW — diagram phải thể hiện quan hệ này. |

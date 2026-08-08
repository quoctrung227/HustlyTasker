# PHASE 3 — TRẠNG THÁI: Objects, Components, Buttons

> Tài liệu master. Bảng chi tiết đầy đủ (mỗi dòng kèm file:line) trong `parts/`:
> - [`parts/s1-domain-states.md`](parts/s1-domain-states.md) — trạng thái mọi entity có vòng đời
> - [`parts/s2-component-states.md`](parts/s2-component-states.md) — 34 component chính, bảng default/hover/loading/disabled/error/empty/success
> - [`parts/s3-buttons-actions.md`](parts/s3-buttons-actions.md) — các nút hành động chính: điều kiện enable/disable, state submit, hiển thị lỗi

## 1. Object/domain states — kết luận chính (chi tiết s1)

- **`Task.status` có đúng 13 giá trị canonical** (`TASK_STATUS_META` — `src/lib/task-statuses.ts:84-109`) + 25 transition T1-T25 được lập bảng (role, hàm, side effects payroll/email/portal). Derive: `SALARY_PENDING_STATUSES` = 10 giá trị, `SALARY_COMPLETED_STATUS` = `"Hoàn tất"`, `OVERDUE_ELIGIBLE_STATUSES` = 5 giá trị.
- **FSM tay của Task đã TẮT chủ đích** (`validateTransition` luôn trả `isValid:true` — `src/lib/fsm-config.ts:122-125`); hàng rào thật là RBAC trong `updateTaskStatus` (`task-actions.ts:68-97`: chỉ admin vào/ra terminal + cấm non-admin set status client-facing) và guard auto-transition `STATUS_TRANSITIONS` (`task-statuses.ts:199-218`) áp cho Inngest/webhook/guest.
- **3 đường "đụng tiền" vào `Hoàn tất`**: admin tay (T11), staff confirm từ banner review (T22 `confirmTaskHoanTat`), khách portal approve (T23 `approveDeliverableViaToken` — `share-portal-actions.ts:792-810`). Guest `/r/` approve KHÔNG đổi task status — chỉ set asset `statusId='Hoàn tất'` + `clientReview='APPROVED'`, chờ staff xác nhận.
- **Review module có 3 trục trạng thái độc lập**: `ReviewVersion.pipelineStatus` (UPLOADING→UPLOADED→PROCESSING→READY|FAILED, FAILED terminal), `ReviewVersion.reviewState` (DRAFT→AWAITING_REVIEW→APPROVED⇄CHANGES_REQUESTED, latest-wins), `ReviewAsset.statusId` (mirror động bộ status task — không có bộ riêng, `src/lib/review/status.ts:1-6`).
- **R5 an toàn phơi khách**: bản dựng mới thành head khi task đang phơi khách → TỰ ĐỘNG revoke ShareLink + kéo task A5/A6/A7 về A2 + null clientReview (`task-sync.ts:452-503`).
- 15+ entity còn lại có bảng đầy đủ: WorkspaceInvitation (PENDING→ACCEPTED/DECLINED/REVOKED/EXPIRED-lazy), UploadSession (timestamp-derived), Invoice (thực tế chỉ SENT→PAID→VOID), Payment (append-only), Payroll (∅→PAID; revert = DELETE row; chặn bởi PayrollLock), ClientTaskRequest, Client (ACTIVE/SOFT_DELETED/TRASHED; MERGED chỉ script migration ghi), Workspace/Profile (soft-delete 30d + cron hard-delete), GuestSession/PIN, OTP/token, Notification.
- **5 giá trị enum "chết"** không code nào ghi: `Invoice.DRAFT` + `OVERDUE`, `ClientRequestStatus.REVIEWING`, `Workspace.SUSPENDED`, `Client.MERGED` (trong app).

## 2. UI component states — kết luận chính (chi tiết s2)

- Repo có **3 thế hệ pattern state song song**: GĐ1 tables `await + window.location.reload()` không loading (`NewDesktopTaskTable.tsx:183,200,757`) → mid-gen toast + `router.refresh()` nhưng vứt isPending → review module đầy đủ loading/error/empty/optimistic-rollback (`TeamBrowser.tsx`).
- **Optimistic update chỉ tồn tại 4 chỗ** (TeamBrowser status chip + rollback, Marketplace claim + rollback, NotificationItem fire-and-forget, useComments SWR) — toàn bộ bảng task KHÔNG optimistic (trái quy tắc `.claude/CLAUDE.md`).
- `ui/button.tsx` KHÔNG có loading prop → ≥10 kiểu spinner tự chế; `ui/input.tsx` không có error state ở base.
- **4 kênh báo lỗi khác nhau đang sống**: sonner toast (đa số), `alert()` native (`CommentComposer.tsx:293`), toast tự viết aria-live trong iframe portal (`GuestReviewApp.tsx:373-377`), inline error (GateScreens, DeliverableSheet).
- Nuốt lỗi im lặng: NotificationBell/Panel, ProfileWorkspaceSwitcher (không .catch → switcher biến mất khi action lỗi).
- Bug đúng/sai: `deleteTask` đơn lẻ KHÔNG check `res.error` ở cả 2 bảng desktop — server lỗi vẫn toast.success rồi reload (`NewDesktopTaskTable.tsx:181-182`, `TaskWorkflowTabs.tsx:208-209`).

## 3. Buttons/actions — kết luận chính (chi tiết s3)

- Bảng đầy đủ nút chính theo 16 flow: điều kiện enable/disable thật, state submit, hiển thị lỗi, optimistic hay chờ server.
- Finding xuyên suốt: (1) nút đụng tiền/phân quyền **nuốt message lỗi server** (PaymentModal toast generic mất message PAYROLL_LOCKED — `PaymentModal.tsx:45` vs `payroll-actions.ts:52`; AssigneeCell; Impersonate console.error không toast); (2) 3 chỗ còn dùng `confirm()` native trong khi MC có ConfirmModal riêng; (3) điều kiện enable phía client ở review module LUÔN hẹp hơn hoặc bằng server (FSM `canAutoTransition` chạy 2 đầu — đúng hướng, server là nguồn sự thật); (4) nút "Tạo task" footer không validate client-side (chỉ chặn double-submit) — lỗi thiếu dữ liệu chỉ biết sau round-trip.

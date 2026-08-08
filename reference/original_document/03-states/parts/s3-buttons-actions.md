# S3 — Nút hành động chính: enable/disable, trạng thái submit, lỗi, optimistic

> Phase 3 §3. Đi theo 16 flow trong `00-discovery/parts/12-user-flows.md`. Mọi điều kiện dưới đây đọc TRỰC TIẾP từ code (không suy đoán); vị trí là `file:line` thật tại thời điểm audit 2026-08-02. Ký hiệu cột **Optimistic**: `CHỜ` = chờ server rồi mới đổi UI (thường kèm `router.refresh()`), `OPT` = đổi UI trước, rollback khi lỗi.

## 0. Mẫu chung của repo (đọc trước khi xem bảng)

| Mẫu | Nơi dùng | Ghi chú |
|---|---|---|
| `useState busy/submitting` + `disabled={busy}` + `Loader2 animate-spin` | Đa số modal (PaymentModal, RecordPaymentModal, ShareLinkSection, InviteToProfileModal, AddTaskModal, ReviewFlowActions…) | Mẫu chuẩn của app |
| `useActionState` / `useTransition` | Chỉ ở auth (login `src/app/login/page.tsx:10`, signup `src/app/signup/page.tsx:35`), PayrollCard revert, MarketplaceToggle, LivePresenceBoard | Không phổ biến như busy-flag thủ công |
| Optimistic + rollback | CHỈ 4 chỗ: claim marketplace, kanban MC, toggle chợ, status chip asset review | Phần còn lại đều CHỜ server |
| `confirm()` native của browser | Revert lương (`PayrollCard.tsx:48`), void invoice (`ClientInvoicesTable.tsx:27`), thu hồi share link (`ShareLinkSection.tsx:80`) | MC dùng ConfirmModal riêng (`RecordPaymentModal.tsx:71` khi `confirmOnDelete`) |
| Lỗi = `toast.error(res.error)` (sonner) | Gần như toàn bộ UI nội bộ | Ngoại lệ đáng chú ý ở §12 (nuốt message server) |
| Trang khách (portal/guest) KHÔNG dùng sonner | `DeliverableSheet` dùng `setErr` inline (`:197`), GuestReviewApp tự viết toast state (`GuestReviewApp.tsx:373-385`, z-120 `:778-791`) | Toast guest từng bị chìm dưới modal — đã fix bằng z-index |

---

## 1. F01 — Đăng nhập / Đăng ký

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Đăng nhập** | `src/app/login/page.tsx:131-144` | `loginAction` — `src/actions/auth-actions.ts:168` (form action qua `useActionState` `:10`) | `disabled={isPending}` (`:133`); input email/password `required` HTML | Spinner `Loader2` + text đổi «Đang xử lý…» (`:136-139`), opacity 60% | Box đỏ trên form hiển thị `state?.error` hoặc `urlError` từ `?error=google…` (`:53-57`, `:20-26`). Không auto-retry | CHỜ (redirect server-side khi thành công; hidden field `next` chống open-redirect `:41`) |
| **Tiếp tục với Google** | `src/components/auth/GoogleSignInButton.tsx:20-28` | Anchor thuần `GET /api/auth/google/authorize` (`src/app/api/auth/google/authorize/route.ts:14`) | Không có disable — là thẻ `<a>`, không JS | Không có pending state (browser navigate) | Lỗi quay về `/login?error=google` / `google_unverified` → box đỏ ở login (`login/page.tsx:22-24`) | CHỜ (OAuth redirect) |
| **Đăng ký** | `src/app/signup/page.tsx:269-273` | `fetch POST /api/auth/signup` trong `startTransition` (`:47-49`) → `src/app/api/auth/signup/route.ts:16` | `disabled={isPending}` (`:269`) | Spinner + «Đang tạo tài khoản…» (`:272-273`) | Lỗi tổng `setError` (`:120-127`) + lỗi từng field `fieldErrors` (`:59-60`); có nhánh lỗi bot-detection BotID/turnstile (`:262`) | CHỜ |

## 2. F04 — Tạo task (đơn + Velox batch)

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Tạo task** (footer wizard bước 5) | `src/components/dashboard/AddTaskModal.tsx:1700-1710` | `handleSubmit` (`:892-938`) → `DashboardActionWrapper.handleSubmit` (`src/components/dashboard/DashboardActionWrapper.tsx:148`) → route 3 nhánh: `createTask` (`src/actions/admin-actions.ts:85`), `createTasksFromBatch` (`src/actions/velox-batch-actions.ts:102`), `createBatchTasks` (`src/actions/bulk-task-actions.ts`) | `disabled={submitting}` (`:1706`) — footer **không** validate field (chỉ server); nút X đóng modal cũng bị block khi `submitting` (`:1615-1623`), toggle Velox cũng `disabled={submitting}` (`:1588`) | Text đổi «Đang thêm...» (`:1709`), opacity 50% | `catch` → `toast.error(err?.message)` (`:933`); guard desync Velox batch throw lỗi to (số dòng video ≠ số link — `DashboardActionWrapper.tsx:312-321`); Multi-Hook Map lưu thất bại → task VẪN tạo, toast riêng báo map mất (`:81-94`, `:389-399`) | CHỜ; sau thành công `startTransition(router.refresh)` (`:433-435`), form reset + màn success (`:920-931`) |
| **Quét Velox** (quick mode) | `AddTaskModal.tsx:482-510` | `POST /api/integrations/scan-folder` (`src/app/api/integrations/scan-folder/route.ts:58`) | Chặn khi chưa dán link folder → `toast.error('Dán link folder…')` (`:492`) | (trong QuickCreateMode) | `toast.error(body?.error \|\| 'Quét lỗi (HTTP …)')` (`:503`, `:510`) | CHỜ |

## 3. F04 — Giao task (assign)

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Chọn assignee** (dropdown cell) | `src/components/tasks/cells/AssigneeCell.tsx:98-136`, item `:244-262` | `assignTask` — `src/actions/task-management-actions.ts:118`; bulk: `bulkAssignTasks` (`src/actions/bulk-task-actions.ts`, dynamic import `:115`) | Chỉ admin thấy dropdown (non-admin read-only `:139-149`); bulk ≥2 task đang chọn → ConfirmModal «Giao hàng loạt» (`:107-114`) | **KHÔNG có pending state** — dropdown đóng ngay (`:100`), không spinner, không disable | Single: `toast.error("Giao task thất bại")` **generic, nuốt message server** (`:134`); bulk: `toast.error(res.error)` thật (`:117`) | CHỜ + `router.refresh()` (`:121`, `:132`) |

## 4. F04 — Đổi trạng thái task (3 bề mặt)

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Dropdown status** (bảng admin) | `src/components/tasks/cells/StatusCell.tsx:132-147` | `updateTaskStatus` — `src/actions/task-actions.ts:17` (kèm `task.version` optimistic-lock `:69`) | Admin: full 13 status (`:143`); USER chỉ có nút «▶ Bắt đầu» khi status=`Nhận task` (`:100-108`), còn lại badge read-only; chọn `Revision` (admin) mở dialog phân loại INTERNAL/CLIENT trước (`:63-66`) | **KHÔNG có busy state** — Select không disable trong lúc gọi, có thể chọn tiếp (double-fire được) | `toast.error(result.error)` (`:71`) hoặc generic «Cập nhật trạng thái thất bại» (`:77`); dialog Revision: nút «Gửi Revision» (`:210`) cũng không busy | CHỜ + `router.refresh()` (`:75`) — Select vẫn hiện status cũ tới khi refresh xong |
| **Kéo-thả kanban** (Mission Control) | `src/components/mission-control/McKanban.tsx:182-221` | `updateTaskStatus` (`:207`) — cùng action với dropdown (ghi chú «MONEY-SAFE» `:13-16`) | Cột «Quá hạn» không có `entryStatus` → thả vào bị chặn + `toast.info` giải thích (`:190-193`); kéo cần di ≥8px (sensor `:168`); thả về đúng cột cũ = no-op (`:195`) | Card nhảy cột NGAY (optimistic move `:197-204`) | Lỗi/throw → `setCols(prev)` snap-back + `toast.error` + `router.refresh()` re-sync (`:208-220`) | **OPT + rollback** |
| **Status chip asset review** (Tệp browser) | `src/components/review/StatusControl.tsx:107-114` (trigger `disabled` prop), caller `src/components/review/TeamBrowser.tsx:888-922` | `apiSetAssetStatus` (`src/lib/review/team-actions.ts:167`) → `PUT /api/review/assets/[id]/status` (`route.ts:18`) | `disabled` prop từ host; no-op nếu chọn lại status cũ (`StatusControl.tsx:101`, `TeamBrowser.tsx:891`) | Chip đổi màu NGAY; guard `pendingStatusRef` chống refresh ngầm ghi đè (`:895`) | Rollback chip về status cũ + `toast.error` (`:911-916`); gửi kèm `rowVersion` — người khác đổi trước thì server từ chối (optimistic-lock) | **OPT + rollback + rowVersion** |

## 5. F05 — Marketplace: Claim / Return / Toggle

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Claim task** (kéo card thả bất kỳ đâu) | `src/components/marketplace/TaskMarketplace.tsx:209-241` (drop zone full-screen `:34-146`) | `claimTask` — `src/actions/claim-actions.ts:128` | Client: drag bị chặn khi chợ đóng (`onDragStart` return sớm `:230-233`); Server (điều kiện THẬT, trong transaction): member workspace (`:141-149`), `marketplaceOpen` check TRONG transaction chống TOCTOU (`:156-163`), task chưa archived, `assigneeId` null, status đúng `Đang đợi giao` (`:170-177`), update theo `version` chống race (`:180-198`) | Card biến khỏi lưới NGAY (`:214`); poll list 10s (`:197`) | Rollback card về lưới + `toast.error(res.error)` (`:217-221`) — message server chi tiết («Task đã được nhận bởi người khác», «Phiên chợ hiện đang đóng»…) | **OPT + rollback** |
| **Trả lại task** (menu ⋮ ở bảng task) | `src/components/TaskWorkflowTabs.tsx:896-920` | `returnTask` — `src/actions/claim-actions.ts:213` | Item CHỈ render khi `claimSource==='MARKET'` && `claimedAt` hợp lệ && **≤10 phút** kể từ claim (`:897-904`) — quá 10 phút nút biến mất | Không pending state | `toast.error(res.error)` (`:910`); thành công → toast + **`window.location.reload()`** (`:912-914`, full reload chứ không refresh) | CHỜ |
| **Mở/Đóng chợ** (admin) | `src/components/marketplace/MarketplaceToggle.tsx:18-38` | `toggleMarketplace` — `src/actions/claim-actions.ts:34` | `disabled={isPending}` (`:37`) | Pill đổi trạng thái NGAY (`:20-21`) | Revert state + `toast.error` (`:25-28`) | **OPT + rollback** |

## 6. F06 — Upload bản dựng

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Chọn/thả file** (drawer task) | `src/components/review/TaskReviewUploadSection.tsx:122-162`, input `:330-338` | `uploadEngine.enqueue` (`src/lib/review/upload-engine.ts:46`) → `POST /api/review/task-upload/initiate` (`route.ts:22`) → S3 multipart R2 → complete | Validate mime/size TRƯỚC khi enqueue (`validateFileMeta` `:124-129`) → `toast.error(meta.message)`; chỉ nhận VIDEO ở mục bàn giao (`:130-133`) | Hàng đợi trạng thái máy: `queued/uploading/paused/completing/processing/done/failed/canceled`; progress + speed per-file trong UploadTray; poll 'refetch' khi còn chuyển động (`:100-114`) | Row failed hiện lỗi inline (`UploadTray.tsx:238`) + nút **Thử lại** (`:290-292`); pause/resume (`:281-287`), cancel chỉ cho row còn chạy (`:119-127`) | CHỜ (placeholder card xuất hiện sau ~400ms `:154`) |
| **Upload ở Tệp browser** | `src/components/review/TeamBrowser.tsx:469` (thả cả cây folder — `enqueueFolderTree`), `:1012` (thả file lên asset = version mới) | Cùng uploadEngine, `POST /api/review/uploads/initiate` (`route.ts:28`) | Filter file hợp lệ trước (`filterValid`) | Như trên (UploadTray dùng chung) | Như trên | CHỜ |
| **Xác nhận đã sửa xong** (banner drawer — lối ra A3/A6) | `TaskReviewUploadSection.tsx:293-305` | `apiConfirmFix` → `POST /api/review/assets/[id]/confirm-fix` (`route.ts:15`) | Banner chỉ hiện khi server trả `fixConfirm` VÀ **không có upload đang chạy** (`uploadInFlight` ẩn banner — `:230-232`, `:270` — chống race với webhook Mux); `disabled={confirmingFix}` (`:299`); tick «đây là bản đã sửa» chỉ ARM highlight, không tự ghi status (owner decision D1, `:197-224`) | `toast.loading('Đang xác nhận…')` → cập nhật cùng id (`:178-181`), spinner trên nút (`:302`) | `toast.error(message, {id: tid})` (`:189`); local snapshot retire banner trước rồi mới refetch (chống double-click 409 — `:182-186`) | CHỜ |
| **Chuyển sang Hoàn tất** (banner khi asset approved) | `TaskReviewUploadSection.tsx:318-326` | `apiConfirmTaskComplete` → `POST /api/review/tasks/[taskId]/confirm-complete` (`route.ts:13`) | Banner hiện khi có asset ở status approved mà task chưa Hoàn tất (`:168-169`); `disabled={confirmingComplete}` (`:321`) | `toast.loading` → success (`:236-239`), spinner (`:324`) | `toast.error` (`:242`) | CHỜ |

## 7. F07 — Review player: Approve-send / Confirm-fix / Feedback-done + Share link

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Duyệt & gửi khách** (F10) | `src/components/review/player/ReviewFlowActions.tsx:141-151` | `apiApproveAndSend` → `POST /api/review/assets/[id]/approve-send` (`route.ts:15`) | Nút CHỈ render khi `isAdmin && canAutoTransition(cur, sentToClient)` (`:55`) — tức task đang A2/A4/A7; `disabled={busy !== null}` khoá cả 3 nút khi 1 nút chạy (`:144`); server re-check cùng FSM | Spinner thay icon Send (`:148`) | `toast.error(e.message)` (`:99`) | CHỜ + `onDone()` refetch (`:97`) |
| **Kết thúc feedback** (F8) | `ReviewFlowActions.tsx:107-117` | `apiMarkFeedbackDone` → `POST .../feedback-done` (`route.ts:13`) | `isAdmin && hasComments && canAutoTransition(cur, internalFeedbackOpen)` (`:68`) — cố ý KHÔNG thu hẹp theo `unresolvedCount` (comment giải thích tại `:59-67`) | Spinner (`:114`) | toast lỗi chung (`:99`) | CHỜ |
| **Xác nhận đã sửa xong** (F9) | `ReviewFlowActions.tsx:118-139` + ConfirmFixDialog `:172-246` | `apiConfirmFix` → `POST .../confirm-fix` (`route.ts:15`) | `(isAssignee \|\| isAdmin) && fixTarget != null` (`:84`) — admin bấm THAY editor được, label đổi «Xác nhận editor đã sửa» (`:132-138`); bắt buộc qua confirm dialog (`:155-167`); dialog hiện cảnh báo còn N feedback chưa xử lý (`:218-222`) | Nút dialog `disabled={busy}` + spinner (`:233-239`); scrim không đóng được khi busy (`:196`) | toast lỗi (`:99`) | CHỜ (server resolve cả round + flip status) |
| **Tạo link chia sẻ /r/** | `src/components/review/ShareLinkModal.tsx` (nút chính `:302-305`) | `apiCreateShare` → `POST /api/review/assets/[id]/share` (`route.ts:14`) / `POST /api/review/shares` (`route.ts:32`) | `disabled={busy}` (`:302`); «Sao chép» khi CHƯA có link = create-then-copy (`:158-160`) | Spinner (`:305`) | `toast.error(e.message \|\| 'Không tạo được link.')` (`:101`) | CHỜ; thành công toast kèm action «Sao chép» (`:96-97`) |
| **Tắt link / Bật lại link** | `ShareLinkModal.tsx:284-291` | `apiSetShareRevoked` → `POST /api/review/shares/[id]/revoke` (`route.ts:18`) | `disabled={busy}` (`:284`); toggle 2 chiều (revoke/un-revoke) | busy chung modal | `toast.error` (`:142`) | CHỜ |

## 8. F08 — Guest `/r/[slug]`: Approve / Request changes / Download / Comment

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Continue** (unlock password) | `src/components/review/share/GateScreens.tsx:31-66` | `guestShareApi(slug).unlock` → `POST /api/r/[slug]/unlock` (`route.ts:21`) | `disabled={!password \|\| busy}` (`:63`) | Spinner (`:66`) | Text đỏ inline dưới ô nhập (`:60`) — không toast | CHỜ |
| **Approve** | Header: `src/components/review/share/GuestReviewApp.tsx:635-642` (luôn hiện — FR-F03); modal xác nhận `:796-816` | `submitDecision('approve')` (`:386-466`) → `POST /api/r/[slug]/decision` (`route.ts:34`) → Inngest `reviewShareDecision` (`src/lib/review/inngest.ts:657`) | Nút header không disable; modal: `disabled={decisionBusy}` (`:810`); CHẶN khi có version mới (`newHead`) → toast bảo bấm Reload, giữ modal + giữ text (`:390-404`); BẮT BUỘC identity: `ensureIdentity('decision')` mở modal tên+email, huỷ → toast «Add your name and email to record your decision.» (`:409-415`) | Spinner trong modal (`:813`); scrim không đóng khi busy (`:797`) | Toast tự viết z-120 (`:778-791`) với message server; wording trung lập vì decision có thể ĐÃ commit trước khi lỗi mạng (`:444-455`) | CHỜ; thành công → banner «You approved this video» (`:661-665`) + `postMessage` về portal cha (`:433`); **lan truyền status task/email là ASYNC qua Inngest** |
| **Request changes** | Header `:627-634`; `RequestChangesModal` `:818-827`, `:848+` | Cùng `submitDecision('request_changes', note)` | Như Approve; draft note do PARENT giữ — đóng modal không mất text (`:860-864`) | `busy` prop | Như Approve | CHỜ |
| **Download** | `GuestReviewApp.tsx:614-624` | `api.fetchDownloadUrl` → presigned R2 URL, navigate `window.location.href` (`:470-487`) | `disabled={!canDownload}`; `canDownload = share.allowDownload && (!downloadOnlyWhenApproved \|\| reviewState==='approved')` (`:469`); tooltip giải thích «Download unlocks after approval.» (`:618`) | Không có state (navigate) | `showToast(e.message)` (`:485-487`) — cố ý không dùng `alert()` trong iframe portal | CHỜ |
| **Gửi comment** (player nội bộ + guest dùng chung) | `src/components/review/player/CommentComposer.tsx:474-479` | `env.api.createComment` → staff: `POST /api/review/versions/[id]/comments` (`route.ts:13,30`); guest: `POST /api/r/[slug]/comments` (`route.ts:36`) qua `ensureIdentity` chặn trước (`GuestReviewApp.tsx:126-131`) | `disabled={!canSend \|\| submitting}` (`:475`); `canSend` = có text HOẶC annotation HOẶC attachment xong, VÀ **không còn attachment đang upload/lỗi** (`:253-258` — chặn gửi rơi mất ảnh lỗi); nút đính kèm disable khi đạt MAX hoặc đang gửi (`:462`) | Spinner thay icon Send (`:479`) | (trong submit) lỗi giữ nguyên nội dung soạn | CHỜ |

## 9. F09 — Client portal `/share/[token]`: Approve / Request changes / ZIP / Comment

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Approve** | `src/components/portal/desk/DeliverableSheet.tsx:204` (block chỉ render khi `d.needsYou && mode===null` `:200`) | `actions.approve` = `approveDeliverableViaToken(token, taskId)` (adapter `src/components/portal/share/SharePortalClient.tsx:49`; action `src/actions/share-portal-actions.ts:765`) | `disabled={busy}` (`:204`); job Closed/Completed không render block | busy chung sheet | `setErr` → text đỏ inline (`:75`, hiển thị `:197`); network reject được try/finally bắt riêng «Could not reach the server…» (`:63-80` — fix nút bị kẹt disabled vĩnh viễn) | CHỜ; server OK mới `onUpdated(...Completed)` cập nhật local (`:73`) |
| **Request changes → Send to the studio** | Mở form `:205`; gửi `:214` | `requestChangesViaToken` (`share-portal-actions.ts:1011`) | Send: `disabled={busy \|\| !notes.trim()}` (`:214`); Cancel `disabled={busy}` (`:215`) | busy | Như trên (`:92-97`) | CHỜ; OK → `onUpdated('In revision')` (`:89`) |
| **Approve nhiều video** | `src/components/portal/desk/YourDesk.tsx:40-47` | `approveDeliverablesViaToken` (`share-portal-actions.ts:855`) | Guard `!actions.approveMany \|\| picked.size===0 \|\| approving` (`:40`); UI chỉ hiện khi ≥2 video chờ (`:81`, `:104`) | `approving` flag | (cùng mẫu setErr) | CHỜ |
| **Download ZIP** | Link build từ `zipUrl`/`zipUrlForAssets` (`SharePortalClient.tsx:82-90`) → `GET /api/share/[token]/download-zip` | Route re-resolve token, chỉ bundle file đúng snapshot đang hiển thị | Thẻ `<a>`/navigate — không disable | Không có pending UI | Lỗi = response của route (không toast) | CHỜ |
| **Invoice PDF** | `invoicePdfUrl` (`SharePortalClient.tsx:77-78`) → `GET /api/share/[token]/invoices/[id]/pdf` (`route.ts:51`) | như trên | như trên | — | — | — |
| **Gửi comment portal** (2 chiều với team) | `src/components/tasks/TaskCommentThread.tsx` (dùng chung staff+portal): submit `:266-274`, nút Gửi/Send `:556-560` | Portal: `postCommentViaToken` (`share-portal-actions.ts:1703`); staff: `createTaskComment` (`src/actions/task-comment-actions.ts:244`, wire tại `TaskCommentColumn.tsx:53`) | `disabled={!body.trim() \|\| busy}` (`:557`); toggle «nội bộ» chỉ staff (`canInternalToggle` `:546-555`); Ctrl/⌘+Enter gửi (`:259`) | Spinner thay icon Send (`:559`) | `setErr(res?.error \|\| 'Không gửi được.')` inline (`:274`) — giữ nguyên text đã gõ | CHỜ + `onRefresh()` |

## 10. F13 — Payroll: Confirm payment / Revert / Export Excel

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Thanh toán** (mở modal) | `src/components/admin/PayrollCard.tsx:215-221` | mở `PaymentModal` | Chỉ render khi CHƯA paid (`isPaid` từ `payrollRecord?.status==='PAID'` `:43`) | — | — | — |
| **Xác nhận đã chuyển khoản** | `src/components/admin/PaymentModal.tsx:134-147` | `confirmPayment` — `src/actions/payroll-actions.ts:22` | `disabled={loading}` (`:136`). Server guard THẬT: `verifyWorkspaceAccess(ADMIN)` (`:33`), cycle resolve từ `workspace.name` server-side (không tin client — `:40-41`), **PayrollLock đã khoá → từ chối** (`:47-53`), validate tiền không âm + tổng = lương+thưởng (`:54-62`) | Text đổi «Đang xử lý...» (`:139-140`) | ⚠️ `toast.error('Lỗi thanh toán')` **GENERIC** (`:45`) — message server chi tiết (vd «Kỳ lương đã bị KHÓA…» `payroll-actions.ts:52`) KHÔNG bao giờ tới admin | CHỜ; success → toast + đóng modal (`:41-43`) |
| **Hoàn tác thanh toán** | `PayrollCard.tsx:203-212` | `revertPayment` — `src/actions/payroll-actions.ts:165` (truyền đúng cycle thật — fix AUDIT R3 `:50-55`) | `confirm()` native trước (`:48`); `disabled={isPending}` (`:207`, `useTransition` `:24`) | Icon RotateCcw quay `animate-spin` (`:211`) | `toast.error(res.error)` — message server THẬT (`:56`) | CHỜ |
| **Xuất XLSX** | `src/app/[workspaceId]/admin/payroll/page.tsx:161-169`; MC: `src/components/mission-control/McPayrollBoard.tsx:139` | `GET /api/exports/monthly-tasks-xlsx` (URL build `:129-131`) | Nút CHỈ render khi `currentUser.role === 'ADMIN'` global (`:127`) — server route tự re-check | Thẻ `<a>` — không pending UI | Lỗi = response route hiển thị trong tab (không toast) | CHỜ |

## 11. F14 — Finance: Tạo invoice / Void / Record payment

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Xuất & Lưu** (invoice) | `src/components/invoice/InvoiceModal.tsx:595-602` | `handleGenerate` (`:315+`) → `createInvoiceRecord` (`src/actions/invoice-actions.ts:314`) → render PDF `POST /api/invoices/generate` (`route.ts:5`) | `disabled={isGenerating \|\| activeItems.length===0}` (`:597`); click còn validate: thiếu billing profile → `toast.error('Vui lòng chọn hồ sơ thanh toán')` (`:316`), giỏ trống (`:317`) | Chuỗi toast tiến trình: «Đang lưu hóa đơn...» (`:373`) → «Đã lưu! Đang tạo PDF...» (`:377`) → «Đã tạo & tải hóa đơn về!» (`:437`); spinner + «Đang tạo...» trên nút (`:600-601`) | `toast.error('Lỗi: ' + e.message)` (`:441`) — message server thật; DB đã lưu mà PDF lỗi thì invoice VẪN tồn tại (2 bước tách rời) | CHỜ |
| **Huỷ hoá đơn (Void)** | `src/components/invoice/ClientInvoicesTable.tsx:108-118` | `voidInvoice` — `src/actions/invoice-actions.ts:581` | Chỉ render khi `status !== 'VOID'` (`:108`); `confirm()` native cảnh báo hoàn cọc + un-bill task (`:27`); `disabled={isVoiding===id}` per-row (`:114`) | disable per-row (không spinner) | `toast.error(message)` thật (`:37`) | CHỜ + `router.refresh()` (`:35`) |
| **Tải PDF invoice** | `ClientInvoicesTable.tsx:105-107`, handler `:43-69` | `GET /api/invoices/[id]/download` | luôn enable | `toast.info('Đang chuẩn bị bản PDF...')` (`:45`) | `toast.error('Lỗi tải xuống: …')` với text từ response (`:49-52`, `:67`) | CHỜ |
| **Ghi nhận đã thu** | `src/components/crm/RecordPaymentModal.tsx:134-136` | `recordPayment` — `src/actions/payment-actions.ts:44` | `disabled={busy}` (`:134`); validate client `amount > 0` → toast (`:51`) | Spinner + nền nút nhạt đi, cursor `not-allowed` (`:134-135`) | `toast.error(res.error \|\| 'Không ghi nhận được.')` (`:64`) | CHỜ + reload history + `onSaved()` (`:59-62`) |
| **Xoá bản ghi thu** | `RecordPaymentModal.tsx:162-164`, handler `:68-83` | `deletePayment` (`payment-actions.ts`) | GĐ1 (/admin/crm): xoá THẲNG không confirm; MC bật `confirmOnDelete` → ConfirmModal (`:68-79`) — hard-delete có audit log | **Không busy state** trên nút row | `toast.error` (`:82`) | CHỜ |

## 12. F15 — Share link portal: Tạo / Thu hồi (CRM)

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Tạo link chia sẻ mới** | `src/components/crm/ShareLinkSection.tsx:117-123` | `createClientShareLink` — `src/actions/share-link-actions.ts:46` | `disabled={busy}` + cursor `wait` (`:119-120`); authz thật ở server: `canManageShareLinks` = profile OWNER/ADMIN (ghi chú `:7-9`) — USER mở modal chỉ nhận refusal message | Spinner thay icon Plus (`:122`) | `toast.error(res.error)` (`:64`) | CHỜ; URL gốc hiện **đúng 1 lần** (chỉ lưu hash — `:102-115`), copy có fallback toast (`:69-77`) |
| **Thu hồi** | `ShareLinkSection.tsx:149-153`, handler `:79-85` | `revokeClientShareLink` (`share-link-actions.ts:91`) | `confirm()` native «hiệu lực ngay lập tức» (`:80`); nút chỉ hiện trên link còn sống (`:149` — `!dead`) | **Không busy state** (bấm nhiều lần được) | `toast.error(res.error)` (`:82`) | CHỜ + reload list |

## 13. F03 — Invite member / Accept / Decline

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Gửi lời mời** (profile) | `src/components/profile/InviteToProfileModal.tsx:109-110` | `inviteToProfileAction` — `src/actions/profile-member-actions.ts` | `disabled={loading \|\| !usernameOrEmail.trim()}` (`:109`) | `loading` flag (nút Huỷ cũng disable `:102-103`) | `toast.error(result.error)` (`:28`) | CHỜ; toast phân biệt direct-add vs gửi invite (`:34`) |
| **Chấp nhận / Từ chối lời mời** | `src/components/workspace/PendingInvitationsBanner.tsx:112-125` | `acceptWorkspaceInvitation` / `declineWorkspaceInvitation` — `src/actions/member-actions.ts:617` / `:937` | `disabled={actionLoading === inv.id}` per-invitation (`:112`, `:124`) | per-row loading | `toast.error(result.error \|\| err.message)` (`:44`, `:54`, `:65`, `:71`) | CHỜ |

## 14. P5 — Impersonate

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Nhập vai** (icon mắt trên LivePresenceBoard) | `src/components/admin/analytics/LivePresenceBoard.tsx:112-113`, handler `:21-29` | `startImpersonation` — `src/actions/impersonation-actions.ts:9` (5 lớp chặn server + audit, TTL 2h) | `disabled={isPending \|\| loading}` (`:112`); **KHÔNG có confirm dialog** | `useTransition` (`:18`) + `impersonatingId` per-user (`:23`) | ⚠️ `catch(console.error)` (`:25`) — **lỗi KHÔNG hiển thị gì cho admin** (không toast); mọi từ chối của 5 lớp guard chết im lặng trên UI | CHỜ (server điều hướng khi thành công) |

## 15. P6 — Xoá / Restore (trash)

| Nút | Component | Action | Enable/disable thật | Đang submit | Khi lỗi | Optimistic |
|---|---|---|---|---|---|---|
| **Xoá task** (menu ⋮, admin) | `src/components/TaskWorkflowTabs.tsx:921-926` (handler `:205-225`) | `task-actions.ts` (soft-delete; restore `:509`, `:553`) | Item chỉ render khi `isAdmin` (`:921`) | — | `toast.error(res.error)` (`:222`) | CHỜ |
| **Khôi phục task/client/profile** (mobile trash) | `src/components/admin/MobileTrash.tsx:46-96` | `restoreCancelledTask` (`task-actions.ts`), `restoreClient`/`permanentlyDeleteClient` (`crm-actions.ts:297/:417`), `restoreProfileAction` (`profile-actions.ts:429`) | `busy` guard per-item (`setBusy(null)` finally) | busy per item | `toast.error(res.error \|\| 'Khôi phục thất bại')` (`:51`, `:63`, `:83`) | CHỜ |
| **Khôi phục / Xoá vĩnh viễn** (review trash — Tệp) | `src/components/review/TeamTrash.tsx` — restore bulk `:313-316`, per-row `:397-401`, purge confirm `:107-109` | `POST /api/review/trash/restore` (`route.ts:18`), `purge` (`route.ts:18`) | Chọn tối đa `RESTORE_CAP=200` (`:34` — khớp limit route); 1 guard toàn cục `restoringKey` chống gọi chồng (`:106`, `:190`); row có folder cha đã xoá → `disabled={!item.restorable}` (`:502`); purge = ADMIN + confirm modal | `toast.loading` → success/error cùng id (`:195-203`, `:224-232`); spinner trên nút bulk (`:316`) | toast với message thật; item không restore được thì toast nói rõ (ghi chú `:8-13`) | CHỜ |

## 16. Nhận xét cắt ngang (điểm yếu lặp lại — input cho phase sau)

| # | Hiện tượng | Bằng chứng | Rủi ro |
|---|---|---|---|
| 1 | **Nút không có pending state → double-fire được**: StatusCell dropdown, AssigneeCell, revoke share link, xoá bản ghi thu tiền, «Gửi Revision» | `StatusCell.tsx:62-79` (không busy), `AssigneeCell.tsx:98-136`, `ShareLinkSection.tsx:79-85`, `RecordPaymentModal.tsx:162`, `StatusCell.tsx:210` | Gọi trùng action; với status là chuỗi tự do + payroll đếm theo status thì double-fire đổi status là rủi ro tiền |
| 2 | **Nuốt message lỗi server** ở đúng các nút đụng tiền/phân quyền: PaymentModal («Lỗi thanh toán» generic — mất message PAYROLL_LOCKED), AssigneeCell single-assign («Giao task thất bại»), Impersonate (console.error, không toast) | `PaymentModal.tsx:45` vs `payroll-actions.ts:52`; `AssigneeCell.tsx:134`; `LivePresenceBoard.tsx:25` | Admin không biết VÌ SAO thao tác fail → thử lại vô ích hoặc làm sai quy trình unlock |
| 3 | Optimistic UI chỉ tồn tại ở 4 bề mặt (claim chợ, kanban MC, toggle chợ, status chip asset) và đều có rollback đúng; phần còn lại CHỜ + `router.refresh()` | §4, §5 | Nhất quán tốt; riêng «Trả lại task» dùng `window.location.reload()` (`TaskWorkflowTabs.tsx:913`) lệch mẫu |
| 4 | 3 chỗ vẫn dùng `confirm()` native trong khi MC đã có ConfirmModal riêng | `PayrollCard.tsx:48`, `ClientInvoicesTable.tsx:27`, `ShareLinkSection.tsx:80` | UI không đồng nhất; confirm native không mô tả được hậu quả phức tạp |
| 5 | Điều kiện enable phía client LUÔN hẹp hơn hoặc bằng server ở review module (FSM `canAutoTransition` chạy 2 đầu), và server là nguồn sự thật (claim: mọi check trong transaction) | `ReviewFlowActions.tsx:55-84`, `claim-actions.ts:156-198` | Đúng hướng — client chỉ để ẩn/hiện nút |
| 6 | Nút «Tạo task» footer không validate field phía client (chỉ chặn khi đang submit) — lỗi thiếu dữ liệu chỉ biết sau round-trip | `AddTaskModal.tsx:1700-1710`, `:892-938` | UX chậm với batch lớn; server vẫn an toàn |

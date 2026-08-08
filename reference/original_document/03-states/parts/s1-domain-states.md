# PHASE 3 §1 — BẢNG TRẠNG THÁI DOMAIN (mọi entity có vòng đời thật trong code)

> Nguồn: đọc trực tiếp code tại worktree `cranky-austin`, ngày 2026-08-02. Mọi giá trị/transition dưới đây đều **grep từ code thật** (kèm `file:line`), KHÔNG suy diễn từ schema. Các giá trị enum có trong `schema.prisma` nhưng **không bao giờ được ghi** bởi code đều được đánh dấu rõ (⚰️ = dead value).
>
> Quy ước cột: **Sự kiện** = tên hàm/route gây transition; **Role** = ai được phép gọi (đã verify guard thật); **Side effects** = email / notification / payroll / portal / audit.

---

## 1. `Task.status` — String TỰ DO (trục xương sống của toàn hệ thống)

### 1.1. Bộ giá trị canonical (13 giá trị — nguồn sự thật duy nhất)

`VALID_TASK_STATUSES` (`src/lib/task-statuses.ts:18-39`) + bảng thuộc tính `TASK_STATUS_META` (`src/lib/task-statuses.ts:84-109`). Schema để String tự do, default `"Đang thực hiện"` (`prisma/schema.prisma:336`) — nhưng default này gần như không bao giờ chạm tới vì mọi đường tạo task đều set status tường minh (xem 1.3). `updateTaskStatus` chặn mọi giá trị ngoài danh sách (`src/actions/task-actions.ts:27-31`).

| # | Status | Mã | Phase | salaryPending | terminal | internalOnly | cron được ghi đè 'Quá hạn' | Label khách (EN) |
|---|--------|----|-------|---------------|----------|--------------|---------------------------|------------------|
| 1 | `Đang đợi giao` | — | production | ✅ | — | — | ✅ | In production |
| 2 | `Nhận task` | — | production | ✅ | — | — | ✅ | Received |
| 3 | `Đã nhận task` | — | production | ❌ | — | — | ✅ | Received |
| 4 | `Đang thực hiện` | — | production | ✅ | — | — | ✅ | In progress |
| 5 | `Đã nộp video (nội bộ)` | A2 | internal_review | ✅ | — | ✅ | ❌ | (In progress) |
| 6 | `Đang sửa feedback (nội bộ)` | A3 | internal_review | ✅ | — | ✅ | ❌ | (In progress) |
| 7 | `Đã sửa feedback (nội bộ)` | A4 | internal_review | ✅ | — | ✅ | ❌ | (In progress) |
| 8 | `Đã gửi video (khách)` | A5 | client_review | ✅ | — | — | ❌ | Ready for your review |
| 9 | `Đã nhận feedback (khách)` | A6 | client_review | ✅ | — | — | ❌ | Revising |
| 10 | `Đã sửa feedback (khách)` | A7 | client_review | ✅ | — | ✅ | ❌ | (In review) |
| 11 | `Revision` | — | internal_review | ✅ | — | — | ✅ | In revision |
| 12 | `Quá hạn` | — | production | ❌ | — | — | ❌ | In progress |
| 13 | `Hoàn tất` | — | closed | ❌ (salaryCompleted ✅) | ✅ | — | ❌ | Completed |
| 14 | `Đã hủy` | — | closed | ❌ | ✅ | — | ❌ | Closed |

3 status legacy `Sửa frame` / `Gửi lại` / `Tạm ngưng` đã bị chủ dự án XÓA 2026-07-07, dữ liệu cũ remap bằng `scripts/migrate-drop-legacy-statuses.ts` (comment tại `task-statuses.ts:33-35`).

**Các hằng DERIVE từ meta (load-bearing, khoá bằng snapshot-test `scripts/test-status-meta-snapshot.ts`):**

| Hằng | Giá trị (derive) | file:line | Ai tiêu thụ |
|---|---|---|---|
| `SALARY_PENDING_STATUSES` | 10 status có salaryPending=✅ (bảng trên) | `task-statuses.ts:116` | Payroll đếm "việc đang nợ lương editor" (F13 — rủi ro số 1 review-fixes) |
| `SALARY_COMPLETED_STATUS` | `'Hoàn tất'` | `task-statuses.ts:119` | Payroll đếm task đã trả |
| `OVERDUE_ELIGIBLE_STATUSES` | 5 status ✅ cột "cron ghi đè" | `task-statuses.ts:128` | Cron check-deadline — whitelist thay blacklist cũ, 6 status video KHÔNG bị cron ghi đè |
| `TERMINAL_STATUSES` | `['Hoàn tất','Đã hủy']` | `task-statuses.ts:148` | Auto-transition (Inngest/webhook/guest) KHÔNG BAO GIỜ flip task terminal (`isTerminalStatus:156`) |
| `REVIEW_PHASE_STATUSES` | A2/A3/A4+Revision + A5/A6/A7 | `task-statuses.ts:138` | Board 2 tab duyệt; task trong đây không tính overdue |
| `CLIENT_FACING_STATUSES` | A5/A6/A7 | `task-statuses.ts:166` | Non-admin bị CẤM set trực tiếp (publish bản dựng cho khách) |
| `STATUS_REQUIRES_NULL_DEADLINE` | `['Revision','Hoàn tất']` | `src/lib/task-invariants.ts` (dùng tại `task-actions.ts:124-127`) | Vào 2 status này thì deadline bị clear |

### 1.2. Hai tầng "FSM" — cái nào thật, cái nào đã tắt

| Cơ chế | file:line | Trạng thái |
|---|---|---|
| FSM đầy đủ `validateTransition` (enum `TaskState`, 14 event) | `src/lib/fsm-config.ts:41-116` | **ĐÃ TẮT chủ đích** — hàm luôn trả `{isValid:true}` (`fsm-config.ts:122-125`, "FSM Disabled as per user request"). Đổi status tay = tự do (R10). |
| Guard AUTO-transition `STATUS_TRANSITIONS` (map target → predecessors hợp lệ, CHỈ 6 status video là target) | `src/lib/task-statuses.ts:199-218` + `canAutoTransition:221` | **ĐANG CHẠY** — chỉ áp cho đường tự động (Inngest / webhook Mux / guest decision / nút F8-F10), không áp cho dropdown tay. |
| RBAC trong `updateTaskStatus` | `src/actions/task-actions.ts:68-97` | **ĐANG CHẠY** — 3 lớp: (1) non-admin chỉ sửa task của mình (`:70-75`); (2) chỉ workspace-admin được vào/ra terminal (`:84-96`, audit H3 — chống editor tự Hoàn tất ăn lương); (3) non-admin bị cấm set status client-facing A5/A6/A7 (`:93`, HT-016). |

Guard predecessor (từ `STATUS_TRANSITIONS`): **A2** ← {Đang thực hiện, Revision, A4, A5} · **A3** ← {A2, A4} · **A4** ← {A3} · **A5** ← {A4, A2, A7} · **A6** ← {A5} · **A7** ← {A6}. Target legacy (`Revision`, `Hoàn tất`…) không có guard — giữ hành vi "flip from anywhere" lịch sử (`task-sync.ts:86-88`).

### 1.3. Bảng transition đầy đủ (sự kiện → role → side effects)

| # | Sự kiện | From → To | Role được phép | Hàm (file:line) | Side effects |
|---|---------|-----------|----------------|------------------|--------------|
| T1 | Admin tạo task đơn | ∅ → `Nhận task` (có assignee) / `Đang đợi giao` (không) | workspace ADMIN | `createTask` `src/actions/admin-actions.ts:232` | Email legacy `taskAssigned` (`admin-actions.ts:319`) + notification `TASK_ASSIGNED` (→ registry email — nguy cơ double-email, xem parts/10 §5.2); audit |
| T2 | Velox batch tạo N task | ∅ → `Nhận task`/`Đang đợi giao` per-row | workspace ADMIN | `createTasksFromBatch` `src/actions/velox-batch-actions.ts:218,239` | Như T1 theo từng row |
| T3 | Admin accept yêu cầu khách | ∅ → `Đang đợi giao` | profile ADMIN (`adminCtx`) | `acceptClientRequest` `src/actions/client-request-actions.ts:124-144` | `ClientTaskRequest` NEW→ACCEPTED (§10); audit `request.accepted` |
| T4 | Khách tự tạo task qua portal (đường cũ, còn mount nhưng UI đã chuyển sang intake) | ∅ → `Đang đợi giao` | Client portal (token) | `createTaskViaToken` `src/actions/share-portal-actions.ts:1231` | notify staff; workspace phải ACTIVE (`:1204`) |
| T5 | Admin giao / đổi assignee | X → `Nhận task`; unassign → `Đang đợi giao` | workspace ADMIN | `assignTask` `src/actions/task-management-actions.ts:178` (assign), `:137,147` (unassign/reset) | Notification `TASK_ASSIGNED`/`TASK_UNASSIGNED` + email registry |
| T6 | Editor tự claim từ chợ | `Đang đợi giao` → `Nhận task` | USER (marketplace mở: `Workspace.marketplaceOpen`, toggle bởi admin `claim-actions.ts:34`) | `claimTask` `src/actions/claim-actions.ts:187` | `claimSource=MARKET`; trả lại: `returnTask` `:248` → `Đang đợi giao` |
| T7 | Editor bắt đầu làm | `Nhận task`/`Đã nhận task` → `Đang thực hiện` | assignee (hoặc admin) | `updateTaskStatus` `src/actions/task-actions.ts:232-234` (nhánh isUserStart) | Email `taskStarted` → admin assignedBy (`:258-269`); notification `TASK_STARTED` (`:342-380`); audit `task.started` (`:394-403`) |
| T8 | Editor nộp bài tay (link) | `Đang thực hiện` → `Revision` (+productLink) | assignee | `updateTaskStatus` — nhánh isUserDelivery `task-actions.ts:235-238` | Email `taskDelivered` → admin (`:275-286`); notification `TASK_DELIVERED`; deadline clear; audit `task.delivered` |
| T9 | Admin reject / gửi feedback | X → `Revision` (actor ≠ assignee) | workspace ADMIN | `updateTaskStatus` — nhánh isAdminReject `task-actions.ts:242` | Email `taskFeedback` → assignee (`:305-315`); deadline clear |
| T10 | Admin resume | `Revision` → `Đang thực hiện` | workspace ADMIN | `updateTaskStatus` — nhánh isAdminResume `task-actions.ts:241` | Email `taskFeedback` "đã phản hồi" → assignee (`:292-302`) |
| T11 | Admin hoàn tất | X → `Hoàn tất` | **CHỈ workspace ADMIN** (guard H3 `task-actions.ts:84-96`) | `updateTaskStatus` — nhánh isComplete `:243` | Email `taskCompleted` (kèm wageVND) → assignee (`:318-327`); deadline clear; **payroll: task rơi vào `SALARY_COMPLETED_STATUS`**; audit `task.completed` |
| T12 | Admin hủy | X → `Đã hủy` | **CHỈ workspace ADMIN** | `updateTaskStatus` — archiveUpdate `task-actions.ts:143` | **auto `isArchived=true`** → biến khỏi board + Total Tasks; assignee giữ nguyên để restore |
| T13 | Admin khôi phục task hủy | `Đã hủy` → `Nhận task` (có assignee) / `Đang đợi giao` | workspace ADMIN | `restoreCancelledTask` `src/actions/task-actions.ts:553-596` | `isArchived=false`, deadline+isPenalized clear; audit `task.restored` |
| T14 | Admin kéo về pool | X → `Đang đợi giao` | workspace ADMIN | `updateTaskStatus` — poolReset `task-actions.ts:133-135` | **assigneeId=null** + deadline+penalize clear (invariant assignee↔status) |
| T15 | **CRON ghi đè quá hạn** | 1 trong 5 `OVERDUE_ELIGIBLE_STATUSES` → `Quá hạn` (deadline đã qua) | SYSTEM (Vercel cron mỗi giờ, guard CRON_SECRET) | `src/app/api/cron/check-deadline/route.ts:156-159` (whitelist `:41,92,142`) | Notification `TASK_OVERDUE` + email + web-push (`:170-189`); 6 status video + Revision/Hoàn tất/Đã hủy/Quá hạn **miễn nhiễm** |
| T16 | **Mux READY (F7)** — bản dựng encode xong | {Đang thực hiện, Revision, A4, A5} → **A2** | SYSTEM (Inngest, không session) | `applyMuxReady` → `syncTaskFromReviewEvent` `src/lib/review/inngest.ts:156-160` + `src/lib/review/task-sync.ts:90-143` | Xem §2.4; notify manager (`inngest.ts:170-182`); nếu task đang phơi khách (clientReview AWAITING/CHANGES) → **thu hồi share + kéo A5/A6/A7 về A2** (`task-sync.ts:452-503`) |
| T17 | **F8 admin chốt phiên feedback** | A2 hoặc A4 → **A3** | **admin-only** (`task-sync.ts:274`) | `markFeedbackDone` `src/lib/review/task-sync.ts:272-289` (route `api/review/assets/[id]/feedback-done`) | Delegate `updateTaskStatus` (email status-change generic → editor); activity `TASK_FEEDBACK_CLOSED` |
| T18 | **F9 editor xác nhận đã sửa** | A3 → **A4** (vòng nội bộ) HOẶC A6 → **A7** (vòng khách) | admin HOẶC assignee (`task-sync.ts:300-302`) | `confirmFixDone` `task-sync.ts:298-369` | Resolve toàn bộ comment mở của round (`:321-333`); notify MANAGER (`:339-347`); A6→A7 còn email khách "Revised — pending final approval" (`:353-359`); activity `TASK_FIX_CONFIRMED` |
| T19 | **F10 admin duyệt & gửi khách** | {A4, A2, A7} → **A5** | **admin-only** (`task-sync.ts:381`) | `approveInternalAndSendToClient` `task-sync.ts:377-423` | **Bridge portal** (`:403-418`): get-or-create ShareLink `/r/{slug}` + `Task.clientReview='AWAITING'` + ghi `productLink` (nếu trống/link `/r/`) + email guest `version_sent`; activity `TASK_SENT_TO_CLIENT` |
| T20 | **Guest request-changes trên `/r/`** | A5 → **A6**; các status khác → `Revision` (fallback legacy, GIỮ deadline); A6/A7 → no-op | Guest (share token, danh tính tự khai — owner waive PIN `share-decision.ts:178-183`) | `submitGuestDecision` → `syncTaskOnChangesRequested` `src/lib/review/share-decision.ts:295-298` + `task-sync.ts:158-196` | `clientReview='CHANGES'` khi vào A6 (`task-sync.ts:190-194`); notify editor+manager `VIDEO_CHANGES_REQUESTED` (`share-decision.ts:336-347`); email guest `feedback_received`; note → comment public (internal nếu freeze comment); Inngest backup idempotent (`:374-387`) |
| T21 | Guest approve trên `/r/` | Task status **KHÔNG đổi** (chỉ asset card + clientReview) | Guest | `share-decision.ts:300-326` | `clientReview='APPROVED'`; asset `statusId='Hoàn tất'` (head only); notify staff `VIDEO_REVIEW_APPROVED` "mở task xác nhận Hoàn tất"; email guest `approved`. Chuyển `Hoàn tất` thật vẫn phải qua T11/T22 |
| T22 | Staff xác nhận Hoàn tất từ banner review | X → `Hoàn tất` | delegate `updateTaskStatus` (admin-only vì terminal) | `confirmTaskHoanTat` `task-sync.ts:26-74` (route `api/review/tasks/[taskId]/confirm-complete`) | Guard: phải có asset `statusId='Hoàn tất'` (`:28-34`); settle `clientReview='APPROVED'` nếu từng phơi khách (`:51-54`); email guest `status_update` "Completed" (`:69-72`) |
| T23 | **Portal khách approve deliverable** | (phase client-facing) → `Hoàn tất` | Client portal (ClientShareLink token) | `approveDeliverableViaToken` `src/actions/share-portal-actions.ts:792-810` (bulk `:936`) | CAS pin đủ trường (chống race admin hủy); `clientReview='APPROVED'`; deadline null; notify staff; audit `task.client_approved` (**payroll: khách approve = Hoàn tất, quyết định chủ dự án Q1**, guard client-facing-phase `:780`) |
| T24 | **Portal khách request changes** | (phase client-facing, ≠Hoàn tất) → `Revision` | Client portal (token) | `requestChangesViaToken` `share-portal-actions.ts:1033-1050` | `clientReview='CHANGES'` + `clientFeedback`; deadline null; notify staff; audit `task.client_changes_requested` |
| T25 | Xóa task cứng | any → ∅ (DELETE row) | workspace ADMIN | `deleteTask` `src/actions/task-management-actions.ts:12-32` | Hard-delete, không trash |

**Ghi chú then chốt:** (1) Task terminal không bao giờ bị auto-flip — `syncTaskFromReviewEvent` từ chối (`task-sync.ts:109-116`, E1/J1: guest bấm request-changes muộn không mở lại task đã trả lương). (2) Race được xử lý bằng optimistic `version` (`task-actions.ts:108,168-181`) + `updateMany` pin status hiện tại (`task-sync.ts:123-124`).

### 1.4. Sub-state của Task (3 trục phụ đi kèm status)

| Trục | Giá trị | Ai ghi | file:line |
|---|---|---|---|
| `clientReview` (String?, portal VIEW) | `null` → `AWAITING` (F10 bridge `task-sync.ts:414-417`) → `APPROVED` (guest approve `share-decision.ts:300-326`; portal T23; confirm-complete `task-sync.ts:51-54`) hoặc `CHANGES` (guest A6 `task-sync.ts:190-194`; portal T24) → về `null` khi bản dựng mới thu hồi phơi bày (`task-sync.ts:487-494`) | Hệ thống + guest + client portal | Portal synthesize `AWAITING` in-memory khi board sống mà clientReview null (`share-portal-actions.ts:396-399`) |
| `invoiceStatus` (enum `InvoiceTaskStatus`) | `UNBILLED` (default) → `INVOICED` (claim atomic khi tạo invoice `invoice-actions.ts:443-452`) → về `UNBILLED` khi void (`:631-637`) | Admin finance | Race chống double-billing bằng `updateMany where UNBILLED` + assert count |
| `isArchived` (Boolean) | `false` → `true` (auto khi `Đã hủy` `task-actions.ts:143`) → `false` (restore `:571`) | workspace ADMIN | Portal readmit row archived nếu clientReview APPROVED/CHANGES (lịch sử — `share-portal-actions.ts:195`) |

---

## 2. Module Review — 3 trục trạng thái độc lập (F06–F08)

### 2.1. `ReviewVersion.pipelineStatus` (enum, per-file pipeline)

Enum `ReviewPipelineStatus` (`prisma/schema.prisma:1623`): `UPLOADING → UPLOADED → PROCESSING → READY | FAILED`. **FAILED là terminal — không bao giờ quay lại** (`inngest.ts:195-197`).

| # | Transition | Sự kiện | Actor | file:line | Side effects |
|---|---|---|---|---|---|
| V1 | ∅ → `UPLOADING` | initiate upload (S3 multipart R2, Idempotency-Key) | Staff (editor/admin, `requireReviewAccess`) | `upload-service.ts:318` (session `expiresAt=+24h` `:246,256`) | Tạo `ReviewAsset`+`ReviewVersion`+`UploadSession` |
| V2 | `UPLOADING` → `UPLOADED` | complete multipart (CAS claim) | Staff | `upload-service.ts:494-495`; `UploadSession.completedAt` `:543` | Quá size → FAILED (`:534`) |
| V3 | `UPLOADED` → `READY` (ảnh) / `PROCESSING` (video) | driveCompletion (atomic, retry-safe) | SYSTEM | `upload-service.ts:396-399` (ảnh set luôn `reviewState=AWAITING_REVIEW`+readyAt) | Video: bắn Inngest `review/upload.completed` → `reviewProcessUpload` sniff magic-bytes, retag BT.709, tạo Mux asset (`inngest.ts:341-451`); không phải video → FAILED (`:390-411`) |
| V4 | `PROCESSING` → `READY` | webhook Mux `video.asset.ready` (idempotent qua ledger `WebhookEvent`) | SYSTEM (Inngest `reviewMuxWebhook`) | `applyMuxReady` `inngest.ts:75-91` — đồng thời `reviewState=AWAITING_REVIEW`, `readyAt`, metadata Mux | Head repoint `currentVersionId` (`:103`); clear approve cũ trên asset (`:99-102`); notify uploader (`:121-128`); task auto-flip A2 (T16); **thu hồi share khách nếu đang phơi** (`:150-154`) |
| V5 | `PROCESSING`\|`UPLOADED` → `FAILED` | webhook `video.asset.errored` / reconcile / abort / expire | SYSTEM hoặc Staff (abort) | errored: `applyMuxErrored` `inngest.ts:220-227`; abort tay: `upload-service.ts:571-577`; janitor expire >24h: `:763-767`; kẹt PROCESSING >24h: `inngest.ts:577-601` | Notify uploader "xử lý thất bại" (`inngest.ts:238-245`); abort set `UploadSession.abortedAt` |
| V6 | Xóa version | soft-delete → trash 30 ngày → purge | Staff (delete), ADMIN (purge ngay), SYSTEM (janitor purge 30d) | `versions.ts:135`; purge `purge.ts:372-390`; janitor `inngest.ts:633` | Xóa version sống cuối = trash cả stack; xóa head = re-point currentVersionId |

Janitor (cron 20:00 UTC → Inngest `reviewJanitor` `inngest.ts:526`): 5 sweep — expire UPLOADING>24h, redrive UPLOADED>15', reconcile PROCESSING>20' (hỏi thẳng Mux), re-enqueue WebhookEvent chưa consume 1h-7d, purge trash>30d.

### 2.2. `ReviewVersion.reviewState` (enum, quyết định của khách per-VERSION)

Enum `ReviewState` (`prisma/schema.prisma:1631`): `DRAFT → AWAITING_REVIEW → APPROVED ⇄ CHANGES_REQUESTED` (khách đổi ý được, lần cuối thắng — `share-decision.ts:7-10`).

| Transition | Sự kiện | Actor | file:line | Side effects |
|---|---|---|---|---|
| `DRAFT` → `AWAITING_REVIEW` | version READY (tự động) | SYSTEM | `inngest.ts:79` (video), `upload-service.ts:398` (ảnh) | — |
| `AWAITING_REVIEW`/`CHANGES_REQUESTED` → `APPROVED` | guest bấm Approve | Guest `/r/` (identity tự khai) | `share-decision.ts:44-47,217-248` (CAS trên state quan sát) | Head: asset `statusId='Hoàn tất'` (`:226-231`) + T21; non-head: chỉ version-level |
| `AWAITING_REVIEW`/`APPROVED` → `CHANGES_REQUESTED` | guest Request changes (+note ≤2000) | Guest | như trên | Head: asset `statusId='Revision'` + T20; note thành comment |
| repeat cùng decision | no-op 200 (idempotent), note vẫn lưu | Guest | `share-decision.ts:201-204` | notify staff cho note mới (`:102-124`) |
| `DRAFT` mà decide | **409** | — | `share-decision.ts:205-207` | — |

Gate trước khi decide (`share-decision.ts:137-186`): share phải gắn task (H1) → task không archived/cancelled (riêng `Hoàn tất` VẪN nhận decision muộn, chỉ chặn ở tầng task-sync — `:161-171`) → `isClientFacingPhase` (`:172-175`) → version READY (`:185-187`).

### 2.3. `ReviewAsset.statusId` (card status — mirror động của Task.status)

KHÔNG có bộ status riêng — đọc verbatim `VALID_TASK_STATUSES` (`src/lib/review/status.ts:1-6`, dropdown route `api/review/statuses`). Mapping "ý nghĩa → status" tập trung tại `REVIEW_STATUS_MAP` (`src/lib/review/status-map.ts:8-29`).

| Sự kiện | Ghi gì | Actor | file:line |
|---|---|---|---|
| Staff set/clear tay | statusId = giá trị bất kỳ trong 13 / `null` | Staff (folder-scope write + optimistic `rowVersion`) | `status.ts:34-90`; activity `STATUS_CHANGED` `:81-86`; no-op nếu trùng `:54` |
| Guest approve (head) | `'Hoàn tất'` | Guest | `share-decision.ts:226-231` |
| Guest request-changes (head) | `'Revision'` | Guest | như trên |
| Version mới READY thành head | **clear `'Hoàn tất'` → null** (chỉ clear đúng giá trị approved, không đụng status staff khác) | SYSTEM | `inngest.ts:99-102` |

Lịch sử trạng thái derive từ `ReviewActivity` — KHÔNG có model StatusHistory riêng (`status-history.ts:39`).

### 2.4. `ShareLink` (link guest `/r/{slug}` của module review)

Trạng thái derive runtime, không cột status: `ACTIVE` (mặc định) / `REVOKED` (`revokedAt`) / `EXPIRED` (`expiresAt`). Gate chain hợp đồng cho guest: `SHARE_NOT_FOUND` 404 → `SHARE_REVOKED` 410 → `SHARE_EXPIRED` 410 → `SHARE_PASSWORD_REQUIRED` 401, message not_found/revoked GIỐNG NHAU chống enumeration (`src/lib/review/share-auth.ts:93,101-103`).

| Transition | Sự kiện | Actor | file:line | Side effects |
|---|---|---|---|---|
| ∅ → ACTIVE | tạo share (items ≤20, password bcrypt, expiry, 4 toggle) | Staff | `shares.ts:197`; 1-click per asset `shares.ts:293` | — |
| ACTIVE ⇄ REVOKED | revoke / un-revoke (kill-switch, set/clear `revokedAt`) | creator HOẶC workspace-admin (`requireShareManageAccessFull` `shares.ts:773`) | `setShareRevoked` `shares.ts:695` | Guest nhận 410 ở request sau; comment giữ nguyên |
| ACTIVE → REVOKED (tự động) | **bản dựng mới thành head khi task đang phơi khách** | SYSTEM | `revokeClientExposureOnNewVersion` `task-sync.ts:483-486` | + task về A2 + clientReview=null (R5: khách không bao giờ thấy bản chưa duyệt) |
| REVOKED/ACTIVE → ∅ | hard-delete link | **workspace-admin-only** (`shares.ts:737-740`) | `deleteShare` `shares.ts:728` | Activity rows giữ lại |
| đổi/xóa password | mọi cookie unlock cũ chết (fingerprint sha256 passwordHash trong JWT unlock) | creator/admin | `share-auth.ts:117,140` | — |

---

## 3. Các entity còn lại có lifecycle thật

### 3.1. `WorkspaceInvitation` — String status (F03)

Giá trị: `PENDING | ACCEPTED | DECLINED | REVOKED | EXPIRED` (unique `[workspaceId, invitedUserId, status]` — 2 invite cùng user khác status sống song song, `schema.prisma:850`). TTL 14 ngày (`member-actions.ts:12,521`).

| Transition | Sự kiện | Role | file:line | Side effects |
|---|---|---|---|---|
| ∅ → PENDING | admin mời (tạo mới hoặc refresh expiresAt invite cũ) | workspace ADMIN | `inviteToWorkspace` `member-actions.ts:303` (re-invite `:527-548`) | Email mời (`:84`) + notification `WORKSPACE_INVITATION_RECEIVED` |
| PENDING → ACCEPTED | invitee chấp nhận (CAS `updateMany where PENDING + expiresAt>now`) | invitee (session sống, chặn LOCKED/CLIENT + sessionVersion `:628-637`) | `acceptWorkspaceInvitation` `member-actions.ts:756-767` | Tạo `WorkspaceMember` + `ProfileAccess(USER)`; notification `WORKSPACE_INVITATION_ACCEPTED`; fallback thông minh: id stale tự thay bằng invite PENDING mới nhất (`:724-736`) |
| PENDING → DECLINED | invitee từ chối | invitee | `member-actions.ts:971` | Notification `WORKSPACE_INVITATION_DECLINED` |
| PENDING → REVOKED | admin thu hồi | workspace ADMIN | `revokeWorkspaceInvitation` `member-actions.ts:1033` | — |
| PENDING → EXPIRED | **lazy** — retire khi user đã là member bấm lại invite cũ (`:700-703`); hết hạn thật chỉ bị CHẶN lúc accept (`:719,738`), KHÔNG có cron đánh dấu | SYSTEM (lazy) | `member-actions.ts:700-703` | — |

### 3.2. `UploadSession` (multipart R2 — F06)

Không cột status; state derive từ 3 timestamp (`getUploadStatus` `upload-service.ts:346`):

| State | Điều kiện | Vào bằng | file:line |
|---|---|---|---|
| Đang upload | `completedAt=null, abortedAt=null, expiresAt>now` | initiate (`expiresAt=+24h`) | `upload-service.ts:246,256` |
| Hoàn tất | `completedAt≠null` | complete (`:543`); self-heal crash-window khôi phục completedAt (`:819-825`) | — |
| Hủy | `abortedAt≠null` | abort tay (`:577`) hoặc janitor quá 24h (`:767`, kèm version→FAILED) | idempotent |

### 3.3. `ClientShareLink` (portal `/share/[token]` — F09/F15)

| Transition | Sự kiện | Role | file:line | Side effects |
|---|---|---|---|---|
| ∅ → ACTIVE | tạo link (raw token hiện đúng 1 lần, DB giữ SHA-256) | Admin | `createClientShareLink` `src/actions/share-link-actions.ts:46` | — |
| ACTIVE → REVOKED | set `revokedAt` (không un-revoke trong code) | Admin | `share-link-actions.ts:99-106` | Hiệu lực ngay (resolve check mỗi request) |
| (runtime) EXPIRED | `expiresAt` quá | — | đọc tại `share-link-actions.ts:133,146` + resolver | Uniform 404 |
| Điều kiện sống thêm | client của link phải `ACTIVE` hoặc `MERGED` (MERGED → follow `mergedIntoId`) | — | `src/lib/share-link-auth.ts:156,242` | Client vào Trash = link chết theo |

Sub-lifecycle notify-email của link (double-opt-in OTP): các cột `notifyEmail*` trên `ClientShareLink` (`schema.prisma:572`), gửi OTP `share-portal-actions.ts:617` (rate-limited), unsubscribe token riêng.

### 3.4. `Invoice` — enum `InvoiceStatus` (F14)

Enum: `DRAFT | SENT | PAID | OVERDUE | VOID` (`schema.prisma:915`). **Thực tế code chỉ dùng 3**: tạo là ghi thẳng `SENT` (`invoice-actions.ts:423` — "Default to SENT for now"); ⚰️ `DRAFT` chỉ là schema-default không ai ghi; ⚰️ `OVERDUE` không bao giờ được ghi (chỉ xuất hiện trong mock `desk-preview/DeskHarness.tsx:36`).

| Transition | Sự kiện | Role | file:line | Side effects |
|---|---|---|---|---|
| ∅ → SENT | tạo invoice từ task UNBILLED | Admin finance (`verifyFinanceAccess`) | `createInvoiceRecord` `invoice-actions.ts:314` (status `:423`) | Claim atomic tasks → `INVOICED` (`:443-452`); trừ deposit clamp (`:459-469`); email `invoiceCreated` (`:496`) |
| SENT → PAID | ghi nhận payment có `invoiceId` | Admin finance | `recordPayment` `src/actions/payment-actions.ts:89` (best-effort) | Tạo row `Payment` (sổ append-only, KHÔNG status — trả góp = nhiều row) |
| SENT/PAID → VOID | void (advisory lock + re-read chống double-refund) | Admin finance | `voidInvoice` `invoice-actions.ts:581-654` | Tasks → `UNBILLED` + gỡ invoiceId (`:631-637`); refund deposit đúng `clientDepositDeducted` (`:645-652`) |

### 3.5. `Payroll` + `PayrollLock` (F13 — tiền thật)

`Payroll.status` String default `"UNPAID"` (`schema.prisma:318`) nhưng **code không bao giờ tạo row UNPAID** — row chỉ sinh ra khi admin xác nhận chi:

| Transition | Sự kiện | Role | file:line | Side effects |
|---|---|---|---|---|
| ∅ → PAID | confirmPayment (upsert, cycle resolve server-side từ workspace.name) | workspace ADMIN | `payroll-actions.ts:64-91` | `paidAt`; **CHẶN nếu PayrollLock.isLocked** (`:47-53`); audit `payroll.locked` |
| PAID → ∅ | revertPayment = **DELETE row** (không flip status) | workspace ADMIN | `payroll-actions.ts:204-208` | **CHẶN nếu cycle locked** (`:186-191`, anti-fraud); audit `payroll.unlocked` |

`PayrollLock` (khoá sổ kỳ lương): ∅ → `isLocked=true` khi `calculateMonthlyBonus` chốt bonus (tx atomic: delete+recreate `MonthlyBonus`/`MonthlyRank` rồi upsert lock CUỐI — `bonus-actions.ts:339-413`); unlock = `revertMonthlyBonus` **xóa** bonus + rank + lock rows (`bonus-actions.ts:78-84`). Nghĩa là lock lifecycle: absent ⇄ locked (bằng create/delete, không flip cờ).

Payroll ĐẾM từ `Task.status`: pending = 10 status `SALARY_PENDING_STATUSES`, completed = `'Hoàn tất'` — vì vậy T11/T22/T23 là các sự kiện "đụng tiền".

### 3.6. `ClientTaskRequest` — enum `ClientRequestStatus` (F10)

Enum: `NEW | REVIEWING | ACCEPTED | REJECTED` (`schema.prisma:625`). ⚰️ `REVIEWING` không bao giờ được GHI — chỉ nằm trong filter đọc (`client-request-actions.ts:54`).

| Transition | Sự kiện | Role | file:line | Side effects |
|---|---|---|---|---|
| ∅ → NEW | khách gửi intake từ portal | Client portal (token) | `submitClientRequestViaToken` `share-portal-actions.ts:1350` (ghi `status:'NEW'` `:1426`) | Badge inbox admin đếm NEW (`client-request-actions.ts:91`) |
| NEW → ACCEPTED | admin duyệt → spawn Task `'Đang đợi giao'` + link taskId | profile ADMIN | `acceptClientRequest` `client-request-actions.ts:102-168` | audit `request.accepted`; chặn re-accept (`:108`) |
| NEW → ACCEPTED (không task) | duyệt qua Velox scan (N task tự tạo) | profile ADMIN | `markRequestAccepted` `:200-219` | idempotent |
| NEW → REJECTED | admin từ chối + note | profile ADMIN | `rejectClientRequest` `:171-193` | `rejectionNote` sanitize; ACCEPTED không thể reject (`:177`) |

### 3.7. `Client` — String status (F15)

Giá trị: `ACTIVE | SOFT_DELETED | MERGED` (+`deletedAt`, `mergedIntoId` — `schema.prisma:546-552`).

| Transition | Sự kiện | Role | file:line | Side effects |
|---|---|---|---|---|
| ACTIVE → SOFT_DELETED | vào Thùng rác (CẢ subtree sub-client, dưới name-lock) | workspace ADMIN | `deleteClient` `crm-actions.ts:260-292` | Task/Invoice giữ nguyên; ClientShareLink chết theo (§3.3); **KHÔNG set hardDeleteAfter → không có cron tự purge client** |
| SOFT_DELETED → ACTIVE | restore (check trùng tên từng node + trong chính batch) | workspace ADMIN | `restoreClient` `crm-actions.ts:297-376` | clear deletedAt + hardDeleteAfter |
| SOFT_DELETED → ∅ | purge tay, chặn nếu còn Invoice (FK Restrict) | workspace ADMIN | `permanentlyDeleteClient` `crm-actions.ts:417+` | Task detach (SetNull), Project/sub-client cascade |
| → MERGED | ⚰️ **KHÔNG có code nào ghi 'MERGED'** — trạng thái tồn dư của migration gộp client (đang pending trên prod). `mergeClientIntoParent` chỉ re-parent `parentId` (`crm-actions.ts:506`), không đổi status | (script migration ngoài app) | Đọc tại: `share-link-auth.ts:156,242` (follow mergedIntoId), `guest-notify.ts:80,213`; bị chặn merge tiếp (`crm-actions.ts:479`) | — |

### 3.8. `Workspace` / `Profile` — soft-delete 30 ngày + cron hard-delete (P6/F16)

`Workspace.status`: `ACTIVE | SOFT_DELETED` (⚰️ `SUSPENDED` trong comment schema — grep 0 chỗ ghi).

| Entity | Transition | Sự kiện | Role | file:line | Side effects |
|---|---|---|---|---|---|
| Workspace | ACTIVE → SOFT_DELETED | delete (hardDeleteAfter=+30d; fallback hard-delete nếu cột chưa migrate) | **OWNER** (hoặc global admin) | `deleteWorkspaceAction` `workspace-actions.ts:181-216` | audit `workspace.soft_deleted`; biến khỏi switcher |
| Workspace | SOFT_DELETED → ACTIVE | restore trong 30 ngày | OWNER | `restoreWorkspaceAction` `workspace-actions.ts:327-340` | clear deletedAt/hardDeleteAfter |
| Workspace | SOFT_DELETED → ∅ | **cron 03:00 daily** xóa cascade khi quá hardDeleteAfter | SYSTEM (CRON_SECRET) | `api/cron/hard-delete-workspaces/route.ts:47-76` | Audit `workspace.hard_deleted` GHI TRƯỚC khi delete |
| Profile | ACTIVE → SOFT_DELETED | delete (+30d — `PROFILE_HARD_DELETE_GRACE_DAYS` `profile-actions.ts:280`) | profile **OWNER** + `isSessionLive` | `deleteProfileAction` `profile-actions.ts:385-424` | audit `profile.soft_deleted` (workspaceId='SYSTEM') |
| Profile | SOFT_DELETED → ACTIVE | restore | OWNER + isSessionLive | `restoreProfileAction` `profile-actions.ts:429-459` | — |
| Profile | SOFT_DELETED → ∅ | **cron 03:30 daily** cascade (workspaces/tasks/members chết theo) | SYSTEM | `api/cron/hard-delete-profiles/route.ts:44-82` | audit trước khi delete |

### 3.9. `GuestSession` + `GuestEmailVerification` + `GuestSubscription` (F08)

| Entity | Lifecycle | file:line |
|---|---|---|
| `GuestSession` | ∅ → sống: tạo qua modal identity (`api/r/[slug]/identity/route.ts:35`) hoặc auto-identity client quen (email tổng hợp `noreply+client-{id}@review.invalid` — KHÔNG BAO GIỜ được coi là verified, `share-auth.ts:53-61,309`). Cookie raw-token TTL 30 ngày (`share-auth.ts:154-187`); **DB row không có expiry** — chết theo cascade ShareLink. Nhánh phụ: `emailVerifiedAt` set khi verify PIN (`schema.prisma:1937`); `lastSeenAt` throttle 1/phút |
| `GuestEmailVerification` (PIN 6 số) | ∅ → pending (`expiresAt=+10m`, tạo tại `guest-subscribe.ts:114`) → consumed (`consumedAt`) HOẶC locked (`attempts` ≥5 — `guest-subscribe.ts:163`). Không có cron dọn (auth-cleanup không đụng bảng này) |
| `GuestSubscription` | ∅ → active: verify PIN thành công, hoặc skip-PIN cho chính email của session (`request-pin/route.ts:68-70`), hoặc auto-subscribe khi guest decide (`share-decision.ts:283-289`) → `unsubscribedAt` (soft, giữ row audit) qua token RFC 8058 (`api/r/unsubscribe/route.ts:17`, `guest-subscribe.ts:268`). Unique `(email, assetId)` — sống sót rotate slug |

### 3.10. `EmailVerificationToken` / `PasswordResetOTP` (F01)

| Entity | Lifecycle | file:line |
|---|---|---|
| `EmailVerificationToken` (hash SHA-256, 3 purpose `EMAIL_VERIFICATION`/`PASSWORD_RESET`/`EMAIL_MIGRATION`) | ∅ → sống (signup `signup-actions.ts:302`; sau verify-OTP mint resetToken `password-reset-actions.ts:256`) → **used** (`usedAt` set atomic CAS — verify-email `api/auth/verify-email/route.ts:38-44` kèm `User.emailVerified=true` + audit `auth.email_verified`; reset-password consume `password-reset-actions.ts:337-343`) → ∅ (cron auth-cleanup 04:00 xóa token hết hạn — `api/cron/auth-cleanup/route.ts:47-49`, cron duy nhất so sánh secret `timingSafeEqual`) |
| `PasswordResetOTP` (OTP 6 số hash, purpose `PASSWORD_RESET`/`EMAIL_MIGRATION`) | ∅ → pending (request: invalidate MỌI OTP pending cũ trước — `password-reset-actions.ts:126-127`) → mỗi lần sai `attemptCount`+1 với optimistic-lock, **≥5 → `invalidatedAt`** (`:225-238`) → đúng → **`consumedAt`** + mint EmailVerificationToken resetToken (`:269-274`) → ∅ (cron xóa expired / consumed >7 ngày — `auth-cleanup/route.ts:52-59`). Đổi mật khẩu xong gửi email cảnh báo (`:396`) |

### 3.11. `Notification` (F12)

| Transition | Sự kiện | Role | file:line | Side effects |
|---|---|---|---|---|
| ∅ → unread | `createNotificationInternal` (mọi biến cố) | SYSTEM | `notification-actions.ts:24` (isRead:false `:102`) | Kèm 1 lần thử web-push (`:58-65`) + email registry (`maybeSendNotificationEmail`, claim atomic `emailSentAt` chống double — `notification-email.ts:107-113`) + broadcast Supabase realtime |
| unread → read | mark 1 cái / mark-all | chính user | `notification-actions.ts:187-190` / `:202-203` | — |
| → archived | archive (kèm set read) | chính user | `notification-actions.ts:222` | — |
| → ∅ | **cron 02:00**: xóa archived >30d + read >90d | SYSTEM | `api/cron/cleanup-notifications/route.ts:35-49` | — |

### 3.12. Các lifecycle nhỏ còn lại (đủ bảng, 1 dòng/entity)

| Entity | States + transitions | file:line |
|---|---|---|
| `ProfileAccessRequest` (cross-team, F03) | `PENDING` (xin quyền `cross-team-actions.ts:69`) → `APPROVED` (`:123`, admin profile đích, cấp `ProfileAccess`) \| `REJECTED` (`:156`). Unique (userId, targetProfileId) | `src/actions/cross-team-actions.ts` |
| `Contact` (danh bạ chat) | `PENDING` (gửi lời mời `:100-110`) → `ACCEPTED` (`:168`) \| `BLOCKED` (`:206,237,265-269`); unfriend/unblock = **delete row** (`:242`) | `src/actions/contact-actions.ts` |
| `UserPresence` | upsert `ONLINE`/`AWAY`/`BUSY`/`OFFLINE` mỗi heartbeat — ⚠️ action nhận cả `'BUSY'` trong khi schema comment chỉ ghi ONLINE\|OFFLINE\|AWAY (String tự do nên không lỗi) | `tracking-actions.ts:91-101` |
| `TaskComment` | sống → `isDeleted=true` (soft, `task-comment-actions.ts:326`); action-item resolve/unresolve (`:427+`); mọi read path filter `isDeleted:false` | `src/actions/task-comment-actions.ts` |
| `ReviewComment` | sống → resolve toggle (`resolvedAt`/`resolvedById`, `comments.ts:493`; auto-resolve cả round khi editor confirm-fix `task-sync.ts:321-333`) → soft-delete `deletedAt` (author hoặc admin, `comments.ts:456`) | `src/lib/review/comments.ts` |
| `ReviewFolder`/`ReviewAsset` (trash) | sống → trash 30d (`deleteItems` `folders.ts:811`, batch `deleteBatchId`) → restore (`folders.ts:997`, re-home về root nếu parent mất) \| purge (admin ngay `purge.ts:372-390` / janitor 30d `inngest.ts:633` — teardown Mux+R2+rows) | parts/05 §2 |
| `WebhookEvent` (ledger Mux) | ∅ → chưa xử lý (`processedAt=null`) → processed (persist-then-claim CUỐI CÙNG `inngest.ts:323-329`); kẹt 1h-7d → janitor re-enqueue (`inngest.ts:606-627`) | `api/webhooks/mux/route.ts:74-80` |
| `Session` (JWT) — không phải bảng状态 nhưng có vòng đời | mint khi login (TTL 30d, rolling-refresh middleware) → thu hồi bằng `User.sessionVersion`+1 (logout-all / reset password / LOCKED) — so DB tại DAL (`isSessionLive`) | parts/09 §session |
| `Agency.status` | ⚰️ default `"ACTIVE"` — không tìm thấy code đổi giá trị (không có file agency-actions.ts) | `schema.prisma:724` |
| `MonthlyRank` | tạo + `isLocked` theo chu kỳ bonus (delete+recreate trong cùng tx với PayrollLock — §3.5) | `bonus-actions.ts:346-397` |

---

## 4. Ghi chú cho Phase 6 (tránh trùng với Phase 1 diagrams)

Tại thời điểm viết file này (2026-08-02), `docs/system-audit/01-diagrams/` mới có **3 file `class.mmd`** (`F03-membership-invite`, `F05-marketplace`, `F10-client-request-inbox`) — **CHƯA có bất kỳ `state.mmd` nào**. Phase 1 vẫn đang chạy (PROGRESS.md).

Khi Phase 1 hoàn tất, các state diagram dự kiến sẽ TRÙNG phạm vi với các bảng ở đây — Phase 6 chỉ nhúng diagram, còn bảng thuộc tính/side-effects lấy từ file này làm nguồn sự thật:

| Bảng trong file này | Folder Phase 1 dự kiến chứa state.mmd tương ứng |
|---|---|
| §1 Task.status (13 giá trị + 25 transition) | `01-diagrams/F04-task-lifecycle/state.mmd` |
| §2.1 ReviewVersion.pipelineStatus | `01-diagrams/F06-review-upload/state.mmd` |
| §2.2 ReviewState + §2.3 ReviewAsset.statusId | `01-diagrams/F07-team-review/state.mmd`, `F08-guest-decision/state.mmd` |
| §3.1 WorkspaceInvitation | `01-diagrams/F03-membership-invite/state.mmd` |
| §3.4/§3.5 Invoice + Payroll/PayrollLock | `01-diagrams/F13-payroll/state.mmd`, `F14-finance/state.mmd` |
| §3.6 ClientTaskRequest | `01-diagrams/F10-client-request-inbox/state.mmd` |
| §3.7/§3.8 Client/Workspace/Profile soft-delete | `01-diagrams/P6-trash-restore/state.mmd` |

Điểm cần Phase 6 nhấn mạnh (rút từ bảng trên): (1) FSM tay đã tắt — hàng rào thật là RBAC + auto-transition guard; (2) 3 sự kiện "đụng tiền" là T11/T22/T23 (mọi đường vào `Hoàn tất`); (3) 5 giá trị enum ⚰️ chết trong schema: `Invoice.DRAFT`/`OVERDUE`, `ClientRequestStatus.REVIEWING`, `Workspace.SUSPENDED`, `Client.MERGED` (chỉ migration ghi); (4) 2 entity soft-delete KHÔNG có cron purge: `Client` (chủ đích, purge tay) và `GuestEmailVerification` (thiếu dọn).

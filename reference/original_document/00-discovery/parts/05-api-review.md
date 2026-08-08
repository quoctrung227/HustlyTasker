# 05 — Inventory API Module Video Review: `/api/review/**` (staff) + `/api/r/**` (guest share)

> Phạm vi: 63 file `route.ts` thật (44 dưới `src/app/api/review/`, 19 dưới `src/app/api/r/`). Mọi số dòng lấy từ code tại thời điểm audit. Không phát hiện route trùng lặp/dead-code trong 2 cây này — bản nội bộ và bản guest của cùng chức năng (comments, playback-token, download, attachments) là 2 route CỐ Ý tách đôi với 2 cơ chế auth khác nhau.

## 0. Cơ chế phân quyền chung của module

### 0.1 Staff (`/api/review/**`)

| Thành phần | File | Cơ chế |
|---|---|---|
| Error boundary | `src/lib/review/route-auth.ts:21` (`withReviewRoute`) | Bọc mọi handler staff: `ReviewAccessError`→401/403, `MuxError`→502, còn lại→500 (không leak message). |
| Auth chính | `src/lib/review/access.ts:32` (`requireReviewAccess`) | `getSession()` (jose JWT) → chặn role `LOCKED`/`CLIENT` (`access.ts:41`); nếu truyền `workspaceId` thì gọi thêm `verifyWorkspaceAccess(workspaceId,'MEMBER')` (`access.ts:50`). **KHÔNG có hệ auth thứ hai** — wrap session thật của app. |
| `isAdmin` | `src/lib/review/access.ts:56-61` | **Workspace-scoped**: OWNER/ADMIN của workspace HOẶC profile của nó — KHÔNG dùng `User.role` toàn cục (chống escalation, ghi chú tại `access.ts:51-55`). |
| Vị trí gọi auth | Trong **service layer** (`src/lib/review/*.ts`), không phải trong route | Route chỉ parse + gọi service; MỌI service tự re-derive `workspaceId` từ row rồi gọi `requireReviewAccess({workspaceId})` (defense-in-depth, vd `folders.ts:199,368,429,661,703,829,1015,1157,1255,1572`; `versions.ts:75,142,214,292`; `upload-service.ts:158,200,344,473,560,607,671,874,908`; `shares.ts:198,301,562,608,737,773`; `comments.ts:111`; `task-sync.ts:35,220`; `status.ts:23,44`; `status-history.ts:42`; `task-assets.ts:98`; `download-zip.ts:79`; `purge.ts:389`). |
| Folder-scope editor (FR-03) | `src/lib/review/folder-scope.ts:32` (`getFolderScope`) + `assertAssetInScope:107` / `assertVersionInScope:120` / `assertFolderPathMutable:96` | Editor (không phải workspace-admin) chỉ thấy/sửa folder theo materialized path suy từ: task được giao (`Task.assigneeId`), asset của task đó, folder mình tạo (`createdById`). Admin/owner = `unrestricted`. Comment funnel gác mọi entry (`comments.ts:112-118`). |
| Rate-limit | **KHÔNG có** trên staff routes | Chỉ session-based; DB rate-limiter chỉ dùng cho guest. |

### 0.2 Guest (`/api/r/**`)

| Thành phần | File | Cơ chế |
|---|---|---|
| Error boundary | `src/lib/review/route-auth.ts:49` (`withShareRoute`) | Như trên nhưng message tiếng Anh; internal-auth throw = bug → 500 chung. |
| Gate slug | `src/lib/review/share-auth.ts:93` (`requireShare`) | Chuỗi HỢP ĐỒNG: `SHARE_NOT_FOUND` 404 → `SHARE_REVOKED` 410 → `SHARE_EXPIRED` 410 → `SHARE_PASSWORD_REQUIRED` 401; message của not_found/revoked GIỐNG NHAU (anti-enumeration, `share-auth.ts:101-103`). Slug regex `^[A-Za-z0-9_-]{8,24}$` trước khi chạm DB (`share-auth.ts:40`). |
| Unlock password | cookie `rv_unlock_{slug}` — JWT HS256 ký bằng `REVIEW_COOKIE_SECRET` (`share-auth.ts:120-144`) | TTL min(24h, hạn share); embed fingerprint sha256 của passwordHash → đổi/xoá mật khẩu là mọi cookie unlock cũ chết (`share-auth.ts:117,140`). |
| Danh tính guest | cookie `rv_guest_{slug}` — token random 32 byte, DB chỉ lưu `sha256(token)` trên `GuestSession` (`share-auth.ts:154-187`) | TTL 30 ngày. `resolveGuestForWrite` (`share-auth.ts:336`): cookie sống → modal name+email → auto-identity client quen (`createLinkClientGuestSession:309`, email tổng hợp `noreply+client-{id}@review.invalid` — KHÔNG bao giờ được coi là email đã verify cho sign-off, `share-auth.ts:53-61`). |
| Scope item | `src/lib/review/share-guest.ts:137` (`assertVersionInShare`) | Version phải thuộc asset nằm trong `ShareLinkItem` (asset trực tiếp hoặc trong subtree folder share); `showAllVersions=false` ⇒ chỉ currentVersion (`share-guest.ts:166`). |
| Rate-limit | `src/lib/review/rate-limit-db.ts:17` (`limitDb`) — fixed-window trên Postgres (`RateLimitBucket`, 1 upsert atomic) | Fail-open cho read, `failClosed:true` cho unlock (chống brute-force khi limiter sập, `rate-limit-db.ts:44-45`). IP lấy `x-real-ip` → `x-vercel-forwarded-for` → phần tử PHẢI nhất của XFF (chống rotate header, fix G1, `rate-limit-db.ts:59-70`). |
| TTL token media guest | `share-auth.ts:371-378` | Mux/R2 token = min(6h, thời gian còn lại tới hạn share), floor 60s. |

### 0.3 Status machine (trạng thái thật từ code)

**3 trục trạng thái độc lập:**

1. **`ReviewPipelineStatus`** (per-version, pipeline file — `prisma/schema.prisma:1623`): `UPLOADING` → `UPLOADED` → `PROCESSING` → `READY` | `FAILED`.
2. **`ReviewState`** (per-version, quyết định của khách — `prisma/schema.prisma:1632`): `DRAFT` → `AWAITING_REVIEW` (auto khi READY) → `CHANGES_REQUESTED` ⇄ `APPROVED` (khách được đổi ý, lần cuối thắng — `share-decision.ts:7-10`).
3. **Asset card status** (`ReviewAsset.statusId`) = **string trạng thái task của app**, đọc động từ `VALID_TASK_STATUSES` (`src/lib/task-statuses.ts:18-39`, 13 giá trị): `Đang đợi giao`, `Nhận task`, `Đã nhận task`, `Đang thực hiện`, **6 status video A2–A7**: `Đã nộp video (nội bộ)` (A2), `Đang sửa feedback (nội bộ)` (A3), `Đã sửa feedback (nội bộ)` (A4), `Đã gửi video (khách)` (A5), `Đã nhận feedback (khách)` (A6), `Đã sửa feedback (khách)` (A7), cùng `Revision`, `Quá hạn`, `Hoàn tất`, `Đã hủy`. Module review KHÔNG hardcode bộ status riêng (`src/lib/review/status.ts:1-6`).

**Guard auto-transition** `STATUS_TRANSITIONS` (`src/lib/task-statuses.ts:199-218`) — chỉ áp cho auto (Inngest/webhook/guest), KHÔNG enforce đổi tay (R10): A2←{Đang thực hiện, Revision, A4, A5}; A3←{A2, A4}; A4←{A3}; A5←{A4, A2, A7}; A6←{A5}; A7←{A6}. Task terminal (`Hoàn tất`/`Đã hủy`) không bao giờ bị auto-flip (`isTerminalStatus`, `task-statuses.ts:156`). Mapping "ý nghĩa → status" tập trung ở `REVIEW_STATUS_MAP` (`src/lib/review/status-map.ts:8-29`).

---

## 1. Nhóm Uploads (staff)

| Method | Path | File:line | Guard thật | Mục đích |
|---|---|---|---|---|
| POST | `/api/review/uploads/initiate` | `src/app/api/review/uploads/initiate/route.ts:28` | `withReviewRoute` → `initiateUpload` (`upload-service.ts:127`, auth `:158`/`:200` theo target folder/asset) + Idempotency-Key header | Tạo asset/version + R2 multipart, trả presigned part URLs. |
| GET | `/api/review/uploads/[uploadSessionId]` | `src/app/api/review/uploads/[uploadSessionId]/route.ts:14` | `withReviewRoute` → `getUploadStatus` (`upload-service.ts:600`, auth `:607`) | Poll trạng thái upload/processing (client poll 3s). |
| POST | `/api/review/uploads/[uploadSessionId]/complete` | `src/app/api/review/uploads/[uploadSessionId]/complete/route.ts:22` | `withReviewRoute` → `completeUpload` (`upload-service.ts:463`, auth `:473`) | CompleteMultipartUpload R2; ảnh→READY, video→PROCESSING + Inngest `review/upload.completed`. Idempotent. |
| POST | `/api/review/uploads/[uploadSessionId]/abort` | `src/app/api/review/uploads/[uploadSessionId]/abort/route.ts:15` | `withReviewRoute` → `abortUpload` (`upload-service.ts:551`, auth `:560`) | Abort multipart + dọn version/asset rác. Idempotent. |

## 2. Nhóm Folders / Tree / Items / Trash (staff)

| Method | Path | File:line | Guard thật | Mục đích |
|---|---|---|---|---|
| GET | `/api/review/tree?workspaceId=` | `src/app/api/review/tree/route.ts:9` | `withReviewRoute` → `getFolderTree` (`folders.ts:632`, auth `:635`) | Cây folder cho sidebar module Tệp. |
| POST | `/api/review/folders` | `src/app/api/review/folders/route.ts:16` | `withReviewRoute` → `createFolder` (`folders.ts:194`, auth `:199`) | Tạo folder. |
| POST | `/api/review/folders/batch` | `src/app/api/review/folders/batch/route.ts:19` | `withReviewRoute` → `createFolderTree` (`folders.ts:303`, auth `:308`) | Tái tạo cây folder từ folder-upload (webkitdirectory), cap ≤250 folder/≤10 cấp. |
| GET | `/api/review/folders/[id]` | `src/app/api/review/folders/[id]/route.ts:12` | `withReviewRoute` → `getFolder` (`folders.ts:365`, auth `:368`) | Chi tiết folder + breadcrumb. |
| PATCH | `/api/review/folders/[id]` | `src/app/api/review/folders/[id]/route.ts:22` | `withReviewRoute` → `renameFolder` (`folders.ts:654`, auth `:661`) + optimistic lock `expectedRowVersion` | Đổi tên folder. |
| GET | `/api/review/folders/[id]/children` | `src/app/api/review/folders/[id]/children/route.ts:14` | `withReviewRoute` → `listChildren` (`folders.ts:412`, auth `:429`/`:443`; lọc theo folder-scope FR-03) | List con của folder (`root` alias gốc workspace); sort/cursor. |
| GET | `/api/review/folders/[id]/manifest` | `src/app/api/review/folders/[id]/manifest/route.ts:14` | `withReviewRoute` → `getFolderManifest` (`folders.ts:1567`, auth `:1572`) | Manifest tải folder: danh sách head-version READY + đường dẫn tương đối. |
| POST | `/api/review/items/move` | `src/app/api/review/items/move/route.ts:24` | `withReviewRoute` → `moveItems` (`folders.ts:683`, auth `:703`) | Di chuyển folder/asset (bulk ≤200, optimistic lock). |
| POST | `/api/review/items/copy` | `src/app/api/review/items/copy/route.ts:19` | `withReviewRoute` → `copyItems` (`folders.ts:1235`, auth `:1255`) | Copy/duplicate (copy-on-reference). |
| POST | `/api/review/items/delete` | `src/app/api/review/items/delete/route.ts:17` | `withReviewRoute` → `deleteItems` (`folders.ts:811`, auth `:829`; guard creator FR-B07 dùng `isAdmin` workspace-scoped) | Soft-delete vào trash 30 ngày. |
| GET | `/api/review/trash?workspaceId=` | `src/app/api/review/trash/route.ts:9` | `withReviewRoute` → `listTrash` (`folders.ts:901`, auth `:906`) | List "Đã xóa gần đây". |
| POST | `/api/review/trash/restore` | `src/app/api/review/trash/restore/route.ts:18` | `withReviewRoute` → `restoreItems` (`folders.ts:997`, auth `:1015`) | Khôi phục từ trash (re-home về root nếu parent mất). |
| POST | `/api/review/trash/purge` | `src/app/api/review/trash/purge/route.ts:18` | `withReviewRoute` → `purgeItemsAuthorized` (`purge.ts:372`, auth `:389`, **chặn non-admin `:390`**) | **ADMIN-only** xóa vĩnh viễn ngay (teardown Mux+R2+rows như cron đêm). |

## 3. Nhóm Assets / Versions / Stack (staff)

| Method | Path | File:line | Guard thật | Mục đích |
|---|---|---|---|---|
| PATCH | `/api/review/assets/[id]` | `src/app/api/review/assets/[id]/route.ts:17` | `withReviewRoute` → `renameAsset` (`folders.ts:1150`, auth `:1157`) | Đổi display-name asset (không đụng fileName version). |
| GET | `/api/review/assets/[id]/versions` | `src/app/api/review/assets/[id]/versions/route.ts:12` | `withReviewRoute` → `listVersions` (`versions.ts:72`, auth `:75`) | List version của stack (modal Manage Versions). |
| POST | `/api/review/assets/[id]/stack` | `src/app/api/review/assets/[id]/stack/route.ts:15` | `withReviewRoute` → `mergeStacks` (`versions.ts:281`, auth `:292`) | Gộp stack nguồn vào asset này thành version mới nhất (FR-C01). |
| DELETE | `/api/review/versions/[id]` | `src/app/api/review/versions/[id]/route.ts:13` | `withReviewRoute` → `deleteVersion` (`versions.ts:135`, auth `:142`) | Xóa 1 version (xóa version sống cuối = trash cả stack; xóa head = re-point currentVersionId). |
| POST | `/api/review/versions/[id]/remove-from-stack` | `src/app/api/review/versions/[id]/remove-from-stack/route.ts:13` | `withReviewRoute` → `removeFromStack` (`versions.ts:209`, auth `:214`) | Tách version ra thành asset độc lập cùng folder (FR-C03). |
| POST | `/api/review/versions/[id]/download-url` | `src/app/api/review/versions/[id]/download-url/route.ts:15` | `withReviewRoute` → `getVersionDownloadUrl` (`upload-service.ts:902`, auth `:908`) | Presigned R2 GET file gốc cho version READY (nội bộ KHÔNG có approval gate — gate đó chỉ guest). |
| POST | `/api/review/versions/[id]/playback-token` | `src/app/api/review/versions/[id]/playback-token/route.ts:15` | `withReviewRoute` → `getVersionPlaybackTokens` (`upload-service.ts:868`, auth `:874`) | Mint Mux signed token 6h (playback/thumbnail/storyboard). |
| GET | `/api/review/download-zip?folders=&assets=` | `src/app/api/review/download-zip/route.ts:29` | `withReviewRoute` → `collectZipFiles` (`download-zip.ts:55`, auth `:79` + folder-scope FR-03); authorize TRƯỚC khi stream | Stream 1 file .zip (STORE, không nén lại) của folder/asset chọn, thẳng từ R2, `maxDuration=300`. |
| POST | `/api/review/task-upload/initiate` | `src/app/api/review/task-upload/initiate/route.ts:22` | `withReviewRoute` → `initiateTaskUpload` (`upload-service.ts:649`, auth `:671`) + Idempotency-Key | "Up thẳng video" từ task-drawer: tự resolve/tạo cây folder từ task, auto-version lên deliverable. |

## 4. Nhóm Comments / Reactions / Attachments (staff)

Mọi hàm comment đi qua funnel `resolveVersionCtx`/`resolveCommentCtx` (`comments.ts:106-129`): 404 nếu version/asset xóa → `requireReviewAccess({workspaceId})` (`comments.ts:111`) → `assertVersionInScope` FR-03 (`comments.ts:112-118`).

| Method | Path | File:line | Guard thật | Mục đích |
|---|---|---|---|---|
| GET | `/api/review/versions/[id]/comments` | `src/app/api/review/versions/[id]/comments/route.ts:13` | funnel trên → `listComments` (`comments.ts:224`) | List + delta-poll (`?since=`), sort/filter (unresolved/internal/public/mine). |
| POST | `/api/review/versions/[id]/comments` | `src/app/api/review/versions/[id]/comments/route.ts:30` | funnel trên → `createComment` (`comments.ts:282`) | Tạo comment/reply (kèm timecode/range, annotation, isInternal, attachments). |
| PATCH | `/api/review/comments/[id]` | `src/app/api/review/comments/[id]/route.ts:13` | funnel → `editComment` (`comments.ts:439`, chỉ author) | Sửa body comment. |
| DELETE | `/api/review/comments/[id]` | `src/app/api/review/comments/[id]/route.ts:20` | funnel → `deleteComment` (`comments.ts:456`, author HOẶC admin) | Xóa comment. |
| POST / DELETE | `/api/review/comments/[id]/resolve` | `src/app/api/review/comments/[id]/resolve/route.ts:13,18` | funnel → `setResolved` (`comments.ts:493`) | Resolve / un-resolve (reply không resolve riêng — 404). |
| POST | `/api/review/comments/[id]/reactions` | `src/app/api/review/comments/[id]/reactions/route.ts:13` | funnel → `addReaction` (`comments.ts:518`) | Thêm emoji reaction (idempotent). |
| DELETE | `/api/review/comments/[id]/reactions/[emoji]` | `src/app/api/review/comments/[id]/reactions/[emoji]/route.ts:12` | funnel → `removeReaction` (`comments.ts:535`) | Gỡ reaction của chính mình. |
| POST | `/api/review/comment-attachments/initiate` | `src/app/api/review/comment-attachments/initiate/route.ts:12` | `withReviewRoute` → `initiateAttachment` (`comments.ts:553`, auth `:558` — **session-only, không workspace-scope** vì chưa gắn version) | Presign R2 PUT cho ảnh đính kèm comment (image/* ≤10MB). |
| GET | `/api/review/comment-attachments/[id]/raw` | `src/app/api/review/comment-attachments/[id]/raw/route.ts:13` | `withReviewRoute` → `getAttachmentRawUrl` (`comments.ts:577`, re-check qua comment→version→asset→workspace) | 302 tới signed R2 URL ngắn hạn (img src ổn định qua poll 5s). |

## 5. Nhóm Statuses / Status-history / Confirm-fix / Approve-send / Feedback-done (staff — trục F7–F10)

| Method | Path | File:line | Guard thật | Mục đích |
|---|---|---|---|---|
| GET | `/api/review/statuses` | `src/app/api/review/statuses/route.ts:10` | `withReviewRoute` → `getReviewStatusOptions` (`status.ts:22`, auth `:23` session-only) | Options dropdown = `VALID_TASK_STATUSES` verbatim (FR-D01). |
| PUT | `/api/review/assets/[id]/status` | `src/app/api/review/assets/[id]/status/route.ts:18` | `withReviewRoute` → `setAssetStatus` (`status.ts:34`, auth `:44` + folder-scope write `:47`, optimistic lock atomic `:63-69`) | Set/clear card status asset; ghi audit `ReviewActivity.STATUS_CHANGED`. |
| GET | `/api/review/assets/[id]/status-history` | `src/app/api/review/assets/[id]/status-history/route.ts:12` | `withReviewRoute` → `getAssetStatusHistory` (`status-history.ts:39`, auth `:42` + scope read `:44`) | "Lịch sử trạng thái" — derive từ `ReviewActivity` (KHÔNG có model ReviewStatusHistory riêng). |
| POST | `/api/review/assets/[id]/feedback-done` | `src/app/api/review/assets/[id]/feedback-done/route.ts:13` | `withReviewRoute` → `markFeedbackDone` (`task-sync.ts:272`; **admin-only `:274`**; predecessor-guard A2/A4→A3) | F8: admin chốt phiên feedback nội bộ → task A3 + email editor. |
| POST | `/api/review/assets/[id]/confirm-fix` | `src/app/api/review/assets/[id]/confirm-fix/route.ts:15` | `withReviewRoute` → `confirmFixDone` (`task-sync.ts:298`; **admin HOẶC assignee `:300-301`**; predecessor-guard) | F9: editor xác nhận đã sửa → A3→A4 (vòng nội bộ) hoặc A6→A7 (vòng khách) + notify manager. |
| POST | `/api/review/assets/[id]/approve-send` | `src/app/api/review/assets/[id]/approve-send/route.ts:15` | `withReviewRoute` → `approveInternalAndSendToClient` (`task-sync.ts:377`; **admin-only `:381`**; predecessor-guard A2/A4/A7→A5) | F10: admin duyệt nội bộ & gửi khách → task A5 + bridge portal (ShareLink + `clientReview='AWAITING'` + email khách). |
| POST | `/api/review/tasks/[taskId]/confirm-complete` | `src/app/api/review/tasks/[taskId]/confirm-complete/route.ts:13` | `withReviewRoute` → `confirmTaskHoanTat` (`task-sync.ts:26`, auth `:35`; delegate `updateTaskStatus` có RBAC + FSM riêng `:37`) | Xác nhận chuyển task sang `Hoàn tất` từ banner drawer (FR-D02). |
| GET | `/api/review/tasks/[taskId]/assets` | `src/app/api/review/tasks/[taskId]/assets/route.ts:16` | `withReviewRoute` → `getTaskAssets` (`task-assets.ts:77`, auth `:98`) | Block BÀN GIAO trong task-drawer (poll 3s khi đang upload/processing). |

## 6. Nhóm Shares (staff quản lý link `/r`)

| Method | Path | File:line | Guard thật | Mục đích |
|---|---|---|---|---|
| POST | `/api/review/shares` | `src/app/api/review/shares/route.ts:32` | `withReviewRoute` → `createShareLink` (`shares.ts:197`, auth `:198`; validate item sống + cùng workspace) | Tạo share link (items ≤20, password bcrypt, expiry, allowComments/Download/downloadOnlyWhenApproved/showAllVersions). |
| GET | `/api/review/shares?workspaceId=…` | `src/app/api/review/shares/route.ts:38` | `withReviewRoute` → `listShares` (`shares.ts:561`, auth `:562`; USER chỉ thấy link mình tạo + link trên task mình được giao, ADMIN thấy hết) | List share theo workspace/task/asset/state. |
| GET | `/api/review/shares/[id]` | `src/app/api/review/shares/[id]/route.ts:29` | `withReviewRoute` → `getShareDetail` (`shares.ts:605`, auth `:608`) | Chi tiết + activity gần nhất. |
| PATCH | `/api/review/shares/[id]` | `src/app/api/review/shares/[id]/route.ts:34` | `withReviewRoute` → `updateShareOptions` (`shares.ts:667` → `requireShareManageAccess`: **creator hoặc workspace-admin**, xem `:773-780`) + optimistic lock | Sửa options link. |
| DELETE | `/api/review/shares/[id]` | `src/app/api/review/shares/[id]/route.ts:41` | `withReviewRoute` → `deleteShare` (`shares.ts:728`; **workspace-admin-only `:737-740`**, KHÔNG dùng global role) | Hard-delete link (activity rows giữ lại). |
| POST | `/api/review/shares/[id]/revoke` | `src/app/api/review/shares/[id]/revoke/route.ts:18` | `withReviewRoute` → `setShareRevoked` (`shares.ts:695` → `requireShareManageAccessFull:773` creator|admin) | Revoke/un-revoke (kill-switch; guest nhận 410 ở request sau). |
| POST | `/api/review/assets/[id]/share` | `src/app/api/review/assets/[id]/share/route.ts:14` | `withReviewRoute` → `getOrCreatePrimaryShareForAsset` (`shares.ts:293`, auth `:301`) | "Copy link khách" 1 click: get-or-create share ACTIVE chính của asset. |

## 7. Guest `/api/r/[slug]/**` — share công khai (không session)

Tất cả (trừ `unsubscribe`) đều: `withShareRoute` + `limitDb(per slug+IP)` + `requireShare(slug, cookies)` (gate 404→410→410→401) trước khi làm gì khác.

### 7.1 Nội dung / Unlock / Identity

| Method | Path | File:line | Guard thật (rate-limit / unlock / identity) | Mục đích |
|---|---|---|---|---|
| GET | `/api/r/[slug]` | `src/app/api/r/[slug]/route.ts:18` | 120/60s per slug+IP; `requireShare`; guest cookie optional | Nội dung share dạng DTO đã cắt gọt (không workspace/task/uploader/email). |
| POST | `/api/r/[slug]/unlock` | `src/app/api/r/[slug]/unlock/route.ts:21` | **5/60s per slug+IP, `failClosed:true`** (`:25`); `resolveShareGate` không qua password-gate (route này LÀ gate); bcrypt compare `:44` | Nhập mật khẩu → set cookie `rv_unlock_{slug}` (JWT, TTL min(24h, hạn share)). |
| POST | `/api/r/[slug]/identity` | `src/app/api/r/[slug]/identity/route.ts:35` | 5/60s; `requireShare`; idempotent trừ khi `force:true` (sign-off AUDIT H2, `:57-60`) | Modal Name+Email → tạo `GuestSession`, set cookie `rv_guest_{slug}` (chỉ trả về name, không leak email). |
| POST | `/api/r/[slug]/events` | `src/app/api/r/[slug]/events/route.ts:33` | 60/60s; `requireShare`; chỉ nhận `link_opened`/`asset_viewed` (loại khác bị reject); debounce 30' bằng cookie `rv_t_{slug}`; `asset_viewed` phải qua `assertVersionInShare` | Ghi analytics viewCount/lastViewedAt + activity xem asset. |

### 7.2 Media (playback / view / download)

| Method | Path | File:line | Guard thật | Mục đích |
|---|---|---|---|---|
| POST | `/api/r/[slug]/playback-token` | `src/app/api/r/[slug]/playback-token/route.ts:29` | 30/60s; `requireShare` + `assertVersionInShare`; version phải READY + có muxPlaybackId | Mint Mux signed tokens scope share, TTL min(6h, hạn share); side-effect asset_viewed (debounce 30'). |
| GET | `/api/r/[slug]/versions/[versionId]/view-url` | `src/app/api/r/[slug]/versions/[versionId]/view-url/route.ts:23` | 60/60s; `requireShare` + `assertVersionInShare`; chỉ IMAGE (video 404) | Presign 15' bản preview ảnh **downscale + watermark** (fix B1 — bản gốc chỉ qua download-url có gate). |
| GET | `/api/r/[slug]/download-url?versionId=` | `src/app/api/r/[slug]/download-url/route.ts:22` | 30/60s; `requireShare`; **gate duyệt guest-only**: `allowDownload && (!downloadOnlyWhenApproved \|\| reviewState===APPROVED)` (`:30,44-46`); `assertVersionInShare`; READY+r2Key | Presigned R2 GET 15' file gốc (attachment) + activity `downloaded`. |

### 7.3 Comments / Reactions / Attachments guest

| Method | Path | File:line | Guard thật | Mục đích |
|---|---|---|---|---|
| GET | `/api/r/[slug]/versions/[versionId]/comments` | `src/app/api/r/[slug]/versions/[versionId]/comments/route.ts:18` | 120/60s; `requireShare`; `isInternal=false` ép trong SQL của service (`listGuestComments`) | Poll 5s comment công khai (delta `?since=`, deletedIds public-only — comment nội bộ KHÔNG bao giờ lộ). |
| POST | `/api/r/[slug]/comments` | `src/app/api/r/[slug]/comments/route.ts:36` | 10/60s **và** 60/3600s per slug+IP; `requireShare`; `resolveGuestForWrite` (cookie → modal inline → auto-identity client) | Guest tạo comment/reply; visibility + author linkage ép server-side. |
| PATCH | `/api/r/[slug]/comments/[id]` | `src/app/api/r/[slug]/comments/[id]/route.ts:18` | 20/60s; `requireShare` + `getGuestSession` bắt buộc (401 nếu cookie chết); service so khớp GuestSession sở hữu comment | Sửa comment CỦA CHÍNH guest (browser khác = read-only, FR-E08 AC4). |
| DELETE | `/api/r/[slug]/comments/[id]` | `src/app/api/r/[slug]/comments/[id]/route.ts:32` | như PATCH | Xóa comment của chính guest. |
| POST | `/api/r/[slug]/comments/[id]/reactions` | `src/app/api/r/[slug]/comments/[id]/reactions/route.ts:23` | 60/60s; `requireShare` + `resolveGuestForWrite` | Thêm reaction (reactorKey `g:{guestSessionId}`, idempotent). |
| DELETE | `/api/r/[slug]/comments/[id]/reactions/[emoji]` | `src/app/api/r/[slug]/comments/[id]/reactions/[emoji]/route.ts:17` | 60/60s; `requireShare` + `getGuestSession` bắt buộc | Gỡ reaction của chính guest. |
| POST | `/api/r/[slug]/comment-attachments/initiate` | `src/app/api/r/[slug]/comment-attachments/initiate/route.ts:24` | 10/60s; `requireShare` + `resolveGuestForWrite`; key R2 embed GuestSession id (claim-by-prefix) | Presign R2 PUT ảnh đính kèm guest (image/* ≤10MB). |
| GET | `/api/r/[slug]/comment-attachments/[id]/raw` | `src/app/api/r/[slug]/comment-attachments/[id]/raw/route.ts:17` | 120/60s; `requireShare`; service chỉ trả attachment của comment PUBLIC trong scope share này | 302 tới signed R2 URL ảnh đính kèm. |

### 7.4 Decision (Approve / Request changes)

| Method | Path | File:line | Guard thật | Mục đích |
|---|---|---|---|---|
| POST | `/api/r/[slug]/decision` | `src/app/api/r/[slug]/decision/route.ts:34` | 5/60s; `requireShare`; identity bắt buộc (cookie hoặc inline `guest{}`); service `submitGuestDecision` (`share-decision.ts:127`) chồng thêm: (1) asset phải có `taskId` — share Team/bare-asset không được decide (AUDIT H1, `:137-146`); (2) task không archived/cancelled (`:169-172`); (3) `isClientFacingPhase(status, clientReview)` (`:173-175`); (4) version READY (`:186`); danh tính tự khai được chấp nhận (chủ dự án waive PIN, `:178-183`) | Khách chốt `approve`/`request_changes` (+note ≤2000 ký tự → comment public, hoặc internal nếu `allowComments=false` — AUDIT M2). Flip `ReviewState` (đổi ý được, no-op idempotent); chỉ head-version mới sync card status + task (A5→A6 qua `syncTaskOnChangesRequested`, portal `clientReview='APPROVED'`); notify staff + Inngest `review/decision.recorded`. |

### 7.5 Notifications PIN (đăng ký nhận email cập nhật) + Unsubscribe

| Method | Path | File:line | Guard thật | Mục đích |
|---|---|---|---|---|
| GET | `/api/r/[slug]/notifications?assetId=` | `src/app/api/r/[slug]/notifications/route.ts:14` | `requireShare` + `getGuestSession` (own-data only); **không rate-limit riêng** | Trạng thái subscription email của guest hiện tại cho 1 asset (UI gear/banner). |
| POST | `/api/r/[slug]/notifications/request-pin` | `src/app/api/r/[slug]/notifications/request-pin/route.ts:47` | `requireShare`; **LUÔN trả 200 neutral `{status:'pin_sent'}`** (anti-enumeration); limits: cooldown 1/60s + burst 3/600s per (email,share), 10/ngày per IP, 10/ngày per **inbox canonical** (strip +tag, gmail-dot — AUDIT L3, `:35-45,80`); auto-subscribe skip-PIN chỉ cho email CỦA session (`:68-70`) | Gửi mã PIN 6 số qua email để bật thông báo review cho asset (bảng `GuestEmailVerification`, `guest-subscribe.ts:114`). |
| POST | `/api/r/[slug]/notifications/verify-pin` | `src/app/api/r/[slug]/notifications/verify-pin/route.ts:25` | 20/600s per IP; `requireShare`; PIN cap 5 lần sai per code (`guest-subscribe.ts:163`); lỗi trả reason invalid/expired/locked/no_pin/reviewer_limit | Xác minh PIN → tạo `GuestSubscription` (email, assetId); stamp `emailVerifiedAt` cho sign-off. |
| POST | `/api/r/unsubscribe?token=` | `src/app/api/r/unsubscribe/route.ts:17` | **Không slug, không session — opaque `unsubscribeToken` LÀ authorization** (`guest-subscribe.ts:268`); idempotent, luôn trả neutral | One-click unsubscribe RFC 8058 (List-Unsubscribe-Post). |
| GET | `/api/r/unsubscribe?token=` | `src/app/api/r/unsubscribe/route.ts:24` | Không mutate — 302 về trang xác nhận `/r/unsubscribe` (chống mail-scanner tự GET hủy đăng ký) | Redirect an toàn cho người bấm từ email. |

---

## 8. Nhận xét kiểm toán (điểm đáng chú ý, có bằng chứng)

1. **Mọi staff route đều auth ở service-layer** — không route nào tự query DB trước khi service gọi `requireReviewAccess({workspaceId})` với workspaceId re-derive từ row. Hai ngoại lệ session-only (không workspace-scope, chấp nhận được vì chưa có tài nguyên đích): `GET /api/review/statuses` (`status.ts:23`) và `POST /api/review/comment-attachments/initiate` (`comments.ts:558`).
2. **Không staff route nào có rate-limit**; toàn bộ `limitDb` chỉ nằm ở `/api/r/**` (grep `limitDb` trong `src/app/api/review/**` = 0 kết quả).
3. **3 gate admin đặc thù** đều dùng `isAdmin` workspace-scoped (không phải global role): `deleteShare` (`shares.ts:737-740`), `purgeItemsAuthorized` (`purge.ts:389-390`), `markFeedbackDone`/`approveInternalAndSendToClient` (`task-sync.ts:274,381`). `requireReviewAccess({admin:true})` (gate theo GLOBAL role, `access.ts:44`) hiện **không có caller nào** trong 63 route (grep `admin: true` = 0 trong route + service).
4. **Decision không cần verify email** — chủ dự án waive impersonation (`share-decision.ts:178-183`); hàng rào còn lại là share phải thuộc task ở client-facing phase. Máy móc `isSyntheticGuestEmail` (`share-auth.ts:59`) vẫn giữ để không coi auto-identity là verified.
5. **Guest không bao giờ chạm `requireReviewAccess`** — 2 hệ tách đôi đúng thiết kế; route guest nào ném lỗi internal-auth sẽ ra 500 chung thay vì lộ envelope nội bộ (`route-auth.ts:49-66`).
6. `GET /api/r/[slug]/notifications` là guest route **duy nhất không có `limitDb`** (chỉ đọc dữ liệu của chính session); `unsubscribe` không limit nhưng token-là-auth và luôn neutral.

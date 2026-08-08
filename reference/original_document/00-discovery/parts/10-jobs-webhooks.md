# 10 — Inventory Background Jobs / Automation / Webhooks

> Phạm vi: cron Vercel, Inngest, webhook nhận, web-push, email pipeline (Resend), tiến trình nền phía client.
> Mọi số dòng lấy từ code thật tại repo root (worktree `cranky-austin`), thời điểm audit 2026-08-02.

---

## 1. Cron Vercel (7 cron trong `vercel.json:22-51`)

Cả 7 cron đều là `GET` handler dưới `src/app/api/cron/*/route.ts` và đều guard bằng `CRON_SECRET` (nhận qua header `x-cron-secret` / `x-cron-key` / `Authorization: Bearer`). **Chỉ `auth-cleanup` so sánh secret bằng `timingSafeEqual`; 6 cron còn lại so sánh `key !== secret` thường** (không timing-safe).

| # | Path (`vercel.json`) | Lịch (UTC) | Handler | Guard CRON_SECRET | Việc làm | Model Prisma đụng |
|---|---|---|---|---|---|---|
| 1 | `/api/cron/send-digest` (`vercel.json:24`) | `0 * * * *` (mỗi giờ) | `src/app/api/cron/send-digest/route.ts:11` | Có — so sánh thường (`route.ts:12-27`) | Gọi `sendDigestEmails('HOURLY')` mỗi giờ; riêng giờ UTC 1 (≈8h VN) chạy thêm `sendDigestEmails('DAILY')` (`route.ts:29-45`) | (gián tiếp qua `notification-email.ts`) `NotificationPreference`, `Notification`, `User`, `WorkspaceMember`, `Task` |
| 2 | `/api/cron/check-deadline` (`vercel.json:28`) | `0 * * * *` (mỗi giờ) | `src/app/api/cron/check-deadline/route.ts:14` | Có — so sánh thường (`route.ts:15-30`) | 3 lượt quét task có `assigneeId` + status trong whitelist `OVERDUE_ELIGIBLE_STATUSES` (`route.ts:8`, import từ `src/lib/task-statuses`): (1a) deadline ≤1h → notification tier `1h` (`route.ts:37-84`); (1b) deadline 1-24h → tier `24h` (`route.ts:86-136`); (2) deadline đã qua → **ghi đè `task.status = 'Quá hạn'`** (`route.ts:156-159`) + notification `TASK_OVERDUE` (`route.ts:170-189`). Dedup theo (taskId, tier) qua `notification.findFirst`. Mỗi notification cũng broadcast realtime (`broadcastNotificationToUser`) | `Task` (đọc + **ghi status**), `Notification` (tạo); gián tiếp: email + web-push qua `createNotificationInternal` |
| 3 | `/api/cron/cleanup-notifications` (`vercel.json:32`) | `0 2 * * *` (02:00 hằng ngày) | `src/app/api/cron/cleanup-notifications/route.ts:11` | Có — so sánh thường (`route.ts:12-27`) | Xóa notification archived >30 ngày (`route.ts:35-40`) và đã đọc >90 ngày (`route.ts:43-49`) | `Notification` (deleteMany) |
| 4 | `/api/cron/hard-delete-workspaces` (`vercel.json:36`) | `0 3 * * *` (03:00 hằng ngày) | `src/app/api/cron/hard-delete-workspaces/route.ts:20` | Có — so sánh thường (`route.ts:22-36`) | Tìm workspace `status='SOFT_DELETED'` quá `hardDeleteAfter` (`route.ts:47-53`), ghi audit `workspace.hard_deleted` TRƯỚC (`route.ts:67-74`) rồi `workspace.delete` → cascade toàn bộ dữ liệu (`route.ts:76`) | `Workspace` (delete cascade), `AuditLog` (qua `audit()`) |
| 5 | `/api/cron/hard-delete-profiles` (`vercel.json:40`) | `30 3 * * *` (03:30 hằng ngày) | `src/app/api/cron/hard-delete-profiles/route.ts:20` | Có — so sánh thường (`route.ts:22-36`) | Tương tự #4 cho `Profile` soft-deleted quá hạn (`route.ts:44-54`); audit `profile.hard_deleted` với `workspaceId:'SYSTEM'` (`route.ts:68-79`) rồi `profile.delete` cascade (`route.ts:82`) | `Profile` (delete cascade), `AuditLog` |
| 6 | `/api/cron/auth-cleanup` (`vercel.json:44`) | `0 4 * * *` (04:00 hằng ngày) | `src/app/api/cron/auth-cleanup/route.ts:27` | Có — **`timingSafeEqual`** (`route.ts:19-25,37`) | Xóa `EmailVerificationToken` hết hạn (`route.ts:47-49`); `PasswordResetOTP` hết hạn hoặc consumed >7 ngày (`route.ts:52-59`); `LoginAttempt` >90 ngày (`route.ts:62-64`) | `EmailVerificationToken`, `PasswordResetOTP`, `LoginAttempt` |
| 7 | `/api/cron/review-janitor` (`vercel.json:48`) | `0 20 * * *` (20:00 UTC = 03:00 VN) | `src/app/api/cron/review-janitor/route.ts:13` | Có — so sánh thường (`route.ts:14-28`) | **Không làm việc nặng** — chỉ bắn 1 event Inngest `review/janitor.requested` (`route.ts:31`) rồi trả 200; toàn bộ dọn dẹp chạy trong function `reviewJanitor` (mục 2) | — (chỉ gửi event) |

Ghi chú thêm:
- Endpoint chẩn đoán `src/app/api/test-email/route.ts` cũng guard bằng CRON_SECRET nhưng **chấp nhận secret qua query param `?secret=`** (`route.ts:17`) — secret có thể lọt vào access log; file tự ghi chú "DELETE after debugging" (`route.ts:3`) nhưng vẫn còn.
- `maxDuration` cho API routes: mặc định 30s, invoices/uploads 60s, download-zip 300s (`vercel.json:2-21`).

---

## 2. Inngest

### 2.1 Serve endpoint

- `src/app/api/inngest/route.ts:17-20` — `serve({ client: inngest, functions: reviewFunctions })`, export `GET/POST/PUT`. Xác thực do Inngest tự làm bằng `INNGEST_SIGNING_KEY` (ghi chú `route.ts:2-3`); middleware app loại trừ `/api` nên không dính session.
- `maxDuration = 800` (`route.ts:15`) — vì bước `ensure-color-tags` stream video qua ffmpeg trong 1 step.
- Client: `new Inngest({ id: 'hustlytasker-review' })` — `src/lib/review/inngest.ts:28`.
- Danh sách đăng ký: `reviewFunctions = [reviewMuxWebhook, reviewProcessUpload, reviewJanitor, reviewShareDecision]` — `src/lib/review/inngest.ts:751`.

### 2.2 Event names (`src/lib/review/inngest.ts:31-41`)

| Event | Ai gửi (file:line) |
|---|---|
| `review/mux.event.received` | Webhook Mux `src/app/api/webhooks/mux/route.ts:87`; janitor re-enqueue `src/lib/review/inngest.ts:617-619` |
| `review/janitor.requested` | Cron `src/app/api/cron/review-janitor/route.ts:31` |
| `review/upload.completed` | Route hoàn tất upload `src/lib/review/upload-service.ts:439`; janitor re-fire `src/lib/review/inngest.ts:473` |
| `review/decision.recorded` | Route quyết định của khách `src/lib/review/share-decision.ts:375` |

### 2.3 Bốn function (tất cả trong `src/lib/review/inngest.ts`)

| Function (id) | Định nghĩa | Trigger | Retries | Việc làm | Model đụng |
|---|---|---|---|---|---|
| `reviewMuxWebhook` (`review-mux-webhook`) | `inngest.ts:259` | event `review/mux.event.received` | 4 | Đọc ledger `WebhookEvent` theo id (`inngest.ts:269-277`); nếu `video.asset.ready` → `applyMuxReady()` (`inngest.ts:64-206`): flip nguyên tử PROCESSING→READY + set metadata Mux + đổi stack-head + clear approve cũ + notify uploader + audit feed + auto-flip task → "Đã nộp video (nội bộ)" + **thu hồi share khách nếu clientReview='AWAITING'** (`inngest.ts:150-154`) + email/notify manager (`inngest.ts:170-182`); nếu `video.asset.errored` → `applyMuxErrored()` (`inngest.ts:213-248`): flip → FAILED + notify uploader. Đánh dấu `processedAt` CUỐI CÙNG (persist-then-claim, `inngest.ts:323-329`) | `WebhookEvent`, `ReviewVersion`, `ReviewAsset`, `ReviewActivity` (qua `recordActivity`), `Task` (qua task-sync), `Notification`, `AuditLog` |
| `reviewProcessUpload` (`review-process-upload`) | `inngest.ts:341` | event `review/upload.completed` | 4 | Với VIDEO đang PROCESSING chưa có Mux asset: sniff magic-bytes từ R2 (`inngest.ts:379-388`) → nếu không phải video: flip FAILED (`inngest.ts:390-411`); retag colorspace BT.709 nếu thiếu tag (`inngest.ts:417-419`, `ensureColorTaggedInput`); tạo Mux asset từ presigned R2 GET 24h với `passthrough=versionId` (`inngest.ts:423-429`); lưu `muxAssetId` có guard chống double-create, xóa asset mồ côi (`inngest.ts:433-451`) | `ReviewVersion`, `ReviewActivity`; ngoài DB: R2 (đọc/ghi), Mux API |
| `reviewJanitor` (`review-janitor`) | `inngest.ts:526` | event `review/janitor.requested` (mỗi đêm từ cron #7) | 2 | 5 sweep độc lập, mỗi sweep 1 step, batch cap 100 (PURGE 25) (`inngest.ts:46-52`): (a) expire upload UPLOADING quá 24h (`inngest.ts:530-551`); (b) redrive version kẹt UPLOADED >15' (`inngest.ts:554-574`); (c) reconcile version kẹt PROCESSING >20' — hỏi thẳng Mux, áp cùng transition như webhook, quá 24h thì FAIL + xóa Mux asset treo (`inngest.ts:577-601` + `reconcileProcessingVersion` `inngest.ts:463-516`); (d) re-enqueue `WebhookEvent` chưa consume 1h–7d (`inngest.ts:606-627`); (e) purge thùng rác quá 30 ngày — xóa vật lý Mux + R2 + DB rows (`inngest.ts:633`, `purgeExpiredTrash` từ `src/lib/review/purge.ts`) | `UploadSession`, `ReviewVersion`, `WebhookEvent`, `ReviewAsset`/`ReviewFolder` (qua purge); Mux + R2 |
| `reviewShareDecision` (`review-share-decision`) | `inngest.ts:657` | event `review/decision.recorded` | 4 | Backup idempotent cho side-effects sau khi khách Approve/Request-changes (quyết định chính đã commit sync trong `share-decision.ts`): guard "latest wins" — skip nếu reviewState đổi hoặc version không còn là head (`inngest.ts:663-683`); `request_changes` → `syncTaskOnChangesRequested` (`inngest.ts:691-694`); `approve` → settle `task.clientReview='APPROVED'` với guard `isArchived:false` (`inngest.ts:704-725`); ghi audit feed `task.client_approved`/`task.client_changes_requested` (`inngest.ts:731-745`) | `ReviewVersion` (đọc), `Task` (updateMany), `AuditLog` |

---

## 3. Webhook NHẬN

### 3.1 `/api/webhooks/mux` — `src/app/api/webhooks/mux/route.ts` (POST, `route.ts:50`)

- **Verify chữ ký**: đọc RAW body trước (`route.ts:51`); header `Mux-Signature: t=<unix>,v1=<hex>`; HMAC-SHA256 trên `"{t}.{rawBody}"` với `MUX_WEBHOOK_SECRET`, tolerance ±5 phút, so sánh bằng `timingSafeEqual`, mọi lỗi → false (`route.ts:23-48`). Sai chữ ký → **401 fail-closed** để Mux retry (`route.ts:54-58`).
- **Idempotent**: ghi ledger `WebhookEvent` với id = Mux event id, unique-violation `P2002` = duplicate → ack không refire (`route.ts:74-80`).
- **Fan-out**: bắn event Inngest `review/mux.event.received` (`route.ts:87-93`); send fail chỉ log — ledger là source of truth, janitor re-enqueue về sau. Trả 200 nhanh, không làm việc nặng trong request.

### 3.2 `/api/webhooks/calendar` — `src/app/api/webhooks/calendar/route.ts` (POST, `route.ts:8`)

- **STUB chưa hoàn thiện / dead-endpoint có mount**: verify auth bị comment (`route.ts:11`), chỉ trả `validationToken` cho Microsoft Graph handshake (`route.ts:14-18`). Phần xử lý event thật nằm trong block comment TODO (`route.ts:23-40`) với `dummyUserId = "find-user-id-by-remote-resource"`.
- Thực tế runtime: **nhận POST không xác thực từ bất kỳ ai**, `console.log` toàn bộ payload (`route.ts:21`) rồi trả `{success:true}` — không ghi DB, không gọi `createScheduleException` (import ở `route.ts:2` không được dùng ngoài comment). Đề xuất: gỡ hoặc hoàn thiện + thêm verify.

---

## 4. Web-push

| Thành phần | File | Nội dung |
|---|---|---|
| Server actions quản lý subscription | `src/actions/push-actions.ts` | `getVapidPublicKey()` (`push-actions.ts:14`) trả null nếu VAPID chưa cấu hình → toggle không hiện; `savePushSubscription` (`push-actions.ts:18`) session-gated, validate endpoint/p256dh/auth, upsert theo unique `endpoint` (`push-actions.ts:37-41`); `deletePushSubscription` (`push-actions.ts:49`) scope theo userId caller (`push-actions.ts:54`) |
| Sender server-side | `src/lib/web-push.ts` | Gate toàn bộ trên env `NEXT_PUBLIC_VAPID_PUBLIC_KEY` + `VAPID_PRIVATE_KEY` (`web-push.ts:14-20`); `sendWebPushToUser` (`web-push.ts:35`) gửi tới mọi subscription của user, `import('web-push')` động (`web-push.ts:47-53`), tự prune endpoint chết 404/410 (`web-push.ts:76-83`), không bao giờ throw |
| Điểm bắn push | `src/actions/notification-actions.ts:58-65` | Fire-and-forget **trong `createNotificationInternal`** — tức MỌI notification in-app đều kèm 1 lần thử web-push (url lấy từ `metadata.url`, tag `task-{taskId}`) |
| Service worker | `public/sw.js` | Push-only: KHÔNG intercept `fetch`, không cache (`sw.js:1-7`); `push` → `showNotification` (`sw.js:18-31`); `notificationclick` → focus tab sẵn có hoặc mở `data.url` (`sw.js:33-49`); `skipWaiting`+`clients.claim` (`sw.js:9-16`) |
| Đăng ký SW phía client | `src/components/notifications/PushNotificationToggle.tsx:65` | `navigator.serviceWorker.register('/sw.js')` sau khi user bật toggle + cấp Notification permission |
| Model | `PushSubscription` (userId, endpoint unique, p256dh, auth, userAgent) | dùng ở `push-actions.ts:37`, `web-push.ts:40` |

---

## 5. Email pipeline (Resend)

### 5.1 Hạ tầng gửi

- `src/lib/email.ts:26` — `sendEmail({to, subject, html, headers?})` duy nhất; Resend client init từ `RESEND_API_KEY` (`email.ts:5-10`), from = `EMAIL_SENDER_NAME <RESEND_FROM_EMAIL>` (fallback `HustlyTasker <notification@hustlytasker.xyz>`). Thiếu key → chỉ warn, KHÔNG gửi (`email.ts:27-30`). Hỗ trợ header phụ (List-Unsubscribe RFC 8058) (`email.ts:16-18`).

### 5.2 Hai hệ template TỒN TẠI SONG SONG (đều đang được dùng thật — không phải dead code)

1. **Registry mới** `src/lib/notification-emails/` — 11 template (`index.ts:21-33`), map từ `NotificationType` qua `pickTemplate` (`index.ts:41-67`). Entry point: `src/lib/notification-email.ts` với 2 cửa:
   - `maybeSendNotificationEmail` (`notification-email.ts:323`) — gọi fire-and-forget sau **mọi** `createNotificationInternal` (`src/actions/notification-actions.ts:49`). Quyết định gửi theo `BYPASS_CONFIG` (mute/digest/quiet-hours, `notification-email.ts:44-65`), claim nguyên tử `emailSentAt` chống double-send (`notification-email.ts:107-113`); check online ĐÃ TẮT theo yêu cầu user (`notification-email.ts:367-369`).
   - `sendDigestEmails` (`notification-email.ts:464`) — cron #1 gọi; gom notification `emailSentAt=null` (tối đa 50/user) cho user có `emailDigestMode=HOURLY/DAILY`, render `digestHourly`/`digestDaily`, đánh dấu `emailSentAt` sau khi gửi (`notification-email.ts:553-556`).
2. **Legacy** `src/lib/email-templates.ts` — gọi trực tiếp `sendEmail` (không qua Notification), vẫn sống ở các action bên dưới.

### 5.3 Bảng email được gửi + trigger

| Email | Template | Trigger từ đâu (file:line) | Người nhận |
|---|---|---|---|
| Task assigned (realtime) | registry `taskAssigned` | mọi notification `TASK_ASSIGNED` → `notification-actions.ts:49` → `notification-email.ts:323` | assignee |
| Task unassigned / status changed / comment / deadline 24h / 1h / overdue / client submitted | registry tương ứng (`notification-emails/index.ts:45-59`) | cùng đường `createNotificationInternal`; deadline/overdue phát từ cron #2 (`check-deadline/route.ts:63,115,170`) | user liên quan |
| Khách duyệt / yêu cầu sửa video (staff nhận) | registry `reviewClientDecision` (`index.ts:61-63`) | notification `VIDEO_REVIEW_APPROVED`/`VIDEO_CHANGES_REQUESTED` tạo sync trong `src/lib/review/share-decision.ts:339,353` | editor + manager |
| Digest hourly/daily | `digestHourly`/`digestDaily` | cron #1 → `sendDigestEmails` (`notification-email.ts:543-551`) | user chọn digest mode |
| GĐ1 giao task (legacy) | `emailTemplates.taskAssigned` | `src/actions/admin-actions.ts:319` (tạo task) | assignee |
| GĐ3 user bắt đầu task | `emailTemplates.taskStarted` | `src/actions/task-actions.ts:259` | admin `assignedBy` |
| GĐ4 user nộp video | `emailTemplates.taskDelivered` | `src/actions/task-actions.ts:276` | admin `assignedBy` |
| Admin resume/reject (feedback) | `emailTemplates.taskFeedback` | `src/actions/task-actions.ts:293,306` | assignee |
| Task hoàn tất 🎉 (kèm wageVND) | `emailTemplates.taskCompleted` | `src/actions/task-actions.ts:319` | assignee |
| Bulk status digest | `emailTemplates.taskStatusBulkDigest` | `src/actions/bulk-task-actions.ts:635` | mỗi recipient gộp nhóm |
| Invoice created | `emailTemplates.invoiceCreated` | `src/actions/invoice-actions.ts:496` | chính actor (admin) |
| Lời mời workspace | `buildWorkspaceInvitationEmail` | `src/actions/member-actions.ts:84` | invitee |
| Verify email đăng ký | `buildVerifyEmailEmail` | `src/actions/signup-actions.ts:350` | email đăng ký |
| OTP reset mật khẩu | `buildPasswordResetOtpEmail` | `src/actions/password-reset-actions.ts:168` | user |
| Cảnh báo đã đổi mật khẩu | `buildPasswordChangedEmail` | `src/actions/password-reset-actions.ts:396` | user |
| OTP đổi email | tái dùng `buildPasswordResetOtpEmail` | `src/actions/email-migration-actions.ts:161` | email MỚI |
| OTP verify cho portal notify email | `renderNotifyVerifyEmailHtml` | `src/actions/share-portal-actions.ts:617` (rate-limited) | email khách khai |
| PIN verify guest /r/ | `renderVerifyPinEmail` | `src/lib/review/guest-subscribe.ts:125` (double-opt-in) | guest |
| Guest notices: `version_sent` / `comment_reply` / `status_update` / `feedback_received` / `approved` | `src/lib/review/guest-emails/notices.ts` (render tại `guest-notify.ts:20-30`) | `notifyGuestsOfAsset` (`guest-notify.ts:90`) gọi từ `comments.ts:428`, `task-sync.ts:71,354,418`, `share-decision.ts:349,360`; gửi cho (1) GuestSubscription theo asset (`guest-notify.ts:191`) và (2) portal notify email theo name-path subtree (`guest-notify.ts:242`, chọn qua `selectPortalNotifyLinks` `guest-notify.ts:46`); kèm List-Unsubscribe per-recipient | guest / client |
| Test email chẩn đoán | HTML inline | `src/app/api/test-email/route.ts:45` — guard CRON_SECRET nhưng nhận secret qua **query param** (`route.ts:17`) | tùy `?to=` |

### 5.4 Kênh realtime kèm theo (bối cảnh)

- `src/lib/notification-broadcast.ts:19,46` — broadcast qua **Supabase Realtime REST** (`/realtime/v1/api/broadcast`), fire-and-forget timeout 3s; dùng bởi cron #2 và `createAndBroadcastNotifications` (`notification-actions.ts:86-106`). Không phải job nền server, chỉ là push kênh phụ.

---

## 6. Tiến trình nền phía client

| File | Trạng thái | Nội dung |
|---|---|---|
| `src/lib/TimerWorker.ts` | **DEAD CODE candidate** | Web Worker tick 1s chống throttle cho "Sidebar Timer" (`TimerWorker.ts:2-3`, START/STOP + drift compensation `TimerWorker.ts:12-35`). **Grep toàn `src/` không có bất kỳ import/`new Worker(`/tham chiếu chuỗi `TimerWorker` nào** → không được mount, không chạy ở runtime. |
| `src/instrumentation-client.ts` | Đang chạy (Next.js ≥15.3 tự load khi client hydrate, `instrumentation-client.ts:4-5`) | Init **Vercel BotID** (thay Cloudflare Turnstile): `initBotId({ protect: [{ path: '/api/auth/signup', method: 'POST' }] })` (`instrumentation-client.ts:13-20`) — thu tín hiệu passive + gắn header cho request tới path được protect; server verify bằng `checkBotId()`. Không có interval/polling nào khác trong file. |
| `public/sw.js` | Đang chạy khi user bật push | Push-only service worker (chi tiết mục 4) — không cache, không fetch handler. |

---

## 7. Nhận xét nổi bật (theo bằng chứng)

1. **Guard cron không đồng nhất**: chỉ `auth-cleanup` dùng `timingSafeEqual` (`src/app/api/cron/auth-cleanup/route.ts:19-25`); 6 cron khác so sánh chuỗi thường — cùng một secret, hai chuẩn so sánh.
2. **`/api/webhooks/calendar` là stub không xác thực**: nhận POST từ bất kỳ ai, log payload, không làm gì thật (`src/app/api/webhooks/calendar/route.ts:11,21,23-40`) — nên gỡ khỏi production hoặc hoàn thiện.
3. **`/api/test-email` còn sống** và nhận CRON_SECRET qua query string (`src/app/api/test-email/route.ts:17`), tự ghi chú phải xóa sau khi debug (`route.ts:3`).
4. **Hai hệ email template song song** (legacy `email-templates.ts` + registry `notification-emails/`) đều đang dùng thật → user có thể nhận 2 email cho cùng một biến cố nếu cả hai đường cùng bắn (vd giao task: `admin-actions.ts:319` legacy + notification `TASK_ASSIGNED` registry).
5. **`TimerWorker.ts` là dead code** — không nơi nào tham chiếu.
6. Kiến trúc webhook Mux → ledger `WebhookEvent` → Inngest, kèm janitor re-enqueue + reconcile trực tiếp với Mux, là đường bền vững nhất trong repo (idempotent nhiều tầng: unique event id, atomic status flip, persist-then-claim `processedAt`).
7. Cron `check-deadline` là cron duy nhất **ghi đè dữ liệu nghiệp vụ** (`task.status='Quá hạn'`, `check-deadline/route.ts:156-159`) — whitelist `OVERDUE_ELIGIBLE_STATUSES` bảo vệ 6 status video mới khỏi bị cron overwrite (`route.ts:5-8`).

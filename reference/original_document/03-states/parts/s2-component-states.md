# S2 — Component States (Phase 3 §2)

> Quét state THẬT của ~34 component tiêu biểu trong `src/components` (330 file, 27 domain) + 2 trang auth. Mỗi bảng chỉ liệt kê state **có trong code** kèm `file:line`; state component KHÔNG xử lý được ghi rõ `✗ KHÔNG xử lý` — đó cũng là finding. Ngày audit: 2026-08-02. Mọi đường dẫn tương đối từ root repo.

## 0. Cách đọc & kết luận nhanh

| Ký hiệu | Nghĩa |
|---|---|
| ✓ | State có xử lý trong code (kèm bằng chứng) |
| ✗ KHÔNG xử lý | Code không có nhánh nào cho state này |
| (kế thừa) | State do component cha/lib xử lý, không nằm trong file này |

**Kết luận tổng (chi tiết ở §10):** repo có **3 thế hệ pattern state** sống song song:
1. **GĐ1 (tables admin cũ)** — `await action → toast → window.location.reload()`, không loading indicator, không optimistic (`NewDesktopTaskTable`, `TaskWorkflowTabs`, `PayrollTable`).
2. **Mobile/mid-gen** — `toast + startTransition(router.refresh())` nhưng **vứt `isPending`** nên vẫn không có pending UI (`MobileTaskView:115`, `DashboardActionWrapper:126`).
3. **Review module (mới nhất)** — đủ cả loading/error/empty/optimistic-rollback/`toast.loading→update-by-id`, skeleton đếm đúng số item (`TeamBrowser`, `UploadTray`, `GuestReviewApp`).

---

## 1. Base UI (`src/components/ui/`) — 28 file, chọn 6 nền tảng

### 1.1 `ui/button.tsx` — Button (cva + Radix Slot)

| State | Có? | Chi tiết thật trong code | Bằng chứng |
|---|---|---|---|
| default | ✓ | 7 variant (`default/destructive/outline/secondary/ghost/link/liquid`) × 4 size qua `cva` | `ui/button.tsx:10-27` |
| hover | ✓ | mỗi variant có lớp hover riêng (`hover:bg-primary/90`, `liquid` thêm `hover:scale-[1.02]`) | `ui/button.tsx:11-20` |
| focus | ✓ | `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2` ở base class | `ui/button.tsx:7` |
| disabled | ✓ | `disabled:pointer-events-none disabled:opacity-50` — chỉ style, điều kiện do caller truyền prop `disabled` | `ui/button.tsx:7` |
| loading | ✗ KHÔNG xử lý | **Không có prop `isLoading`/spinner tích hợp** → mỗi caller tự chế `<Loader2 className="animate-spin"/>` (đếm được ≥10 biến thể khắp repo, xem §10.4) | `ui/button.tsx:36-53` |
| error/empty/success | ✗ | Không thuộc phạm vi button | — |

### 1.2 `ui/input.tsx` — Input

| State | Có? | Chi tiết | Bằng chứng |
|---|---|---|---|
| default | ✓ | `border-input bg-background`, `placeholder:text-muted-foreground` | `ui/input.tsx:14` |
| focus | ✓ | `focus-visible:ring-2 focus-visible:ring-ring` | `ui/input.tsx:14` |
| disabled | ✓ | `disabled:cursor-not-allowed disabled:opacity-50` | `ui/input.tsx:14` |
| error/invalid | ✗ KHÔNG xử lý | Không có style `aria-invalid`/border đỏ ở base — form nào cần báo lỗi phải tự render div lỗi bên ngoài (login/signup làm vậy) | `ui/input.tsx:5-25` |

### 1.3 `ui/dialog.tsx` — Dialog (Radix wrapper)

| State | Có? | Chi tiết | Bằng chứng |
|---|---|---|---|
| open/close | ✓ | animate theo `data-[state=open/closed]` (fade overlay, zoom+slide content) | `ui/dialog.tsx:24,41` |
| hover/focus nút đóng | ✓ | `hover:opacity-100` + `focus:ring-2`, có `sr-only` "Đóng" | `ui/dialog.tsx:47-49` |
| loading/error | ✗ | Wrapper thuần, không có | — |

### 1.4 `ui/ConfirmModal.tsx` — ConfirmProvider/useConfirm (promise-based)

| State | Có? | Chi tiết | Bằng chứng |
|---|---|---|---|
| open | ✓ | `confirm(opts)` trả `Promise<boolean>`, resolve qua ref | `ui/ConfirmModal.tsx:32-48` |
| variant | ✓ | `danger/info/warning` đổi glow + màu tiêu đề (⚠️ khi danger) | `ui/ConfirmModal.tsx:63-71,88-92` |
| hover | ✓ | nút hủy `hover:bg-white/10`, nút xác nhận `hover:scale-105 active:scale-95` | `ui/ConfirmModal.tsx:82,88` |
| loading | ✗ KHÔNG xử lý | Modal đóng NGAY khi bấm xác nhận (`setIsOpen(false)` trước khi caller chạy async) → không có trạng thái "đang xoá…" trong modal; khoảng chờ sau đó do caller tự lo (thường là không có gì — xem §2) | `ui/ConfirmModal.tsx:40-43` |

### 1.5 `ui/empty-state.tsx` — EmptyState dùng chung (Mobile P2 §Pattern 9)

| State | Có? | Chi tiết | Bằng chứng |
|---|---|---|---|
| 4 variant empty | ✓ | `first-use/cleared/no-results/error` với icon map mặc định (Inbox/PartyPopper/SearchX/RefreshCcw) | `ui/empty-state.tsx:13,31-36` |
| CTA | ✓ | nút Link (href) hoặc onClick, tap-target `min-h-[44px]` | `ui/empty-state.tsx:60-76` |

Ghi chú: chỉ mobile + review module dùng component này; các bảng admin GĐ1 vẫn dùng text thô (xem §2.2, §8.1).

### 1.6 `ui/PageSkeleton.tsx` — skeleton route-level

| State | Có? | Chi tiết | Bằng chứng |
|---|---|---|---|
| loading | ✓ | `animate-pulse` thuần CSS, server-safe, dùng cho `loading.tsx` các route chính (title + 3 card + 6 row trung tính) | `ui/PageSkeleton.tsx:5-21` |

---

## 2. Bảng task desktop & workflow

### 2.1 `TaskTable.tsx` — dispatcher (34 dòng)

Chỉ rẽ nhánh `isMobile ? MobileTaskView : NewDesktopTaskTable` (`TaskTable.tsx:29-33`); **không có state riêng**. ⚠️ Vẫn `import DesktopTaskTable` (dead code 53KB) vào bundle — `TaskTable.tsx:9`.

### 2.2 `NewDesktopTaskTable.tsx` (871 dòng) — bảng task desktop đang dùng

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| default | ✓ | bảng inline-style, sort 3 cột, phân trang client | `NewDesktopTaskTable.tsx:160-167` |
| hover | ✓ | header sort `hover:text-zinc-400`, icon action `hover:text-zinc-300` | `NewDesktopTaskTable.tsx:468,720` |
| loading | ✗ KHÔNG xử lý | Không có `isPending`/spinner nào; mọi mutation chờ trắng rồi **`window.location.reload()`** (xoá 1: `:183`, xoá bulk: `:200`, trả task: `:757`) — full page reload thay vì refresh RSC | `NewDesktopTaskTable.tsx:183,200,757` |
| disabled | ✓ | chỉ 2 nút phân trang `disabled={page === 1 / totalPages}` | `NewDesktopTaskTable.tsx:792,829` |
| error | ✓ một phần | bulk-delete + trả-task có check `res.error → toast.error`; **xoá đơn lẻ KHÔNG check** — `await deleteTask()` rồi `toast.success('Đã xoá task')` vô điều kiện (server lỗi vẫn báo thành công) | check: `:195-196,754`; bỏ check: `:181-182` |
| empty | ✓ | text thô `"Không có task nào."` (không dùng `ui/empty-state`) | `NewDesktopTaskTable.tsx:487-490` |
| success | ✓ | `toast.success` (sonner) + reload; guard editor chưa Start: `toast.warning('Vui lòng bấm "Bắt đầu"…')` | `NewDesktopTaskTable.tsx:171-172,182,198` |
| optimistic | ✗ KHÔNG xử lý | Không có — trái với quy tắc `.claude/CLAUDE.md` ("Chơi hệ Optimistic UI") | — |

### 2.3 `TaskWorkflowTabs.tsx` (1036 dòng) — tabs + kéo-thả đổi trạng thái

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| default | ✓ | 1 state cụm tab `activeTab` mặc định `'all'` + search + page + sort | `TaskWorkflowTabs.tsx:121-129` |
| drag (riêng) | ✓ | `isDragging`/`dragOverTabId`; hint `animate-pulse` "Kéo lên một tab phía trên để đổi trạng thái" | `TaskWorkflowTabs.tsx:132-133,410-416` |
| loading | ✗ KHÔNG xử lý | Drop tab → `await updateTaskStatus/bulkUpdateStatus` không có pending UI, xong mới `router.refresh()`; xoá thì `window.location.reload()` | `TaskWorkflowTabs.tsx:298-316,210,226` |
| disabled | ✓ | phân trang `disabled={page===1/totalPages}` | `TaskWorkflowTabs.tsx:948,992` |
| error | ✓ một phần | drop: `res.error→toast.error` + `catch → toast.error('Cập nhật trạng thái thất bại')`; **xoá đơn lẻ không check `deleteTask` error** (giống 2.2) | `TaskWorkflowTabs.tsx:302,311,318-319`; bỏ check: `:208-209` |
| empty | ✓ | text thô `"Không có task nào."` | `TaskWorkflowTabs.tsx:628` |
| success | ✓ | `toast.success('Đã chuyển task sang …')` + clear selection + refresh; no-op: `toast.info('Các task đã ở trạng thái này rồi')` | `TaskWorkflowTabs.tsx:294,304-306,313-315` |

### 2.4 `tasks/cells/StatusCell.tsx` (216 dòng) — ô trạng thái trên bảng

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| default | ✓ | map màu 15 status string (kể cả 6 status video A2–A7) | `tasks/cells/StatusCell.tsx:28-48` |
| USER view | ✓ | `Nhận task` → nút vàng "▶ Bắt đầu" `hover:scale-105`; `Đang thực hiện` → badge chấm `animate-ping` "Đang làm…" | `tasks/cells/StatusCell.tsx:100-119` |
| ADMIN view | ✓ | Radix Select đổi status + dialog phân loại Revision (CLIENT/INTERNAL cho KPI) | `tasks/cells/StatusCell.tsx:132-147,163-213` |
| loading | ✗ KHÔNG xử lý | Trong lúc `await updateTaskStatus` Select **không disabled, không spinner** — bấm lại được (double-fire) | `tasks/cells/StatusCell.tsx:62-79` |
| error | ✓ | `res.error→toast.error` + `catch→toast.error('Cập nhật trạng thái thất bại')` | `tasks/cells/StatusCell.tsx:70-72,76-78` |
| success | ✓ | `toast.success` + `router.refresh()` (không optimistic — chip đổi sau round-trip) | `tasks/cells/StatusCell.tsx:74-75,90-91` |

### 2.5 `tasks/TaskDetailModal.tsx` (774 dòng) — chi tiết task (desktop)

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading (mutation) | ✓ | 3 cờ: `savingCard` (mọi edit field), `savingMap` (Multi-Hook Map), `starting` (nút Bắt đầu có `Loader2` + `disabled`) | `tasks/TaskDetailModal.tsx:159,90,625,646` |
| error | ✓ | toast theo từng nhánh, kể cả **partial-failure có thật**: "Link đã lưu, nhưng chưa chuyển status. Vui lòng thử lại." | `tasks/TaskDetailModal.tsx:138,145,262,414-417` |
| empty | ✓ | "Chưa có ghi chú nào." trong tab notes | `tasks/TaskDetailModal.tsx:756` |
| success | ✓ | toast nghiệp vụ cụ thể ("Đã nộp bài — admin sẽ review sớm. Deadline đã được tạm dừng.") | `tasks/TaskDetailModal.tsx:408,509` |
| validation | ✓ | chặn trước khi gọi server: "Cần nhập link Delivery trước khi xác nhận.", "Tên không được để trống" | `tasks/TaskDetailModal.tsx:378,464` |

### 2.6 `mobile/MobileTaskView.tsx` (631 dòng) — bảng task mobile

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading (hydrate) | ✓ | `isHydrating` → render 3× `MobileTaskCardSkeleton` | `mobile/MobileTaskView.tsx:122,471-476` |
| loading (mutation) | ⚠️ nửa vời | `const [, startTransition] = useTransition()` — **`isPending` bị vứt**, refresh mượt nhưng không có indicator | `mobile/MobileTaskView.tsx:115,290,330,343` |
| refresh | ✓ | `PullToRefresh onRefresh={handleRefresh}` | `mobile/MobileTaskView.tsx:368,469` |
| error | ✓ | mọi mutation: `res.error→toast.error` + catch fallback ("Không thể cập nhật trạng thái. Vui lòng thử lại.") | `mobile/MobileTaskView.tsx:286,294,340,345,359,364` |
| empty | ✓ | `renderEmptyState()` dùng `ui/EmptyState` chuẩn, copy theo tab ("Chưa có task nào" / "Không có task ở giai đoạn này") | `mobile/MobileTaskView.tsx:378-405,526-533` |
| success | ✓ | toast + `startTransition(router.refresh())`; swipe actions đổi status nhanh | `mobile/MobileTaskView.tsx:289-290,329-330,483` |

---

## 3. Tạo task (AddTaskModal + wrapper)

### 3.1 `dashboard/AddTaskModal.tsx` (1742 dòng — component client lớn nhất repo)

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading (submit) | ✓ | `submitting` → nút "Tạo task" `disabled` + label đổi "Đang thêm…" (không spinner); các nút step cũng disabled | `dashboard/AddTaskModal.tsx:446,1703-1707,1588,1619` |
| disabled | ✓ | nút Back `disabled={step === 0}` | `dashboard/AddTaskModal.tsx:1680` |
| error | ✓ | `catch → toast.error(err?.message \|\| "Lỗi khi tạo task…")`; Velox scan lỗi riêng (HTTP status, link rỗng) | `dashboard/AddTaskModal.tsx:932-933,492-510` |
| success | ✓ | **màn hình success riêng** (`submitted=true` → `renderSuccess()`, copy phân biệt "Đã giao task!" vs "Đã thêm vào hàng đợi!" theo assigneeId) + clear draft + reset Velox/Multi-Hook state | `dashboard/AddTaskModal.tsx:443,920-931,1466-1486,1655-1656` |
| draft-restore | ✓ | auto-save draft, mở lại modal → `toast.success("Đã khôi phục bản nháp đang nhập dở")` | `dashboard/AddTaskModal.tsx:637,601` |
| confetti | ✗ | Không có confetti — success là motion.div scale-in | `dashboard/AddTaskModal.tsx:1483-1486` |

### 3.2 `dashboard/DashboardActionWrapper.tsx` (504 dòng) — cha của AddTaskModal

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading | ⚠️ nửa vời | `const [, startTransition] = useTransition()` — **vứt `isPending`**; refresh sau tạo task không có indicator | `dashboard/DashboardActionWrapper.tsx:126,298-300,433-434` |
| error | ✓ | `createTasksFromBatch` lỗi → `throw` cho AddTaskModal toast; **partial-failure Multi-Hook Map có 3 nhánh toast riêng** ("Đã tạo các task nhưng không lưu được Multi-Hook Map…") | `dashboard/DashboardActionWrapper.tsx:294,81-93,394-398` |
| success | ✓ | `toast.success('Đã gắn Multi-Hook Map vào task đầu của lô…')` + refresh | `dashboard/DashboardActionWrapper.tsx:89,298-300` |

---

## 4. Notifications

### 4.1 `notifications/NotificationBell.tsx` (88 dòng)

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| default | ✓ | poll count 30s + realtime Supabase channel + sound cho 4 loại task-event | `notifications/NotificationBell.tsx:26-34,49-62` |
| hover | ✓ | `hover:bg-white/10` trên nút chuông | `notifications/NotificationBell.tsx:68` |
| badge | ✓ | unread > 0 → chuông tím + badge `99+` cap | `notifications/NotificationBell.tsx:71-76` |
| error | ✗ KHÔNG xử lý | `getUnreadNotificationCount` chỉ đọc `res.data` — `res.error` bị nuốt im lặng (badge đứng yên khi server lỗi) | `notifications/NotificationBell.tsx:27-30` |

### 4.2 `notifications/NotificationPanel.tsx` (175 dòng)

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading | ✓ | `Loader2 animate-spin` khi `loading && items.length===0`; nút "Tải thêm" disabled + label "Đang tải…" | `notifications/NotificationPanel.tsx:143-147,163-170` |
| empty | ✓ | `EmptyNotification` với copy theo tab ("Không có thông báo chưa đọc" / "Chưa có thông báo nào") | `notifications/NotificationPanel.tsx:149-151` |
| error (load) | ✗ KHÔNG xử lý | `load()` là `try/finally` **không có catch** — `getNotifications` throw → unhandled rejection, UI rơi về empty-state như thể không có thông báo | `notifications/NotificationPanel.tsx:30-48` |
| error (mark-all) | ✓ | `res.error→toast.error` | `notifications/NotificationPanel.tsx:83-88` |
| success | ✓ | `toast.success('Đã đánh dấu N thông báo là đã đọc')` | `notifications/NotificationPanel.tsx:91` |

### 4.3 `notifications/NotificationItem.tsx`

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| optimistic | ✓ không rollback | Click → `onLocalUpdate({isRead:true})` rồi `void markNotificationRead(id)` **fire-and-forget** — server lỗi thì UI vẫn đã-đọc | `notifications/NotificationItem.tsx:105-106` |
| error | ✓ | accept/decline invite có đủ `res.error→toast` + catch | `notifications/NotificationItem.tsx:63-77,90-97` |

---

## 5. Review module — phía staff (`components/review/`)

### 5.1 `review/TeamBrowser.tsx` (1886 dòng) — file browser "Tệp" (chuẩn state ĐẦY ĐỦ nhất repo)

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading | ✓ | `loading` + `loadingMore` riêng; skeleton **đếm theo `itemCount` thư mục** (fix L12 — hết 9 ghost card cho folder 1 item); nút refresh xoay khi loading | `review/TeamBrowser.tsx:188-189,317-329,1808-1825,1312` |
| error | ✓ | `error` state → `ErrorState` full-panel **có nút Retry** (`onRetry={reload}`) | `review/TeamBrowser.tsx:190,326,1334-1335` |
| empty | ✓ | `EmptyState` cục bộ phân biệt root/thư mục ("Chưa có asset nào trong workspace này" / "Thư mục trống") + CTA upload/tạo folder; sidebar "Chưa có thư mục nào." | `review/TeamBrowser.tsx:1336-1341,1852-1860,1699` |
| loading (mutation) | ✓ | pattern `const tid = toast.loading('Đang …') → toast.success/error({id: tid})` cho: tạo folder, download, move/copy, nhân bản, undo, xoá, gộp version | `review/TeamBrowser.tsx:496-510,705-731,759-776,785-796,822-830,840-853,989-998` |
| optimistic | ✓ có rollback | Đổi status chip: set trước → gọi `apiSetAssetStatus(rowVersion)` → lỗi thì **rollback về prevStatus** + guard `pendingStatusRef` chống silentRefresh đè | `review/TeamBrowser.tsx:887-919` |
| success | ✓ | toast có **action Undo** khi xoá ("Đã chuyển vào 'Đã xóa gần đây'") | `review/TeamBrowser.tsx:844-852` |
| disabled | ✓ | nút tạo thư mục `disabled={loading}` + tile "Đang tạo…" pending | `review/TeamBrowser.tsx:1773-1776,1797,1346-1347` |

### 5.2 `review/StatusControl.tsx` (197 dòng) — dropdown status trong Tệp

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading | ✓ | fetch options khi mở popover: `Loader2` "Đang tải…"; cache module-level, lỗi thì xoá cache để retry lần mở sau | `review/StatusControl.tsx:164-167,24-33` |
| error | ✓ | inline "Không tải được danh sách trạng thái." | `review/StatusControl.tsx:168-169` |
| empty (search) | ✓ | "Không có trạng thái khớp." | `review/StatusControl.tsx:170-171` |
| disabled | ✓ | prop `disabled` chặn mở + `disabled:opacity-50` | `review/StatusControl.tsx:107-114` |
| hover | ✓ | option `hover:bg-violet-500/15`, active có `Check` | `review/StatusControl.tsx:181-187` |
| success | (kế thừa) | Write + optimistic do cha (`TeamBrowser.doSetStatus`) — file này chỉ own UI mở/tìm | `review/StatusControl.tsx:8-9` |

### 5.3 `review/UploadTray.tsx` (313 dòng) — khay upload toàn cục

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| per-file states | ✓ | máy trạng thái 8 mức: `queued/uploading/paused/completing/processing/done/failed/canceled`, mỗi mức UI riêng (progress bar %, "Đang hoàn tất…", "Đang xử lý video…", check xanh, tam giác đỏ) | `review/UploadTray.tsx:209-222,245-273` |
| loading (aggregate) | ✓ | header tách 2 pha upload/transcode (fix L15 — hết nhảy "100%" rồi lùi); pill thu gọn cùng logic | `review/UploadTray.tsx:44-59,72-78` |
| error | ✓ | dòng lỗi chi tiết đỏ dưới file + nút Retry (`uploadEngine.retry`) | `review/UploadTray.tsx:238-240,290-294` |
| confirm-hủy | ✓ | hủy 1 file >50% hỏi `window.confirm`; "Hủy tất cả" là confirm inline 2 nút, chỉ cancel file chưa terminal | `review/UploadTray.tsx:178-183,112-143` |
| speed/ETA | ✓ | `formatBytes/s • còn ~ETA` khi đang upload | `review/UploadTray.tsx:231-235` |
| empty | ✓ | `items.length===0 → return null` (tray tự ẩn) | `review/UploadTray.tsx:37` |

### 5.4 `review/TeamUpload.tsx` — `UploadingCard` (card ghost trong grid Tệp)

failed (viền đỏ + message) / processing–completing (spinner) / uploading (Ring % SVG) / paused ("Đã tạm dừng") — `review/TeamUpload.tsx:151-189`.

### 5.5 `review/TaskReviewUploadSection.tsx` (726 dòng) — khối "nộp bản dựng" trong task

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| validation | ✓ | chặn file sai loại trước upload: `toast.error(meta.message)`, "Mục bàn giao chỉ nhận video…" | `review/TaskReviewUploadSection.tsx:127-131` |
| loading | ✓ | `confirmingFix`/`confirmingComplete` → nút disabled + `Loader2`; spinner "Đang xác định thư mục đích…" | `review/TaskReviewUploadSection.tsx:299-302,321-324,438` |
| loading (mutation) | ✓ | `toast.loading('Đang xác nhận đã sửa xong…') → success/error({id})`, tương tự cho Hoàn tất | `review/TaskReviewUploadSection.tsx:178-189,236-242` |
| disabled | ✓ | `disabled={!workspaceId}` trên nút upload | `review/TaskReviewUploadSection.tsx:652,707` |

### 5.6 `review/player/ReviewPlayerShell.tsx` (1207 dòng) — trang player nội bộ

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading (page) | ✓ | `!data` → full-screen `Loader2` trên nền zinc-950 | `review/player/ReviewPlayerShell.tsx:652-657` |
| error (page) | ✓ | `loadError` → màn hình lỗi + nút "Quay lại Tệp" | `review/player/ReviewPlayerShell.tsx:132-133,166,637-650` |
| loading (download) | ✓ | `downloading` → nút disabled + spinner | `review/player/ReviewPlayerShell.tsx:190-217,897-902` |
| error (action) | ✓ | toast: "Tải xuống thất bại.", lỗi upload version, "Chỉ tải lên video cho phiên bản mới." | `review/player/ReviewPlayerShell.tsx:212-213,600-604` |
| success | ✓ | `toast.success("Đang tải phiên bản mới…")` (hand-off sang UploadTray) | `review/player/ReviewPlayerShell.tsx:612` |
| disabled | ✓ | so sánh version `disabled={data.versions.length < 2}`, prev/next version disabled ở biên | `review/player/ReviewPlayerShell.tsx:823,869,885` |
| empty | ✓ | "Không có phiên bản để xem." / InfoPanel "Không có thông tin." | `review/player/ReviewPlayerShell.tsx:1015,1143` |

### 5.7 `review/player/VideoStage.tsx` — video stage (hls.js)

buffering: `!controller.ready && !controller.error → Loader2` đè poster (`VideoStage.tsx:132-135`); error: `AlertTriangle` + message từ hook (`:137-141`); poster fallback (`:122`).

### 5.8 `review/player/CommentComposer.tsx` (496 dòng)

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| disabled (send) | ✓ | `canSend` = có text/annotation/attachment **và** không còn attachment đang upload (`pendingAttach`) | `review/player/CommentComposer.tsx:256-258,475` |
| loading | ✓ | `submitting` → icon Send đổi `Loader2`; attachment đang upload có spinner riêng; nút thêm ảnh disabled khi đạt `MAX_ATTACHMENTS` | `review/player/CommentComposer.tsx:479,379,462` |
| error | ⚠️ | **dùng `alert()` native** thay toast ("surface minimally; the poll will reconcile") — lệch chuẩn sonner của toàn app | `review/player/CommentComposer.tsx:291-293` |
| success | ✓ | `onPosted(comment)` đẩy thẳng vào cache SWR (optimistic-append), reset body/annotation/range | `review/player/CommentComposer.tsx:280-290` |

### 5.9 `review/player/CommentsPanel.tsx` (283 dòng)

Empty 3 tình huống có copy riêng: chưa mở bình luận (`:220`), chỉ version khác có comment (`emptyOtherVersions(otherTotal)` `:229`), chưa có comment (`:239`); mutations đi qua SWR cache "optimistically then revalidate" (`CommentsPanel.tsx:2-4`, `useComments.ts:21-25`).

---

## 6. Review module — guest `/r/[slug]`

### 6.1 `review/share/GateScreens.tsx` (81 dòng)

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| expired / unavailable | ✓ | 2 màn full-page; copy `unavailable` cố ý gộp 404+revoked+deleted (chống enumeration) | `review/share/GateScreens.tsx:12-26,1-3` |
| loading | ✓ | `busy` → nút Continue disabled + `Loader2` | `review/share/GateScreens.tsx:31,63-66` |
| error | ✓ | **inline đỏ dưới input** ("Incorrect password…"), không toast | `review/share/GateScreens.tsx:42,60` |
| disabled | ✓ | `disabled={!password \|\| busy}` | `review/share/GateScreens.tsx:63` |
| success | ✓ | unlock cookie → `router.refresh()` cho RSC vượt gate | `review/share/GateScreens.tsx:39-40` |

### 6.2 `review/share/GuestReviewApp.tsx` (984 dòng) — app review của khách

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading (decision) | ✓ | `decisionBusy` → Approve/Request disabled + spinner; **modal chặn đóng khi busy** | `review/share/GuestReviewApp.tsx:366,797,803-813` |
| error | ✓ phân nhánh | 3 nhánh nghiệp vụ: `DECISIONS_DISABLED` → "This review isn't open for approval."; `NOT_FOUND` → đóng modal + copy trung lập (comment giải thích vì asset có thể đã trash); còn lại → message + `refreshContent()` tự chữa 409 stale | `review/share/GuestReviewApp.tsx:438-463` |
| toast (tự viết) | ✓ | **KHÔNG dùng sonner/alert** — state `toast` + `role="status" aria-live="polite"` (comment: alert() trong iframe portal "looks like the browser breaking") | `review/share/GuestReviewApp.tsx:373-377,784-788,459-461` |
| identity form | ✓ | `busy`/`error` inline + `disabled={!valid \|\| busy}` + spinner | `review/share/GuestReviewApp.tsx:922-934,976-979` |
| request-changes | ✓ | RequestBox: cancel/send disabled khi busy + spinner "Send request" | `review/share/GuestReviewApp.tsx:893-901` |
| disabled (nav/dl) | ✓ | prev/next asset disabled ở biên; download gate `allowDownload && (!downloadOnlyWhenApproved \|\| approved)` | `review/share/GuestReviewApp.tsx:591-602,617,469` |
| success | ✓ | "Approved — the team has been notified." / "Changes requested…" + postMessage sang portal cha để sync | `review/share/GuestReviewApp.tsx:423,431-434` |

---

## 7. Portal khách `/share/[token]`

### 7.1 `portal/share/SharePortalClient.tsx` (108 dòng)

**Adapter thuần** — build `DeliverableActions` bind token (useMemo `:48-91`) rồi render `DeskApp mode="share"`; **không có UI state nào tại đây**; token không ra DOM (`:9-11`). Mọi state nằm ở cây `portal/desk`.

### 7.2 `portal/desk/DeliverableSheet.tsx` — sheet duyệt deliverable (đại diện cây desk)

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading | ✓ | `busy` chung cho approve/request-changes; comment feed có `busy`/`loaded` riêng; rating `busy` riêng | `portal/desk/DeliverableSheet.tsx:39,353-356,300` |
| error | ✓ | **inline `err` state** (không toast): "Could not approve. Please try again." — comment code ghi rõ bài học "permanently disabled Approve button and no message at all → try/finally" | `portal/desk/DeliverableSheet.tsx:40,66,75,92,319` |
| disabled | ✓ | Approve/Request `disabled={busy}`; Send `disabled={busy \|\| !notes.trim()}`; rating cần đủ 3 sao mục | `portal/desk/DeliverableSheet.tsx:204-215,330,422` |
| optimistic | ✓ | request-changes "optimistic patches" lên list deliverable (header file) | `portal/desk/DeliverableSheet.tsx:6` |

---

## 8. Auth (`src/app/login`, `signup`)

### 8.1 `app/login/page.tsx` (155 dòng)

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading | ✓ | `useActionState(loginAction)` → `isPending`: nút disabled + `Loader2` + "Đang xử lý…" | `app/login/page.tsx:10,133-144` |
| error | ✓ | banner đỏ gộp `state?.error` (server action) + `urlError` (lỗi Google OAuth đọc từ `?error=`) | `app/login/page.tsx:53-57,20-26` |
| focus | ✓ | input `focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/20` | `app/login/page.tsx:82,98` |
| hover | ✓ | show/hide password `hover:bg-white/5`, nút submit `active:scale-[0.98]` | `app/login/page.tsx:103,134` |
| success | (kế thừa) | redirect do `loginAction` server-side (`next` hidden field chống open-redirect) | `app/login/page.tsx:41` |

### 8.2 `app/signup/page.tsx` (286 dòng)

`useTransition` isPending (`:35`) → nút disabled + spinner + "Đang tạo tài khoản…" (`:269-273`); error banner (`:120-127`) + `fieldErrors` per-field kể cả lỗi BotID/turnstile (`:59-60,262`); `PasswordStrengthMeter` realtime (`:217`).

---

## 9. Các domain còn lại

### 9.1 `marketplace/` — TaskMarketplace + Provider + Card

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading | ✓ | `loading` khi fetch; nút refresh `disabled={loading}` + icon xoay; poll 10s khi mở | `marketplace/TaskMarketplace.tsx:157,167-170,342-346,195-199` |
| optimistic | ✓ có rollback | Claim kéo-thả: remove card ngay → `claimTask` lỗi thì **push trả lại list** + toast.error | `marketplace/TaskMarketplace.tsx:209-222` |
| market-closed | ✓ | server trả `marketplaceOpen:false` → khoá drag + clear list | `marketplace/TaskMarketplace.tsx:173-179,230` |
| empty | ✓ | màn empty có motion icon (scale/rotate loop) | `marketplace/TaskMarketplace.tsx:395-401` |
| success | ✓ | toast "Task đã được nhận thành công!" + tự đóng modal khi hết task (500ms) | `marketplace/TaskMarketplace.tsx:224-226` |
| hover (card) | ✓ | style theo type (SHORT/LONG/TRIAL) `hover:border-*`, accent bar `group-hover:opacity-100`; deadline đổi màu đỏ/amber theo giờ còn lại | `marketplace/MarketTaskCard.tsx:27-57,82,67-77` |
| trigger | ✓ | Provider 2 mode floating/event, badge count broadcast qua CustomEvent | `marketplace/MarketplaceProvider.tsx:25-46` |

### 9.2 `admin/PayrollTable.tsx` (142 dòng) — bảng lương

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| default | ✓ | tính `baseSalary` từ `tasks.wageVND` + bonus từ payroll record, chip ĐÃ TRẢ/CHƯA TRẢ | `admin/PayrollTable.tsx:52-66,92-100` |
| hover | ✓ | `hover:bg-white/5` mỗi row; nút Thanh toán `hover:scale-105` | `admin/PayrollTable.tsx:69,109` |
| loading / error / empty | ✗ KHÔNG xử lý | Thuần props render — `users` rỗng → bảng chỉ còn header, không message; không mutation tại đây | `admin/PayrollTable.tsx:20-28,50-52` |

### 9.3 `admin/PaymentModal.tsx` (155 dòng) — xác nhận trả lương (đụng tiền thật)

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading | ✓ | `loading` → nút disabled + "Đang xử lý…" | `admin/PaymentModal.tsx:25,136-140` |
| error | ⚠️ generic | `toast.error('Lỗi thanh toán')` — **không surface `res.error`** thật từ server; **không try/catch**: nếu `confirmPayment` throw thì `setLoading(false)` (`:40`) không chạy → nút kẹt "Đang xử lý…" vĩnh viễn | `admin/PaymentModal.tsx:29-47` |
| empty (QR) | ✓ | "Chưa cập nhật QR" khi user thiếu paymentQrUrl | `admin/PaymentModal.tsx:107-110` |
| success | ✓ | toast + `onClose()` (list cập nhật nhờ cha; copy STK có toast riêng) | `admin/PaymentModal.tsx:41-43,49-52` |

### 9.4 `invoice/InvoiceModal.tsx` (858 dòng) — tạo hóa đơn

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| loading (fetch task) | ✓ | spinner giữa modal; lỗi fetch → toast "Không tải được dữ liệu" | `invoice/InvoiceModal.tsx:514,98-99` |
| empty | ✓ | "Không có task chưa xuất hóa đơn." | `invoice/InvoiceModal.tsx:516` |
| validation | ✓ | chặn trước submit: "Vui lòng chọn hồ sơ thanh toán", "Hóa đơn đang trống" | `invoice/InvoiceModal.tsx:316-317` |
| loading (generate) | ✓ | `isGenerating` → nút disabled + spinner + "Đang tạo…"; progress 2 bước bằng toast ("Đang lưu hóa đơn…" → "Đã lưu! Đang tạo PDF…") | `invoice/InvoiceModal.tsx:44,597-601,373-377` |
| error | ✓ | `catch → toast.error('Lỗi: …')` | `invoice/InvoiceModal.tsx:439-441` |
| success | ✓ | "Đã tạo & tải hóa đơn về!" | `invoice/InvoiceModal.tsx:437` |

### 9.5 `invoice/ClientInvoicesTable.tsx` (126 dòng)

Per-row busy: `isVoiding===id` disable đúng nút đó (`:24,114`); void dùng `confirm()` native chứ không `useConfirm` (`:27`); download có toast 3 pha info→success/error (`:45-67`); empty "Chưa có hóa đơn nào." (`:71-73`); refresh qua `router.refresh()` (`:35`).

### 9.6 `crm/ClientList.tsx` (888 dòng) — cây khách hàng CRM

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| drag-merge | ✓ | banner `animate-pulse` "Kéo và thả vào một khách hàng chính khác để gộp…" khi `draggingId` | `crm/ClientList.tsx:181-196` |
| loading (merge) | ⚠️ | `toast.loading('Đang gộp khách hàng...')` nhưng **`toast.dismiss()` toàn cục** rồi toast mới — không dùng pattern update-by-id như review module | `crm/ClientList.tsx:117-123` |
| validation | ✓ | rename: "Tên không được để trống" | `crm/ClientList.tsx:103` |
| error | ✓ | mọi action check `res.error→toast.error` (rename/merge/trash/split) | `crm/ClientList.tsx:111,123,387,402` |
| empty | ✓ | phân biệt search vs no-data: "Không tìm thấy kết quả." / "Chưa có dữ liệu khách hàng." (text thô, không EmptyState) | `crm/ClientList.tsx:225-235` |
| success | ✓ | toast từng nghiệp vụ ("Đã gộp khách hàng thành công!", "Đã chuyển vào Thùng rác") | `crm/ClientList.tsx:121,388,403` |

### 9.7 `layout/ProfileWorkspaceSwitcher.tsx` (338 dòng)

| State | Có? | Chi tiết thật | Bằng chứng |
|---|---|---|---|
| default | ✓ | dropdown profile+workspace, load 1 lần khi mount qua server action | `layout/ProfileWorkspaceSwitcher.tsx:68-75` |
| loading | ✗ KHÔNG xử lý | Trước khi data về, `profiles.length===0 → return null` — **switcher biến mất thay vì skeleton** | `layout/ProfileWorkspaceSwitcher.tsx:109` |
| error | ✗ KHÔNG xử lý | `getMyProfilesAndWorkspaces().then(...)` **không có `.catch`** — action lỗi ⇒ switcher biến mất im lặng vĩnh viễn, không retry | `layout/ProfileWorkspaceSwitcher.tsx:68-75` |
| success (switch) | ✓ | đổi workspace = `router.push('/{wsId}/admin\|dashboard')`, không cần state | `layout/ProfileWorkspaceSwitcher.tsx:93-101` |

---

## 10. Tổng hợp finding xuyên suốt (để Phase 3 states.md + Phase 4 dùng)

| # | Finding | Bằng chứng đại diện | Mức |
|---|---|---|---|
| 10.1 | **3 thế hệ pattern state song song** (reload-cả-trang → refresh-không-pending → review-module đầy đủ). Cùng 1 hành vi "đổi status task" có 3 UX khác nhau tùy màn hình | §2.2 vs §2.6 vs §5.1 | Kiến trúc |
| 10.2 | **`window.location.reload()` sau mutation** ở cả 2 bảng task desktop (xoá, bulk-xoá, trả task) — mất scroll/filter/selection, tải lại toàn app | `NewDesktopTaskTable.tsx:183,200,757`; `TaskWorkflowTabs.tsx:210,226,913` | High (UX) |
| 10.3 | **`deleteTask` đơn lẻ không check error** ở cả 2 bảng desktop: server lỗi vẫn `toast.success('Đã xoá task')` rồi reload — user tưởng đã xoá | `NewDesktopTaskTable.tsx:181-182`; `TaskWorkflowTabs.tsx:208-209` | High (đúng/sai) |
| 10.4 | **`isPending` bị vứt** (`const [, startTransition]`) ở 2 wrapper chính → có transition nhưng không bao giờ có loading indicator | `DashboardActionWrapper.tsx:126`; `MobileTaskView.tsx:115` | Medium |
| 10.5 | **Button base không có loading prop** → mỗi component tự chế spinner/label (≥10 kiểu: `Loader2`, đổi text, icon xoay…), không thống nhất | `ui/button.tsx:36-53` + §2-§9 | Medium (DX) |
| 10.6 | **4 kênh báo lỗi khác nhau đang sống**: sonner toast (đa số), `alert()` native (`CommentComposer.tsx:293`), toast tự viết aria-live (`GuestReviewApp.tsx:373-377` — có lý do iframe), inline err (`GateScreens`, `DeliverableSheet`). Guest surfaces cố ý tránh sonner; nội bộ thì lệch chuẩn không chủ đích | §5.8, §6.2, §6.1, §7.2 | Medium |
| 10.7 | **Optimistic update chỉ có 4 chỗ**, 2 chỗ có rollback đúng (TeamBrowser status `:887-919`, Marketplace claim `:209-222`), 1 fire-and-forget không rollback (NotificationItem `:105-106`), 1 qua SWR (useComments). Toàn bộ bảng task KHÔNG optimistic — trái quy tắc `.claude/CLAUDE.md` mục 3 | §5.1, §9.1, §4.3, §2 | Medium |
| 10.8 | **Nuốt lỗi im lặng**: NotificationBell bỏ `res.error` (`:27-30`); NotificationPanel `try/finally` không catch (`:30-48`); ProfileWorkspaceSwitcher không `.catch` → switcher biến mất khi action lỗi (`:68-75,109`) | §4.1, §4.2, §9.7 | Medium |
| 10.9 | **PaymentModal (tiền thật)**: lỗi generic không surface `res.error`; không try/catch → throw làm nút kẹt "Đang xử lý…" | `admin/PaymentModal.tsx:29-47` | Medium |
| 10.10 | **Empty state 2 chuẩn**: mobile + review dùng `ui/EmptyState` variant hóa; bảng admin GĐ1 + CRM dùng text thô giữa bảng | §1.5 vs §2.2/§9.6 | Low |
| 10.11 | **Confetti: không tồn tại** trong repo; success cao nhất là màn hình success của AddTaskModal (motion scale-in) + toast có action Undo của TeamBrowser | `AddTaskModal.tsx:1466-1486`; `TeamBrowser.tsx:844-852` | Ghi nhận |
| 10.12 | Điểm sáng nên nhân rộng: pattern `toast.loading(tid) → toast.success/error({id:tid})` + optimistic-rollback + rowVersion + skeleton đếm theo itemCount của review module | `TeamBrowser.tsx:496-510,887-919,1808-1825` | Khuyến nghị |

**Khuyến nghị bám repo (không sách giáo khoa):** không cần thư viện mới — chuẩn review-module đã có sẵn trong repo. Việc đáng làm theo thứ tự tác động: (1) vá 10.3 (2 dòng check `res.error`); (2) thay `window.location.reload()` bằng `startTransition(router.refresh())` + dùng `isPending` đang bị vứt (10.2+10.4 — cùng file, ít rủi ro vì actions giữ nguyên); (3) thêm `loading` prop vào `ui/button.tsx` rồi để các form mới dùng dần; (4) PaymentModal surface `res.error` + try/finally vì đây là luồng tiền thật.

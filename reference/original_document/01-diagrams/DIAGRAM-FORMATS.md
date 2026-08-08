# Cách xem diagram — định dạng & nền tảng

Vấn đề cũ: diagram nhúng PDF dạng **PNG** (raster) nên phóng to bị vỡ pixel. Đã khắc phục bằng **SVG vector** (phóng vô hạn không vỡ) + 2 nền tảng xem.

## 1. ⭐ HTML Explorer (khuyến nghị — offline, tất cả 83 diagram)

**File:** [`diagram-explorer.html`](diagram-explorer.html) — mở bằng Chrome/Edge (nhấp đúp). 1 file tự chứa, chạy offline, gửi ai cũng xem được.

- Sidebar: 11 diagram hệ thống + 24 flow (mỗi flow class/sequence/state).
- **Lăn chuột = phóng tại con trỏ · Kéo = di chuyển · Nhấp đúp = vừa khung** (như bản đồ).
- Nút: Vừa khung / − / + / 100% / **↓ SVG** (tải riêng 1 diagram).
- Ô "Lọc sơ đồ" để tìm nhanh.
- Vector nét ở mọi mức zoom — đã kiểm tra trên ERD 67 model + ERD Task (đọc được từng field khi phóng).

## 2. Figma / FigJam (canvas vô hạn, editable) — các MAP chính

**Board:** https://www.figma.com/board/k0UeSomu03oaqyhNY2tz5z

Đã đẩy **9 map native** (editable như diagram thật, tự tách vùng không chồng): 8 ERD domain (Tenant, Task, CRM, Finance, Review module, Auth, Notification, Misc) + **Kiến trúc hệ thống**. Đây là các "map" cần canvas vô hạn nhất.

**Giới hạn của FigJam generate:** không hỗ trợ **class diagram**, và với diagram nhiều node thì kém gọn hơn bản render sẵn. Vì vậy **class diagram + toàn bộ sequence/state theo flow nằm trong HTML Explorer** (mục 1).

### Muốn đưa THÊM diagram vào Figma (kể cả class) — import SVG:
Figma/FigJam nhận kéo-thả file SVG và giữ nguyên vector, editable. Các file SVG gốc nằm cạnh mỗi diagram:
- Hệ thống: `system/*.svg`
- Theo flow: `F01-auth/class.svg`, `F01-auth/sequence.svg`, … (83 file `.svg`).

Cách: mở 1 file Figma/FigJam → kéo-thả các `.svg` vào canvas → mỗi diagram thành vector độc lập, phóng vô hạn.

## 3. File nguồn & bản render sẵn

| Loại | Vị trí | Ghi chú |
|---|---|---|
| Nguồn Mermaid | `**/*.mmd` (83 file) | Sửa được, tái tạo mọi định dạng |
| SVG vector | `**/*.svg` (83 file) | Dùng cho Explorer + import Figma; **phóng không vỡ** |
| PNG (cũ) | `**/*.png` (83 file) | Chỉ để nhúng nhanh vào tài liệu; **không** dùng để zoom |

Render lại khi sửa `.mmd`:
```bash
mmdc -i <file>.mmd -o <file>.svg -p <puppeteer.json>
```

> Lưu ý dọn dẹp: trong Figma drafts có 1 board test tên **"AUDIT test — connectivity check"** (tạo lúc kiểm tra kết nối) — bạn có thể xoá.

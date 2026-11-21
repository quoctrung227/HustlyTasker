# HT-ORG-INVITATION-V2 — ĐẶC TẢ NGHIỆP VỤ

**Dự án:** HustlyTasker

**Phạm vi:** Quản lý lời mời thành viên tổ chức

**Trạng thái:** DEVELOPMENT ROLLOUT COMPLETE — PENDING OWNER MANUAL ACCEPTANCE

## Current development rollout — 2026-11-13

Owner attachment7575b212 subsequently authorized exactlyworkspace0005 and
notifications0004 under backup/rehearsal gates. Both applied at11:44:56/58UTC,
development history39→41,allpriorbusinessfingerprints preserved,AI0002UNAPPLIED.
Fresh restored-clone19securitychecks and25direct/proxyHTTP GETsmokePASS;previous
implementation suites below are historical,notrerun. No realemail/provider,
businessfixtures,envchange,commit/push/deploy orOwneracceptance. See
[rollout evidence/manual checklist](ORG_INVITATION_V2_ROLLOUT.md) and
[HANDOVER](HANDOVER.md). Positive directoryGET writesquota,so verifiedisolated;
only non-writing checks executed on development. Stop for Owner manual acceptance.

## Quyết định hiện hành — Owner phê duyệt ngày 13/11/2026

D01–D07 dưới đây thay thế các đề xuất chưa được duyệt trong phụ lục khảo sát.
Trong phiên implementation trước rollout, Owner cho phép code backend/frontend, tạo migration mới và kiểm thử PostgreSQL
cô lập; **không cho apply migration hoặc ghi dữ liệu development**, sửa `.env`,
gửi email thật, gọi AI, commit/push/deploy. Phụ lục khảo sát cũ là lịch sử thiết kế,
không được dùng để đảo quyết định hiện hành hoặc tuyên bố implementation đã xong.

| ID | Quyết định APPROVED |
|---|---|
| D01 | Giữ current-month MEMBER Workspace grant sau accept hợp lệ, không grant trước accept, không assign Task; giữ inherited ADMIN và rejoin stale-access cleanup, không reactivate Workspace rows đã revoke |
| D02 | New create chỉ `recipient_user_id`; giữ lịch sử và legacy token accept/decline tới expiry thực tế, không kéo dài hạn/suy đoán recipient; giữ route tương thích nhưng không quảng bá mã trong UI V2 |
| D03 | Directory chỉ Owner/Admin đủ quyền, active accounts, 20/page, server search; safe name/username, masked email chỉ khi cần phân biệt; chặn lựa chọn còn mơ hồ, không full email/phone/staff/verification/other-Profile data |
| D04 | Giữ rejoin fail-closed hiện hành; repeated accept không thêm membership/audit hoặc phục hồi quyền đã revoke; concurrency kiểm chứng PostgreSQL thật cô lập |
| D05 | Mở typed Invitation context/FK trong Notification hiện có; own recipient thấy trước membership, bắt buộc đúng account; read-state độc lập decision, giữ Task notifications |
| D06 | Web Invitation/Notification commit độc lập SMTP, mail không token/code/auto-accept; delivery state thật, không misleading post-commit create failure; bounded retry cùng Invitation, current active account/current email; không worker/outbox mới nếu không cần |
| D07 | TTL7 ngày; 20/page; debounce khoảng300ms; 30invites/inviter/24h,5invites/recipient-account/24h,3mail-attempts/Invitation/24h gồm lần đầu,30searches/user/minute; enforcement nhiều worker phải có bằng chứng, không chỉ cache process-local |

Contract implementation sử dụng route manager hiện có, strict ACCOUNT create,
recipient inbox/ID decisions riêng và legacy token decisions chỉ cho hàng cũ.
Mọi mutation tiếp tục server-side authorization/SessionAuthentication/CSRF.
Schema/constraint changes đã chỉ được apply trong isolated tests ở task này.
Kết quả implementation hiện hành ở mục15; mục10–14 giữ lịch sử thiết kế.

## 1. Các yêu cầu đã xác nhận

1. Khi người có quyền nhấn **Thêm thành viên**, hệ thống hiển thị danh sách những tài khoản đã đăng ký HustlyTasker.
2. Danh sách có ô tìm kiếm để phục vụ khi số lượng người dùng lớn.
3. Một tài khoản được phép tham gia nhiều tổ chức.
4. Người mời lựa chọn vai trò của người nhận ngay khi gửi lời mời.
5. Người nhận có thông báo trên Web với hai hành động: **Chấp nhận** và **Từ chối**.
6. Email chỉ thông báo có lời mời, không chứa mã để nhập.
7. Chỉ khi người nhận chấp nhận thì tư cách thành viên tổ chức mới được tạo.

**Loại bỏ khỏi luồng mời mới:** nhập mã mời, xác thực mã qua email và giao diện nhập mã.

## 2. Luồng nghiệp vụ chính

### 2.1. Người quản lý gửi lời mời

**Bước 1:** Truy cập tổ chức → Thành viên → Thêm thành viên.

**Bước 2:** Hệ thống mở hộp thoại lựa chọn tài khoản. Hiển thị:

- Tên hiển thị.
- Avatar (nếu có).
- Thông tin nhận diện tài khoản để tránh chọn nhầm người trùng tên.
- Trạng thái liên quan đến tổ chức hiện tại.

Danh sách được phân trang, mặc định tải khoảng 20 tài khoản mỗi lượt. Tìm kiếm trên server, không tải toàn bộ tài khoản về trình duyệt.

**Bước 3:** Người mời chọn một tài khoản.

**Bước 4:** Người mời chọn vai trò từ danh sách vai trò mà mình có quyền cấp theo RBAC hiện tại.

Không cho phép tự ý cấp quyền OWNER hoặc quyền vượt thẩm quyền. Chuyển quyền sở hữu tổ chức phải là nghiệp vụ riêng.

**Bước 5:** Nhấn **Gửi lời mời**.

Hệ thống kiểm tra quyền, tài khoản đích, tổ chức, vai trò, lời mời trùng và tư cách thành viên hiện tại.

**Bước 6:** Tạo Invitation ở trạng thái `PENDING`, tạo thông báo trên Web và lên lịch gửi email.

**Kết quả:** Người nhận chưa trở thành thành viên ngay lập tức.

### 2.2. Người nhận xử lý lời mời

**Bước 1:** Người nhận đăng nhập HustlyTasker bằng đúng tài khoản được mời.

**Bước 2:** Tại biểu tượng thông báo, hiển thị nội dung tương tự:

> Bạn được mời tham gia tổ chức **ABC Studio** với vai trò **MEMBER** bởi **Nguyễn Văn A**.

Hai nút hành động:

- **Chấp nhận**
- **Từ chối**

**Bước 3A — Chấp nhận:**

Hệ thống kiểm tra lại lời mời còn hiệu lực, tài khoản đang đăng nhập đúng người nhận và vai trò được mời vẫn hợp lệ.

Tạo membership bằng transaction; cập nhật lời mời thành `ACCEPTED`.

Thông báo kết quả thành công và cho phép người dùng truy cập tổ chức theo vai trò đã được cấp.

**Bước 3B — Từ chối:**

Cập nhật lời mời thành `DECLINED`.

Không tạo membership. Thông báo kết quả và cập nhật trạng thái phía người mời.

### 2.3. Email thông báo

Email chỉ chứa:

- Tên tổ chức mời.
- Tên người mời.
- Vai trò được đề nghị.
- Thông tin rằng người nhận cần đăng nhập HustlyTasker để phản hồi.
- Đường dẫn đến trang thông báo/lời mời trên Web.

Email **không chứa mã mời hoặc nút có thể chấp nhận lời mời mà không cần đăng nhập**.

Nếu email gửi thất bại, lời mời và thông báo Web vẫn tồn tại. Trạng thái gửi email được theo dõi riêng với trạng thái Invitation.

## 3. Trạng thái Invitation

| Trạng thái | Ý nghĩa |
|---|---|
| `PENDING` | Đã gửi lời mời, đang chờ phản hồi |
| `ACCEPTED` | Người nhận đã đồng ý |
| `DECLINED` | Người nhận đã từ chối |
| `REVOKED` | Người có thẩm quyền đã thu hồi |
| `EXPIRED` | Lời mời đã quá hạn |

`REVOKED` và `EXPIRED` là hai trạng thái tôi đề xuất bổ sung để quản lý vòng đời lời mời an toàn.

Các trạng thái kết thúc không được tiếp tục chấp nhận.

Vai trò được chọn lúc gửi phải được lưu cùng Invitation. Không được tự động đổi vai trò người nhận trong lúc chờ mà không có hành động quản lý minh bạch.

## 4. Quy tắc nghiệp vụ bắt buộc

**BR-01 — Quyền gửi lời mời:** Chỉ tài khoản có quyền quản lý thành viên tổ chức mới được xem danh sách ứng viên và gửi lời mời.

**BR-02 — Phạm vi lựa chọn:** Chỉ tài khoản đã đăng ký và còn hoạt động mới đủ điều kiện nhận lời mời.

**BR-03 — Nhiều tổ chức:** Một tài khoản có thể thuộc nhiều tổ chức, nhưng không được có hai membership trùng nhau trong cùng tổ chức.

**BR-04 — Lời mời trùng:** Không được tồn tại hai lời mời `PENDING` cho cùng một tài khoản trong cùng một tổ chức.

**BR-05 — Phân quyền:** Người gửi không được mời người khác vào vai trò cao hơn quyền cấp vai trò của mình.

**BR-06 — Xác nhận danh tính:** Chỉ đúng tài khoản được mời mới có thể chấp nhận hoặc từ chối, bất kể ai biết ID của lời mời.

**BR-07 — Tính nguyên tử:** Chấp nhận lời mời và tạo membership phải được xử lý an toàn trước thao tác đồng thời. Không được tạo trùng thành viên khi nhấn nhiều lần.

**BR-08 — Bảo mật thông tin:** Danh sách tài khoản chỉ cung cấp thông tin cần thiết để lựa chọn. Không hiển thị số điện thoại, dữ liệu tổ chức khác, vai trò nội bộ hoặc thông tin nhạy cảm.

**BR-09 — Phạm vi tổ chức (Owner D01 APPROVED):** Chỉ sau accept hợp lệ mới tạo/kích hoạt Profile membership và áp dụng policy hiện có để thêm MEMBER vào Workspace tháng hiện tại. Không cấp Workspace access trước accept, không tự phân công Task; giữ inherited ADMIN governance. Rejoin phải cleanup quyền Workspace cũ, không tự kích hoạt lại Workspace rows đã revoke hoặc cấp quyền ngoài vai trò/tổ chức tương ứng.

**BR-10 — Audit:** Lưu người gửi, người nhận, tổ chức, vai trò được đề nghị và các sự kiện gửi, chấp nhận, từ chối, thu hồi.

**BR-11 — Thông báo:** Lời mời và trạng thái thông báo đọc/chưa đọc là hai khái niệm độc lập. Đọc thông báo không có nghĩa là đã phản hồi lời mời.

**BR-12 — Chống spam:** Phải có giới hạn tần suất gửi và gửi lại email/thông báo.

## 5. Các trường hợp lỗi và cách xử lý

| Mã | Tình huống | Hành vi yêu cầu |
|---|---|---|
| E01 | Tài khoản được chọn đã thuộc tổ chức | Không gửi; thông báo “Người này đã là thành viên” |
| E02 | Đã có lời mời `PENDING` | Không tạo trùng; cho phép xem lời mời hiện tại |
| E03 | Người nhận từ chối | Không tạo membership; người có quyền có thể mời lại theo quy tắc chống spam |
| E04 | Người nhận không còn hoạt động | Chặn chấp nhận và vô hiệu hóa lời mời nếu cần |
| E05 | Người gửi không đủ quyền | Backend từ chối, dù frontend vẫn hiển thị nút |
| E06 | Chọn vai trò không được phép cấp | Backend từ chối và không tạo lời mời |
| E07 | Người khác cố chấp nhận bằng ID Invitation | Từ chối, không tiết lộ dữ liệu lời mời |
| E08 | Người nhận nhấn Chấp nhận hai lần | Không tạo hai membership; phản hồi trạng thái nhất quán |
| E09 | Hai quản lý đồng thời mời cùng một tài khoản | Chỉ một lời mời hợp lệ được tạo |
| E10 | Email không gửi được | Giữ lời mời trên Web; ghi nhận lỗi gửi email để có thể thử lại |
| E11 | Lời mời bị thu hồi trước khi chấp nhận | Không cho chấp nhận; hiển thị “Lời mời đã bị thu hồi” |
| E12 | Lời mời hết hạn | Không cho chấp nhận; hướng dẫn liên hệ người quản lý |
| E13 | Tổ chức bị xóa hoặc không còn hoạt động | Không tạo membership |
| E14 | Vai trò được mời không còn hợp lệ | Không cấp quyền sai; yêu cầu người quản lý gửi lời mời phù hợp |
| E15 | Người dùng mất mạng khi nhấn Chấp nhận | Khi kết nối lại, tải trạng thái thật từ server; không đoán kết quả |
| E16 | Tìm kiếm không có kết quả | Hiển thị trạng thái rỗng, không báo lỗi hệ thống |
| E17 | Tìm kiếm có hàng nghìn kết quả | Phân trang và giới hạn dữ liệu trả về |
| E18 | Hai tài khoản trùng tên | Hiển thị thông tin nhận diện bổ sung, tránh chọn nhầm |
| E19 | Người mời bị mất quyền hoặc rời tổ chức khi lời mời còn chờ | Không để lời mời trở thành đường cấp quyền ngoài kiểm soát; cần kiểm tra lại thẩm quyền theo chính sách đã chọn |
| E20 | Người dùng đang ở một tổ chức khác khi nhận lời mời | Chấp nhận đúng tổ chức được mời, không làm thay đổi membership của tổ chức hiện tại |

## 6. Màn hình cần thay đổi

### A. Tổ chức → Thành viên

- Thay form nhập email/mã mời bằng bộ chọn tài khoản.
- Hiển thị danh sách người dùng và ô tìm kiếm.
- Chọn người nhận và vai trò.
- Xác nhận gửi lời mời.
- Hiển thị danh sách lời mời đang chờ và hành động thu hồi phù hợp quyền.

### B. Thông báo trên Web

- Bổ sung loại thông báo lời mời tổ chức.
- Hiển thị rõ tổ chức, người mời, vai trò.
- Có nút Chấp nhận/Từ chối với trạng thái loading và phản hồi lỗi.
- Sau khi xử lý, thay nút bằng trạng thái kết quả.

### C. Email

- Thay email chứa mã mời bằng email thông báo.
- Không yêu cầu người dùng nhập bất kỳ mã nào.
- Không đặt thao tác chấp nhận lời mời trực tiếp trong email.

## 7. Tác động hệ thống cần rà soát

| Thành phần | Nội dung |
|---|---|
| Invitation | Chuyển từ mời dựa trên email/code sang mời dựa trên account ID |
| Membership | Chỉ tạo khi Invitation được chấp nhận |
| Notification | Thêm thông báo lời mời với hành động Chấp nhận/Từ chối |
| Email | Chỉ phục vụ thông báo, có cơ chế xử lý gửi thất bại |
| RBAC | Kiểm tra quyền mời, chọn vai trò và quyền truy cập tổ chức |
| Frontend | Bộ chọn tài khoản, tìm kiếm, quản lý lời mời, xử lý thông báo |
| Database | Có thể cần migration; phải khảo sát schema hiện tại trước khi quyết định |
| Documentation | Cập nhật SRS, HLD, API contract, ERD và quy trình nghiệp vụ liên quan |

Không được tự động xóa lời mời cũ hoặc làm mất lịch sử Invitation khi chuyển đổi cơ chế.

## 8. Điều kiện nghiệm thu

Chức năng chỉ được coi là hoàn thành khi:

1. Người quản lý có quyền xem và tìm kiếm được tài khoản đã đăng ký.
2. Tìm kiếm vẫn hoạt động khi danh sách lớn.
3. Người mời chọn đúng vai trò được phép cấp.
4. Người nhận nhận được thông báo Web và email thông báo theo cấu hình hệ thống.
5. Người nhận có thể Chấp nhận hoặc Từ chối trực tiếp trên Web.
6. Membership chỉ được tạo đúng một lần khi chấp nhận.
7. Không còn yêu cầu nhập mã mời trong luồng mới.
8. Không lộ danh sách tài khoản cho người không có quyền.
9. Không thể chấp nhận thay người khác, cấp sai vai trò hoặc tham gia tổ chức ngoài ý muốn.
10. Dữ liệu membership, các tổ chức hiện hữu và lịch sử lời mời được bảo toàn.

## 9. Giới hạn triển khai — cập nhật theo Owner approval

- Được sửa source và tạo migration mới trong phạm vi Invitation V2.
- Được apply migration và mutation tests chỉ trên PostgreSQL cô lập.
- Không apply migration hoặc thay đổi dữ liệu database development.
- Không sửa `.env`, gửi email thật hoặc gọi AI provider.
- Không thay đổi AI, Task, Review hoặc Analytics ngoài các tích hợp quyền truy cập thực sự cần thiết.
- Không commit, push hoặc deploy.

---

## 10. Historical source audit — trước Owner implementation approval

**HISTORICAL: DESIGN READY trước khi Owner phê duyệt D01–D07.**
Các mô tả "chưa được duyệt/chưa triển khai" ở mục10–14 là checkpoint khảo sát,
không phải ranh giới implementation hiện hành. Quyết định APPROVED đầu tài liệu
và checkpoint implementation trong HANDOVER có hiệu lực mới nhất.

Mục 1–9 ở trên được giữ nguyên từ đặc tả Owner cung cấp. Phụ lục này là kết quả
khảo sát source và đề xuất thiết kế; không phải implementation đã được duyệt.
Không sửa runtime, model, migration, settings, `.env` hoặc database. Không gửi
email, gọi AI hoặc chạy mutation tests trong task đặc tả này.

Checkpoint rollout trước vẫn là **DEVELOPMENT ROLLOUT COMPLETE — PENDING OWNER
MANUAL ACCEPTANCE**. Báo cáo trước ghi nhận 39 migrations, `tasks.0005`,
`reviews.0003`, `notifications.0003` APPLIED và `ai.0002` UNAPPLIED. Đây là bằng
chứng lịch sử của rollout, không phải một lần kiểm tra database mới trong task
V2. Không apply lại các migration đó.

### 10.1. Source thực tế và khoảng cách với yêu cầu

| Nội dung | Đã có trong source | V2 còn thiếu hoặc phải thay đổi sau phê duyệt |
|---|---|---|
| Lifecycle | [ProfileInvitation](../backend/apps/workspace/models.py) có đủ `PENDING`, `ACCEPTED`, `DECLINED`, `REVOKED`, `EXPIRED`, expiry mặc định 7 ngày | Không tạo lại các status; tiếp tục dùng effective expiry và terminal timestamps |
| Delivery | Cùng model có `QUEUED`, `SENT`, `FAILED`, thời điểm attempted/delivered riêng | Chỉ mới tách dữ liệu lưu trữ; điều kiện accept vẫn phụ thuộc `SENT` |
| Recipient | Có `recipient_user` nullable, email normalized và token digest bắt buộc | Chưa có acceptance kind để phân biệt account-bound V2 với token-bound legacy |
| Duplicate pending | `uniq_pending_profile_user` và `uniq_pending_profile_email` đã có | Tái sử dụng account uniqueness; xử lý pending đã hết hạn trong transaction trước khi mời lại |
| Membership | `uniq_active_profile_user` chỉ chặn hai membership **active**; lịch sử inactive có thể nhiều hàng | Không được tự thay thành unique toàn bộ lịch sử hoặc xóa hàng cũ; cần quyết định rejoin rõ ràng |
| Role ceiling | `_can_issue_role` trong [invitation_services.py](../backend/apps/workspace/invitation_services.py): Owner cấp ADMIN/MEMBER, Admin chỉ MEMBER | Giữ nguyên; Workspace Admin hoặc `is_staff` đơn thuần không đủ quyền quản lý thành viên Profile |
| Gửi lời mời | POST nhận `recipient_email`, `requested_role`; email không nhất thiết đã có account | Chưa có global registered-account candidate search và account-ID create contract |
| Phản hồi | Accept/decline nhận token; kiểm tra current normalized email và recipient identity | Chưa có inbox/detail/accept/decline theo ID cho chính account được mời |
| Email failure | [invitation_delivery.py](../backend/apps/workspace/invitation_delivery.py) dùng `on_commit`, có thể lưu PENDING/FAILED rồi trả 503; mail preflight có thể chặn trước insert | V2 cần giữ Invitation + Web notification dù mail lỗi, không báo tạo thất bại sau khi transaction đã commit |
| Notification | [models.py](../backend/apps/notifications/models.py), [access.py](../backend/apps/notifications/access.py), [serializers.py](../backend/apps/notifications/serializers.py) chỉ hỗ trợ Task context | Chưa có invitation target; current feed/mark-read đòi Profile và Workspace access nên người chưa là thành viên không thấy được |
| React | [OrganizationMembers](../frontend/src/features/members/OrganizationMembers.tsx) dùng email; [recipient page](../frontend/src/pages/members.tsx) nhập mã; [NotificationHub](../frontend/src/features/notifications/NotificationHub.tsx) mở Task | Cần account picker và typed invitation notification; không thể chỉ thêm một nút hoặc event enum |

Chưa tìm thấy standalone SRS V3/HLD kèm bằng chứng phê duyệt của giảng viên.
Repository có diagrams/ERD lịch sử đã đối chiếu: [invitation sequence](../reference/original_document/01-diagrams/F03-membership-invite/sequence.mmd),
[tenant ERD](../reference/original_document/01-diagrams/system/erd-tenant.mmd) và
[notification ERD](../reference/original_document/01-diagrams/system/erd-notify.mmd).
Chúng mô tả hệ Prisma/Next/Resend cũ, gồm direct-add, TTL 14 ngày và quota khác;
không phải contract Django/V2 hoặc quyền đổi stack/quy tắc hiện hành. Không áp
những giá trị đó vào V2. API/DATABASE/RBAC và DECISION_LOG hiện tại vẫn là nguồn
đối chiếu; đồng bộ tài liệu/ERD tương ứng khi contract/schema được duyệt.

### 10.2. Hai điểm phải phân biệt với thiết kế hiện hành

**BR-09 và Workspace tháng hiện tại.**
`_join_current_workspace_after_acceptance` đang tự tạo WorkspaceMember MEMBER
của đúng tháng hiện tại khi accept hợp lệ. Quy tắc này đã được Owner duyệt ở
HT-FE-WORKSPACE-INHERITANCE-01 và có regression tests. V2 yêu cầu không tự thêm
Workspace, nên không được gọi nguyên service accept cũ rồi coi BR-09 đã đạt.
Đề xuất V2 ACCOUNT chỉ tạo/reactivate Profile membership; không tạo WorkspaceMember,
không assign Task và không khôi phục Workspace access cũ. Cần chốt phạm vi
supersede đối với V2 và pending legacy trước khi code.

Việc **không tạo WorkspaceMember** khác với quyền quản trị Workspace đã được kế
thừa hợp lệ từ vai trò Profile ADMIN. Không tự bỏ inherited ADMIN governance hoặc
đổi RBAC toàn hệ thống. Nếu muốn ADMIN cũng không có quyền đó, đây là quyết định
RBAC riêng ngoài đặc tả triển khai Invitation.

**E19 đã có kiểm tra cho accept.** `_validate_original_inviter_locked` xác minh
account/membership người mời còn active và vẫn đủ role ceiling. V2 nên giữ kiểm
tra này tại mutation, không chỉ dựa trên capability lúc GET. Decline không cấp
quyền, nên đề xuất vẫn cho đúng recipient từ chối khi inviter đã mất quyền;
không dùng sự mất quyền của inviter để giữ recipient mắc kẹt trong lời mời.

## 11. Historical technical proposal — superseded where Owner decisions differ

### 11.1. Identity, directory và dữ liệu tối thiểu

- Tái sử dụng User/Profile/ProfileMembership/ProfileInvitation. Chỉ User active
  đã đăng ký mới xuất hiện trong candidate API cho V2.
- Candidate API chỉ mở cho active Profile Owner/Admin có quyền quản lý lời mời
  tại tổ chức active. Không phải endpoint public hoặc directory cho mọi User.
- Trả account reference để POST, tên hiển thị an toàn, thông tin phân biệt đã
  được duyệt và quan hệ với **tổ chức đang xét**. Không trả email/phone, email
  verification state, `is_staff`, danh sách tổ chức khác hoặc vai trò nơi khác.
- User hiện có first_name/last_name/username, không có avatar field. Không thêm
  upload/avatar schema; có thể dùng initials trang trí cạnh tên.
- Username có thể chứa `@`, dạng số điện thoại hoặc dữ liệu liên hệ. Không tự coi mọi username là
  public-safe. [Task presentation](../backend/apps/tasks/presentation.py) có
  lọc email/UUID/control characters cho nhãn Task nhưng không phải policy đã
  duyệt cho directory toàn hệ thống. Đề xuất full name + safe username; nếu
  không có thông tin phân biệt an toàn thì không cho gửi dựa trên nhãn mơ hồ.
  Không hiển thị UUID làm tên hoặc tự tạo public handle khi chưa duyệt.
- Native pagination hiện có: 20/page, tối đa 100 theo
  [pagination.py](../backend/api/pagination.py). Search server-side có thứ tự
  ổn định và tie-break bằng ID; validate input, giới hạn query và kiểm tra query
  plan với dữ liệu synthetic lớn. Index mới chỉ được thiết kế sau đo lường.
- Có thể trả `ACTIVE_MEMBER`, `PENDING_INVITATION`, `AVAILABLE`, hoặc trạng thái
  không khả dụng an toàn. Admin không được nhận ID/role của pending ADMIN nằm
  ngoài role ceiling; trả trạng thái không khả dụng chung nếu cần.
- Account ID trong POST là target, không phải chứng cứ authorization. Backend
  revalidate User active, Profile, role, pending và membership tại transaction.

### 11.2. Schema tối thiểu cần review

Đây là **đề xuất cần migration sau phê duyệt**, không phải thay đổi đã tạo:

1. Thêm discriminator trên ProfileInvitation, ví dụ `acceptance_kind` với
   `EMAIL_TOKEN` / `ACCOUNT`; tên chính thức sẽ chốt tại contract review.
   Default cho hàng cũ là legacy EMAIL_TOKEN; không suy đoán/backfill recipient.
2. ACCOUNT bắt buộc `recipient_user`; email chỉ là metadata delivery, không còn
   là quyền accept. Không chuyển account được mời khi email thay đổi.
3. Rà soát token digest nullability/conditional validation cho ACCOUNT và giữ
   legacy digest uniqueness. Không phát hành raw invitation token trong luồng mới.
4. Thay `pinv_use_requires_sent` bằng CHECK có điều kiện theo acceptance kind:
   legacy vẫn đòi SENT; ACCOUNT được accept/decline cả QUEUED/FAILED. Giữ nguyên
   lifecycle/timestamps/delivery constraints và pending-account uniqueness.
5. Mở rộng Notification bằng protected Invitation FK nullable và context branch
   rõ ràng: legacy null-context, Task context hiện tại, Invitation context có
   Profile/Invitation/Audit event nhưng không Task/Workspace. Task branch vẫn
   giữ đủ context và current-tenant access checks.
6. Thêm event invitation và indexes recipient/status/order nếu query plan yêu
   cầu; không tạo một Notification giả gắn với Task/Workspace để vượt constraint.
   Không đổi FK/delete policy hoặc history cũ theo suy đoán.

Account invitation visibility phải dựa trên **recipient_user = request.user**
và acceptance kind, không đòi membership có trước. Đây là quyền đọc invitation
tối thiểu, không phải quyền đọc Profile detail, Workspace, Task hoặc thành viên.
Notification và Invitation IDs không mang quyền tự thân; kiểm tra canonical FK,
same-Profile target, audit event và recipient trong service/projection.

### 11.3. API contract proposal

Các route dưới đây là **đề xuất chưa tồn tại**, trừ manager routes được ghi rõ.
Giữ SessionAuthentication, CSRF, strict serializers, non-cacheable private data
và error conventions hiện hành; không thêm AllowAny cho recipient endpoints.

| Method / route đề xuất | Request / response và quyền |
|---|---|
| GET `/api/v1/profiles/{profile_id}/invitation-candidates/?search=...&page=1` | Manager-only paginated directory; safe labels, current-organization relation, allowed roles; không tải toàn bộ accounts |
| POST `/api/v1/profiles/{profile_id}/invitations/` — canonical route đã có | V2 strict body `{recipient_user_id, requested_role}`; server gắn ACCOUNT, actor/inviter/Profile từ context; không nhận owner/status/membership ID. Sau cutover từ chối email-only create, không giữ một đường tạo mới ngoài account policy |
| GET `/api/v1/invitations/` | Inbox của đúng authenticated recipient, hỗ trợ zero-Profile và đang chọn Profile khác; chỉ ACCOUNT records theo policy đã duyệt |
| GET `/api/v1/invitations/{invitation_id}/` | Recipient-only minimum metadata và current action capabilities; không lộ email/digest/tổ chức khác |
| POST `/api/v1/invitations/{invitation_id}/accept/` | Strict empty body; xác minh account, lifecycle, expiry, role/inviter lại; tạo membership atomically; không nhận Profile/role/User override |
| POST `/api/v1/invitations/{invitation_id}/decline/` | Strict empty body; terminalize đúng invitation, không tạo membership |
| POST manager `.../invitations/{id}/revoke/` — route đã có | Tái sử dụng quyền/role ceiling; race với accept được serialize |
| POST manager `.../invitations/{id}/resend/` — route đã có | ACCOUNT: retry email cho cùng invitation, không rotate role/expiry hoặc tạo pending/notif mới; legacy vẫn giữ semantics cũ trong thời gian tương thích được duyệt |

Response tạo thành công nên là `201` với Invitation metadata, `delivery_status`
và email warning an toàn nếu có. PENDING có nghĩa chờ recipient, không có nghĩa
SMTP thành công. Recipient action response không tiết lộ delivery diagnostics.
Notification DTO cần typed target `TASK` / `PROFILE_INVITATION`; không tái dùng
Task UUID fields bắt buộc hoặc tin `target_url` tùy ý. Bổ sung capability read-only
để UI hiển thị action; mutation luôn revalidate.

Giữ `400` cho input sai, `403` cho action bị cấm trong scope đã biết, tenant-safe
`404` cho invitation/account ngoài quyền, `409` cho state/duplicate conflict và
`429` cho quota. Có thể trả invitation hiện tại khi duplicate **chỉ nếu manager
có quyền đọc đúng record đó**. Không biến duplicate response thành đường lộ
pending ADMIN cho Admin hoặc directory cho User không có quyền.

### 11.4. Transaction, replay và lịch sử

**Create:** xác minh quyền → lock tenant aggregate/counters theo thứ tự thống
nhất → revalidate target/role/pending/membership → insert Invitation PENDING +
AuditLog + invitation Notification trong **một transaction** → commit → email.
Lỗi audit/notification rollback cả business mutation. Không tạo membership lúc gửi.

**Accept:** recipient-specific lookup → lock Profile/Invitation và các identity/
membership cần thiết → kiểm tra lại account active, expiry, pending, invited role,
inviter hiện tại và Profile active → tạo/reactivate membership hợp lệ → terminalize
ACCEPTED + audit trong cùng transaction. Không tự assign, đổi Task/Review hoặc
tạo WorkspaceMember ở ACCOUNT V2 theo BR-09 được chốt. Serialize cả direct-add,
revoke/demote membership và accept để không bypass policy bằng race.

Review lock order trước code, gồm sorted User locks nếu nhiều account, advisory
recipient counters qua nhiều Profile và current Profile-first lock conventions;
không thêm target-User lock tùy tiện gây đảo thứ tự. Concurrency tests phải dùng
transaction thật trên PostgreSQL, không chỉ mocked sequential requests.

Đề xuất repeated accept của **cùng recipient trên cùng ACCOUNT đã ACCEPTED** trả
canonical state, không ghi thêm membership/audit/notification. Nếu membership
sau đó bị revoke, replay không được reactivate hoặc cấp lại quyền; UI không báo
đang có access chỉ từ historical ACCEPTED. Opposite/terminal actions conflict.
Không tự replay POST khi mất mạng; GET lại state thật trước khi cho thử tiếp.

Khi reactivate Profile membership, phải giữ `_revoke_stale_workspace_access`
trong transaction: soft-revoke các WorkspaceMember cũ còn active và giữ audit/
lịch sử, không tự reactivate các hàng đã bị thu hồi. Chỉ bỏ current-month grant
là chưa đủ, vì membership Profile active có thể khiến Workspace rows cũ tự có
hiệu lực lại. Không chạy cleanup hay đổi dữ liệu lịch sử trong task thiết kế này.

Inactive rejoin hiện chỉ cho đúng một hàng inactive, cùng role, không OWNER;
nhiều hàng hoặc role khác bị từ chối. Đề xuất giữ nguyên điều kiện an toàn này
cho V2 cho tới khi Owner chọn chính sách khác. Không cấp role mới bằng cách
ghi đè membership lịch sử hoặc siết unique tất cả rows khi chưa kiểm kê/backfill.

### 11.5. Email, retry và chống spam

- Email V2 chỉ có tên tổ chức/người mời an toàn, role và liên kết tới trang Web
  đang được bảo vệ đăng nhập. Không có token/code, URL bearer credential hoặc
  GET accept; mở email không tạo membership và không đánh dấu đã phản hồi.
- Sau commit, email fail phải ghi FAILED an toàn nhưng giữ Web Invitation và
  Notification. Không raise 503 khiến frontend hiểu nhầm create chưa commit.
  Nếu mail chưa cấu hình, V2 vẫn có thể tạo Web invitation và thể hiện rõ email
  chưa gửi theo delivery policy được duyệt, không giả SENT.
- SENT chỉ là mail backend chấp nhận gửi, không chứng minh hộp thư nhận được.
  Không log email body, raw token, credentials hoặc provider exception.
- `transaction.on_commit` hiện tại **không phải durable queue**. Crash sau commit
  có thể để QUEUED chưa gửi. Cần chốt bounded explicit retry/recovery hay durable
  outbox trước khi hứa tự động retry. Không tự thêm Celery/Redis/worker.
- ACCOUNT retry giữ cùng invitation/role/expiry và notification/read-state;
  không rotate sang record mới như legacy resend. Re-invite sau terminal state
  là hành động tạo lời mời mới có audit/rate limit, không hồi sinh hàng cũ.
- Current durable issuance caps là 30 records/inviter/24h và 5/normalized email/24h;
  cache token-action throttle 5/day. Đây là giá trị **source hiện có**, không
  phải quota V2 đã duyệt. V2 cần account-keyed recipient budget, search throttle
  và **email-attempt** budget vì retry cùng hàng không tăng record counter cũ.
  Không gọi process-local DRF cache là multi-worker protection.
- Trước send/retry cần xác minh recipient account còn active và địa chỉ nhận hiện
  tại; thay email không chuyển quyền invitation. Chốt destination policy để
  không gửi tên tổ chức tới địa chỉ cũ sau email change. Không tự áp email-verified
  prerequisite làm khóa các tài khoản legacy.
- Không kiểm tra `.env`, cấu hình SMTP hoặc gửi email thật trong audit này.
  Tình trạng SMTP Owner từng báo hoạt động là lịch sử; **REAL EMAIL DELIVERY NOT
  VERIFIED IN THIS TASK**. Live send cần authorization riêng.

## 12. Historical UI/UX design research — implementation follows current approval

Giữ master teal/neutral, Plus Jakarta Sans và shared Dialog/FormField/Button/
Alert/Pagination. Không tạo design system hoặc dependency mới.

1. Manager mở **Thêm thành viên**: ô **Tìm tài khoản**, danh sách chọn bằng native
   radio rows, tên + disambiguator đã duyệt, current-organization status, pagination.
   Giữ lựa chọn qua trang tìm kiếm nhưng revalidate khi gửi; không chọn mơ hồ chỉ
   bằng display name. Chọn role từ server capability, không từ suy luận frontend.
2. Pending vô hiệu submit lặp; lỗi field gần input, summary focus khi nhiều lỗi;
   empty/no-results khác lỗi network. Đóng dialog/đổi User/Profile hủy request;
   key gồm User/Profile/search/page, reset page và bỏ kết quả stale.
3. Invitation notification có tên tổ chức/người mời/role và **Chấp nhận/Từ chối**.
   Mark-read độc lập với decision. Sau server xác nhận mới đổi status; chưa có
   quyền tenant vẫn chỉ đọc được invitation tối thiểu của chính recipient.
4. Sau accept invalidate Profile list, recipient invitations, Notification feed/
   unread count. Nếu đang ở tổ chức khác, giữ context hiện tại và hiện **Đến tổ
   chức**; không tự nhảy tenant hoặc chép cache của Profile cũ sang Profile mới.
5. Refresh/pagination/login lại phải lấy đúng server state; session expiry/logout
   xóa private cache. Email link về trang inbox/notifications, không chứa token.
6. Native dialog có Escape, focus return; action labels rõ, focus visible, live
   status không cướp focus. Kế hoạch kiểm tra 375/768/1440 và landscape, keyboard,
   long labels và axe; chưa có browser verification V2 ở task này.

Đã đọc đầy đủ skill local và master. Nhóm audit đã chạy offline, exit 0:

```text
search.py "server search pagination" --domain ux -n 3
search.py "notification action pending feedback" --domain ux -n 3
search.py "loading button disable async" --domain ux -n 3
search.py "async search stale response cleanup" --stack react -n 3
```

Kết quả Search/No Results, Loading Buttons, Effects/Cleanup và Forms/Debounce
được dùng cho đề xuất ở trên. Kết quả Mobile/Haptic ở query notification ban đầu
đã bị loại và query hẹp được chạy lại; không áp guidance native-only vào Web.
Đây là nghiên cứu thiết kế, không phải UI đã triển khai/được đo responsive/axe.

## 13. Historical traceability/test plan — apply approved D01 exception

Owner đã chọn **giữ** current-month MEMBER grant sau accept hợp lệ. Vì vậy các
case BR09 dưới đây về không auto-grant thuộc phương án cũ: implementation tests
phải kiểm tra current-month grant theo policy có sẵn, không grant trước accept,
không grant Workspace lịch sử/revoked rows và không tự assign Task.

| Requirement | Cách kiểm chứng cần bổ sung trên PostgreSQL cô lập / React thật |
|---|---|
| BR01, BR05; E05–E06 | Owner/Admin ceilings, MEMBER/Workspace Admin/staff-only denied; quyền đổi giữa GET và POST |
| BR02, BR08; E04, E16–E18 | Active registered search; input/large dataset/order/pagination/query bounds; duplicate names; không email/phone/other-Profile data; safe labels và role-ceiling redaction |
| BR03–BR04, BR07; E01–E03, E08–E09 | Concurrent invite/invite, accept/accept, accept/decline/revoke/direct-add; unique pending/account và active membership; replay không cấp lại quyền sau revoke; inactive ambiguity |
| BR06; E07, E20 | Người chưa có Profile thấy own inbox; wrong-account IDOR kể cả biết UUID; đang chọn Profile khác vẫn accept đúng invitation; không ảnh hưởng Profile đang chọn |
| BR09; E13–E14, E19 | Archived Profile/recipient/inviter inactive/demoted; không auto Workspace/Task access ở ACCOUNT; rejoin soft-revoke stale active Workspace rows, giữ lịch sử và không reactivate revoked rows; giữ inherited ADMIN theo role policy và legacy behavior được chốt |
| BR10 | Invitation + audit + Web notification rollback cùng transaction; audit không chép token/email body; giữ lịch sử sender/recipient/role và event proof |
| BR11; E10–E12, E15 | Mark-read không accept; decline không tạo membership; mail unavailable/FAILED vẫn Web accept được; expiry/revoke/current-state refresh sau mất mạng |
| BR12 | Account-keyed durable quotas, repeated mail-attempt limits, search abuse; chống bypass bằng đổi email/multi-Profile/multi-worker; không reset expiry khi resend |
| Migration compatibility | Legacy default/mode, conditional SENT CHECK, nullable token rules, Notification three branches/FKs; full chain và restore rehearsal; không sửa applied migrations/không backfill đoán identity |
| Frontend/E2E | Manager chọn account+role → send → recipient account khác login → notification accept/decline → membership đúng; reload/pagination, 400/403/404/409/429, CSRF, logout/cache isolation, responsive/keyboard/axe |

Existing tests được đọc nhưng **không chạy lại**: `test_invitation_api.py`,
`test_invitation_model_services.py`, `test_invitation_delivery_api.py`,
`test_workspace_inheritance.py`, `OrganizationMembers.test.tsx`,
`members.test.ts`, `pages/members.test.tsx`, `NotificationHub.test.tsx` và
`frontend/e2e/members.spec.ts`. Các tests token/503/current-month grant hiện tại
định nghĩa legacy behavior, không được xóa hoặc nới assertion để V2 pass.
1056 backend và 1182 frontend PASS là checkpoint rollout lịch sử, không phải
V2 test result. Task này chỉ kiểm tra documentation/source preservation và diff.

## 14. Historical pending decision package — D01–D07 now approved above

| ID | Cần chốt | Khuyến nghị, CHƯA APPROVED |
|---|---|---|
| INV2-D01 | Phạm vi BR-09 supersede current-month auto-grant đã duyệt trước đây | ACCOUNT V2 không tạo WorkspaceMember; legacy giữ semantics đến hết giai đoạn tương thích. Giữ inherited ADMIN governance hợp lệ, không đổi global RBAC |
| INV2-D02 | Legacy pending/token UI/API chuyển tiếp thế nào | Discriminator default EMAIL_TOKEN cho rows cũ; new create chỉ ACCOUNT sau cutover. Giữ lịch sử và legacy accept/decline có thời hạn; không tự expose pending legacy qua ID hoặc suy đoán recipient |
| INV2-D03 | Thông tin phân biệt tài khoản được phép đưa ra directory | Safe full name + safe username, không raw email/UUID làm nhãn. Nếu không thể phân biệt an toàn thì chặn chọn mơ hồ; phương án masked email/public handle cần privacy/schema review riêng |
| INV2-D04 | Rejoin/inactive membership và repeated accept | Giữ fail-closed current role/one-inactive/non-OWNER policy; repeated accept trả canonical state, không cấp lại quyền đã revoke. Không siết unique toàn bộ historical rows tùy tiện |
| INV2-D05 | Kiến trúc invitation Notification và schema | Mở typed invitation context + protected FK trên hệ thống hiện tại; quyền riêng recipient trước membership, Task branch giữ nguyên. Duyệt constraint/migration/backward compatibility trước code |
| INV2-D06 | Delivery/recovery và destination sau email change | Web commit độc lập, email trạng thái thật, explicit bounded retry cùng invitation. Chỉ hứa durable automatic dispatch nếu duyệt outbox; current email không quyết định account identity |
| INV2-D07 | Quotas/search/retry/expiry/visibility | Giữ TTL 7 ngày và ceilings hiện có làm baseline đề xuất; duyệt budget account-ID, email-attempt/search limits, metadata của archived/terminal invite. Decline không cấp quyền nên cho recipient từ chối khi inviter đã mất quyền |

Các yêu cầu xác nhận ở mục 1 được ghi nhận từ Owner, không bị đổi thành đề xuất.
Gói lựa chọn ở bảng này được giữ làm lịch sử, không phải trạng thái phê duyệt
hiện hành. Owner đã cung cấp quyết định thay thế cụ thể ở đầu tài liệu và cho
phép implementation/tạo migration mới; apply development vẫn chưa được phép.

Đề xuất thực hiện sau Owner review: (A) chốt các decision và contract/schema,
(B) backend account invitations + recipient notification + isolated security/
migration tests, (C) React picker/decision flow + real isolated E2E, (D) rollout
database riêng có backup/rehearsal/approval. Không bắt đầu các bước đó ở task này.

## 15. Historical implementation verification — before approved development rollout

**HT-ORG-INVITATION-V2 — IMPLEMENTATION COMPLETE — PENDING DEVELOPMENT MIGRATION APPROVAL.**
Mục này và bảng APPROVED đầu tài liệu là trạng thái hiện hành. Các phương án cũ
ở mục10–14, đặc biệt phương án bỏ current-month grant, không phải rule runtime.

| Quyết định | Implementation và bằng chứng |
|---|---|
| D01 | Accept mới cấp membership và current-month MEMBER Workspace grant theo policy có sẵn; giữ inherited ADMIN, rejoin soft-revocation, không reactivate revoked rows/assign Task. Backend và inheritance browser4/4 kiểm chứng |
| D02 | Public create chỉ recipient_user_id/requested_role; legacy EMAIL_TOKEN giữ digest/expiry/identity, accept/decline tới expiry thật. Không legacy resend/new token UI; direct compatibility route còn hoạt động trong browser |
| D03 | Owner/Admin directory, active accounts,20/page,server search max100, safe labels/masked fallback, ambiguous selection disabled. Backend privacy/input/query tests và browser25candidate/pagination/search |
| D04 | Transaction/explicit row-lock order và scoped uniqueness; fail-closed rejoin, canonical replay không cấp lại quyền. Real PostgreSQL concurrent invite/quota/accept/reciprocal create/retry tests |
| D05 | Existing Notification mở PROFILE_INVITED + protected Invitation FK, strict context branches. Own recipient projection trước membership, independent mark-read, dedup and existing Task branch preserved |
| D06 | Web Invitation+audit+notice atomic; mail after commit, FAILED không tạo misleading503. Retry cùng ID/role/expiry/read-state, current active User/current email; fake failed-mail browser vẫn Web accept thành công |
| D07 | TTL7days,20/page,~300msdebounce; durable PostgreSQL rolling30invites/inviter24h,5/recipient-account24h,3mailattempts/Invitation24h,30searches/user/minute; quota boundary races kiểm chứng, không phụ thuộc process-local cache |

### 15.1. Canonical routes and React flow

Các API dưới `/api/v1/`, authenticated SessionAuthentication và CSRF trên mutation:

- `GET profiles/{profile_id}/invitation-candidates/?search=...&page=...`.
- `GET/POST profiles/{profile_id}/invitations/`; POST dùng registered recipient
  account ID và requested role, không nhận owner/tenant/token/email để cấp quyền.
- Manager detail/revoke/resend routes giữ canonical paths; resend chỉ retry
  ACCOUNT PENDING và không tạo Invitation mới hoặc kéo dài expiry.
- `GET invitations/`, `GET invitations/{id}/`, `POST invitations/{id}/accept/`
  và `POST invitations/{id}/decline/` chỉ cho đúng recipient ACCOUNT.
- Existing notifications feed/unread-count/read hỗ trợ typed Invitation target;
  không cần Task giả, không dùng notification làm tenant authority.
- Legacy `POST invitations/accept/` và `decline/` chỉ xử lý token rows cũ theo
  identity/security policy có sẵn; không quảng bá token form trong navigation mới.

Manager chọn account/role → Web create201 → người nhận login đúng account →
own notification/inbox → xác nhận Accept/Decline → server revalidate → refresh
profiles/invitations/notifications. Read không accept; không tự chuyển Profile.
Người chưa có Profile vẫn nhận/đáp lời mời. Không optimistic membership grant.

### 15.2. New migration files and legacy preservation

`workspace.0005_account_invitations` thêm acceptance_kind, nullable ACCOUNT token,
conditional legacy SENT/identity/email uniqueness, inbox index và durable quota
models. Rows cũ mặc định EMAIL_TOKEN, không đoán recipient hay kéo dài expiry.
`notifications.0004_invitation_context` thêm protected Invitation FK/event/strict
three-branch CHECK; phụ thuộc workspace0005 và notifications0003 hiện hữu.
31migration files có sẵn không thay đổi; full graph/models và legacy migration
fixtures PASS trên isolated PostgreSQL. Reverse có new ACCOUNT/notification data
không tương thích bị từ chối atomic; không hứa rollback tự động hoặc xóa rows.

Hai migration mới CHƯA được apply development. Rollout riêng phải fresh preflight,
backup+restore rehearsal, exact scoped plans, phối hợp backend stop/start và
post-check dữ liệu. Không dùng migrate tổng quát hoặc apply ai.0002 development.
Không restart code mới trên persistent schema cũ chỉ vì isolated tests PASS.

### 15.3. Actual verification and source preservation

| Check | Final result |
|---|---|
| Focused backend Invitation/Notification/migration/delivery |62/62 PASS,23.148s,Python/launcher0|
| Full isolated PostgreSQL backend |1108/1108 PASS,398.807s,0FAIL/ERROR/SKIP,actual child0/launcher0|
| pip/Django/model drift/migration graph/full chain |PASS,isolated shared runner0|
| Frontend unit/contract |1236/1236 PASS,36files,39.54s,process0|
| Typecheck/Biome/build |PASS,process0|
| Real isolated Invitation V2 browser |7/7 PASS,52.8s|
| Members / fake delivery failure browser |4/4 PASS40.2s /2/2 PASS16.0s|
| Inheritance / reassignment / stability browser |4/4 PASS28.8s /4/4 PASS35.0s /4/4 PASS20.4s|

Browser final25/25; Playwright/launcher/isolatedbackend exits0, owned DB/resources
removed. Actual responsive375/768/1440/812x375, axe, keyboard/focus, cache/logout,
wrong recipient, zeroProfile, role ceiling, CSRF, fake SMTPFAILED and bounded
retry, legacy acceptance and current-month grant were exercised. Mock/unit and
real browser results are separate; no manual development acceptance is claimed.
Initial invalid-search500 and test selector/native-search Escape failures remain
in ignored evidence with corrections and passing reruns; no hidden failed test.

UI UX Pro Max full skill/master and offline UX/React searches applied to native
radio picker, pagination/debounce, pending/errors, cancel/stale cleanup and explicit
decision confirmation. Existing teal/neutral tokens and shared components retained.
Screenshots/raw process/stdout/stderr/child receipts are Git-ignored under
`.local_backups/HT-ORG-INVITATION-V2-IMPLEMENTATION/`.

Git main/HEAD31f0af932a9ffaf3e578115d63faa4a776e75175 unchanged;817baseline files
retained,31pre-existing migration hashes unchanged. No .env read/change, development
SQL connection, real email/provider call, commit/push/deploy. Metadata-only Docker
inspection confirms historical dev container/volume/loopback remain; no fresh row
inventory or SQL fingerprint was taken, so previous39migrations/row counts are
historical, not a V2 query result. No V2 or AI migration was applied to development.
Final documentation verification:affected-document relative links resolve,
git diff --check exit0 and16new files have no whitespace errors. Owned test-resource
cleanup is recorded independently from test process success.

### 15.4. Remaining limitations and exact safe continuation

REAL EMAIL DELIVERY NOT VERIFIED IN THIS TASK. Fake/locmem transport verifies both
success/failure; SENT means transport acceptance, not inbox delivery. on_commit is
not durable outbox: crash can leave QUEUED/reserved attempt; explicit capped retry
is provided, no worker guaranteed. Quota history retention/maintenance needs a
separate production-scale policy. Build has a nonfatal chunk-size advisory.

Only next step proposed: Owner reviews implementation and separately authorizes
controlled development migration with fresh backup/rehearsal. No rollout is
authorized by passing tests. SRS/HLD submitted material was not silently edited;
record this approved V2 policy in a later report revision when Owner chooses.
Stop at OWNER REVIEW GATE; no AI/Project/deployment/adjacent task is started.

# ORIGINAL_REQUIREMENTS.md

# HustlyTasker System Requirements

## 1. Tổng quan hệ thống

## Tên hệ thống

HustlyTasker


## Mục tiêu

HustlyTasker là hệ thống quản lý workflow sản xuất nội dung dành cho agency/team.

Hệ thống hỗ trợ:

- Quản lý workspace.
- Quản lý thành viên.
- Quản lý task.
- Theo dõi tiến độ sản xuất.
- Review sản phẩm.
- Tương tác với client.
- Quản lý tài chính.
- Quản lý CRM.
- Tự động hóa workflow.


## Kiến trúc nghiệp vụ

Hệ thống hoạt động theo mô hình:

User
→ Profile
→ Workspace
→ Task
→ Review
→ Client Approval
→ Completion
→ Finance


---

# 2. User Roles


## Internal User

### Owner

Quyền:

- Quản lý workspace.
- Quản lý thành viên.
- Quản lý task.
- Quản lý tài chính.


## Admin

Quyền:

- Quản trị workspace.
- Phân quyền user.
- Duyệt workflow.


## Member / Editor

Quyền:

- Nhận task.
- Thực hiện task.
- Upload sản phẩm.
- Cập nhật trạng thái.


## Guest Reviewer

Quyền:

- Review sản phẩm thông qua link.
- Không cần tài khoản.


## Client

Quyền:

- Xem portal.
- Xem deliverable.
- Approve hoặc request change.


---

# 3. Module List


# F01 - Authentication System

## ID

F01


## Tên chức năng

User Authentication


## Mô tả

Quản lý đăng ký, đăng nhập và xác thực người dùng.


## User Role

All users


## Luồng hoạt động

1. User đăng ký tài khoản.
2. Hệ thống gửi OTP email.
3. User xác nhận OTP.
4. User đăng nhập.
5. Hệ thống tạo session.


## Input

- Email.
- Username.
- Password.
- OTP.


## Output

- Account được tạo.
- Session đăng nhập.


## Priority

Critical


---

# F02 - Profile & Workspace Management

## ID

F02


## Tên chức năng

Profile Workspace


## Mô tả

Quản lý team/profile và workspace theo từng tháng.


## User Role

Owner
Admin
Member


## Luồng hoạt động

1. User đăng nhập.
2. Chọn profile.
3. Chọn workspace.
4. Làm việc trong workspace.


## Input

- Profile.
- Workspace information.


## Output

Workspace được tạo hoặc truy cập.


## Priority

High


---

# F03 - Membership Invitation

## ID

F03


## Tên chức năng

Workspace Member Management


## Mô tả

Cho phép admin mời thành viên vào workspace.


## User Role

Owner
Admin


## Luồng hoạt động

1. Admin gửi invitation.
2. User nhận lời mời.
3. User accept hoặc decline.
4. Membership được cập nhật.


## Input

- Email user.
- Role.


## Output

Workspace member.


## Priority

High


---

# F04 - Task Lifecycle Management

## ID

F04


## Tên chức năng

Task Workflow


## Mô tả

Quản lý vòng đời task từ tạo đến hoàn thành.


## User Role

Owner
Admin
Editor


## Luồng hoạt động

Task flow:

Pending

↓

Assigned

↓

Working

↓

Review

↓

Completed


## Input

- Task information.
- Assignee.
- Deadline.


## Output

Task status.


## Priority

Critical


---

# F05 - Marketplace

## ID

F05


## Tên chức năng

Task Marketplace


## Mô tả

Cho phép editor nhận task khả dụng.


## User Role

Editor


## Luồng hoạt động

1. Task được public.
2. Editor xem marketplace.
3. Editor claim task.
4. Task chuyển sang assigned.


## Input

- Task availability.


## Output

Task assignment.


## Priority

Medium


---

# F06 - Review Upload System

## ID

F06


## Tên chức năng

Deliverable Review


## Mô tả

Quản lý upload file/video và quá trình review.


## User Role

Editor
Admin
Client


## Luồng hoạt động

1. Editor upload deliverable.
2. System xử lý file.
3. Reviewer kiểm tra.
4. Client approve hoặc request change.


## Input

- Video/file.
- Comment.


## Output

Review result.


## Priority

Critical


---

# F07 - Team Review Status

## ID

F07


## Tên chức năng

Internal Review Tracking


## Mô tả

Theo dõi trạng thái review nội bộ.


## User Role

Admin
Editor


## Luồng hoạt động

Editor submit → Team review → Approval.


## Input

Review status.


## Output

Updated workflow.


## Priority

High


---

# F08 - Guest Review Decision

## ID

F08


## Tên chức năng

Guest Review


## Mô tả

Cho phép khách review thông qua public link.


## User Role

Guest Reviewer


## Luồng hoạt động

1. Nhận review link.
2. Xem deliverable.
3. Approve/request change.


## Input

Review token.


## Output

Client decision.


## Priority

High


---

# F09 - Client Portal

## ID

F09


## Tên chức năng

Client Portal


## Mô tả

Cổng thông tin dành cho khách hàng.


## User Role

Client


## Luồng hoạt động

Client truy cập link → xem task → xem deliverable.


## Input

Share token.


## Output

Client dashboard.


## Priority

High


---

# F10 - Client Request Inbox

## ID

F10


## Tên chức năng

Client Request Management


## Mô tả

Quản lý yêu cầu mới từ client.


## User Role

Client
Admin


## Luồng hoạt động

Client gửi request → Admin xử lý.


## Input

Request information.


## Output

New task/request.


## Priority

Medium


---

# F11 - Task Comments

## ID

F11


## Tên chức năng

Task Discussion


## Mô tả

Cho phép trao đổi trong task.


## User Role

Member
Admin
Client


## Input

Comment text.


## Output

Comment history.


## Priority

Medium


---

# F12 - Notification System

## ID

F12


## Tên chức năng

Notification


## Mô tả

Thông báo sự kiện trong hệ thống.


## User Role

All users


## Luồng hoạt động

Event xảy ra → tạo notification → user nhận.


## Input

System event.


## Output

Notification.


## Priority

Medium


---

# F13 - Payroll Management

## ID

F13


## Tên chức năng

Payroll


## Mô tả

Quản lý thanh toán cho thành viên.


## User Role

Owner
Admin


## Luồng hoạt động

Task hoàn thành → tính toán → thanh toán.


## Input

Task completion.


## Output

Payroll record.


## Priority

Medium


---

# F14 - Finance Invoice

## ID

F14


## Tên chức năng

Invoice Management


## Mô tả

Quản lý hóa đơn và thanh toán.


## User Role

Owner
Admin


## Luồng hoạt động

Create invoice → Send → Paid.


## Input

Invoice data.


## Output

Invoice status.


## Priority

Medium


---

# F15 - CRM Share Link

## ID

F15


## Tên chức năng

CRM Management


## Mô tả

Quản lý client và share link.


## User Role

Admin


## Luồng hoạt động

Create client → Generate share link → Client access.


## Input

Client information.


## Output

CRM record.


## Priority

Medium


---

# F16 - System Automation

## ID

F16


## Tên chức năng

Cron & Webhook


## Mô tả

Tự động hóa các tác vụ hệ thống.


## User Role

System


## Luồng hoạt động

Cron/Webhook trigger → Process → Update database.


## Input

System event.


## Output

Updated system state.


## Priority

Medium


---

# 4. Non Functional Requirements


## Security

Yêu cầu:

- Authentication.
- RBAC authorization.
- Session protection.
- Input validation.
- Secret management.


## Database

Yêu cầu:

- Relational database.
- Data consistency.
- Migration support.


## Deployment

Yêu cầu:

- Containerization.
- Environment separation.
- Production deployment.


---

# 5. Development Priority


## Phase 1

Core System:

- Authentication.
- Workspace.
- Membership.


## Phase 2

Workflow:

- Task.
- Assignment.
- Review.


## Phase 3

Client:

- Portal.
- Approval.


## Phase 4

Business:

- CRM.
- Finance.
- Payroll.


## Phase 5

Optimization:

- Notification.
- Automation.
- Deployment.
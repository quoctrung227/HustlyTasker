# DATABASE_SCHEMA.md

# HustlyTasker Database Design

Version: 0.1

Status:
Draft - Before Django Models Implementation


---

# 1. Database Overview


## Database Technology

PostgreSQL


## ORM

Django ORM


## Primary Key Strategy

All main entities use:

UUID


## Common Fields

All business tables should inherit:

BaseModel


Common fields:

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| created_at | timestamp | Creation time |
| updated_at | timestamp | Last update time |



---

# 2. Accounts Domain


Application:

apps/accounts


## User


Purpose:

Store system users.


Table:

users


Fields:


| Field | Type | Constraint | Description |
|-|-|-|-|
| id | UUID | PK | User identifier |
| email | varchar | Unique | Login email |
| password | varchar | Required | Hashed password |
| first_name | varchar | Optional | First name |
| last_name | varchar | Optional | Last name |
| is_active | boolean | Default true | Account status |
| is_staff | boolean | Default false | Admin permission |
| created_at | timestamp | | Creation time |
| updated_at | timestamp | | Update time |


Relationships:


User 1 --- N Workspace (Owner)


User N --- N Workspace

through WorkspaceMember


User N --- N Task

through TaskAssignment



---

# 3. Workspace Domain


Application:

apps/workspace



# Workspace


Purpose:

Represent a working environment/team/project space.


Table:

workspaces


Fields:


| Field | Type | Constraint |
|-|-|-|
| id | UUID | PK |
| name | varchar | Required |
| description | text | Optional |
| owner_id | FK User | Required |
| created_at | timestamp | |
| updated_at | timestamp | |



Relationships:


User 1 --- N Workspace


Workspace 1 --- N WorkspaceMember


Workspace 1 --- N Task



---


# WorkspaceMember


Purpose:

Manage users belonging to workspace.


Table:

workspace_members


Fields:


| Field | Type | Constraint |
|-|-|-|
| id | UUID | PK |
| workspace_id | FK | Required |
| user_id | FK | Required |
| role | enum | Required |
| joined_at | timestamp | |



Role:


OWNER

ADMIN

MEMBER

VIEWER



Relationships:


User N --- N Workspace


through WorkspaceMember



---

# 4. Task Domain


Application:

apps/tasks



# Task


Purpose:

Store work items.


Table:

tasks


Fields:


| Field | Type | Constraint |
|-|-|-|
| id | UUID | PK |
| workspace_id | FK | Required |
| title | varchar | Required |
| description | text | Optional |
| status | enum | Required |
| priority | enum | Required |
| deadline | datetime | Optional |
| created_by | FK User | Required |
| created_at | timestamp | |
| updated_at | timestamp | |



Status:


PENDING

ASSIGNED

WORKING

REVIEW

COMPLETED

CANCELLED



Priority:


LOW

MEDIUM

HIGH

URGENT



Relationships:


Workspace 1 --- N Task


Task N --- N User

through TaskAssignment



---


# TaskAssignment


Purpose:

Store task members.


Table:

task_assignments


Fields:


| Field | Type |
|-|-|
| id | UUID |
| task_id | FK |
| user_id | FK |
| assigned_at | timestamp |



Relationships:


Task N --- N User



---


# TaskComment


Purpose:

Store discussion inside task.


Table:

task_comments


Fields:


| Field | Type |
|-|-|
| id | UUID |
| task_id | FK |
| user_id | FK |
| content | text |
| created_at | timestamp |



Relationships:


Task 1 --- N Comment



---

# 5. Review Domain


Application:

apps/reviews



# Deliverable


Purpose:

Store submitted files/results.


Table:

deliverables


Fields:


| Field | Type |
|-|-|
| id | UUID |
| task_id | FK |
| file_url | varchar |
| uploaded_by | FK User |
| status | enum |
| created_at | timestamp |
| updated_at | timestamp |



Status:


PENDING

SUBMITTED

APPROVED

REJECTED



Relationships:


Task 1 --- N Deliverable



---


# Review


Table:

reviews


Fields:


| Field | Type |
|-|-|
| id | UUID |
| deliverable_id | FK |
| reviewer_id | FK User |
| status | enum |
| comment | text |
| created_at | timestamp |



Status:


PENDING

APPROVED

REQUEST_CHANGE



Relationships:


Deliverable 1 --- N Review



---

# 6. Client Domain


Application:

apps/clients



# Client


Purpose:

Store external customers.


Table:

clients


Fields:


| Field | Type |
|-|-|
| id | UUID |
| name | varchar |
| email | varchar |
| company | varchar |
| phone | varchar |
| created_at | timestamp |
| updated_at | timestamp |



Relationships:


Client 1 --- N Invoice



---


# ShareLink


Purpose:

Allow external access.


Table:

share_links


Fields:


| Field | Type |
|-|-|
| id | UUID |
| client_id | FK |
| token | varchar |
| expired_at | timestamp |
| created_at | timestamp |



---

# 7. Finance Domain


Application:

apps/finance



# Invoice


Purpose:

Store billing information.


Table:

invoices


Fields:


| Field | Type |
|-|-|
| id | UUID |
| client_id | FK |
| invoice_number | varchar |
| amount | decimal |
| status | enum |
| due_date | date |
| paid_at | timestamp |
| created_at | timestamp |



Status:


DRAFT

SENT

PAID

OVERDUE

CANCELLED



Relationships:


Client 1 --- N Invoice


Invoice 1 --- N Payment



---


# Payment


Table:

payments


Fields:


| Field | Type |
|-|-|
| id | UUID |
| invoice_id | FK |
| amount | decimal |
| payment_method | varchar |
| paid_at | timestamp |



---

# 8. Notification Domain


Application:

apps/notifications



# Notification


Table:

notifications


Fields:


| Field | Type |
|-|-|
| id | UUID |
| user_id | FK |
| title | varchar |
| message | text |
| is_read | boolean |
| created_at | timestamp |



Relationships:


User 1 --- N Notification



---

# 9. Audit Log Domain


Purpose:

Track important system activities.


Table:

audit_logs


Fields:


| Field | Type |
|-|-|
| id | UUID |
| user_id | FK |
| action | varchar |
| entity_name | varchar |
| entity_id | UUID |
| metadata | JSON |
| created_at | timestamp |



Example:


User updated Task status

User deleted Workspace member



---

# 10. Entity Relationship Overview


User

|

| N:N

|

WorkspaceMember

|

|

Workspace


Workspace

|

| 1:N

|

Task


Task

|

| 1:N

|

Deliverable


Deliverable

|

| 1:N

|

Review



Task

|

| N:N

|

User

through TaskAssignment



Client

|

| 1:N

|

Invoice

|

| 1:N

|

Payment



---

# 11. Database Constraints


## Unique Constraints


User.email unique


Invoice.invoice_number unique


ShareLink.token unique



## Index Strategy


Create indexes for:


- User email
- Task status
- Task deadline
- Workspace owner
- Notification unread status


---

# 12. Future Extension


Possible future modules:


- Calendar
- Chat
- Analytics Dashboard
- Automation Workflow
- AI Assistant


This schema must be reviewed against original Class Diagram before Django Models implementation.
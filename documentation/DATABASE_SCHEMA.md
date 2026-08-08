# DATABASE_SCHEMA.md

# HustlyTasker Database Design


## Database Technology

PostgreSQL


## ORM

Django ORM


---

# 1. User Domain


## User

Purpose:

Store system users.


Fields:

| Field | Type | Description |
|-|-|-|
| id | UUID | Primary key |
| email | varchar | Login email |
| password | varchar | Encrypted password |
| role | varchar | User role |
| created_at | timestamp | Created time |
| updated_at | timestamp | Updated time |


Relationships:

User 1 --- N WorkspaceMember

User 1 --- N TaskAssignment


---

# 2. Workspace Domain


## Workspace


Fields:


| Field | Type |
|-|-|
| id | UUID |
| name | varchar |
| owner_id | FK User |
| created_at | timestamp |


Relationship:


User

↓

Workspace


---

# 3. Task Domain


## Task


Fields:


| Field | Type |
|-|-|
| id | UUID |
| workspace_id | FK |
| title | varchar |
| description | text |
| status | enum |
| deadline | datetime |
| created_at | timestamp |


Status:


PENDING

ASSIGNED

WORKING

REVIEW

COMPLETED


---

# 4. Review Domain


## Deliverable


Fields:


| Field | Type |
|-|-|
| id | UUID |
| task_id | FK |
| file_url | varchar |
| uploaded_by | FK User |
| status | enum |


---

# 5. Finance Domain


## Invoice


Fields:


| Field | Type |
|-|-|
| id | UUID |
| client_id | FK |
| amount | decimal |
| status | enum |


---

# Future Update

This document will be updated before creating Django Models.
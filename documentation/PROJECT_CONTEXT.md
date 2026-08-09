# HustlyTasker Project Context

## Project Overview

HustlyTasker is a workflow management system designed for content production teams and agencies.

The system manages the complete workflow:

User
→ Profile
→ Workspace
→ Task
→ Assignment
→ Review
→ Client Approval
→ Completion
→ Finance


## Main Goals

The system helps teams:

- Manage workspace collaboration.
- Create and assign tasks.
- Track production progress.
- Review deliverables.
- Manage clients.
- Track invoices and payments.
- Maintain workflow history.


## Current Technology Stack

Backend:
- Django

API:
- Django REST Framework

Database:
- PostgreSQL

ORM:
- Django ORM

Frontend planned:
- React / Next.js

Container:
- Docker


## Current Development Status

Current Phase:

PHASE 2.2 - API Architecture


Completed:

- Project documentation
- Django setup
- PostgreSQL Docker environment
- Django applications structure
- Database schema
- Django Models
- Initial migrations
- Django Admin testing
- DRF foundation


Not completed:

- Authentication API
- Permission system
- Business APIs
- Frontend
- Deployment


## Architecture Rules

Do not:

- Change technology stack without approval.
- Replace Django architecture.
- Rebuild database without reason.

Development follows:

Models
↓
Migration
↓
API
↓
Frontend


## AI Development Instructions

When continuing development:

1. Read documentation first.
2. Check current phase before coding.
3. Do not recreate completed components.
4. Preserve existing architecture.
5. Explain changes before implementation.
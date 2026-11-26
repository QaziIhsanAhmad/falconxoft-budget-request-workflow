## Budget Request Workflow — Assessment

This repository extends the Django + Inertia + React starter kit with a role-based Budget Request Workflow.

### Project Overview

The application allows employees to submit budget requests, Managers to review them, and Admins to oversee requests and financial totals.

A budget request contains:
- Title
- Requested amount
- Business justification
- Request status
- Requester and reviewer information
- Reviewer feedback
- Creation and update timestamps

### Request Lifecycle

Requests move through the following statuses:

- **PENDING** — Newly submitted and awaiting review.
- **APPROVED** — Approved by a Manager.
- **REJECTED** — Rejected by a Manager with mandatory feedback.
- **WITHDRAWN** — Withdrawn by the requesting Client.

### Roles and Permissions

| Role | Permissions |
|---|---|
| Client | Create requests, edit own pending requests, withdraw own pending requests, view permitted requests. |
| Manager | View requests available for review and approve or reject pending requests. Rejection requires feedback. |
| Admin | View all requests and financial totals; permanently delete requests. Admins cannot approve or reject requests. |

### Architecture and Design Decisions

The Budget Request Workflow follows a layered Django architecture:

- **Models:** Store budget request data and relationships.
- **Domain policies:** Centralize role-based access rules and workflow conditions.
- **Services:** Handle business operations such as creating, updating, withdrawing and reviewing requests.
- **Tests:** Verify permissions, valid transitions, validation errors and service behavior.

Business rules are enforced in backend services rather than relying only on frontend controls. This prevents unauthorized users from bypassing workflow restrictions by sending requests directly to the backend.

Manager review operations use database transactions and row-level locking to help protect against concurrent updates.

### Important Workflow Rules

- Only the owning Client can edit or withdraw their own pending request.
- Only Managers can review pending requests.
- Rejection requires non-empty feedback.
- Approved, rejected and withdrawn requests cannot be reviewed again.
- Admin privileges do not automatically grant Manager review permissions.

### Implementation Status

**Backend:** Budget request services, policies and backend tests have been implemented.

**Frontend:** The assessment-specific frontend workflow is still in progress. Do not consider the full assessment complete until the frontend workflows are implemented and verified.

### Loom Demo

Demo recording: To be added after recording.


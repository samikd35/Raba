# Organization & Tenant Architecture

## Purpose
The `src/mint/api/organization` module manages the **multi-tenancy** aspect of the application. It handles Organizations, Teams, Memberships, and Invites.

## Directory Structure
- `endpoints.py`: CRUD for Org/Team/Member resources.
- `service.py`: Business logic for inviting users, changing roles, and validating access.
- `models.py`: Pydantic definitions for `OrganizationCreate`, `TeamResponse`, etc.

## Key Concepts
1.  **Tenancy Levels:**
    - **Individual:** Default scope for a single user.
    - **Organization:** A container for multiple teams and users.
    - **Team:** A subgroup within an Organization (optional layer).
2.  **Roles:**
    - `Owner`: Full control, billing management.
    - `Admin`: User management.
    - `Member`: Standard access.
3.  **Invitations:**
    - Uses `invitations` table.
    - Flows: Email Invite -> Token Generation -> User Click -> Accept -> Link User to Org.

## Integration
- **Auth:** Heavily relies on `AuthContext` to verify if `current_user` has permission to act on `org_id`.
- **Billing:** Organizations are the primary entity for "Team Plan" billing.

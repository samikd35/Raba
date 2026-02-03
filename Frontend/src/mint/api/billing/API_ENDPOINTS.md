# Billing & Cohort API Endpoints Documentation

## Overview

This document describes all billing and cohort management API endpoints implemented in Phase 4.

**Base URL**: `/api`

**Authentication**: All endpoints require Bearer token authentication (TODO: Implement in future phase)

**Common HTTP Status Codes**:
- `200 OK` - Success
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Duplicate resource or constraint violation
- `500 Internal Server Error` - Server error

---

## Billing Endpoints

### Pricing Configuration

#### `GET /api/billing/pricing-config`

Get active pricing configuration.

**Access**: All authenticated users

**Response**: `200 OK`
```json
{
  "id": "uuid",
  "admin_seat_price_credits": 100,
  "estimated_credits_per_user": 500,
  "is_active": true,
  "effective_from": "2025-01-01T00:00:00Z",
  "effective_until": null,
  "created_by": "user-id",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

#### `PUT /api/billing/pricing-config`

Update pricing configuration (deactivates current, creates new).

**Access**: Super admin only

**Request Body**:
```json
{
  "admin_seat_price_credits": 150,
  "estimated_credits_per_user": 600
}
```

**Response**: `200 OK` (same structure as GET)

---

### Invoices

#### `GET /api/billing/invoices/pending?tenant_id={tenant_id}`

Get all pending invoices for an organization.

**Access**: Organization admin

**Query Parameters**:
- `tenant_id` (required): Organization tenant ID

**Response**: `200 OK`
```json
[
  {
    "id": "uuid",
    "invoice_number": "INV-202501-000001",
    "tenant_id": "org-123",
    "period_start": "2024-12-01T00:00:00Z",
    "period_end": "2025-01-01T00:00:00Z",
    "credits_allocated": 5000,
    "admin_seat_charges": 300,
    "total_amount_credits": 5300,
    "admin_seats_count": 3,
    "members_count": 10,
    "status": "pending",
    "issued_at": "2025-01-01T00:00:00Z",
    "due_date": "2025-01-31T00:00:00Z",
    "paid_at": null,
    "payment_method": null,
    "stripe_invoice_id": "in_1abc123",
    "stripe_hosted_invoice_url": "https://invoice.stripe.com/...",
    "stripe_invoice_pdf": "https://pay.stripe.com/.../pdf",
    "metadata": { ... },
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  }
]
```

#### `GET /api/billing/invoices/paid?tenant_id={tenant_id}&limit=50`

Get paid invoices for an organization.

**Access**: Organization admin

**Query Parameters**:
- `tenant_id` (required): Organization tenant ID
- `limit` (optional): Maximum invoices to return (1-100, default: 50)

**Response**: `200 OK` (same structure as pending invoices)

#### `GET /api/billing/invoices/{invoice_id}`

Get invoice details with line items.

**Access**: Organization admin

**Path Parameters**:
- `invoice_id` (required): Invoice ID

**Response**: `200 OK`
```json
{
  "invoice": {
    "id": "uuid",
    "invoice_number": "INV-202501-000001",
    ...
  },
  "line_items": [
    {
      "id": "uuid",
      "invoice_id": "invoice-uuid",
      "item_type": "credit_allocation",
      "description": "Credits allocated during December 2024",
      "quantity": 1,
      "unit_price_credits": 5000,
      "total_price_credits": 5000,
      "metadata": { ... },
      "created_at": "2025-01-01T00:00:00Z"
    },
    {
      "id": "uuid",
      "invoice_id": "invoice-uuid",
      "item_type": "admin_seat",
      "description": "Admin seat charges (3 seats × 100 credits)",
      "quantity": 3,
      "unit_price_credits": 100,
      "total_price_credits": 300,
      "metadata": { ... },
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

#### `POST /api/billing/invoices/{invoice_id}/mark-paid`

Manually mark an invoice as paid (for non-Stripe payments).

**Access**: Organization admin

**Path Parameters**:
- `invoice_id` (required): Invoice ID

**Request Body**:
```json
{
  "payment_method": "bank_transfer",
  "payment_reference": "TXN-123456",
  "payment_notes": "Wire transfer received on 2025-01-15"
}
```

**Response**: `200 OK` (invoice object with updated status)

---

### Bulk Purchase

#### `POST /api/billing/bulk-purchase`

Calculate bulk credit purchase and create Stripe Invoice.

**Access**: Prepay organization admin only

**Formula**: `(members × credits_per_member) + (admin_seats × seat_price)`

**Request Body**:
```json
{
  "tenant_id": "org-123",
  "member_count": 50,
  "credits_per_member": 500
}
```

**Response**: `200 OK`
```json
{
  "tenant_id": "org-123",
  "member_count": 50,
  "credits_per_member": 500,
  "member_credits_total": 25000,
  "admin_seats_count": 3,
  "admin_seat_price_credits": 100,
  "admin_seats_total": 300,
  "total_credits": 25300,
  "total_amount_usd": 25300.0,
  "stripe_invoice_id": "in_1abc123",
  "stripe_invoice_number": "ABC-1234",
  "stripe_hosted_invoice_url": "https://invoice.stripe.com/...",
  "stripe_invoice_pdf": "https://pay.stripe.com/.../pdf"
}
```

**Error Responses**:
- `400 Bad Request`: Organization is not prepay_org
- `404 Not Found`: Organization billing config not found

---

### Admin Seat Billing History

#### `GET /api/billing/admin-seat-history?tenant_id={tenant_id}&limit=50`

Get admin seat billing history for an organization.

**Access**: Organization admin

**Query Parameters**:
- `tenant_id` (required): Organization tenant ID
- `limit` (optional): Maximum records to return (1-100, default: 50)

**Response**: `200 OK`
```json
[
  {
    "id": "uuid",
    "tenant_id": "org-123",
    "billing_period_start": "2024-12-01T00:00:00Z",
    "billing_period_end": "2025-01-01T00:00:00Z",
    "admin_seats_count": 3,
    "seat_price_credits": 100,
    "total_charged_credits": 300,
    "consumption_id": "consumption-uuid",
    "deducted_at": "2025-01-01T01:00:00Z",
    "invoice_id": null,
    "status": "completed",
    "error_message": null,
    "metadata": {
      "processed_by": "billing_service",
      "processed_at": "2025-01-01T01:00:00Z"
    },
    "created_at": "2025-01-01T01:00:00Z"
  }
]
```

**Possible `status` values**:
- `completed`: Credits deducted successfully
- `invoiced`: Insufficient credits, invoice created
- `failed`: Billing failed with error

---

## Cohort Endpoints

### Cohort CRUD Operations

#### `POST /api/cohorts`

Create a new cohort in an organization.

**Access**: Organization admin

**Request Body**:
```json
{
  "tenant_id": "org-123",
  "name": "Engineering Team",
  "description": "Software engineers working on product",
  "color": "#3B82F6",
  "settings": {
    "default_credits_per_member": 1000
  }
}
```

**Response**: `201 Created`
```json
{
  "id": "cohort-uuid",
  "tenant_id": "org-123",
  "name": "Engineering Team",
  "description": "Software engineers working on product",
  "color": "#3B82F6",
  "is_active": true,
  "settings": {
    "default_credits_per_member": 1000
  },
  "created_by": "user-id",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

**Error Responses**:
- `409 Conflict`: Cohort name already exists in organization

#### `GET /api/cohorts?tenant_id={tenant_id}&include_inactive=false`

List all cohorts for an organization.

**Access**: Organization admin

**Query Parameters**:
- `tenant_id` (required): Organization tenant ID
- `include_inactive` (optional): Include inactive cohorts (default: false)

**Response**: `200 OK` (array of cohort objects)

#### `GET /api/cohorts/{cohort_id}`

Get a specific cohort by ID.

**Access**: Organization admin

**Path Parameters**:
- `cohort_id` (required): Cohort ID

**Response**: `200 OK` (cohort object)

**Error Responses**:
- `404 Not Found`: Cohort not found

#### `PUT /api/cohorts/{cohort_id}`

Update a cohort's properties.

**Access**: Organization admin

**Path Parameters**:
- `cohort_id` (required): Cohort ID

**Request Body** (all fields optional):
```json
{
  "name": "Senior Engineering Team",
  "description": "Updated description",
  "color": "#EF4444",
  "settings": {
    "default_credits_per_member": 1500
  }
}
```

**Response**: `200 OK` (updated cohort object)

**Error Responses**:
- `404 Not Found`: Cohort not found
- `409 Conflict`: New name conflicts with existing cohort

#### `DELETE /api/cohorts/{cohort_id}`

Deactivate a cohort (soft delete).

**Access**: Organization admin

**Important**: This will also deactivate all credit_lots associated with this cohort via database trigger.

**Path Parameters**:
- `cohort_id` (required): Cohort ID

**Response**: `200 OK` (deactivated cohort object with `is_active: false`)

---

### Cohort Membership Operations

#### `POST /api/cohorts/{cohort_id}/members`

Assign a user to a cohort.

**Access**: Organization admin

**Constraint**: A user can only belong to ONE cohort per organization.

**Path Parameters**:
- `cohort_id` (required): Cohort ID

**Request Body**:
```json
{
  "user_id": "user-123"
}
```

**Response**: `201 Created`
```json
{
  "id": "membership-uuid",
  "cohort_id": "cohort-uuid",
  "user_tenant_id": "tenant-membership-uuid",
  "user_id": "user-123",
  "user_email": "user@example.com",
  "user_full_name": "John Doe",
  "user_role": "member",
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Error Responses**:
- `404 Not Found`: Cohort not found or user not member of organization
- `409 Conflict`: User already in another cohort in this organization
- `400 Bad Request`: Cannot assign to inactive cohort

#### `DELETE /api/cohorts/{cohort_id}/members/{user_id}`

Remove a user from a cohort.

**Access**: Organization admin

**Path Parameters**:
- `cohort_id` (required): Cohort ID
- `user_id` (required): User ID

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "User user-123 removed from cohort cohort-uuid"
}
```

**Error Responses**:
- `404 Not Found`: Cohort not found or user not in cohort

#### `GET /api/cohorts/{cohort_id}/members?include_user_details=true`

Get all members of a cohort.

**Access**: Organization admin

**Path Parameters**:
- `cohort_id` (required): Cohort ID

**Query Parameters**:
- `include_user_details` (optional): Include user profile details (default: true)

**Response**: `200 OK`
```json
[
  {
    "id": "membership-uuid",
    "cohort_id": "cohort-uuid",
    "user_tenant_id": "tenant-membership-uuid",
    "user_id": "user-123",
    "user_email": "user@example.com",
    "user_full_name": "John Doe",
    "user_role": "member",
    "created_at": "2025-01-01T00:00:00Z"
  }
]
```

---

## Testing the Endpoints

### Using cURL

**Get Pricing Config:**
```bash
curl -X GET "http://localhost:8000/api/billing/pricing-config" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Create Cohort:**
```bash
curl -X POST "http://localhost:8000/api/cohorts" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "tenant_id": "org-123",
    "name": "Engineering Team",
    "description": "Software engineers",
    "color": "#3B82F6"
  }'
```

**Bulk Purchase:**
```bash
curl -X POST "http://localhost:8000/api/billing/bulk-purchase" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "tenant_id": "org-123",
    "member_count": 50,
    "credits_per_member": 500
  }'
```

### Using Swagger UI

Navigate to: `http://localhost:8000/docs`

- Endpoints are organized under "💰 Billing" and "👥 Cohorts" tags
- Click "Authorize" button to add Bearer token
- Try out endpoints interactively

---

## Authorization Notes (TODO)

Currently, authentication and authorization are marked as TODO in the code. In a production deployment, you should:

1. **Implement authentication middleware**:
   - Extract and validate JWT tokens
   - Reject requests with invalid/missing tokens

2. **Implement authorization checks**:
   - `require_super_admin`: Only super admins can update pricing
   - `require_org_admin`: Only organization admins can access their org's data
   - Verify user has access to the specific tenant_id

3. **Example authorization dependency**:
```python
async def require_org_admin(
    tenant_id: str,
    current_user = Depends(get_current_user)
):
    # Check if user is admin of this organization
    membership = get_user_tenant_membership(current_user.id, tenant_id)
    if not membership or membership.role not in ['owner', 'admin']:
        raise HTTPException(status_code=403, detail="Organization admin access required")
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error type",
  "detail": "Detailed error message"
}
```

Common error types:
- `BillingError`: General billing operation error
- `InvoiceNotFoundError`: Invoice not found
- `InvalidPricingConfigError`: Invalid pricing configuration
- `CohortError`: General cohort operation error
- `CohortNotFoundError`: Cohort not found
- `DuplicateCohortNameError`: Cohort name already exists
- `CohortMembershipError`: Cohort membership operation error

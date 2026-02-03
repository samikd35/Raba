# Admin API: Credit Exchange Rates

Base path: `/credit-exchange-rates`

These endpoints manage rows in the `credit_exchange_rates` table. **Admin or super_admin** role is required (via server-side `get_admin_user` and `get_super_admin_user`).

All requests must include an access token:

```
Authorization: Bearer <JWT>
Content-Type: application/json
```

> **Data types**: `credits_per_unit` is a decimal and is returned as a **string** in JSON. Timestamps are ISO-8601 with timezone.

---

## Endpoints Overview

| Method | Path          | Description                                | Success |
| -----: | ------------- | ------------------------------------------ | ------- |
|    GET | `/`           | List rates (optionally filter by `active`) | 200     |
|    GET | `/{currency}` | Get a single rate by currency              | 200     |
|   POST | `/`           | Create a new rate                          | 201     |
|  PATCH | `/{currency}` | Update an existing rate (partial)          | 200     |
| DELETE | `/{currency}` | Delete a rate                              | 204     |

---

## Models

### `CreditRateOut` (response)

```json
{
  "currency": "USD",
  "credits_per_unit": "1.000000",
  "is_active": true,
  "created_at": "2025-10-21T08:30:12.123456+00:00",
  "updated_at": "2025-10-21T09:05:00.000000+00:00"
}
```

### `CreditRateCreate` (request body for POST)

```json
{
  "currency": "USD",
  "credits_per_unit": "1.000000",
  "is_active": true
}
```

- `currency`: **3-letter ISO 4217**, case-insensitive (stored uppercase).
- `credits_per_unit`: decimal string with up to 18 digits precision and 6 decimal places; **must be ≥ 0**.
- `is_active`: boolean, defaults to `true` if omitted.

### `CreditRateUpdate` (request body for PATCH)

```json
{
  "credits_per_unit": "1.250000",
  "is_active": false
}
```

- All fields optional; send only what you want to change.

---

## 1) List rates

**GET** `/credit-exchange-rates?active=true|false`

Query params:

- `active` (optional, boolean): when provided, filters by `is_active`.

**Response 200**

```json
[
  {
    "currency": "EUR",
    "credits_per_unit": "1.080000",
    "is_active": true,
    "created_at": "2025-10-18T12:01:00.000000+00:00",
    "updated_at": "2025-10-20T09:15:33.000000+00:00"
  },
  {
    "currency": "USD",
    "credits_per_unit": "1.000000",
    "is_active": true,
    "created_at": "2025-10-18T12:00:00.000000+00:00",
    "updated_at": "2025-10-21T09:05:00.000000+00:00"
  }
]
```

**cURL**

```bash
curl -X GET "$API_BASE/credit-exchange-rates?active=true"   -H "Authorization: Bearer $TOKEN"
```

---

## 2) Get by currency

**GET** `/credit-exchange-rates/{currency}`

Path params:

- `currency` – e.g. `USD`, `eur` (case-insensitive)

**Response 200**

```json
{
  "currency": "USD",
  "credits_per_unit": "1.000000",
  "is_active": true,
  "created_at": "2025-10-18T12:00:00.000000+00:00",
  "updated_at": "2025-10-21T09:05:00.000000+00:00"
}
```

**cURL**

```bash
curl -X GET "$API_BASE/credit-exchange-rates/USD"   -H "Authorization: Bearer $TOKEN"
```

---

## 3) Create rate

**POST** `/credit-exchange-rates`

Body: `CreditRateCreate`

**Response 201**

```json
{
  "currency": "KES",
  "credits_per_unit": "0.780000",
  "is_active": true,
  "created_at": "2025-10-21T10:40:00.000000+00:00",
  "updated_at": "2025-10-21T10:40:00.000000+00:00"
}
```

**cURL**

```bash
curl -X POST "$API_BASE/credit-exchange-rates"   -H "Authorization: Bearer $TOKEN"   -H "Content-Type: application/json"   -d '{"currency":"KES","credits_per_unit":"0.780000","is_active":true}'
```

**Notes**

- Returns **409 Conflict** if a rate for that `currency` already exists.

---

## 4) Update rate

**PATCH** `/credit-exchange-rates/{currency}`

Body: `CreditRateUpdate` (any subset of fields)

**Response 200**

```json
{
  "currency": "USD",
  "credits_per_unit": "1.150000",
  "is_active": true,
  "created_at": "2025-10-18T12:00:00.000000+00:00",
  "updated_at": "2025-10-21T11:05:00.000000+00:00"
}
```

**cURL**

```bash
curl -X PATCH "$API_BASE/credit-exchange-rates/USD"   -H "Authorization: Bearer $TOKEN"   -H "Content-Type: application/json"   -d '{"credits_per_unit":"1.150000"}'
```

---

## 5) Delete rate

**DELETE** `/credit-exchange-rates/{currency}`

**Response 204 No Content**

**cURL**

```bash
curl -X DELETE "$API_BASE/credit-exchange-rates/USD"   -H "Authorization: Bearer $TOKEN"
```

---

## Errors

| Status | When                                        | Example `detail`                                                       |
| -----: | ------------------------------------------- | ---------------------------------------------------------------------- |
|    401 | Missing/invalid token                       | `"Not authenticated"`                                                  |
|    403 | Authenticated but not `admin`/`super_admin` | `{"code":"forbidden","message":"Admin or super_admin role required."}` |
|    404 | Resource not found                          | `"Rate for 'XXX' not found"`                                           |
|    409 | POST conflict (duplicate currency)          | `"Rate for 'USD' already exists"`                                      |
|    422 | Validation errors                           | Pydantic field errors                                                  |

**422 example**

```json
{
  "detail": [
    {
      "loc": ["body", "credits_per_unit"],
      "msg": "ensure this value is greater than or equal to 0",
      "type": "value_error.number.not_ge",
      "ctx": { "limit_value": 0 }
    }
  ]
}
```

---

## Behaviour & Notes

- Responses are sorted by `currency` ascending for the list endpoint.
- `currency` is treated case-insensitively by the API and stored uppercase.
- `is_active` defaults to `true` if omitted in POST.
- Timestamps are provided by the database; your client **should not** send them.
- For deactivation instead of deletion, prefer `PATCH {currency} { "is_active": false }`.

---

## Quick Axios Examples

```ts
import axios from "axios";

const api = axios.create({
  baseURL: `${API_BASE}/credit-exchange-rates`,
  headers: { Authorization: `Bearer ${token}` },
});

// List active
const { data: activeRates } = await api.get("/", { params: { active: true } });

// Get one
const { data: usd } = await api.get("/USD");

// Create
await api.post("/", {
  currency: "KES",
  credits_per_unit: "0.780000",
  is_active: true,
});

// Update
await api.patch("/USD", { credits_per_unit: "1.150000" });

// Delete
await api.delete("/USD");
```

---

**Version**: 1.0 • **Last updated**: 2025-10-21

# Payment Management & Refund Tracking Specification

**Project:** PayPause
**Module Owner:** Bhuvan

---

## 1. Overview

The Payment Management module provides transaction history, advanced multi-attribute filtering, duplicate payment warnings, and end-to-end refund tracking. It is built to operate independently while cleanly integrating with Ayush's core backend and duplicate-detection engine.

---

## 2. API Endpoints

### 1. `POST /api/payments`
Creates a validated payment record with automatic sensitive credential stripping and duplicate checks.

**Request Body:**
```json
{
  "transaction_ref": "UPI/2026/123456789012",
  "provider": "PhonePe",
  "merchant": "Swiggy Bangalore",
  "amount": 349.50,
  "currency": "INR",
  "category": "food",
  "payment_date": "2026-11-20",
  "notes": "Dinner order"
}
```

**Security Sanitization:**
If a payload accidentally contains fields like `upi_pin`, `otp`, `cvv`, or `netbanking_password`, the backend strips them before validation and persistence.

---

### 2. `GET /api/payments`
Returns paginated transactions with multi-parameter filtering:
- `transaction_ref`: UTR or reference search
- `date_from` / `date_to`: Date boundaries
- `min_amount` / `max_amount`: Numerical range filtering
- `category`: Category string
- `merchant`: Substring matching on merchant/payee name
- `provider`: Channel filter (e.g., GPay, PhonePe, Paytm, BHIM)
- `status`: Payment status (`completed`, `pending`, `failed`)
- `refund_status`: Status filter
- `limit` (default 50) & `offset` (default 0)

---

### 3. `GET /api/payments/{id}`
Returns details of a specific payment. Enforces strict user ownership; requests for records belonging to another user return `404 Not Found`.

---

### 4. `PATCH /api/payments/{id}`
Modifies mutable metadata (notes, merchant description, refund status). Immutable fields (`id`, `user_id`, `created_at`) are protected against modification.

---

### 5. `GET /api/payments/refunds`
Lists all transactions with active or resolved refund activity:
- `not_requested`
- `requested`
- `processing`
- `completed`
- `rejected`
- `unknown`

---

### 6. `GET /api/payments/summary`
Generates aggregate spend and refund metrics for the authenticated citizen:
- `total_transactions`: Total recorded payments
- `total_spend`: Sum of all payment amounts in INR
- `category_breakdown`: Key-value spending per category
- `refund_breakdown`: Counts per refund status
- `pending_refunds_count`: Active refund disputes
- `pending_refunds_amount`: Total capital locked in pending refunds

---

## 3. Duplicate Detection Integration Contract

Ayush owns the core duplicate payment detection engine. The Payment Service interacts with it through `DuplicateCheckerInterface`:

```python
class DuplicateCheckerInterface(ABC):
    @abstractmethod
    def check_payment(
        self,
        user_id: str,
        amount: float,
        transaction_ref: Optional[str],
        merchant: str,
        payment_date: str,
    ) -> DuplicateCheckResult:
        pass
```

When creating a payment, if `check_payment` returns `is_duplicate=True`, a `duplicate_warning` payload is attached to the payment response containing confidence score, matching payment ID, and reason.

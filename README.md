# PayPause — Bhuvan Independent Backend Contribution

>**Think Before Money Moves.**
> Intelligent payment safety, refund tracking, subscription management, recovery grievance desk, and Flagsmith A/B experimentation for Indian digital consumers.

---

## 1. Modules Owned by Bhuvan

1. **Flagsmith Experimentation (`/api/experiments`):** Official Flagsmith SDK integration for the `payment_intelligence_experience` multivariate feature flag (50/50 split between `risk_score_first` and `payment_passport_first`), server-side identity evaluation, canonical backend scenario validation, and duplicate-protected event tracking.
2. **Payment Management (`/api/payments`):** Validated payment records, multi-attribute transaction filtering (date range, amount range, category, provider, merchant substring), duplicate check warning contract, and aggregate spend summaries.
3. **Refund Tracking (`/api/payments/refunds`):** Full refund lifecycle tracking (`requested`, `processing`, `completed`, `rejected`, `unknown`) with reference IDs and expected dates.
4. **Recurring Payments / Subscriptions (`/api/subscriptions`):** Weekly, monthly, quarterly, and yearly subscription management with deterministic leap-year and month-end date clamping, monthly commitment metrics, and 30-day renewal alerts.
5. **Recovery Desk (`/api/recovery`):** Dispute tracking across 7 incident types, automated category-specific evidence checklists, and deterministic complaint drafts citing **RBI Circular RBI/2017-18/15**, **Helpline 1930**, and [cybercrime.gov.in](https://cybercrime.gov.in/).

---

## 2. Project Directory Structure

```text
paypause/
├── backend/
│   └── app/
│       ├── api/
│       │   ├── payments.py
│       │   ├── recovery.py
│       │   ├── experiments.py
│       │   └── subscriptions.py
│       ├── schemas/
│       │   ├── payments.py
│       │   ├── recovery.py
│       │   ├── experiments.py
│       │   └── subscriptions.py
│       ├── services/
│       │   ├── payments/
│       │   ├── recovery/
│       │   ├── experiments/
│       │   └── subscriptions/
│       ├── repositories/
│       │   ├── interfaces/
│       │   └── development/
│       ├── integrations/
│       │   └── flagsmith/
│       ├── core/
│       │   ├── config.py
│       │   ├── security.py
│       │   └── dependencies.py
│       └── dev_main.py
├── tests/
│   └── bhuvan/
├── docs/
│   ├── PAYMENT_MANAGEMENT_SPECIFICATION.md
│   ├── RECOVERY_SPECIFICATION.md
│   ├── FLAGS_EXPERIMENT.md
│   ├── BHUVAN_IMPLEMENTATION_REPORT.md
│   └── INTEGRATION_GUIDE.md
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 3. Quickstart & Local Execution

### 1. Set Up Python Virtual Environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example configuration:

```powershell
Copy-Item .env.example .env
```

**Offline mode:** Leave `FLAGSMITH_ENVIRONMENT_KEY` empty. The backend uses a deterministic SHA-256 fallback allocator.

**Live Flagsmith mode:** Add your Flagsmith Development Server-side Environment Key to your local `.env` file:

```ini
FLAGSMITH_ENVIRONMENT_KEY=your-server-side-environment-key
```

Never commit or share your `.env` file. The live integration uses the Flagsmith feature flag `payment_intelligence_experience`.

### 3. Run Standalone Development Server

```powershell
python -m uvicorn backend.app.dev_main:app --reload --port 8000
```

- **Interactive API Documentation (Swagger):** http://127.0.0.1:8000/docs
- **Alternative Documentation (ReDoc):** http://127.0.0.1:8000/redoc
- **Health Check Endpoint:** http://127.0.0.1:8000/health

---

## 4. Running Automated Tests

Run the automated test suite using Pytest:

```powershell
python -m pytest backend/tests/bhuvan -v
```

Currently, all 47 tests pass. The suite covers Flagsmith experimentation, payments, recovery, subscriptions, and backend integration.

---



## 5. Security & Privacy Guarantees

- **Sensitive Credential Protection:** All payment and dispute payloads are passed through `sanitize_payload()` which strips `upi_pin`, `otp`, `cvv`, and banking passwords prior to storage.
- **Data Ownership Isolation:** Every payment, subscription, and incident query filters by authenticated `user_id`. Cross-user access returns `404 Not Found`.
- **Backend-Owned Verification:** The frontend cannot mark experiment scenarios as correct or emit primary success metrics directly. Only server-side evaluation triggers events.

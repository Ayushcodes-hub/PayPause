
# PayPause — Ayush Core Backend

<p align="center">
  <strong>Think Before Money Moves.</strong><br/>
  An evidence-led payment safety and electricity-bill intelligence API for Indian consumers.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-Backend-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Database-Supabase-3FCF8E?logo=supabase&logoColor=white" />
  <img src="https://img.shields.io/badge/Branch-Ayush%20Core%20Backend-8957E5" />
</p>

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [System Architecture](#system-architecture)
4. [Technology Stack](#technology-stack)
5. [Getting Started](#getting-started)
6. [Environment Configuration](#environment-configuration)
7. [Running the Backend](#running-the-backend)
8. [API Reference](#api-reference)
9. [PayGuard](#payguard)
10. [BillSense](#billsense)
11. [Payment Passport](#payment-passport)
12. [Database Architecture](#database-architecture)
13. [Security and Privacy](#security-and-privacy)
14. [Testing](#testing)
15. [Project Structure](#project-structure)
16. [Current Scope and Limitations](#current-scope-and-limitations)
17. [Development Workflow](#development-workflow)

---

## Overview

**PayPause** is designed to make digital payment decisions more informed, explainable and cautious.

This branch delivers the core backend infrastructure for three major capabilities:

| Module | Purpose |
|---|---|
| PayGuard | Identifies suspicious indicators in UPI IDs, payment URLs and QR codes. |
| BillSense | Extracts, validates and analyzes electricity bills using OCR and document processing. |
| Payment Passport | Maintains authenticated, user-specific payment safety assessment history. |

The backend exposes versioned REST APIs through FastAPI and uses Supabase for authentication and persistent storage.

### Core design principles

- Evidence-driven risk analysis.
- Explainable recommendations rather than unexplained scores.
- Local document processing wherever possible.
- Authentication and user-scoped data access.
- Optional AI assistance without making AI a dependency for core functionality.
- Structured APIs designed for frontend integration.

---

## Features

### PayGuard — Payment Safety

- UPI ID structural validation.
- Payment URL inspection.
- Suspicious hostname and URL-pattern detection.
- HTTPS and transport-security indicators.
- QR image decoding.
- UPI payment URI parsing.
- Evidence-based risk scoring.
- Severity classification.
- Actionable safety recommendations.
- Payment Passport assessment persistence.

### BillSense — Electricity Bill Intelligence

- PDF and image document processing.
- Native PDF text extraction.
- OCR fallback for scanned documents.
- Electricity bill field extraction.
- Provider identification.
- Meter-reading validation.
- Charge consistency checks.
- Consumption analysis.
- OCR confidence information.
- Optional Groq-powered explanations.

### Payment Passport — Assessment History

- Authenticated assessment persistence.
- User-specific assessment history.
- Paginated assessment retrieval.
- Individual assessment lookup.
- Assessment deletion.
- Supabase PostgreSQL integration.
- Row-level security support.

---

## System Architecture

```text
                    CLIENT APPLICATION
                           |
                           |
                    REST API REQUEST
                           |
                           v
                 +--------------------+
                 |     FASTAPI        |
                 |   APPLICATION      |
                 +--------------------+
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
         PAYGUARD       BILLSENSE    PAYMENT PASSPORT
             |             |             |
       +-----+-----+   +---+-------+     |
       |     |     |   |     |     |     |
       UPI  URL   QR   PDF   OCR  AI     |
       |     |     |   |     |     |     |
       +-----+-----+   +-----+-----+     |
             |             |             |
             v             v             v
       RISK ENGINE     BILL ANALYSIS   SUPABASE
             |             |          DATABASE
             +-------------+
                           |
                           v
                 STRUCTURED API RESPONSE
```

### Request lifecycle

1. Client submits a request to the FastAPI application.
2. Protected endpoints validate the Supabase access token.
3. The relevant service performs analysis and validation.
4. The application generates a structured response.
5. PayGuard attempts to persist its assessment in Payment Passport.
6. The client receives the result and applicable recommendations.

---

## Technology Stack

| Category | Technology |
|---|---|
| Programming Language | Python |
| Backend Framework | FastAPI |
| ASGI Server | Uvicorn |
| Data Validation | Pydantic |
| Authentication | Supabase Auth |
| Database | Supabase PostgreSQL |
| Database SDK | Supabase Python SDK |
| QR Decoding | ZXing-C++ |
| Image Processing | Pillow |
| PDF Processing | PyMuPDF |
| OCR Engine | RapidOCR |
| Inference Runtime | ONNX Runtime |
| AI Integration | Groq |
| HTTP Client | HTTPX |
| Testing | Pytest |
| Async Testing | pytest-asyncio |

---

## Getting Started

### Prerequisites

Install the following:

- Python
- Git
- A Supabase project
- A Groq API key if optional AI explanations are required

### 1. Clone the repository

```powershell
git clone https://github.com/Ayushcodes-hub/PayPause.git
cd PayPause
```

### 2. Switch to Ayush's branch

```powershell
git switch feature/ayush-core-backend
```

### 3. Create a virtual environment

```powershell
python -m venv .venv
```

### 4. Activate the environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 5. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

---

## Environment Configuration

Create a `.env` file inside the `backend` directory.

Example configuration:

```dotenv
APP_NAME=PayPause API
APP_VERSION=0.2.0
ENVIRONMENT=development
DEBUG=true

API_V1_PREFIX=/api/v1
HOST=127.0.0.1
PORT=8000

CORS_ORIGINS=["http://localhost:5173"]
LOG_LEVEL=INFO

SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY

AI_PROVIDER=groq
AI_API_KEY=
AI_MODEL=
AI_REQUEST_TIMEOUT_SECONDS=30
```

### Environment variables

| Variable | Description |
|---|---|
| SUPABASE_URL | Supabase project URL |
| SUPABASE_ANON_KEY | Supabase public/anonymous key |
| SUPABASE_SERVICE_ROLE_KEY | Backend-only administrative database key |
| AI_PROVIDER | Optional AI provider selection |
| AI_API_KEY | Optional Groq API key |
| AI_MODEL | Configured Groq model |
| AI_REQUEST_TIMEOUT_SECONDS | AI request timeout |
| CORS_ORIGINS | Allowed frontend origins |
| ENVIRONMENT | Application environment |
| DEBUG | Development debugging mode |

**Important:** Never commit `.env`, expose the service-role key in frontend code, or publish API credentials.

AI configuration is optional. Core PayGuard and deterministic BillSense processing can operate without Groq.

---

## Running the Backend

Run the following commands from the repository root:

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Available documentation

| Resource | URL |
|---|---|
| API Root | http://127.0.0.1:8000/ |
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |
| OpenAPI Schema | http://127.0.0.1:8000/openapi.json |
| Health | http://127.0.0.1:8000/health |
| Readiness | http://127.0.0.1:8000/health/ready |

---

## API Reference

All versioned endpoints are under:

```text
/api/v1
```

Protected endpoints require a valid Supabase access token.

```http
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
```

### General endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Application information |
| GET | `/health` | Health check |
| GET | `/health/live` | Liveness check |
| GET | `/health/ready` | Readiness check |
| GET | `/api/v1/health` | Versioned health check |
| GET | `/api/v1/auth/me` | Authenticated user information |

### PayGuard endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/payguard/assess` | UPI, URL or combined assessment |
| POST | `/api/v1/payguard/assess-qr` | QR image assessment |

### BillSense endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/billsense/analyze` | Electricity bill analysis |

### Payment Passport endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/payment-passport/assessments` | List assessments |
| GET | `/api/v1/payment-passport/assessments/{assessment_id}` | Retrieve assessment |
| DELETE | `/api/v1/payment-passport/assessments/{assessment_id}` | Delete assessment |

---

## PayGuard

PayGuard is the payment safety analysis engine.

Its purpose is to identify suspicious indicators before a user proceeds with a digital payment.

### Supported inputs

- UPI identifiers.
- Payment URLs.
- Combined UPI and URL submissions.
- Payment QR images.

### UPI analysis

The UPI analyzer examines:

- Identifier structure.
- Structural validity.
- Suspicious keywords.
- Unusual separators and punctuation.
- Evidence severity and score contribution.

### URL analysis

The URL analyzer evaluates:

- URL structure.
- Hostname validity.
- HTTPS versus HTTP.
- Embedded credentials.
- IP-address-based destinations.
- Punycode indicators.
- URL shorteners.
- Unusual ports.
- Suspicious hostname patterns.
- Deep subdomains.

The current URL analysis is local and heuristic-based. It does not visit submitted URLs, follow redirects, resolve DNS or perform live reputation checks.

### QR analysis

The QR processing pipeline:

1. Accepts a supported image upload.
2. Validates the image.
3. Decodes the QR locally.
4. Parses supported UPI payment URIs or URLs.
5. Passes extracted information to the relevant analyzer.
6. Returns a structured risk assessment.

Supported image formats:

- PNG
- JPEG
- WEBP

### Risk scoring

Risk evidence is aggregated into a bounded score from 0 to 100.

| Score | Classification |
|---:|---|
| 0–19 | Low |
| 20–39 | Moderate |
| 40–69 | High |
| 70–100 | Critical |

The response includes:

- Risk score.
- Risk classification.
- Evidence.
- Severity.
- Recommendations.
- Assessment identifier.
- Coverage and limitations.
- Safety disclaimer.

The risk score is a heuristic indicator, not a probability of fraud or a guarantee of payment safety.

---

## BillSense

BillSense transforms electricity bills into structured information.

It combines PDF extraction, OCR, validation, consumption calculations and optional AI explanations.

### Supported document types

- PDF
- PNG
- JPEG
- WEBP

### Document processing safeguards

| Constraint | Limit |
|---|---:|
| Maximum upload size | 10 MB |
| Maximum PDF pages | 10 |
| Maximum image dimensions | 20 megapixels |
| Password-protected PDFs | Unsupported |

### Extraction pipeline

```text
             ELECTRICITY BILL
                     |
                     v
              DOCUMENT VALIDATION
                     |
                     v
              DOCUMENT DETECTION
                     |
             +-------+-------+
             |               |
             v               v
        NATIVE PDF       IMAGE / SCANNED
        EXTRACTION          DOCUMENT
             |               |
             |               v
             |           RAPIDOCR
             |               |
             +-------+-------+
                     |
                     v
               TEXT PARSING
                     |
                     v
              FIELD EXTRACTION
                     |
                     v
              BILL VALIDATION
                     |
                     v
             CONSUMPTION ANALYSIS
                     |
                     v
             OPTIONAL GROQ INSIGHTS
                     |
                     v
              STRUCTURED RESPONSE
```

### Extracted information

- Electricity provider.
- Consumer name.
- Consumer number.
- Bill number.
- Billing period.
- Bill date.
- Due date.
- Previous meter reading.
- Current meter reading.
- Units consumed.
- Energy charges.
- Fixed charges.
- Taxes.
- Late fee.
- Total payable amount.

### Supported provider patterns

The parser includes patterns for Indian electricity utilities such as:

- BESCOM
- MESCOM
- HESCOM
- GESCOM
- CESC
- TANGEDCO
- MSEDCL
- KSEB

### Validation

BillSense checks:

- Required field presence.
- Numeric field validity.
- Negative values.
- Meter-reading consistency.
- Charge arithmetic consistency.
- Extraction confidence where available.

### Consumption analysis

The service derives available consumption metrics, including:

- Units consumed.
- Billing-period duration.
- Average daily consumption.
- Consumption observations.
- Relevant validation warnings.

### Optional AI explanations

Groq provides an optional explanation layer.

The AI provider does not replace deterministic extraction, validation or calculations. If the AI service is unavailable or not configured, the API can still return its core analysis.

---

## Payment Passport

Payment Passport stores structured PayGuard assessment history for authenticated users.

### Capabilities

- Assessment persistence.
- User-specific history.
- Paginated listing.
- Individual assessment retrieval.
- Assessment deletion.
- Supabase PostgreSQL integration.

### Data design

The persistence layer stores the structured assessment rather than the original submitted UPI ID or payment URL.

Records are associated with the authenticated user's Supabase identity.

---

## Database Architecture

Payment Passport uses Supabase PostgreSQL.

Migration:

```text
supabase/migrations/002_payment_passport.sql
```

Table:

```text
public.payment_passport_assessments
```

The migration establishes:

- UUID-based record identification.
- Authenticated user association.
- Assessment identifier.
- Risk score and risk level.
- Input type.
- Structured JSON assessment.
- Creation timestamp.
- User and assessment uniqueness.
- User-scoped indexes.
- Row-level security policies.

The backend administrative client uses the service-role credential. This credential must remain server-side.

The API verifies the bearer token and derives the user identity from Supabase Auth rather than trusting a client-supplied user ID.

---

## Security and Privacy

Security considerations include:

- Supabase bearer-token verification.
- Authenticated access to protected endpoints.
- User-scoped Payment Passport operations.
- Server-only service-role credentials.
- Local URL inspection without visiting submitted URLs.
- Local QR decoding.
- QR payloads are not returned to the client.
- File type and size validation.
- PDF page and image-dimension limits.
- Optional AI processing separated from deterministic analysis.
- Structured request logging and error handling.

### Important disclaimer

PayPause is a decision-support tool. It does not authenticate a payee, guarantee that a payment is safe, prove that a transaction is fraudulent, initiate or reverse payments, or replace official bank, UPI-provider or electricity-utility channels.

Users should independently verify recipient details and important bill information.

---

## Testing

The backend test suite uses Pytest.

Run all tests from the backend directory:

```powershell
cd backend
python -m pytest tests -q
```

Run Ayush's API tests:

```powershell
python -m pytest tests\ayush\test_api.py -q
```

Run syntax checks from the repository root:

```powershell
python -m compileall -q backend\app backend\tests
```

### Latest recorded test result

```text
180 passed
3 warnings
```

The full backend test suite completed successfully in approximately 20.54 seconds during the recorded verification.

The warnings were dependency deprecation notices, not test failures.

Tests include API, PayGuard, QR processing, BillSense, AI-provider and Payment Passport coverage.

Automated tests do not imply that every live external integration or deployment environment is configured correctly.

---

## Project Structure

The following is a high-level map of the Ayush backend components:

```text
PayPause/
¦
+-- backend/
¦   +-- app/
¦   ¦   +-- api/
¦   ¦   ¦   +-- v1/
¦   ¦   ¦       +-- payguard.py
¦   ¦   ¦       +-- billsense.py
¦   ¦   ¦       +-- payment_passport.py
¦   ¦   ¦
¦   ¦   +-- core/
¦   ¦   ¦   +-- auth.py
¦   ¦   ¦   +-- config.py
¦   ¦   ¦   +-- middleware.py
¦   ¦   ¦   +-- supabase.py
¦   ¦   ¦
¦   ¦   +-- repositories/
¦   ¦   ¦   +-- payment_passport.py
¦   ¦   ¦
¦   ¦   +-- services/
¦   ¦   ¦   +-- payguard/
¦   ¦   ¦   +-- billsense/
¦   ¦   ¦   +-- ai/
¦   ¦   ¦
¦   ¦   +-- main.py
¦   ¦
¦   +-- tests/
¦   ¦   +-- ayush/
¦   ¦
¦   +-- requirements.txt
¦
+-- supabase/
    +-- migrations/
        +-- 002_payment_passport.sql
```

---

## Current Scope and Limitations

This README describes the implementation available on `feature/ayush-core-backend`.

| Component | Branch status |
|---|---|
| PayGuard UPI analysis | Implemented |
| PayGuard URL analysis | Implemented |
| PayGuard QR analysis | Implemented |
| BillSense PDF/image analysis | Implemented |
| BillSense OCR | Implemented |
| BillSense validation and consumption analysis | Implemented |
| Optional Groq explanations | Implemented |
| Payment Passport backend | Implemented |
| Supabase migration | Implemented |
| Frontend integration | Separate workstream |
| Flagsmith experiments | Requires integration and verification |
| Payment Management | Not claimed as completed by this branch |
| Recovery Desk | Not claimed as completed by this branch |

### Known technical boundaries

- PayGuard uses local heuristics, not live fraud-intelligence or bank verification.
- BillSense focuses on Indian electricity bills.
- OCR extraction can be imperfect and should be verified.
- Groq is optional and does not determine the core risk score or bill calculations.
- Payment Passport is an assessment-history service, not a bank transaction ledger.

---

## Development Workflow

The repository uses feature branches to isolate contributors' work.

| Branch | Workstream |
|---|---|
| `feature/ayush-core-backend` | Ayush — core backend |
| `feature/bhuvan-backend` | Bhuvan — separate backend work |
| `main` | Shared integration target |

### Branch safety

- Develop on your assigned feature branch.
- Review API contracts before integration.
- Coordinate changes to shared files.
- Do not overwrite another contributor's work.
- Merge only after review and integration testing.

---

<p align="center">
  <strong>PayPause</strong><br/>
  Think Before Money Moves.<br/><br/>
  Built to make digital payment decisions more informed, explainable and cautious.
</p>

---

# Integrated Backend Modules â€” Bhuvan Contribution

The integrated backend also includes the following modules:

| Module | API prefix | Main responsibility |
|---|---|---|
| Payment management | `/api/payments` | Payment records, refund lifecycle and payment history |
| Subscription management | `/api/subscriptions` | Recurring payment tracking, renewal dates and commitments |
| Recovery desk | `/api/recovery` | Payment disputes, incident tracking and complaint assistance |
| Experiments | `/api/experiments` | Experiment scenarios, participant assignment and evaluation |
| Flagsmith integration | Internal service | Feature flags and experiment variant evaluation |

### Architecture

The integrated project retains Ayush's main FastAPI application, Supabase authentication, PayGuard, BillSense and Payment Passport. Bhuvan's modules are included as additional backend capabilities.

Bhuvan's current repository implementations are development in-memory adapters. Their data is not yet durable across application restarts and must be replaced with production persistence adapters before deployment.

### Bhuvan implementation documentation

- `docs/BHUVAN_IMPLEMENTATION_REPORT.md`
- `docs/INTEGRATION_GUIDE.md`
- `docs/FLAGS_EXPERIMENT.md`
- `docs/PAYMENT_MANAGEMENT_SPECIFICATION.md`
- `docs/RECOVERY_SPECIFICATION.md`


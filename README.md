                                                   # PayPause — Think Before Money Moves.

<p align="center">
  <strong>An intelligent financial safety and personal money-management platform for India.</strong>
  <br />
  Helping people understand payment risks, track financial commitments, analyse electricity bills and take informed action when transactions go wrong.
</p>

<p align="center">
  <a href="https://github.com/Ayushcodes-hub/PayPause"><img src="https://img.shields.io/badge/Project-PayPause-172554?style=for-the-badge" alt="PayPause" /></a>
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-Frontend-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Supabase-Database%20%26%20Auth-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase" />
</p>

<p align="center">
  <a href="#-overview">Overview</a> ·
  <a href="#-features">Features</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="#-technology-stack">Technology</a> ·
  <a href="#-getting-started">Setup</a> ·
  <a href="#-api-reference">APIs</a> ·
  <a href="#-testing">Testing</a>
</p>

---

## Table of Contents

- [Overview](#-overview)
- [The Problem](#-the-problem)
- [Features](#-features)
  - [PayGuard](#1-payguard--digital-payment-safety)
  - [BillSense](#2-billsense--electricity-bill-intelligence)
  - [Payment Passport](#3-payment-passport--payment-safety-history)
  - [Payment Management](#4-payment-management--financial-transaction-tracking)
  - [Subscription Management](#5-subscription-management--recurring-expense-intelligence)
  - [Recovery Desk](#6-recovery-desk--payment-dispute-assistance)
  - [Experiments and Flagsmith](#7-experiments--feature-management)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Repository Structure](#-repository-structure)
- [Getting Started](#-getting-started)
- [Environment Configuration](#-environment-configuration)
- [Running the Application](#-running-the-application)
- [API Reference](#-api-reference)
- [Database and Migrations](#-database-and-migrations)
- [Authentication and Security](#-authentication-and-security)
- [Testing and Quality](#-testing-and-quality)
- [Production Configuration](#-production-configuration)
- [Known Limitations and Deployment Notes](#-known-limitations-and-deployment-notes)
- [Development Workflow](#-development-workflow)
- [Contributing](#-contributing)
- [Disclaimer](#-disclaimer)

---

## 🌐 Overview

**PayPause** is a financial safety and money-management platform designed around one simple idea:

> **Think Before Money Moves.**

Digital payments have made everyday transactions faster, but they have also introduced challenges: suspicious payment identifiers, misleading QR codes, complicated electricity bills, forgotten subscriptions, incomplete transaction records and confusing payment-dispute processes.

PayPause brings several useful financial tools together in one workspace.

It combines a modern web interface with a modular backend to help users:

- Evaluate suspicious UPI IDs, payment URLs and QR codes before proceeding.
- Understand electricity bills through document extraction, validation and consumption analysis.
- Maintain a history of payment-safety assessments.
- Record and analyse payments, refunds and transaction activity.
- Track recurring subscriptions and upcoming financial commitments.
- Organise payment incidents, evidence and complaint drafts.
- Support controlled experiments and feature-flag evaluation.

PayPause is designed as a **decision-support platform**. It provides structured evidence, analysis and recommendations; it does not move money or replace banks, UPI applications or official complaint channels.

### Project objectives

| Objective | How PayPause addresses it |
|---|---|
| Safer digital payments | Evidence-based UPI, URL and QR inspection |
| Better financial visibility | Payment records, summaries and recurring-cost tracking |
| Understandable utility bills | OCR, extraction, validation and consumption analysis |
| Better dispute organisation | Incident records, evidence references and complaint drafts |
| Personalised user experience | Authenticated workspace and user-scoped records |
| Extensible architecture | Modular APIs, repository interfaces and feature flags |

---

## ⚠️ The Problem

Financial decisions often happen with incomplete information.

- A user may receive a payment request from an unfamiliar UPI ID.
- A QR code may hide a payment destination that is difficult to inspect manually.
- A payment link may contain suspicious hostname or URL characteristics.
- An electricity bill may contain unfamiliar charges or inconsistent readings.
- Recurring payments can become difficult to track across multiple services.
- A failed or unauthorised transaction can require organised evidence and follow-up.

PayPause aims to reduce this information gap by placing practical analysis and financial organisation tools in one application.

---

## 🚀 Features

### 1. PayGuard — Digital Payment Safety

PayGuard analyses payment-related inputs and identifies suspicious indicators before a user proceeds.

**Supported inputs**

- UPI IDs.
- Payment URLs.
- Combined UPI and URL assessments.
- Payment QR images.

**UPI analysis**

- Identifier structure and format validation.
- Suspicious keywords and patterns.
- Unusual separators and punctuation.
- Evidence-based risk indicators.

**URL analysis**

- URL and hostname structure.
- HTTPS versus HTTP indicators.
- Embedded credentials.
- IP-address-based destinations.
- Punycode indicators.
- URL shorteners.
- Unusual ports.
- Suspicious hostname patterns.
- Deep subdomains.

**QR analysis**

1. Accepts an image upload.
2. Validates the image.
3. Decodes the QR code locally.
4. Parses supported UPI payment URIs or URLs.
5. Passes extracted information to the relevant analysis service.
6. Returns a structured assessment.

Supported image formats include PNG, JPEG and WEBP.

**Risk assessment**

PayGuard produces a bounded heuristic score and a severity classification.

| Score | Classification |
|---:|---|
| 0–19 | Low |
| 20–39 | Moderate |
| 40–69 | High |
| 70–100 | Critical |

Assessment responses can include:

- Risk score and classification.
- Detected evidence.
- Evidence severity.
- Recommendations.
- Assessment identifier.
- Coverage information and limitations.

**Important:** A risk score is not a probability of fraud, a bank verification result or a guarantee that a payment is safe.

### 2. BillSense — Electricity Bill Intelligence

BillSense converts supported electricity-bill documents into structured information that users can inspect and understand.

**Supported documents**

- PDF documents.
- PNG images.
- JPEG images.
- WEBP images.

**Document-processing pipeline**

```text
             ELECTRICITY BILL
                     |
                     v
             DOCUMENT VALIDATION
                     |
                     v
              DOCUMENT DETECTION
                     |
              +------+------+
              |             |
              v             v
         NATIVE PDF     SCANNED / IMAGE
         EXTRACTION       DOCUMENT
              |             |
              |             v
              |          RAPIDOCR
              |             |
              +------+------+
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
              OPTIONAL GROQ AI
                     |
                     v
              STRUCTURED RESULT
```

**Extracted information may include**

- Electricity provider.
- Consumer name and consumer number.
- Bill number.
- Billing period.
- Bill date and due date.
- Previous and current meter readings.
- Units consumed.
- Energy charges.
- Fixed charges.
- Taxes and late fees.
- Total payable amount.

**Validation and analysis**

- Required-field checks.
- Numeric and negative-value validation.
- Meter-reading consistency.
- Charge arithmetic consistency.
- OCR confidence information where available.
- Billing-period duration.
- Average daily consumption.
- Consumption observations and warnings.

**Provider coverage**

The parser includes patterns for Indian electricity utilities such as BESCOM, MESCOM, HESCOM, GESCOM, CESC, TANGEDCO, MSEDCL and KSEB.

**Optional AI explanations**

Groq can provide an additional explanation layer. It does not replace deterministic extraction, validation or calculations.

Document safeguards currently include a 10 MB upload limit, a 10-page PDF limit and a 20-megapixel image-dimension limit. Password-protected PDFs are unsupported.

### 3. Payment Passport — Payment Safety History

Payment Passport maintains structured records of PayGuard assessments for authenticated users.

Capabilities include:

- Assessment persistence.
- User-specific assessment history.
- Paginated retrieval.
- Individual assessment lookup.
- Assessment deletion.
- Supabase PostgreSQL integration.
- User-scoped database access.

The module is intended as a history of safety assessments, not as a bank account or transaction ledger.

### 4. Payment Management — Financial Transaction Tracking

The Payment Management module provides APIs for organising payment records and tracking refund activity.

Capabilities include:

- Creating payment records.
- Retrieving payment history.
- Filtering by transaction reference, date, amount, category, merchant, provider and status.
- Paginated payment retrieval.
- Individual payment lookup.
- Updating permitted payment and refund fields.
- Refund activity tracking.
- Payment summaries.
- Duplicate-payment checks.

The module is designed to help users maintain visibility over recorded payments. It does not initiate bank transfers or execute refunds.

### 5. Subscription Management — Recurring Expense Intelligence

Subscription Management helps users organise recurring financial commitments.

Capabilities include:

- Creating subscription records.
- Listing and filtering subscriptions.
- Retrieving individual subscriptions.
- Updating subscription details.
- Pausing and resuming subscriptions.
- Deleting subscription records.
- Normalising recurring costs into monthly equivalents.
- Summarising recurring commitments.
- Identifying upcoming renewal information.

The goal is to make recurring financial obligations easier to understand and monitor.

### 6. Recovery Desk — Payment Dispute Assistance

Recovery Desk provides a structured workflow for recording and following up on payment incidents.

Capabilities include:

- Reporting payment incidents and disputes.
- Listing incidents with filters and pagination.
- Retrieving incident details.
- Updating incident status.
- Maintaining incident timelines.
- Managing evidence references.
- Removing individual evidence items.
- Generating structured complaint drafts.
- Organising follow-up information.

Complaint-draft generation is intended to help users prepare information for appropriate official channels. It does not submit complaints automatically or guarantee a recovery outcome.

### 7. Experiments — Feature Management

The experimentation module supports controlled scenario assignment and evaluation.

Capabilities include:

- Retrieving public experiment scenarios.
- Assigning a stable experiment variant.
- Submitting scenario attempts.
- Recording experiment events.
- Evaluating experiment results.
- Restricting aggregate experiment telemetry to configured administrators.

**Flagsmith integration** provides server-side feature-flag and variant evaluation. A deterministic fallback is available when the Flagsmith environment key is not configured.

---

## 🏗️ Architecture

PayPause uses a modular full-stack architecture.

```text
                    ┌───────────────────────────┐
                    │        USER               │
                    └─────────────┬─────────────┘
                                  |
                                  v
                    ┌───────────────────────────┐
                    │     REACT WEB APP         │
                    │    TypeScript + Vite      │
                    └─────────────┬─────────────┘
                                  |
                           HTTPS / REST
                                  |
                                  v
                    ┌───────────────────────────┐
                    │       FASTAPI             │
                    │    APPLICATION LAYER      │
                    └─────────────┬─────────────┘
                                  |
          ┌───────────────┬───────┼────────┬────────────────┐
          |               |       |        |                |
          v               v       v        v                v
     PAYGUARD         BILLSENSE  PAYMENT  SUBSCRIPTION   RECOVERY
     PAYMENT          BILL       MANAGE-  MANAGEMENT     DESK
     SAFETY           ANALYSIS   MENT
          |               |       |        |                |
          └───────────────┴───────┼────────┴────────────────┘
                                  |
                                  v
                    ┌───────────────────────────┐
                    │   SERVICE / REPOSITORY    │
                    │       LAYER               │
                    └─────────────┬─────────────┘
                                  |
                    ┌─────────────┴─────────────┐
                    |                           |
                    v                           v
          ┌──────────────────┐       ┌────────────────────┐
          │ DEVELOPMENT      │       │ PRODUCTION         │
          │ IN-MEMORY ADAPTERS│       │ SUPABASE ADAPTERS  │
          └──────────────────┘       └─────────┬──────────┘
                                               |
                                               v
                                  ┌────────────────────────┐
                                  │ SUPABASE               │
                                  │ Auth + PostgreSQL      │
                                  └────────────────────────┘

                 OPTIONAL / SUPPORTING SERVICES
                 ├── Groq AI
                 └── Flagsmith
```

### Architectural layers

| Layer | Responsibility |
|---|---|
| Frontend | User interface, navigation, forms and API integration |
| API | HTTP routes, request handling and response contracts |
| Services | Business rules and application workflows |
| Repository interfaces | Contracts between services and persistence |
| Development repositories | In-memory implementations for development and testing |
| Production repositories | Supabase-backed persistence adapters |
| Authentication | Supabase identity verification and user context |
| Database | Persistent user and application records |
| Integrations | Optional AI and feature-flag services |

### Design principles

- Separation of API, service and persistence responsibilities.
- Modular backend domains.
- Explicit repository interfaces.
- Structured validation and error handling.
- User-scoped data access.
- Deterministic core analysis wherever practical.
- Optional external AI rather than mandatory AI dependence.
- Separate development and production persistence implementations.

---

## 🧰 Technology Stack

### Frontend

| Technology | Purpose |
|---|---|
| React 19 | Component-based user interface |
| TypeScript | Static typing |
| Vite | Development server and production bundling |
| React Router | Client-side routing |
| Supabase JavaScript SDK | Authentication and session management |
| TanStack React Query | Server-state and data-fetching support |
| Zustand | Client-side state management |
| React Hook Form | Form management |
| Zod | Schema validation |
| Radix UI | Accessible interface primitives |
| Lucide React | Icons |
| Motion | UI animation |
| GSAP | Animation tooling |
| Three.js | 3D graphics |
| React Three Fiber / Drei | React-based 3D integration |
| ECharts | Data visualisation |
| PixiJS | 2D rendering |
| Oxlint | Frontend linting |
| Vitest and Testing Library | Frontend testing dependencies |

### Backend

| Technology | Purpose |
|---|---|
| Python | Backend programming language |
| FastAPI | REST API framework |
| Uvicorn | ASGI server |
| Pydantic | Data validation and settings |
| HTTPX | HTTP client |
| python-dotenv | Environment configuration |
| Pytest | Backend testing |
| pytest-asyncio | Asynchronous tests |

### AI and document processing

| Technology | Purpose |
|---|---|
| Groq | Optional AI-powered explanations |
| RapidOCR | Optical character recognition |
| ONNX Runtime | OCR inference runtime |
| PyMuPDF | PDF processing and text extraction |
| Pillow | Image processing |
| ZXing-C++ | QR code decoding |

### Database and integrations

| Technology | Purpose |
|---|---|
| Supabase Auth | User authentication |
| Supabase PostgreSQL | Persistent relational database |
| Supabase Python SDK | Backend database integration |
| Supabase JavaScript SDK | Frontend authentication integration |
| Flagsmith | Feature flags and experimentation |

### Development and quality

| Technology | Purpose |
|---|---|
| Git | Version control |
| GitHub | Source hosting and pull requests |
| npm | Frontend dependency management |
| Python virtual environments | Backend dependency isolation |
| TypeScript compiler | Frontend type checking |
| Vite build | Frontend production build |
| Oxlint | Static linting |

---

## 📁 Repository Structure

```text
PayPause/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── billsense.py
│   │   │   │   ├── payguard.py
│   │   │   │   └── payment_passport.py
│   │   │   ├── experiments.py
│   │   │   ├── payments.py
│   │   │   ├── recovery.py
│   │   │   └── subscriptions.py
│   │   │
│   │   ├── core/
│   │   │   ├── auth.py
│   │   │   ├── bhuvan_auth_bridge.py
│   │   │   ├── config.py
│   │   │   ├── dependencies.py
│   │   │   ├── exceptions.py
│   │   │   ├── logging.py
│   │   │   ├── middleware.py
│   │   │   ├── security.py
│   │   │   └── supabase.py
│   │   │
│   │   ├── integrations/
│   │   │   └── flagsmith/
│   │   │
│   │   ├── repositories/
│   │   │   ├── development/
│   │   │   ├── interfaces/
│   │   │   └── production/
│   │   │
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   ├── billsense/
│   │   │   ├── experiments/
│   │   │   ├── payguard/
│   │   │   ├── payments/
│   │   │   ├── recovery/
│   │   │   └── subscriptions/
│   │   │
│   │   ├── dev_main.py
│   │   └── main.py
│   │
│   ├── tests/
│   │   ├── ayush/
│   │   └── bhuvan/
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── supabase.ts
│   │   ├── App.tsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.tsx
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.ts
│
├── docs/
│   ├── BHUVAN_IMPLEMENTATION_REPORT.md
│   ├── FLAGS_EXPERIMENT.md
│   ├── INTEGRATION_GUIDE.md
│   ├── PAYMENT_MANAGEMENT_SPECIFICATION.md
│   └── RECOVERY_SPECIFICATION.md
│
├── supabase/
│   └── migrations/
│       ├── 001_initial_profiles.sql
│       ├── 002_payment_passport.sql
│       ├── 003_production_persistence.sql
│       └── 004_production_persistence_corrections.sql
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

## ⚙️ Getting Started

### Prerequisites

Install the following tools:

- Git
- Python 3.11 or a compatible newer version
- Node.js compatible with the Vite version in the frontend lockfile
- npm
- A Supabase project
- Optional: Groq API key
- Optional: Flagsmith environment key

### 1. Clone the repository

```powershell
git clone https://github.com/Ayushcodes-hub/PayPause.git
cd PayPause
```

### 2. Create and activate a Python virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks environment activation, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Install backend dependencies

From the repository root:

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

### 4. Configure backend environment variables

Copy the example environment file:

```powershell
Copy-Item .env.example backend\.env
```

Edit `backend\.env` and provide the appropriate credentials.

### 5. Install frontend dependencies

```powershell
cd frontend
npm install
```

### 6. Configure frontend environment variables

Create `frontend\.env.local`:

```dotenv
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_SUPABASE_PUBLIC_ANON_KEY
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Use the public/anonymous client key intended for browser applications. Never place the Supabase service-role key in frontend environment variables.

---

## 🔐 Environment Configuration

### Backend — `backend/.env`

The root `.env.example` provides the shared configuration template.

| Variable | Purpose |
|---|---|
| `APP_NAME` | Application name |
| `APP_VERSION` | API version metadata |
| `ENVIRONMENT` | `development`, `testing` or `production` |
| `DEBUG` | Debug mode |
| `API_V1_PREFIX` | Versioned API prefix |
| `HOST` | Backend host |
| `PORT` | Backend port |
| `CORS_ORIGINS` | Permitted frontend origins |
| `LOG_LEVEL` | Application logging level |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase public/anonymous key |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend-only administrative key |
| `AI_PROVIDER` | Optional AI provider |
| `AI_API_KEY` | Optional AI provider credential |
| `AI_MODEL` | Configured AI model |
| `AI_REQUEST_TIMEOUT_SECONDS` | AI request timeout |
| `APP_ENV` | Additional module environment setting |
| `FLAGSMITH_ENVIRONMENT_KEY` | Flagsmith server-side environment key |
| `FLAGSMITH_API_URL` | Flagsmith API endpoint |
| `FLAGSMITH_REQUEST_TIMEOUT_SECONDS` | Flagsmith request timeout |
| `DEV_DEFAULT_USER_ID` | Development fallback identity |
| `DEV_DEFAULT_USER_EMAIL` | Development fallback email |

### Frontend — `frontend/.env.local`

| Variable | Purpose |
|---|---|
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Browser-safe Supabase public key |
| `VITE_API_BASE_URL` | Backend API base URL |

Environment files containing secrets must remain outside version control.

---

## ▶️ Running the Application

Run the frontend and backend in separate terminals.

### Terminal 1 — Backend

From the repository root:

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### Terminal 2 — Frontend

From the repository root:

```powershell
cd frontend
npm run dev
```

Vite normally serves the application at:

```text
http://localhost:5173
```

### Production frontend build

```powershell
cd frontend
npm run build
```

### Preview the production frontend build

```powershell
npm run preview
```

### Backend health endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | Application information |
| `GET /health` | Health check |
| `GET /health/live` | Liveness check |
| `GET /health/ready` | Readiness check |
| `GET /api/v1/health` | Versioned API health |

---

## 🔌 API Reference

The backend exposes domain-specific REST APIs.

Interactive documentation is available at:

**`http://127.0.0.1:8000/docs`**

### PayGuard, BillSense and Payment Passport

These routes use the versioned prefix `/api/v1`.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/payguard/assess` | Assess UPI and/or payment URL |
| `POST` | `/api/v1/payguard/assess-qr` | Assess a QR image |
| `POST` | `/api/v1/billsense/analyze` | Analyse an electricity bill |
| `GET` | `/api/v1/payment-passport/assessments` | List assessment history |
| `GET` | `/api/v1/payment-passport/assessments/{assessment_id}` | Retrieve an assessment |
| `DELETE` | `/api/v1/payment-passport/assessments/{assessment_id}` | Delete an assessment |
| `GET` | `/api/v1/auth/me` | Retrieve authenticated user information |

### Payment Management

Prefix: `/api/payments`

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/payments` | Create a payment record |
| `GET` | `/api/payments` | List and filter payments |
| `GET` | `/api/payments/refunds` | List refund activity |
| `GET` | `/api/payments/summary` | Payment and refund summary |
| `GET` | `/api/payments/{payment_id}` | Retrieve a payment |
| `PATCH` | `/api/payments/{payment_id}` | Update payment information |

### Subscription Management

Prefix: `/api/subscriptions`

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/subscriptions` | Create a subscription |
| `GET` | `/api/subscriptions` | List subscriptions |
| `GET` | `/api/subscriptions/summary` | Recurring-expense summary |
| `GET` | `/api/subscriptions/{subscription_id}` | Retrieve a subscription |
| `PATCH` | `/api/subscriptions/{subscription_id}` | Update a subscription |
| `POST` | `/api/subscriptions/{subscription_id}/pause` | Pause a subscription |
| `POST` | `/api/subscriptions/{subscription_id}/resume` | Resume a subscription |
| `DELETE` | `/api/subscriptions/{subscription_id}` | Delete a subscription |

### Recovery Desk

Prefix: `/api/recovery`

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/recovery/incidents` | Create a payment incident |
| `GET` | `/api/recovery/incidents` | List incidents |
| `GET` | `/api/recovery/incidents/{incident_id}` | Retrieve incident details |
| `PATCH` | `/api/recovery/incidents/{incident_id}` | Update an incident |
| `POST` | `/api/recovery/incidents/{incident_id}/complaint-draft` | Generate a complaint draft |
| `DELETE` | `/api/recovery/incidents/{incident_id}/evidence/{evidence_id}` | Remove an evidence item |

### Experiments

Prefix: `/api/experiments`

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/experiments/scenarios` | Retrieve public scenarios |
| `POST` | `/api/experiments/assign` | Assign an experiment variant |
| `POST` | `/api/experiments/submit` | Submit an experiment attempt |
| `GET` | `/api/experiments/status` | Retrieve administrator-only experiment telemetry |

Protected endpoints require a valid authenticated Supabase user context. Refer to the generated OpenAPI documentation for request schemas, response schemas, query parameters and status codes.

---

## 🗄️ Database and Migrations

PayPause uses Supabase PostgreSQL for persistent application data.

Database migrations are maintained in:

```text
supabase/migrations/
```

| Migration | Purpose |
|---|---|
| `001_initial_profiles.sql` | Initial profile and user-related schema |
| `002_payment_passport.sql` | Payment Passport persistence |
| `003_production_persistence.sql` | Production persistence schema |
| `004_production_persistence_corrections.sql` | Ownership, constraints, indexes and atomic persistence corrections |

### Applying migrations

Before applying migrations to a live project:

1. Confirm the target Supabase project.
2. Review the migration SQL.
3. Back up important existing data.
4. Validate the migrations against a staging database.
5. Apply migrations in numerical order.
6. Verify tables, indexes, constraints, policies and database functions.
7. Run authenticated integration tests.

Do not assume that a migration file in GitHub has already been applied to the live Supabase database.

### Persistence strategy

The backend separates repository interfaces from their implementations.

- Development and testing use in-memory repositories where configured.
- Production configuration selects Supabase-backed repository implementations.
- Production mode requires valid Supabase configuration.
- User ownership is intended to be enforced through authenticated identity and database scoping.

Production persistence must be tested against the actual Supabase schema before deployment.

---

## 🔒 Authentication and Security

PayPause integrates Supabase Auth for user authentication.

The frontend obtains the current session and sends the access token with API requests:

```http
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
```

The backend validates authenticated identity and uses that identity to scope protected operations.

### Security practices

- Keep service-role credentials on the backend only.
- Never commit `.env` or `.env.local` files.
- Use the browser-safe Supabase public key in the frontend.
- Validate incoming request data.
- Apply user ownership checks to personal records.
- Restrict administrator-only experiment telemetry.
- Keep development fallback identities out of production.
- Configure CORS for trusted frontend origins.
- Use HTTPS in deployed environments.
- Review database Row Level Security policies.
- Avoid logging secrets, access tokens or sensitive payment information.

### Payment and document safety

- PayGuard URL inspection is local and heuristic-based; it does not visit submitted URLs.
- QR decoding is performed locally by the backend processing pipeline.
- BillSense validates uploaded documents before processing.
- AI explanations are optional and separate from deterministic calculations.

Security must be verified in the deployed environment; configuration alone is not proof of production security.

---

## 🧪 Testing and Quality

PayPause includes backend tests across the project modules.

### Run the complete backend test suite

From the repository root:

```powershell
python -m pytest backend\tests -q
```

### Run a specific test module

```powershell
python -m pytest backend\tests\ayush -q
```

```powershell
python -m pytest backend\tests\bhuvan -q
```

### Backend syntax compilation

```powershell
python -m compileall -q backend\app
```

### Frontend lint

```powershell
cd frontend
npm run lint
```

### Frontend production build

```powershell
npm run build
```

### Recorded integration verification

The integrated code was previously verified with:

| Check | Recorded result |
|---|---|
| Backend test suite | 248 passed, 3 warnings |
| Backend compile check | Successful |
| Frontend TypeScript and production build | Successful |
| Frontend lint | 0 errors, 5 warnings |
| Production service and dependency imports | Successful |

These are recorded development checks, not a claim that the live production environment, database migrations or external integrations have been fully deployed and verified.

---

## 🚀 Production Configuration

The backend supports separate development and production repository configurations.

For production:

1. Set `ENVIRONMENT=production`.
2. Configure the Supabase project URL.
3. Configure the backend Supabase credentials securely.
4. Validate and apply the database migrations.
5. Verify authentication and ownership enforcement.
6. Configure the frontend's production API URL.
7. Configure trusted CORS origins.
8. Configure optional Groq and Flagsmith integrations if required.
9. Run backend and frontend tests against the deployment configuration.
10. Verify health and readiness endpoints.

### Production readiness checklist

- [ ] Production Supabase project selected.
- [ ] Database migrations reviewed and applied.
- [ ] Existing records and ownership constraints validated.
- [ ] Row Level Security policies reviewed.
- [ ] Production repository adapters tested against live schema.
- [ ] Supabase authentication verified end to end.
- [ ] Frontend environment variables configured.
- [ ] CORS restricted to trusted origins.
- [ ] Service-role key stored securely on the backend.
- [ ] Groq integration tested if enabled.
- [ ] Flagsmith integration tested if enabled.
- [ ] Health and readiness endpoints verified.
- [ ] Production build deployed.
- [ ] Error handling and logging reviewed.

---

## ⚖️ Known Limitations and Deployment Notes

PayPause is an evolving platform. The following boundaries are important:

- PayGuard uses heuristic analysis; it does not provide live bank verification, guaranteed fraud detection or a guarantee of recipient legitimacy.
- URL inspection does not currently perform live DNS, redirect or external reputation checks.
- OCR output may contain extraction errors and should be checked against the original bill.
- BillSense's provider patterns focus on selected Indian electricity utilities.
- Groq is optional and does not replace deterministic analysis.
- Payment records and refund tracking do not execute bank transactions or refunds.
- Recovery Desk prepares and organises information; it does not automatically file complaints or recover funds.
- Development in-memory data is not durable across process restarts.
- Production Supabase adapters require validation against the actual deployed database schema.
- Database migration files must be applied and verified separately from Git integration.
- A successful local test suite does not guarantee that all external services are configured correctly.

---

## 🌱 Development Workflow

The repository uses feature branches to isolate work and integrate contributions through pull requests.

### Branch conventions

Use descriptive feature branches, for example:

```text
feature/<module-or-contributor>
fix/<issue-description>
docs/<documentation-change>
```

### Recommended workflow

```powershell
git switch main
git pull --ff-only origin main

git switch -c feature/your-change

# Make and test your changes.

git status
git diff --check
git add <specific-files>
git commit -m "feat: describe your change"
git push -u origin feature/your-change
```

Open a pull request targeting `main` and review the changes before merging.

### Contribution guidelines

- Keep modules separated by responsibility.
- Preserve existing API contracts unless a change is coordinated.
- Use repository interfaces rather than coupling services directly to database implementations.
- Add tests for new functionality and bug fixes.
- Never commit credentials or local environment files.
- Validate database changes before deployment.
- Avoid unrelated changes in shared files.
- Document new environment variables and API endpoints.

---

## 📚 Project Documentation

Additional technical documentation is available in `docs/`:

| Document | Description |
|---|---|
| `BHUVAN_IMPLEMENTATION_REPORT.md` | Backend implementation report |
| `INTEGRATION_GUIDE.md` | Integration guidance |
| `FLAGS_EXPERIMENT.md` | Flagsmith and experiment documentation |
| `PAYMENT_MANAGEMENT_SPECIFICATION.md` | Payment management specification |
| `RECOVERY_SPECIFICATION.md` | Recovery workflow specification |

For endpoint-level details, use the running FastAPI Swagger UI at `/docs`.

---

## ⚠️ Disclaimer

PayPause is an informational and decision-support application.

It does not:

- Guarantee that a payment recipient is legitimate.
- Guarantee detection of every fraudulent payment request.
- Initiate, authorise, reverse or settle financial transactions.
- Execute refunds or recover lost funds.
- Replace banks, payment service providers, electricity utilities, legal professionals or official complaint mechanisms.

Users should independently verify payment recipients, review bill information and contact the appropriate official institution when necessary.

---

## 👥 Project

**Repository:** [Ayushcodes-hub/PayPause](https://github.com/Ayushcodes-hub/PayPause)

**Primary branch:** `main`

<p align="center">
  <strong>PayPause</strong>
  <br />
  <em>Think Before Money Moves.</em>
  <br /><br />
  Built to make digital payment decisions safer, financial commitments clearer and recovery workflows more organised.
</p>

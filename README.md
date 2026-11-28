 
<h1 align="center">💸 PayPause</h1>

<h3 align="center">Think Before Money Moves.</h3>

<p align="center">
  <strong>An intelligent financial safety and personal money-management platform for India.</strong>
  <br />
  Helping people understand payment risks, track financial commitments, analyse electricity bills, and take informed action when transactions go wrong.
</p>

<p align="center">
  <a href="https://github.com/Ayushcodes-hub/PayPause">
    <img src="https://img.shields.io/badge/Project-PayPause-172554?style=for-the-badge" alt="PayPause" />
  </a>
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-Frontend-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Supabase-Database%20%26%20Auth-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Architecture-Modular-blue?style=flat-square" alt="Modular Architecture" />
  <img src="https://img.shields.io/badge/API-REST-orange?style=flat-square" alt="REST API" />
  <img src="https://img.shields.io/badge/Testing-Pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white" alt="Pytest" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/License-See%20Repository-lightgrey?style=flat-square" alt="License" />
</p>

<p align="center">
  <a href="#-overview">Overview</a> ·
  <a href="#-why-paypause">Why PayPause</a> ·
  <a href="#-features">Features</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="#-technology-stack">Technology</a> ·
  <a href="#-installation--setup">Setup</a> ·
  <a href="#-api-reference">APIs</a> ·
  <a href="#-testing--quality-assurance">Testing</a> ·
  <a href="#-roadmap">Roadmap</a>
</p>

---

# 📌 Table of Contents

1. [Overview](#-overview)
2. [Why PayPause](#-why-paypause)
3. [Project Vision and Objectives](#-project-vision-and-objectives)
4. [Features and Modules](#-features-and-modules)
   - [PayGuard](#1-payguard--digital-payment-safety)
   - [BillSense](#2-billsense--electricity-bill-intelligence)
   - [Payment Passport](#3-payment-passport--payment-safety-history)
   - [Payment Management](#4-payment-management--financial-transaction-tracking)
   - [Subscription Management](#5-subscription-management--recurring-expense-intelligence)
   - [Recovery Desk](#6-recovery-desk--payment-dispute-assistance)
   - [Experiments and Feature Management](#7-experiments--feature-management)
5. [How PayPause Works](#-how-paypause-works)
6. [System Architecture](#-system-architecture)
7. [Technology Stack](#-technology-stack)
8. [Repository Structure](#-repository-structure)
9. [Installation and Setup](#-installation--setup)
10. [Environment Configuration](#-environment-configuration)
11. [Running the Application](#-running-the-application)
12. [API Reference](#-api-reference)
13. [Database and Persistence](#-database-and-persistence)
14. [Authentication and Security](#-authentication-and-security)
15. [Testing and Quality Assurance](#-testing-and-quality-assurance)
16. [Production Configuration](#-production-configuration)
17. [Known Limitations](#-known-limitations)
18. [Future Roadmap](#-future-roadmap)
19. [Development Workflow](#-development-workflow)
20. [Contributing](#-contributing)
21. [Project Documentation](#-project-documentation)
22. [Disclaimer](#-disclaimer)
23. [Project Information](#-project-information)

---

# 🌐 Overview

**PayPause** is a modular financial safety and personal money-management platform designed to help individuals make more informed decisions in an increasingly digital financial environment.

India's digital payment ecosystem has transformed how people pay, receive money, manage subscriptions and interact with financial services. However, convenience also brings new challenges: suspicious payment identifiers, deceptive QR codes, misleading payment URLs, complicated electricity bills, forgotten recurring expenses and difficult payment-dispute processes.

PayPause brings multiple practical tools together in a single application.

Instead of treating financial safety, payment tracking, bill analysis and dispute assistance as unrelated problems, PayPause approaches them as interconnected parts of everyday financial management.

The platform combines:

- A modern React and TypeScript frontend.
- A Python and FastAPI backend.
- Modular financial-analysis services.
- Supabase authentication and PostgreSQL persistence.
- OCR-based document processing.
- Optional AI-powered explanations.
- Feature flags and experimentation support.

The central philosophy is simple:

> **Pause. Understand. Verify. Then act.**

PayPause is designed as a decision-support platform. It helps users organise information, identify potential warning signs and understand financial commitments. It does not directly initiate financial transactions or replace banks, UPI applications, electricity providers or official dispute-resolution mechanisms.

---

# 💡 Why PayPause?

Financial decisions frequently happen with incomplete information.

Consider some everyday situations:

| Situation | Common difficulty | PayPause module |
|---|---|---|
| An unfamiliar UPI ID requests payment | Recipient information may be difficult to assess | PayGuard |
| Someone shares a payment QR code | The encoded payment destination may not be obvious | PayGuard |
| A suspicious payment link arrives | URL structure and destination may be misleading | PayGuard |
| An electricity bill suddenly increases | Charges and consumption may be difficult to understand | BillSense |
| Multiple subscriptions renew every month | Recurring expenses can go unnoticed | Subscription Management |
| A payment fails or becomes disputed | Information and evidence can become scattered | Recovery Desk |
| A user wants to review earlier risk assessments | Previous checks may not be organised | Payment Passport |
| Payment activity needs better organisation | Transaction records can be difficult to monitor | Payment Management |

PayPause aims to reduce these information gaps through a unified workspace.

## The core idea

<details>
<summary><strong>Explore the PayPause decision workflow</strong></summary>

```text
                A FINANCIAL DECISION
                         |
                         v
                IDENTIFY THE PROBLEM
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
     PAYMENT RISK     BILL ANALYSIS   MONEY TRACKING
          |              |              |
          v              v              v
       PAYGUARD        BILLSENSE      FINANCIAL
                                      MANAGEMENT
          |              |              |
          +--------------+--------------+
                         |
                         v
                 STRUCTURED INSIGHTS
                         |
                         v
                 INFORMED DECISION
                         |
              +----------+----------+
              |                     |
              v                     v
        PROCEED WITH CARE      INVESTIGATE /
                               TAKE ACTION
```

</details>

---

# 🎯 Project Vision and Objectives

PayPause is built around six objectives.

| Objective | Implementation approach |
|---|---|
| Digital payment safety | UPI, URL and QR inspection |
| Financial visibility | Payment records and recurring-cost tracking |
| Understandable utility bills | OCR, extraction and consumption analysis |
| Better dispute organisation | Incident records and complaint drafts |
| Personalised financial workspace | Authentication and user-scoped records |
| Extensible software architecture | Modular APIs, services and repository interfaces |

## Engineering objectives

The project also demonstrates several software-engineering principles:

- Separation of concerns.
- Modular application design.
- REST API development.
- Typed frontend development.
- Authentication and access control.
- Repository abstraction.
- Database-backed persistence.
- Automated testing.
- External service integration.
- Development and production configuration separation.

---

# 🚀 Features and Modules

PayPause is organised into specialised modules. Each module addresses a different part of the user's financial workflow.

## 1. PayGuard — Digital Payment Safety

**PayGuard helps users inspect payment-related information and identify suspicious indicators before proceeding.**

Digital payment scams may involve misleading UPI identifiers, QR codes, payment links and deceptive destinations.

PayGuard analyses the structure of supported inputs and returns a structured risk assessment.

### Supported inputs

- UPI IDs.
- Payment URLs.
- Combined UPI and URL assessments.
- Payment QR images.

### UPI analysis

The UPI analysis service examines characteristics such as:

- Identifier structure and format.
- Suspicious keywords and patterns.
- Unusual separators and punctuation.
- Potentially misleading identifier characteristics.
- Other configured risk indicators.

### URL analysis

The URL analysis engine evaluates characteristics such as:

- URL and hostname structure.
- HTTPS versus HTTP indicators.
- Embedded credentials.
- IP-address-based destinations.
- Punycode indicators.
- URL shorteners.
- Unusual ports.
- Suspicious hostname patterns.
- Deep subdomains.
- Other structural anomalies.

### QR code analysis

PayGuard supports a processing pipeline for payment QR images.

```text
             QR IMAGE UPLOAD
                    |
                    v
             IMAGE VALIDATION
                    |
                    v
              QR DECODING
                    |
                    v
           EXTRACTED QR CONTENT
                    |
          +---------+---------+
          |                   |
          v                   v
       UPI URI             PAYMENT URL
          |                   |
          v                   v
      UPI PARSER          URL ANALYSER
          |                   |
          +---------+---------+
                    |
                    v
             RISK ASSESSMENT
                    |
                    v
             STRUCTURED RESULT
```

Supported image formats include PNG, JPEG and WEBP.

### Risk assessment

PayGuard produces a bounded heuristic risk score and a severity classification.

| Score | Classification |
|---:|---|
| 0–19 | Low |
| 20–39 | Moderate |
| 40–69 | High |
| 70–100 | Critical |

An assessment may contain:

- Risk score.
- Severity classification.
- Detected indicators.
- Evidence descriptions.
- Evidence severity.
- Recommendations.
- Assessment identifier.
- Coverage information and limitations.

**Important:** A heuristic risk score is not a probability of fraud. It is not a bank verification result and cannot guarantee that a recipient or payment destination is legitimate.

---

## 2. BillSense — Electricity Bill Intelligence

**BillSense transforms supported electricity-bill documents into structured information that users can inspect and understand.**

Electricity bills may contain multiple charges, meter readings, billing periods, taxes and other details. These can be difficult to interpret without manually examining the entire document.

BillSense combines document processing, OCR, field extraction, validation and consumption analysis.

### Supported documents

- PDF documents.
- PNG images.
- JPEG images.
- WEBP images.

### Document-processing architecture

```text
                  ELECTRICITY BILL
                          |
                          v
                  DOCUMENT VALIDATION
                          |
                          v
                   DOCUMENT DETECTION
                          |
                 +--------+--------+
                 |                 |
                 v                 v
            NATIVE PDF        SCANNED / IMAGE
            EXTRACTION          DOCUMENT
                 |                 |
                 |                 v
                 |              RAPIDOCR
                 |                 |
                 +--------+--------+
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
                  STRUCTURED RESPONSE
```

### Extracted information

Depending on document quality and available fields, BillSense may extract:

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
- Taxes and late fees.
- Total payable amount.

### Validation and analysis

BillSense performs structured checks such as:

- Required-field validation.
- Numeric-value validation.
- Negative-value checks.
- Meter-reading consistency.
- Charge arithmetic consistency.
- OCR confidence analysis where available.
- Billing-period duration analysis.
- Average daily consumption calculation.
- Consumption observations and warnings.

### Provider coverage

The parser includes patterns for selected Indian electricity utilities, including:

- BESCOM.
- MESCOM.
- HESCOM.
- GESCOM.
- CESC.
- TANGEDCO.
- MSEDCL.
- KSEB.

Provider recognition and field extraction depend on document format and quality. This list does not imply that every bill layout from every provider is supported.

### Optional AI explanations

Groq integration provides an optional AI explanation layer.

The intended division of responsibilities is:

| Component | Responsibility |
|---|---|
| OCR | Extract text from supported documents |
| Parser | Identify relevant bill fields |
| Validator | Check extracted information |
| Consumption analyser | Calculate and interpret consumption |
| Groq | Optional natural-language explanations |

AI is supplementary. It does not replace deterministic calculations or document validation.

### Document safeguards

Current processing safeguards include:

- Maximum upload size: 10 MB.
- Maximum PDF length: 10 pages.
- Maximum image dimensions: 20 megapixels.
- Password-protected PDFs are unsupported.

---

## 3. Payment Passport — Payment Safety History

Payment Passport maintains structured records of PayGuard assessments for authenticated users.

Instead of treating every risk assessment as a one-time operation, Payment Passport provides a way to revisit previous assessments.

### Capabilities

- Save assessment records.
- Retrieve user-specific assessment history.
- Paginate assessment results.
- Retrieve an individual assessment.
- Delete an assessment.
- Persist records through Supabase PostgreSQL.
- Scope records to the authenticated user.

### Why it matters

A payment-safety assessment is more useful when users can review it later.

Payment Passport provides historical context and helps users organise previous checks.

It is a record of safety assessments, not a bank account, payment wallet or complete banking transaction ledger.

---

## 4. Payment Management — Financial Transaction Tracking

Payment Management provides APIs for organising payment records and monitoring refund activity.

### Capabilities

- Create payment records.
- Retrieve payment history.
- Filter payments by supported fields.
- Paginate payment retrieval.
- Retrieve individual payment records.
- Update permitted payment information.
- Track refund activity.
- Generate payment summaries.
- Perform duplicate-payment checks.

### Supported filtering concepts

Depending on the endpoint and request parameters, filtering can include:

- Transaction reference.
- Date.
- Amount.
- Category.
- Merchant.
- Payment provider.
- Payment status.

### Intended benefits

- Better visibility into recorded financial activity.
- Easier organisation of payment information.
- Improved refund tracking.
- Identification of potentially duplicated records.
- A foundation for more advanced personal-finance analytics.

The module records and manages payment information. It does not initiate bank transfers, debit accounts or execute refunds.

---

## 5. Subscription Management — Recurring Expense Intelligence

Recurring financial commitments can become difficult to monitor when users subscribe to multiple services.

Subscription Management provides structured records and APIs for organising recurring expenses.

### Capabilities

- Create subscription records.
- List subscriptions.
- Retrieve individual subscriptions.
- Filter subscription information.
- Update subscription details.
- Pause subscriptions.
- Resume subscriptions.
- Delete subscription records.
- Calculate monthly-equivalent costs.
- Generate recurring-expense summaries.
- Monitor renewal information.

### Monthly-equivalent calculation

Different subscriptions may use different billing frequencies.

PayPause normalises recurring costs into monthly equivalents to make comparisons easier.

Examples of the intended calculation:

| Billing frequency | Monthly equivalent |
|---|---|
| Weekly | Amount × 52 ÷ 12 |
| Monthly | Amount |
| Quarterly | Amount ÷ 3 |
| Yearly | Amount ÷ 12 |

This helps users compare recurring commitments on a common monthly basis.

---

## 6. Recovery Desk — Payment Dispute Assistance

Recovery Desk provides a structured workflow for recording payment incidents and organising follow-up information.

When a payment becomes disputed or appears unauthorised, users may need to organise transaction information, evidence and complaint details.

Recovery Desk is designed to make that process more structured.

### Capabilities

- Report payment incidents.
- Retrieve incident records.
- List incidents with supported filters.
- Paginate incident history.
- Update incident information.
- Maintain incident status and timelines.
- Manage evidence references.
- Remove individual evidence items.
- Generate structured complaint drafts.
- Organise follow-up information.

### Example incident workflow

```text
              PAYMENT INCIDENT
                     |
                     v
              CREATE INCIDENT
                     |
                     v
              RECORD DETAILS
                     |
                     v
              ADD EVIDENCE
                     |
                     v
             REVIEW INFORMATION
                     |
                     v
            GENERATE COMPLAINT DRAFT
                     |
                     v
            USER REVIEWS THE DRAFT
                     |
                     v
           APPROPRIATE OFFICIAL CHANNEL
```

Complaint drafts are intended to help users organise information for appropriate official channels.

Recovery Desk does not automatically submit complaints, contact banks, reverse payments or guarantee recovery of funds.

---

## 7. Experiments and Feature Management

PayPause includes an experimentation module for controlled scenario assignment and evaluation.

This provides a foundation for evaluating different application experiences and recording structured experiment activity.

### Capabilities

- Retrieve public experiment scenarios.
- Assign experiment variants.
- Maintain stable experiment assignments.
- Submit scenario attempts.
- Record experiment events.
- Evaluate experiment results.
- Restrict aggregate experiment telemetry to configured administrators.

### Flagsmith integration

Flagsmith provides server-side feature-flag and variant evaluation.

The integration supports controlled feature activation and experimentation.

A deterministic fallback is available when the Flagsmith environment key is not configured.

This makes it possible to develop and test the application without making the external feature-flag service mandatory for every development run.

---

# 🔄 How PayPause Works

At a high level, PayPause follows a request-processing lifecycle.

```text
                  USER INTERACTION
                         |
                         v
                  REACT FRONTEND
                         |
                         v
                  REQUEST VALIDATION
                         |
                         v
                    FASTAPI ROUTE
                         |
                         v
                 AUTHENTICATION CONTEXT
                         |
                         v
                  APPLICATION SERVICE
                         |
                         v
                  BUSINESS LOGIC
                         |
                         v
                  REPOSITORY LAYER
                         |
                +--------+--------+
                |                 |
                v                 v
          DEVELOPMENT         PRODUCTION
          REPOSITORY          REPOSITORY
                |                 |
                v                 v
           IN-MEMORY          SUPABASE
                              POSTGRESQL
                |                 |
                +--------+--------+
                         |
                         v
                 STRUCTURED RESPONSE
                         |
                         v
                  REACT FRONTEND
                         |
                         v
                    USER RESULT
```

## Request lifecycle

1. The user interacts with the frontend.
2. The frontend prepares an API request.
3. The backend receives the request through a FastAPI route.
4. Request data is validated against the relevant schema.
5. Authentication context is resolved for protected operations.
6. The appropriate application service executes the business workflow.
7. The repository layer retrieves or persists information.
8. The API returns a structured response.
9. The frontend presents the result.

## Separation of responsibilities

The project separates the following concerns:

| Component | Main responsibility |
|---|---|
| Frontend | Interface and user interaction |
| API routes | HTTP request and response handling |
| Schemas | Input and output validation |
| Services | Business logic and workflows |
| Repository interfaces | Persistence contracts |
| Development repositories | In-memory data implementations |
| Production repositories | Supabase-backed persistence |
| Integrations | External AI and feature-flag services |

---

# 🏗️ System Architecture

PayPause uses a modular full-stack architecture.

## High-level system diagram

```text
                         ┌───────────────────────┐
                         │         USER          │
                         └───────────┬───────────┘
                                     |
                                     v
                         ┌───────────────────────┐
                         │     REACT 19 APP      │
                         │  TypeScript + Vite    │
                         └───────────┬───────────┘
                                     |
                                  REST API
                                     |
                                     v
                         ┌───────────────────────┐
                         │       FASTAPI         │
                         │    APPLICATION API    │
                         └───────────┬───────────┘
                                     |
              ┌──────────────────────┼─────────────────────┐
              |                      |                     |
              v                      v                     v
        ┌────────────┐        ┌────────────┐        ┌────────────┐
        │  PAYGUARD  │        │  BILLSENSE │        │  PAYMENT   │
        │            │        │            │        │  PASSPORT  │
        └────────────┘        └────────────┘        └────────────┘
              |                      |                     |
              └──────────────────────┼─────────────────────┘
                                     |
              ┌──────────────────────┼─────────────────────┐
              |                      |                     |
              v                      v                     v
        ┌────────────┐        ┌────────────┐        ┌────────────┐
        │  PAYMENTS  │        │SUBSCRIPTIONS│       │  RECOVERY  │
        │ MANAGEMENT │        │ MANAGEMENT │        │    DESK    │
        └────────────┘        └────────────┘        └────────────┘
                                     |
                                     v
                         ┌───────────────────────┐
                         │   SERVICE LAYER       │
                         │   BUSINESS LOGIC      │
                         └───────────┬───────────┘
                                     |
                                     v
                         ┌───────────────────────┐
                         │  REPOSITORY INTERFACE │
                         └───────────┬───────────┘
                                     |
                        ┌────────────┴────────────┐
                        |                         |
                        v                         v
              ┌──────────────────┐      ┌──────────────────┐
              │   DEVELOPMENT    │      │   PRODUCTION     │
              │ IN-MEMORY DATA   │      │ SUPABASE ADAPTERS│
              └──────────────────┘      └────────┬─────────┘
                                                 |
                                                 v
                                      ┌─────────────────────┐
                                      │ SUPABASE            │
                                      │ AUTH + POSTGRESQL   │
                                      └─────────────────────┘

                       SUPPORTING INTEGRATIONS
                       ├── Groq AI
                       └── Flagsmith
```

## Backend architecture

The backend is organised into distinct layers.

### API layer

Responsible for:

- Defining REST endpoints.
- Receiving HTTP requests.
- Validating incoming data.
- Resolving dependencies.
- Returning structured responses.

### Schema layer

Uses Pydantic models to define and validate structured request and response data.

### Service layer

Contains application-specific business logic.

Examples include:

- Payment-risk analysis.
- Bill parsing and validation.
- Consumption analysis.
- Subscription calculations.
- Recovery workflows.
- Experiment assignment and evaluation.

### Repository layer

Separates business logic from the persistence implementation.

PayPause contains:

- Repository interfaces.
- Development in-memory repositories.
- Production Supabase-backed repositories.

This design makes it possible to use different persistence implementations without requiring every service to know the details of the database.

## Development and production separation

| Area | Development and testing | Production configuration |
|---|---|---|
| Persistence | In-memory repositories where configured | Supabase-backed repositories |
| Duplicate analysis | Development implementation | Production wrapper implementation |
| Scenario validation | Development implementation | Production wrapper implementation |
| Database | No durable storage for in-memory records | Supabase PostgreSQL |
| Configuration | Development environment | Production environment |
| External integrations | Optional | Configured as required |

The production service wrappers currently reuse deterministic development logic. They should not be interpreted as independent machine-learning fraud-detection models.

---

# 🧰 Technology Stack

PayPause combines frontend engineering, backend development, document processing, database integration and external services.

## Frontend technologies

| Technology | Role |
|---|---|
| React 19 | Component-based user interface |
| TypeScript | Static typing and maintainability |
| Vite | Development server and production bundling |
| React Router | Client-side navigation |
| Supabase JavaScript SDK | Authentication and session integration |
| TanStack React Query | Server-state and data-fetching support |
| Zustand | Client-side state management |
| React Hook Form | Form management |
| Zod | Schema validation |
| Radix UI | Accessible interface primitives |
| Lucide React | Icon system |
| Motion | Interface animation |
| GSAP | Animation tooling |
| Three.js | 3D graphics |
| React Three Fiber / Drei | React-based 3D integration |
| ECharts | Data visualisation |
| PixiJS | 2D rendering |
| Oxlint | Frontend linting |
| Vitest and Testing Library | Frontend testing dependencies |

The package manifest includes a broader set of UI and development dependencies; actual use varies by component and module.

## Backend technologies

| Technology | Role |
|---|---|
| Python | Backend programming language |
| FastAPI | REST API framework |
| Uvicorn | ASGI application server |
| Pydantic | Request validation and settings |
| HTTPX | HTTP client |
| python-dotenv | Environment configuration |
| Pytest | Automated testing |
| pytest-asyncio | Asynchronous test support |

## AI and document processing

| Technology | Role |
|---|---|
| Groq | Optional AI-powered explanations |
| RapidOCR | Optical character recognition |
| ONNX Runtime | OCR inference runtime |
| PyMuPDF | PDF processing and text extraction |
| Pillow | Image processing |
| ZXing-C++ | QR code decoding |

## Database and integrations

| Technology | Role |
|---|---|
| Supabase Auth | User authentication |
| Supabase PostgreSQL | Relational data persistence |
| Supabase Python SDK | Backend database integration |
| Supabase JavaScript SDK | Frontend authentication integration |
| Flagsmith | Feature flags and experimentation |

## Development and engineering tools

| Technology | Role |
|---|---|
| Git | Version control |
| GitHub | Repository hosting and collaboration |
| npm | Frontend package management |
| Python virtual environments | Dependency isolation |
| TypeScript compiler | Static type checking |
| Vite | Frontend production build |
| Oxlint | Static linting |
| Pytest | Backend test automation |

---

# 📁 Repository Structure

The repository is organised to keep frontend, backend, tests, documentation and database migrations separate.

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

### Directory responsibilities

| Directory | Responsibility |
|---|---|
| `backend/app/api/` | REST endpoints |
| `backend/app/core/`

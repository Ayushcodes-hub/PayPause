# Recovery Desk Specification

**Project:** PayPause
**Module Owner:** Bhuvan

---

## 1. Overview

Recovery Desk assists citizens when payments go wrong. Whether dealing with a suspicious UPI collect request, an unauthorized debit, an electricity bill phishing link, or an unfulfilled refund, Recovery Desk tracks the dispute lifecycle and deterministically generates statutory dispute notices.

---

## 2. Supported Incident Categories

1. `suspicious_upi`: Fake QR codes, collect requests from unknown VPAs, or suspicious payment requests.
2. `unauthorised_transaction`: Debits occurring without voluntary customer consent or credential disclosure.
3. `failed_payment`: Account debited but merchant order not completed.
4. `delayed_refund`: Merchant cancellation approved but refund not credited beyond turnaround window.
5. `duplicate_payment`: Multiple debits for a single transaction.
6. `suspected_fraud`: Phishing links, fake customer support calls, or APK malware.
7. `other_dispute`: Miscellaneous payment issues.

---

## 3. Deterministic Evidence Checklists

For each incident category, the system provides a tailored evidence checklist:
- **`suspicious_upi`**: Counterparty VPA, screenshot of QR/prompt, requester mobile number.
- **`unauthorised_transaction`**: 12-digit UTR, bank debit SMS with timestamp, account statement, declaration of non-disclosure.
- **`failed_payment`**: Transaction UTR, merchant failure screen, passbook/statement debit entry.
- **`delayed_refund`**: Merchant refund approval email, gateway ARN, bank statement covering T+7 window.

---

## 4. Statutory Complaint Draft Generation

Endpoint: `POST /api/recovery/incidents/{id}/complaint-draft`

### Principles:
- **No LLM / Pure Determinism:** Uses proven grievance letter structures to ensure 100% legal reliability.
- **Never Invalids or Fabricates:** References only user-provided facts (UTR, amount, timestamp, provider).
- **Clear Disclaimers:** Explicitly marked as a **Citizen Preparation Draft** and clarifies that generating the draft does not constitute an officially filed complaint.
- **Accurate Cybercrime Statement:** States *"I intend to report this incident through the National Cybercrime Reporting Portal (Helpline 1930 / https://cybercrime.gov.in/)"* and never falsely claims that a complaint has already been filed.
- **User-Confirmed Credential Disclosures:**
  - Supports user-specified `credentials_disclosed` (`"yes"`, `"no"`, `"not_sure"`, `"prefer_not_to_say"`).
  - Only generates a non-disclosure declaration if the user explicitly answered `"no"`.
  - If `"yes"`, highlights that credentials were compromised under deception/duress.
  - If unanswered or `"not_sure"`, remains strictly neutral requesting technical investigation without making assumptions.
  - Never collects or stores raw credentials (such as PIN, OTP, password).
- **Statutory Guidance Included:**
  - **RBI Circular RBI/2017-18/15**: Mandates customer zero/limited liability for unauthorized electronic transactions reported within 3 days.
  - **National Cyber Crime Helpline: 1930**: Immediate golden-hour reporting to freeze fraudster accounts.
  - **National Cybercrime Reporting Portal**: [https://cybercrime.gov.in/](https://cybercrime.gov.in/)
  - **RBI Integrated Ombudsman**: [https://cms.rbi.org.in/](https://cms.rbi.org.in/)

---

## 5. Evidence Management & Validation

### Validation Rules
- **Placeholder Rejection:** All fields (`id`, `title`, `file_reference`, `description`, `uploaded_at`) strictly reject placeholder strings such as `"string"`, `"placeholder"`, `"dummy"`, `"test"`, `"null"`, etc.
- **Empty Object Rejection:** Submitting empty objects `{}` or records without non-empty `id` and `title` triggers HTTP 422.
- **Timestamp Validation:** `uploaded_at` must adhere to valid ISO-8601 datetime format (e.g., `2026-11-20T14:30:00Z`).
- **Preservation on Update:** Adding evidence via `PATCH` appends or updates without silently discarding legitimate existing items.

### Evidence Removal Endpoint
- **`DELETE /api/recovery/incidents/{incident_id}/evidence/{evidence_id}`**
  - Enforces authenticated user ownership (returns 404 if incident does not belong to user).
  - Returns HTTP 404 if the evidence item does not exist on the incident.
  - Returns the updated incident record with the evidence removed and automatically appends a removal event to the incident timeline.

---

## 6. Duplicate Incident & Idempotency Protection

- **Root Cause of Prior Duplication:** Prior to this fix, every `POST /api/recovery/incidents` call unconditionally minted a new UUID without validating whether an identical request was already processed, causing rapid client double-submits or network retries to create duplicate records.
- **Idempotency Key:** Clients can supply `idempotency_key` in the request payload. Subsequent requests with the same key return the existing incident with `is_duplicate=True`.
- **Automatic Fingerprint Match:** If identical incidents are submitted (same user, category, provider, amount, transaction_ref, and incident datetime), the existing incident is returned safely without spawning redundant records.
- **Legitimate Separate Incidents:** Separate incidents with differing amounts, dates, or transaction references continue to be created normally.

---

## 7. Security & Isolation

- All endpoints enforce authenticated ownership (`X-User-Id` in dev; Supabase auth token in production).
- Strict separation prevents cross-user access (HTTP 404 returned for unauthorized records).
- All payloads are sanitized to exclude confidential banking credentials.

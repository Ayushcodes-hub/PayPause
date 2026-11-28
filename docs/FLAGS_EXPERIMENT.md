# Flagsmith Experimentation Specification

**Project:** PayPause
**Lead Engineer:** Bhuvan
**Feature Flag:** `payment_intelligence_experience`
**Experiment Name:** `PayPause Payment Intelligence Experience`

---

## 1. Executive Summary & Hypothesis

PayPause introduces an intelligent payment safety layer for Indian digital payments. In this hackathon experiment, we scientifically measure whether a structured **Payment Passport** presentation helps citizens identify fraud signals and make safe verification decisions compared to a conventional **Risk Score First** presentation.

### Research Hypothesis
> A structured **Payment Passport** presentation (Variant B) will improve a user's ability to identify payment risks and choose an appropriate verification action compared with a conventional **Risk Score First** presentation (Variant A).

---

## 2. Experiment Setup & Traffic Allocation

| Parameter | Configuration |
|---|---|
| **Feature Flag Key** | `payment_intelligence_experience` |
| **SDK Type** | Official Flagsmith Python Server-side SDK (`flagsmith>=6.0.0`) |
| **Variant A (Control)** | `risk_score_first` (50% traffic) |
| **Variant B (Treatment)** | `payment_passport_first` (50% traffic) |
| **Participant Identity** | Stable User ID or Session UUID |
| **Evaluation Method** | Server-side identity evaluation (`get_identity_flags(identifier=...)`) |

---

## 3. Metrics Architecture

### Primary Metric (Single Source of Truth)
- **`risk_check_correctly_completed`**
  *Definition:* Emitted **only** when the backend independently validates that the citizen chose both the correct risk determination and an appropriate safety verification action. The frontend cannot trigger this event directly.

### Secondary Metrics
- **`risk_signal_understood`**: Emitted when the participant identifies the specific risk signal (e.g., mismatched VPA domain, PIN requested for credit, or phishing SMS link).
- **`verification_action_selected`**: Emitted when the participant chooses an appropriate safety action (e.g., verifying VPA, checking official discom portal, or calling 1930).
- **`verification_abandoned`**: Emitted when a participant exits or cancels verification before completing the scenario check.

---

## 4. API Endpoints

### 1. `GET /api/experiments/scenarios`
Retrieves interactive scenario challenges. **Security rule:** Canonical answer keys, evaluation rules, and correct action sets are withheld by the backend and never exposed.

**Sample Response:**
```json
[
  {
    "id": "scen_upi_qr_tamper",
    "title": "Merchant Counter QR Code Payment",
    "category": "upi_safety",
    "amount": 450.0,
    "context": "You are paying INR 450 at a grocery store...",
    "options": [
      {"id": "opt_proceed", "label": "Proceed and enter UPI PIN immediately."},
      {"id": "opt_pause_verify", "label": "Pause: alert shopkeeper that VPA does not match."}
    ],
    "verification_actions": [
      {"id": "act_verify_vpa", "label": "Verify VPA with store owner"}
    ]
  }
]
```

### 2. `POST /api/experiments/assign`
Allocates or fetches the stable variant for a participant identifier.

**Request:**
```json
{
  "participant_id": "usr_citizen_001"
}
```

**Response (live Flagsmith mode — requires `FLAGSMITH_ENVIRONMENT_KEY` configured):**
```json
{
  "participant_id": "usr_citizen_001",
  "experiment_name": "PayPause Payment Intelligence Experience",
  "feature_name": "payment_intelligence_experience",
  "variant": "payment_passport_first",
  "source": "flagsmith_real",
  "is_live_flagsmith": true,
  "assigned_at": "2026-11-26T18:00:00Z"
}
```

**Response (offline / fallback mode — when `FLAGSMITH_ENVIRONMENT_KEY` is not set):**
```json
{
  "participant_id": "usr_citizen_001",
  "experiment_name": "PayPause Payment Intelligence Experience",
  "feature_name": "payment_intelligence_experience",
  "variant": "risk_score_first",
  "source": "deterministic_fallback",
  "is_live_flagsmith": false,
  "assigned_at": "2026-11-26T18:00:00Z"
}
```

> **Note:** `source: "flagsmith_real"` and `is_live_flagsmith: true` are only returned when `FLAGSMITH_ENVIRONMENT_KEY` is configured and the Flagsmith API call succeeds. The default local development state uses `deterministic_fallback`.

### 3. `POST /api/experiments/submit`
Submits an answer for backend correctness evaluation and event tracking. Protected by idempotency keys to prevent duplicate event inflation.

**Request:**
```json
{
  "participant_id": "usr_citizen_001",
  "scenario_id": "scen_upi_qr_tamper",
  "selected_answer": "opt_pause_verify",
  "selected_action": "act_verify_vpa",
  "idempotency_key": "idem_citizen001_scen1"
}
```

**Response:**
```json
{
  "submission_id": "subm_a1b2c3d4",
  "participant_id": "usr_citizen_001",
  "scenario_id": "scen_upi_qr_tamper",
  "variant": "payment_passport_first",
  "is_correct": true,
  "score": 1.0,
  "feedback": "Scanned VPA does not match merchant...",
  "is_duplicate": false,
  "events_recorded": [
    "risk_signal_understood",
    "verification_action_selected",
    "risk_check_correctly_completed"
  ],
  "submitted_at": "2026-11-26T18:01:00Z"
}
```

### 4. `GET /api/experiments/status`
Aggregates telemetry, assignments, submissions, and accuracy rates across variants.

---

## 5. Offline Fallback & Error Handling

If `FLAGSMITH_ENVIRONMENT_KEY` is unconfigured or the Flagsmith API times out:
1. The backend logs a warning and engages the deterministic SHA-256 fallback allocator.
2. The exact same user ID continues receiving the exact same variant (50/50 modulo split).
3. `is_live_flagsmith` is reported as `false` and `source` as `deterministic_fallback`.
4. No random or arbitrary assignments occur, preserving test stability.

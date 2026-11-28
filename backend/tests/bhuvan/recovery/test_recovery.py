"""Unit and API tests for Recovery Desk incident tracking and complaint drafting."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.recovery import router as recovery_router
from backend.app.schemas.recovery import IncidentCreate, IncidentUpdate
from backend.app.services.recovery.recovery_service import RecoveryService
from backend.app.repositories.development.in_memory_incident_repo import InMemoryIncidentRepository
from backend.app.core.dependencies import get_current_user, get_incident_repo
from backend.app.core.security import AuthenticatedUser


@pytest.fixture
def incident_repo():
    return InMemoryIncidentRepository()


@pytest.fixture
def recovery_service(incident_repo):
    return RecoveryService(repo=incident_repo)


@pytest.fixture
def auth_user():
    return AuthenticatedUser(
        user_id="user_recovery_bhuvan",
        email="recovery@paypause.local",
        is_active=True,
    )


@pytest.fixture
def intruder_user():
    return AuthenticatedUser(
        user_id="user_recovery_intruder",
        email="intruder@paypause.local",
        is_active=True,
    )


@pytest.fixture
def client(incident_repo, auth_user):
    app = FastAPI()
    app.include_router(recovery_router)
    app.dependency_overrides[get_incident_repo] = lambda: incident_repo
    app.dependency_overrides[get_current_user] = lambda: auth_user
    return TestClient(app)


# ==========================================
# 1. INCIDENT CREATION & CHECKLIST TESTS
# ==========================================

def test_create_incident_generates_evidence_checklist(client):
    """Test incident creation returns populated category-specific evidence checklist."""
    payload = {
        "category": "suspicious_upi",
        "incident_datetime": "2026-11-20T11:45:00",
        "provider": "PhonePe",
        "transaction_ref": "UPI/2026/FRAUD/001",
        "amount": 2500.0,
        "currency": "INR",
        "description": "Received unsolicited collect request claiming to be power department refund.",
        "follow_up_date": "2026-11-22",
    }
    resp = client.post("/api/recovery/incidents", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("inc_")
    assert data["status"] == "reported"
    assert len(data["timeline"]) == 1

    # Verify checklist attached
    checklist = data["evidence_checklist"]
    assert len(checklist) >= 2
    item_names = [item["item_name"] for item in checklist]
    assert any("VPA" in name for name in item_names)


def test_invalid_category_rejected(client):
    """Test invalid incident category is rejected by schema validator."""
    payload = {
        "category": "fake_unknown_category",
        "incident_datetime": "2026-11-20T11:45:00",
        "provider": "PhonePe",
        "amount": 500.0,
        "description": "Short desc",
    }
    resp = client.post("/api/recovery/incidents", json=payload)
    assert resp.status_code == 422


# ==========================================
# 2. RETRIEVAL & USER ISOLATION TESTS
# ==========================================

def test_incident_user_ownership(incident_repo, auth_user, intruder_user):
    """Test that a user cannot retrieve or modify another user's incident."""
    app = FastAPI()
    app.include_router(recovery_router)
    app.dependency_overrides[get_incident_repo] = lambda: incident_repo

    # User A creates incident
    app.dependency_overrides[get_current_user] = lambda: auth_user
    client_a = TestClient(app)
    c_resp = client_a.post(
        "/api/recovery/incidents",
        json={
            "category": "unauthorised_transaction",
            "incident_datetime": "2026-11-18T09:15:00",
            "provider": "SBI Netbanking",
            "transaction_ref": "SBI/DISPUTE/9988",
            "amount": 10000.0,
            "description": "Unauthorized transfer debit notice received while asleep.",
        },
    )
    inc_id = c_resp.json()["id"]

    # Intruder tries to access
    app.dependency_overrides[get_current_user] = lambda: intruder_user
    client_b = TestClient(app)
    get_resp = client_b.get(f"/api/recovery/incidents/{inc_id}")
    assert get_resp.status_code == 404

    # Intruder tries to generate complaint draft
    draft_resp = client_b.post(f"/api/recovery/incidents/{inc_id}/complaint-draft")
    assert draft_resp.status_code == 404


# ==========================================
# 3. STATUS UPDATES & TIMELINE TESTS
# ==========================================

def test_incident_status_update_appends_timeline(client):
    """Test changing status records a new milestone in incident timeline."""
    c_resp = client.post(
        "/api/recovery/incidents",
        json={
            "category": "failed_payment",
            "incident_datetime": "2026-11-15T16:20:00",
            "provider": "GPay",
            "transaction_ref": "GPAY/FAIL/4433",
            "amount": 750.0,
            "description": "Amount debited but merchant bill remained unpaid.",
        },
    )
    inc_id = c_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/recovery/incidents/{inc_id}",
        json={"status": "under_investigation"},
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["status"] == "under_investigation"
    assert len(data["timeline"]) == 2
    assert "under_investigation" in data["timeline"][-1]["event"]


# ==========================================
# 4. COMPLAINT DRAFT GENERATION TESTS
# ==========================================

def test_complaint_draft_contains_statutory_protections(client):
    """Verify complaint draft includes 1930 helpline, cybercrime portal, and RBI circular."""
    c_resp = client.post(
        "/api/recovery/incidents",
        json={
            "category": "unauthorised_transaction",
            "incident_datetime": "2026-11-19T22:10:00",
            "provider": "HDFC Bank",
            "transaction_ref": "HDFC/UTR/778899",
            "amount": 12500.0,
            "description": "Unauthorized transaction debited from savings account without OTP sharing.",
        },
    )
    inc_id = c_resp.json()["id"]

    draft_resp = client.post(f"/api/recovery/incidents/{inc_id}/complaint-draft")
    assert draft_resp.status_code == 200
    draft = draft_resp.json()

    assert draft["is_draft"] is True
    assert "DISCLAIMER" in draft["formal_letter_body"]
    assert "1930" in draft["statutory_guidance"]["national_cyber_helpline"]
    assert "cybercrime.gov.in" in draft["statutory_guidance"]["official_cyber_portal"]
    assert "RBI/2017-18/15" in draft["statutory_guidance"]["rbi_protection_circular"]
    assert "HDFC/UTR/778899" in draft["formal_letter_body"]
    assert "12,500.00" in draft["formal_letter_body"]

    # Verify statement expresses intention rather than falsely claiming filing
    assert "I intend to report this incident through the National Cybercrime Reporting Portal" in draft["formal_letter_body"]
    assert "I have also recorded this incident" not in draft["formal_letter_body"]

    # Verify RBI circular wording is neutral (requests protection, does not claim bank was notified)
    assert "I hereby invoke protection under Reserve Bank of India Circular RBI/2017-18/15" in draft["formal_letter_body"]
    assert "I have promptly reported this incident" not in draft["formal_letter_body"]


def test_complaint_draft_credentials_disclosed_confirmed_no(client):
    """When user explicitly states credentials were NOT disclosed, include non-disclosure affirmation."""
    c_resp = client.post(
        "/api/recovery/incidents",
        json={
            "category": "unauthorised_transaction",
            "incident_datetime": "2026-11-20T10:00:00",
            "provider": "SBI",
            "amount": 5000.0,
            "description": "Money deducted while phone was locked.",
            "credentials_disclosed": "no",
        },
    )
    inc_id = c_resp.json()["id"]
    assert c_resp.json()["credentials_disclosed"] == "no"

    draft_resp = client.post(f"/api/recovery/incidents/{inc_id}/complaint-draft")
    assert draft_resp.status_code == 200
    body = draft_resp.json()["formal_letter_body"]
    assert "I affirm that no confidential authentication credentials" in body


def test_complaint_draft_credentials_disclosed_confirmed_yes(client):
    """When user explicitly states credentials MAY have been disclosed, draft reflects this safely."""
    c_resp = client.post(
        "/api/recovery/incidents",
        json={
            "category": "suspected_fraud",
            "incident_datetime": "2026-11-20T11:00:00",
            "provider": "PhonePe",
            "amount": 8000.0,
            "description": "Scammer tricked user into entering PIN on fake page.",
            "credentials_disclosed": "yes",
        },
    )
    inc_id = c_resp.json()["id"]

    draft_resp = client.post(f"/api/recovery/incidents/{inc_id}/complaint-draft")
    assert draft_resp.status_code == 200
    body = draft_resp.json()["formal_letter_body"]
    assert "credentials may have been compromised or disclosed under deception/duress" in body
    assert "I affirm that no confidential authentication credentials" not in body


def test_complaint_draft_credentials_unanswered_neutral(client):
    """When credentials_disclosed is omitted or unanswered, draft remains neutral without assumptions."""
    c_resp = client.post(
        "/api/recovery/incidents",
        json={
            "category": "failed_payment",
            "incident_datetime": "2026-11-20T12:00:00",
            "provider": "GPay",
            "amount": 1200.0,
            "description": "Debit occurred but order failed.",
        },
    )
    inc_id = c_resp.json()["id"]
    assert c_resp.json()["credentials_disclosed"] is None

    draft_resp = client.post(f"/api/recovery/incidents/{inc_id}/complaint-draft")
    assert draft_resp.status_code == 200
    body = draft_resp.json()["formal_letter_body"]
    assert "investigate the authorization logs and technical circumstances surrounding this disputed transaction without prejudice" in body
    assert "I affirm that no confidential authentication credentials" not in body


def test_update_credentials_disclosed_via_patch(client):
    """Test updating credentials_disclosed status via PATCH."""
    c_resp = client.post(
        "/api/recovery/incidents",
        json={
            "category": "suspicious_upi",
            "incident_datetime": "2026-11-20T13:00:00",
            "provider": "Paytm",
            "amount": 3000.0,
            "description": "Collect request scam.",
        },
    )
    inc_id = c_resp.json()["id"]

    # Patch with "not_sure"
    patch_resp = client.patch(
        f"/api/recovery/incidents/{inc_id}",
        json={"credentials_disclosed": "not_sure"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["credentials_disclosed"] == "not_sure"

    draft_resp = client.post(f"/api/recovery/incidents/{inc_id}/complaint-draft")
    body = draft_resp.json()["formal_letter_body"]
    assert "circumstances of authentication remain unverified or disputed" in body


# ==========================================
# 5. EVIDENCE VALIDATION & PLACEHOLDER REJECTION
# ==========================================

def test_invalid_placeholder_evidence_rejected(client):
    """Verify placeholder records like 'string' and empty evidence objects are rejected."""
    # 1. 'string' placeholder in evidence id
    resp1 = client.post(
        "/api/recovery/incidents",
        json={
            "category": "suspicious_upi",
            "incident_datetime": "2026-11-20T10:00:00",
            "provider": "PhonePe",
            "amount": 500.0,
            "description": "Scam payment QR code at checkout.",
            "evidence_references": [
                {"id": "string", "title": "Store QR Screenshot"}
            ],
        },
    )
    assert resp1.status_code == 422

    # 2. 'string' placeholder in evidence title
    resp2 = client.post(
        "/api/recovery/incidents",
        json={
            "category": "suspicious_upi",
            "incident_datetime": "2026-11-20T10:00:00",
            "provider": "PhonePe",
            "amount": 500.0,
            "description": "Scam payment QR code at checkout.",
            "evidence_references": [
                {"id": "ev_01", "title": "string"}
            ],
        },
    )
    assert resp2.status_code == 422

    # 3. Invalid uploaded_at format (not ISO datetime)
    resp3 = client.post(
        "/api/recovery/incidents",
        json={
            "category": "suspicious_upi",
            "incident_datetime": "2026-11-20T10:00:00",
            "provider": "PhonePe",
            "amount": 500.0,
            "description": "Scam payment QR code at checkout.",
            "evidence_references": [
                {"id": "ev_01", "title": "Bank SMS", "uploaded_at": "string"}
            ],
        },
    )
    assert resp3.status_code == 422

    # 4. Empty evidence object
    resp4 = client.post(
        "/api/recovery/incidents",
        json={
            "category": "suspicious_upi",
            "incident_datetime": "2026-11-20T10:00:00",
            "provider": "PhonePe",
            "amount": 500.0,
            "description": "Scam payment QR code at checkout.",
            "evidence_references": [{}],
        },
    )
    assert resp4.status_code == 422


def test_valid_evidence_preserved_and_appended(client):
    """Verify valid evidence is saved and subsequent updates preserve existing evidence."""
    # Create incident with valid evidence
    c_resp = client.post(
        "/api/recovery/incidents",
        json={
            "category": "unauthorised_transaction",
            "incident_datetime": "2026-11-20T10:00:00",
            "provider": "HDFC",
            "amount": 4500.0,
            "description": "Unauthorized night debit.",
            "evidence_references": [
                {
                    "id": "ev_bank_sms",
                    "title": "Bank Debit SMS",
                    "file_reference": "sms_alert.png",
                    "uploaded_at": "2026-11-20T10:05:00Z",
                }
            ],
        },
    )
    assert c_resp.status_code == 201
    inc_id = c_resp.json()["id"]
    ev_list = c_resp.json()["evidence_references"]
    assert len(ev_list) == 1
    assert ev_list[0]["id"] == "ev_bank_sms"

    # Append second evidence item via PATCH
    patch_resp = client.patch(
        f"/api/recovery/incidents/{inc_id}",
        json={
            "add_evidence": [
                {
                    "id": "ev_statement_pdf",
                    "title": "Monthly Passbook Statement",
                    "file_reference": "statement_nov.pdf",
                    "uploaded_at": "2026-11-20T10:10:00Z",
                }
            ]
        },
    )
    assert patch_resp.status_code == 200
    updated_ev_list = patch_resp.json()["evidence_references"]
    assert len(updated_ev_list) == 2
    ev_ids = [e["id"] for e in updated_ev_list]
    assert "ev_bank_sms" in ev_ids
    assert "ev_statement_pdf" in ev_ids


# ==========================================
# 6. EVIDENCE REMOVAL TESTS
# ==========================================

def test_evidence_removal_success(client):
    """Test safely removing an evidence reference by evidence ID."""
    # Create incident with two items
    c_resp = client.post(
        "/api/recovery/incidents",
        json={
            "category": "failed_payment",
            "incident_datetime": "2026-11-20T11:00:00",
            "provider": "PhonePe",
            "amount": 1000.0,
            "description": "Double debit on failed recharge.",
            "evidence_references": [
                {"id": "ev_recharge_fail", "title": "Recharge Failed Screen"},
                {"id": "ev_passbook", "title": "Bank Passbook Snapshot"},
            ],
        },
    )
    inc_id = c_resp.json()["id"]
    assert len(c_resp.json()["evidence_references"]) == 2

    # Delete first item
    del_resp = client.delete(f"/api/recovery/incidents/{inc_id}/evidence/ev_recharge_fail")
    assert del_resp.status_code == 200
    remaining_ev = del_resp.json()["evidence_references"]
    assert len(remaining_ev) == 1
    assert remaining_ev[0]["id"] == "ev_passbook"

    # Verify timeline updated
    timeline = del_resp.json()["timeline"]
    assert any("Evidence removed" in event["event"] for event in timeline)


def test_evidence_removal_missing_evidence_returns_404(client):
    """Verify deleting a non-existent evidence ID returns 404."""
    c_resp = client.post(
        "/api/recovery/incidents",
        json={
            "category": "failed_payment",
            "incident_datetime": "2026-11-20T11:00:00",
            "provider": "GPay",
            "amount": 750.0,
            "description": "Disputed bill payment.",
            "evidence_references": [
                {"id": "ev_existing", "title": "Receipt Screenshot"}
            ],
        },
    )
    inc_id = c_resp.json()["id"]

    del_resp = client.delete(f"/api/recovery/incidents/{inc_id}/evidence/ev_does_not_exist")
    assert del_resp.status_code == 404
    assert "not found" in del_resp.json()["detail"].lower()


def test_evidence_removal_missing_incident_returns_404(client):
    """Verify deleting evidence from non-existent incident returns 404."""
    del_resp = client.delete("/api/recovery/incidents/inc_unknown_999/evidence/ev_any")
    assert del_resp.status_code == 404
    assert "incident" in del_resp.json()["detail"].lower()


def test_evidence_removal_ownership_protection(incident_repo, auth_user, intruder_user):
    """Verify an intruder cannot remove evidence from another user's incident."""
    app = FastAPI()
    app.include_router(recovery_router)
    app.dependency_overrides[get_incident_repo] = lambda: incident_repo

    # User A creates incident
    app.dependency_overrides[get_current_user] = lambda: auth_user
    client_a = TestClient(app)
    c_resp = client_a.post(
        "/api/recovery/incidents",
        json={
            "category": "unauthorised_transaction",
            "incident_datetime": "2026-11-20T11:30:00",
            "provider": "SBI",
            "amount": 6000.0,
            "description": "Unauthorized transaction.",
            "evidence_references": [
                {"id": "ev_confidential", "title": "Confidential Affidavit"}
            ],
        },
    )
    inc_id = c_resp.json()["id"]

    # User B attempts to delete evidence
    app.dependency_overrides[get_current_user] = lambda: intruder_user
    client_b = TestClient(app)
    del_resp = client_b.delete(f"/api/recovery/incidents/{inc_id}/evidence/ev_confidential")
    assert del_resp.status_code == 404

    # Verify evidence still present for User A
    app.dependency_overrides[get_current_user] = lambda: auth_user
    get_resp = client_a.get(f"/api/recovery/incidents/{inc_id}")
    assert len(get_resp.json()["evidence_references"]) == 1


# ==========================================
# 7. DUPLICATE INCIDENT & IDEMPOTENCY TESTS
# ==========================================

def test_duplicate_incident_idempotency_protection(client):
    """Verify identical duplicate submissions return existing incident without duplication."""
    payload = {
        "category": "delayed_refund",
        "incident_datetime": "2026-11-18T15:00:00",
        "provider": "Paytm",
        "transaction_ref": "REF/PAYTM/DUP_CHECK_001",
        "amount": 1999.0,
        "description": "Flight cancellation refund delayed by merchant beyond 14 days.",
        "idempotency_key": "idem_delayed_refund_001",
    }
    # First post
    resp1 = client.post("/api/recovery/incidents", json=payload)
    assert resp1.status_code == 201
    inc_id1 = resp1.json()["id"]
    assert resp1.json()["is_duplicate"] is False

    # Second post with identical idempotency key
    resp2 = client.post("/api/recovery/incidents", json=payload)
    assert resp2.status_code == 201
    assert resp2.json()["id"] == inc_id1
    assert resp2.json()["is_duplicate"] is True


def test_legitimate_separate_incidents_allowed(client):
    """Verify legitimate separate incidents (different amounts/dates/refs) are both created."""
    base_payload = {
        "category": "failed_payment",
        "provider": "PhonePe",
        "description": "Electricity payment failed at counter.",
    }
    # Incident 1
    resp1 = client.post(
        "/api/recovery/incidents",
        json={
            **base_payload,
            "incident_datetime": "2026-11-10T10:00:00",
            "transaction_ref": "UTR_LEGIT_1",
            "amount": 500.0,
        },
    )
    assert resp1.status_code == 201
    id1 = resp1.json()["id"]

    # Incident 2 (different amount & tx ref)
    resp2 = client.post(
        "/api/recovery/incidents",
        json={
            **base_payload,
            "incident_datetime": "2026-11-10T10:00:00",
            "transaction_ref": "UTR_LEGIT_2",
            "amount": 850.0,
        },
    )
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]

    # Incident 3 (different date)
    resp3 = client.post(
        "/api/recovery/incidents",
        json={
            **base_payload,
            "incident_datetime": "2026-11-12T10:00:00",
            "transaction_ref": "UTR_LEGIT_3",
            "amount": 500.0,
        },
    )
    assert resp3.status_code == 201
    id3 = resp3.json()["id"]

    # All three must be distinct
    assert id1 != id2
    assert id2 != id3
    assert id1 != id3
    assert not resp1.json()["is_duplicate"]
    assert not resp2.json()["is_duplicate"]
    assert not resp3.json()["is_duplicate"]




def test_complaint_draft_does_not_claim_completed_actions(client):
    """Verify that the complaint draft never falsely claims the user has taken any external action.

    The draft must not assert that the user has already:
    - Reported the incident to the bank
    - Notified any authority
    - Contacted 1930 helpline
    - Filed a complaint on the cybercrime portal
    - Any other completed external action not confirmed by user input.
    """
    c_resp = client.post(
        "/api/recovery/incidents",
        json={
            "category": "unauthorised_transaction",
            "incident_datetime": "2026-11-25T09:00:00",
            "provider": "ICICI Bank",
            "transaction_ref": "ICICI/UTR/NOACTION",
            "amount": 7500.0,
            "description": "Amount debited without user initiation.",
        },
    )
    assert c_resp.status_code == 201
    inc_id = c_resp.json()["id"]

    draft_resp = client.post(f"/api/recovery/incidents/{inc_id}/complaint-draft")
    assert draft_resp.status_code == 200
    body = draft_resp.json()["formal_letter_body"]

    # None of these false-action phrases should appear in the draft
    false_action_phrases = [
        "I have promptly reported",
        "I have notified",
        "I have contacted",
        "I have already filed",
        "I have already reported",
        "I have reported this incident to",
        "I have also recorded this incident",
    ]
    for phrase in false_action_phrases:
        assert phrase not in body, (
            f"Complaint draft falsely claims a completed action. "
            f"Found disallowed phrase: '{phrase}'"
        )

    # Confirm the neutral RBI wording IS present
    assert "I hereby invoke protection under Reserve Bank of India Circular RBI/2017-18/15" in body
    # Confirm the cybercrime portal statement is intentional, not asserting completion
    assert "I intend to report this incident through the National Cybercrime Reporting Portal" in body

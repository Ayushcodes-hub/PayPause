"""Integration smoke test for dev_main application.

Validates that all 4 modules (Experiments, Payments, Subscriptions, Recovery)
run together cohesively within dev_main FastAPI app.
"""

from fastapi.testclient import TestClient
from backend.app.dev_main import app

client = TestClient(app)


def test_health_and_root():
    """Verify health check and root endpoints."""
    h_resp = client.get("/health")
    assert h_resp.status_code == 200
    h_data = h_resp.json()
    assert h_data["status"] == "healthy"
    assert "experiments" in h_data["modules_active"]

    r_resp = client.get("/")
    assert r_resp.status_code == 200
    assert "/docs" in r_resp.json()["documentation"]


def test_end_to_end_demonstration_workflow():
    """Demonstrate end-to-end integration across all modules."""
    # 1. Experimentation
    assign_resp = client.post(
        "/api/experiments/assign",
        json={"participant_id": "demo_citizen_001"},
    )
    assert assign_resp.status_code == 200
    variant = assign_resp.json()["variant"]

    submit_resp = client.post(
        "/api/experiments/submit",
        json={
            "participant_id": "demo_citizen_001",
            "scenario_id": "scen_upi_qr_tamper",
            "selected_answer": "opt_pause_verify",
            "selected_action": "act_verify_vpa",
        },
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["is_correct"] is True

    # 2. Payment Management
    pay_resp = client.post(
        "/api/payments",
        json={
            "provider": "PhonePe",
            "merchant": "BESCOM Utility",
            "amount": 1850.0,
            "payment_date": "2026-11-20",
            "category": "utilities",
        },
    )
    assert pay_resp.status_code == 201
    payment_id = pay_resp.json()["id"]

    # 3. Subscription Management
    sub_resp = client.post(
        "/api/subscriptions",
        json={
            "name": "Hotstar Premium",
            "amount": 299.0,
            "frequency": "monthly",
            "start_date": "2026-11-01",
            "next_expected_date": "2026-12-01",
            "category": "entertainment",
        },
    )
    assert sub_resp.status_code == 201
    assert sub_resp.json()["monthly_equivalent_cost"] == 299.0

    # 4. Recovery Desk
    inc_resp = client.post(
        "/api/recovery/incidents",
        json={
            "category": "suspicious_upi",
            "incident_datetime": "2026-11-21T10:00:00",
            "provider": "PhonePe",
            "amount": 1850.0,
            "description": "Scam QR scanned at store; funds debited to fraudulent merchant handle.",
        },
    )
    assert inc_resp.status_code == 201
    inc_id = inc_resp.json()["id"]

    draft_resp = client.post(f"/api/recovery/incidents/{inc_id}/complaint-draft")
    assert draft_resp.status_code == 200
    draft = draft_resp.json()
    assert draft["is_draft"] is True
    assert "RBI/2017-18/15" in draft["statutory_guidance"]["rbi_protection_circular"]

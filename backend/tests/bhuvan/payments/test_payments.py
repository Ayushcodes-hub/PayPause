"""Unit and API tests for Payment Management and Refund Tracking."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.payments import router as payments_router
from backend.app.schemas.payments import PaymentCreate, PaymentUpdate
from backend.app.services.payments.payment_service import PaymentService
from backend.app.repositories.development.in_memory_payment_repo import InMemoryPaymentRepository
from backend.app.repositories.development.mock_duplicate_checker import MockDuplicateChecker
from backend.app.core.dependencies import (
    get_current_user,
    get_payment_repo,
    get_duplicate_checker,
)
from backend.app.core.security import AuthenticatedUser


@pytest.fixture
def payment_repo():
    return InMemoryPaymentRepository()


@pytest.fixture
def duplicate_checker(payment_repo):
    return MockDuplicateChecker(payment_repo=payment_repo)


@pytest.fixture
def payment_service(payment_repo, duplicate_checker):
    return PaymentService(payment_repo=payment_repo, duplicate_checker=duplicate_checker)


@pytest.fixture
def auth_user():
    return AuthenticatedUser(
        user_id="user_bhuvan_test",
        email="bhuvan@test.local",
        is_active=True,
        roles=["user"],
    )


@pytest.fixture
def other_user():
    return AuthenticatedUser(
        user_id="user_other_intruder",
        email="intruder@test.local",
        is_active=True,
        roles=["user"],
    )


@pytest.fixture
def client(payment_repo, duplicate_checker, auth_user):
    app = FastAPI()
    app.include_router(payments_router)
    app.dependency_overrides[get_payment_repo] = lambda: payment_repo
    app.dependency_overrides[get_duplicate_checker] = lambda: duplicate_checker
    app.dependency_overrides[get_current_user] = lambda: auth_user
    return TestClient(app)


# ==========================================
# 1. PAYMENT CREATION & SECURITY TESTS
# ==========================================

def test_create_payment_success(client):
    """Test successful payment record creation."""
    payload = {
        "transaction_ref": "UPI/2026/987654321",
        "provider": "PhonePe",
        "merchant": "Swiggy Bangalore",
        "amount": 349.50,
        "currency": "INR",
        "category": "food",
        "payment_date": "2026-11-20",
        "status": "completed",
    }
    resp = client.post("/api/payments", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("pay_")
    assert data["merchant"] == "Swiggy Bangalore"
    assert data["amount"] == 349.50
    assert data["verification_status"] == "user_recorded"
    assert data["refund_status"] == "not_requested"


def test_sensitive_credentials_never_stored(client, payment_repo):
    """Verify UPI PINs, OTPs, CVVs are stripped and never stored in persistence."""
    payload = {
        "transaction_ref": "UPI/SEC/123",
        "provider": "GPay",
        "merchant": "Grocery Store",
        "amount": 100.0,
        "payment_date": "2026-11-20",
        "upi_pin": "123456",  # FORBIDDEN!
        "otp": "999888",      # FORBIDDEN!
        "cvv": "456",         # FORBIDDEN!
    }
    resp = client.post("/api/payments", json=payload)
    assert resp.status_code == 201
    created_id = resp.json()["id"]

    # Check database record directly
    raw_record = payment_repo.get_payment_by_id(created_id, "user_bhuvan_test")
    assert "upi_pin" not in raw_record
    assert "otp" not in raw_record
    assert "cvv" not in raw_record


def test_duplicate_payment_detection_warning(client):
    """Test that duplicate transaction reference triggers warning from duplicate check engine."""
    payload = {
        "transaction_ref": "UPI/DUP/9999",
        "provider": "Paytm",
        "merchant": "BESCOM Electricity",
        "amount": 1500.0,
        "payment_date": "2026-11-15",
    }
    # First creation
    resp1 = client.post("/api/payments", json=payload)
    assert resp1.status_code == 201
    assert resp1.json()["duplicate_warning"] is None

    # Second creation with identical transaction reference
    resp2 = client.post("/api/payments", json=payload)
    assert resp2.status_code == 201
    data2 = resp2.json()
    assert data2["duplicate_warning"] is not None
    assert data2["duplicate_warning"]["is_suspected_duplicate"] is True
    assert data2["duplicate_warning"]["confidence"] == 1.0


# ==========================================
# 2. RETRIEVAL & USER OWNERSHIP TESTS
# ==========================================

def test_get_payment_by_id(client):
    """Test retrieving payment by ID."""
    create_resp = client.post(
        "/api/payments",
        json={
            "provider": "GPay",
            "merchant": "Bookstore",
            "amount": 550.0,
            "payment_date": "2026-11-10",
        },
    )
    p_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/payments/{p_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == p_id
    assert get_resp.json()["merchant"] == "Bookstore"


def test_user_ownership_enforcement(payment_repo, duplicate_checker, auth_user, other_user):
    """Test that user cannot retrieve or modify another user's payments."""
    app = FastAPI()
    app.include_router(payments_router)
    app.dependency_overrides[get_payment_repo] = lambda: payment_repo
    app.dependency_overrides[get_duplicate_checker] = lambda: duplicate_checker

    # 1. User A creates payment
    app.dependency_overrides[get_current_user] = lambda: auth_user
    client_a = TestClient(app)
    c_resp = client_a.post(
        "/api/payments",
        json={
            "provider": "BHIM",
            "merchant": "Confidential Store",
            "amount": 900.0,
            "payment_date": "2026-11-12",
        },
    )
    payment_id = c_resp.json()["id"]

    # 2. User B attempts to access payment
    app.dependency_overrides[get_current_user] = lambda: other_user
    client_b = TestClient(app)
    intruder_resp = client_b.get(f"/api/payments/{payment_id}")
    assert intruder_resp.status_code == 404  # Not found for intruder

    # 3. User B attempts to patch payment
    intruder_patch = client_b.patch(
        f"/api/payments/{payment_id}",
        json={"notes": "Hacked note"},
    )
    assert intruder_patch.status_code == 404


# ==========================================
# 3. LISTING, FILTERING & PAGINATION TESTS
# ==========================================

def test_payment_listing_and_filters(client):
    """Test filtering by category, amount range, and merchant."""
    # Seed payments
    client.post(
        "/api/payments",
        json={
            "transaction_ref": "UTR_FOOD_1",
            "provider": "PhonePe",
            "merchant": "McDonalds",
            "amount": 250.0,
            "category": "food",
            "payment_date": "2026-11-01",
        },
    )
    client.post(
        "/api/payments",
        json={
            "transaction_ref": "UTR_FOOD_2",
            "provider": "GPay",
            "merchant": "Dominos",
            "amount": 650.0,
            "category": "food",
            "payment_date": "2026-11-05",
        },
    )
    client.post(
        "/api/payments",
        json={
            "transaction_ref": "UTR_UTIL_1",
            "provider": "GPay",
            "merchant": "BESCOM",
            "amount": 2100.0,
            "category": "utilities",
            "payment_date": "2026-11-10",
        },
    )

    # Filter by category = food
    resp_cat = client.get("/api/payments?category=food")
    assert resp_cat.status_code == 200
    assert resp_cat.json()["total"] == 2

    # Filter by amount >= 500
    resp_amt = client.get("/api/payments?min_amount=500")
    assert resp_amt.status_code == 200
    assert resp_amt.json()["total"] == 2

    # Search by merchant substring
    resp_merch = client.get("/api/payments?merchant=domino")
    assert resp_merch.status_code == 200
    assert resp_merch.json()["total"] == 1
    assert resp_merch.json()["items"][0]["merchant"] == "Dominos"


# ==========================================
# 4. PATCH UPDATE & IMMUTABILITY TESTS
# ==========================================

def test_patch_payment_updates_mutable_fields_only(client, payment_repo):
    """Test updating notes and merchant while immutable fields remain untouched."""
    c_resp = client.post(
        "/api/payments",
        json={
            "provider": "PhonePe",
            "merchant": "Local Cafe",
            "amount": 180.0,
            "payment_date": "2026-11-02",
        },
    )
    p_id = c_resp.json()["id"]
    original_created_at = c_resp.json()["created_at"]

    patch_resp = client.patch(
        f"/api/payments/{p_id}",
        json={
            "merchant": "Artisan Coffee House",
            "notes": "Reviewed with friends",
            "id": "pay_fake_hacked_id",    # Immutable: should be ignored
            "user_id": "usr_fake_user",      # Immutable: should be ignored
        },
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["id"] == p_id
    assert data["user_id"] == "user_bhuvan_test"
    assert data["merchant"] == "Artisan Coffee House"
    assert data["notes"] == "Reviewed with friends"
    assert data["created_at"] == original_created_at


# ==========================================
# 5. REFUND TRACKING TESTS
# ==========================================

def test_refund_workflow(client):
    """Test requesting a refund and querying refund history."""
    # 1. Create a payment
    c_resp = client.post(
        "/api/payments",
        json={
            "provider": "Paytm",
            "merchant": "Flight Ticket",
            "amount": 4200.0,
            "payment_date": "2026-11-03",
        },
    )
    p_id = c_resp.json()["id"]

    # 2. Request refund
    patch_resp = client.patch(
        f"/api/payments/{p_id}",
        json={
            "refund_status": "requested",
            "refund_reference": "REF/AIR/9910",
            "expected_refund_date": "2026-11-28",
            "refund_notes": "Flight cancelled by airline",
        },
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["refund_status"] == "requested"
    assert patch_resp.json()["refund_requested_at"] is not None

    # 3. Query /api/payments/refunds
    refunds_resp = client.get("/api/payments/refunds")
    assert refunds_resp.status_code == 200
    refunds = refunds_resp.json()["items"]
    assert len(refunds) >= 1
    assert any(r["id"] == p_id for r in refunds)


# ==========================================
# 6. PAYMENT SUMMARY TESTS
# ==========================================

def test_payment_summary_calculation(client):
    """Test aggregated payment summary stats."""
    # Create payments with different categories
    client.post(
        "/api/payments",
        json={
            "provider": "GPay",
            "merchant": "Store 1",
            "amount": 100.0,
            "category": "groceries",
            "payment_date": "2026-11-01",
        },
    )
    c2 = client.post(
        "/api/payments",
        json={
            "provider": "GPay",
            "merchant": "Store 2",
            "amount": 200.0,
            "category": "utilities",
            "payment_date": "2026-11-02",
        },
    )
    # Mark second as refund requested
    client.patch(
        f"/api/payments/{c2.json()['id']}",
        json={"refund_status": "requested"},
    )

    summary_resp = client.get("/api/payments/summary")
    assert summary_resp.status_code == 200
    s_data = summary_resp.json()
    assert s_data["total_transactions"] >= 2
    assert s_data["total_spend"] >= 300.0
    assert s_data["pending_refunds_count"] >= 1
    assert s_data["pending_refunds_amount"] >= 200.0

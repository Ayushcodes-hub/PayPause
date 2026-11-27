"""Unit and API tests for Recurring Payment / Subscription Management."""

from datetime import date
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.subscriptions import router as subscriptions_router
from backend.app.schemas.subscriptions import SubscriptionCreate
from backend.app.services.subscriptions.subscription_service import SubscriptionService
from backend.app.repositories.development.in_memory_subscription_repo import InMemorySubscriptionRepository
from backend.app.core.dependencies import get_current_user, get_subscription_repo
from backend.app.core.security import AuthenticatedUser


@pytest.fixture
def sub_repo():
    return InMemorySubscriptionRepository()


@pytest.fixture
def sub_service(sub_repo):
    return SubscriptionService(repo=sub_repo)


@pytest.fixture
def auth_user():
    return AuthenticatedUser(
        user_id="user_sub_tester",
        email="subtester@paypause.local",
        is_active=True,
    )


@pytest.fixture
def other_user():
    return AuthenticatedUser(
        user_id="user_sub_other",
        email="other@paypause.local",
        is_active=True,
    )


@pytest.fixture
def client(sub_repo, auth_user):
    app = FastAPI()
    app.include_router(subscriptions_router)
    app.dependency_overrides[get_subscription_repo] = lambda: sub_repo
    app.dependency_overrides[get_current_user] = lambda: auth_user
    return TestClient(app)


# ==========================================
# 1. DETERMINISTIC DATE CALCULATION TESTS
# ==========================================

def test_deterministic_weekly_calculation():
    """Verify weekly billing advances exactly 7 days."""
    start = date(2026, 11, 1)
    nxt = SubscriptionService.calculate_next_billing_date(start, "weekly")
    assert nxt == date(2026, 11, 8)


def test_deterministic_month_end_clamp():
    """Verify month-end dates correctly clamp to the last valid day of subsequent month."""
    # Jan 31 -> Feb 28 in non-leap year (2025)
    start_jan = date(2025, 1, 31)
    nxt_feb = SubscriptionService.calculate_next_billing_date(start_jan, "monthly")
    assert nxt_feb == date(2025, 2, 28)

    # Jan 31 -> Feb 29 in leap year (2024)
    start_leap_jan = date(2024, 1, 31)
    nxt_leap_feb = SubscriptionService.calculate_next_billing_date(start_leap_jan, "monthly")
    assert nxt_leap_feb == date(2024, 2, 29)


def test_deterministic_leap_year_yearly_clamp():
    """Verify Feb 29 on leap year advances to Feb 28 on following non-leap year."""
    leap_date = date(2024, 2, 29)
    nxt_year = SubscriptionService.calculate_next_billing_date(leap_date, "yearly")
    assert nxt_year == date(2025, 2, 28)


def test_invalid_frequency_raises_error():
    """Verify invalid frequency throws ValueError."""
    with pytest.raises(ValueError):
        SubscriptionService.calculate_next_billing_date(date(2026, 1, 1), "bi-weekly")


# ==========================================
# 2. SUBSCRIPTION CRUD & MONTHLY COST TESTS
# ==========================================

def test_create_subscription_calculates_monthly_cost(client):
    """Test creating a yearly subscription correctly computes monthly equivalent cost."""
    payload = {
        "name": "Amazon Prime",
        "amount": 1499.0,
        "currency": "INR",
        "frequency": "yearly",
        "start_date": "2026-01-01",
        "next_expected_date": "2027-01-01",
        "category": "entertainment",
        "cancellation_reminder_days": 7,
    }
    resp = client.post("/api/subscriptions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("sub_")
    assert data["is_active"] is True
    # 1499 / 12 = 124.92
    assert data["monthly_equivalent_cost"] == 124.92


def test_pause_and_resume_subscription(client):
    """Test pausing and resuming subscription."""
    c_resp = client.post(
        "/api/subscriptions",
        json={
            "name": "Gym Membership",
            "amount": 1500.0,
            "frequency": "monthly",
            "start_date": "2026-10-01",
            "next_expected_date": "2026-11-01",
            "category": "health",
        },
    )
    s_id = c_resp.json()["id"]

    # Pause
    pause_resp = client.post(f"/api/subscriptions/{s_id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["is_active"] is False

    # Resume
    resume_resp = client.post(f"/api/subscriptions/{s_id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["is_active"] is True


def test_user_ownership_isolation(sub_repo, auth_user, other_user):
    """Test user cannot view or modify another user's subscription."""
    app = FastAPI()
    app.include_router(subscriptions_router)
    app.dependency_overrides[get_subscription_repo] = lambda: sub_repo

    # User A creates
    app.dependency_overrides[get_current_user] = lambda: auth_user
    client_a = TestClient(app)
    c_resp = client_a.post(
        "/api/subscriptions",
        json={
            "name": "Confidential Sub",
            "amount": 500.0,
            "frequency": "monthly",
            "start_date": "2026-11-01",
            "next_expected_date": "2026-12-01",
        },
    )
    sub_id = c_resp.json()["id"]

    # User B tries to view
    app.dependency_overrides[get_current_user] = lambda: other_user
    client_b = TestClient(app)
    get_resp = client_b.get(f"/api/subscriptions/{sub_id}")
    assert get_resp.status_code == 404


def test_upcoming_forecast_and_summary(sub_service):
    """Test summary calculates commitments and ignores paused subscriptions for alerts."""
    ref_date = date(2026, 11, 20)

    # 1. Active subscription due in 5 days (within 30 days)
    sub_service.create_subscription(
        user_id="user_summary_test",
        payload=SubscriptionCreate(
            name="Netflix",
            amount=649.0,
            frequency="monthly",
            start_date="2026-10-25",
            next_expected_date="2026-11-25",
            cancellation_reminder_days=7,
        ),
    )
    # 2. Paused subscription due in 3 days
    paused = sub_service.create_subscription(
        user_id="user_summary_test",
        payload=SubscriptionCreate(
            name="Spotify Paused",
            amount=119.0,
            frequency="monthly",
            start_date="2026-10-23",
            next_expected_date="2026-11-23",
        ),
    )
    sub_service.set_active_status(paused.id, "user_summary_test", is_active=False)

    summary = sub_service.get_summary(user_id="user_summary_test", reference_date=ref_date)
    assert summary.total_subscriptions == 2
    assert summary.active_subscriptions == 1
    assert summary.paused_subscriptions == 1
    assert summary.total_monthly_commitment == 649.0
    assert len(summary.upcoming_payments) == 1
    assert summary.upcoming_payments[0].name == "Netflix"
    assert summary.upcoming_payments[0].days_remaining == 5
    assert summary.upcoming_payments[0].reminder_due is True

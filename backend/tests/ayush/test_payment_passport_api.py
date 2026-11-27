from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.auth import AuthenticatedUser, get_current_user
from app.main import app
from app.api.v1 import payment_passport


client = TestClient(app)
USER_ID = UUID("123e4567-e89b-12d3-a456-426614174000")


@pytest.fixture
def passport_client():
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=USER_ID,
        email="test@example.com",
    )
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_history_is_scoped_to_authenticated_user(passport_client, monkeypatch):
    captured = {}

    def fake_list(user_id, limit, offset):
        captured.update(user_id=user_id, limit=limit, offset=offset)
        return [{"assessment_id": "assessment-1", "risk_score": 20}]

    monkeypatch.setattr(payment_passport, "list_assessments", fake_list)

    response = passport_client.get(
        "/api/v1/payment-passport/assessments?limit=10&offset=5"
    )

    assert response.status_code == 200
    assert response.json()["data"]["count"] == 1
    assert captured == {
        "user_id": str(USER_ID),
        "limit": 10,
        "offset": 5,
    }


def test_history_rejects_invalid_pagination(passport_client):
    response = passport_client.get(
        "/api/v1/payment-passport/assessments?limit=500"
    )
    assert response.status_code == 422


def test_get_assessment_returns_record(passport_client, monkeypatch):
    record = {
        "assessment_id": "assessment-1",
        "risk_score": 35,
        "risk_level": "moderate",
    }
    captured = {}

    def fake_get(user_id, assessment_id):
        captured.update(user_id=user_id, assessment_id=assessment_id)
        return record

    monkeypatch.setattr(payment_passport, "get_assessment", fake_get)

    response = passport_client.get(
        "/api/v1/payment-passport/assessments/assessment-1"
    )

    assert response.status_code == 200
    assert response.json()["data"]["risk_score"] == 35
    assert captured["user_id"] == str(USER_ID)


def test_get_missing_assessment_returns_404(passport_client, monkeypatch):
    monkeypatch.setattr(
        payment_passport,
        "get_assessment",
        lambda user_id, assessment_id: None,
    )

    response = passport_client.get(
        "/api/v1/payment-passport/assessments/missing"
    )

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_delete_assessment(passport_client, monkeypatch):
    captured = {}

    def fake_delete(user_id, assessment_id):
        captured.update(user_id=user_id, assessment_id=assessment_id)
        return True

    monkeypatch.setattr(payment_passport, "delete_assessment", fake_delete)

    response = passport_client.delete(
        "/api/v1/payment-passport/assessments/assessment-1"
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert captured["user_id"] == str(USER_ID)


def test_delete_missing_assessment_returns_404(passport_client, monkeypatch):
    monkeypatch.setattr(
        payment_passport,
        "delete_assessment",
        lambda user_id, assessment_id: False,
    )

    response = passport_client.delete(
        "/api/v1/payment-passport/assessments/missing"
    )

    assert response.status_code == 404


def test_passport_requires_authentication():
    response = client.get("/api/v1/payment-passport/assessments")
    assert response.status_code == 401

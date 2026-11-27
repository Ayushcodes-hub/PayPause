from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.auth import AuthenticatedUser, get_current_user
from app.main import app


client = TestClient(app)

TEST_USER_ID = UUID("123e4567-e89b-12d3-a456-426614174000")


@pytest.fixture
def authenticated_client():
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=TEST_USER_ID,
        email="test@example.com",
    )

    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_upi_assessment_returns_complete_response(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/payguard/assess",
        json={
            "input_type": "upi",
            "upi_id": "merchant@bank",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Payment risk assessment completed."

    assessment = body["data"]

    assert assessment["assessment_id"]
    assert assessment["input_type"] == "upi"
    assert assessment["risk_score"] == 0
    assert assessment["risk_level"] == "low"
    assert assessment["evidence"] == []
    assert len(assessment["recommendations"]) >= 1
    assert assessment["coverage"]
    assert assessment["limitations"]
    assert assessment["disclaimer"]


def test_url_assessment_returns_complete_response(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/payguard/assess",
        json={
            "input_type": "url",
            "payment_url": "https://example.com/pay",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["data"]["input_type"] == "url"
    assert body["data"]["risk_score"] == 0
    assert body["data"]["risk_level"] == "low"
    assert len(body["data"]["recommendations"]) >= 1


def test_combined_assessment_processes_both_inputs(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/payguard/assess",
        json={
            "input_type": "both",
            "upi_id": "merchant@bank",
            "payment_url": "https://example.com/pay",
        },
    )

    assert response.status_code == 200

    assessment = response.json()["data"]

    assert assessment["input_type"] == "both"
    assert assessment["risk_score"] == 0
    assert assessment["risk_level"] == "low"
    assert assessment["coverage"]
    assert assessment["limitations"]


def test_missing_bearer_token_is_rejected():
    response = client.post(
        "/api/v1/payguard/assess",
        json={
            "input_type": "upi",
            "upi_id": "merchant@bank",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["success"] is False


def test_missing_required_input_returns_422(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/payguard/assess",
        json={
            "input_type": "upi",
        },
    )

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_unexpected_request_field_returns_422(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/payguard/assess",
        json={
            "input_type": "upi",
            "upi_id": "merchant@bank",
            "unexpected": "value",
        },
    )

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_mismatched_input_type_returns_422(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/payguard/assess",
        json={
            "input_type": "upi",
            "payment_url": "https://example.com/pay",
        },
    )

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_invalid_input_type_returns_422(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/payguard/assess",
        json={
            "input_type": "unknown",
            "upi_id": "merchant@bank",
        },
    )

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_payguard_response_includes_security_headers(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/payguard/assess",
        json={
            "input_type": "upi",
            "upi_id": "merchant@bank",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-request-id")

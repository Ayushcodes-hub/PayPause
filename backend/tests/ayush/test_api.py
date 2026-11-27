from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "running"
    assert body["tagline"] == "Think Before Money Moves."
    assert body["application"] == "PayPause API"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "paypause-api",
    }


def test_liveness_endpoint():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_endpoint_reports_database_available(monkeypatch):
    mock_client = MagicMock()

    monkeypatch.setattr(
        "app.main.get_supabase_admin_client",
        lambda: mock_client,
    )

    response = client.get("/health/ready")

    assert response.status_code == 200

    checks = response.json()["checks"]

    assert checks["application"] == "initialized"
    assert checks["database"] == "available"
    expected_ai_status = (
        "configured"
        if settings.AI_API_KEY and settings.AI_MODEL
        else "not_configured"
    )
    assert checks["ai_provider"] == expected_ai_status


def test_readiness_endpoint_reports_database_unavailable(monkeypatch):
    mock_client = MagicMock()

    mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = (
        RuntimeError("Simulated database failure")
    )

    monkeypatch.setattr(
        "app.main.get_supabase_admin_client",
        lambda: mock_client,
    )

    response = client.get("/health/ready")

    assert response.status_code == 503

    body = response.json()

    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == "unavailable"


def test_versioned_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["data"]["service"] == "paypause-api"


def test_unknown_route_returns_standard_error_response():
    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404

    body = response.json()

    assert body["success"] is False
    assert body["error"]["code"] == "HTTP_ERROR"
    assert body["error"]["message"] == "Not Found"


def test_responses_include_request_id():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("x-request-id")


def test_responses_include_security_headers():
    response = client.get("/health")

    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"

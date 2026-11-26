
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.core.auth as auth
from app.main import app


client = TestClient(app)

TEST_USER_ID = "123e4567-e89b-12d3-a456-426614174000"


class MockAsyncClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, headers):
        return self.response


def configure_supabase(monkeypatch, status_code, payload=None):
    monkeypatch.setattr(
        auth.settings,
        "SUPABASE_URL",
        "https://example.supabase.co",
    )
    monkeypatch.setattr(
        auth.settings,
        "SUPABASE_ANON_KEY",
        "test-public-key",
    )

    response = SimpleNamespace(
        status_code=status_code,
        json=lambda: payload,
    )

    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda **kwargs: MockAsyncClient(response),
    )


def test_auth_me_rejects_missing_token():
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["success"] is False


def test_auth_me_rejects_invalid_token(monkeypatch):
    configure_supabase(monkeypatch, 401)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_auth_me_returns_verified_user(monkeypatch):
    configure_supabase(
        monkeypatch,
        200,
        {
            "id": TEST_USER_ID,
            "email": "test@example.com",
        },
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer valid-test-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {
            "id": TEST_USER_ID,
            "email": "test@example.com",
        },
    }


def test_auth_me_fails_closed_when_supabase_is_unavailable(monkeypatch):
    configure_supabase(monkeypatch, 500)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 503
    assert response.json()["success"] is False

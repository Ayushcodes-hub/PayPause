
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import app.core.auth as auth


TEST_USER_ID = "123e4567-e89b-12d3-a456-426614174000"


def credentials(token="test-access-token", scheme="Bearer"):
    return HTTPAuthorizationCredentials(
        scheme=scheme,
        credentials=token,
    )


class MockAsyncClient:
    def __init__(self, response=None, error=None, **kwargs):
        self.response = response
        self.error = error
        self.kwargs = kwargs
        self.request_headers = None
        self.request_url = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, headers):
        self.request_url = url
        self.request_headers = headers

        if self.error:
            raise self.error

        return self.response


@pytest.fixture
def configured_supabase(monkeypatch):
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


@pytest.mark.asyncio
async def test_missing_token_is_rejected():
    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(None)

    assert exc.value.status_code == 401
    assert exc.value.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_non_bearer_scheme_is_rejected():
    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(credentials(scheme="Basic"))

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_supabase_configuration_returns_503(monkeypatch):
    monkeypatch.setattr(auth.settings, "SUPABASE_URL", None)
    monkeypatch.setattr(
        auth.settings,
        "SUPABASE_ANON_KEY",
        None,
    )

    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(credentials())

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_valid_token_returns_verified_user(
    monkeypatch,
    configured_supabase,
):
    response = SimpleNamespace(
        status_code=200,
        json=lambda: {
            "id": TEST_USER_ID,
            "email": "test@example.com",
        },
    )

    mock_client = MockAsyncClient(response=response)

    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda **kwargs: mock_client,
    )

    user = await auth.get_current_user(credentials())

    assert user.id == UUID(TEST_USER_ID)
    assert user.email == "test@example.com"
    assert mock_client.request_url == (
        "https://example.supabase.co/auth/v1/user"
    )
    assert mock_client.request_headers["apikey"] == "test-public-key"
    assert mock_client.request_headers["Authorization"] == (
        "Bearer test-access-token"
    )


@pytest.mark.asyncio
async def test_invalid_token_returns_401(
    monkeypatch,
    configured_supabase,
):
    response = SimpleNamespace(status_code=401)

    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda **kwargs: MockAsyncClient(response=response),
    )

    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(credentials())

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_supabase_server_error_returns_503(
    monkeypatch,
    configured_supabase,
):
    response = SimpleNamespace(status_code=500)

    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda **kwargs: MockAsyncClient(response=response),
    )

    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(credentials())

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_network_failure_returns_503(
    monkeypatch,
    configured_supabase,
):
    request = httpx.Request(
        "GET",
        "https://example.supabase.co/auth/v1/user",
    )
    error = httpx.ConnectError(
        "Connection failed",
        request=request,
    )

    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda **kwargs: MockAsyncClient(error=error),
    )

    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(credentials())

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_malformed_user_response_is_rejected(
    monkeypatch,
    configured_supabase,
):
    response = SimpleNamespace(
        status_code=200,
        json=lambda: {
            "id": "not-a-valid-uuid",
            "email": "test@example.com",
        },
    )

    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda **kwargs: MockAsyncClient(response=response),
    )

    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(credentials())

    assert exc.value.status_code == 503

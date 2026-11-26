
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import BaseModel, ValidationError

from app.core.config import settings


bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """Minimal, server-verified Supabase user identity."""

    id: UUID
    email: str | None = None


def authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication is required or the access token is invalid.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def authentication_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication service is temporarily unavailable.",
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> AuthenticatedUser:
    """
    Validate the bearer token directly with Supabase Auth.

    Never trust user IDs supplied by request bodies or query parameters.
    The returned identity comes from Supabase's verified user response.
    """

    if credentials is None:
        raise authentication_error()

    if credentials.scheme.lower() != "bearer":
        raise authentication_error()

    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise authentication_unavailable()

    url = (
        f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user"
    )

    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {credentials.credentials}",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)

    except httpx.RequestError:
        raise authentication_unavailable() from None

    if response.status_code in (401, 403):
        raise authentication_error()

    if response.status_code != 200:
        raise authentication_unavailable()

    try:
        payload = response.json()
        user = AuthenticatedUser.model_validate(payload)

    except (ValueError, ValidationError, TypeError):
        raise authentication_unavailable() from None

    return user

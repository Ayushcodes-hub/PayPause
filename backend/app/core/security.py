"""Security and authentication abstractions for development.

This module provides a replaceable authentication mechanism. In production,
Ayush's shared Supabase / JWT authentication dependency replaces get_current_user.
"""

from typing import Optional
from pydantic import BaseModel, Field


class AuthenticatedUser(BaseModel):
    """Standard representation of an authenticated user across all endpoints."""

    user_id: str = Field(..., description="Unique user identifier")
    email: Optional[str] = Field(default=None, description="User email address")
    is_active: bool = Field(default=True, description="Whether user account is active")
    roles: list[str] = Field(default_factory=lambda: ["user"], description="User roles")


# Sensitive field protection list: Never store these in any payment or incident record
FORBIDDEN_CREDENTIAL_FIELDS = {
    "upi_pin",
    "pin",
    "otp",
    "cvv",
    "cvc",
    "password",
    "mpin",
    "netbanking_password",
    "card_cvv",
}


def sanitize_payload(payload: dict) -> dict:
    """Recursively strip any forbidden banking credentials or sensitive secrets."""
    sanitized = {}
    for key, value in payload.items():
        if key.lower() in FORBIDDEN_CREDENTIAL_FIELDS:
            continue
        if isinstance(value, dict):
            sanitized[key] = sanitize_payload(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_payload(v) if isinstance(v, dict) else v for v in value
            ]
        else:
            sanitized[key] = value
    return sanitized

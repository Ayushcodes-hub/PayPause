"""Bridge Bhuvan modules to Ayush's verified Supabase identity."""

from fastapi import Depends

from app.core.auth import (
    AuthenticatedUser as SupabaseAuthenticatedUser,
    get_current_user as get_supabase_current_user,
)
from backend.app.core.security import (
    AuthenticatedUser as BhuvanAuthenticatedUser,
)


async def get_bhuvan_supabase_user(
    current_user: SupabaseAuthenticatedUser = Depends(
        get_supabase_current_user
    ),
) -> BhuvanAuthenticatedUser:
    """Convert verified Supabase identity into Bhuvan's user schema."""

    return BhuvanAuthenticatedUser(
        user_id=str(current_user.id),
        email=current_user.email,
        is_active=True,
        roles=["user"],
    )

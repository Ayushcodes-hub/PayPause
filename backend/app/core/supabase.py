from functools import lru_cache

from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.core.config import settings


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    """
    Return a cached backend-only Supabase administrative client.

    The service-role key must never be exposed to frontend applications
    or ordinary unauthenticated requests.
    """

    if not settings.SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not configured.")

    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is not configured."
        )

    options = SyncClientOptions(
        postgrest_client_timeout=5,
    )

    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
        options=options,
    )

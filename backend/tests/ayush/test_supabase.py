from unittest.mock import MagicMock

import pytest
import app.core.supabase as supabase_module
from supabase.lib.client_options import SyncClientOptions


@pytest.fixture(autouse=True)
def clear_supabase_client_cache():
    supabase_module.get_supabase_admin_client.cache_clear()
    yield
    supabase_module.get_supabase_admin_client.cache_clear()


def test_missing_supabase_url_raises_error(monkeypatch):
    monkeypatch.setattr(supabase_module.settings, "SUPABASE_URL", None)
    monkeypatch.setattr(
        supabase_module.settings,
        "SUPABASE_SERVICE_ROLE_KEY",
        "test-service-role-key",
    )

    with pytest.raises(RuntimeError, match="SUPABASE_URL is not configured"):
        supabase_module.get_supabase_admin_client()


def test_missing_service_role_key_raises_error(monkeypatch):
    monkeypatch.setattr(
        supabase_module.settings,
        "SUPABASE_URL",
        "https://example.supabase.co",
    )
    monkeypatch.setattr(
        supabase_module.settings,
        "SUPABASE_SERVICE_ROLE_KEY",
        None,
    )

    with pytest.raises(
        RuntimeError,
        match="SUPABASE_SERVICE_ROLE_KEY is not configured",
    ):
        supabase_module.get_supabase_admin_client()


def test_supabase_client_initializes_with_valid_configuration(monkeypatch):
    mock_client = MagicMock()

    monkeypatch.setattr(
        supabase_module.settings,
        "SUPABASE_URL",
        "https://example.supabase.co",
    )
    monkeypatch.setattr(
        supabase_module.settings,
        "SUPABASE_SERVICE_ROLE_KEY",
        "test-service-role-key",
    )

    create_client_mock = MagicMock(return_value=mock_client)
    monkeypatch.setattr(
        supabase_module,
        "create_client",
        create_client_mock,
    )

    client = supabase_module.get_supabase_admin_client()

    assert client is mock_client
    create_client_mock.assert_called_once()

    args, kwargs = create_client_mock.call_args
    assert args == (
        "https://example.supabase.co",
        "test-service-role-key",
    )

    options = kwargs["options"]
    assert isinstance(options, SyncClientOptions)
    assert options.postgrest_client_timeout == 5


def test_supabase_client_is_cached(monkeypatch):
    mock_client = MagicMock()

    monkeypatch.setattr(
        supabase_module.settings,
        "SUPABASE_URL",
        "https://example.supabase.co",
    )
    monkeypatch.setattr(
        supabase_module.settings,
        "SUPABASE_SERVICE_ROLE_KEY",
        "test-service-role-key",
    )

    create_client_mock = MagicMock(return_value=mock_client)
    monkeypatch.setattr(
        supabase_module,
        "create_client",
        create_client_mock,
    )

    first_client = supabase_module.get_supabase_admin_client()
    second_client = supabase_module.get_supabase_admin_client()

    assert first_client is second_client
    create_client_mock.assert_called_once()

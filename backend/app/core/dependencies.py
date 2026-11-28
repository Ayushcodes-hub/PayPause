"""FastAPI dependency providers for PayPause.

Development/testing use in-memory repositories.
Production requires complete Supabase configuration and uses persistent
Supabase repositories. Production never silently falls back to memory.
"""

from functools import lru_cache
from typing import Annotated, Optional

from fastapi import Header, Depends

from backend.app.core.config import Settings, get_settings
from backend.app.core.security import AuthenticatedUser

from backend.app.repositories.interfaces.payment_repo import PaymentRepositoryInterface
from backend.app.repositories.interfaces.incident_repo import IncidentRepositoryInterface
from backend.app.repositories.interfaces.subscription_repo import SubscriptionRepositoryInterface
from backend.app.repositories.interfaces.experiment_repo import ExperimentRepositoryInterface
from backend.app.repositories.interfaces.duplicate_check import DuplicateCheckerInterface
from backend.app.repositories.interfaces.scenario_validator import ScenarioValidatorInterface

from backend.app.repositories.development.in_memory_payment_repo import InMemoryPaymentRepository
from backend.app.repositories.development.in_memory_incident_repo import InMemoryIncidentRepository
from backend.app.repositories.development.in_memory_subscription_repo import InMemorySubscriptionRepository
from backend.app.repositories.development.in_memory_experiment_repo import InMemoryExperimentRepository
from backend.app.repositories.development.mock_duplicate_checker import MockDuplicateChecker
from backend.app.repositories.development.mock_scenario_validator import MockScenarioValidator

from backend.app.integrations.flagsmith.client import FlagsmithIntegrationService


# Existing development/testing singletons.
_payment_repo = InMemoryPaymentRepository()
_incident_repo = InMemoryIncidentRepository()
_subscription_repo = InMemorySubscriptionRepository()
_experiment_repo = InMemoryExperimentRepository()

_duplicate_checker = MockDuplicateChecker(payment_repo=_payment_repo)
_scenario_validator = MockScenarioValidator()
_flagsmith_service = FlagsmithIntegrationService()

_production_bundle = None
_production_duplicate_checker = None


def _get_repository_bundle():
    """Resolve repository implementations according to application environment."""
    global _production_bundle, _production_duplicate_checker

    settings = get_settings()
    environment = str(getattr(settings, "ENVIRONMENT", "development")).lower()

    if environment != "production":
        return {
            "payment": _payment_repo,
            "incident": _incident_repo,
            "subscription": _subscription_repo,
            "experiment": _experiment_repo,
            "duplicate_checker": _duplicate_checker,
            "scenario_validator": _scenario_validator,
        }

    if _production_bundle is not None:
        return _production_bundle

    required = (
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
    )
    missing = [
        key for key in required
        if not getattr(settings, key, None)
    ]

    if missing:
        raise RuntimeError(
            "Production persistence is not configured. Missing: "
            + ", ".join(missing)
        )

    # Validate the actual service-role connection before exposing repositories.
    from backend.app.core.supabase import get_supabase_admin_client
    get_supabase_admin_client()

    from backend.app.repositories.production import (
        SupabasePaymentRepository,
        SupabaseSubscriptionRepository,
        SupabaseIncidentRepository,
        SupabaseExperimentRepository,
    )
    from backend.app.repositories.production.production_services import (
        ProductionDuplicateChecker,
        ProductionScenarioValidator,
    )

    payment_repo = SupabasePaymentRepository()
    incident_repo = SupabaseIncidentRepository()
    subscription_repo = SupabaseSubscriptionRepository()
    experiment_repo = SupabaseExperimentRepository()

    # The existing duplicate-check interface is retained, but it now receives
    # the production payment repository rather than the in-memory repository.
    production_duplicate_checker = ProductionDuplicateChecker(
        payment_repo=payment_repo
    )
    production_scenario_validator = ProductionScenarioValidator()

    _production_bundle = {
        "payment": payment_repo,
        "incident": incident_repo,
        "subscription": subscription_repo,
        "experiment": experiment_repo,
        "duplicate_checker": production_duplicate_checker,
        "scenario_validator": production_scenario_validator,
    }
    _production_duplicate_checker = production_duplicate_checker

    return _production_bundle


def get_current_user(
    x_user_id: Annotated[Optional[str], Header(alias="X-User-Id")] = None,
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    """Replaceable development authentication dependency."""
    user_id = (
        x_user_id.strip()
        if x_user_id and x_user_id.strip()
        else settings.dev_default_user_id
    )
    return AuthenticatedUser(
        user_id=user_id,
        email=settings.dev_default_user_email,
        is_active=True,
        roles=["user"],
    )


def get_payment_repo() -> PaymentRepositoryInterface:
    return _get_repository_bundle()["payment"]


def get_incident_repo() -> IncidentRepositoryInterface:
    return _get_repository_bundle()["incident"]


def get_subscription_repo() -> SubscriptionRepositoryInterface:
    return _get_repository_bundle()["subscription"]


def get_experiment_repo() -> ExperimentRepositoryInterface:
    return _get_repository_bundle()["experiment"]


def get_duplicate_checker() -> DuplicateCheckerInterface:
    return _get_repository_bundle()["duplicate_checker"]


def get_scenario_validator() -> ScenarioValidatorInterface:
    return _get_repository_bundle()["scenario_validator"]


def get_flagsmith_service() -> FlagsmithIntegrationService:
    return _flagsmith_service

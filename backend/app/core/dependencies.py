"""FastAPI Dependency Injection providers for PayPause modules.

These dependencies allow clean separation of business logic and persistence.
When integrating with Ayush's backend, these dependencies can be swapped
out with production Supabase repositories and authentication.
"""

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

# Singletons for development persistence
_payment_repo = InMemoryPaymentRepository()
_incident_repo = InMemoryIncidentRepository()
_subscription_repo = InMemorySubscriptionRepository()
_experiment_repo = InMemoryExperimentRepository()
_duplicate_checker = MockDuplicateChecker(payment_repo=_payment_repo)
_scenario_validator = MockScenarioValidator()
_flagsmith_service = FlagsmithIntegrationService()



def get_current_user(
    x_user_id: Annotated[Optional[str], Header(alias="X-User-Id")] = None,
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    """Replaceable development authentication dependency.

    Accepts an X-User-Id request header if provided; otherwise falls back to
    the configured dev user ID. When Ayush integrates with Supabase, replace
    this dependency with the shared Supabase auth token validator.
    """
    user_id = x_user_id.strip() if x_user_id and x_user_id.strip() else settings.dev_default_user_id
    return AuthenticatedUser(
        user_id=user_id,
        email=settings.dev_default_user_email,
        is_active=True,
        roles=["user"],
    )


def get_payment_repo() -> PaymentRepositoryInterface:
    """Return payment repository instance."""
    return _payment_repo


def get_incident_repo() -> IncidentRepositoryInterface:
    """Return incident repository instance."""
    return _incident_repo


def get_subscription_repo() -> SubscriptionRepositoryInterface:
    """Return subscription repository instance."""
    return _subscription_repo


def get_experiment_repo() -> ExperimentRepositoryInterface:
    """Return experiment repository instance."""
    return _experiment_repo


def get_duplicate_checker() -> DuplicateCheckerInterface:
    """Return duplicate check engine adapter."""
    return _duplicate_checker


def get_scenario_validator() -> ScenarioValidatorInterface:
    """Return scenario validation engine adapter."""
    return _scenario_validator


def get_flagsmith_service() -> FlagsmithIntegrationService:
    """Return Flagsmith experimentation service."""
    return _flagsmith_service

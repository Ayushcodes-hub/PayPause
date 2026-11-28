"""API routes for Flagsmith experimentation system."""

import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.schemas.experiments import (
    ExperimentAssignRequest,
    ExperimentAssignResponse,
    ExperimentScenarioResponse,
    ExperimentSubmitRequest,
    ExperimentSubmitResponse,
    ExperimentStatusResponse,
)
from backend.app.services.experiments.experiment_service import ExperimentService
from backend.app.core.dependencies import (
    get_current_user,
    get_experiment_repo,
    get_scenario_validator,
    get_flagsmith_service,
)
from backend.app.core.security import AuthenticatedUser
from backend.app.repositories.interfaces.experiment_repo import (
    ExperimentRepositoryInterface,
)
from backend.app.repositories.interfaces.scenario_validator import (
    ScenarioValidatorInterface,
)
from backend.app.integrations.flagsmith.client import FlagsmithIntegrationService

logger = logging.getLogger("paypause.api.experiments")

router = APIRouter(prefix="/api/experiments", tags=["Flagsmith Experiments"])


def get_experiment_service(
    repo: Annotated[ExperimentRepositoryInterface, Depends(get_experiment_repo)],
    validator: Annotated[ScenarioValidatorInterface, Depends(get_scenario_validator)],
    flagsmith: Annotated[FlagsmithIntegrationService, Depends(get_flagsmith_service)],
) -> ExperimentService:
    return ExperimentService(
        experiment_repo=repo,
        scenario_validator=validator,
        flagsmith_service=flagsmith,
    )


def _authenticated_participant(
    req: ExperimentAssignRequest | ExperimentSubmitRequest,
    current_user: AuthenticatedUser,
):
    """Never accept a participant identity supplied by the client."""
    return req.model_copy(update={"participant_id": current_user.user_id})


def _require_experiment_admin(current_user: AuthenticatedUser) -> None:
    """Restrict aggregate experiment telemetry to explicitly configured admins."""
    allowed_ids = {
        value.strip()
        for value in os.getenv("PAYPAUSE_EXPERIMENT_ADMIN_IDS", "").split(",")
        if value.strip()
    }

    if not allowed_ids or current_user.user_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required for experiment telemetry.",
        )


@router.get(
    "/scenarios",
    response_model=list[ExperimentScenarioResponse],
    summary="Retrieve experiment scenarios without answer keys",
)
def list_experiment_scenarios(
    service: Annotated[ExperimentService, Depends(get_experiment_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[ExperimentScenarioResponse]:
    try:
        return service.get_public_scenarios()
    except Exception:
        logger.exception("Failed to retrieve experiment scenarios")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve experiment scenarios. Please try again later.",
        )


@router.post(
    "/assign",
    response_model=ExperimentAssignResponse,
    summary="Assign or retrieve stable experiment variant",
)
def assign_experiment_variant(
    req: ExperimentAssignRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ExperimentService, Depends(get_experiment_service)],
) -> ExperimentAssignResponse:
    try:
        trusted_request = _authenticated_participant(req, current_user)
        return service.assign_participant(trusted_request)
    except ValueError as exc:
        logger.warning("Invalid assign request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception:
        logger.exception(
            "Experiment assignment failed for authenticated user '%s'",
            current_user.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Experiment assignment failed. Please try again later.",
        )


@router.post(
    "/submit",
    response_model=ExperimentSubmitResponse,
    summary="Submit scenario answer and track verifiable events",
)
def submit_experiment_attempt(
    req: ExperimentSubmitRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ExperimentService, Depends(get_experiment_service)],
) -> ExperimentSubmitResponse:
    try:
        trusted_request = _authenticated_participant(req, current_user)
        return service.submit_scenario_attempt(trusted_request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception:
        logger.exception(
            "Submission processing failed for authenticated user '%s', scenario '%s'",
            current_user.user_id,
            req.scenario_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Submission processing failed. Please try again later.",
        )


@router.get(
    "/status",
    response_model=ExperimentStatusResponse,
    summary="Retrieve administrator-only experiment telemetry",
)
def get_experiment_status(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ExperimentService, Depends(get_experiment_service)],
) -> ExperimentStatusResponse:
    _require_experiment_admin(current_user)

    try:
        return service.get_experiment_status()
    except Exception:
        logger.exception("Failed to retrieve experiment status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve experiment status. Please try again later.",
        )

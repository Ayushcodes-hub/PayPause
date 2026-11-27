"""API routes for Flagsmith experimentation system."""

import logging
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
    get_experiment_repo,
    get_scenario_validator,
    get_flagsmith_service,
)
from backend.app.repositories.interfaces.experiment_repo import ExperimentRepositoryInterface
from backend.app.repositories.interfaces.scenario_validator import ScenarioValidatorInterface
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


@router.get(
    "/scenarios",
    response_model=list[ExperimentScenarioResponse],
    summary="Retrieve experiment scenarios without answer keys",
)
def list_experiment_scenarios(
    service: Annotated[ExperimentService, Depends(get_experiment_service)],
) -> list[ExperimentScenarioResponse]:
    """Retrieve scenarios available for the experimentation study.

    Expected answers and validation logic are strictly withheld.
    """
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
    service: Annotated[ExperimentService, Depends(get_experiment_service)],
) -> ExperimentAssignResponse:
    """Retrieve or allocate an experiment variant for a participant/session.

    Guarantees deterministic stability for each participant identity.
    """
    try:
        return service.assign_participant(req)
    except ValueError as exc:
        logger.warning("Invalid assign request: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        logger.exception("Experiment assignment failed for participant '%s'", req.participant_id)
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
    service: Annotated[ExperimentService, Depends(get_experiment_service)],
) -> ExperimentSubmitResponse:
    """Evaluate participant's scenario response against canonical backend criteria.

    Protected against duplicates via scoped idempotency keys. Emits primary metric
    'risk_check_correctly_completed' only upon genuine backend verification.
    Local persistence and event recording are atomic. Flagsmith events are
    forwarded only after a submission is confirmed as newly accepted.
    """
    try:
        return service.submit_scenario_attempt(req)
    except Exception:
        logger.exception(
            "Submission processing failed for participant '%s', scenario '%s'",
            req.participant_id,
            req.scenario_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Submission processing failed. Please try again later.",
        )


@router.get(
    "/status",
    response_model=ExperimentStatusResponse,
    summary="Retrieve experiment telemetry, assignment counts, and variant stats",
)
def get_experiment_status(
    service: Annotated[ExperimentService, Depends(get_experiment_service)],
) -> ExperimentStatusResponse:
    """Return aggregated metrics, variant breakdown, and recorded telemetry.

    Returns only aggregate counts. No individual participant records are exposed.

    Production deployment note:
        Evaluate whether operator/admin authorization is required before
        exposing this endpoint publicly in a production deployment.
    """
    try:
        return service.get_experiment_status()
    except Exception:
        logger.exception("Failed to retrieve experiment status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve experiment status. Please try again later.",
        )

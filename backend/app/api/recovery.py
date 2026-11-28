"""API routes for Recovery Desk incident tracking and complaint draft generation."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.schemas.recovery import (
    IncidentCreate,
    IncidentUpdate,
    IncidentResponse,
    IncidentListResponse,
    ComplaintDraftResponse,
)
from backend.app.services.recovery.recovery_service import RecoveryService
from backend.app.core.dependencies import get_current_user, get_incident_repo
from backend.app.core.security import AuthenticatedUser
from backend.app.repositories.interfaces.incident_repo import IncidentRepositoryInterface

router = APIRouter(prefix="/api/recovery", tags=["Recovery Desk"])


def get_recovery_service(
    repo: Annotated[IncidentRepositoryInterface, Depends(get_incident_repo)],
) -> RecoveryService:
    return RecoveryService(repo=repo)


@router.post(
    "/incidents",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a new payment incident or dispute",
)
def create_incident(
    payload: IncidentCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RecoveryService, Depends(get_recovery_service)],
) -> IncidentResponse:
    """Register an incident with category, evidence references, and automated checklist generation."""
    return service.create_incident(user_id=current_user.user_id, payload=payload)


@router.get(
    "/incidents",
    response_model=IncidentListResponse,
    summary="List recovery incidents for authenticated user",
)
def list_incidents(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RecoveryService, Depends(get_recovery_service)],
    category: Optional[str] = Query(None, description="Category filter (e.g. suspicious_upi, unauthorised_transaction)"),
    incident_status: Optional[str] = Query(None, alias="status", description="Status filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> IncidentListResponse:
    """Retrieve filtered, paginated incidents reported by the user."""
    return service.list_incidents(
        user_id=current_user.user_id,
        category=category,
        status=incident_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/incidents/{incident_id}",
    response_model=IncidentResponse,
    summary="Retrieve incident details and timeline",
)
def get_incident(
    incident_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RecoveryService, Depends(get_recovery_service)],
) -> IncidentResponse:
    """Get incident details, timeline milestones, and attached complaint draft."""
    incident = service.get_incident_by_id(incident_id, current_user.user_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )
    return incident


@router.patch(
    "/incidents/{incident_id}",
    response_model=IncidentResponse,
    summary="Update incident status, follow-up date, or append evidence",
)
def update_incident(
    incident_id: str,
    payload: IncidentUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RecoveryService, Depends(get_recovery_service)],
) -> IncidentResponse:
    """Apply updates to incident status, tracking timeline transitions automatically."""
    updated = service.update_incident(incident_id, current_user.user_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found or unauthorized.",
        )
    return updated


@router.post(
    "/incidents/{incident_id}/complaint-draft",
    response_model=ComplaintDraftResponse,
    summary="Generate deterministic statutory complaint draft for bank or cybercrime portal",
)
def generate_complaint_draft(
    incident_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RecoveryService, Depends(get_recovery_service)],
) -> ComplaintDraftResponse:
    """Generate a formal citizen dispute letter referencing RBI circulars, Helpline 1930, and evidence checklist."""
    draft = service.generate_complaint_draft(incident_id, current_user.user_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )
    return draft


@router.delete(
    "/incidents/{incident_id}/evidence/{evidence_id}",
    response_model=IncidentResponse,
    summary="Remove an evidence item from an incident by its ID",
)
def remove_evidence(
    incident_id: str,
    evidence_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RecoveryService, Depends(get_recovery_service)],
) -> IncidentResponse:
    """Safely remove an evidence reference from an incident by its ID.

    Verifies incident ownership before allowing removal.
    Returns 404 if the incident is not found or if the evidence ID is not found.
    """
    incident_found, evidence_found, updated = service.remove_evidence(
        incident_id=incident_id,
        user_id=current_user.user_id,
        evidence_id=evidence_id,
    )
    if not incident_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )
    if not evidence_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID '{evidence_id}' not found on incident '{incident_id}'.",
        )
    return updated

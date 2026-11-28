"""API routes for Recurring Payment / Subscription Management."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.schemas.subscriptions import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionListResponse,
    SubscriptionSummaryResponse,
)
from backend.app.services.subscriptions.subscription_service import SubscriptionService
from backend.app.core.dependencies import get_current_user, get_subscription_repo
from backend.app.core.security import AuthenticatedUser
from backend.app.repositories.interfaces.subscription_repo import SubscriptionRepositoryInterface

router = APIRouter(prefix="/api/subscriptions", tags=["Recurring Payments & Subscriptions"])


def get_subscription_service(
    repo: Annotated[SubscriptionRepositoryInterface, Depends(get_subscription_repo)],
) -> SubscriptionService:
    return SubscriptionService(repo=repo)


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new recurring subscription",
)
def create_subscription(
    payload: SubscriptionCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionResponse:
    """Register a new recurring payment subscription."""
    return service.create_subscription(user_id=current_user.user_id, payload=payload)


@router.get(
    "",
    response_model=SubscriptionListResponse,
    summary="List subscriptions for the current user",
)
def list_subscriptions(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
    is_active: Optional[bool] = Query(None, description="Filter active or paused subscriptions"),
    category: Optional[str] = Query(None, description="Category filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> SubscriptionListResponse:
    """Retrieve filtered subscriptions with monthly cost breakdown."""
    return service.list_subscriptions(
        user_id=current_user.user_id,
        is_active=is_active,
        category=category,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/summary",
    response_model=SubscriptionSummaryResponse,
    summary="Get recurring expense summary and 30-day forecast",
)
def get_subscription_summary(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionSummaryResponse:
    """Aggregate monthly commitments and upcoming renewal alerts."""
    return service.get_summary(user_id=current_user.user_id)


@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Retrieve subscription by ID",
)
def get_subscription(
    subscription_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionResponse:
    """Get individual subscription details ensuring authenticated ownership."""
    sub = service.get_subscription_by_id(subscription_id, current_user.user_id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription with ID '{subscription_id}' not found.",
        )
    return sub


@router.patch(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Update subscription details",
)
def update_subscription(
    subscription_id: str,
    payload: SubscriptionUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionResponse:
    """Update mutable subscription parameters."""
    updated = service.update_subscription(subscription_id, current_user.user_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription with ID '{subscription_id}' not found or unauthorized.",
        )
    return updated


@router.post(
    "/{subscription_id}/pause",
    response_model=SubscriptionResponse,
    summary="Pause active subscription",
)
def pause_subscription(
    subscription_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionResponse:
    """Mark subscription as paused (inactive)."""
    updated = service.set_active_status(subscription_id, current_user.user_id, is_active=False)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return updated


@router.post(
    "/{subscription_id}/resume",
    response_model=SubscriptionResponse,
    summary="Resume paused subscription",
)
def resume_subscription(
    subscription_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionResponse:
    """Reactivate paused subscription."""
    updated = service.set_active_status(subscription_id, current_user.user_id, is_active=True)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return updated


@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete subscription",
)
def delete_subscription(
    subscription_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> None:
    """Permanently delete a subscription record."""
    deleted = service.delete_subscription(subscription_id, current_user.user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription with ID '{subscription_id}' not found.",
        )

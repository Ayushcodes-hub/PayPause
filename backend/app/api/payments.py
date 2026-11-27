"""API routes for Payment Management and Refund Tracking."""

from datetime import date
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.schemas.payments import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentListResponse,
    PaymentSummaryResponse,
)
from backend.app.services.payments.payment_service import PaymentService
from backend.app.core.dependencies import (
    get_current_user,
    get_payment_repo,
    get_duplicate_checker,
)
from backend.app.core.security import AuthenticatedUser
from backend.app.repositories.interfaces.payment_repo import PaymentRepositoryInterface
from backend.app.repositories.interfaces.duplicate_check import DuplicateCheckerInterface

router = APIRouter(prefix="/api/payments", tags=["Payment Management"])


def get_payment_service(
    repo: Annotated[PaymentRepositoryInterface, Depends(get_payment_repo)],
    dup_checker: Annotated[DuplicateCheckerInterface, Depends(get_duplicate_checker)],
) -> PaymentService:
    return PaymentService(payment_repo=repo, duplicate_checker=dup_checker)


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new payment record",
)
def create_payment(
    payload: PaymentCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> PaymentResponse:
    """Record a user payment with duplicate verification and credential stripping."""
    return service.create_payment(user_id=current_user.user_id, payload=payload)


@router.get(
    "",
    response_model=PaymentListResponse,
    summary="List and filter payments for authenticated user",
)
def list_payments(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
    transaction_ref: Optional[str] = Query(None, description="Search by transaction reference / UTR"),
    date_from: Optional[date] = Query(None, description="Filter payments on or after date"),
    date_to: Optional[date] = Query(None, description="Filter payments on or before date"),
    min_amount: Optional[float] = Query(None, ge=0.0, description="Minimum amount"),
    max_amount: Optional[float] = Query(None, ge=0.0, description="Maximum amount"),
    category: Optional[str] = Query(None, description="Category filter"),
    merchant: Optional[str] = Query(None, description="Merchant substring search"),
    provider: Optional[str] = Query(None, description="Provider filter (e.g. GPay, PhonePe)"),
    payment_status: Optional[str] = Query(None, alias="status", description="Payment status filter"),
    refund_status: Optional[str] = Query(None, description="Refund status filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PaymentListResponse:
    """Retrieve filtered, paginated payment transaction history."""
    return service.list_payments(
        user_id=current_user.user_id,
        transaction_ref=transaction_ref,
        date_from=date_from,
        date_to=date_to,
        min_amount=min_amount,
        max_amount=max_amount,
        category=category,
        merchant=merchant,
        provider=provider,
        status=payment_status,
        refund_status=refund_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/refunds",
    response_model=PaymentListResponse,
    summary="List payments with refund requests or tracking updates",
)
def list_refunds(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
    refund_status: Optional[str] = Query(
        None, description="Filter by status: requested, processing, completed, rejected"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PaymentListResponse:
    """Retrieve payments that have active or resolved refund activity."""
    return service.list_refunds(
        user_id=current_user.user_id,
        refund_status=refund_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/summary",
    response_model=PaymentSummaryResponse,
    summary="Get user payment and refund aggregate summary",
)
def get_payment_summary(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> PaymentSummaryResponse:
    """Calculate summary statistics including total spend, category breakdown, and pending refunds."""
    return service.get_summary(user_id=current_user.user_id)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Get payment details by ID",
)
def get_payment(
    payment_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> PaymentResponse:
    """Retrieve a single payment record, enforcing user ownership."""
    payment = service.get_payment_by_id(payment_id=payment_id, user_id=current_user.user_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID '{payment_id}' not found.",
        )
    return payment


@router.patch(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Update payment or refund information",
)
def update_payment(
    payment_id: str,
    payload: PaymentUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> PaymentResponse:
    """Safely update mutable payment fields or refund metadata."""
    updated = service.update_payment(
        payment_id=payment_id,
        user_id=current_user.user_id,
        update_in=payload,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID '{payment_id}' not found or unauthorized.",
        )
    return updated

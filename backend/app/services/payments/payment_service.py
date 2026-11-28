"""Business logic service for Payment Management and Refund Tracking."""

from datetime import datetime, date, timezone
from typing import Optional, Any

from backend.app.schemas.payments import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentListResponse,
    PaymentSummaryResponse,
)
from backend.app.repositories.interfaces.payment_repo import PaymentRepositoryInterface
from backend.app.repositories.interfaces.duplicate_check import DuplicateCheckerInterface
from backend.app.core.security import sanitize_payload


class PaymentService:
    """Service managing payments, duplicate evaluation, and refund workflows."""

    def __init__(
        self,
        payment_repo: PaymentRepositoryInterface,
        duplicate_checker: Optional[DuplicateCheckerInterface] = None,
    ) -> None:
        self.payment_repo = payment_repo
        self.duplicate_checker = duplicate_checker

    def create_payment(self, user_id: str, payload: PaymentCreate) -> PaymentResponse:
        """Create a validated payment record with duplicate check telemetry."""
        # 1. Sanitize payload against sensitive credentials
        data = sanitize_payload(payload.model_dump())
        data["user_id"] = user_id
        data["verification_status"] = "user_recorded"

        # 2. Duplicate payment check (integrating with Ayush's engine contract)
        dup_warning = None
        if self.duplicate_checker:
            check_res = self.duplicate_checker.check_payment(
                user_id=user_id,
                amount=payload.amount,
                transaction_ref=payload.transaction_ref,
                merchant=payload.merchant,
                payment_date=payload.payment_date,
            )
            if check_res.is_duplicate:
                dup_warning = {
                    "is_suspected_duplicate": True,
                    "confidence": check_res.confidence,
                    "reason": check_res.reason,
                    "matched_payment_id": check_res.matched_payment_id,
                    "details": check_res.details,
                }

        # 3. Persist record
        created = self.payment_repo.create_payment(data)
        if dup_warning:
            created["duplicate_warning"] = dup_warning

        return PaymentResponse(**created)

    def list_payments(
        self,
        user_id: str,
        transaction_ref: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        category: Optional[str] = None,
        merchant: Optional[str] = None,
        provider: Optional[str] = None,
        status: Optional[str] = None,
        refund_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaymentListResponse:
        """Retrieve paginated and filtered payments for the authenticated user."""
        items, total = self.payment_repo.list_payments(
            user_id=user_id,
            transaction_ref=transaction_ref,
            date_from=date_from,
            date_to=date_to,
            min_amount=min_amount,
            max_amount=max_amount,
            category=category,
            merchant=merchant,
            provider=provider,
            status=status,
            refund_status=refund_status,
            limit=limit,
            offset=offset,
        )
        return PaymentListResponse(
            items=[PaymentResponse(**p) for p in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_payment_by_id(self, payment_id: str, user_id: str) -> Optional[PaymentResponse]:
        """Retrieve single payment ensuring authenticated ownership."""
        record = self.payment_repo.get_payment_by_id(payment_id=payment_id, user_id=user_id)
        if not record:
            return None
        return PaymentResponse(**record)

    def update_payment(
        self, payment_id: str, user_id: str, update_in: PaymentUpdate
    ) -> Optional[PaymentResponse]:
        """Apply safe updates to payment or refund fields."""
        # Sanitize and extract only provided fields
        update_data = sanitize_payload(update_in.model_dump(exclude_unset=True))
        if not update_data:
            record = self.payment_repo.get_payment_by_id(payment_id=payment_id, user_id=user_id)
            return PaymentResponse(**record) if record else None

        # Automatically capture refund_requested_at when status becomes requested
        if update_data.get("refund_status") == "requested":
            update_data.setdefault("refund_requested_at", datetime.now(timezone.utc).isoformat())

        updated = self.payment_repo.update_payment(
            payment_id=payment_id, user_id=user_id, update_fields=update_data
        )
        if not updated:
            return None
        return PaymentResponse(**updated)

    def list_refunds(
        self,
        user_id: str,
        refund_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaymentListResponse:
        """Retrieve payments that have active or completed refund statuses."""
        items, total = self.payment_repo.list_refunds(
            user_id=user_id,
            refund_status=refund_status,
            limit=limit,
            offset=offset,
        )
        return PaymentListResponse(
            items=[PaymentResponse(**p) for p in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_summary(self, user_id: str) -> PaymentSummaryResponse:
        """Calculate spend aggregates and refund metrics."""
        summary = self.payment_repo.get_summary(user_id=user_id)
        return PaymentSummaryResponse(**summary)

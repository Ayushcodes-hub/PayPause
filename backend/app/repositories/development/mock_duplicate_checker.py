"""Development implementation of DuplicateCheckerInterface.

Simulates Ayush's core duplicate payment detection engine for local development
and testing without implementing a competing engine.
"""

from typing import Optional
from backend.app.repositories.interfaces.duplicate_check import (
    DuplicateCheckerInterface,
    DuplicateCheckResult,
)
from backend.app.repositories.interfaces.payment_repo import PaymentRepositoryInterface


class MockDuplicateChecker(DuplicateCheckerInterface):
    """Development adapter simulating duplicate payment checks."""

    def __init__(self, payment_repo: Optional[PaymentRepositoryInterface] = None) -> None:
        self.payment_repo = payment_repo

    def check_payment(
        self,
        user_id: str,
        amount: float,
        transaction_ref: Optional[str],
        merchant: str,
        payment_date: str,
    ) -> DuplicateCheckResult:
        if not self.payment_repo:
            return DuplicateCheckResult(
                is_duplicate=False,
                confidence=0.0,
                reason="Duplicate checker operating in standalone mock mode (no repo attached)",
            )

        # Check by transaction reference if present and non-empty
        if transaction_ref and transaction_ref.strip():
            existing = self.payment_repo.get_payment_by_transaction_ref(
                transaction_ref=transaction_ref.strip(), user_id=user_id
            )
            if existing:
                return DuplicateCheckResult(
                    is_duplicate=True,
                    confidence=1.0,
                    reason=f"Identical transaction reference '{transaction_ref}' already recorded.",
                    matched_payment_id=existing.get("id"),
                    details={
                        "rule": "exact_transaction_ref_match",
                        "existing_amount": existing.get("amount"),
                    },
                )

        # Check for ambiguous potential duplicate: same user, exact same amount, same merchant on same date
        payments, _ = self.payment_repo.list_payments(
            user_id=user_id,
            min_amount=amount,
            max_amount=amount,
            merchant=merchant,
            limit=5,
        )
        for p in payments:
            if p.get("payment_date") == payment_date:
                return DuplicateCheckResult(
                    is_duplicate=True,
                    confidence=0.85,
                    reason=(
                        f"Potential duplicate: existing payment of INR {amount} to '{merchant}' "
                        f"found on the same date ({payment_date})."
                    ),
                    matched_payment_id=p.get("id"),
                    details={
                        "rule": "fuzzy_amount_merchant_date_match",
                        "existing_payment_id": p.get("id"),
                    },
                )

        return DuplicateCheckResult(
            is_duplicate=False,
            confidence=0.0,
            reason="No duplicate payment detected",
        )

"""Abstract Base Class defining the contract for Payment & Refund persistence."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, Any


class PaymentRepositoryInterface(ABC):
    """Repository interface for Payment and Refund persistence."""

    @abstractmethod
    def create_payment(self, payment_data: dict[str, Any]) -> dict[str, Any]:
        """Persist a new payment record and return the created record."""
        pass

    @abstractmethod
    def get_payment_by_id(self, payment_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a single payment record by payment_id ensuring user ownership."""
        pass

    @abstractmethod
    def get_payment_by_transaction_ref(
        self, transaction_ref: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        """Find an existing payment by transaction reference for a specific user."""
        pass

    @abstractmethod
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
    ) -> tuple[list[dict[str, Any]], int]:
        """Return a filtered, paginated list of payments and total count."""
        pass

    @abstractmethod
    def update_payment(
        self, payment_id: str, user_id: str, update_fields: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Update mutable fields of a payment record for the authorized user."""
        pass

    @abstractmethod
    def list_refunds(
        self,
        user_id: str,
        refund_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return payments that have a refund request or non-default refund status."""
        pass

    @abstractmethod
    def get_summary(self, user_id: str) -> dict[str, Any]:
        """Generate payment aggregates (total spend, categories, refund status totals)."""
        pass

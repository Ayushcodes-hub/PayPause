"""Interface for Ayush's core duplicate payment detection engine.

Ayush owns the core duplicate-payment detection engine. This interface defines
the contract so our payment module can check for duplicate payments without
implementing a competing engine.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from pydantic import BaseModel, Field


class DuplicateCheckResult(BaseModel):
    """Result returned by the duplicate payment check engine."""

    is_duplicate: bool = Field(..., description="Whether a suspected duplicate was detected")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Detection confidence score")
    reason: str = Field(default="", description="Explanation of duplicate detection")
    matched_payment_id: Optional[str] = Field(
        default=None, description="ID of existing matching payment if found"
    )
    details: dict[str, Any] = Field(default_factory=dict, description="Metadata from detection engine")


class DuplicateCheckerInterface(ABC):
    """Contract for external duplicate payment detection engine."""

    @abstractmethod
    def check_payment(
        self,
        user_id: str,
        amount: float,
        transaction_ref: Optional[str],
        merchant: str,
        payment_date: str,
    ) -> DuplicateCheckResult:
        """Evaluate whether an incoming payment matches an existing payment."""
        pass

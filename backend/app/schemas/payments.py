"""Pydantic schemas for Payment Management and Refund Tracking."""

from datetime import date, datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator
from backend.app.core.security import FORBIDDEN_CREDENTIAL_FIELDS


class PaymentBase(BaseModel):
    transaction_ref: Optional[str] = Field(
        default=None,
        description="Transaction reference / UTR if available",
        max_length=64,
    )
    provider: str = Field(
        ...,
        description="Payment provider (e.g. GPay, PhonePe, Paytm, BHIM, Bank)",
        min_length=2,
        max_length=50,
    )
    merchant: str = Field(
        ...,
        description="Merchant or beneficiary description",
        min_length=2,
        max_length=150,
    )
    amount: float = Field(..., gt=0.0, description="Payment amount in currency units")
    currency: str = Field(default="INR", max_length=5)
    category: str = Field(
        default="general",
        description="Category (e.g. food, utilities, shopping, subscription, transfer)",
        max_length=50,
    )
    payment_date: str = Field(
        ..., description="Date of payment (YYYY-MM-DD or ISO timestamp)"
    )
    status: str = Field(
        default="completed",
        description="Payment status: completed, pending, failed",
    )
    linked_bill_id: Optional[str] = Field(default=None, description="Associated bill identifier")
    linked_incident_id: Optional[str] = Field(default=None, description="Associated Recovery Desk incident")
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("payment_date")
    @classmethod
    def validate_payment_date(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("payment_date is required")
        try:
            # Validate ISO or YYYY-MM-DD format
            if "T" in v:
                datetime.fromisoformat(v)
            else:
                date.fromisoformat(v)
        except ValueError:
            raise ValueError("payment_date must be valid ISO-8601 or YYYY-MM-DD format")
        return v


class PaymentCreate(PaymentBase):
    """Payload for creating a new payment record."""
    pass


class PaymentUpdate(BaseModel):
    """Payload for updating mutable payment fields via PATCH."""
    merchant: Optional[str] = Field(default=None, min_length=2, max_length=150)
    category: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=500)
    linked_bill_id: Optional[str] = None
    linked_incident_id: Optional[str] = None
    status: Optional[str] = None

    # Refund fields updated via payment patch or dedicated endpoint
    refund_status: Optional[str] = Field(
        default=None,
        description="not_requested, requested, processing, completed, rejected, unknown",
    )
    refund_reference: Optional[str] = Field(default=None, max_length=64)
    expected_refund_date: Optional[str] = None
    refund_notes: Optional[str] = Field(default=None, max_length=500)


class PaymentResponse(BaseModel):
    id: str
    user_id: str
    transaction_ref: Optional[str] = None
    provider: str
    merchant: str
    amount: float
    currency: str
    category: str
    payment_date: str
    status: str
    verification_status: str = Field(
        default="user_recorded",
        description="user_recorded (self-entered) or bank_verified (authorized external)",
    )
    refund_status: str = "not_requested"
    refund_reference: Optional[str] = None
    expected_refund_date: Optional[str] = None
    refund_notes: Optional[str] = None
    refund_requested_at: Optional[str] = None
    linked_bill_id: Optional[str] = None
    linked_incident_id: Optional[str] = None
    notes: Optional[str] = None
    duplicate_warning: Optional[bool | dict[str, Any]] = None
    created_at: str
    updated_at: str


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    limit: int
    offset: int


class PaymentSummaryResponse(BaseModel):
    total_transactions: int
    total_spend: float
    category_breakdown: dict[str, float]
    refund_breakdown: dict[str, int]
    pending_refunds_count: int
    pending_refunds_amount: float

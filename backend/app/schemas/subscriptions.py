"""Pydantic schemas for Recurring Payment / Subscription Management."""

from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


FrequencyType = Literal["weekly", "monthly", "quarterly", "yearly"]


class SubscriptionBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Name of subscription (e.g. Netflix, Wi-Fi)")
    amount: float = Field(..., gt=0.0, description="Recurring cost per cycle")
    currency: str = Field(default="INR", max_length=5)
    frequency: FrequencyType = Field(..., description="Billing frequency: weekly, monthly, quarterly, yearly")
    start_date: str = Field(..., description="Subscription start date (YYYY-MM-DD)")
    next_expected_date: str = Field(..., description="Next billing date (YYYY-MM-DD)")
    category: str = Field(default="entertainment", max_length=50)
    provider: Optional[str] = Field(default=None, max_length=50, description="Payment method/provider used")
    cancellation_reminder_days: int = Field(
        default=3, ge=0, le=30, description="Days before renewal to alert user"
    )
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("start_date", "next_expected_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be formatted as YYYY-MM-DD")
        return v


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    amount: Optional[float] = Field(default=None, gt=0.0)
    frequency: Optional[FrequencyType] = None
    next_expected_date: Optional[str] = None
    category: Optional[str] = None
    provider: Optional[str] = None
    is_active: Optional[bool] = None
    cancellation_reminder_days: Optional[int] = Field(default=None, ge=0, le=30)
    notes: Optional[str] = None

    @field_validator("next_expected_date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                date.fromisoformat(v)
            except ValueError:
                raise ValueError("Date must be formatted as YYYY-MM-DD")
        return v


class SubscriptionResponse(BaseModel):
    id: str
    user_id: str
    name: str
    amount: float
    currency: str
    frequency: str
    start_date: str
    next_expected_date: str
    category: str
    provider: Optional[str] = None
    is_active: bool
    cancellation_reminder_days: int
    monthly_equivalent_cost: float
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class UpcomingPaymentItem(BaseModel):
    subscription_id: str
    name: str
    amount: float
    currency: str
    due_date: str
    days_remaining: int
    reminder_due: bool


class SubscriptionListResponse(BaseModel):
    items: list[SubscriptionResponse]
    total: int
    limit: int
    offset: int


class SubscriptionSummaryResponse(BaseModel):
    total_subscriptions: int
    active_subscriptions: int
    paused_subscriptions: int
    total_monthly_commitment: float
    upcoming_30_days_total: float
    upcoming_payments: list[UpcomingPaymentItem]

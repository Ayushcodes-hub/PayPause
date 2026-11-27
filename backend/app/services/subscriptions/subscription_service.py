"""Business logic service for Recurring Payment / Subscription Management.

Includes deterministic date calculations handling leap years and month-ends,
monthly equivalent expense forecasting, and cancellation reminders.
"""

import calendar
from datetime import date, timedelta
from typing import Optional, Any

from backend.app.schemas.subscriptions import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionListResponse,
    UpcomingPaymentItem,
    SubscriptionSummaryResponse,
)
from backend.app.repositories.interfaces.subscription_repo import SubscriptionRepositoryInterface
from backend.app.core.security import sanitize_payload


class SubscriptionService:
    """Service managing recurring subscriptions and forecast calculations."""

    def __init__(self, repo: SubscriptionRepositoryInterface) -> None:
        self.repo = repo

    def create_subscription(
        self, user_id: str, payload: SubscriptionCreate
    ) -> SubscriptionResponse:
        """Create a new subscription with calculated monthly equivalent cost."""
        data = sanitize_payload(payload.model_dump())
        data["user_id"] = user_id
        data["is_active"] = True

        monthly_cost = self._calc_monthly_cost(payload.amount, payload.frequency)
        data["monthly_equivalent_cost"] = monthly_cost

        created = self.repo.create_subscription(data)
        return SubscriptionResponse(**created)

    def list_subscriptions(
        self,
        user_id: str,
        is_active: Optional[bool] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SubscriptionListResponse:
        """Retrieve subscriptions for the user with optional filtering."""
        items, total = self.repo.list_subscriptions(
            user_id=user_id,
            is_active=is_active,
            category=category,
            limit=limit,
            offset=offset,
        )
        return SubscriptionListResponse(
            items=[SubscriptionResponse(**s) for s in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_subscription_by_id(
        self, subscription_id: str, user_id: str
    ) -> Optional[SubscriptionResponse]:
        """Retrieve a specific subscription by ID."""
        record = self.repo.get_subscription_by_id(subscription_id, user_id)
        if not record:
            return None
        return SubscriptionResponse(**record)

    def update_subscription(
        self, subscription_id: str, user_id: str, payload: SubscriptionUpdate
    ) -> Optional[SubscriptionResponse]:
        """Update mutable subscription fields."""
        update_data = sanitize_payload(payload.model_dump(exclude_unset=True))
        if not update_data:
            existing = self.repo.get_subscription_by_id(subscription_id, user_id)
            return SubscriptionResponse(**existing) if existing else None

        existing = self.repo.get_subscription_by_id(subscription_id, user_id)
        if not existing:
            return None

        # Re-calculate monthly cost if amount or frequency is modified
        amount = update_data.get("amount", existing.get("amount"))
        freq = update_data.get("frequency", existing.get("frequency"))
        update_data["monthly_equivalent_cost"] = self._calc_monthly_cost(amount, freq)

        updated = self.repo.update_subscription(subscription_id, user_id, update_data)
        return SubscriptionResponse(**updated) if updated else None

    def set_active_status(
        self, subscription_id: str, user_id: str, is_active: bool
    ) -> Optional[SubscriptionResponse]:
        """Pause or resume a subscription."""
        return self.update_subscription(
            subscription_id=subscription_id,
            user_id=user_id,
            payload=SubscriptionUpdate(is_active=is_active),
        )

    def delete_subscription(self, subscription_id: str, user_id: str) -> bool:
        """Delete subscription record."""
        return self.repo.delete_subscription(subscription_id, user_id)

    def get_summary(
        self, user_id: str, reference_date: Optional[date] = None
    ) -> SubscriptionSummaryResponse:
        """Calculate recurring expense commitment and upcoming payment forecast."""
        ref_date = reference_date or date.today()
        all_subs, _ = self.repo.list_subscriptions(user_id=user_id, limit=200)

        total_subscriptions = len(all_subs)
        active_subs = [s for s in all_subs if s.get("is_active", True)]
        paused_count = total_subscriptions - len(active_subs)

        total_monthly_commitment = sum(
            float(s.get("monthly_equivalent_cost", 0.0)) for s in active_subs
        )

        upcoming_items: list[UpcomingPaymentItem] = []
        upcoming_30_total = 0.0

        for s in active_subs:
            try:
                due_date = date.fromisoformat(s["next_expected_date"])
                days_diff = (due_date - ref_date).days
                if 0 <= days_diff <= 30:
                    amount = float(s.get("amount", 0.0))
                    upcoming_30_total += amount
                    reminder_days = int(s.get("cancellation_reminder_days", 3))
                    upcoming_items.append(
                        UpcomingPaymentItem(
                            subscription_id=s["id"],
                            name=s["name"],
                            amount=amount,
                            currency=s.get("currency", "INR"),
                            due_date=s["next_expected_date"],
                            days_remaining=days_diff,
                            reminder_due=(days_diff <= reminder_days),
                        )
                    )
            except Exception:
                continue

        upcoming_items.sort(key=lambda x: x.days_remaining)

        return SubscriptionSummaryResponse(
            total_subscriptions=total_subscriptions,
            active_subscriptions=len(active_subs),
            paused_subscriptions=paused_count,
            total_monthly_commitment=round(total_monthly_commitment, 2),
            upcoming_30_days_total=round(upcoming_30_total, 2),
            upcoming_payments=upcoming_items,
        )

    @staticmethod
    def calculate_next_billing_date(start_date: date, frequency: str) -> date:
        """Advance date deterministically handling leap years and month-end clamp."""
        freq = frequency.lower()
        if freq == "weekly":
            return start_date + timedelta(days=7)

        if freq in ("monthly", "quarterly"):
            months_to_add = 1 if freq == "monthly" else 3
            month = start_date.month - 1 + months_to_add
            year = start_date.year + month // 12
            month = month % 12 + 1
            day = min(start_date.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)

        if freq == "yearly":
            year = start_date.year + 1
            month = start_date.month
            day = min(start_date.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)

        raise ValueError(f"Unsupported frequency: '{frequency}'")

    @staticmethod
    def _calc_monthly_cost(amount: float, frequency: str) -> float:
        freq = frequency.lower()
        if freq == "weekly":
            return round((amount * 52) / 12, 2)
        elif freq == "monthly":
            return round(amount, 2)
        elif freq == "quarterly":
            return round(amount / 3, 2)
        elif freq == "yearly":
            return round(amount / 12, 2)
        return round(amount, 2)

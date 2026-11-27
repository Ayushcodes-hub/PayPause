"""Abstract Base Class defining the contract for recurring subscription persistence."""

from abc import ABC, abstractmethod
from typing import Optional, Any


class SubscriptionRepositoryInterface(ABC):
    """Repository interface for recurring payment subscriptions."""

    @abstractmethod
    def create_subscription(self, data: dict[str, Any]) -> dict[str, Any]:
        """Persist a new recurring subscription."""
        pass

    @abstractmethod
    def get_subscription_by_id(self, subscription_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a subscription by ID ensuring user ownership."""
        pass

    @abstractmethod
    def list_subscriptions(
        self,
        user_id: str,
        is_active: Optional[bool] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return a filtered, paginated list of subscriptions for a user."""
        pass

    @abstractmethod
    def update_subscription(
        self, subscription_id: str, user_id: str, update_fields: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Update mutable fields of a subscription."""
        pass

    @abstractmethod
    def delete_subscription(self, subscription_id: str, user_id: str) -> bool:
        """Delete or archive a subscription record."""
        pass

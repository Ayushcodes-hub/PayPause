"""Thread-safe In-Memory implementation of SubscriptionRepositoryInterface."""

import threading
from datetime import datetime, timezone
from typing import Optional, Any
import uuid

from backend.app.repositories.interfaces.subscription_repo import SubscriptionRepositoryInterface


class InMemorySubscriptionRepository(SubscriptionRepositoryInterface):
    """In-memory subscription repository."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscriptions: dict[str, dict[str, Any]] = {}

    def create_subscription(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = dict(data)
            if "id" not in record or not record["id"]:
                record["id"] = f"sub_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()
            record.setdefault("created_at", now)
            record.setdefault("updated_at", now)
            record.setdefault("is_active", True)
            self._subscriptions[record["id"]] = record
            return dict(record)

    def get_subscription_by_id(self, subscription_id: str, user_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            record = self._subscriptions.get(subscription_id)
            if record and record.get("user_id") == user_id:
                return dict(record)
            return None

    def list_subscriptions(
        self,
        user_id: str,
        is_active: Optional[bool] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        with self._lock:
            results = []
            for s in self._subscriptions.values():
                if s.get("user_id") != user_id:
                    continue
                if is_active is not None and s.get("is_active") != is_active:
                    continue
                if category and (s.get("category") or "").lower() != category.lower():
                    continue
                results.append(dict(s))

            results.sort(key=lambda x: x.get("next_expected_date") or x.get("created_at", ""))
            total = len(results)
            paginated = results[offset : offset + limit]
            return paginated, total

    def update_subscription(
        self, subscription_id: str, user_id: str, update_fields: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        with self._lock:
            record = self._subscriptions.get(subscription_id)
            if not record or record.get("user_id") != user_id:
                return None
            immutable = {"id", "user_id", "created_at"}
            for k, v in update_fields.items():
                if k not in immutable:
                    record[k] = v
            record["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._subscriptions[subscription_id] = record
            return dict(record)

    def delete_subscription(self, subscription_id: str, user_id: str) -> bool:
        with self._lock:
            record = self._subscriptions.get(subscription_id)
            if record and record.get("user_id") == user_id:
                del self._subscriptions[subscription_id]
                return True
            return False

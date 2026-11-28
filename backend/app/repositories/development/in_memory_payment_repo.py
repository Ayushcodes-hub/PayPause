"""Thread-safe In-Memory implementation of PaymentRepositoryInterface for development and testing."""

import threading
from datetime import date, datetime, timezone
from typing import Optional, Any
import uuid

from backend.app.repositories.interfaces.payment_repo import PaymentRepositoryInterface


class InMemoryPaymentRepository(PaymentRepositoryInterface):
    """In-memory payment and refund repository."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._payments: dict[str, dict[str, Any]] = {}

    def create_payment(self, payment_data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = dict(payment_data)
            if "id" not in record or not record["id"]:
                record["id"] = f"pay_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()
            record.setdefault("created_at", now)
            record.setdefault("updated_at", now)
            record.setdefault("refund_status", "not_requested")
            record.setdefault("status", "completed")
            self._payments[record["id"]] = record
            return dict(record)

    def get_payment_by_id(self, payment_id: str, user_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            record = self._payments.get(payment_id)
            if record and record.get("user_id") == user_id:
                return dict(record)
            return None

    def get_payment_by_transaction_ref(
        self, transaction_ref: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        with self._lock:
            for p in self._payments.values():
                if (
                    p.get("user_id") == user_id
                    and p.get("transaction_ref")
                    and p.get("transaction_ref").strip().lower()
                    == transaction_ref.strip().lower()
                ):
                    return dict(p)
            return None

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
        with self._lock:
            results = []
            for p in self._payments.values():
                if p.get("user_id") != user_id:
                    continue
                if (
                    transaction_ref
                    and transaction_ref.strip().lower()
                    not in (p.get("transaction_ref") or "").lower()
                ):
                    continue
                if p.get("payment_date"):
                    try:
                        p_date = (
                            datetime.fromisoformat(p["payment_date"]).date()
                            if isinstance(p["payment_date"], str)
                            else p["payment_date"]
                        )
                        if date_from and p_date < date_from:
                            continue
                        if date_to and p_date > date_to:
                            continue
                    except Exception:
                        pass
                amount = float(p.get("amount", 0.0))
                if min_amount is not None and amount < min_amount:
                    continue
                if max_amount is not None and amount > max_amount:
                    continue
                if category and (p.get("category") or "").lower() != category.lower():
                    continue
                if (
                    merchant
                    and merchant.lower() not in (p.get("merchant") or "").lower()
                ):
                    continue
                if provider and (p.get("provider") or "").lower() != provider.lower():
                    continue
                if status and (p.get("status") or "").lower() != status.lower():
                    continue
                if (
                    refund_status
                    and (p.get("refund_status") or "").lower() != refund_status.lower()
                ):
                    continue
                results.append(dict(p))

            # Sort descending by payment_date / created_at
            results.sort(
                key=lambda x: (x.get("payment_date") or x.get("created_at") or ""),
                reverse=True,
            )
            total = len(results)
            paginated = results[offset : offset + limit]
            return paginated, total

    def update_payment(
        self, payment_id: str, user_id: str, update_fields: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        with self._lock:
            record = self._payments.get(payment_id)
            if not record or record.get("user_id") != user_id:
                return None
            # Immutable fields: id, user_id, created_at
            immutable = {"id", "user_id", "created_at"}
            for k, v in update_fields.items():
                if k not in immutable:
                    record[k] = v
            record["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._payments[payment_id] = record
            return dict(record)

    def list_refunds(
        self,
        user_id: str,
        refund_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        with self._lock:
            results = []
            for p in self._payments.values():
                if p.get("user_id") != user_id:
                    continue
                status = p.get("refund_status", "not_requested")
                if status == "not_requested":
                    continue
                if refund_status and status.lower() != refund_status.lower():
                    continue
                results.append(dict(p))
            results.sort(
                key=lambda x: (x.get("refund_requested_at") or x.get("updated_at") or ""),
                reverse=True,
            )
            total = len(results)
            paginated = results[offset : offset + limit]
            return paginated, total

    def get_summary(self, user_id: str) -> dict[str, Any]:
        with self._lock:
            user_payments = [p for p in self._payments.values() if p.get("user_id") == user_id]
            total_amount = sum(float(p.get("amount", 0.0)) for p in user_payments)
            category_totals: dict[str, float] = {}
            refund_totals: dict[str, int] = {}
            pending_refunds_count = 0
            pending_refunds_amount = 0.0

            for p in user_payments:
                cat = p.get("category", "uncategorized")
                category_totals[cat] = category_totals.get(cat, 0.0) + float(p.get("amount", 0.0))

                r_status = p.get("refund_status", "not_requested")
                refund_totals[r_status] = refund_totals.get(r_status, 0) + 1
                if r_status in ("requested", "processing"):
                    pending_refunds_count += 1
                    pending_refunds_amount += float(p.get("amount", 0.0))

            return {
                "total_transactions": len(user_payments),
                "total_spend": round(total_amount, 2),
                "category_breakdown": {k: round(v, 2) for k, v in category_totals.items()},
                "refund_breakdown": refund_totals,
                "pending_refunds_count": pending_refunds_count,
                "pending_refunds_amount": round(pending_refunds_amount, 2),
            }

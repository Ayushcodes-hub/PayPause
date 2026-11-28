"""Production Supabase repository adapters for PayPause.

All user-owned reads and writes are explicitly owner-scoped. The Supabase
service-role client bypasses RLS, so application-level filters are mandatory.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.app.core.supabase import get_supabase_admin_client


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _client():
    return get_supabase_admin_client()


def _data(response):
    return response.data or []


def _one(query):
    data = query.execute().data
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return data[0] if data else None
    return data


def _rows(query):
    return _data(query.execute())


def _clean(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


class SupabasePaymentRepository:
    TABLE = "payments"

    def create_payment(self, payment_data):
        payload = dict(payment_data)
        payload.setdefault("id", _id("pay"))
        payload.setdefault("created_at", _now())
        payload.setdefault("updated_at", payload["created_at"])
        payload.setdefault("refund_status", "not_requested")
        payload.setdefault("status", "completed")
        return _one(_client().table(self.TABLE).insert(payload).select("*"))

    def get_payment_by_id(self, payment_id, user_id):
        return _one(
            _client().table(self.TABLE).select("*")
            .eq("id", payment_id).eq("user_id", str(user_id))
        )

    def get_payment_by_transaction_ref(self, transaction_ref, user_id):
        return _one(
            _client().table(self.TABLE).select("*")
            .eq("user_id", str(user_id))
            .ilike("transaction_ref", transaction_ref.strip())
            .limit(1)
        )

    def list_payments(
        self, user_id, transaction_ref=None, date_from=None, date_to=None,
        min_amount=None, max_amount=None, category=None, merchant=None,
        provider=None, status=None, refund_status=None, limit=50, offset=0
    ):
        query = (
            _client().table(self.TABLE).select("*", count="exact")
            .eq("user_id", str(user_id))
        )
        if transaction_ref:
            query = query.ilike("transaction_ref", f"%{transaction_ref}%")
        if date_from:
            query = query.gte("payment_date", date_from)
        if date_to:
            query = query.lte("payment_date", date_to)
        if min_amount is not None:
            query = query.gte("amount", min_amount)
        if max_amount is not None:
            query = query.lte("amount", max_amount)
        if category:
            query = query.ilike("category", category)
        if merchant:
            query = query.ilike("merchant", f"%{merchant}%")
        if provider:
            query = query.ilike("provider", provider)
        if status:
            query = query.ilike("status", status)
        if refund_status:
            query = query.ilike("refund_status", refund_status)

        query = query.order("payment_date", desc=True).range(
            offset, offset + limit - 1
        )
        response = query.execute()
        return response.data or [], response.count or 0

    def update_payment(self, payment_id, user_id, update_fields):
        fields = dict(update_fields)
        for key in ("id", "user_id", "created_at"):
            fields.pop(key, None)
        fields["updated_at"] = _now()
        return _one(
            _client().table(self.TABLE).update(fields)
            .eq("id", payment_id).eq("user_id", str(user_id)).select("*")
        )

    def list_refunds(self, user_id, refund_status=None, limit=50, offset=0):
        query = (
            _client().table(self.TABLE).select("*", count="exact")
            .eq("user_id", str(user_id))
            .neq("refund_status", "not_requested")
        )
        if refund_status:
            query = query.ilike("refund_status", refund_status)
        response = (
            query.order("refund_requested_at", desc=True)
            .range(offset, offset + limit - 1).execute()
        )
        return response.data or [], response.count or 0

    def get_summary(self, user_id):
        rows = _rows(
            _client().table(self.TABLE).select("*")
            .eq("user_id", str(user_id))
        )
        categories = {}
        refunds = {}
        total_spend = 0.0
        pending_count = 0
        pending_amount = 0.0

        for row in rows:
            amount = float(row.get("amount") or 0)
            total_spend += amount
            category = row.get("category") or "general"
            categories[category] = categories.get(category, 0.0) + amount

            refund_status = row.get("refund_status") or "not_requested"
            refunds[refund_status] = refunds.get(refund_status, 0) + 1
            if refund_status in ("requested", "processing"):
                pending_count += 1
                pending_amount += amount

        return {
            "total_transactions": len(rows),
            "total_spend": round(total_spend, 2),
            "category_breakdown": categories,
            "refund_breakdown": refunds,
            "pending_refunds_count": pending_count,
            "pending_refunds_amount": round(pending_amount, 2),
        }


class SupabaseSubscriptionRepository:
    TABLE = "subscriptions"

    def create_subscription(self, subscription_data):
        payload = dict(subscription_data)
        payload.setdefault("id", _id("sub"))
        payload.setdefault("created_at", _now())
        payload.setdefault("updated_at", payload["created_at"])
        payload.setdefault("is_active", True)
        if payload.get("monthly_equivalent_cost") is None:
            amount = float(payload["amount"])
            frequency = payload["frequency"]
            divisor = {
                "weekly": 12 / 52,
                "monthly": 1,
                "quarterly": 3,
                "yearly": 12,
            }[frequency]
            payload["monthly_equivalent_cost"] = round(amount / divisor, 2)
        return _one(
            _client().table(self.TABLE).insert(payload).select("*")
        )

    def get_subscription_by_id(self, subscription_id, user_id):
        return _one(
            _client().table(self.TABLE).select("*")
            .eq("id", subscription_id).eq("user_id", str(user_id))
        )

    def list_subscriptions(
        self, user_id, is_active=None, category=None, limit=50, offset=0
    ):
        query = (
            _client().table(self.TABLE).select("*", count="exact")
            .eq("user_id", str(user_id))
        )
        if is_active is not None:
            query = query.eq("is_active", is_active)
        if category:
            query = query.ilike("category", category)
        response = (
            query.order("next_expected_date")
            .range(offset, offset + limit - 1).execute()
        )
        return response.data or [], response.count or 0

    def update_subscription(self, subscription_id, user_id, update_fields):
        fields = dict(update_fields)
        for key in ("id", "user_id", "created_at"):
            fields.pop(key, None)
        fields["updated_at"] = _now()
        return _one(
            _client().table(self.TABLE).update(fields)
            .eq("id", subscription_id).eq("user_id", str(user_id))
            .select("*")
        )

    def delete_subscription(self, subscription_id, user_id):
        response = (
            _client().table(self.TABLE).delete()
            .eq("id", subscription_id).eq("user_id", str(user_id))
            .execute()
        )
        return bool(response.data)


class SupabaseIncidentRepository:
    TABLE = "recovery_incidents"

    def create_incident(self, incident_data):
        payload = dict(incident_data)
        user_id = str(payload["user_id"])
        result = _one(
            _client().rpc(
                "create_recovery_incident_atomically",
                {"p_user_id": user_id, "p_incident": payload},
            )
        )
        if result is None:
            raise RuntimeError("Incident creation RPC returned no result")
        incident = result["incident"]
        incident["is_duplicate"] = result["is_duplicate"]
        return incident

    def get_incident_by_id(self, incident_id, user_id):
        return _one(
            _client().table(self.TABLE).select("*")
            .eq("id", incident_id).eq("user_id", str(user_id))
        )

    def list_incidents(
        self, user_id, category=None, status=None, limit=50, offset=0
    ):
        query = (
            _client().table(self.TABLE).select("*", count="exact")
            .eq("user_id", str(user_id))
        )
        if category:
            query = query.eq("category", category)
        if status:
            query = query.eq("status", status)
        response = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1).execute()
        )
        return response.data or [], response.count or 0

    def update_incident(self, incident_id, user_id, update_fields):
        fields = dict(update_fields)
        fields.pop("id", None)
        fields.pop("user_id", None)
        result = _one(
            _client().rpc(
                "update_recovery_incident_atomically",
                {
                    "p_user_id": str(user_id),
                    "p_incident_id": incident_id,
                    "p_fields": fields,
                },
            )
        )
        return result

    def save_complaint_draft(self, incident_id, user_id, draft_data):
        return _one(
            _client().rpc(
                "save_recovery_complaint_draft",
                {
                    "p_user_id": str(user_id),
                    "p_incident_id": incident_id,
                    "p_draft": draft_data,
                },
            )
        )

    def remove_evidence(self, incident_id, user_id, evidence_id):
        result = _one(
            _client().rpc(
                "remove_recovery_evidence_atomically",
                {
                    "p_user_id": str(user_id),
                    "p_incident_id": incident_id,
                    "p_evidence_id": evidence_id,
                },
            )
        )
        if not result:
            return False, False, None
        return (
            result["incident_found"],
            result["evidence_found"],
            result.get("incident"),
        )

    def find_duplicate_incident(
        self, user_id, category, provider, amount,
        incident_datetime, transaction_ref=None
    ):
        query = (
            _client().table(self.TABLE).select("*")
            .eq("user_id", str(user_id))
            .eq("category", category)
            .ilike("provider", provider.strip())
            .eq("incident_datetime", incident_datetime)
        )
        candidates = _rows(query)
        expected_ref = (transaction_ref or "").strip().casefold()
        for row in candidates:
            stored_ref = (row.get("transaction_ref") or "").strip().casefold()
            if stored_ref != expected_ref:
                continue
            if abs(float(row["amount"]) - float(amount)) <= 0.001:
                return row
        return None

    def get_incident_by_idempotency_key(self, idempotency_key, user_id):
        return _one(
            _client().table(self.TABLE).select("*")
            .eq("user_id", str(user_id))
            .eq("idempotency_key", idempotency_key)
        )


class SupabaseExperimentRepository:
    ASSIGNMENTS = "experiment_assignments"
    SUBMISSIONS = "experiment_submissions"
    EVENTS = "experiment_events"

    def get_assignment(self, participant_id, experiment_name):
        owner = str(participant_id)
        return _one(
            _client().table(self.ASSIGNMENTS).select("*")
            .eq("owner_user_id", owner)
            .eq("participant_id", owner)
            .eq("experiment_name", experiment_name)
        )

    def save_assignment(self, assignment_data):
        payload = dict(assignment_data)
        owner = str(payload["participant_id"])
        payload["owner_user_id"] = owner
        payload.setdefault("id", str(uuid4()))
        payload.setdefault("assigned_at", _now())
        return _one(
            _client().table(self.ASSIGNMENTS).upsert(
                payload,
                on_conflict="owner_user_id,participant_id,experiment_name",
            ).select("*")
        )

    def save_submission_atomic(self, scoped_key, submission_data, events):
        payload = dict(submission_data)
        owner = str(payload["participant_id"])
        payload["owner_user_id"] = owner
        payload["scoped_key"] = scoped_key

        event_payloads = []
        for event in events:
            item = dict(event)
            item["owner_user_id"] = owner
            item.setdefault("event_id", _id("evt"))
            item.setdefault("created_at", _now())
            event_payloads.append(item)

        result = _one(
            _client().rpc(
                "submit_experiment_atomically_v2",
                {
                    "p_owner_user_id": owner,
                    "p_submission": payload,
                    "p_events": event_payloads,
                },
            )
        )
        if result is None:
            raise RuntimeError("Atomic experiment submission returned no result")

        from backend.app.repositories.interfaces.experiment_repo import AtomicSubmitResult
        return AtomicSubmitResult(
            is_new=result["is_new"],
            submission=result["submission"],
            events=result.get("events", []),
        )

    def record_event(self, event_data):
        payload = dict(event_data)
        payload["owner_user_id"] = str(payload["participant_id"])
        payload.setdefault("event_id", _id("evt"))
        payload.setdefault("created_at", _now())
        return _one(
            _client().table(self.EVENTS).insert(payload).select("*")
        )

    def get_events(
        self, experiment_name=None, participant_id=None, metric_name=None
    ):
        query = _client().table(self.EVENTS).select("*")
        if participant_id is not None:
            query = query.eq("owner_user_id", str(participant_id))
            query = query.eq("participant_id", str(participant_id))
        if experiment_name:
            query = query.eq("experiment_name", experiment_name)
        if metric_name:
            query = query.eq("metric_name", metric_name)
        return _rows(query.order("created_at", desc=True))

    def get_experiment_stats(self, experiment_name):
        # This aggregate is intended only for the admin-authorized experiment
        # status endpoint. Individual participant reads remain owner-scoped.
        assignments = _rows(
            _client().table(self.ASSIGNMENTS).select("*")
            .eq("experiment_name", experiment_name)
            .not_.is_("owner_user_id", "null")
        )
        submissions = _rows(
            _client().table(self.SUBMISSIONS).select("*")
            .eq("experiment_name", experiment_name)
            .not_.is_("owner_user_id", "null")
        )
        events = _rows(
            _client().table(self.EVENTS).select("*")
            .eq("experiment_name", experiment_name)
            .not_.is_("owner_user_id", "null")
        )

        variants = {}
        for submission in submissions:
            variant = submission.get("variant") or "unknown"
            stats = variants.setdefault(
                variant, {"total": 0, "correct": 0, "accuracy": 0.0}
            )
            stats["total"] += 1
            stats["correct"] += int(bool(submission.get("is_correct")))

        for stats in variants.values():
            stats["accuracy"] = (
                round(stats["correct"] / stats["total"], 4)
                if stats["total"] else 0.0
            )

        metric_counts = {}
        for event in events:
            metric = event.get("metric_name") or "unknown"
            metric_counts[metric] = metric_counts.get(metric, 0) + 1

        return {
            "experiment_name": experiment_name,
            "total_assignments": len(assignments),
            "total_submissions": len(submissions),
            "total_events": len(events),
            "variants": variants,
            "event_metrics": metric_counts,
        }

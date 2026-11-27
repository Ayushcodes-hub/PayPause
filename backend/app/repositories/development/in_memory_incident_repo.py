"""Thread-safe In-Memory implementation of IncidentRepositoryInterface for Recovery Desk."""

import threading
from datetime import datetime, timezone
from typing import Optional, Any
import uuid

from backend.app.repositories.interfaces.incident_repo import IncidentRepositoryInterface


class InMemoryIncidentRepository(IncidentRepositoryInterface):
    """In-memory recovery incident and complaint draft repository."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._incidents: dict[str, dict[str, Any]] = {}
        self._drafts: dict[str, dict[str, Any]] = {}
        # Key: (user_id, idempotency_key) -> incident_id
        self._idempotency_map: dict[tuple[str, str], str] = {}

    def get_incident_by_idempotency_key(
        self, idempotency_key: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        with self._lock:
            inc_id = self._idempotency_map.get((user_id, idempotency_key))
            if inc_id and inc_id in self._incidents:
                return dict(self._incidents[inc_id])
            return None

    def find_duplicate_incident(
        self,
        user_id: str,
        category: str,
        provider: str,
        amount: float,
        incident_datetime: str,
        transaction_ref: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        with self._lock:
            clean_provider = (provider or "").strip().lower()
            clean_tx = (transaction_ref or "").strip().lower()
            for inc in self._incidents.values():
                if inc.get("user_id") != user_id:
                    continue
                if inc.get("category") != category:
                    continue
                if (inc.get("provider") or "").strip().lower() != clean_provider:
                    continue
                if abs(float(inc.get("amount", 0.0)) - float(amount)) > 0.001:
                    continue
                if inc.get("incident_datetime") != incident_datetime:
                    continue

                # Check transaction reference matching
                inc_tx = (inc.get("transaction_ref") or "").strip().lower()
                if clean_tx and inc_tx and clean_tx == inc_tx:
                    return dict(inc)
                elif not clean_tx and not inc_tx:
                    return dict(inc)
            return None

    def create_incident(self, incident_data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            user_id = incident_data.get("user_id", "")
            idempotency_key = incident_data.get("idempotency_key")

            # 1. Check idempotency key if provided
            if idempotency_key and idempotency_key.strip():
                clean_key = idempotency_key.strip()
                existing_id = self._idempotency_map.get((user_id, clean_key))
                if existing_id and existing_id in self._incidents:
                    existing_record = dict(self._incidents[existing_id])
                    existing_record["is_duplicate"] = True
                    return existing_record

            # 2. Check identical duplicate submission
            category = incident_data.get("category", "")
            provider = incident_data.get("provider", "")
            amount = float(incident_data.get("amount", 0.0))
            incident_datetime = incident_data.get("incident_datetime", "")
            tx_ref = incident_data.get("transaction_ref")

            duplicate_record = self.find_duplicate_incident(
                user_id=user_id,
                category=category,
                provider=provider,
                amount=amount,
                incident_datetime=incident_datetime,
                transaction_ref=tx_ref,
            )
            if duplicate_record:
                duplicate_record["is_duplicate"] = True
                return duplicate_record

            # 3. Create fresh legitimate incident
            record = dict(incident_data)
            if "id" not in record or not record["id"]:
                record["id"] = f"inc_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()
            record.setdefault("created_at", now)
            record.setdefault("updated_at", now)
            record.setdefault("status", "reported")
            record.setdefault("timeline", [
                {"timestamp": now, "event": "Incident reported by user", "status": record["status"]}
            ])
            record["is_duplicate"] = False
            self._incidents[record["id"]] = record

            if idempotency_key and idempotency_key.strip():
                self._idempotency_map[(user_id, idempotency_key.strip())] = record["id"]

            return dict(record)


    def get_incident_by_id(self, incident_id: str, user_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            record = self._incidents.get(incident_id)
            if record and record.get("user_id") == user_id:
                res = dict(record)
                if incident_id in self._drafts:
                    res["latest_complaint_draft"] = dict(self._drafts[incident_id])
                return res
            return None

    def list_incidents(
        self,
        user_id: str,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        with self._lock:
            results = []
            for inc in self._incidents.values():
                if inc.get("user_id") != user_id:
                    continue
                if category and (inc.get("category") or "").lower() != category.lower():
                    continue
                if status and (inc.get("status") or "").lower() != status.lower():
                    continue
                res = dict(inc)
                if inc["id"] in self._drafts:
                    res["latest_complaint_draft"] = dict(self._drafts[inc["id"]])
                results.append(res)

            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            total = len(results)
            paginated = results[offset : offset + limit]
            return paginated, total

    def update_incident(
        self, incident_id: str, user_id: str, update_fields: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        with self._lock:
            record = self._incidents.get(incident_id)
            if not record or record.get("user_id") != user_id:
                return None
            immutable = {"id", "user_id", "created_at"}
            now = datetime.now(timezone.utc).isoformat()

            old_status = record.get("status")
            new_status = update_fields.get("status")

            for k, v in update_fields.items():
                if k not in immutable:
                    record[k] = v
            record["updated_at"] = now

            if new_status and new_status != old_status:
                record.setdefault("timeline", []).append({
                    "timestamp": now,
                    "event": f"Status changed from {old_status} to {new_status}",
                    "status": new_status,
                })

            self._incidents[incident_id] = record
            res = dict(record)
            if incident_id in self._drafts:
                res["latest_complaint_draft"] = dict(self._drafts[incident_id])
            return res

    def save_complaint_draft(
        self, incident_id: str, user_id: str, draft_data: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        with self._lock:
            record = self._incidents.get(incident_id)
            if not record or record.get("user_id") != user_id:
                return None
            now = datetime.now(timezone.utc).isoformat()
            draft_record = dict(draft_data)
            draft_record["incident_id"] = incident_id
            draft_record["generated_at"] = now
            self._drafts[incident_id] = draft_record
            record.setdefault("timeline", []).append({
                "timestamp": now,
                "event": "Complaint draft generated",
                "status": record.get("status", "drafted"),
            })
            record["updated_at"] = now
            return dict(draft_record)

    def remove_evidence(
        self, incident_id: str, user_id: str, evidence_id: str
    ) -> tuple[bool, bool, Optional[dict[str, Any]]]:
        with self._lock:
            record = self._incidents.get(incident_id)
            if not record or record.get("user_id") != user_id:
                return False, False, None

            evidence_list = record.get("evidence_references", [])
            target = next((e for e in evidence_list if e.get("id") == evidence_id), None)
            if not target:
                return True, False, None

            # Remove target evidence
            record["evidence_references"] = [e for e in evidence_list if e.get("id") != evidence_id]
            now = datetime.now(timezone.utc).isoformat()
            record["updated_at"] = now
            record.setdefault("timeline", []).append({
                "timestamp": now,
                "event": f"Evidence removed: {target.get('title', evidence_id)} ({evidence_id})",
                "status": record.get("status", "reported"),
            })
            self._incidents[incident_id] = record
            res = dict(record)
            if incident_id in self._drafts:
                res["latest_complaint_draft"] = dict(self._drafts[incident_id])
            return True, True, res

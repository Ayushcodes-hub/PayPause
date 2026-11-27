"""Thread-safe In-Memory implementation of ExperimentRepositoryInterface.

Concurrency note:
    save_submission_atomic holds the repository lock for the entire
    check-and-insert operation, guaranteeing that concurrent callers with
    the same scoped_key produce exactly one accepted submission and one set
    of persisted events.

Production note:
    A SQL/NoSQL production adapter must implement save_submission_atomic
    using a unique database constraint on scoped_key (e.g.
    INSERT ... ON CONFLICT DO NOTHING) inside a serialisable transaction
    to achieve equivalent safety across multiple processes or replicas.
"""

import threading
from datetime import datetime, timezone
from typing import Optional, Any
import uuid

from backend.app.repositories.interfaces.experiment_repo import (
    ExperimentRepositoryInterface,
    AtomicSubmitResult,
)


class InMemoryExperimentRepository(ExperimentRepositoryInterface):
    """In-memory experiment store for assignments, submissions, and events."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Key: (participant_id, experiment_name) -> assignment record
        self._assignments: dict[tuple[str, str], dict[str, Any]] = {}
        # Key: scoped_key -> submission record
        self._submissions_by_scoped_key: dict[str, dict[str, Any]] = {}
        # Ordered list of all submission records
        self._submissions: list[dict[str, Any]] = []
        # Ordered list of all tracked events
        self._events: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Assignments
    # ------------------------------------------------------------------

    def get_assignment(self, participant_id: str, experiment_name: str) -> Optional[dict[str, Any]]:
        with self._lock:
            res = self._assignments.get((participant_id, experiment_name))
            return dict(res) if res else None

    def save_assignment(self, assignment_data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            key = (assignment_data["participant_id"], assignment_data["experiment_name"])
            now = datetime.now(timezone.utc).isoformat()
            record = dict(assignment_data)
            record.setdefault("assigned_at", now)
            self._assignments[key] = record
            return dict(record)

    # ------------------------------------------------------------------
    # Atomic submission + event persistence
    # ------------------------------------------------------------------

    def save_submission_atomic(
        self,
        scoped_key: str,
        submission_data: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> AtomicSubmitResult:
        """Check-and-insert under a single lock acquisition.

        If scoped_key is new: persist submission + all events, return is_new=True.
        If scoped_key already exists: return existing submission, is_new=False,
        empty events list — no new events are written.
        """
        with self._lock:
            existing = self._submissions_by_scoped_key.get(scoped_key)
            if existing:
                return AtomicSubmitResult(is_new=False, submission=dict(existing), events=[])

            # Build and store the submission record
            now = datetime.now(timezone.utc).isoformat()
            record = dict(submission_data)
            if not record.get("id"):
                record["id"] = f"subm_{uuid.uuid4().hex[:12]}"
            record.setdefault("submitted_at", now)
            self._submissions_by_scoped_key[scoped_key] = record
            self._submissions.append(record)

            # Persist all events atomically alongside the submission
            persisted_events: list[dict[str, Any]] = []
            for ev in events:
                ev_record = dict(ev)
                if "event_id" not in ev_record:
                    ev_record["event_id"] = f"evt_{uuid.uuid4().hex[:12]}"
                ev_record.setdefault("timestamp", now)
                self._events.append(ev_record)
                persisted_events.append(ev_record)

            return AtomicSubmitResult(is_new=True, submission=dict(record), events=persisted_events)

    # ------------------------------------------------------------------
    # Standalone event recording (used for other purposes if needed)
    # ------------------------------------------------------------------

    def record_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = dict(event_data)
            if "event_id" not in record:
                record["event_id"] = f"evt_{uuid.uuid4().hex[:12]}"
            record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            self._events.append(record)
            return dict(record)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_events(
        self,
        experiment_name: Optional[str] = None,
        participant_id: Optional[str] = None,
        metric_name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            results = []
            for evt in self._events:
                if experiment_name and evt.get("experiment_name") != experiment_name:
                    continue
                if participant_id and evt.get("participant_id") != participant_id:
                    continue
                if metric_name and evt.get("metric_name") != metric_name:
                    continue
                results.append(dict(evt))
            return results

    def get_experiment_stats(self, experiment_name: str) -> dict[str, Any]:
        with self._lock:
            matching_subms = [
                s for s in self._submissions
                if s.get("experiment_name") == experiment_name
            ]
            matching_events = [
                e for e in self._events
                if e.get("experiment_name") == experiment_name
            ]

            variants: dict[str, Any] = {}
            for s in matching_subms:
                var = s.get("variant", "unknown")
                if var not in variants:
                    variants[var] = {
                        "total_submissions": 0,
                        "correct_submissions": 0,
                        "accuracy_rate": 0.0,
                    }
                variants[var]["total_submissions"] += 1
                if s.get("is_correct"):
                    variants[var]["correct_submissions"] += 1

            for var, stats in variants.items():
                if stats["total_submissions"] > 0:
                    stats["accuracy_rate"] = round(
                        stats["correct_submissions"] / stats["total_submissions"], 4
                    )

            metric_counts: dict[str, int] = {}
            for e in matching_events:
                m = e.get("metric_name", "unknown")
                metric_counts[m] = metric_counts.get(m, 0) + 1

            return {
                "experiment_name": experiment_name,
                "total_assignments": len(
                    [a for k, a in self._assignments.items() if k[1] == experiment_name]
                ),
                "total_submissions": len(matching_subms),
                "variants": variants,
                "event_metrics": metric_counts,
            }

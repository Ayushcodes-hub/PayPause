"""Abstract Base Class defining the contract for Flagsmith experiment persistence."""

from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass, field


@dataclass
class AtomicSubmitResult:
    """Result returned by save_submission_atomic.

    Attributes:
        is_new: True if the submission was freshly accepted; False if a prior
                submission already existed under the scoped idempotency key.
        submission: The persisted submission record (new or existing).
        events: Local metric-event records persisted atomically alongside the
                submission. Empty list when is_new is False (duplicate).

    Production note:
        Implementations backed by a SQL/NoSQL database must enforce equivalent
        atomicity using unique constraints or database transactions to prevent
        race conditions across multiple processes or replicas.
    """

    is_new: bool
    submission: dict[str, Any]
    events: list[dict[str, Any]] = field(default_factory=list)


class ExperimentRepositoryInterface(ABC):
    """Repository interface for experiment assignment, submission, and event recording."""

    @abstractmethod
    def get_assignment(self, participant_id: str, experiment_name: str) -> Optional[dict[str, Any]]:
        """Retrieve stable assignment for participant to ensure consistent variant evaluation."""
        pass

    @abstractmethod
    def save_assignment(self, assignment_data: dict[str, Any]) -> dict[str, Any]:
        """Persist experiment variant assignment for a participant."""
        pass

    @abstractmethod
    def save_submission_atomic(
        self,
        scoped_key: str,
        submission_data: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> AtomicSubmitResult:
        """Atomically save a submission and its events if the scoped key is new.

        The scoped key is composed of participant_id + scenario_id + raw
        idempotency key so that two different participants sharing the same
        raw key cannot retrieve each other's data.

        If scoped_key already exists, return the previously stored submission
        and an empty events list (is_new=False). Otherwise persist the
        submission and all provided events together and return them (is_new=True).

        In-memory implementations must hold their lock for the full duration of
        the check-and-insert so that concurrent callers cannot both see
        is_new=True for the same key.

        Production note:
            SQL adapters must implement this using a unique constraint on
            scoped_key combined with an INSERT ... ON CONFLICT DO NOTHING
            (or equivalent) inside a serialisable transaction.
        """
        pass

    @abstractmethod
    def record_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Persist a single experiment metric event (used for standalone event recording)."""
        pass

    @abstractmethod
    def get_events(
        self,
        experiment_name: Optional[str] = None,
        participant_id: Optional[str] = None,
        metric_name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve logged experiment events for reporting and verification."""
        pass

    @abstractmethod
    def get_experiment_stats(self, experiment_name: str) -> dict[str, Any]:
        """Return aggregated experiment submission stats by variant."""
        pass

"""Abstract Base Class defining the contract for Recovery Desk incident persistence."""

from abc import ABC, abstractmethod
from typing import Optional, Any


class IncidentRepositoryInterface(ABC):
    """Repository interface for Recovery Desk incidents & complaint drafts."""

    @abstractmethod
    def create_incident(self, incident_data: dict[str, Any]) -> dict[str, Any]:
        """Persist a new recovery incident and return the created record."""
        pass

    @abstractmethod
    def get_incident_by_id(self, incident_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """Retrieve an incident by ID ensuring authenticated user ownership."""
        pass

    @abstractmethod
    def list_incidents(
        self,
        user_id: str,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return filtered and paginated recovery incidents for a user."""
        pass

    @abstractmethod
    def update_incident(
        self, incident_id: str, user_id: str, update_fields: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Update mutable fields of an incident for the authorized user."""
        pass

    @abstractmethod
    def save_complaint_draft(
        self, incident_id: str, user_id: str, draft_data: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Attach or save a generated complaint draft to the incident."""
        pass

    @abstractmethod
    def remove_evidence(
        self, incident_id: str, user_id: str, evidence_id: str
    ) -> tuple[bool, bool, Optional[dict[str, Any]]]:
        """Safely remove an evidence item by its ID.

        Returns:
            (incident_found: bool, evidence_found: bool, updated_incident: Optional[dict])
        """
        pass

    @abstractmethod
    def find_duplicate_incident(
        self,
        user_id: str,
        category: str,
        provider: str,
        amount: float,
        incident_datetime: str,
        transaction_ref: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Check for an existing identical incident to protect against accidental duplicate creation."""
        pass

    @abstractmethod
    def get_incident_by_idempotency_key(
        self, idempotency_key: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        """Retrieve an incident previously created with a specific idempotency key."""
        pass

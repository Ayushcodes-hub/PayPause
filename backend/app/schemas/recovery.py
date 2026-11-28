"""Pydantic schemas for Recovery Desk incident management and complaint assistance."""

from datetime import datetime
from typing import Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator


IncidentCategory = Literal[
    "suspicious_upi",
    "failed_payment",
    "suspected_fraud",
    "unauthorised_transaction",
    "duplicate_payment",
    "delayed_refund",
    "other_dispute",
]

IncidentStatus = Literal[
    "reported",
    "under_investigation",
    "grievance_filed",
    "resolved",
    "closed",
]

CredentialDisclosureAnswer = Literal[
    "yes",
    "no",
    "not_sure",
    "prefer_not_to_say",
]

DISALLOWED_PLACEHOLDERS = {
    "string",
    "placeholder",
    "dummy",
    "test",
    "n/a",
    "na",
    "null",
    "none",
    "undefined",
}


class EvidenceItem(BaseModel):
    id: str = Field(..., min_length=2, max_length=64, description="Evidence reference identifier")
    title: str = Field(..., min_length=3, max_length=200, description="Brief label (e.g. Screenshot of UPI QR, Bank Debit SMS)")
    description: Optional[str] = Field(default=None, max_length=1000)
    file_reference: Optional[str] = Field(default=None, max_length=255)
    uploaded_at: Optional[str] = Field(default=None, description="Upload timestamp in ISO-8601 format")

    @field_validator("id", "title")
    @classmethod
    def validate_required_not_placeholder(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only.")
        clean = v.strip()
        if clean.lower() in DISALLOWED_PLACEHOLDERS:
            raise ValueError(f"Placeholder value '{clean}' is not allowed.")
        return clean

    @field_validator("file_reference", "description")
    @classmethod
    def validate_optional_not_placeholder(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not clean:
                return None
            if clean.lower() in DISALLOWED_PLACEHOLDERS:
                raise ValueError(f"Placeholder value '{clean}' is not allowed.")
            return clean
        return None

    @field_validator("uploaded_at")
    @classmethod
    def validate_uploaded_at_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if clean.lower() in DISALLOWED_PLACEHOLDERS:
                raise ValueError(f"Placeholder value '{clean}' is not allowed for uploaded_at.")
            try:
                # Validate ISO datetime format (e.g. 2026-11-20T14:30:00 or 2026-11-20T14:30:00Z)
                datetime.fromisoformat(clean.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError(
                    f"uploaded_at '{clean}' is not a valid ISO-8601 date/time (e.g. 2026-11-20T14:30:00Z)"
                )
            return clean
        return None



class IncidentCreate(BaseModel):
    category: IncidentCategory = Field(..., description="Category of the incident")
    incident_datetime: str = Field(..., description="Date and time of incident occurrence (ISO format)")
    provider: str = Field(..., min_length=2, max_length=50, description="Payment provider (e.g. GPay, PhonePe, SBI)")
    transaction_ref: Optional[str] = Field(default=None, max_length=64, description="Transaction reference / UTR")
    amount: float = Field(..., gt=0.0, description="Disputed amount")
    currency: str = Field(default="INR", max_length=5)
    description: str = Field(..., min_length=10, max_length=2000, description="Detailed account of what occurred")
    evidence_references: list[EvidenceItem] = Field(default_factory=list)
    follow_up_date: Optional[str] = Field(default=None, description="Expected next action date (YYYY-MM-DD)")
    credentials_disclosed: Optional[CredentialDisclosureAnswer] = Field(
        default=None,
        description="User-confirmed credential disclosure answer: yes, no, not_sure, prefer_not_to_say",
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Optional client-provided idempotency key to prevent duplicate creation on network retries",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider_not_placeholder(cls, v: str) -> str:
        clean = v.strip()
        if clean.lower() in DISALLOWED_PLACEHOLDERS:
            raise ValueError(f"Placeholder value '{clean}' is not allowed for provider.")
        return clean

    @field_validator("transaction_ref")
    @classmethod
    def validate_tx_ref_not_placeholder(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not clean:
                return None
            if clean.lower() in DISALLOWED_PLACEHOLDERS:
                raise ValueError(f"Placeholder value '{clean}' is not allowed for transaction_ref.")
            return clean
        return None

    @field_validator("credentials_disclosed", mode="before")
    @classmethod
    def normalize_credentials_disclosed(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            clean = v.strip().lower().replace(" ", "_")
            if clean in ("yes", "y"):
                return "yes"
            if clean in ("no", "n"):
                return "no"
            if clean in ("not_sure", "unsure"):
                return "not_sure"
            if clean in ("prefer_not_to_say", "prefer_not_to_say_"):
                return "prefer_not_to_say"
            return clean
        return v

    @field_validator("incident_datetime")
    @classmethod
    def validate_dt(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("incident_datetime must be in ISO format (e.g. 2026-11-20T14:30:00)")
        return v


class IncidentUpdate(BaseModel):
    status: Optional[IncidentStatus] = None
    description: Optional[str] = Field(default=None, min_length=10, max_length=2000)
    follow_up_date: Optional[str] = None
    credentials_disclosed: Optional[CredentialDisclosureAnswer] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    add_evidence: Optional[list[EvidenceItem]] = None

    @field_validator("credentials_disclosed", mode="before")
    @classmethod
    def normalize_credentials_disclosed(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            clean = v.strip().lower().replace(" ", "_")
            if clean in ("yes", "y"):
                return "yes"
            if clean in ("no", "n"):
                return "no"
            if clean in ("not_sure", "unsure"):
                return "not_sure"
            if clean in ("prefer_not_to_say", "prefer_not_to_say_"):
                return "prefer_not_to_say"
            return clean
        return v



class TimelineEvent(BaseModel):
    timestamp: str
    event: str
    status: str


class EvidenceChecklistItem(BaseModel):
    item_name: str
    is_mandatory: bool
    description: str
    how_to_obtain: str


class ComplaintDraftResponse(BaseModel):
    incident_id: str
    is_draft: bool = True
    draft_title: str
    disclaimer: str
    formal_letter_body: str
    recommended_evidence_checklist: list[EvidenceChecklistItem]
    statutory_guidance: dict[str, Any]
    generated_at: str


class IncidentResponse(BaseModel):
    id: str
    user_id: str
    category: str
    incident_datetime: str
    provider: str
    transaction_ref: Optional[str] = None
    amount: float
    currency: str
    description: str
    evidence_references: list[dict[str, Any]]
    status: str
    follow_up_date: Optional[str] = None
    credentials_disclosed: Optional[str] = None
    is_duplicate: bool = Field(default=False, description="Whether this response returned an existing incident via idempotency")
    timeline: list[dict[str, Any]]
    latest_complaint_draft: Optional[dict[str, Any]] = None
    evidence_checklist: list[EvidenceChecklistItem] = Field(default_factory=list)
    created_at: str
    updated_at: str


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    total: int
    limit: int
    offset: int

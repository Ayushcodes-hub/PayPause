"""Pydantic schemas for Flagsmith experiment management."""

from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


class ScenarioOption(BaseModel):
    id: str = Field(..., description="Option identifier")
    label: str = Field(..., description="Readable option text")


class VerificationActionOption(BaseModel):
    id: str = Field(..., description="Action identifier")
    label: str = Field(..., description="Readable action text")


class ExperimentScenarioResponse(BaseModel):
    """Public scenario schema without canonical answers or evaluation rules."""

    id: str = Field(..., description="Unique scenario identifier")
    title: str = Field(..., description="Scenario title")
    category: str = Field(..., description="Scenario category")
    amount: float = Field(..., description="Transaction amount involved")
    context: str = Field(..., description="Description of the payment scenario")
    options: list[ScenarioOption] = Field(..., description="Answer choices presented to participant")
    verification_actions: list[VerificationActionOption] = Field(
        default_factory=list, description="Verification action choices"
    )


class ExperimentAssignRequest(BaseModel):
    """Request to assign or retrieve participant's experiment variant."""

    participant_id: str = Field(
        ...,
        min_length=3,
        max_length=128,
        description="Stable participant or session identifier",
    )
    experiment_name: str = Field(
        default="PayPause Payment Intelligence Experience",
        max_length=200,
        description="Name of the experiment",
    )
    feature_name: str = Field(
        default="payment_intelligence_experience",
        max_length=200,
        description="Flagsmith feature flag name",
    )
    traits: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional user traits for Flagsmith targeting (max 20 keys)",
    )

    @field_validator("participant_id")
    @classmethod
    def participant_id_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("participant_id must not be blank or whitespace-only")
        return v

    @field_validator("traits")
    @classmethod
    def traits_bounded(cls, v: Optional[dict]) -> Optional[dict]:
        if v is not None and len(v) > 20:
            raise ValueError("traits must not exceed 20 keys")
        return v


class ExperimentAssignResponse(BaseModel):
    """Response containing assigned variant and experiment metadata."""

    participant_id: str
    experiment_name: str
    feature_name: str
    variant: str = Field(..., description="Assigned variant (risk_score_first or payment_passport_first)")
    source: str = Field(..., description="Evaluation source: flagsmith_real or deterministic_fallback")
    is_live_flagsmith: bool = Field(..., description="Whether assigned via active Flagsmith API")
    assigned_at: str
    error: Optional[str] = None


class ExperimentSubmitRequest(BaseModel):
    """Submission payload for an experiment scenario attempt."""

    participant_id: str = Field(
        ...,
        min_length=3,
        max_length=128,
        description="Participant identifier",
    )
    scenario_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="ID of the scenario attempted",
    )
    selected_answer: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="ID of selected answer option",
    )
    selected_action: Optional[str] = Field(
        default=None,
        max_length=128,
        description="ID of selected verification action",
    )
    start_timestamp: Optional[str] = Field(
        default=None,
        description="ISO timestamp when participant began scenario",
    )
    abandoned: bool = Field(
        default=False,
        description="Whether participant abandoned verification before completing",
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Client-provided idempotency key to prevent duplicate submissions",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional client telemetry (max 20 keys)",
    )

    @field_validator("participant_id")
    @classmethod
    def participant_id_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("participant_id must not be blank or whitespace-only")
        return v

    @field_validator("scenario_id")
    @classmethod
    def scenario_id_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("scenario_id must not be blank or whitespace-only")
        return v

    @field_validator("selected_answer")
    @classmethod
    def selected_answer_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("selected_answer must not be blank or whitespace-only")
        return v

    @field_validator("metadata")
    @classmethod
    def metadata_bounded(cls, v: Optional[dict]) -> Optional[dict]:
        if v is not None and len(v) > 20:
            raise ValueError("metadata must not exceed 20 keys")
        return v


class ExperimentSubmitResponse(BaseModel):
    """Backend-validated result of the experiment submission."""

    submission_id: str
    participant_id: str
    scenario_id: str
    variant: str
    is_correct: bool = Field(..., description="Backend validated correctness")
    score: float = Field(..., ge=0.0, le=1.0)
    feedback: str = Field(..., description="Educational explanation for the user")
    is_duplicate: bool = Field(
        default=False, description="Whether this submission was already recorded via idempotency"
    )
    events_recorded: list[str] = Field(
        default_factory=list, description="List of metric events recorded during this submission"
    )
    submitted_at: str


class ExperimentStatusResponse(BaseModel):
    """Aggregated status and metrics for the experiment.

    Production deployment note:
        This endpoint exposes aggregate telemetry. It does not expose individual
        participant records. Production deployments should evaluate whether
        operator/admin authorization is required before exposing this endpoint
        publicly.
    """

    experiment_name: str
    feature_name: str
    is_flagsmith_configured: bool
    total_assignments: int
    total_submissions: int
    variant_stats: dict[str, Any]
    event_counts: dict[str, int]
    primary_metric: str = "risk_check_correctly_completed"
    secondary_metrics: list[str] = [
        "risk_signal_understood",
        "verification_action_selected",
        "verification_abandoned",
    ]

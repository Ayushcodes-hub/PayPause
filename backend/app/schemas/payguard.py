
from decimal import Decimal
from typing import Annotated, Self
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class PaymentInputType(str, Enum):
    UPI = "upi"
    URL = "url"
    BOTH = "both"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PayGuardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_type: PaymentInputType

    upi_id: Annotated[str | None, Field(max_length=320)] = None
    payment_url: Annotated[str | None, Field(max_length=2048)] = None

    recipient_name: Annotated[
        str | None,
        Field(max_length=120),
    ] = None

    amount: Annotated[
        Decimal | None,
        Field(
            gt=Decimal("0"),
            le=Decimal("10000000"),
            max_digits=12,
            decimal_places=2,
        ),
    ] = None

    @field_validator("upi_id", "recipient_name")
    @classmethod
    def normalize_optional_strings(cls, value: str | None):
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty or whitespace.")

        return value

    @field_validator("payment_url")
    @classmethod
    def validate_payment_url_presence(cls, value: str | None):
        if value is None:
            return None

        if not value.strip():
            raise ValueError("Payment URL cannot be empty or whitespace.")

        # Preserve the original URL.
        # The URL analyzer handles whitespace and control characters.
        return value

    @model_validator(mode="after")
    def validate_input_combination(self) -> Self:
        if self.input_type == PaymentInputType.UPI:
            if not self.upi_id:
                raise ValueError("upi_id is required for UPI analysis.")

            if self.payment_url is not None:
                raise ValueError(
                    "payment_url is not allowed for UPI-only analysis."
                )

        elif self.input_type == PaymentInputType.URL:
            if not self.payment_url:
                raise ValueError("payment_url is required for URL analysis.")

            if self.upi_id is not None:
                raise ValueError(
                    "upi_id is not allowed for URL-only analysis."
                )

        elif self.input_type == PaymentInputType.BOTH:
            if not self.upi_id or not self.payment_url:
                raise ValueError(
                    "Both upi_id and payment_url are required."
                )

        return self


class RiskEvidence(BaseModel):
    code: str
    title: str
    description: str
    severity: EvidenceSeverity
    points: int = Field(ge=0, le=100)


class RiskRecommendation(BaseModel):
    priority: EvidenceSeverity
    action: str
    reason: str


class PayGuardAssessment(BaseModel):
    assessment_id: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel

    input_type: PaymentInputType

    evidence: list[RiskEvidence] = Field(default_factory=list)
    recommendations: list[RiskRecommendation] = Field(
        default_factory=list
    )

    coverage: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    disclaimer: str = (
        "This assessment is an automated risk screening, "
        "not a guarantee that a payment is safe or fraudulent."
    )

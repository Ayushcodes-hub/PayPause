
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class UPIEvidence:
    code: str
    title: str
    description: str
    severity: str
    points: int


@dataclass(frozen=True)
class UPIAnalysis:
    is_valid_format: bool
    normalized_upi_id: str
    risk_points: int
    evidence: tuple[UPIEvidence, ...]
    coverage: tuple[str, ...]
    limitations: tuple[str, ...]


# Conservative syntax checks. These rules validate structure,
# not whether the payment address actually exists.
UPI_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{1,255}@[A-Za-z0-9][A-Za-z0-9.-]{1,63}$"
)

SUSPICIOUS_KEYWORDS = {
    "refund",
    "reward",
    "cashback",
    "lottery",
    "prize",
    "winner",
    "claim",
    "support",
    "helpdesk",
    "kyc",
    "verify",
    "security",
}


def analyze_upi_id(upi_id: str) -> UPIAnalysis:
    """
    Perform deterministic, offline UPI ID analysis.

    This function does not contact payment networks,
    verify account ownership, or establish fraud.
    """

    if not isinstance(upi_id, str):
        raise TypeError("UPI ID must be a string.")

    normalized = upi_id.strip()

    if not normalized:
        raise ValueError("UPI ID cannot be empty.")

    evidence: list[UPIEvidence] = []

    def add_evidence(
        code: str,
        title: str,
        description: str,
        severity: str,
        points: int,
    ) -> None:
        evidence.append(
            UPIEvidence(
                code=code,
                title=title,
                description=description,
                severity=severity,
                points=points,
            )
        )

    # 1. Basic format validation.
    is_valid = bool(UPI_PATTERN.fullmatch(normalized))

    if not is_valid:
        add_evidence(
            code="INVALID_UPI_FORMAT",
            title="Unrecognized UPI ID format",
            description=(
                "The supplied identifier does not match "
                "the accepted structural format."
            ),
            severity="medium",
            points=25,
        )

    # 2. Multiple separators can indicate an unusual identifier.
    if normalized.count("@") != 1:
        add_evidence(
            code="UNUSUAL_SEPARATOR_COUNT",
            title="Unusual UPI separator structure",
            description=(
                "A standard UPI ID should contain exactly "
                "one @ separator."
            ),
            severity="medium",
            points=20,
        )

    # 3. Suspicious keywords are weak indicators only.
    local_part = normalized.split("@", 1)[0].lower()

    matched_keywords = sorted(
        keyword
        for keyword in SUSPICIOUS_KEYWORDS
        if keyword in local_part
    )

    if matched_keywords:
        add_evidence(
            code="SUSPICIOUS_KEYWORD",
            title="Potentially misleading payment identifier",
            description=(
                "The identifier contains terms sometimes "
                "used in deceptive payment requests: "
                + ", ".join(matched_keywords)
                + ". This alone does not establish fraud."
            ),
            severity="low",
            points=10,
        )

    # 4. Excessive punctuation can reduce readability.
    if re.search(r"[._-]{3,}", local_part):
        add_evidence(
            code="EXCESSIVE_PUNCTUATION",
            title="Unusual identifier punctuation",
            description=(
                "The identifier contains repeated punctuation "
                "that may make it harder to read accurately."
            ),
            severity="low",
            points=5,
        )

    # 5. Avoid duplicate evidence codes.
    unique_evidence = {
        item.code: item for item in evidence
    }

    final_evidence = tuple(unique_evidence.values())

    # This is a heuristic indicator score, not a fraud probability.
    risk_points = min(
        100,
        sum(item.points for item in final_evidence),
    )

    return UPIAnalysis(
        is_valid_format=is_valid,
        normalized_upi_id=normalized,
        risk_points=risk_points,
        evidence=final_evidence,
        coverage=(
            "UPI identifier structural validation",
            "Basic suspicious keyword screening",
            "Identifier readability checks",
        ),
        limitations=(
            "UPI account ownership is not verified.",
            "Payment network reputation is not checked.",
            "A valid format does not guarantee payment safety.",
            "Keyword matches are weak indicators, not proof of fraud.",
        ),
    )


from collections import defaultdict
from uuid import uuid4

from app.schemas.payguard import (
    EvidenceSeverity,
    PaymentInputType,
    PayGuardAssessment,
    RiskEvidence,
    RiskLevel,
)

from app.services.payguard.upi_analyzer import UPIAnalysis
from app.services.payguard.url_analyzer import URLAnalysis
from app.services.payguard.recommendations import generate_recommendations


EVIDENCE_GROUPS = {
    "INVALID_UPI_FORMAT": "upi_structure",
    "UNUSUAL_SEPARATOR_COUNT": "upi_structure",
    "SUSPICIOUS_KEYWORD": "upi_identity",
    "EXCESSIVE_PUNCTUATION": "upi_readability",
    "INVALID_URL_STRUCTURE": "url_structure",
    "INVALID_HOSTNAME": "url_structure",
    "URL_INVALID_CHARACTERS": "url_structure",
    "INSECURE_HTTP": "url_transport",
    "EMBEDDED_CREDENTIALS": "url_obfuscation",
    "IP_ADDRESS_HOST": "url_destination",
    "PUNYCODE_DOMAIN": "url_destination",
    "URL_SHORTENER": "url_destination",
    "UNUSUAL_PORT": "url_port",
    "SUSPICIOUS_HOST_KEYWORD": "url_hostname",
    "DEEP_SUBDOMAIN": "url_hostname",
}


SEVERITY_ORDER = {
    EvidenceSeverity.INFO: 0,
    EvidenceSeverity.LOW: 1,
    EvidenceSeverity.MEDIUM: 2,
    EvidenceSeverity.HIGH: 3,
    EvidenceSeverity.CRITICAL: 4,
}


def classify_risk(score: int) -> RiskLevel:
    if score < 20:
        return RiskLevel.LOW
    if score < 40:
        return RiskLevel.MODERATE
    if score < 70:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def calculate_risk_score(
    evidence: list[RiskEvidence],
) -> int:
    grouped_points: dict[str, int] = defaultdict(int)

    for item in evidence:
        group = EVIDENCE_GROUPS.get(
            item.code,
            f"independent:{item.code}",
        )

        grouped_points[group] = max(
            grouped_points[group],
            item.points,
        )

    return min(100, sum(grouped_points.values()))


def collect_evidence(
    upi_analysis: UPIAnalysis | None = None,
    url_analysis: URLAnalysis | None = None,
) -> list[RiskEvidence]:
    collected: dict[str, RiskEvidence] = {}

    analyses = [
        analysis
        for analysis in (upi_analysis, url_analysis)
        if analysis is not None
    ]

    for analysis in analyses:
        for item in analysis.evidence:
            candidate = RiskEvidence(
                code=item.code,
                title=item.title,
                description=item.description,
                severity=EvidenceSeverity(item.severity),
                points=item.points,
            )

            existing = collected.get(item.code)

            if existing is None:
                collected[item.code] = candidate
                continue

            candidate_strength = (
                candidate.points,
                SEVERITY_ORDER[candidate.severity],
            )

            existing_strength = (
                existing.points,
                SEVERITY_ORDER[existing.severity],
            )

            if candidate_strength > existing_strength:
                collected[item.code] = candidate

    return list(collected.values())


def collect_coverage(
    upi_analysis: UPIAnalysis | None = None,
    url_analysis: URLAnalysis | None = None,
) -> list[str]:
    coverage: list[str] = []

    for analysis in (upi_analysis, url_analysis):
        if analysis is not None:
            coverage.extend(analysis.coverage)

    return list(dict.fromkeys(coverage))


def collect_limitations(
    upi_analysis: UPIAnalysis | None = None,
    url_analysis: URLAnalysis | None = None,
) -> list[str]:
    limitations: list[str] = []

    for analysis in (upi_analysis, url_analysis):
        if analysis is not None:
            limitations.extend(analysis.limitations)

    return list(dict.fromkeys(limitations))


def build_risk_assessment(
    input_type: PaymentInputType,
    upi_analysis: UPIAnalysis | None = None,
    url_analysis: URLAnalysis | None = None,
) -> PayGuardAssessment:

    if not isinstance(input_type, PaymentInputType):
        raise TypeError(
            "input_type must be a valid PaymentInputType."
        )

    if input_type == PaymentInputType.UPI:
        if upi_analysis is None or url_analysis is not None:
            raise ValueError(
                "UPI-only assessment requires only UPI analysis."
            )

    elif input_type == PaymentInputType.URL:
        if url_analysis is None or upi_analysis is not None:
            raise ValueError(
                "URL-only assessment requires only URL analysis."
            )

    elif input_type == PaymentInputType.BOTH:
        if upi_analysis is None or url_analysis is None:
            raise ValueError(
                "Combined assessment requires both analyses."
            )

    evidence = collect_evidence(
        upi_analysis=upi_analysis,
        url_analysis=url_analysis,
    )

    risk_score = calculate_risk_score(evidence)

    recommendations = generate_recommendations(evidence)

    return PayGuardAssessment(
        assessment_id=str(uuid4()),
        risk_score=risk_score,
        risk_level=classify_risk(risk_score),
        input_type=input_type,
        evidence=evidence,
        recommendations=recommendations,
        coverage=collect_coverage(
            upi_analysis=upi_analysis,
            url_analysis=url_analysis,
        ),
        limitations=collect_limitations(
            upi_analysis=upi_analysis,
            url_analysis=url_analysis,
        ),
    )

from types import SimpleNamespace

import pytest

from app.schemas.payguard import (
    EvidenceSeverity,
    PaymentInputType,
    RiskEvidence,
    RiskLevel,
)

from app.services.payguard.risk_engine import (
    EVIDENCE_GROUPS,
    build_risk_assessment,
    calculate_risk_score,
    classify_risk,
    collect_evidence,
)

from app.services.payguard.recommendations import (
    RECOMMENDATION_RULES,
    generate_recommendations,
)


def make_evidence(
    code: str,
    points: int,
    severity: EvidenceSeverity = EvidenceSeverity.MEDIUM,
) -> RiskEvidence:
    return RiskEvidence(
        code=code,
        title=f"Test evidence: {code}",
        description="Evidence created for testing.",
        severity=severity,
        points=points,
    )


def test_every_registered_evidence_code_has_recommendation():
    assert set(EVIDENCE_GROUPS) == set(RECOMMENDATION_RULES)


def test_related_evidence_uses_maximum_points():
    evidence = [
        make_evidence("INVALID_UPI_FORMAT", 25),
        make_evidence("UNUSUAL_SEPARATOR_COUNT", 20),
    ]

    assert calculate_risk_score(evidence) == 25


def test_independent_evidence_groups_are_added():
    evidence = [
        make_evidence("INVALID_UPI_FORMAT", 25),
        make_evidence("SUSPICIOUS_KEYWORD", 10),
        make_evidence("INSECURE_HTTP", 20),
    ]

    assert calculate_risk_score(evidence) == 55


def test_unknown_evidence_codes_are_independent():
    evidence = [
        make_evidence("UNKNOWN_TEST_A", 15),
        make_evidence("UNKNOWN_TEST_B", 20),
    ]

    assert calculate_risk_score(evidence) == 35


def test_risk_score_is_capped_at_100():
    evidence = [
        make_evidence("UNKNOWN_TEST_A", 60),
        make_evidence("UNKNOWN_TEST_B", 70),
    ]

    assert calculate_risk_score(evidence) == 100


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0, RiskLevel.LOW),
        (19, RiskLevel.LOW),
        (20, RiskLevel.MODERATE),
        (39, RiskLevel.MODERATE),
        (40, RiskLevel.HIGH),
        (69, RiskLevel.HIGH),
        (70, RiskLevel.CRITICAL),
        (100, RiskLevel.CRITICAL),
    ],
)
def test_risk_classification_boundaries(score, expected):
    assert classify_risk(score) == expected


def test_unknown_evidence_does_not_disappear_from_recommendation_pipeline():
    evidence = make_evidence("UNKNOWN_TEST_CODE", 20)

    recommendations = generate_recommendations([evidence])

    assert len(recommendations) == 1
    assert recommendations[0].priority == EvidenceSeverity.INFO


def test_recommendations_are_sorted_by_priority():
    evidence = [
        make_evidence(
            "EXCESSIVE_PUNCTUATION",
            5,
            EvidenceSeverity.LOW,
        ),
        make_evidence(
            "INVALID_URL_STRUCTURE",
            100,
            EvidenceSeverity.HIGH,
        ),
        make_evidence(
            "URL_SHORTENER",
            15,
            EvidenceSeverity.MEDIUM,
        ),
    ]

    recommendations = generate_recommendations(evidence)

    priorities = [item.priority for item in recommendations]

    assert priorities == [
        EvidenceSeverity.CRITICAL,
        EvidenceSeverity.MEDIUM,
        EvidenceSeverity.LOW,
    ]


def test_empty_evidence_generates_general_verification_guidance():
    recommendations = generate_recommendations([])

    assert len(recommendations) == 1
    assert recommendations[0].priority == EvidenceSeverity.INFO
    assert "recipient" in recommendations[0].action.lower()
    assert "amount" in recommendations[0].action.lower()


def test_risk_engine_rejects_unsupported_input_type():
    with pytest.raises(TypeError):
        build_risk_assessment("unsupported")


def test_collect_evidence_preserves_stronger_duplicate_finding():
    weaker = SimpleNamespace(
        code="TEST_DUPLICATE",
        title="Weaker finding",
        description="Lower severity evidence.",
        severity="low",
        points=10,
    )

    stronger = SimpleNamespace(
        code="TEST_DUPLICATE",
        title="Stronger finding",
        description="Higher points evidence.",
        severity="high",
        points=30,
    )

    result = collect_evidence(
        upi_analysis=SimpleNamespace(evidence=(weaker,)),
        url_analysis=SimpleNamespace(evidence=(stronger,)),
    )

    assert len(result) == 1
    assert result[0].title == "Stronger finding"
    assert result[0].points == 30
    assert result[0].severity == EvidenceSeverity.HIGH


def test_collect_evidence_uses_severity_as_tie_breaker():
    weaker = SimpleNamespace(
        code="TEST_DUPLICATE",
        title="Lower severity finding",
        description="Lower severity.",
        severity="medium",
        points=20,
    )

    stronger = SimpleNamespace(
        code="TEST_DUPLICATE",
        title="Higher severity finding",
        description="Higher severity.",
        severity="critical",
        points=20,
    )

    result = collect_evidence(
        upi_analysis=SimpleNamespace(evidence=(weaker,)),
        url_analysis=SimpleNamespace(evidence=(stronger,)),
    )

    assert len(result) == 1
    assert result[0].title == "Higher severity finding"
    assert result[0].severity == EvidenceSeverity.CRITICAL

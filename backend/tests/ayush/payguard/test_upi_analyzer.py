
import pytest

from app.services.payguard.upi_analyzer import analyze_upi_id


def test_valid_merchant_has_no_risk_indicators():
    result = analyze_upi_id("merchant@bank")

    assert result.is_valid_format is True
    assert result.risk_points == 0
    assert result.evidence == ()


@pytest.mark.parametrize(
    "upi_id",
    [
        "refundhelp@bank",
        "lotterywinner@bank",
    ],
)
def test_suspicious_keywords_generate_weak_evidence(upi_id):
    result = analyze_upi_id(upi_id)

    assert result.is_valid_format is True
    assert result.risk_points == 10
    assert any(
        item.code == "SUSPICIOUS_KEYWORD"
        for item in result.evidence
    )


@pytest.mark.parametrize(
    "upi_id",
    [
        "merchantbank",
        "merchant@@bank",
    ],
)
def test_malformed_identifiers_are_flagged(upi_id):
    result = analyze_upi_id(upi_id)

    assert result.is_valid_format is False
    assert result.risk_points == 45


def test_excessive_punctuation_generates_evidence():
    result = analyze_upi_id("merchant...help@bank")

    assert result.is_valid_format is True
    assert result.risk_points == 5
    assert result.evidence[0].code == "EXCESSIVE_PUNCTUATION"


def test_whitespace_is_normalized():
    result = analyze_upi_id("  merchant@bank  ")

    assert result.normalized_upi_id == "merchant@bank"
    assert result.is_valid_format is True


@pytest.mark.parametrize("upi_id", ["", "   "])
def test_empty_identifiers_are_rejected(upi_id):
    with pytest.raises(ValueError):
        analyze_upi_id(upi_id)


@pytest.mark.parametrize("upi_id", [12345, None, [], {}])
def test_non_string_identifiers_are_rejected(upi_id):
    with pytest.raises(TypeError):
        analyze_upi_id(upi_id)


def test_analysis_includes_limitations():
    result = analyze_upi_id("merchant@bank")

    assert len(result.limitations) >= 1
    assert any(
        "ownership" in limitation.lower()
        for limitation in result.limitations
    )


def test_risk_points_never_exceed_100():
    result = analyze_upi_id("merchant@@bank")

    assert 0 <= result.risk_points <= 100

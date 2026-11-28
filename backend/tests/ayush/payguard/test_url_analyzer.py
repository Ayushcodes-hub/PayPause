
import pytest

from app.services.payguard.url_analyzer import analyze_payment_url


def test_normal_https_url():
    result = analyze_payment_url("https://example.com/pay")

    assert result.is_valid_url is True
    assert result.hostname == "example.com"
    assert result.risk_points == 0
    assert result.evidence == ()


def test_http_url_generates_evidence():
    result = analyze_payment_url("http://example.com/pay")

    assert result.is_valid_url is True
    assert any(
        item.code == "INSECURE_HTTP"
        for item in result.evidence
    )


def test_ip_address_host_is_detected():
    result = analyze_payment_url("http://192.0.2.1/pay")

    assert any(
        item.code == "IP_ADDRESS_HOST"
        for item in result.evidence
    )


def test_embedded_credentials_are_detected():
    result = analyze_payment_url(
        "https://user:password@example.com/pay"
    )

    assert any(
        item.code == "EMBEDDED_CREDENTIALS"
        for item in result.evidence
    )


def test_punycode_domain_is_detected():
    result = analyze_payment_url(
        "https://xn--e1afmkfd.xn--p1ai/"
    )

    assert any(
        item.code == "PUNYCODE_DOMAIN"
        for item in result.evidence
    )


def test_known_url_shortener_is_detected():
    result = analyze_payment_url("https://bit.ly/example")

    assert any(
        item.code == "URL_SHORTENER"
        for item in result.evidence
    )


def test_unusual_port_is_detected():
    result = analyze_payment_url("https://example.com:8443/pay")

    assert any(
        item.code == "UNUSUAL_PORT"
        for item in result.evidence
    )


def test_suspicious_hostname_keyword_is_detected():
    result = analyze_payment_url(
        "https://secure-login.example.com/"
    )

    assert any(
        item.code == "SUSPICIOUS_HOST_KEYWORD"
        for item in result.evidence
    )


def test_deep_subdomain_is_detected():
    result = analyze_payment_url(
        "https://a.b.c.d.example.com/"
    )

    assert any(
        item.code == "DEEP_SUBDOMAIN"
        for item in result.evidence
    )


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "ftp://example.com/file",
        "https:///missing-host",
        "https://example.com:99999/pay",
        "not-a-url",
    ],
)
def test_malformed_urls_are_rejected(url):
    result = analyze_payment_url(url)

    assert result.is_valid_url is False
    assert result.risk_points == 100


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/pay now",
        "https://example.com/pay\n",
        "https://example.com\\@evil.com",
    ],
)
def test_whitespace_and_backslashes_are_rejected(url):
    result = analyze_payment_url(url)

    assert result.is_valid_url is False
    assert any(
        item.code == "URL_INVALID_CHARACTERS"
        for item in result.evidence
    )


@pytest.mark.parametrize("url", ["", "   "])
def test_empty_urls_are_rejected(url):
    with pytest.raises(ValueError):
        analyze_payment_url(url)


@pytest.mark.parametrize("url", [123, None, [], {}])
def test_non_string_urls_are_rejected(url):
    with pytest.raises(TypeError):
        analyze_payment_url(url)


def test_analysis_includes_limitations():
    result = analyze_payment_url("https://example.com/pay")

    assert len(result.limitations) >= 1
    assert any(
        "DNS" in limitation
        for limitation in result.limitations
    )


def test_risk_points_stay_within_range():
    result = analyze_payment_url("http://192.0.2.1:8080/pay")

    assert 0 <= result.risk_points <= 100

@pytest.mark.parametrize(
    "url",
    [
        "https://-example.com/",
        "https://example..com/",
        "https://.example.com/",
        "https://example-.com/",
    ],
)
def test_invalid_hostname_labels_are_rejected(url):
    result = analyze_payment_url(url)

    assert result.is_valid_url is False
    assert any(
        item.code == "INVALID_HOSTNAME"
        for item in result.evidence
    )


def test_https_with_http_standard_port_is_flagged():
    result = analyze_payment_url("https://example.com:80/pay")

    assert any(
        item.code == "UNUSUAL_PORT"
        for item in result.evidence
    )


def test_http_with_https_standard_port_is_flagged():
    result = analyze_payment_url("http://example.com:443/pay")

    assert any(
        item.code == "UNUSUAL_PORT"
        for item in result.evidence
    )


def test_https_with_standard_port_is_not_flagged():
    result = analyze_payment_url("https://example.com:443/pay")

    assert not any(
        item.code == "UNUSUAL_PORT"
        for item in result.evidence
    )


def test_http_with_standard_port_is_not_flagged():
    result = analyze_payment_url("http://example.com:80/pay")

    assert not any(
        item.code == "UNUSUAL_PORT"
        for item in result.evidence
    )
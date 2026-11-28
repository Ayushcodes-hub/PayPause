
import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class URLEvidence:
    code: str
    title: str
    description: str
    severity: str
    points: int


@dataclass(frozen=True)
class URLAnalysis:
    is_valid_url: bool
    normalized_url: str
    hostname: str | None
    risk_points: int
    evidence: tuple[URLEvidence, ...]
    coverage: tuple[str, ...]
    limitations: tuple[str, ...]


# Known URL-shortening services.
# These are indicators, not proof of malicious intent.
URL_SHORTENERS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "is.gd",
    "cutt.ly",
    "rb.gy",
    "shorturl.at",
    "rebrand.ly",
    "ow.ly",
    "buff.ly",
}


# Suspicious-looking hostname keywords.
# Their presence alone does not establish malicious intent.
SUSPICIOUS_HOST_KEYWORDS = {
    "login",
    "verify",
    "secure",
    "account",
    "update",
    "wallet",
    "payment",
    "refund",
    "claim",
}


def analyze_payment_url(payment_url: str) -> URLAnalysis:
    """
    Analyze a payment URL without making network requests.

    Does not open the URL, resolve DNS, follow redirects,
    or establish whether a website is fraudulent.
    """

    if not isinstance(payment_url, str):
        raise TypeError("Payment URL must be a string.")

    normalized = payment_url.strip()

    if not normalized:
        raise ValueError("Payment URL cannot be empty.")

    evidence: list[URLEvidence] = []
    hostname: str | None = None

    def add_evidence(
        code: str,
        title: str,
        description: str,
        severity: str,
        points: int,
    ) -> None:
        evidence.append(
            URLEvidence(
                code=code,
                title=title,
                description=description,
                severity=severity,
                points=points,
            )
        )

    # Reject whitespace, control characters and backslashes.
    # Check the original input before normalization because
    # strip() would otherwise silently remove some characters.
    if any(
        char.isspace() or ord(char) < 32 or char == "\\"
        for char in payment_url
    ):
        add_evidence(
            "URL_INVALID_CHARACTERS",
            "Invalid URL characters detected",
            "The submitted URL contains whitespace, control "
            "characters or backslashes.",
            "medium",
            15,
        )

        return URLAnalysis(
            is_valid_url=False,
            normalized_url=normalized,
            hostname=None,
            risk_points=15,
            evidence=tuple(evidence),
            coverage=("Local URL character validation",),
            limitations=(
                "The destination website was not opened.",
                "No DNS resolution or reputation lookup was performed.",
            ),
        )

    # Parse locally. Never fetch this URL.
    try:
        parsed = urlsplit(normalized)

        if parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError("Unsupported URL scheme.")

        if not parsed.netloc:
            raise ValueError("Missing network location.")

        if parsed.username is not None or parsed.password is not None:
            add_evidence(
                "EMBEDDED_CREDENTIALS",
                "Credentials embedded in URL",
                "The URL contains user information before its hostname.",
                "high",
                30,
            )

        hostname = parsed.hostname

        if not hostname:
            raise ValueError("Missing hostname.")

        # Accessing port also validates malformed port syntax.
        port = parsed.port

    except ValueError:
        return URLAnalysis(
            is_valid_url=False,
            normalized_url=normalized,
            hostname=None,
            risk_points=100,
            evidence=(
                URLEvidence(
                    "INVALID_URL_STRUCTURE",
                    "Invalid URL structure",
                    "The submitted value is not a supported HTTP or HTTPS URL.",
                    "high",
                    100,
                ),
            ),
            coverage=("Local URL structure validation",),
            limitations=(
                "No website content was inspected.",
                "No DNS or reputation lookup was performed.",
                "URL validity does not establish payment safety.",
            ),
        )

    hostname = hostname.lower()

    # Support IP literals separately from DNS hostnames.
    # IPv6 addresses contain colons and cannot pass DNS-label validation.
    try:
        ipaddress.ip_address(hostname)
        is_ip_address = True
    except ValueError:
        is_ip_address = False

    if not is_ip_address:
        # Remove one optional trailing DNS root dot.
        if hostname.endswith("."):
            hostname = hostname[:-1]

        if not hostname:
            return URLAnalysis(
                is_valid_url=False,
                normalized_url=normalized,
                hostname=None,
                risk_points=100,
                evidence=(
                    URLEvidence(
                        "INVALID_HOSTNAME",
                        "Invalid hostname",
                        "The URL does not contain a usable hostname.",
                        "high",
                        100,
                    ),
                ),
                coverage=("Local URL structure validation",),
                limitations=(
                    "No website content was inspected.",
                    "No DNS or reputation lookup was performed.",
                ),
            )

        # Validate DNS-style hostname labels.
        # Each label must be 1–63 characters, use only ASCII
        # letters, digits and hyphens, and cannot start or end
        # with a hyphen.
        hostname_labels = hostname.split(".")

        hostname_is_valid = (
            len(hostname) <= 253
            and all(
                1 <= len(label) <= 63
                and re.fullmatch(
                    r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?",
                    label,
                )
                for label in hostname_labels
            )
        )

        if not hostname_is_valid:
            return URLAnalysis(
                is_valid_url=False,
                normalized_url=normalized,
                hostname=None,
                risk_points=100,
                evidence=(
                    URLEvidence(
                        "INVALID_HOSTNAME",
                        "Invalid hostname",
                        "The hostname contains an empty, malformed or invalid domain label.",
                        "high",
                        100,
                    ),
                ),
                coverage=("Local URL hostname validation",),
                limitations=(
                    "No website content was inspected.",
                    "No DNS resolution or reputation lookup was performed.",
                    "Hostname structure does not establish domain ownership.",
                ),
            )

    # 1. HTTPS check.
    if parsed.scheme.lower() == "http":
        add_evidence(
            "INSECURE_HTTP",
            "Unencrypted HTTP connection",
            "The URL uses HTTP rather than encrypted HTTPS.",
            "medium",
            20,
        )

    # 2. IP literal check.
    if is_ip_address:
        add_evidence(
            "IP_ADDRESS_HOST",
            "IP address used as destination",
            "The URL uses an IP address instead of a conventional domain.",
            "medium",
            20,
        )

    # 3. Punycode domain check.
    if any(
        label.startswith("xn--")
        for label in hostname.split(".")
    ):
        add_evidence(
            "PUNYCODE_DOMAIN",
            "Internationalized domain encoding detected",
            "The hostname contains punycode. Inspect the displayed domain carefully.",
            "medium",
            20,
        )

    # 4. URL shortener check.
    if hostname in URL_SHORTENERS:
        add_evidence(
            "URL_SHORTENER",
            "URL shortening service detected",
            "The destination is hidden behind a known URL-shortening service.",
            "medium",
            15,
        )

    # 5. Unusual port check.
    standard_port = (
        80 if parsed.scheme.lower() == "http" else 443
    )

    if port is not None and port != standard_port:
        add_evidence(
            "UNUSUAL_PORT",
            "Non-standard destination port",
            f"The URL specifies port {port}, which is not a standard HTTP or HTTPS port.",
            "medium",
            15,
        )

    # 6. Suspicious hostname keyword check.
    hostname_labels = hostname.split(".")

    suspicious_keywords_found = [
        keyword
        for keyword in SUSPICIOUS_HOST_KEYWORDS
        if any(keyword in label for label in hostname_labels)
    ]

    if suspicious_keywords_found:
        add_evidence(
            "SUSPICIOUS_HOST_KEYWORD",
            "Suspicious-looking hostname wording",
            "The hostname contains potentially sensitive wording: "
            + ", ".join(sorted(suspicious_keywords_found))
            + ". This is a weak indicator and does not prove fraud.",
            "low",
            10,
        )

    # 7. Hostname contains many nested subdomains.
    if len(hostname.split(".")) >= 5:
        add_evidence(
            "DEEP_SUBDOMAIN",
            "Unusually deep hostname structure",
            "The hostname contains many domain labels. "
            "Check which domain actually controls the destination.",
            "low",
            10,
        )

    # Deduplicate findings.
    unique_evidence = {
        item.code: item for item in evidence
    }

    final_evidence = tuple(unique_evidence.values())

    risk_points = min(
        100,
        sum(item.points for item in final_evidence),
    )

    return URLAnalysis(
        is_valid_url=True,
        normalized_url=normalized,
        hostname=hostname,
        risk_points=risk_points,
        evidence=final_evidence,
        coverage=(
            "HTTP and HTTPS scheme validation",
            "Embedded credential detection",
            "IP literal detection",
            "Punycode hostname detection",
            "Known URL shortener detection",
            "Non-standard port detection",
            "Suspicious hostname wording",
            "Subdomain depth analysis",
            "DNS-style hostname label validation",
        ),
        limitations=(
            "The destination website was not opened.",
            "No DNS resolution or domain reputation lookup was performed.",
            "Redirect destinations were not inspected.",
            "Website content and payment forms were not inspected.",
            "A valid HTTPS URL does not guarantee that a payment is safe.",
            "Hostname indicators do not independently establish fraudulent intent.",
        ),
    )

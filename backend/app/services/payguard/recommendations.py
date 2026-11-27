
from app.schemas.payguard import (
    EvidenceSeverity,
    RiskEvidence,
    RiskRecommendation,
)


# Recommendations are tied to concrete evidence codes.
# They are not selected from the aggregate risk score.
RECOMMENDATION_RULES = {
    "INVALID_UPI_FORMAT": (
        EvidenceSeverity.HIGH,
        "Do not proceed with this UPI ID until it is corrected.",
        "The identifier does not match the accepted UPI structure.",
    ),
    "UNUSUAL_SEPARATOR_COUNT": (
        EvidenceSeverity.MEDIUM,
        "Ask the recipient to confirm their exact UPI ID.",
        "The identifier contains an unusual number of @ separators.",
    ),
    "SUSPICIOUS_KEYWORD": (
        EvidenceSeverity.MEDIUM,
        "Independently verify the payment request with the recipient.",
        "The identifier contains wording sometimes used in deceptive requests.",
    ),
    "EXCESSIVE_PUNCTUATION": (
        EvidenceSeverity.LOW,
        "Check every character of the UPI ID before paying.",
        "Repeated punctuation can make an identifier harder to read accurately.",
    ),
    "INVALID_URL_STRUCTURE": (
        EvidenceSeverity.CRITICAL,
        "Do not open or use this submitted payment link.",
        "The URL does not have a supported structure.",
    ),
    "INVALID_HOSTNAME": (
        EvidenceSeverity.CRITICAL,
        "Do not proceed using this payment link.",
        "The URL does not contain a usable hostname.",
    ),
    "URL_INVALID_CHARACTERS": (
        EvidenceSeverity.HIGH,
        "Reject this link and obtain a fresh URL from a trusted source.",
        "The submitted URL contains whitespace, control characters or backslashes.",
    ),
    "EMBEDDED_CREDENTIALS": (
        EvidenceSeverity.CRITICAL,
        "Do not use this link. Obtain the destination address independently.",
        "The URL embeds user information before its hostname.",
    ),
    "INSECURE_HTTP": (
        EvidenceSeverity.HIGH,
        "Do not enter payment credentials on this unencrypted connection.",
        "The URL uses HTTP instead of HTTPS.",
    ),
    "IP_ADDRESS_HOST": (
        EvidenceSeverity.HIGH,
        "Verify the destination independently before interacting with it.",
        "The URL uses an IP address instead of a conventional domain.",
    ),
    "PUNYCODE_DOMAIN": (
        EvidenceSeverity.HIGH,
        "Inspect the domain carefully and verify its official spelling.",
        "Internationalized domain encoding can make lookalike domains harder to recognize.",
    ),
    "URL_SHORTENER": (
        EvidenceSeverity.MEDIUM,
        "Verify the full destination through an independent trusted channel.",
        "The shortened URL hides its final destination.",
    ),
    "UNUSUAL_PORT": (
        EvidenceSeverity.MEDIUM,
        "Verify why the payment link uses a non-standard port.",
        "The destination specifies an unusual network port.",
    ),
    "SUSPICIOUS_HOST_KEYWORD": (
        EvidenceSeverity.MEDIUM,
        "Confirm that this is the organization's genuine domain.",
        "The hostname contains potentially misleading payment-related wording.",
    ),
    "DEEP_SUBDOMAIN": (
        EvidenceSeverity.LOW,
        "Check the registrable domain rather than relying on the first hostname label.",
        "The hostname contains several nested domain labels.",
    ),
}


def generate_recommendations(
    evidence: list[RiskEvidence],
) -> list[RiskRecommendation]:
    """
    Generate deterministic recommendations from detected evidence.

    Recommendations are independent of the aggregate risk score.
    Duplicate actions are removed.
    """

    recommendations: list[RiskRecommendation] = []
    seen_actions: set[str] = set()

    for item in evidence:
        rule = RECOMMENDATION_RULES.get(item.code)

        if rule is None:
            continue

        priority, action, reason = rule

        if action in seen_actions:
            continue

        recommendations.append(
            RiskRecommendation(
                priority=priority,
                action=action,
                reason=reason,
            )
        )

        seen_actions.add(action)

    # No detected indicators does not establish payment safety.
    if not recommendations:
        recommendations.append(
            RiskRecommendation(
                priority=EvidenceSeverity.INFO,
                action=(
                    "Verify the recipient's identity and payment amount "
                    "before authorizing the transaction."
                ),
                reason=(
                    "No indicators covered by the current screening "
                    "rules were detected. This does not guarantee safety."
                ),
            )
        )

    # Display the most important actions first.
    priority_order = {
        EvidenceSeverity.CRITICAL: 0,
        EvidenceSeverity.HIGH: 1,
        EvidenceSeverity.MEDIUM: 2,
        EvidenceSeverity.LOW: 3,
        EvidenceSeverity.INFO: 4,
    }

    recommendations.sort(
        key=lambda item: priority_order[item.priority]
    )

    return recommendations


from urllib.parse import parse_qs, urlsplit


MAX_QUERY_FIELDS = 50


def extract_upi_id_from_qr(payload: str) -> str:
    """
    Extract the payee UPI ID from a UPI payment QR URI.

    This validates URI structure only. It does not verify
    account ownership or recipient identity.
    """

    if not isinstance(payload, str):
        raise ValueError("UPI QR payload must be text.")

    if not payload or len(payload.encode("utf-8")) > 4096:
        raise ValueError("Invalid UPI QR payload.")

    try:
        parsed = urlsplit(payload)

        if parsed.scheme.lower() != "upi":
            raise ValueError("Unsupported UPI URI scheme.")

        if parsed.netloc.lower() != "pay":
            raise ValueError("Unsupported UPI payment URI.")

        if parsed.path or parsed.fragment:
            raise ValueError("Invalid UPI payment URI structure.")

        parameters = parse_qs(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=False,
            max_num_fields=MAX_QUERY_FIELDS,
        )

    except (ValueError, UnicodeError) as exc:
        raise ValueError("Malformed UPI payment URI.") from exc

    payee_ids = parameters.get("pa", [])

    if len(payee_ids) != 1:
        raise ValueError(
            "UPI payment URI must contain exactly one payee address."
        )

    upi_id = payee_ids[0].strip()

    if not upi_id:
        raise ValueError("UPI payee address cannot be empty.")

    return upi_id

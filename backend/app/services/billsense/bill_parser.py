import re
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ExtractedField:
    value: str | float | None
    source_text: str | None
    confidence: float | None


@dataclass(frozen=True)
class ParsedElectricityBill:
    provider: ExtractedField
    consumer_number: ExtractedField
    consumer_name: ExtractedField
    bill_number: ExtractedField
    billing_period: ExtractedField
    issue_date: ExtractedField
    due_date: ExtractedField
    units_consumed_kwh: ExtractedField
    previous_reading: ExtractedField
    current_reading: ExtractedField
    total_amount_inr: ExtractedField
    energy_charges_inr: ExtractedField
    fixed_charges_inr: ExtractedField
    taxes_inr: ExtractedField
    late_fee_inr: ExtractedField
    source_text: str


PROVIDERS = (
    "BESCOM",
    "MESCOM",
    "HESCOM",
    "GESCOM",
    "CESC",
    "TANGEDCO",
    "TSSPDCL",
    "TSNPDCL",
    "MSEDCL",
    "MahaVitaran",
    "Tata Power",
    "Adani Electricity",
    "BSES Rajdhani",
    "BSES Yamuna",
    "Torrent Power",
    "WBSEDCL",
    "KSEB",
    "JVVNL",
    "AVVNL",
    "DVVNL",
    "UPPCL",
)

DATE_PATTERN = (
    r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}"
)

LABELS = {
    "consumer_number": (
        r"consumer\s*(?:no|number|id)|"
        r"account\s*(?:no|number)|"
        r"rr\s*no|rr\s*number|"
        r"service\s*(?:no|number|connection)"
    ),
    "consumer_name": r"consumer\s*name|customer\s*name",
    "bill_number": r"bill\s*(?:no|number|id)",
    "billing_period": r"billing\s*period|bill\s*period",
    "issue_date": r"bill\s*date|issue\s*date|billing\s*date",
    "due_date": r"due\s*date|payment\s*due",
    "units_consumed_kwh": (
        r"units?\s*consumed|"
        r"consumption\s*\(?kwh\)?|"
        r"energy\s*consumed"
    ),
    "previous_reading": r"previous\s*(?:meter\s*)?reading",
    "current_reading": r"current\s*(?:meter\s*)?reading",
    "total_amount_inr": (
        r"total\s*(?:amount\s*)?(?:payable|due)|"
        r"net\s*amount\s*payable|"
        r"amount\s*payable|"
        r"bill\s*amount|"
        r"grand\s*total"
    ),
    "energy_charges_inr": r"energy\s*charges?|units?\s*charges?",
    "fixed_charges_inr": r"fixed\s*charges?",
    "taxes_inr": r"tax(?:es)?|gst",
    "late_fee_inr": r"late\s*(?:payment\s*)?fee|delayed\s*payment\s*charges?",
}


def _find_labeled_value(text: str, label_pattern: str):
    for line in text.splitlines():
        match = re.search(
            rf"\b(?:{label_pattern})\b\s*[:\-]?\s*(.+?)\s*$",
            line,
            re.IGNORECASE,
        )

        if match:
            value = match.group(1).strip(" :-\t")

            if value:
                return value, line.strip()

    return None, None


def _field(text: str, label_pattern: str) -> ExtractedField:
    value, source = _find_labeled_value(text, label_pattern)

    if value is None:
        return ExtractedField(None, None, None)

    return ExtractedField(value, source, 0.85)


def _amount_field(text: str, label_pattern: str) -> ExtractedField:
    raw, source = _find_labeled_value(text, label_pattern)

    if raw is None:
        return ExtractedField(None, None, None)

    match = re.search(
        r"(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d{1,2})?)",
        raw,
        re.IGNORECASE,
    )

    if not match:
        return ExtractedField(None, source, None)

    try:
        amount = float(match.group(1).replace(",", ""))
    except ValueError:
        return ExtractedField(None, source, None)

    return ExtractedField(amount, source, 0.85)


def _date_field(text: str, label_pattern: str) -> ExtractedField:
    raw, source = _find_labeled_value(text, label_pattern)

    if raw is None:
        return ExtractedField(None, None, None)

    match = re.search(DATE_PATTERN, raw, re.IGNORECASE)

    if not match:
        return ExtractedField(None, source, None)

    return ExtractedField(match.group(0), source, 0.85)


def _provider_field(text: str) -> ExtractedField:
    upper_text = text.upper()

    for provider in sorted(PROVIDERS, key=len, reverse=True):
        if provider.upper() in upper_text:
            return ExtractedField(provider, provider, 0.95)

    return ExtractedField(None, None, None)


def _consumption_field(text: str) -> ExtractedField:
    raw, source = _find_labeled_value(
        text,
        LABELS["units_consumed_kwh"],
    )

    if raw is None:
        return ExtractedField(None, None, None)

    match = re.search(
        r"([\d,]+(?:\.\d+)?)\s*(?:kwh|units?)?",
        raw,
        re.IGNORECASE,
    )

    if not match:
        return ExtractedField(None, source, None)

    try:
        value = float(match.group(1).replace(",", ""))
    except ValueError:
        return ExtractedField(None, source, None)

    return ExtractedField(value, source, 0.85)


def parse_electricity_bill(text: str) -> ParsedElectricityBill:
    """
    Extract structured fields from OCR or native PDF text.

    Confidence values are extraction heuristics, not guarantees
    of factual accuracy.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Bill text cannot be empty.")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    return ParsedElectricityBill(
        provider=_provider_field(normalized),
        consumer_number=_field(
            normalized, LABELS["consumer_number"]
        ),
        consumer_name=_field(
            normalized, LABELS["consumer_name"]
        ),
        bill_number=_field(
            normalized, LABELS["bill_number"]
        ),
        billing_period=_field(
            normalized, LABELS["billing_period"]
        ),
        issue_date=_date_field(
            normalized, LABELS["issue_date"]
        ),
        due_date=_date_field(
            normalized, LABELS["due_date"]
        ),
        units_consumed_kwh=_consumption_field(normalized),
        previous_reading=_field(
            normalized, LABELS["previous_reading"]
        ),
        current_reading=_field(
            normalized, LABELS["current_reading"]
        ),
        total_amount_inr=_amount_field(
            normalized, LABELS["total_amount_inr"]
        ),
        energy_charges_inr=_amount_field(
            normalized, LABELS["energy_charges_inr"]
        ),
        fixed_charges_inr=_amount_field(
            normalized, LABELS["fixed_charges_inr"]
        ),
        taxes_inr=_amount_field(
            normalized, LABELS["taxes_inr"]
        ),
        late_fee_inr=_amount_field(
            normalized, LABELS["late_fee_inr"]
        ),
        source_text=normalized,
    )



def apply_ocr_confidence(bill: ParsedElectricityBill, ocr_lines) -> ParsedElectricityBill:
    """
    Replace parser heuristics with actual OCR line confidence.

    Fields are matched against their original source lines.
    Provider names are matched as substrings because provider
    extraction may return only part of a heading.

    Unmatched fields and native PDF text retain None confidence.
    """
    lines = tuple(
        (
            " ".join(line.text.casefold().split()),
            line.confidence,
        )
        for line in ocr_lines
        if line.text.strip()
    )

    updates = {}

    for name in ParsedElectricityBill.__dataclass_fields__:
        if name == "source_text":
            continue

        field = getattr(bill, name)

        if field.source_text is None:
            continue

        source = " ".join(field.source_text.casefold().split())

        confidence = None

        for line_text, line_confidence in lines:
            if line_text == source:
                confidence = line_confidence
                break

        if confidence is None and name == "provider":
            for line_text, line_confidence in lines:
                if source in line_text:
                    confidence = line_confidence
                    break

        updates[name] = replace(field, confidence=confidence)

    return replace(bill, **updates)

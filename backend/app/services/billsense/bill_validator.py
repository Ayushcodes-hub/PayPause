from dataclasses import dataclass

from app.services.billsense.bill_parser import ParsedElectricityBill


@dataclass(frozen=True)
class BillIssue:
    code: str
    message: str
    severity: str


@dataclass(frozen=True)
class BillValidationResult:
    is_valid: bool
    issues: tuple[BillIssue, ...]


def _number(value):
    if value is None:
        return None

    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def validate_bill(bill: ParsedElectricityBill) -> BillValidationResult:
    issues = []

    required_fields = {
        "consumer_number": bill.consumer_number.value,
        "billing_period": bill.billing_period.value,
        "total_amount_inr": bill.total_amount_inr.value,
    }

    for field, value in required_fields.items():
        if value is None:
            issues.append(BillIssue(
                code=f"MISSING_{field.upper()}",
                message=f"Could not extract {field.replace('_', ' ')}.",
                severity="warning",
            ))

    numeric_fields = {
        "units_consumed_kwh": bill.units_consumed_kwh.value,
        "previous_reading": bill.previous_reading.value,
        "current_reading": bill.current_reading.value,
        "total_amount_inr": bill.total_amount_inr.value,
        "energy_charges_inr": bill.energy_charges_inr.value,
        "fixed_charges_inr": bill.fixed_charges_inr.value,
        "taxes_inr": bill.taxes_inr.value,
        "late_fee_inr": bill.late_fee_inr.value,
    }

    for field, value in numeric_fields.items():
        number = _number(value)

        if number is not None and number < 0:
            issues.append(BillIssue(
                code=f"NEGATIVE_{field.upper()}",
                message=f"{field.replace('_', ' ')} cannot be negative.",
                severity="error",
            ))

    previous = _number(bill.previous_reading.value)
    current = _number(bill.current_reading.value)
    units = _number(bill.units_consumed_kwh.value)

    if previous is not None and current is not None:
        if current < previous:
            issues.append(BillIssue(
                code="METER_READING_DECREASED",
                message="Current meter reading is lower than previous reading.",
                severity="error",
            ))
        elif units is not None:
            difference = current - previous

            if abs(difference - units) > 1:
                issues.append(BillIssue(
                    code="METER_CONSUMPTION_MISMATCH",
                    message=(
                        f"Meter reading difference is {difference:g} kWh, "
                        f"but reported consumption is {units:g} kWh."
                    ),
                    severity="warning",
                ))

    components = [
        _number(bill.energy_charges_inr.value),
        _number(bill.fixed_charges_inr.value),
        _number(bill.taxes_inr.value),
        _number(bill.late_fee_inr.value),
    ]
    total = _number(bill.total_amount_inr.value)

    if total is not None and all(value is not None for value in components):
        calculated_total = sum(components)

        if abs(calculated_total - total) > 2:
            issues.append(BillIssue(
                code="BILL_AMOUNT_MISMATCH",
                message=(
                    f"Extracted charge components total ₹{calculated_total:.2f}, "
                    f"but payable amount is ₹{total:.2f}."
                ),
                severity="warning",
            ))

    return BillValidationResult(
        is_valid=not any(issue.severity == "error" for issue in issues),
        issues=tuple(issues),
    )

from dataclasses import dataclass
from datetime import datetime
import re

from app.services.billsense.bill_parser import ParsedElectricityBill
from app.services.billsense.bill_validator import _number


@dataclass(frozen=True)
class ConsumptionAnalysis:
    units_consumed_kwh: float | None
    is_derived: bool
    daily_average_kwh: float | None
    billing_days: int | None
    previous_consumption_kwh: float | None
    change_percentage: float | None
    usage_status: str
    observations: tuple[str, ...]


def _billing_days(period):
    if not period:
        return None

    dates = re.findall(
        r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
        str(period),
    )

    if len(dates) < 2:
        return None

    parsed = []

    for value in dates[:2]:
        result = None

        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
            try:
                result = datetime.strptime(value, fmt).date()
                break
            except ValueError:
                continue

        if result is None:
            return None

        parsed.append(result)

    days = (parsed[1] - parsed[0]).days
    return days if days > 0 else None


def analyze_consumption(
    bill: ParsedElectricityBill,
    previous_consumption_kwh: float | None = None,
) -> ConsumptionAnalysis:
    observations = []

    units = _number(bill.units_consumed_kwh.value)
    is_derived = False

    previous_reading = _number(bill.previous_reading.value)
    current_reading = _number(bill.current_reading.value)

    if (
        units is None
        and previous_reading is not None
        and current_reading is not None
        and current_reading >= previous_reading
    ):
        units = current_reading - previous_reading
        is_derived = True
        observations.append(
            "Consumption was calculated from meter readings."
        )

    days = _billing_days(bill.billing_period.value)

    daily_average = (
        units / days
        if units is not None and days is not None
        else None
    )

    change_percentage = None
    usage_status = "insufficient_data"

    if units is not None and previous_consumption_kwh is not None:
        if previous_consumption_kwh < 0:
            raise ValueError("Previous consumption cannot be negative.")

        if previous_consumption_kwh == 0:
            usage_status = "baseline_zero"
            observations.append(
                "Percentage change cannot be calculated from zero baseline."
            )
        else:
            change_percentage = (
                (units - previous_consumption_kwh)
                / previous_consumption_kwh
            ) * 100

            if change_percentage >= 30:
                usage_status = "significantly_higher"
                observations.append(
                    "Consumption is at least 30% higher than the supplied comparison."
                )
            elif change_percentage <= -30:
                usage_status = "significantly_lower"
                observations.append(
                    "Consumption is at least 30% lower than the supplied comparison."
                )
            else:
                usage_status = "normal"

    elif units is not None:
        usage_status = "no_comparison"

    return ConsumptionAnalysis(
        units_consumed_kwh=units,
        is_derived=is_derived,
        daily_average_kwh=daily_average,
        billing_days=days,
        previous_consumption_kwh=previous_consumption_kwh,
        change_percentage=change_percentage,
        usage_status=usage_status,
        observations=tuple(observations),
    )

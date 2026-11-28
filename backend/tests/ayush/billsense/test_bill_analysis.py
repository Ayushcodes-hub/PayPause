from dataclasses import replace

import pytest

from app.services.billsense.bill_parser import parse_electricity_bill
from app.services.billsense.bill_validator import validate_bill
from app.services.billsense.consumption_analyzer import analyze_consumption


SAMPLE = """
BESCOM
Consumer Name: AYUSH
RR Number: R123456
Billing Period: 01/10/2026 - 31/10/2026
Previous Reading: 1200
Current Reading: 1450
Units Consumed: 250 kWh
Energy Charges: Rs. 1750
Fixed Charges: Rs. 100
GST: Rs. 50
Late Fee: Rs. 0
Total Amount Payable: Rs. 1900
"""


def test_valid_bill():
    result = validate_bill(parse_electricity_bill(SAMPLE))
    assert result.is_valid
    assert not result.issues


def test_detects_meter_decrease():
    bill = parse_electricity_bill(SAMPLE)
    bill = replace(
        bill,
        previous_reading=replace(bill.previous_reading, value="1500"),
    )

    result = validate_bill(bill)

    assert not result.is_valid
    assert any(
        issue.code == "METER_READING_DECREASED"
        for issue in result.issues
    )


def test_detects_amount_mismatch():
    bill = parse_electricity_bill(SAMPLE)
    bill = replace(
        bill,
        total_amount_inr=replace(
            bill.total_amount_inr, value=2500.0
        ),
    )

    result = validate_bill(bill)

    assert any(
        issue.code == "BILL_AMOUNT_MISMATCH"
        for issue in result.issues
    )


def test_detects_missing_consumer_number():
    bill = parse_electricity_bill(
        "Billing Period: 01/10/2026 - 31/10/2026"
    )

    result = validate_bill(bill)

    assert any(
        issue.code == "MISSING_CONSUMER_NUMBER"
        for issue in result.issues
    )


def test_calculates_daily_consumption():
    bill = parse_electricity_bill(SAMPLE)
    result = analyze_consumption(bill)

    assert result.units_consumed_kwh == 250
    assert result.billing_days == 30
    assert result.daily_average_kwh == pytest.approx(250 / 30)
    assert result.usage_status == "no_comparison"


def test_calculates_change_against_previous_period():
    bill = parse_electricity_bill(SAMPLE)
    result = analyze_consumption(
        bill,
        previous_consumption_kwh=200,
    )

    assert result.change_percentage == pytest.approx(25)
    assert result.usage_status == "normal"


def test_flags_significant_increase():
    bill = parse_electricity_bill(SAMPLE)
    result = analyze_consumption(
        bill,
        previous_consumption_kwh=150,
    )

    assert result.usage_status == "significantly_higher"


def test_derives_units_from_meter_readings():
    bill = parse_electricity_bill(SAMPLE)
    bill = replace(
        bill,
        units_consumed_kwh=replace(
            bill.units_consumed_kwh, value=None
        ),
    )

    result = analyze_consumption(bill)

    assert result.units_consumed_kwh == 250
    assert result.is_derived


def test_rejects_negative_previous_consumption():
    bill = parse_electricity_bill(SAMPLE)

    with pytest.raises(ValueError):
        analyze_consumption(bill, previous_consumption_kwh=-10)

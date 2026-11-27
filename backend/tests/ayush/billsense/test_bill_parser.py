from app.services.billsense.bill_parser import parse_electricity_bill


SAMPLE_BILL = """
BESCOM - Bangalore Electricity Supply Company
Consumer Name: AYUSH ARYAMAN
RR Number: R123456
Bill Number: BILL202611
Billing Period: 01/10/2026 - 31/10/2026
Bill Date: 02/11/2026
Due Date: 15/11/2026
Previous Reading: 1200
Current Reading: 1450
Units Consumed: 250 kWh
Energy Charges: Rs. 1750.00
Fixed Charges: Rs. 100.00
GST: Rs. 50.00
Late Fee: Rs. 0.00
Total Amount Payable: Rs. 1900.00
"""


def test_extracts_provider():
    result = parse_electricity_bill(SAMPLE_BILL)
    assert result.provider.value == "BESCOM"


def test_extracts_consumer_details():
    result = parse_electricity_bill(SAMPLE_BILL)
    assert result.consumer_number.value == "R123456"
    assert result.consumer_name.value == "AYUSH ARYAMAN"


def test_extracts_billing_dates():
    result = parse_electricity_bill(SAMPLE_BILL)
    assert result.issue_date.value == "02/11/2026"
    assert result.due_date.value == "15/11/2026"


def test_extracts_consumption():
    result = parse_electricity_bill(SAMPLE_BILL)
    assert result.units_consumed_kwh.value == 250.0


def test_extracts_amounts():
    result = parse_electricity_bill(SAMPLE_BILL)
    assert result.energy_charges_inr.value == 1750.0
    assert result.fixed_charges_inr.value == 100.0
    assert result.taxes_inr.value == 50.0
    assert result.total_amount_inr.value == 1900.0


def test_preserves_source_text():
    result = parse_electricity_bill(SAMPLE_BILL)
    assert "BESCOM" in result.source_text


def test_rejects_empty_text():
    import pytest

    with pytest.raises(ValueError):
        parse_electricity_bill("   ")

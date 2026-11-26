from app.services.billsense.ocr_engine import OCRLine
from app.services.billsense.bill_parser import (
    apply_ocr_confidence,
    parse_electricity_bill,
)


def test_ocr_confidence_uses_actual_line_scores():
    text = (
        "BESCOM ELECTRICITY BILL\n"
        "RR Number: R123456\n"
        "Units Consumed: 250 kWh\n"
        "Total Amount Payable: Rs. 1900.00"
    )

    lines = (
        OCRLine("BESCOM ELECTRICITY BILL", 0.9873, None),
        OCRLine("RR Number: R123456", 0.9916, None),
        OCRLine("Units Consumed: 250 kWh", 0.9995, None),
        OCRLine("Total Amount Payable: Rs. 1900.00", 0.9863, None),
    )

    bill = apply_ocr_confidence(parse_electricity_bill(text), lines)

    assert bill.provider.confidence == 0.9873
    assert bill.consumer_number.confidence == 0.9916
    assert bill.units_consumed_kwh.confidence == 0.9995
    assert bill.total_amount_inr.confidence == 0.9863


def test_unmatched_ocr_fields_have_no_confidence():
    text = (
        "BESCOM ELECTRICITY BILL\n"
        "RR Number: R123456\n"
        "Units Consumed: 250 kWh"
    )

    lines = (
        OCRLine("UNRELATED OCR TEXT", 0.99, None),
    )

    bill = apply_ocr_confidence(parse_electricity_bill(text), lines)

    assert bill.provider.confidence is None
    assert bill.consumer_number.confidence is None
    assert bill.units_consumed_kwh.confidence is None


def test_native_pdf_text_keeps_confidence_none():
    text = (
        "BESCOM ELECTRICITY BILL\n"
        "RR Number: R123456\n"
        "Units Consumed: 250 kWh"
    )

    lines = (
        OCRLine("BESCOM ELECTRICITY BILL", None, None),
        OCRLine("RR Number: R123456", None, None),
        OCRLine("Units Consumed: 250 kWh", None, None),
    )

    bill = apply_ocr_confidence(parse_electricity_bill(text), lines)

    assert bill.provider.confidence is None
    assert bill.consumer_number.confidence is None
    assert bill.units_consumed_kwh.confidence is None

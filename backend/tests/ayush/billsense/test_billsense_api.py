from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.exceptions import PayPauseException
from app.api.v1 import billsense
from app.schemas.billsense import (
    BillSenseAssessment,
    BillSenseFields,
    BillSenseField,
    ConsumptionAnalysisResponse,
)
from app.services.billsense.document_validator import (
    MAX_DOCUMENT_BYTES,
    DocumentValidationError,
)


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=uuid4(),
        email="test@example.com",
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_current_user, None)


def sample_assessment():
    empty = BillSenseField()

    return BillSenseAssessment(
        document_type="image",
        fields=BillSenseFields(
            provider=empty,
            consumer_number=BillSenseField(
                value="123456",
                source_text="Consumer Number: 123456",
                confidence=0.95,
            ),
            consumer_name=empty,
            bill_number=empty,
            billing_period=BillSenseField(
                value="01/10/2026 - 31/10/2026",
                source_text="Billing Period: 01/10/2026 - 31/10/2026",
                confidence=0.95,
            ),
            issue_date=empty,
            due_date=empty,
            units_consumed_kwh=BillSenseField(
                value=120.0,
                source_text="Units Consumed: 120 kWh",
                confidence=0.95,
            ),
            previous_reading=empty,
            current_reading=empty,
            total_amount_inr=BillSenseField(
                value=950.0,
                source_text="Total Amount: Rs. 950",
                confidence=0.95,
            ),
            energy_charges_inr=empty,
            fixed_charges_inr=empty,
            taxes_inr=empty,
            late_fee_inr=empty,
        ),
        is_valid=True,
        validation_issues=[],
        consumption=ConsumptionAnalysisResponse(
            units_consumed_kwh=120.0,
            is_derived=False,
            daily_average_kwh=4.0,
            billing_days=30,
            previous_consumption_kwh=None,
            change_percentage=None,
            usage_status="normal",
            observations=[],
        ),
        extracted_text="Consumer Number: 123456",
        ocr_pages=1,
        average_ocr_confidence=0.95,
        processing_time_ms=100.0,
    )


def test_billsense_requires_authentication():
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/billsense/analyze",
            files={
                "bill_file": (
                    "bill.png",
                    b"test",
                    "image/png",
                )
            },
        )

    assert response.status_code == 401


def test_billsense_rejects_invalid_document(client, monkeypatch):
    def reject_document(content):
        raise DocumentValidationError("The uploaded document is invalid.")

    monkeypatch.setattr(
        billsense,
        "_analyze_bill",
        reject_document,
    )

    response = client.post(
        "/api/v1/billsense/analyze",
        files={
            "bill_file": (
                "invalid.png",
                b"invalid-document",
                "image/png",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert (
        response.json()["error"]["code"]
        == "BILLSENSE_INVALID_DOCUMENT"
    )


def test_billsense_rejects_oversized_upload(client):
    response = client.post(
        "/api/v1/billsense/analyze",
        files={
            "bill_file": (
                "large.pdf",
                b"x" * (MAX_DOCUMENT_BYTES + 1),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413
    assert (
        response.json()["error"]["code"]
        == "BILLSENSE_DOCUMENT_TOO_LARGE"
    )


def test_billsense_returns_structured_analysis(client, monkeypatch):
    monkeypatch.setattr(
        billsense,
        "_analyze_bill",
        lambda content: sample_assessment(),
    )

    response = client.post(
        "/api/v1/billsense/analyze",
        files={
            "bill_file": (
                "bill.png",
                b"test-document",
                "image/png",
            )
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["success"] is True
    assert payload["data"]["document_type"] == "image"
    assert payload["data"]["fields"]["consumer_number"]["value"] == "123456"
    assert payload["data"]["consumption"]["units_consumed_kwh"] == 120.0
def test_billsense_processes_real_bescom_pdf(client):
    import pymupdf

    bill_text = """
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

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), bill_text, fontsize=11)
    pdf_bytes = document.tobytes()
    document.close()

    response = client.post(
        "/api/v1/billsense/analyze",
        files={
            "bill_file": (
                "synthetic_bescom_bill.pdf",
                pdf_bytes,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["success"] is True

    assessment = payload["data"]
    fields = assessment["fields"]
    consumption = assessment["consumption"]

    assert assessment["document_type"] == "pdf"
    assert assessment["is_valid"] is True

    assert fields["provider"]["value"] == "BESCOM"
    assert fields["consumer_number"]["value"] == "R123456"
    assert fields["consumer_name"]["value"] == "AYUSH ARYAMAN"
    assert fields["units_consumed_kwh"]["value"] == 250.0
    assert fields["total_amount_inr"]["value"] == 1900.0

    assert consumption["units_consumed_kwh"] == 250.0
    assert consumption["is_derived"] is False
    assert consumption["billing_days"] == 30
    assert consumption["usage_status"] == "no_comparison"

    assert assessment["ocr_pages"] == 1
    assert "BESCOM" in assessment["extracted_text"]

def test_billsense_processes_real_bescom_image(client):
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont

    lines = [
        "BESCOM ELECTRICITY BILL",
        "Consumer Name: AYUSH ARYAMAN",
        "RR Number: R123456",
        "Bill Number: BILL202611",
        "Billing Period: 01/10/2026 - 31/10/2026",
        "Bill Date: 02/11/2026",
        "Due Date: 15/11/2026",
        "Previous Reading: 1200",
        "Current Reading: 1450",
        "Units Consumed: 250 kWh",
        "Energy Charges: Rs. 1750.00",
        "Fixed Charges: Rs. 100.00",
        "GST: Rs. 50.00",
        "Late Fee: Rs. 0.00",
        "Total Amount Payable: Rs. 1900.00",
    ]

    image = Image.new("RGB", (1800, 1400), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 40)

    y = 80
    for line in lines:
        draw.text((100, y), line, fill="black", font=font)
        y += 78

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    response = client.post(
        "/api/v1/billsense/analyze",
        files={
            "bill_file": (
                "synthetic_bescom_bill.png",
                buffer.getvalue(),
                "image/png",
            )
        },
    )

    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["success"] is True

    assessment = payload["data"]
    fields = assessment["fields"]
    consumption = assessment["consumption"]

    assert assessment["document_type"] == "image"
    assert assessment["is_valid"] is True

    assert fields["provider"]["value"] == "BESCOM"
    assert fields["consumer_number"]["value"] == "R123456"
    assert fields["consumer_name"]["value"] == "AYUSH ARYAMAN"
    assert fields["units_consumed_kwh"]["value"] == 250.0

    assert fields["previous_reading"]["value"] == "1200"
    assert fields["current_reading"]["value"] == "1450"
    assert fields["energy_charges_inr"]["value"] == 1750.0
    assert fields["total_amount_inr"]["value"] == 1900.0

    assert consumption["units_consumed_kwh"] == 250.0
    assert consumption["billing_days"] == 30
    assert consumption["is_derived"] is False

    assert assessment["ocr_pages"] == 1
    assert assessment["average_ocr_confidence"] > 0.80
    assert "BESCOM" in assessment["extracted_text"]

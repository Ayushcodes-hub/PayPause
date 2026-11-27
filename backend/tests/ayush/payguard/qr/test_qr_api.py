
from io import BytesIO
from uuid import UUID

import zxingcpp
from fastapi.testclient import TestClient
from PIL import Image

from app.core.auth import AuthenticatedUser, get_current_user
from app.main import app


client = TestClient(app)

TEST_USER_ID = UUID("123e4567-e89b-12d3-a456-426614174000")


def create_qr_image(payload: str) -> bytes:
    barcode = zxingcpp.create_barcode(
        payload,
        zxingcpp.BarcodeFormat.QRCode,
    )
    generated = zxingcpp.write_barcode_to_image(barcode, scale=5)
    height, width = generated.shape

    image = Image.frombytes(
        "L",
        (width, height),
        bytes(generated),
    )

    output = BytesIO()
    image.save(output, format="PNG")
    image.close()

    return output.getvalue()


def create_authenticated_client():
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=TEST_USER_ID,
        email="test@example.com",
    )
    return client


def remove_authentication_override():
    app.dependency_overrides.pop(get_current_user, None)


def test_upi_qr_assessment_returns_complete_response():
    authenticated_client = create_authenticated_client()

    try:
        payload = "upi://pay?pa=merchant@bank&pn=Test"
        response = authenticated_client.post(
            "/api/v1/payguard/assess-qr",
            files={
                "qr_image": (
                    "payment.png",
                    create_qr_image(payload),
                    "image/png",
                )
            },
        )

        assert response.status_code == 200

        body = response.json()
        assessment = body["data"]

        assert body["success"] is True
        assert assessment["input_type"] == "upi"
        assert assessment["assessment_id"]
        assert assessment["risk_level"] in {
            "low", "moderate", "high", "critical"
        }
        assert assessment["coverage"]
        assert assessment["limitations"]
        assert payload not in response.text

    finally:
        remove_authentication_override()


def test_https_qr_assessment_returns_complete_response():
    authenticated_client = create_authenticated_client()

    try:
        payload = "https://example.com/payment"

        response = authenticated_client.post(
            "/api/v1/payguard/assess-qr",
            files={
                "qr_image": (
                    "payment.png",
                    create_qr_image(payload),
                    "image/png",
                )
            },
        )

        assert response.status_code == 200
        assert response.json()["data"]["input_type"] == "url"
        assert payload not in response.text

    finally:
        remove_authentication_override()


def test_unsupported_qr_payload_returns_422():
    authenticated_client = create_authenticated_client()

    try:
        response = authenticated_client.post(
            "/api/v1/payguard/assess-qr",
            files={
                "qr_image": (
                    "payment.png",
                    create_qr_image("mailto:test@example.com"),
                    "image/png",
                )
            },
        )

        assert response.status_code == 422
        assert response.json()["success"] is False
        assert response.json()["error"]["code"] == "UNSUPPORTED_QR_PAYLOAD"

    finally:
        remove_authentication_override()


def test_invalid_image_returns_422():
    authenticated_client = create_authenticated_client()

    try:
        response = authenticated_client.post(
            "/api/v1/payguard/assess-qr",
            files={
                "qr_image": (
                    "invalid.png",
                    b"not an image",
                    "image/png",
                )
            },
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "QR_DECODE_FAILED"

    finally:
        remove_authentication_override()


def test_empty_image_returns_422():
    authenticated_client = create_authenticated_client()

    try:
        response = authenticated_client.post(
            "/api/v1/payguard/assess-qr",
            files={
                "qr_image": (
                    "empty.png",
                    b"",
                    "image/png",
                )
            },
        )

        assert response.status_code == 422

    finally:
        remove_authentication_override()


def test_missing_authentication_is_rejected():
    remove_authentication_override()

    response = client.post(
        "/api/v1/payguard/assess-qr",
        files={
            "qr_image": (
                "payment.png",
                create_qr_image("upi://pay?pa=merchant@bank"),
                "image/png",
            )
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_oversized_image_returns_413():
    from app.services.payguard.qr_decoder import MAX_IMAGE_BYTES

    authenticated_client = create_authenticated_client()

    try:
        response = authenticated_client.post(
            "/api/v1/payguard/assess-qr",
            files={
                "qr_image": (
                    "large.png",
                    b"x" * (MAX_IMAGE_BYTES + 1),
                    "image/png",
                )
            },
        )

        assert response.status_code == 413
        assert response.json()["error"]["code"] == "QR_IMAGE_TOO_LARGE"

    finally:
        remove_authentication_override()


def test_qr_assessment_includes_security_headers():
    authenticated_client = create_authenticated_client()

    try:
        response = authenticated_client.post(
            "/api/v1/payguard/assess-qr",
            files={
                "qr_image": (
                    "payment.png",
                    create_qr_image("upi://pay?pa=merchant@bank"),
                    "image/png",
                )
            },
        )

        assert response.status_code == 200
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("x-request-id")

    finally:
        remove_authentication_override()

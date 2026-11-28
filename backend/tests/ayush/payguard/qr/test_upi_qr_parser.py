import pytest

from app.services.payguard.upi_qr_parser import extract_upi_id_from_qr


def test_extracts_valid_upi_id():
    assert (
        extract_upi_id_from_qr("upi://pay?pa=merchant%40okaxis")
        == "merchant@okaxis"
    )


def test_ignores_optional_payment_parameters():
    payload = (
        "upi://pay?pa=merchant%40okaxis"
        "&pn=Merchant&am=10.00&cu=INR&tn=Payment"
    )
    assert extract_upi_id_from_qr(payload) == "merchant@okaxis"


def test_trims_whitespace_from_payee_id():
    assert (
        extract_upi_id_from_qr("upi://pay?pa=%20merchant%40okaxis%20")
        == "merchant@okaxis"
    )


@pytest.mark.parametrize(
    "payload",
    [
        "upi://pay",
        "upi://pay?pn=Merchant",
        "upi://pay?pa=",
        "upi://pay?pa=merchant%40okaxis&pa=other%40bank",
        "https://pay.example.com?pa=merchant%40okaxis",
        "upi://collect?pa=merchant%40okaxis",
        "upi://pay/path?pa=merchant%40okaxis",
        "upi://pay?pa=merchant%40okaxis#fragment",
    ],
)
def test_rejects_invalid_upi_payment_uris(payload):
    with pytest.raises(ValueError):
        extract_upi_id_from_qr(payload)


def test_rejects_non_string_payload():
    with pytest.raises(ValueError):
        extract_upi_id_from_qr(None)


def test_rejects_oversized_payload():
    payload = "upi://pay?pa=merchant%40okaxis&x=" + ("a" * 4100)
    with pytest.raises(ValueError):
        extract_upi_id_from_qr(payload)


def test_rejects_excessive_query_parameters():
    parameters = "&".join(f"x{i}=value" for i in range(51))
    payload = f"upi://pay?pa=merchant%40okaxis&{parameters}"

    with pytest.raises(ValueError):
        extract_upi_id_from_qr(payload)

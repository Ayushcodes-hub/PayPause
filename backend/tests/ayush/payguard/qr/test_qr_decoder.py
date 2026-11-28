from io import BytesIO

import pytest
import zxingcpp
from PIL import Image

from app.services.payguard.qr_decoder import decode_qr_image


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


def test_decodes_upi_qr():
    payload = "upi://pay?pa=test@upi&pn=Test"
    result = decode_qr_image(create_qr_image(payload))

    assert result.payload == payload
    assert result.payload_type == "upi"
    assert result.format == "QR_CODE"


def test_decodes_https_url_qr():
    payload = "https://example.com/payment"
    result = decode_qr_image(create_qr_image(payload))

    assert result.payload == payload
    assert result.payload_type == "url"


def test_classifies_unsupported_payload():
    payload = "mailto:test@example.com"
    result = decode_qr_image(create_qr_image(payload))

    assert result.payload == payload
    assert result.payload_type == "unsupported"


def test_rejects_empty_upload():
    with pytest.raises(ValueError, match="empty"):
        decode_qr_image(b"")


def test_rejects_non_bytes_input():
    with pytest.raises(ValueError, match="bytes"):
        decode_qr_image("not image bytes")


def test_rejects_oversized_upload():
    from app.services.payguard.qr_decoder import MAX_IMAGE_BYTES

    oversized = b"x" * (MAX_IMAGE_BYTES + 1)

    with pytest.raises(ValueError, match="maximum allowed size"):
        decode_qr_image(oversized)


def test_rejects_invalid_image():
    with pytest.raises(ValueError, match="Invalid or unsafe image"):
        decode_qr_image(b"this is not an image")


def test_rejects_animated_gif():
    frames = [
        Image.new("RGB", (100, 100), color="white"),
        Image.new("RGB", (100, 100), color="black"),
    ]

    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
    )

    for frame in frames:
        frame.close()

    with pytest.raises(ValueError, match="Animated images"):
        decode_qr_image(output.getvalue())


def test_rejects_multiple_qr_codes():
    first = Image.open(BytesIO(create_qr_image("first-qr")))
    second = Image.open(BytesIO(create_qr_image("second-qr")))

    canvas = Image.new(
        "RGB",
        (first.width + second.width + 80, max(first.height, second.height)),
        "white",
    )

    canvas.paste(first, (0, 0))
    canvas.paste(second, (first.width + 80, 0))

    output = BytesIO()
    canvas.save(output, format="PNG")

    first.close()
    second.close()
    canvas.close()

    with pytest.raises(ValueError, match="exactly one QR code"):
        decode_qr_image(output.getvalue())

def test_rejects_image_exceeding_pixel_limit():
    image = Image.new("RGB", (4001, 4000), "white")
    output = BytesIO()

    try:
        image.save(output, format="PNG")
    finally:
        image.close()

    with pytest.raises(ValueError, match="pixel limit"):
        decode_qr_image(output.getvalue())

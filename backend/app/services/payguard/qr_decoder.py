from dataclasses import dataclass
from io import BytesIO
from typing import Literal
from urllib.parse import urlsplit

import zxingcpp
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_PAYLOAD_BYTES = 4096

ALLOWED_IMAGE_FORMATS = {"PNG", "JPEG", "WEBP"}

PayloadType = Literal["upi", "url", "unsupported"]


@dataclass(frozen=True)
class QRDecodeResult:
    payload: str
    payload_type: PayloadType
    format: str = "QR_CODE"


def _validate_image(image_bytes: bytes) -> Image.Image:
    if not isinstance(image_bytes, bytes):
        raise ValueError("Image input must be bytes.")

    if not image_bytes:
        raise ValueError("Uploaded image is empty.")

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("Image exceeds the maximum allowed size.")

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise ValueError("Animated images are not supported.")

            if image.format not in ALLOWED_IMAGE_FORMATS:
                raise ValueError("Unsupported image format.")

            width, height = image.size

            if width <= 0 or height <= 0:
                raise ValueError("Invalid image dimensions.")

            if width * height > MAX_IMAGE_PIXELS:
                raise ValueError("Image dimensions exceed the allowed pixel limit.")

            image.load()
            normalized = ImageOps.exif_transpose(image)
            return normalized.convert("RGB")

    except ValueError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise ValueError("Invalid or unsafe image.") from exc


def _classify_payload(payload: str) -> PayloadType:
    parsed = urlsplit(payload)
    scheme = parsed.scheme.lower()

    if scheme == "upi":
        return "upi"

    if scheme in {"http", "https"}:
        return "url"

    return "unsupported"


def decode_qr_image(image_bytes: bytes) -> QRDecodeResult:
    """
    Decode exactly one QR code from an uploaded image.

    This function performs local decoding only. It never opens URLs,
    contacts payment providers, or initiates financial transactions.
    """

    image = _validate_image(image_bytes)

    try:
        barcodes = zxingcpp.read_barcodes(
            image,
            formats=zxingcpp.BarcodeFormat.QRCode,
            try_rotate=True,
            try_downscale=True,
            try_invert=True,
        )
    except Exception as exc:
        raise ValueError("QR decoding failed.") from exc
    finally:
        image.close()

    if not barcodes:
        raise ValueError("No readable QR code was found.")

    if len(barcodes) != 1:
        raise ValueError("Image must contain exactly one QR code.")

    payload = barcodes[0].text

    if not isinstance(payload, str) or not payload:
        raise ValueError("QR code contains no readable text payload.")

    try:
        payload_size = len(payload.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ValueError("QR payload has invalid text encoding.") from exc

    if payload_size > MAX_PAYLOAD_BYTES:
        raise ValueError("QR payload exceeds the maximum allowed size.")

    payload_type = _classify_payload(payload)

    return QRDecodeResult(
        payload=payload,
        payload_type=payload_type,
    )

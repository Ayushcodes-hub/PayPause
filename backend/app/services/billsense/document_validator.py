from dataclasses import dataclass
from enum import Enum

import pymupdf
from PIL import Image, UnidentifiedImageError
from io import BytesIO


MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_PDF_PAGES = 10

SUPPORTED_IMAGE_FORMATS = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
}


class DocumentType(str, Enum):
    IMAGE = "image"
    PDF = "pdf"


@dataclass(frozen=True)
class DocumentMetadata:
    document_type: DocumentType
    mime_type: str
    size_bytes: int
    page_count: int
    image_width: int | None = None
    image_height: int | None = None


class DocumentValidationError(ValueError):
    """Raised when an uploaded bill document is invalid."""


def validate_document(
    content: bytes,
    filename: str | None = None,
    declared_content_type: str | None = None,
) -> DocumentMetadata:
    """
    Validate an electricity bill image or PDF entirely in memory.

    Filename and declared MIME type are not trusted for format detection.
    """

    del filename, declared_content_type

    if not isinstance(content, bytes) or not content:
        raise DocumentValidationError("The uploaded document is empty.")

    if len(content) > MAX_DOCUMENT_BYTES:
        raise DocumentValidationError(
            "The uploaded document exceeds the 10 MB limit."
        )

    if content.startswith(b"%PDF-"):
        return _validate_pdf(content)

    return _validate_image(content)


def _validate_pdf(content: bytes) -> DocumentMetadata:
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.is_encrypted:
                raise DocumentValidationError(
                    "Password-protected PDFs are not supported."
                )

            if not document.is_pdf:
                raise DocumentValidationError(
                    "The uploaded document is not a valid PDF."
                )

            page_count = document.page_count

            if page_count < 1:
                raise DocumentValidationError(
                    "The PDF does not contain any pages."
                )

            if page_count > MAX_PDF_PAGES:
                raise DocumentValidationError(
                    f"PDFs may contain at most {MAX_PDF_PAGES} pages."
                )

    except DocumentValidationError:
        raise
    except Exception as exc:
        raise DocumentValidationError(
            "The uploaded PDF is invalid or cannot be read."
        ) from exc

    return DocumentMetadata(
        document_type=DocumentType.PDF,
        mime_type="application/pdf",
        size_bytes=len(content),
        page_count=page_count,
    )


def _validate_image(content: bytes) -> DocumentMetadata:
    try:
        with Image.open(BytesIO(content)) as image:
            image_format = image.format

            if image_format not in SUPPORTED_IMAGE_FORMATS:
                raise DocumentValidationError(
                    "Only PNG, JPEG and WEBP images are supported."
                )

            if getattr(image, "is_animated", False):
                raise DocumentValidationError(
                    "Animated images are not supported."
                )

            width, height = image.size

            if width < 1 or height < 1:
                raise DocumentValidationError(
                    "The uploaded image has invalid dimensions."
                )

            if width * height > MAX_IMAGE_PIXELS:
                raise DocumentValidationError(
                    "The uploaded image exceeds the 20 megapixel limit."
                )

            image.verify()

    except DocumentValidationError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise DocumentValidationError(
            "The uploaded image is invalid or cannot be decoded."
        ) from exc

    return DocumentMetadata(
        document_type=DocumentType.IMAGE,
        mime_type=SUPPORTED_IMAGE_FORMATS[image_format],
        size_bytes=len(content),
        page_count=1,
        image_width=width,
        image_height=height,
    )

from io import BytesIO

import pymupdf
import pytest
from PIL import Image

from app.services.billsense.document_validator import (
    DocumentType,
    DocumentValidationError,
    MAX_DOCUMENT_BYTES,
    validate_document,
)


def create_image(format="PNG", size=(200, 200)):
    image = Image.new("RGB", size, "white")
    output = BytesIO()
    image.save(output, format=format)
    return output.getvalue()


def create_pdf(page_count=1, encryption=pymupdf.PDF_ENCRYPT_NONE):
    document = pymupdf.open()

    for _ in range(page_count):
        document.new_page()

    if encryption == pymupdf.PDF_ENCRYPT_NONE:
        output = document.tobytes(encryption=encryption)
    else:
        output = document.tobytes(
            encryption=encryption,
            owner_pw="owner-password",
            user_pw="user-password",
        )

    document.close()
    return output


def test_valid_png():
    result = validate_document(create_image("PNG"))

    assert result.document_type == DocumentType.IMAGE
    assert result.mime_type == "image/png"
    assert result.page_count == 1
    assert result.image_width == 200


def test_valid_jpeg():
    result = validate_document(create_image("JPEG"))

    assert result.document_type == DocumentType.IMAGE
    assert result.mime_type == "image/jpeg"


def test_valid_webp():
    result = validate_document(create_image("WEBP"))

    assert result.document_type == DocumentType.IMAGE
    assert result.mime_type == "image/webp"


def test_valid_pdf():
    result = validate_document(create_pdf())

    assert result.document_type == DocumentType.PDF
    assert result.mime_type == "application/pdf"
    assert result.page_count == 1


def test_rejects_empty_document():
    with pytest.raises(DocumentValidationError, match="empty"):
        validate_document(b"")


def test_rejects_oversized_document():
    content = b"x" * (MAX_DOCUMENT_BYTES + 1)

    with pytest.raises(DocumentValidationError, match="10 MB"):
        validate_document(content)


def test_rejects_invalid_file():
    with pytest.raises(DocumentValidationError, match="invalid"):
        validate_document(b"not a real document")


def test_rejects_password_protected_pdf():
    content = create_pdf(encryption=pymupdf.PDF_ENCRYPT_AES_256)

    with pytest.raises(DocumentValidationError, match="Password-protected"):
        validate_document(content)


def test_rejects_pdf_with_too_many_pages():
    content = create_pdf(page_count=11)

    with pytest.raises(DocumentValidationError, match="at most 10"):
        validate_document(content)


def test_rejects_unsupported_image_format():
    image = Image.new("RGB", (100, 100), "white")
    output = BytesIO()
    image.save(output, format="BMP")

    with pytest.raises(DocumentValidationError, match="PNG, JPEG and WEBP"):
        validate_document(output.getvalue())


def test_rejects_mime_type_spoofing():
    content = create_image("PNG")

    result = validate_document(
        content,
        filename="electricity_bill.jpg",
        declared_content_type="image/jpeg",
    )

    assert result.mime_type == "image/png"

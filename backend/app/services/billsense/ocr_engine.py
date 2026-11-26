from dataclasses import dataclass
from io import BytesIO
from threading import Lock
from time import perf_counter

import numpy as np
import pymupdf
from PIL import Image
from rapidocr import RapidOCR

from app.services.billsense.document_validator import (
    DocumentType,
    MAX_IMAGE_PIXELS,
    validate_document,
)


PDF_RENDER_SCALE = 2.0
MIN_NATIVE_TEXT_LENGTH = 15


@dataclass(frozen=True)
class OCRLine:
    text: str
    confidence: float | None
    bounding_box: tuple[tuple[float, float], ...] | None


@dataclass(frozen=True)
class OCRPage:
    page_number: int
    text: str
    lines: tuple[OCRLine, ...]
    extraction_method: str
    processing_time_ms: float


@dataclass(frozen=True)
class OCRResult:
    document_type: DocumentType
    full_text: str
    pages: tuple[OCRPage, ...]
    processing_time_ms: float
    average_confidence: float | None


_engine = None
_engine_lock = Lock()


def _get_ocr_engine():
    global _engine

    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = RapidOCR()

    return _engine


def _run_image_ocr(image: Image.Image, page_number: int) -> OCRPage:
    started = perf_counter()

    image = image.convert("RGB")
    output = _get_ocr_engine()(image)

    texts = output.txts or ()
    scores = output.scores or ()
    boxes = output.boxes

    lines = []

    for index, text in enumerate(texts):
        text = str(text).strip()

        if not text:
            continue

        confidence = (
            float(scores[index])
            if index < len(scores) and scores[index] is not None
            else None
        )

        bounding_box = None

        if boxes is not None and index < len(boxes):
            try:
                bounding_box = tuple(
                    (float(point[0]), float(point[1]))
                    for point in boxes[index]
                )
            except (TypeError, ValueError, IndexError):
                bounding_box = None

        lines.append(
            OCRLine(
                text=text,
                confidence=confidence,
                bounding_box=bounding_box,
            )
        )

    return OCRPage(
        page_number=page_number,
        text="\n".join(line.text for line in lines),
        lines=tuple(lines),
        extraction_method="rapidocr",
        processing_time_ms=(perf_counter() - started) * 1000,
    )


def _process_image(content: bytes) -> tuple[OCRPage, ...]:
    with Image.open(BytesIO(content)) as image:
        image.load()
        return (_run_image_ocr(image.copy(), 1),)


def _process_pdf(content: bytes) -> tuple[OCRPage, ...]:
    results = []

    with pymupdf.open(stream=content, filetype="pdf") as document:
        for index, page in enumerate(document):
            started = perf_counter()

            native_text = page.get_text("text").strip()

            if len(native_text) >= MIN_NATIVE_TEXT_LENGTH:
                lines = tuple(
                    OCRLine(text=line.strip(), confidence=None, bounding_box=None)
                    for line in native_text.splitlines()
                    if line.strip()
                )

                results.append(
                    OCRPage(
                        page_number=index + 1,
                        text="\n".join(line.text for line in lines),
                        lines=lines,
                        extraction_method="pdf_text",
                        processing_time_ms=(perf_counter() - started) * 1000,
                    )
                )
                continue

            rect = page.rect
            width = max(1, int(rect.width * PDF_RENDER_SCALE))
            height = max(1, int(rect.height * PDF_RENDER_SCALE))

            if width * height > MAX_IMAGE_PIXELS:
                scale = (MAX_IMAGE_PIXELS / (rect.width * rect.height)) ** 0.5
                matrix = pymupdf.Matrix(scale, scale)
            else:
                matrix = pymupdf.Matrix(PDF_RENDER_SCALE, PDF_RENDER_SCALE)

            pixmap = page.get_pixmap(
                matrix=matrix,
                colorspace=pymupdf.csRGB,
                alpha=False,
            )

            if pixmap.width * pixmap.height > MAX_IMAGE_PIXELS:
                raise ValueError("Rendered PDF page exceeds the pixel limit.")

            image = Image.frombytes(
                "RGB",
                (pixmap.width, pixmap.height),
                pixmap.samples,
            )

            results.append(_run_image_ocr(image, index + 1))

    return tuple(results)


def extract_document_text(content: bytes) -> OCRResult:
    """
    Extract text from a validated bill image or PDF.

    PDF text is extracted natively when available. Scanned pages and
    uploaded images are processed locally using RapidOCR.
    """
    metadata = validate_document(content)
    started = perf_counter()

    if metadata.document_type == DocumentType.PDF:
        pages = _process_pdf(content)
    else:
        pages = _process_image(content)

    confidences = [
        line.confidence
        for page in pages
        for line in page.lines
        if line.confidence is not None
    ]

    average_confidence = (
        sum(confidences) / len(confidences)
        if confidences
        else None
    )

    return OCRResult(
        document_type=metadata.document_type,
        full_text="\n\n".join(
            page.text for page in pages if page.text
        ),
        pages=pages,
        processing_time_ms=(perf_counter() - started) * 1000,
        average_confidence=average_confidence,
    )

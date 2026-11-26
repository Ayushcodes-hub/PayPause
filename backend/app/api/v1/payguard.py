
from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.exceptions import PayPauseException
from app.repositories.payment_passport import save_assessment
import logging

from app.schemas.common import APIResponse
from app.schemas.payguard import (
    PaymentInputType,
    PayGuardAssessment,
    PayGuardRequest,
)

from app.services.payguard.risk_engine import build_risk_assessment
from app.services.payguard.upi_analyzer import analyze_upi_id
from app.services.payguard.url_analyzer import analyze_payment_url
from app.services.payguard.upi_qr_parser import extract_upi_id_from_qr
from app.services.payguard.qr_decoder import (
    MAX_IMAGE_BYTES,
    decode_qr_image,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/payguard",
    tags=["PayGuard"],
)


@router.post(
    "/assess",
    response_model=APIResponse[PayGuardAssessment],
    summary="Assess payment safety",
    description=(
        "Analyze UPI identifiers and payment URLs using "
        "deterministic, local risk screening."
    ),
)
def assess_payment(
    request: PayGuardRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[PayGuardAssessment]:
    """
    Generate an evidence-based payment risk assessment.

    Authentication is verified through Supabase.
    Submitted payment URLs are analyzed locally and never fetched.
    """

    upi_analysis = None
    url_analysis = None

    if request.input_type in (
        PaymentInputType.UPI,
        PaymentInputType.BOTH,
    ):
        upi_analysis = analyze_upi_id(request.upi_id)

    if request.input_type in (
        PaymentInputType.URL,
        PaymentInputType.BOTH,
    ):
        url_analysis = analyze_payment_url(request.payment_url)

    assessment = build_risk_assessment(
        input_type=request.input_type,
        upi_analysis=upi_analysis,
        url_analysis=url_analysis,
    )

    try:
        save_assessment(str(current_user.id), assessment)
    except Exception:
        logger.exception("Could not save PayGuard assessment to Payment Passport.")

    return APIResponse[PayGuardAssessment](
        success=True,
        message="Payment risk assessment completed.",
        data=assessment,
    )


@router.post(
    "/assess-qr",
    response_model=APIResponse[PayGuardAssessment],
    summary="Assess payment QR code",
    description=(
        "Decode an uploaded QR image locally and assess "
        "its UPI or URL payload using PayGuard."
    ),
)
async def assess_payment_qr(
    qr_image: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[PayGuardAssessment]:
    """
    Assess a QR payment code.

    The image is processed locally.
    Decoded payloads are never returned to the client.
    URLs are analyzed locally and never fetched.
    """

    try:
        image_bytes = await qr_image.read(MAX_IMAGE_BYTES + 1)
    finally:
        await qr_image.close()

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise PayPauseException(
            message="Uploaded QR image exceeds the maximum allowed size.",
            code="QR_IMAGE_TOO_LARGE",
            status_code=413,
        )

    try:
        decoded = await run_in_threadpool(
            decode_qr_image,
            image_bytes,
        )
    except ValueError as exc:
        raise PayPauseException(
            message=str(exc),
            code="QR_DECODE_FAILED",
            status_code=422,
        ) from exc

    if decoded.payload_type == "upi":
        input_type = PaymentInputType.UPI

        try:
            upi_id = extract_upi_id_from_qr(decoded.payload)
        except ValueError as exc:
            raise PayPauseException(
                message=str(exc),
                code="INVALID_UPI_QR_PAYLOAD",
                status_code=422,
            ) from exc

        upi_analysis = analyze_upi_id(upi_id)
        url_analysis = None

    elif decoded.payload_type == "url":
        input_type = PaymentInputType.URL

        upi_analysis = None
        url_analysis = analyze_payment_url(decoded.payload)

    else:
        raise PayPauseException(
            message=(
                "The QR code does not contain a supported "
                "UPI or HTTP/HTTPS payload."
            ),
            code="UNSUPPORTED_QR_PAYLOAD",
            status_code=422,
        )

    assessment = build_risk_assessment(
        input_type=input_type,
        upi_analysis=upi_analysis,
        url_analysis=url_analysis,
    )

    try:
        save_assessment(str(current_user.id), assessment)
    except Exception:
        logger.exception("Could not save QR assessment to Payment Passport.")

    return APIResponse[PayGuardAssessment](
        success=True,
        message="QR payment risk assessment completed.",
        data=assessment,
    )

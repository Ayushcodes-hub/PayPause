import json
import logging

from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.services.ai.groq_provider import (
    AIProviderError,
    AIProviderNotConfigured,
    get_ai_provider,
)
from app.core.exceptions import PayPauseException
from app.schemas.common import APIResponse
from app.schemas.billsense import (
    BillSenseAssessment,
    BillSenseAIInsights,
    BillSenseField,
    BillSenseFields,
    BillSenseIssue,
    ConsumptionAnalysisResponse,
)
from app.services.billsense.document_validator import (
    MAX_DOCUMENT_BYTES,
    DocumentValidationError,
)
from app.services.billsense.ocr_engine import extract_document_text
from app.services.billsense.bill_parser import (
    apply_ocr_confidence,
    parse_electricity_bill,
)
from app.services.billsense.bill_validator import validate_bill
from app.services.billsense.consumption_analyzer import analyze_consumption


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/billsense",
    tags=["BillSense"],
)


def _analyze_bill(content: bytes) -> BillSenseAssessment:
    ocr_result = extract_document_text(content)

    if not ocr_result.full_text.strip():
        raise ValueError(
            "No readable text could be extracted from this document."
        )

    bill = parse_electricity_bill(ocr_result.full_text)
    bill = apply_ocr_confidence(
        bill,
        tuple(line for page in ocr_result.pages for line in page.lines),
    )
    validation = validate_bill(bill)
    consumption = analyze_consumption(bill)

    fields = BillSenseFields(
        **{
            name: BillSenseField(
                value=getattr(bill, name).value,
                source_text=getattr(bill, name).source_text,
                confidence=getattr(bill, name).confidence,
            )
            for name in BillSenseFields.model_fields
        }
    )

    return BillSenseAssessment(
        document_type=ocr_result.document_type.value,
        fields=fields,
        is_valid=validation.is_valid,
        validation_issues=[
            BillSenseIssue(
                code=issue.code,
                message=issue.message,
                severity=issue.severity,
            )
            for issue in validation.issues
        ],
        consumption=ConsumptionAnalysisResponse(
            units_consumed_kwh=consumption.units_consumed_kwh,
            is_derived=consumption.is_derived,
            daily_average_kwh=consumption.daily_average_kwh,
            billing_days=consumption.billing_days,
            previous_consumption_kwh=consumption.previous_consumption_kwh,
            change_percentage=consumption.change_percentage,
            usage_status=consumption.usage_status,
            observations=list(consumption.observations),
        ),
        extracted_text=ocr_result.full_text,
        ocr_pages=len(ocr_result.pages),
        average_ocr_confidence=ocr_result.average_confidence,
        processing_time_ms=ocr_result.processing_time_ms,
    )


@router.post(
    "/analyze",
    response_model=APIResponse[BillSenseAssessment],
    summary="Analyze an Indian electricity bill",
    description=(
        "Extract electricity bill information using local OCR "
        "and deterministic financial validation."
    ),
)
async def analyze_electricity_bill(
    bill_file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[BillSenseAssessment]:

    try:
        content = await bill_file.read(MAX_DOCUMENT_BYTES + 1)
    finally:
        await bill_file.close()

    if len(content) > MAX_DOCUMENT_BYTES:
        raise PayPauseException(
            message="Uploaded electricity bill exceeds the 10 MB limit.",
            code="BILLSENSE_DOCUMENT_TOO_LARGE",
            status_code=413,
        )

    try:
        assessment = await run_in_threadpool(
            _analyze_bill,
            content,
        )
    except DocumentValidationError as exc:
        raise PayPauseException(
            message=str(exc),
            code="BILLSENSE_INVALID_DOCUMENT",
            status_code=422,
        ) from exc
    except ValueError as exc:
        raise PayPauseException(
            message=str(exc),
            code="BILLSENSE_ANALYSIS_FAILED",
            status_code=422,
        ) from exc

    assessment.ai_insights = await _generate_ai_insights(assessment)

    return APIResponse[BillSenseAssessment](
        success=True,
        message="Electricity bill analysis completed.",
        data=assessment,
    )



async def _generate_ai_insights(
    assessment: BillSenseAssessment,
) -> BillSenseAIInsights | None:
    """Generate optional explanations from deterministic bill results."""

    if not settings.AI_API_KEY or not settings.AI_MODEL:
        return None

    consumption = assessment.consumption

    safe_data = {
        "is_valid": assessment.is_valid,
        "validation_issues": [
            {
                "code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
            }
            for issue in assessment.validation_issues
        ],
        "consumption": {
            "units_consumed_kwh": consumption.units_consumed_kwh,
            "daily_average_kwh": consumption.daily_average_kwh,
            "billing_days": consumption.billing_days,
            "change_percentage": consumption.change_percentage,
            "usage_status": consumption.usage_status,
            "observations": consumption.observations,
        },
        "total_amount_inr": assessment.fields.total_amount_inr.value,
    }

    system_prompt = (
        "You are PayPause BillSense, a careful electricity-bill "
        "explanation assistant. Explain only the supplied facts. "
        "Never invent charges, readings, tariffs, or savings. "
        "Do not override validation results or claim a bill is authentic. "
        "Return concise plain text with an explanation followed by "
        "a section titled Recommendations and 2 to 4 practical suggestions."
    )

    user_prompt = (
        "Explain these already-computed electricity bill results "
        "in simple language. Clearly distinguish verified calculations "
        "from possible explanations. If validation issues exist, "
        "tell the user to verify the original bill.\n\n"
        + json.dumps(safe_data, ensure_ascii=False)
    )

    try:
        provider = get_ai_provider()
        response = await provider.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=600,
        )

        parts = response.split("Recommendations", maxsplit=1)
        explanation = parts[0].strip()
        recommendations = []

        if len(parts) == 2:
            recommendations = [
                line.lstrip("-?* ").strip()
                for line in parts[1].splitlines()
                if line.strip() and line.strip() not in {":", "-"}
            ]

        return BillSenseAIInsights(
            explanation=explanation or response,
            recommendations=recommendations[:5],
        )

    except AIProviderNotConfigured:
        return None
    except AIProviderError:
        logger.warning(
            "BillSense AI insights unavailable; returning deterministic analysis."
        )
        return None
    except Exception:
        logger.exception(
            "Unexpected BillSense AI error; returning deterministic analysis."
        )
        return None

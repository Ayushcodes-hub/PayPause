from fastapi import APIRouter, Depends, Query

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.exceptions import PayPauseException
from app.repositories.payment_passport import (
    list_assessments,
    get_assessment,
    delete_assessment,
)
from app.schemas.common import APIResponse

router = APIRouter(
    prefix="/payment-passport",
    tags=["Payment Passport"],
)


@router.get("/assessments", response_model=APIResponse[dict])
def passport_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    records = list_assessments(str(current_user.id), limit, offset)
    return APIResponse(
        success=True,
        message="Payment Passport history retrieved.",
        data={"items": records, "count": len(records)},
    )


@router.get("/assessments/{assessment_id}", response_model=APIResponse[dict])
def passport_assessment(
    assessment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    record = get_assessment(str(current_user.id), assessment_id)
    if record is None:
        raise PayPauseException(
            message="Passport assessment was not found.",
            code="PASSPORT_ASSESSMENT_NOT_FOUND",
            status_code=404,
        )
    return APIResponse(
        success=True,
        message="Payment Passport assessment retrieved.",
        data=record,
    )


@router.delete("/assessments/{assessment_id}", response_model=APIResponse[dict])
def remove_passport_assessment(
    assessment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    deleted = delete_assessment(str(current_user.id), assessment_id)
    if not deleted:
        raise PayPauseException(
            message="Passport assessment was not found.",
            code="PASSPORT_ASSESSMENT_NOT_FOUND",
            status_code=404,
        )
    return APIResponse(
        success=True,
        message="Payment Passport assessment deleted.",
        data={"assessment_id": assessment_id},
    )

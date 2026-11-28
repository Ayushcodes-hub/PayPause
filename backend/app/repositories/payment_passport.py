import logging

from app.core.supabase import get_supabase_admin_client
from app.schemas.payguard import PayGuardAssessment

logger = logging.getLogger(__name__)


def save_assessment(user_id: str, assessment: PayGuardAssessment) -> None:
    # Persist only the structured assessment, never the original UPI ID or URL.
    payload = assessment.model_dump(mode="json")
    client = get_supabase_admin_client()

    client.table("payment_passport_assessments").insert({
        "user_id": user_id,
        "assessment_id": assessment.assessment_id,
        "risk_score": assessment.risk_score,
        "risk_level": assessment.risk_level.value,
        "input_type": assessment.input_type.value,
        "assessment": payload,
    }).execute()


def list_assessments(user_id: str, limit: int = 50, offset: int = 0):
    response = (
        get_supabase_admin_client()
        .table("payment_passport_assessments")
        .select("assessment_id,risk_score,risk_level,input_type,created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return response.data or []


def get_assessment(user_id: str, assessment_id: str):
    response = (
        get_supabase_admin_client()
        .table("payment_passport_assessments")
        .select("assessment_id,risk_score,risk_level,input_type,assessment,created_at")
        .eq("user_id", user_id)
        .eq("assessment_id", assessment_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def delete_assessment(user_id: str, assessment_id: str) -> bool:
    response = (
        get_supabase_admin_client()
        .table("payment_passport_assessments")
        .delete()
        .eq("user_id", user_id)
        .eq("assessment_id", assessment_id)
        .execute()
    )
    return bool(response.data)

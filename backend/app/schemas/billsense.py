from pydantic import BaseModel, Field


class BillSenseField(BaseModel):
    value: str | float | None = None
    source_text: str | None = None
    confidence: float | None = None


class BillSenseFields(BaseModel):
    provider: BillSenseField
    consumer_number: BillSenseField
    consumer_name: BillSenseField
    bill_number: BillSenseField
    billing_period: BillSenseField
    issue_date: BillSenseField
    due_date: BillSenseField
    units_consumed_kwh: BillSenseField
    previous_reading: BillSenseField
    current_reading: BillSenseField
    total_amount_inr: BillSenseField
    energy_charges_inr: BillSenseField
    fixed_charges_inr: BillSenseField
    taxes_inr: BillSenseField
    late_fee_inr: BillSenseField


class BillSenseIssue(BaseModel):
    code: str
    message: str
    severity: str


class ConsumptionAnalysisResponse(BaseModel):
    units_consumed_kwh: float | None
    is_derived: bool
    daily_average_kwh: float | None
    billing_days: int | None
    previous_consumption_kwh: float | None
    change_percentage: float | None
    usage_status: str
    observations: list[str] = Field(default_factory=list)


class BillSenseAssessment(BaseModel):
    document_type: str
    fields: BillSenseFields
    is_valid: bool
    validation_issues: list[BillSenseIssue]
    consumption: ConsumptionAnalysisResponse
    extracted_text: str
    ocr_pages: int
    average_ocr_confidence: float | None
    processing_time_ms: float
    ai_insights: BillSenseAIInsights | None = None
    disclaimer: str = (
        "Automated document extraction and screening may contain errors. "
        "Verify important bill details against the original document."
    )


class BillSenseAIInsights(BaseModel):
    explanation: str
    recommendations: list[str] = Field(default_factory=list)

from pydantic import BaseModel, Field, validator
from typing import Optional
import re


class ActionResult(BaseModel):
    success: bool
    message: str

class HeuristicUpdate(BaseModel):
    rule: Optional[str] = Field(None, max_length=1000)
    explanation: Optional[str] = Field(None, max_length=5000)
    domain: Optional[str] = Field(None, max_length=100)
    is_golden: Optional[bool] = None

    @validator('rule', 'explanation', 'domain')
    def strip_and_validate(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v


class DecisionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    context: str = Field(..., min_length=1, max_length=10000)
    options_considered: Optional[str] = Field(None, max_length=5000)
    decision: str = Field(..., min_length=1, max_length=5000)
    rationale: str = Field(..., min_length=1, max_length=5000)
    domain: Optional[str] = Field(None, max_length=100)
    files_touched: Optional[str] = Field(None, max_length=5000)
    tests_added: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = Field("accepted", pattern="^(accepted|rejected|superseded|deprecated)$")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(20, ge=1, le=100)


class SpikeReportCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    topic: str = Field(..., min_length=1, max_length=200)
    question: str = Field(..., min_length=1, max_length=1000)
    findings: str = Field(..., min_length=1, max_length=50000)
    gotchas: Optional[str] = Field(None, max_length=10000)
    resources: Optional[str] = Field(None, max_length=10000)
    time_invested_minutes: Optional[int] = Field(None, ge=0, le=10000)
    domain: Optional[str] = Field(None, max_length=100)
    tags: Optional[str] = Field(None, max_length=500)


class AssumptionCreate(BaseModel):
    assumption: str = Field(..., min_length=1, max_length=1000)
    context: str = Field(..., min_length=1, max_length=5000)
    source: Optional[str] = Field(None, max_length=500)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    status: Optional[str] = Field("active", pattern="^(active|retired|challenged)$")
    domain: Optional[str] = Field(None, max_length=100)


class InvariantCreate(BaseModel):
    statement: str = Field(..., min_length=1, max_length=1000)
    rationale: str = Field(..., min_length=1, max_length=5000)
    domain: Optional[str] = Field(None, max_length=100)
    scope: Optional[str] = Field(None, max_length=500)
    validation_type: Optional[str] = Field(None, max_length=100)
    validation_code: Optional[str] = Field(None, max_length=10000)
    severity: Optional[str] = Field("medium", pattern="^(critical|high|medium|low)$")
    status: Optional[str] = Field("active", pattern="^(active|retired|investigating)$")


class DecisionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    context: Optional[str] = Field(None, min_length=1, max_length=10000)
    options_considered: Optional[str] = Field(None, max_length=5000)
    decision: Optional[str] = Field(None, min_length=1, max_length=5000)
    rationale: Optional[str] = Field(None, min_length=1, max_length=5000)
    domain: Optional[str] = Field(None, max_length=100)
    files_touched: Optional[str] = Field(None, max_length=5000)
    tests_added: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = Field(None, pattern="^(accepted|rejected|superseded|deprecated)$")


class AssumptionUpdate(BaseModel):
    assumption: Optional[str] = Field(None, min_length=1, max_length=1000)
    context: Optional[str] = Field(None, min_length=1, max_length=5000)
    source: Optional[str] = Field(None, max_length=500)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    status: Optional[str] = Field(None, pattern="^(active|retired|challenged)$")
    domain: Optional[str] = Field(None, max_length=100)


class InvariantUpdate(BaseModel):
    statement: Optional[str] = Field(None, min_length=1, max_length=1000)
    rationale: Optional[str] = Field(None, min_length=1, max_length=5000)
    domain: Optional[str] = Field(None, max_length=100)
    scope: Optional[str] = Field(None, max_length=500)
    validation_type: Optional[str] = Field(None, max_length=100)
    validation_code: Optional[str] = Field(None, max_length=10000)
    severity: Optional[str] = Field(None, pattern="^(critical|high|medium|low)$")
    status: Optional[str] = Field(None, pattern="^(active|retired|investigating)$")


class SpikeReportUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    topic: Optional[str] = Field(None, min_length=1, max_length=200)
    question: Optional[str] = Field(None, min_length=1, max_length=1000)
    findings: Optional[str] = Field(None, min_length=1, max_length=50000)
    gotchas: Optional[str] = Field(None, max_length=10000)
    resources: Optional[str] = Field(None, max_length=10000)
    time_invested_minutes: Optional[int] = Field(None, ge=0, le=10000)
    domain: Optional[str] = Field(None, max_length=100)
    tags: Optional[str] = Field(None, max_length=500)


class SpikeReportRate(BaseModel):
    spike_id: int = Field(..., gt=0)
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = Field(None, max_length=1000)


class OpenInEditorRequest(BaseModel):
    filepath: str = Field(..., min_length=1, max_length=1000)
    line_number: Optional[int] = Field(None, ge=1)


class FraudReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject|escalate)$")
    notes: Optional[str] = Field(None, max_length=5000)


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    workflow_data: Optional[str] = Field(None)

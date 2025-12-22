"""
Pydantic models for the Emergent Learning Dashboard API.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel


class HeuristicUpdate(BaseModel):
    rule: Optional[str] = None
    explanation: Optional[str] = None
    domain: Optional[str] = None
    is_golden: Optional[bool] = None


class DecisionCreate(BaseModel):
    title: str
    context: str
    options_considered: Optional[str] = None
    decision: str
    rationale: str
    domain: Optional[str] = None
    files_touched: Optional[str] = None
    tests_added: Optional[str] = None
    status: Optional[str] = "accepted"


class DecisionUpdate(BaseModel):
    title: Optional[str] = None
    context: Optional[str] = None
    options_considered: Optional[str] = None
    decision: Optional[str] = None
    rationale: Optional[str] = None
    domain: Optional[str] = None
    files_touched: Optional[str] = None
    tests_added: Optional[str] = None
    status: Optional[str] = None


class InvariantCreate(BaseModel):
    statement: str
    rationale: str
    domain: Optional[str] = None
    scope: Optional[str] = "codebase"  # codebase, module, function, runtime
    validation_type: Optional[str] = None  # manual, automated, test
    validation_code: Optional[str] = None
    severity: Optional[str] = "error"  # error, warning, info


class InvariantUpdate(BaseModel):
    statement: Optional[str] = None
    rationale: Optional[str] = None
    domain: Optional[str] = None
    scope: Optional[str] = None
    validation_type: Optional[str] = None
    validation_code: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None


class AssumptionCreate(BaseModel):
    assumption: str
    context: str
    source: Optional[str] = None
    confidence: Optional[float] = 0.5
    domain: Optional[str] = None


class AssumptionUpdate(BaseModel):
    assumption: Optional[str] = None
    context: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    status: Optional[str] = None
    domain: Optional[str] = None


class WorkflowCreate(BaseModel):
    name: str
    description: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class QueryRequest(BaseModel):
    query: str
    limit: int = 20


class SpikeReportCreate(BaseModel):
    title: str
    topic: str
    question: str
    findings: str
    gotchas: Optional[str] = None
    resources: Optional[str] = None
    time_invested_minutes: Optional[int] = None
    domain: Optional[str] = None
    tags: Optional[str] = None


class SpikeReportUpdate(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    question: Optional[str] = None
    findings: Optional[str] = None
    gotchas: Optional[str] = None
    resources: Optional[str] = None
    time_invested_minutes: Optional[int] = None
    domain: Optional[str] = None
    tags: Optional[str] = None


class SpikeReportRate(BaseModel):
    score: float  # 0-5 usefulness score


class FraudReviewRequest(BaseModel):
    outcome: str  # 'true_positive' or 'false_positive'
    reviewed_by: Optional[str] = 'human'
    notes: Optional[str] = None


class ActionResult(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None


class OpenInEditorRequest(BaseModel):
    path: str
    line: Optional[int] = None

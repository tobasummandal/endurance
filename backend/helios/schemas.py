"""Pydantic response/request schemas mirroring the shared API contract."""
from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


IssueSeverity = Literal["low", "medium", "high", "critical"]
IssueCategory = Literal[
    "off_by_one",
    "unit_mismatch",
    "numerical_instability",
    "float_equality",
    "mutable_default",
    "module_state",
    "bare_except",
    "shape_assumption",
    "boundary_condition",
    "other",
]
IssueSource = Literal["static", "llm"]
SessionStatus = Literal["created", "audited", "fixing", "verified", "routed"]
RoutePattern = Literal[
    "nested_numeric_loop",
    "matmul",
    "fft",
    "elementwise_ufunc",
    "monte_carlo",
    "other",
]
Complexity = Literal["low", "medium", "high"]
Verdict = Literal["all_agree", "partial_disagree", "all_disagree", "error"]


class SessionCreate(BaseModel):
    filename: str
    source_code: str


class SessionOut(BaseModel):
    id: str
    filename: str
    language: Literal["python"] = "python"
    source_code: str
    created_at: datetime
    status: SessionStatus


class IssueOut(BaseModel):
    id: str
    session_id: str
    category: IssueCategory
    severity: IssueSeverity
    line_start: int
    line_end: int
    title: str
    explanation: str
    source: IssueSource


class FixOut(BaseModel):
    id: str
    session_id: str
    issue_id: str
    fixed_code: str
    diff_summary: str
    created_at: datetime


class TestCaseResult(BaseModel):
    index: int
    input_preview: str
    original_output_preview: str
    fix_output_preview: str
    agreed: bool
    original_ms: float
    fix_ms: float
    notes: Optional[str] = None


class VerificationOut(BaseModel):
    id: str
    fix_id: str
    test_cases: list[TestCaseResult]
    passed: int
    failed: int
    overall_verdict: Verdict
    created_at: datetime


class RouteCandidate(BaseModel):
    line_start: int
    line_end: int
    pattern: RoutePattern
    estimated_speedup: str
    complexity: Complexity
    rationale: str


class RouteResultOut(BaseModel):
    session_id: str
    gpu_candidates: list[RouteCandidate]
    quantum_candidates: list = Field(default_factory=list)
    created_at: datetime


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    error: ErrorBody


# ---- Live (interactive) audit ----

class LiveAuditRequest(BaseModel):
    filename: str = "draft.py"
    source_code: str
    session_token: str | None = None  # opaque client-supplied id for caching/cancel


class LiveFinding(BaseModel):
    category: IssueCategory
    severity: IssueSeverity
    line_start: int
    line_end: int
    title: str
    explanation: str
    source: IssueSource


class LiveStaticResponse(BaseModel):
    findings: list[LiveFinding]
    elapsed_ms: float


class LiveFixPreviewRequest(BaseModel):
    filename: str = "draft.py"
    source_code: str
    finding: LiveFinding


class LiveFixPreviewResponse(BaseModel):
    fixed_code: str
    diff_summary: str


class LiveStatsResponse(BaseModel):
    static_calls: int
    stream_calls: int
    fix_preview_calls: int
    cache_hits: int
    cache_misses: int
    cancellations: int
    rate_limited: int
    active_tokens: int

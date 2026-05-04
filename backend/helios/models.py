from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlmodel import SQLModel, Field, Column, JSON


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Session(SQLModel, table=True):
    __tablename__ = "sessions"
    id: str = Field(default_factory=_uuid, primary_key=True)
    filename: str
    language: str = "python"
    source_code: str
    status: str = "created"  # created | audited | fixing | verified | routed
    created_at: datetime = Field(default_factory=_now)


class Issue(SQLModel, table=True):
    __tablename__ = "issues"
    id: str = Field(default_factory=_uuid, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    category: str
    severity: str
    line_start: int
    line_end: int
    title: str
    explanation: str
    source: str  # static | llm
    created_at: datetime = Field(default_factory=_now)


class Fix(SQLModel, table=True):
    __tablename__ = "fixes"
    id: str = Field(default_factory=_uuid, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    issue_id: str = Field(foreign_key="issues.id", index=True)
    fixed_code: str
    diff_summary: str
    created_at: datetime = Field(default_factory=_now)


class Verification(SQLModel, table=True):
    __tablename__ = "verifications"
    id: str = Field(default_factory=_uuid, primary_key=True)
    fix_id: str = Field(foreign_key="fixes.id", index=True)
    test_cases: list = Field(default_factory=list, sa_column=Column(JSON))
    passed: int = 0
    failed: int = 0
    overall_verdict: str = "error"  # all_agree | partial_disagree | all_disagree | error
    created_at: datetime = Field(default_factory=_now)


class RouteResult(SQLModel, table=True):
    __tablename__ = "route_results"
    id: str = Field(default_factory=_uuid, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    gpu_candidates: list = Field(default_factory=list, sa_column=Column(JSON))
    quantum_candidates: list = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)

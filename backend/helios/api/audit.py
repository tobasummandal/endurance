from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession, select

from ..analysis.llm_audit import merge_dedupe, run_llm_audit
from ..analysis.static import run_static_checks
from ..db import get_session
from ..errors import HeliosError
from ..models import Issue, Session
from ..schemas import IssueOut

router = APIRouter()


@router.post("/sessions/{session_id}/audit", response_model=list[IssueOut])
def audit(session_id: str, db: DBSession = Depends(get_session)) -> list[IssueOut]:
    s = db.get(Session, session_id)
    if not s:
        raise HeliosError(404, "not_found", "session not found")

    static = run_static_checks(s.source_code)
    llm = run_llm_audit(s.filename, s.source_code)
    merged = merge_dedupe(static, llm)

    # Replace any prior issues for this session (re-audit semantics).
    prior = db.exec(select(Issue).where(Issue.session_id == session_id)).all()
    for p in prior:
        db.delete(p)
    db.flush()

    issues = []
    for f in merged:
        issue = Issue(
            session_id=session_id,
            category=f["category"],
            severity=f["severity"],
            line_start=f["line_start"],
            line_end=f["line_end"],
            title=f["title"],
            explanation=f["explanation"],
            source=f["source"],
        )
        db.add(issue)
        issues.append(issue)

    s.status = "audited"
    db.add(s)
    db.commit()
    for i in issues:
        db.refresh(i)
    return [IssueOut.model_validate(i.model_dump()) for i in issues]


@router.get("/sessions/{session_id}/issues", response_model=list[IssueOut])
def list_issues(session_id: str, db: DBSession = Depends(get_session)) -> list[IssueOut]:
    if not db.get(Session, session_id):
        raise HeliosError(404, "not_found", "session not found")
    rows = db.exec(select(Issue).where(Issue.session_id == session_id)).all()
    return [IssueOut.model_validate(r.model_dump()) for r in rows]

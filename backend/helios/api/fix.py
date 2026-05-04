from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession

from ..analysis.fix_generator import generate_fix
from ..db import get_session
from ..errors import HeliosError
from ..models import Fix, Issue, Session
from ..schemas import FixOut

router = APIRouter()


@router.post("/sessions/{session_id}/issues/{issue_id}/fix", response_model=FixOut)
def create_fix(session_id: str, issue_id: str, db: DBSession = Depends(get_session)) -> FixOut:
    s = db.get(Session, session_id)
    if not s:
        raise HeliosError(404, "not_found", "session not found")
    issue = db.get(Issue, issue_id)
    if not issue or issue.session_id != session_id:
        raise HeliosError(404, "not_found", "issue not found")

    try:
        result = generate_fix(s.filename, s.source_code, issue.model_dump())
    except Exception as e:
        raise HeliosError(500, "fix_failed", f"fix generation failed: {e}")

    fix = Fix(
        session_id=session_id,
        issue_id=issue_id,
        fixed_code=result["fixed_code"],
        diff_summary=result["diff_summary"],
    )
    db.add(fix)
    s.status = "fixing"
    db.add(s)
    db.commit()
    db.refresh(fix)
    return FixOut.model_validate(fix.model_dump())


@router.get("/sessions/{session_id}/fixes/{fix_id}", response_model=FixOut)
def get_fix(session_id: str, fix_id: str, db: DBSession = Depends(get_session)) -> FixOut:
    fix = db.get(Fix, fix_id)
    if not fix or fix.session_id != session_id:
        raise HeliosError(404, "not_found", "fix not found")
    return FixOut.model_validate(fix.model_dump())

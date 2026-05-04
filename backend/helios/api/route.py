from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession

from ..analysis.route_classifier import classify
from ..db import get_session
from ..errors import HeliosError
from ..models import RouteResult, Session
from ..schemas import RouteCandidate, RouteResultOut

router = APIRouter()


@router.post("/sessions/{session_id}/route", response_model=RouteResultOut)
def route(session_id: str, db: DBSession = Depends(get_session)) -> RouteResultOut:
    s = db.get(Session, session_id)
    if not s:
        raise HeliosError(404, "not_found", "session not found")
    cands = classify(s.source_code)
    rr = RouteResult(
        session_id=session_id,
        gpu_candidates=cands,
        quantum_candidates=[],
    )
    db.add(rr)
    s.status = "routed"
    db.add(s)
    db.commit()
    db.refresh(rr)
    return RouteResultOut(
        session_id=session_id,
        gpu_candidates=[RouteCandidate.model_validate(c) for c in cands],
        quantum_candidates=[],
        created_at=rr.created_at,
    )

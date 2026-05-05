from fastapi import APIRouter, Depends, Query
from sqlmodel import Session as DBSession

from ..analysis.route_classifier import classify
from ..analysis.quantum_router import run as run_quantum_router
from ..db import get_session
from ..errors import HeliosError
from ..models import RouteResult, Session
from ..schemas import RouteCandidate, RouteResultOut

router = APIRouter()


@router.get("/quantum-router")
def quantum_router(eta: float = Query(5.0, ge=1.0, le=100.0)) -> dict:
    """Hybrid Immune-filter -> ATC scheduler demo. Pure deterministic fixture.

    Independent of any session — drives the live demo panel. Returns FIFO
    baseline schedule, ATC schedule across CPU+QPU lanes, immune-filter
    rejections, ATC priority queue, and a sensitivity sweep over eta.
    """
    return run_quantum_router(eta=eta)


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

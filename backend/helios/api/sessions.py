from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession, select

from ..config import settings
from ..db import get_session
from ..errors import HeliosError
from ..models import Session
from ..schemas import SessionCreate, SessionOut

router = APIRouter()


@router.post("/sessions", response_model=SessionOut)
def create_session(body: SessionCreate, db: DBSession = Depends(get_session)) -> SessionOut:
    if not body.source_code.strip():
        raise HeliosError(400, "empty_source", "source_code is empty")
    line_count = body.source_code.count("\n") + 1
    if line_count > settings.max_file_lines:
        raise HeliosError(
            400, "file_too_large",
            f"file has {line_count} lines, limit is {settings.max_file_lines}",
        )
    s = Session(filename=body.filename, source_code=body.source_code)
    db.add(s)
    db.commit()
    db.refresh(s)
    return SessionOut.model_validate(s.model_dump())


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(db: DBSession = Depends(get_session)) -> list[SessionOut]:
    rows = db.exec(select(Session).order_by(Session.created_at.desc())).all()
    return [SessionOut.model_validate(r.model_dump()) for r in rows]


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session_view(session_id: str, db: DBSession = Depends(get_session)) -> SessionOut:
    s = db.get(Session, session_id)
    if not s:
        raise HeliosError(404, "not_found", "session not found")
    return SessionOut.model_validate(s.model_dump())

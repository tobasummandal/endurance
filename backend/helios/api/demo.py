"""Hardcoded demo flow — bypasses LLM/sandbox so the 2-min walkthrough is deterministic.

All endpoints live under /api/demo/* and return canned payloads from
helios.demo.fixtures.payloads. The verify endpoint streams Server-Sent
Events with realistic gaps so the UI ticker animates.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, StreamingResponse

from ..demo.fixtures import payloads


router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/sessions")
def create_demo_session() -> dict:
    return payloads.session_payload()


@router.get("/sessions/{session_id}")
def get_demo_session(session_id: str) -> dict:
    return payloads.session_payload()


@router.get("/audit")
def demo_audit() -> list[dict]:
    return payloads.audit_payload()


@router.get("/issues/{issue_id}/trace")
def demo_trace(issue_id: str) -> dict:
    return payloads.reasoning_trace_payload(issue_id)


@router.get("/fix")
def demo_fix() -> dict:
    return payloads.fix_payload()


@router.get("/verify/stream")
async def demo_verify_stream() -> StreamingResponse:
    steps = payloads.verify_steps()
    final = payloads.verify_payload()

    async def gen():
        for i, step in enumerate(steps):
            yield f"event: step\ndata: {json.dumps({'index': i, **step, 'state': 'running'})}\n\n"
            await asyncio.sleep(step["ms"] / 1000)
            yield f"event: step\ndata: {json.dumps({'index': i, **step, 'state': 'done'})}\n\n"
        yield f"event: result\ndata: {json.dumps(final)}\n\n"
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/verify")
def demo_verify() -> dict:
    return payloads.verify_payload()


@router.get("/question")
def demo_question() -> dict:
    return payloads.question_payload()


@router.post("/question/answer")
def demo_question_answer(payload: dict) -> dict:
    # Echo for the trace; nothing persisted in demo mode.
    return {"ok": True, "answer": payload}


@router.get("/route")
def demo_route() -> dict:
    return payloads.route_payload()


@router.get("/trace.jsonl", response_class=PlainTextResponse)
def demo_trace_jsonl() -> str:
    trace = payloads.reasoning_trace_payload()
    fix = payloads.fix_payload()
    verify = payloads.verify_payload()
    lines = [
        json.dumps({"event": "audit", "issues": payloads.audit_payload()}),
        json.dumps({"event": "reasoning_trace", "trace": trace}),
        json.dumps({
            "event": "refactor",
            "decisions": fix["refactor_decisions"],
            "bug_fixes": fix["bug_fixes_applied"],
        }),
        json.dumps({"event": "verify", "verdict": verify["overall_verdict"], "cases": verify["test_cases"]}),
    ]
    return "\n".join(lines) + "\n"


@router.get("/verification_report.pdf")
def demo_pdf() -> StreamingResponse:
    # Minimal one-page PDF generated inline so the demo download button works
    # without a real PDF toolchain. Content is deliberately terse — investors
    # will glance at the filename and the green banner, not read the bytes.
    body = (
        b"BT /F1 12 Tf 60 760 Td "
        b"(Helios verification report) Tj 0 -20 Td "
        b"(File: mc_2deg_thermo_init.py) Tj 0 -20 Td "
        b"(Verdict: 12/12 cases agree, rtol=1e-9) Tj 0 -20 Td "
        b"(Original biased Cv ~0.3% on analytical test) Tj 0 -20 Td "
        b"(Refactor matches analytical solution) Tj ET"
    )
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length " + str(len(body)).encode() + b">>stream\n"
        + body + b"\nendstream endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF\n"
    )
    return StreamingResponse(
        iter([pdf]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=helios_verification_report.pdf"},
    )

"""
Gateway service — the orchestrator the Next.js UI talks to.

Endpoints:
  GET  /health              — health
  POST /solve               — synchronous: returns full result + audit
  GET  /solve/stream?prompt=...  — SSE: streams per-stage events for the UI animation
  GET  /audit               — recent gateway-level audit entries

Pipeline (mirrors CLAUDE.md):
  classifier → extractor → dispatcher → builder (template) → verifier (3 checks)
  → router (sponsor's 5-gate engine, calls our backends with payload)
  → SSE re-emission of every stage
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import AsyncIterator, Optional

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import translator, verifier, cot


ROUTER_URL = os.getenv("ROUTER_URL", "http://localhost:8000")

app = FastAPI(
    title="Quantum Routing Brain — Gateway",
    description="LLM translation + verification + SSE in front of the sponsor router",
    version="0.1.0",
)

# UI runs on a different origin (Next.js dev server :3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


_audit: list[dict] = []


class SolveRequest(BaseModel):
    prompt: str
    latency_budget_ms: Optional[int] = None
    classification_level: Optional[str] = None  # override
    task_id: Optional[str] = None  # for direct CSV-row submission


def _stage_event(stage: str, status: str, **data) -> dict:
    """Standard SSE event payload."""
    return {
        "event": f"{stage}.{status}",
        "data": json.dumps({"stage": stage, "status": status, "ts_ms": int(time.time() * 1000), **data}),
    }


async def _run_pipeline(req: SolveRequest) -> AsyncIterator[dict]:
    """Run the full pipeline as an async generator yielding SSE event dicts."""
    overrides = {}
    if req.latency_budget_ms is not None:
        overrides["latency_budget_ms"] = req.latency_budget_ms
    if req.classification_level is not None:
        overrides["classification_level"] = req.classification_level
    if req.task_id is not None:
        overrides["task_id"] = req.task_id

    # ── classifier ──
    yield _stage_event("classifier", "start", prompt=req.prompt)
    cls = translator.classify(req.prompt)
    yield _stage_event("classifier", "done", **cls)

    if cls.get("problem_type") in (None, "unknown", "qrng"):
        yield _stage_event(
            "pipeline",
            "abort",
            reason=f"problem_type={cls.get('problem_type')}; gateway demo supports vrp/maxcut/freq_coloring",
        )
        return

    pt = cls["problem_type"]

    # ── extractor ──
    yield _stage_event("extractor", "start", problem_type=pt)
    ext = translator.extract(req.prompt, pt)
    yield _stage_event("extractor", "done", **ext)
    params = ext["params"]

    # ── dispatcher (build router request body) ──
    yield _stage_event("dispatcher", "start")
    body = translator.dispatch(pt, params, overrides=overrides)
    yield _stage_event("dispatcher", "done", task_profile_row={k: v for k, v in body.items() if k != "payload"})

    # ── builder (template metadata, no execution yet) ──
    yield _stage_event("builder", "start")
    static = verifier.static_check(pt, params)
    yield _stage_event("builder", "done", qubits=static.get("qubits"), depth=static.get("depth"))

    # ── verifier ──
    yield _stage_event("verifier", "start")
    full_verify = verifier.verify(pt, params)
    yield _stage_event(
        "verifier.static",
        "pass" if full_verify["static"] and full_verify["static"]["passed"] else "fail",
        **(full_verify["static"] or {}),
    )
    if full_verify["simulator"]:
        yield _stage_event(
            "verifier.simulator",
            "pass" if full_verify["simulator"]["passed"] else "fail",
            **full_verify["simulator"],
        )
    if full_verify["cost_benefit"]:
        yield _stage_event(
            "verifier.cost_benefit",
            "pass" if full_verify["cost_benefit"]["passed"] else "fail",
            **full_verify["cost_benefit"],
        )

    # ── router (sponsor's 5-gate engine) ──
    yield _stage_event("router", "start")
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(f"{ROUTER_URL}/route", json=body)
            resp.raise_for_status()
            routing = resp.json()
        except Exception as e:
            yield _stage_event("router", "error", error=str(e))
            return

    # Stream each gate result as its own event so the UI can light pillars in sequence
    for i, (gate_key, gate_val) in enumerate(routing["gate_results"].items(), start=1):
        yield _stage_event(
            f"router.gate_{i}",
            "pass" if gate_val["passed"] else "fail",
            gate_name=gate_key,
            **gate_val,
        )
    yield _stage_event(
        "router",
        "decision",
        decision=routing["decision"],
        routed_to=routing["routed_to"],
        reasoning=routing["reasoning"],
    )

    # ── execution results (already run by router) ──
    if routing.get("classical_result"):
        yield _stage_event("execution.classical", "done", result=routing["classical_result"])
    if routing.get("quantum_result"):
        yield _stage_event("execution.quantum", "done", result=routing["quantum_result"])

    # ── audit + CoT envelope ──
    cot_xml = cot.envelope(
        task_id=body["task_id"],
        task_name=body["task_name"],
        decision=routing["decision"],
        classification_level=body["classification_level"],
        rationale=routing["reasoning"],
    )
    audit_entry = {
        "ts_ms": int(time.time() * 1000),
        "prompt": req.prompt,
        "classifier": cls,
        "extractor": ext,
        "task_profile_row": {k: v for k, v in body.items() if k != "payload"},
        "verifier": full_verify,
        "routing": routing,
        "cot_xml": cot_xml,
    }
    _audit.append(audit_entry)
    if len(_audit) > 100:
        _audit.pop(0)

    yield _stage_event("audit", "done", cot_xml=cot_xml)
    yield _stage_event("pipeline", "complete")


# ─── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "gateway",
        "router_url": ROUTER_URL,
        "gemini_enabled": os.getenv("GEMINI_API_KEY") is not None,
    }


@app.post("/solve")
async def solve(req: SolveRequest):
    """Synchronous: drain the pipeline, return last audit entry."""
    async for _ in _run_pipeline(req):
        pass
    return _audit[-1] if _audit else {"error": "no audit entry produced"}


@app.get("/solve/stream")
async def solve_stream(
    prompt: str,
    latency_budget_ms: Optional[int] = None,
    classification_level: Optional[str] = None,
    task_id: Optional[str] = None,
):
    """SSE stream of pipeline stages for the UI animation."""
    req = SolveRequest(
        prompt=prompt,
        latency_budget_ms=latency_budget_ms,
        classification_level=classification_level,
        task_id=task_id,
    )

    async def event_gen():
        async for ev in _run_pipeline(req):
            # sse-starlette expects {"event": ..., "data": ...}
            yield ev
            await asyncio.sleep(0.01)  # small breath so the UI can animate

    return EventSourceResponse(event_gen())


@app.get("/audit")
def get_audit():
    return {"total": len(_audit), "log": _audit}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

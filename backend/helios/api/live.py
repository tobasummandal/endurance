"""Live (interactive) audit endpoints — stateless, no DB writes.

Phase 1: POST /live/audit/static
Phase 2: POST /live/audit/stream  (SSE)
Phase 3: POST /live/fix/preview
Phase 4: GET  /live/stats         (telemetry)
"""
from __future__ import annotations
import asyncio
import json
import time
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse

from ..analysis.fix_generator import generate_fix
from ..analysis.llm_audit import merge_dedupe, run_llm_audit
from ..analysis.static import run_static_checks
from ..analysis.test_synthesizer import function_source as fn_source_text
from ..config import settings
from ..errors import HeliosError
from ..live.cache import cache
from ..live.inflight import inflight
from ..live.ratelimit import limiter
from ..live.stats import stats
from ..schemas import (
    LiveAuditRequest,
    LiveFinding,
    LiveFixPreviewRequest,
    LiveFixPreviewResponse,
    LiveStaticResponse,
    LiveStatsResponse,
)

router = APIRouter(prefix="/live")


def _client_token(req: LiveAuditRequest, x_session_token: str | None) -> str:
    return req.session_token or x_session_token or "anon"


def _check_size(source: str) -> None:
    n = source.count("\n") + 1
    if n > settings.live_max_file_lines:
        raise HeliosError(
            400, "file_too_large_for_live",
            f"live audit limit is {settings.live_max_file_lines} lines (got {n})",
        )


def _enforce_rate(token: str) -> None:
    if not limiter.take(token):
        stats.inc("rate_limited")
        raise HeliosError(429, "rate_limited", "live audit rate limit exceeded")


# ---------- Phase 1: static-only ----------

@router.post("/audit/static", response_model=LiveStaticResponse)
def live_static(
    body: LiveAuditRequest,
    x_session_token: str | None = Header(default=None),
) -> LiveStaticResponse:
    token = _client_token(body, x_session_token)
    _enforce_rate(token)
    _check_size(body.source_code)

    stats.inc("static_calls")
    t0 = time.perf_counter()
    findings = run_static_checks(body.source_code)
    elapsed = (time.perf_counter() - t0) * 1000.0
    return LiveStaticResponse(
        findings=[LiveFinding(**f) for f in findings],
        elapsed_ms=elapsed,
    )


# ---------- Phase 2: streaming (static + LLM) ----------

def _sse(event: str, payload) -> bytes:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n".encode()


async def _stream_generator(body: LiveAuditRequest, token: str, request: Request) -> AsyncIterator[bytes]:
    """Emit SSE events:
        static       -> immediate AST findings
        cache_hit    -> whole-file cache hit, no LLM call needed
        llm_partial  -> findings for a subset of functions (per-function audit)
        llm          -> consolidated llm findings (whole-file fallback)
        merged       -> static + llm merged + sorted
        done         -> stream complete
        error        -> recoverable error
    """
    yield _sse("hello", {"token": token, "ts": time.time()})

    # 1) static — instant
    static_findings = run_static_checks(body.source_code)
    yield _sse("static", static_findings)

    # 2) cache check (whole-file)
    cached_full = cache.lookup_full(token, body.source_code)
    if cached_full is not None:
        stats.inc("cache_hits")
        yield _sse("cache_hit", {"count": len(cached_full)})
        merged = merge_dedupe(static_findings, cached_full)
        yield _sse("merged", merged)
        yield _sse("done", {"reason": "full_cache"})
        return

    stats.inc("cache_misses")

    # 3) per-function diff cache: identify which functions need re-audit
    cached_per_fn, need_audit = cache.split_by_function(token, body.source_code)
    if cached_per_fn:
        yield _sse("llm_partial", cached_per_fn)

    if not need_audit:
        # All functions cached individually but full-file hash didn't match
        # (e.g. comments-only edit). Use cached findings as the LLM result.
        cache.store_full(token, body.source_code, cached_per_fn)
        merged = merge_dedupe(static_findings, cached_per_fn)
        yield _sse("merged", merged)
        yield _sse("done", {"reason": "per_fn_cache"})
        return

    # 4) LLM audit for changed functions, in parallel with cancellation
    new_findings: list[dict] = []
    try:
        for fn in need_audit:
            if await request.is_disconnected():
                stats.inc("cancellations")
                yield _sse("error", {"code": "client_disconnect"})
                return
            snippet = fn_source_text(body.source_code, fn)
            offset = max(0, fn.lineno - 1)
            fn_findings = await asyncio.to_thread(
                run_llm_audit,
                body.filename,
                snippet,
                model=settings.gemini_live_model,
                line_offset=offset,
            )
            cache.store_function_findings(token, fn, fn_findings)
            new_findings.extend(fn_findings)
            yield _sse("llm_partial", fn_findings)
    except asyncio.CancelledError:
        stats.inc("cancellations")
        yield _sse("error", {"code": "cancelled"})
        raise

    all_llm = cached_per_fn + new_findings
    cache.store_full(token, body.source_code, all_llm)
    yield _sse("llm", all_llm)
    merged = merge_dedupe(static_findings, all_llm)
    yield _sse("merged", merged)
    yield _sse("done", {"reason": "ok"})


@router.post("/audit/stream")
async def live_stream(
    body: LiveAuditRequest,
    request: Request,
    x_session_token: str | None = Header(default=None),
):
    token = _client_token(body, x_session_token)
    _enforce_rate(token)
    _check_size(body.source_code)
    stats.inc("stream_calls")

    # Cancel any previous in-flight stream for this token
    placeholder = asyncio.current_task()
    prior = inflight.claim(token, placeholder) if placeholder else None
    if prior is not None and not prior.done():
        prior.cancel()
        stats.inc("cancellations")

    async def gen():
        try:
            async for chunk in _stream_generator(body, token, request):
                yield chunk
        finally:
            if placeholder is not None:
                inflight.release(token, placeholder)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------- Phase 3: stateless fix preview ----------

@router.post("/fix/preview", response_model=LiveFixPreviewResponse)
def live_fix_preview(
    body: LiveFixPreviewRequest,
    x_session_token: str | None = Header(default=None),
) -> LiveFixPreviewResponse:
    token = x_session_token or "anon"
    _enforce_rate(token)
    _check_size(body.source_code)
    stats.inc("fix_preview_calls")

    issue = body.finding.model_dump()
    try:
        result = generate_fix(body.filename, body.source_code, issue)
    except Exception as e:
        raise HeliosError(500, "fix_failed", f"fix generation failed: {e}")
    return LiveFixPreviewResponse(
        fixed_code=result["fixed_code"],
        diff_summary=result["diff_summary"],
    )


# ---------- Phase 4: stats ----------

@router.get("/stats", response_model=LiveStatsResponse)
def live_stats() -> LiveStatsResponse:
    snap = stats.snapshot()
    return LiveStatsResponse(active_tokens=cache.active_tokens(), **snap)

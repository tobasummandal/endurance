"""Helios MCP server — stdio transport.

Tools exposed (all narrowly scoped to scientific Python; non-scientific
inputs get a warning attached to the response, never a silent pass):

    helios_audit              — fast static check, optionally + LLM (deep=True)
    helios_fix_preview        — generate a fix for one finding (no DB)
    helios_session_create     — start a persistent session for verify/route
    helios_session_verify     — sandboxed verification of a fix
    helios_session_route      — flag GPU-acceleration candidates
    helios_detect_scientific  — heuristic 'is this scientific?' check
"""
from __future__ import annotations
import json
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from ..agent.client import HeliosClient, HeliosClientError
from ..agent.review import review_code
from ..detector.scientific import WARNING_BANNER, detect_scientific


SERVER_NAME = "helios"
SERVER_VERSION = "0.1.0"

DESCRIPTION = (
    "Helios — correctness layer for SCIENTIFIC Python. Audits silent bugs "
    "(off-by-one, unit mismatches, numerical instability), generates fixes "
    "verified by sandboxed numerical comparison, and flags GPU candidates. "
    "Tuned for code using numpy / scipy / torch / jax / pandas / sympy / "
    "qiskit / etc. Will warn (not block) if used on non-scientific code."
)


def _client() -> HeliosClient:
    base = os.environ.get("HELIOS_API_URL", "http://localhost:8000")
    return HeliosClient(base_url=base)


def _format_review_text(rev) -> str:
    return rev.to_agent_text()


def _wrap_warning(payload: dict, source: str) -> dict:
    """Attach a non-scientific-code warning to the payload if applicable."""
    score = detect_scientific(source)
    payload["scientific_score"] = {
        "score": score.score,
        "is_scientific": score.is_scientific,
        "confidence": score.confidence,
        "reason": score.reason,
        "positive_signals": score.positive_signals,
        "negative_signals": score.negative_signals,
    }
    if not score.is_scientific:
        payload["warning"] = WARNING_BANNER
    return payload


# ---- tool definitions ----

TOOLS: list[Tool] = [
    Tool(
        name="helios_audit",
        description=(
            "Audit scientific Python for SILENT bugs that don't crash but produce "
            "wrong results: off-by-one in numerical integration, unit/dimensional "
            "mismatches, subtractive cancellation, broken boundary conditions, "
            "shape assumptions, mutable defaults. ONLY for code using "
            "numpy/scipy/torch/jax/pandas/sympy/qiskit/etc. Non-scientific code "
            "will receive a warning. Set deep=true to add an LLM pass (Gemini "
            "Flash) on top of the fast AST checks."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "source_code": {"type": "string", "description": "Full Python source."},
                "filename": {"type": "string", "default": "draft.py"},
                "deep": {"type": "boolean", "default": False,
                         "description": "Run LLM audit in addition to static checks."},
            },
            "required": ["source_code"],
        },
    ),
    Tool(
        name="helios_fix_preview",
        description=(
            "Generate a corrected file applying ONE specific finding from "
            "helios_audit. Returns rewritten source + a one-line diff summary. "
            "Does not verify — call helios_session_verify after persisting."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "source_code": {"type": "string"},
                "filename": {"type": "string", "default": "draft.py"},
                "finding": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "severity": {"type": "string"},
                        "line_start": {"type": "integer"},
                        "line_end": {"type": "integer"},
                        "title": {"type": "string"},
                        "explanation": {"type": "string"},
                        "source": {"type": "string"},
                    },
                    "required": ["category", "severity", "line_start", "line_end",
                                 "title", "explanation", "source"],
                },
            },
            "required": ["source_code", "finding"],
        },
    ),
    Tool(
        name="helios_session_create",
        description=(
            "Persist a Python file as a Helios session — required for verify "
            "and route. Returns a session_id. Use this when you need durable "
            "audit/fix/verify history, not for ephemeral live audits."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "source_code": {"type": "string"},
                "filename": {"type": "string", "default": "draft.py"},
            },
            "required": ["source_code"],
        },
    ),
    Tool(
        name="helios_session_audit",
        description=(
            "Run the full scientific-code audit (static + LLM) on a persistent "
            "session — same scope as helios_audit but with durable Issue ids. "
            "Use only on numerical Python (numpy / scipy / torch / jax / etc.); "
            "returns a list of Issue objects you can pass to helios_session_fix."
        ),
        inputSchema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    ),
    Tool(
        name="helios_session_fix",
        description=(
            "Generate a persisted fix for one Issue from a session. Returns "
            "fix_id you can pass to helios_session_verify."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "issue_id": {"type": "string"},
            },
            "required": ["session_id", "issue_id"],
        },
    ),
    Tool(
        name="helios_session_verify",
        description=(
            "Sandboxed numerical verification of a fix: synthesizes ~12 test "
            "inputs, runs original and fix in isolated subprocesses, compares "
            "with numpy.allclose tolerance + exception-class equality. Slow "
            "(10–60s); call only when you need proof the fix is correct. "
            "Returns per-test verdict + overall (all_agree / partial_disagree / "
            "all_disagree)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "fix_id": {"type": "string"},
            },
            "required": ["session_id", "fix_id"],
        },
    ),
    Tool(
        name="helios_session_route",
        description=(
            "Flag blocks of scientific code that would benefit from GPU "
            "acceleration: nested numerical loops, matmul, FFT, elementwise "
            "ufuncs in pure-Python loops, Monte Carlo. NOT for web/IO code."
        ),
        inputSchema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    ),
    Tool(
        name="helios_detect_scientific",
        description=(
            "Run only the heuristic 'is this scientific Python?' detector. "
            "Useful for an agent to decide BEFORE calling helios_audit whether "
            "Helios is the right tool. Returns a score in [0,1], confidence, "
            "and the signals that contributed."
        ),
        inputSchema={
            "type": "object",
            "properties": {"source_code": {"type": "string"}},
            "required": ["source_code"],
        },
    ),
]


def _err(msg: str) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps({"error": msg}, indent=2))]


def _json(payload: Any) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(payload, indent=2, default=str))]


async def _call(name: str, args: dict[str, Any]) -> list[TextContent]:
    cl = _client()
    try:
        if name == "helios_detect_scientific":
            score = detect_scientific(args.get("source_code", ""))
            return _json({
                "score": score.score,
                "is_scientific": score.is_scientific,
                "confidence": score.confidence,
                "reason": score.reason,
                "positive_signals": score.positive_signals,
                "negative_signals": score.negative_signals,
            })

        if name == "helios_audit":
            src = args["source_code"]
            rev = review_code(
                src,
                filename=args.get("filename", "draft.py"),
                deep=bool(args.get("deep", False)),
                client=cl,
            )
            return _json(rev.to_dict())

        if name == "helios_fix_preview":
            src = args["source_code"]
            payload = cl.fix_preview(
                src,
                finding=args["finding"],
                filename=args.get("filename", "draft.py"),
            )
            return _json(_wrap_warning(payload, src))

        if name == "helios_session_create":
            src = args["source_code"]
            payload = cl.create_session(src, filename=args.get("filename", "draft.py"))
            return _json(_wrap_warning(payload, src))

        if name == "helios_session_audit":
            return _json(cl.session_audit(args["session_id"]))

        if name == "helios_session_fix":
            return _json(cl.session_fix(args["session_id"], args["issue_id"]))

        if name == "helios_session_verify":
            return _json(cl.session_verify(args["session_id"], args["fix_id"]))

        if name == "helios_session_route":
            return _json(cl.session_route(args["session_id"]))

        return _err(f"unknown tool: {name}")
    except HeliosClientError as e:
        return _err(f"{e.code}: {e.message}")
    except KeyError as e:
        return _err(f"missing argument: {e}")
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}")


def build_server() -> Server:
    server = Server(SERVER_NAME)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        return await _call(name, arguments or {})

    return server


def main() -> None:
    """Entry point for `helios-mcp` — runs stdio MCP server."""
    import asyncio

    async def _run():
        server = build_server()
        async with stdio_server() as (read, write):
            init_opts = server.create_initialization_options()
            await server.run(read, write, init_opts)

    asyncio.run(_run())


if __name__ == "__main__":
    main()

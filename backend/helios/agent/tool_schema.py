"""Function-calling tool schemas for OpenAI / Anthropic / Gemini-style agents.

These are *declarations* — the agent's tool-runtime decides when to invoke
them and feeds the input back through `review_code()` (or HeliosClient
directly). Helios is intentionally narrow: the description tells the agent
"only call this on scientific / numerical Python."
"""
from __future__ import annotations

# Source for review() — emphasizes scope so the agent self-gates calls.
_REVIEW_DESCRIPTION = (
    "Audit Python source for SILENT bugs (off-by-one, unit mismatches, "
    "numerical instability, broken boundary conditions, shape assumptions). "
    "USE ONLY for scientific / numerical Python that imports numpy, scipy, "
    "torch, jax, pandas, sympy, qiskit, or similar. DO NOT use for web "
    "handlers, ORM models, CLI plumbing, or general business logic — Helios "
    "will return low-signal findings and a warning. Returns findings with "
    "category, severity, line range, and a plain-English explanation."
)

_FIX_DESCRIPTION = (
    "Generate a corrected version of a Python file that fixes ONE specific "
    "scientific-code bug previously flagged by helios_audit. Returns the "
    "rewritten file plus a one-line diff summary. Does not auto-verify — "
    "follow up with helios_verify_session for numerical agreement testing."
)

_VERIFY_DESCRIPTION = (
    "Run a fix through Helios's sandboxed verification: synthesizes ~12 test "
    "inputs, executes the original and the fix in isolated subprocesses, "
    "compares outputs with numpy.allclose tolerance. USE ONLY after a fix "
    "exists. Takes 10–60 seconds. Returns per-test verdict and an overall "
    "all_agree / partial_disagree / all_disagree."
)

_ROUTE_DESCRIPTION = (
    "Flag blocks of scientific Python that would benefit from GPU "
    "acceleration (nested numerical loops, matmul, FFT, elementwise "
    "ufuncs, Monte Carlo). Returns line ranges, estimated speedup, "
    "engineering complexity. NOT for web/IO-bound code."
)

_AUDIT_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "source_code": {
            "type": "string",
            "description": "The full Python source to audit. Single file.",
        },
        "filename": {
            "type": "string",
            "description": "File name for context (used in prompts and findings).",
            "default": "draft.py",
        },
        "deep": {
            "type": "boolean",
            "description": (
                "If true, run the LLM audit in addition to fast static checks. "
                "Costs Gemini tokens; default false for tight feedback loops."
            ),
            "default": False,
        },
    },
    "required": ["source_code"],
}

_FIX_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "source_code": {"type": "string"},
        "filename": {"type": "string", "default": "draft.py"},
        "finding": {
            "type": "object",
            "description": "One Issue/finding object as returned by helios_audit.",
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
}

_VERIFY_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "session_id": {"type": "string"},
        "fix_id": {"type": "string"},
    },
    "required": ["session_id", "fix_id"],
}

_ROUTE_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "session_id": {"type": "string"},
    },
    "required": ["session_id"],
}


# OpenAI / Gemini "function" shape
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "helios_audit",
            "description": _REVIEW_DESCRIPTION,
            "parameters": _AUDIT_INPUT_SCHEMA,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "helios_fix_preview",
            "description": _FIX_DESCRIPTION,
            "parameters": _FIX_INPUT_SCHEMA,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "helios_verify_session",
            "description": _VERIFY_DESCRIPTION,
            "parameters": _VERIFY_INPUT_SCHEMA,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "helios_route_session",
            "description": _ROUTE_DESCRIPTION,
            "parameters": _ROUTE_INPUT_SCHEMA,
        },
    },
]


# Anthropic-style: flat name/description/input_schema
ANTHROPIC_TOOLS = [
    {
        "name": "helios_audit",
        "description": _REVIEW_DESCRIPTION,
        "input_schema": _AUDIT_INPUT_SCHEMA,
    },
    {
        "name": "helios_fix_preview",
        "description": _FIX_DESCRIPTION,
        "input_schema": _FIX_INPUT_SCHEMA,
    },
    {
        "name": "helios_verify_session",
        "description": _VERIFY_DESCRIPTION,
        "input_schema": _VERIFY_INPUT_SCHEMA,
    },
    {
        "name": "helios_route_session",
        "description": _ROUTE_DESCRIPTION,
        "input_schema": _ROUTE_INPUT_SCHEMA,
    },
]


# Convenience alias
TOOL_SCHEMAS = {
    "openai": OPENAI_TOOLS,
    "anthropic": ANTHROPIC_TOOLS,
    "gemini": OPENAI_TOOLS,  # Gemini accepts the OpenAI shape
}

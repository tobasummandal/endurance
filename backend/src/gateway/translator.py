"""
Natural language → task profile row + problem-specific payload.

Three-stage pipeline (matches CLAUDE.md S4a):
  1. classify(prompt)  → one of {vrp, maxcut, freq_coloring, qrng, unknown}
  2. extract(prompt, problem_type) → params dict, validated by Pydantic
  3. dispatch(problem_type, params) → full router request body (TaskRequest schema)

Backend: Gemini 2.5 Flash via google-genai SDK if GEMINI_API_KEY is set.
Fallback: keyword-based canned mappings for the three demo problems so the demo
runs without an API key.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, ValidationError


ProblemType = Literal["vrp", "maxcut", "freq_coloring", "qrng", "unknown"]

CLASSIFIER_SYSTEM_PROMPT = """You are the classifier stage of a tactical task router for the Xtremis Quantum Routing Brain.
Given a natural-language description of a defense compute task, output a single JSON object:
  {"problem_type": <one of: vrp, maxcut, freq_coloring, qrng, unknown>, "confidence": <0-1 float>, "rationale": "<one sentence>"}

Definitions:
  - vrp:           Vehicle Routing / TSP / drone routing / target assignment ordering.
  - maxcut:        Bipartition / clustering / community detection / cut optimization on a graph.
  - freq_coloring: Frequency assignment / spectrum deconfliction / graph coloring / channel allocation.
  - qrng:          Cryptographic key material / random number generation.
  - unknown:       Anything else.

Output JSON only, no prose."""

EXTRACTOR_SYSTEM_TEMPLATES = {
    "vrp": """Extract VRP parameters as JSON:
  {"distance_matrix": [[float, ...], ...], "n_cities": int}
If the prompt names cities/targets without distances, generate a plausible random symmetric matrix
with values 1-15. n_cities should be ≤ 4 for the demo (each city = n qubits). Output JSON only.""",
    "maxcut": """Extract MaxCut parameters as JSON:
  {"n_nodes": int, "edges": [[int, int], ...]}
If a graph isn't explicitly described, generate a small interference graph (n_nodes ≤ 8). Output JSON only.""",
    "freq_coloring": """Extract frequency-assignment parameters as JSON:
  {"n_nodes": int, "n_colors": int, "edges": [[int, int], ...]}
n_nodes * n_colors ≤ 18 for the demo. Edges represent interference pairs that must take different
frequencies. Output JSON only.""",
}


# ─── Pydantic intermediate models ──────────────────────────────────────────────

class VRPParams(BaseModel):
    distance_matrix: list[list[float]]
    n_cities: int = Field(ge=2, le=6)


class MaxCutParams(BaseModel):
    n_nodes: int = Field(ge=3, le=12)
    edges: list[list[int]]


class FreqColoringParams(BaseModel):
    n_nodes: int = Field(ge=2, le=8)
    n_colors: int = Field(ge=2, le=4)
    edges: list[list[int]]


PARAM_MODELS = {
    "vrp": VRPParams,
    "maxcut": MaxCutParams,
    "freq_coloring": FreqColoringParams,
}


# ─── Gemini client (lazy) ──────────────────────────────────────────────────────

_GEMINI_CLIENT = None
_GEMINI_MODEL = "gemini-2.5-flash"


def _gemini_client():
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is not None:
        return _GEMINI_CLIENT
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    from google import genai
    _GEMINI_CLIENT = genai.Client(api_key=key)
    return _GEMINI_CLIENT


def _call_gemini(system: str, user: str) -> tuple[str, dict]:
    """Returns (text, telemetry). Raises on failure."""
    client = _gemini_client()
    if client is None:
        raise RuntimeError("GEMINI_API_KEY not set")
    t0 = time.perf_counter()
    resp = client.models.generate_content(
        model=_GEMINI_MODEL,
        contents=[user],
        config={
            "system_instruction": system,
            "response_mime_type": "application/json",
            "temperature": 0.1,
        },
    )
    dt_ms = (time.perf_counter() - t0) * 1000
    usage = getattr(resp, "usage_metadata", None)
    return resp.text, {
        "model": _GEMINI_MODEL,
        "latency_ms": round(dt_ms, 1),
        "input_tokens": getattr(usage, "prompt_token_count", None) if usage else None,
        "output_tokens": getattr(usage, "candidates_token_count", None) if usage else None,
    }


# ─── Canned fallback (no API key) ──────────────────────────────────────────────

KEYWORDS = {
    "vrp": ["route", "drone", "vehicle", "tsp", "tour", "delivery", "courier", "target"],
    "freq_coloring": ["frequency", "spectrum", "channel", "interference", "coloring", "color", "deconflict"],
    "maxcut": ["maxcut", "max-cut", "cut", "partition", "bipartition", "cluster"],
    "qrng": ["random", "rng", "key material", "qrng"],
}


def _classify_canned(prompt: str) -> dict:
    p = prompt.lower()
    scores = {pt: sum(1 for kw in kws if kw in p) for pt, kws in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return {"problem_type": "unknown", "confidence": 0.0, "rationale": "No keywords matched.", "_source": "canned"}
    return {
        "problem_type": best,
        "confidence": min(0.5 + 0.15 * scores[best], 0.9),
        "rationale": f"Matched {scores[best]} {best} keyword(s).",
        "_source": "canned",
    }


def _extract_canned(prompt: str, problem_type: ProblemType) -> dict:
    """Reasonable demo defaults; deterministic so the demo is reproducible."""
    if problem_type == "vrp":
        return {
            "n_cities": 4,
            "distance_matrix": [
                [0, 2, 9, 10],
                [1, 0, 6, 4],
                [15, 7, 0, 8],
                [6, 3, 12, 0],
            ],
        }
    if problem_type == "maxcut":
        return {
            "n_nodes": 8,
            "edges": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 0],
                      [0, 4], [1, 5], [2, 6], [3, 7]],
        }
    if problem_type == "freq_coloring":
        return {
            "n_nodes": 5,
            "n_colors": 3,
            "edges": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 0]],
        }
    return {}


# ─── Public API ────────────────────────────────────────────────────────────────

def classify(prompt: str) -> dict:
    """Returns {problem_type, confidence, rationale, _source, ?telemetry}."""
    if _gemini_client() is None:
        return _classify_canned(prompt)
    try:
        text, tel = _call_gemini(CLASSIFIER_SYSTEM_PROMPT, prompt)
        data = json.loads(text)
        data.setdefault("_source", "gemini")
        data["_telemetry"] = tel
        return data
    except Exception as e:
        out = _classify_canned(prompt)
        out["_fallback_reason"] = f"Gemini call failed: {e}"
        return out


def extract(prompt: str, problem_type: ProblemType) -> dict:
    """Returns {params, _source, ?telemetry, ?_fallback_reason}."""
    if problem_type not in PARAM_MODELS:
        return {"params": {}, "_source": "noop"}

    if _gemini_client() is None:
        return {"params": _extract_canned(prompt, problem_type), "_source": "canned"}

    sys_prompt = EXTRACTOR_SYSTEM_TEMPLATES[problem_type]
    try:
        text, tel = _call_gemini(sys_prompt, prompt)
        params = json.loads(text)
        # Validate against pydantic; if it fails, retry once with the error
        try:
            PARAM_MODELS[problem_type](**params)
            return {"params": params, "_source": "gemini", "_telemetry": tel}
        except ValidationError as ve:
            retry_user = f"{prompt}\n\nPrior output failed validation: {ve}\nFix and re-emit JSON."
            text2, tel2 = _call_gemini(sys_prompt, retry_user)
            params2 = json.loads(text2)
            PARAM_MODELS[problem_type](**params2)
            return {"params": params2, "_source": "gemini_retry", "_telemetry": tel2}
    except Exception as e:
        return {
            "params": _extract_canned(prompt, problem_type),
            "_source": "canned",
            "_fallback_reason": f"Gemini extract failed: {e}",
        }


# Map our problem_type → defensible task profile defaults (matches CSV columns we care about)
TASK_PROFILE_DEFAULTS = {
    "vrp": {
        "task_id": "C2-VRP-DEMO",
        "task_name": "Vehicle Routing (drone tasking)",
        "task_category": "JADC2/C2",
        "classification_level": "CUI",
        "deadline_class": "batch",
        "latency_budget_ms": 30000,
        "quantum_candidate": "Y",
        "quantum_algorithm": "QAOA",
        "priority": 2,
    },
    "maxcut": {
        "task_id": "SM-MAXCUT-DEMO",
        "task_name": "Spectrum interference partition",
        "task_category": "Spectrum Management",
        "classification_level": "CUI",
        "deadline_class": "batch",
        "latency_budget_ms": 15000,
        "quantum_candidate": "Y",
        "quantum_algorithm": "QAOA",
        "priority": 2,
    },
    "freq_coloring": {
        "task_id": "SM-FREQ-DEMO",
        "task_name": "Frequency assignment (channel deconfliction)",
        "task_category": "Spectrum Management",
        "classification_level": "CUI",
        "deadline_class": "batch",
        "latency_budget_ms": 30000,
        "quantum_candidate": "Y",
        "quantum_algorithm": "QAOA",
        "priority": 2,
    },
}


def dispatch(
    problem_type: ProblemType,
    params: dict,
    overrides: Optional[dict] = None,
) -> dict:
    """Build the full TaskRequest body the router expects."""
    if problem_type not in TASK_PROFILE_DEFAULTS:
        raise ValueError(f"Cannot dispatch unknown problem_type={problem_type}")
    body = dict(TASK_PROFILE_DEFAULTS[problem_type])
    if overrides:
        body.update(overrides)
    body["payload"] = {"problem_type": problem_type, **params}
    return body

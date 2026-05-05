"""LLM-driven audit pass — finds silent scientific bugs."""
from __future__ import annotations
from typing import Any

from ..config import settings
from ..llm import generate, load_prompt, parse_json

VALID_CATEGORIES = {
    "off_by_one", "unit_mismatch", "numerical_instability", "float_equality",
    "mutable_default", "module_state", "bare_except", "shape_assumption",
    "boundary_condition", "other",
}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def run_llm_audit(
    filename: str,
    source: str,
    *,
    model: str | None = None,
    line_offset: int = 0,
) -> list[dict]:
    """Run a single LLM audit pass on `source`.

    `line_offset` shifts reported line numbers (used when auditing a function
    snippet — caller passes the function's start line minus 1).
    """
    prompt = load_prompt("audit.v1.txt").format(filename=filename, source_code=source)
    try:
        text = generate(
            model or settings.gemini_audit_model,
            prompt,
            json_mode=True,
            max_output_tokens=4096,
        )
        raw = parse_json(text)
    except Exception:
        return []
    if not isinstance(raw, list):
        return []

    out: list[dict] = []
    line_count = source.count("\n") + 1
    for item in raw:
        if not isinstance(item, dict):
            continue
        cat = item.get("category", "other")
        if cat not in VALID_CATEGORIES:
            cat = "other"
        sev = item.get("severity", "medium")
        if sev not in VALID_SEVERITIES:
            sev = "medium"
        try:
            ls = int(item.get("line_start", 1))
            le = int(item.get("line_end", ls))
        except (TypeError, ValueError):
            continue
        ls = max(1, min(ls, line_count)) + line_offset
        le = max(ls, min(le + line_offset, line_count + line_offset))
        title = str(item.get("title", "")).strip()[:80]
        expl = str(item.get("explanation", "")).strip()
        if not title or not expl:
            continue
        out.append({
            "category": cat,
            "severity": sev,
            "line_start": ls,
            "line_end": le,
            "title": title,
            "explanation": expl,
            "source": "llm",
        })
    return out


def merge_dedupe(static_findings: list[dict], llm_findings: list[dict]) -> list[dict]:
    """Dedupe by (category, line_start). Static findings win on overlap."""
    seen: dict[tuple, dict] = {}
    for f in static_findings:
        seen[(f["category"], f["line_start"])] = f
    for f in llm_findings:
        key = (f["category"], f["line_start"])
        if key not in seen:
            seen[key] = f
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(
        seen.values(),
        key=lambda x: (severity_rank.get(x["severity"], 99), x["line_start"]),
    )

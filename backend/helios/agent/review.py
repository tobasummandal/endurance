"""High-level review() — what an agent typically calls after generating code.

Behavior:
  1. Run the scientific detector. If non-scientific, attach a warning.
  2. Run a fast static audit (no LLM cost).
  3. Optionally run a deep audit (LLM) — controlled by `deep=True`.
  4. Return a single Review object with everything merged + the warning.

The agent decides what to do with the result:
  - re-prompt itself with the findings,
  - surface them to the user,
  - silently drop low-severity findings on small edits.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

from ..detector.scientific import ScientificScore, WARNING_BANNER, detect_scientific
from .client import HeliosClient, HeliosClientError


@dataclass
class Review:
    is_scientific: bool
    detector: ScientificScore
    warning: str | None
    findings: list[dict] = field(default_factory=list)
    static_findings: list[dict] = field(default_factory=list)
    llm_findings: list[dict] = field(default_factory=list)
    error: str | None = None
    # convenience: top-of-list summary for the agent
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["detector"] = asdict(self.detector)
        return d

    def to_agent_text(self, max_findings: int = 10) -> str:
        """Render the review as a string the agent can paste into its context."""
        parts: list[str] = []
        if self.warning:
            parts.append(self.warning)
            parts.append("")
        if self.error:
            parts.append(f"Helios error: {self.error}")
            return "\n".join(parts)
        parts.append(self.summary)
        if not self.findings:
            return "\n".join(parts)
        parts.append("")
        parts.append("Findings:")
        for f in self.findings[:max_findings]:
            sev = f.get("severity", "?").upper()
            cat = f.get("category", "?")
            ls = f.get("line_start", "?")
            le = f.get("line_end", ls)
            line = f"line {ls}" if ls == le else f"lines {ls}–{le}"
            parts.append(f"  [{sev:8s}] {cat:22s} {line}: {f.get('title', '')}")
            expl = f.get("explanation", "").strip()
            if expl:
                parts.append(f"             {expl}")
        if len(self.findings) > max_findings:
            parts.append(f"  ... and {len(self.findings) - max_findings} more.")
        return "\n".join(parts)


def review_code(
    source: str,
    *,
    filename: str = "draft.py",
    deep: bool = False,
    client: HeliosClient | None = None,
) -> Review:
    """Run the standard agent-side review.

    `deep=False` (default) runs only the static analyzer — sub-100ms, free.
    `deep=True` also runs the LLM audit (Gemini Flash by default).
    """
    detector = detect_scientific(source)
    warning = None if detector.is_scientific else WARNING_BANNER

    cl = client or HeliosClient()
    findings: list[dict] = []
    static: list[dict] = []
    llm: list[dict] = []
    error: str | None = None

    try:
        if deep:
            res = cl.audit(source, filename=filename)
            static = res.get("static", [])
            llm = res.get("llm", [])
            findings = res.get("findings", static)
        else:
            res = cl.audit_static(source, filename=filename)
            static = res.get("findings", [])
            findings = static
    except HeliosClientError as e:
        error = f"{e.code}: {e.message}"

    if error:
        summary = f"Review failed ({error})."
    elif not findings:
        summary = "No findings. Static checks pass." + (" Deep audit clean." if deep else "")
    else:
        n = len(findings)
        n_high = sum(1 for f in findings if f.get("severity") in ("high", "critical"))
        summary = f"{n} finding(s); {n_high} high/critical."

    return Review(
        is_scientific=detector.is_scientific,
        detector=detector,
        warning=warning,
        findings=findings,
        static_findings=static,
        llm_findings=llm,
        error=error,
        summary=summary,
    )

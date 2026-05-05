"""Generate a single-issue fix via LLM."""
from __future__ import annotations
from ..config import settings
from ..llm import generate, load_prompt, parse_json


# Issue categories that warrant a structural refactor (encapsulate state into a class)
# rather than a minimal in-place rewrite.
_REFACTOR_CATEGORIES = {"module_state"}


def _prompt_for(category: str) -> str:
    return "refactor.v1.txt" if category in _REFACTOR_CATEGORIES else "fix.v1.txt"


def generate_fix(filename: str, source: str, issue: dict) -> dict:
    prompt = load_prompt(_prompt_for(issue["category"])).format(
        filename=filename,
        source_code=source,
        category=issue["category"],
        line_start=issue["line_start"],
        line_end=issue["line_end"],
        title=issue["title"],
        explanation=issue["explanation"],
    )
    text = generate(settings.gemini_fix_model, prompt, json_mode=True, max_output_tokens=12000)
    obj = parse_json(text)
    if not isinstance(obj, dict) or "fixed_code" not in obj:
        raise ValueError("Fix generator returned malformed JSON")
    return {
        "fixed_code": str(obj["fixed_code"]),
        "diff_summary": str(obj.get("diff_summary", "Applied fix"))[:200],
    }

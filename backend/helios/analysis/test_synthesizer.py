"""Identify the function(s) touched by a fix and synthesize test inputs."""
from __future__ import annotations
import ast
import difflib
import json
from typing import Optional

from ..config import settings
from ..llm import generate, load_prompt, parse_json


def diff_changed_lines(original: str, fixed: str) -> set[int]:
    """1-indexed line numbers in `original` that differ from `fixed`."""
    o = original.splitlines()
    f = fixed.splitlines()
    matcher = difflib.SequenceMatcher(a=o, b=f)
    changed: set[int] = set()
    for tag, i1, i2, _, _ in matcher.get_opcodes():
        if tag == "equal":
            continue
        for ln in range(i1 + 1, max(i1 + 1, i2) + 1):
            changed.add(ln)
    return changed


def find_target_functions(source: str, changed_lines: set[int]) -> list[ast.FunctionDef]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start = node.lineno
            end = getattr(node, "end_lineno", node.lineno)
            if any(start <= ln <= end for ln in changed_lines):
                out.append(node)
    return out


def function_signature(fn: ast.FunctionDef) -> str:
    args = [a.arg for a in fn.args.args]
    return f"{fn.name}({', '.join(args)})"


def function_source(source: str, fn: ast.FunctionDef) -> str:
    lines = source.splitlines()
    start = fn.lineno - 1
    end = getattr(fn, "end_lineno", fn.lineno)
    return "\n".join(lines[start:end])


def synthesize_inputs(fn_source: str, signature: str, n: Optional[int] = None) -> list[list]:
    n = n or settings.test_case_count
    prompt = load_prompt("test_synth.v1.txt").format(
        n=n, signature=signature, function_source=fn_source
    )
    try:
        text = generate(settings.gemini_audit_model, prompt, json_mode=True, max_output_tokens=4096)
        raw = parse_json(text)
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    out: list[list] = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("args"), list):
            out.append(item["args"])
    return out

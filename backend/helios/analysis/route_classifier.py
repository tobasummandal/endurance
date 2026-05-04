"""Pattern-match GPU-suitable blocks; classify with Gemini."""
from __future__ import annotations
import ast
import json
from typing import Any

from ..config import settings
from ..llm import generate, load_prompt, parse_json


VALID_PATTERNS = {
    "nested_numeric_loop", "matmul", "fft", "elementwise_ufunc", "monte_carlo", "other",
}
VALID_COMPLEXITY = {"low", "medium", "high"}


def _matmul_call(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in {"matmul", "dot"}:
            return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.MatMult):
        return True
    return False


def _fft_call(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Attribute) and "fft" in f.attr.lower():
            return True
        if isinstance(f, ast.Name) and "fft" in f.id.lower():
            return True
    return False


def find_candidates(source: str) -> list[dict]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    candidates: list[dict] = []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.loop_depth = 0

        def visit_For(self, node: ast.For):
            self.loop_depth += 1
            try:
                if self.loop_depth >= 2:
                    candidates.append({
                        "line_start": node.lineno,
                        "line_end": getattr(node, "end_lineno", node.lineno),
                        "pattern": "nested_numeric_loop",
                    })
                self.generic_visit(node)
            finally:
                self.loop_depth -= 1

        def visit_Call(self, node: ast.Call):
            if _matmul_call(node):
                candidates.append({
                    "line_start": node.lineno,
                    "line_end": getattr(node, "end_lineno", node.lineno),
                    "pattern": "matmul",
                })
            elif _fft_call(node):
                candidates.append({
                    "line_start": node.lineno,
                    "line_end": getattr(node, "end_lineno", node.lineno),
                    "pattern": "fft",
                })
            self.generic_visit(node)

        def visit_BinOp(self, node: ast.BinOp):
            if isinstance(node.op, ast.MatMult):
                candidates.append({
                    "line_start": node.lineno,
                    "line_end": getattr(node, "end_lineno", node.lineno),
                    "pattern": "matmul",
                })
            self.generic_visit(node)

    V().visit(tree)

    # Dedupe by (line_start, pattern), keep outermost
    seen: dict[tuple, dict] = {}
    for c in candidates:
        key = (c["line_start"], c["pattern"])
        if key not in seen:
            seen[key] = c
    return list(seen.values())


def classify(source: str) -> list[dict]:
    cands = find_candidates(source)
    if not cands:
        return []
    prompt = load_prompt("route.v1.txt").format(
        candidates_json=json.dumps(cands, indent=2),
        source_code=source,
    )
    try:
        text = generate(settings.gemini_route_model, prompt, json_mode=True, max_output_tokens=4096)
        raw = parse_json(text)
    except Exception:
        # fall back: return candidates with placeholder annotation
        return [
            {**c, "estimated_speedup": "unknown", "complexity": "medium",
             "rationale": "Pattern detected; LLM classification unavailable."}
            for c in cands
        ]
    if not isinstance(raw, list):
        return []

    out: list[dict] = []
    for c, item in zip(cands, raw):
        if not isinstance(item, dict):
            continue
        pat = item.get("pattern", c["pattern"])
        if pat not in VALID_PATTERNS:
            pat = "other"
        comp = item.get("complexity", "medium")
        if comp not in VALID_COMPLEXITY:
            comp = "medium"
        out.append({
            "line_start": c["line_start"],
            "line_end": c["line_end"],
            "pattern": pat,
            "estimated_speedup": str(item.get("estimated_speedup", "unknown"))[:40],
            "complexity": comp,
            "rationale": str(item.get("rationale", ""))[:400],
        })
    return out

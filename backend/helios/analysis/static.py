"""Cheap deterministic AST-level checks. Run before LLM audit."""
from __future__ import annotations
import ast
from dataclasses import dataclass


@dataclass
class StaticFinding:
    category: str
    severity: str
    line_start: int
    line_end: int
    title: str
    explanation: str

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "severity": self.severity,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "title": self.title,
            "explanation": self.explanation,
            "source": "static",
        }


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.findings: list[StaticFinding] = []

    # range(1, N) over what looks like an indexable container — likely off-by-one
    def visit_For(self, node: ast.For) -> None:
        if (
            isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
            and len(node.iter.args) >= 2
        ):
            first = node.iter.args[0]
            if isinstance(first, ast.Constant) and first.value == 1:
                self.findings.append(
                    StaticFinding(
                        category="off_by_one",
                        severity="high",
                        line_start=node.lineno,
                        line_end=getattr(node, "end_lineno", node.lineno),
                        title="Loop starts at index 1 — possible off-by-one",
                        explanation=(
                            "range(1, N) skips index 0. In numerical integration / discretization "
                            "this often drops the first interval and silently produces wrong results."
                        ),
                    )
                )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for default in node.args.defaults + node.args.kw_defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.findings.append(
                    StaticFinding(
                        category="mutable_default",
                        severity="medium",
                        line_start=node.lineno,
                        line_end=getattr(node, "end_lineno", node.lineno),
                        title=f"Mutable default argument in {node.name}",
                        explanation=(
                            "Mutable default args persist across calls. Computed state leaks "
                            "between invocations and can corrupt scientific results."
                        ),
                    )
                )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.findings.append(
                StaticFinding(
                    category="bare_except",
                    severity="medium",
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    title="Bare except: clause",
                    explanation=(
                        "Bare except swallows numerical errors (overflow, NaN propagation, "
                        "linalg failures), masking silent miscalculations."
                    ),
                )
            )
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        # heuristic: float == float
        if any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
            if _looks_floaty(node.left) or any(_looks_floaty(c) for c in node.comparators):
                self.findings.append(
                    StaticFinding(
                        category="float_equality",
                        severity="medium",
                        line_start=node.lineno,
                        line_end=getattr(node, "end_lineno", node.lineno),
                        title="Float equality comparison",
                        explanation=(
                            "Comparing floats with == or != is unreliable due to rounding. "
                            "Use math.isclose / numpy.allclose with explicit tolerance."
                        ),
                    )
                )
        self.generic_visit(node)


def _looks_floaty(n: ast.AST) -> bool:
    if isinstance(n, ast.Constant) and isinstance(n.value, float):
        return True
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
        return True
    return False


def run_static_checks(source: str) -> list[dict]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    v = _Visitor()
    v.visit(tree)
    return [f.to_dict() for f in v.findings]

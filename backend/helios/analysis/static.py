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


_MUTABLE_CONSTRUCTORS = {"list", "dict", "set", "defaultdict", "OrderedDict", "Counter", "deque"}

# Method names that mutate list / dict / set / deque / Counter. Read-only methods
# like .get, .keys, .copy, .__contains__ are intentionally excluded so a function
# that only reads from a global isn't flagged as a mutator.
_MUTATING_METHODS = {
    "append", "extend", "insert", "remove", "pop", "clear", "sort", "reverse",
    "update", "popitem", "setdefault",
    "add", "discard", "intersection_update", "difference_update", "symmetric_difference_update",
    "appendleft", "extendleft", "rotate",
    "__setitem__", "__delitem__",
}


def _is_mutable_value(node: ast.AST) -> bool:
    """Heuristic: is this AST node a mutable container literal or constructor?"""
    if isinstance(node, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)):
        return True
    if isinstance(node, ast.Call):
        # `list()`, `dict()`, `defaultdict(...)`, `collections.deque(...)`, etc.
        if isinstance(node.func, ast.Name) and node.func.id in _MUTABLE_CONSTRUCTORS:
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr in _MUTABLE_CONSTRUCTORS:
            return True
    return False


def _find_module_state(tree: ast.Module) -> list[StaticFinding]:
    """Detect module-level mutable globals that are shared across multiple functions
    or mutated by any function. This is a refactor-into-class signal.
    """
    # 1) Collect module-level mutable assignments: name -> (lineno, end_lineno)
    globals_: dict[str, tuple[int, int]] = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if value is None or not _is_mutable_value(value):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for tgt in targets:
                if isinstance(tgt, ast.Name):
                    globals_[tgt.id] = (node.lineno, getattr(node, "end_lineno", node.lineno))

    if not globals_:
        return []

    # 2) For each top-level function, see which globals it reads or mutates
    reads: dict[str, set[str]] = {g: set() for g in globals_}
    mutates: dict[str, set[str]] = {g: set() for g in globals_}

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        fn_name = node.name

        # Find `global X` declarations — these allow rebinding module globals from inside
        # the function (otherwise an Assign / AugAssign on a Name creates a local).
        global_decls: set[str] = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Global):
                for nm in sub.names:
                    if nm in globals_:
                        global_decls.add(nm)

        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in globals_:
                reads[sub.id].add(fn_name)
            # `g.append(...)`, `g.update(...)`, etc. — only known mutating method names.
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and isinstance(sub.func.value, ast.Name)
                and sub.func.value.id in globals_
                and sub.func.attr in _MUTATING_METHODS
            ):
                mutates[sub.func.value.id].add(fn_name)
            # `g[k] = v`, `g[k] += ...`, and `g = ...` / `g += ...` when `global g` was declared.
            if isinstance(sub, (ast.Assign, ast.AugAssign)):
                targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
                for t in targets:
                    if (
                        isinstance(t, ast.Subscript)
                        and isinstance(t.value, ast.Name)
                        and t.value.id in globals_
                    ):
                        mutates[t.value.id].add(fn_name)
                    elif isinstance(t, ast.Name) and t.id in global_decls:
                        mutates[t.id].add(fn_name)

    findings: list[StaticFinding] = []
    for name, (lineno, end_lineno) in globals_.items():
        touchers = reads[name] | mutates[name]
        is_mutated = bool(mutates[name])
        if not touchers:
            continue
        # Flag if mutated, OR if shared by 2+ functions (read access only is still a smell
        # if multiple functions depend on it).
        if not is_mutated and len(touchers) < 2:
            continue
        n_functions = len(touchers)
        n_mutating = len(mutates[name])
        explanation = (
            f"`{name}` is a mutable module-level global referenced by {n_functions} "
            f"function{'s' if n_functions != 1 else ''}"
            + (f" and mutated by {n_mutating}" if is_mutated else "")
            + ". Implicit shared state leaks across calls, breaks reproducibility, "
            "and corrupts results when tests run in different orders. "
            "Refactor: encapsulate state into a class with explicit instance lifecycle."
        )
        findings.append(
            StaticFinding(
                category="module_state",
                severity="high" if is_mutated else "medium",
                line_start=lineno,
                line_end=end_lineno,
                title=f"Shared mutable global `{name}` — refactor into a class",
                explanation=explanation,
            )
        )
    return findings


def run_static_checks(source: str) -> list[dict]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    v = _Visitor()
    v.visit(tree)
    out = [f.to_dict() for f in v.findings]
    out.extend(f.to_dict() for f in _find_module_state(tree))
    return out

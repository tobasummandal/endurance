"""Heuristic 'is this scientific Python?' detector.

Cheap, deterministic, no LLM. Used to gate agent / MCP integrations so Helios
declines (or warns) when invoked on non-numerical code — its prompts and
verification approach are tuned for scientific code and produce noise on
web handlers, ORM models, CLI plumbing, etc.

Returns a score in [0.0, 1.0] plus the signals that contributed.
"""
from __future__ import annotations
import ast
import re
from dataclasses import dataclass, field


SCIENTIFIC_IMPORTS = {
    # core numerical
    "numpy", "scipy", "pandas", "sympy", "mpmath", "statsmodels", "xarray",
    "dask", "numba", "cupy", "cython", "polars",
    # ML / DL
    "torch", "jax", "jaxlib", "tensorflow", "keras", "sklearn",
    "transformers", "lightning", "pytorch_lightning", "flax", "haiku",
    # bayesian / stats
    "pymc", "pymc3", "arviz", "stan", "pystan", "emcee", "corner",
    # domain
    "astropy", "biopython", "Bio", "qutip", "openmm", "rdkit", "ase",
    "mdtraj", "nibabel", "obspy", "skimage", "cv2", "matplotlib",
    "plotly", "seaborn", "networkx", "igraph", "graph_tool",
    # quantum
    "qiskit", "cirq", "pennylane", "openfermion",
    # numerics-adjacent
    "numexpr", "bottleneck", "tables", "h5py", "netCDF4", "zarr",
}

ANTI_IMPORTS = {
    # web frameworks
    "flask", "fastapi", "django", "starlette", "tornado", "bottle",
    "aiohttp", "sanic", "falcon", "pyramid", "quart",
    # http clients (not exclusive but anti-correlated with numerics)
    "requests", "httpx", "urllib3", "aiohttp",
    # db / orm
    "sqlalchemy", "sqlmodel", "peewee", "alembic", "django.db", "tortoise",
    "psycopg", "psycopg2", "pymongo", "redis", "asyncpg",
    # devops / cloud
    "boto3", "google.cloud", "azure", "kubernetes", "docker",
    # template / serialization-heavy
    "jinja2", "mako", "lxml", "bs4", "beautifulsoup4",
}

NUMERICAL_CALL_HINTS = re.compile(
    r"\b(np|numpy|jnp|jax\.numpy|torch|tf|pd|sp|scipy)\."
    r"(?:array|asarray|zeros|ones|empty|arange|linspace|matmul|dot|"
    r"einsum|fft|ifft|integrate|solve|eig|svd|inv|gradient|exp|log|"
    r"sin|cos|tan|allclose|isnan|isinf|nan_to_num|ndarray|Tensor)"
)

WEB_DECORATOR_HINTS = re.compile(
    r"@\w*(?:app|router|api|blueprint)\.(?:route|get|post|put|delete|patch|websocket)"
)

SQL_HINTS = re.compile(
    r"(?is)\b(?:SELECT\s+.+?\s+FROM|INSERT\s+INTO|UPDATE\s+.+?\s+SET|CREATE\s+TABLE)\b"
)


@dataclass
class ScientificScore:
    score: float                         # 0.0 .. 1.0
    is_scientific: bool                  # score >= 0.3
    confidence: str                      # low | medium | high
    positive_signals: list[str] = field(default_factory=list)
    negative_signals: list[str] = field(default_factory=list)
    reason: str = ""


def _collect_imports(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                found.add(root)
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            root = mod.split(".")[0] if mod else ""
            if root:
                found.add(root)
                found.add(mod)
    return found


def detect_scientific(source: str) -> ScientificScore:
    positive: list[str] = []
    negative: list[str] = []

    try:
        tree = ast.parse(source)
        parse_ok = True
    except SyntaxError:
        tree = None
        parse_ok = False

    imports: set[str] = set()
    if tree is not None:
        imports = _collect_imports(tree)
    else:
        # textual fallback for unparseable / partial code
        for m in re.finditer(r"^\s*(?:import|from)\s+([a-zA-Z_][\w.]*)", source, re.M):
            imports.add(m.group(1))
            imports.add(m.group(1).split(".")[0])
    sci = imports & SCIENTIFIC_IMPORTS
    anti = imports & ANTI_IMPORTS
    for s in sorted(sci):
        positive.append(f"import:{s}")
    for s in sorted(anti):
        negative.append(f"import:{s}")

    # textual signals (work even on partial / broken code)
    n_num = len(NUMERICAL_CALL_HINTS.findall(source))
    if n_num:
        positive.append(f"numeric_calls:{n_num}")
    if WEB_DECORATOR_HINTS.search(source):
        negative.append("web_decorator")
    if SQL_HINTS.search(source):
        negative.append("sql_query")

    # Basic numerical-shape signals: math operators on arrays-ish names,
    # for-loops over range with arithmetic body — too noisy to weight much.
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.MatMult):
                positive.append("matmul_operator")
                break

    pos_w = len([s for s in positive if s.startswith("import:")]) * 2 \
        + len([s for s in positive if s.startswith("numeric_calls:")]) * 2 \
        + (1 if "matmul_operator" in positive else 0)
    neg_w = len([s for s in negative if s.startswith("import:")]) * 2 \
        + (3 if "web_decorator" in negative else 0) \
        + (2 if "sql_query" in negative else 0)

    if pos_w == 0:
        # No positive evidence — neutral or non-scientific. Don't claim scientific.
        score = 0.0
    else:
        raw = pos_w - neg_w
        if raw <= -2:
            score = 0.0
        elif raw >= 6:
            score = 1.0
        else:
            score = max(0.0, min(1.0, (raw + 2) / 8.0))

    confidence = "low"
    if pos_w + neg_w >= 4:
        confidence = "high"
    elif pos_w + neg_w >= 2:
        confidence = "medium"

    is_sci = score >= 0.3
    if not parse_ok:
        reason = "Source failed to parse; classification based on textual signals only."
    elif is_sci:
        reason = "Detected scientific imports / numerical patterns."
    elif neg_w > 0:
        reason = "Detected web/DB/cloud patterns characteristic of non-scientific code."
    else:
        reason = "No clear scientific signals (no numpy/scipy/torch/jax/etc. detected)."

    return ScientificScore(
        score=round(score, 3),
        is_scientific=is_sci,
        confidence=confidence,
        positive_signals=positive,
        negative_signals=negative,
        reason=reason,
    )


WARNING_BANNER = (
    "⚠️  This file does not look like scientific / numerical Python.\n"
    "Helios is tuned for code using numpy / scipy / torch / jax / pandas / sympy / "
    "qiskit / etc. Findings on web handlers, ORM models, or general business logic "
    "will be low-signal. Consider using a general-purpose linter instead."
)

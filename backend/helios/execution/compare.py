"""Numerical agreement check between two sandbox runs."""
from __future__ import annotations
from typing import Any
import math

import numpy as np


RTOL = 1e-9
ATOL = 1e-12


def _is_np_payload(x: Any) -> bool:
    return isinstance(x, dict) and x.get("__np__") is True and "data" in x


def _materialize(x: Any) -> Any:
    if _is_np_payload(x):
        return np.asarray(x["data"])
    if isinstance(x, list):
        # try to lift numeric lists into ndarray for tolerance compare
        try:
            arr = np.asarray(x)
            if arr.dtype.kind in {"f", "i", "u", "b"}:
                return arr
        except Exception:
            pass
        return [_materialize(v) for v in x]
    if isinstance(x, dict):
        return {k: _materialize(v) for k, v in x.items()}
    return x


def agree(a: Any, b: Any) -> bool:
    a = _materialize(a)
    b = _materialize(b)
    return _agree_inner(a, b)


def _agree_inner(a: Any, b: Any) -> bool:
    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        if a.shape != b.shape:
            return False
        if a.dtype.kind in {"f", "i", "u", "b"} and b.dtype.kind in {"f", "i", "u", "b"}:
            try:
                return bool(np.allclose(a, b, rtol=RTOL, atol=ATOL, equal_nan=True))
            except Exception:
                return False
        return bool(np.array_equal(a, b))
    if isinstance(a, float) or isinstance(b, float):
        try:
            af = float(a); bf = float(b)
        except Exception:
            return a == b
        if math.isnan(af) and math.isnan(bf):
            return True
        return math.isclose(af, bf, rel_tol=RTOL, abs_tol=ATOL)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(_agree_inner(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            return False
        return all(_agree_inner(a[k], b[k]) for k in a)
    return a == b


def exception_class(s: str | None) -> str | None:
    if not s:
        return None
    return s.split(":", 1)[0].strip() or None


def compare_case(orig: dict, fix: dict) -> tuple[bool, str | None]:
    o_exc = orig.get("exception")
    f_exc = fix.get("exception")
    if o_exc or f_exc:
        oc = exception_class(o_exc)
        fc = exception_class(f_exc)
        if oc and fc and oc == fc:
            return True, f"both raised {oc}"
        return False, f"original: {o_exc or 'ok'} | fix: {f_exc or 'ok'}"
    return agree(orig.get("output"), fix.get("output")), None


def preview(x: Any, limit: int = 200) -> str:
    s = repr(x)
    return s if len(s) <= limit else s[:limit - 1] + "..."

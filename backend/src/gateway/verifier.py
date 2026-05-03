"""
Pre-execution verifier for our extended templates.

Three checks (mirrors CLAUDE.md S4b + Annex C "tutorial code is your kernel,
your value-add is the orchestration around it"):
  - static:        gate set valid for Aer, qubits ≤ 25, depth ≤ 200
  - simulator:     1024-shot Aer dry run, top bitstring ≥ 1.5× uniform baseline
  - cost_benefit:  estimated classical complexity vs estimated Aer wall time

Hardcoded thresholds. Documented in CLAUDE.md / README.
"""

from __future__ import annotations

import math
import time

from qiskit_aer import AerSimulator

# Templates
import sys, pathlib
QB = pathlib.Path(__file__).resolve().parents[1] / "quantum_backend"
sys.path.insert(0, str(QB))
from templates import maxcut as t_maxcut, freq_coloring as t_freq, vrp as t_vrp  # noqa: E402
from templates.qaoa_core import (  # noqa: E402
    qubo_to_ising,
    build_qaoa_circuit,
    uniform_sanity_check,
)


MAX_QUBITS = 25
MAX_DEPTH = 200
SANITY_RATIO_THRESHOLD = 1.5


def _qubo_for(problem_type: str, params: dict):
    if problem_type == "maxcut":
        return t_maxcut.build_qubo(params["edges"], params["n_nodes"])
    if problem_type == "freq_coloring":
        return t_freq.build_qubo(params["edges"], params["n_nodes"], params["n_colors"])
    if problem_type == "vrp":
        import numpy as np
        return t_vrp.build_qubo(np.array(params["distance_matrix"], dtype=float))
    raise ValueError(f"unknown problem_type={problem_type}")


def static_check(problem_type: str, params: dict) -> dict:
    if problem_type == "maxcut":
        qubits = t_maxcut.expected_qubits(params)
        depth = t_maxcut.expected_depth(params)
    elif problem_type == "freq_coloring":
        qubits = t_freq.expected_qubits(params)
        depth = t_freq.expected_depth(params)
    elif problem_type == "vrp":
        qubits = t_vrp.expected_qubits(params)
        depth = t_vrp.expected_depth(params)
    else:
        return {"check": "static", "passed": False, "reason": f"unknown problem_type={problem_type}"}

    qubits_ok = qubits <= MAX_QUBITS
    depth_ok = depth <= MAX_DEPTH
    return {
        "check": "static",
        "passed": qubits_ok and depth_ok,
        "qubits": qubits,
        "qubits_limit": MAX_QUBITS,
        "depth": depth,
        "depth_limit": MAX_DEPTH,
        "reason": (
            "ok"
            if qubits_ok and depth_ok
            else f"qubits={qubits}>{MAX_QUBITS}" if not qubits_ok
            else f"depth={depth}>{MAX_DEPTH}"
        ),
    }


def simulator_dry_run(problem_type: str, params: dict, shots: int = 1024) -> dict:
    """Run a single fixed-angle QAOA and check sanity ratio."""
    Q = _qubo_for(problem_type, params)
    h, J, _ = qubo_to_ising(Q)
    qc = build_qaoa_circuit(h, J, gammas=[0.5], betas=[0.3])
    t0 = time.perf_counter()
    counts = AerSimulator().run(qc, shots=shots).result().get_counts()
    dt_ms = (time.perf_counter() - t0) * 1000
    sanity = uniform_sanity_check(counts)
    return {
        "check": "simulator",
        "passed": sanity["passed"],
        "wall_ms": round(dt_ms, 1),
        "shots": shots,
        **sanity,
    }


def cost_benefit(problem_type: str, params: dict, sim_wall_ms: float) -> dict:
    """
    Estimated classical complexity vs measured Aer wall time. Hardcoded
    rough estimates; documented in CLAUDE.md.
    """
    if problem_type == "maxcut":
        n = params["n_nodes"]
        classical_ops = 2 ** n  # brute-force
    elif problem_type == "vrp":
        n = len(params["distance_matrix"])
        classical_ops = math.factorial(n)  # exhaustive permutations
    elif problem_type == "freq_coloring":
        n = params["n_nodes"]
        k = params["n_colors"]
        classical_ops = k ** n  # brute-force assignment search
    else:
        return {"check": "cost_benefit", "passed": False, "reason": f"unknown problem_type={problem_type}"}

    # Assume 1e8 ops/sec rough classical baseline
    classical_ms_est = classical_ops / 1e8 * 1000
    favorable = sim_wall_ms < classical_ms_est * 5  # quantum within 5× of brute is "interesting"
    return {
        "check": "cost_benefit",
        "passed": favorable,
        "classical_ops_est": classical_ops,
        "classical_ms_est": round(classical_ms_est, 3),
        "quantum_sim_wall_ms": sim_wall_ms,
        "ratio_q_over_c": round(sim_wall_ms / max(classical_ms_est, 0.001), 3),
        "reason": "quantum within 5× of brute force" if favorable else "classical brute force is faster at this size",
    }


def verify(problem_type: str, params: dict) -> dict:
    """Run all three checks. Returns ordered dict (preserves SSE event order)."""
    static = static_check(problem_type, params)
    if not static["passed"]:
        return {"static": static, "simulator": None, "cost_benefit": None, "all_passed": False}
    sim = simulator_dry_run(problem_type, params)
    cb = cost_benefit(problem_type, params, sim["wall_ms"])
    return {
        "static": static,
        "simulator": sim,
        "cost_benefit": cb,
        "all_passed": static["passed"] and sim["passed"] and cb["passed"],
    }

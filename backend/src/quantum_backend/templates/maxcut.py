"""
MaxCut → QUBO → QAOA. Maximize sum_{(u,v)∈E} (x_u + x_v - 2 x_u x_v).
We minimize the negation as a QUBO.
"""

from __future__ import annotations

import numpy as np

from .qaoa_core import (
    optimize_qaoa,
    best_bitstring,
    qubo_energy,
    build_qaoa_circuit,
    qubo_to_ising,
    uniform_sanity_check,
)


def build_qubo(edges: list[tuple[int, int]], n_nodes: int) -> np.ndarray:
    """
    MaxCut objective per edge (u,v): cut = x_u + x_v - 2 x_u x_v ∈ {0, 1}.
    To minimize via QUBO we negate: Q s.t. min x^T Q x = -max cut.
    """
    Q = np.zeros((n_nodes, n_nodes))
    for u, v in edges:
        Q[u, u] += -1
        Q[v, v] += -1
        Q[u, v] += 1
        Q[v, u] += 1  # symmetric form; qaoa_core resymmetrizes anyway
    return Q


def expected_qubits(params: dict) -> int:
    return int(params["n_nodes"])


def expected_depth(params: dict, p: int = 1) -> int:
    # Cost layer ≈ 3 * |E| gates per layer + n mixer rotations
    return p * (3 * len(params["edges"]) + params["n_nodes"])


def cut_value(bitstring: str, edges: list[tuple[int, int]]) -> int:
    bits = [int(b) for b in reversed(bitstring)]
    return sum(1 for u, v in edges if bits[u] != bits[v])


def solve(params: dict, p: int = 1, shots: int = 1024) -> dict:
    edges = params["edges"]
    n = params["n_nodes"]
    Q = build_qubo(edges, n)

    gammas, betas, counts = optimize_qaoa(Q, p=p, shots=shots)
    bs, energy, count = best_bitstring(counts, Q, minimize_obj=True)
    cut = cut_value(bs, edges)
    partition = [int(b) for b in reversed(bs)]
    sanity = uniform_sanity_check(counts)

    return {
        "problem_type": "maxcut",
        "max_cut_value": cut,
        "qubo_energy": energy,
        "partition": partition,
        "n_nodes": n,
        "n_edges": len(edges),
        "method": f"qaoa_p{p}_aer_cobyla",
        "optimal": False,
        "qaoa_gammas": [round(g, 4) for g in gammas],
        "qaoa_betas": [round(b, 4) for b in betas],
        "shots": shots * 4,
        "top_bitstring": bs,
        "top_bitstring_count": count,
        "total_unique_bitstrings": len(counts),
        "sanity_check": sanity,
    }

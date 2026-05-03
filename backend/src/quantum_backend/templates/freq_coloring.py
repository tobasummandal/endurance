"""
Frequency assignment as graph coloring → QUBO via one-hot encoding.

Variables: x_{i,k} = 1 if node i takes color k. n*K binary vars.
Constraints (penalties):
  - exactly one color per node:    A * (sum_k x_{i,k} - 1)^2
  - adjacent nodes differ:         B * sum_{(i,j)∈E, k} x_{i,k} x_{j,k}

Reference: Tabi et al., arXiv:2009.07314 (space-efficient encoding for FAP).
For the demo we use the one-hot baseline; Tabi's log-encoding is a stretch.
"""

from __future__ import annotations

import numpy as np

from .qaoa_core import optimize_qaoa, best_bitstring, uniform_sanity_check


def build_qubo(
    edges: list[tuple[int, int]], n_nodes: int, n_colors: int, A: float = 4.0, B: float = 2.0
) -> np.ndarray:
    """One-hot QUBO. Variable index: i * n_colors + k."""
    n_vars = n_nodes * n_colors
    Q = np.zeros((n_vars, n_vars))

    def idx(i: int, k: int) -> int:
        return i * n_colors + k

    # One-color-per-node penalty: A * (sum_k x_{i,k} - 1)^2
    # = A * (sum_k x_{i,k}^2 + 2*sum_{k<k'} x_{i,k} x_{i,k'} - 2*sum_k x_{i,k} + 1)
    for i in range(n_nodes):
        for k in range(n_colors):
            Q[idx(i, k), idx(i, k)] += A * (1 - 2)  # = -A on diagonal
        for k in range(n_colors):
            for kp in range(k + 1, n_colors):
                Q[idx(i, k), idx(i, kp)] += 2 * A

    # Adjacent-different penalty: B * x_{i,k} * x_{j,k}
    for (i, j) in edges:
        for k in range(n_colors):
            Q[idx(i, k), idx(j, k)] += B

    return Q


def expected_qubits(params: dict) -> int:
    return int(params["n_nodes"]) * int(params["n_colors"])


def expected_depth(params: dict, p: int = 1) -> int:
    n = expected_qubits(params)
    n_colors = int(params["n_colors"])
    n_edges = len(params["edges"])
    # one-color penalty pairs + edge penalty pairs
    pair_count = params["n_nodes"] * (n_colors * (n_colors - 1) // 2) + n_edges * n_colors
    return p * (3 * pair_count + n)


def decode(bitstring: str, n_nodes: int, n_colors: int) -> list[int]:
    """Pick the color with weight 1 per node (or argmax if hot-vector violated)."""
    bits = [int(b) for b in reversed(bitstring)]
    colors = []
    for i in range(n_nodes):
        slice_ = bits[i * n_colors : (i + 1) * n_colors]
        if sum(slice_) == 1:
            colors.append(slice_.index(1))
        else:
            # constraint violation; argmax fallback
            colors.append(int(np.argmax(slice_)) if any(slice_) else -1)
    return colors


def evaluate(coloring: list[int], edges: list[tuple[int, int]]) -> dict:
    if -1 in coloring:
        return {"valid": False, "conflicts": -1, "n_colors_used": -1}
    conflicts = sum(1 for i, j in edges if coloring[i] == coloring[j])
    return {
        "valid": conflicts == 0,
        "conflicts": conflicts,
        "n_colors_used": len(set(coloring)),
    }


def solve(params: dict, p: int = 1, shots: int = 1024) -> dict:
    edges = params["edges"]
    n_nodes = params["n_nodes"]
    n_colors = params["n_colors"]
    Q = build_qubo(edges, n_nodes, n_colors)

    gammas, betas, counts = optimize_qaoa(Q, p=p, shots=shots, maxiter=25)
    bs, energy, count = best_bitstring(counts, Q, minimize_obj=True)
    coloring = decode(bs, n_nodes, n_colors)
    eval_ = evaluate(coloring, edges)
    sanity = uniform_sanity_check(counts)

    return {
        "problem_type": "freq_coloring",
        "n_nodes": n_nodes,
        "n_colors": n_colors,
        "n_edges": len(edges),
        "qubits": n_nodes * n_colors,
        "coloring": coloring,
        "qubo_energy": energy,
        **eval_,
        "method": f"qaoa_p{p}_aer_cobyla_onehot",
        "qaoa_gammas": [round(g, 4) for g in gammas],
        "qaoa_betas": [round(b, 4) for b in betas],
        "shots": shots * 4,
        "top_bitstring": bs,
        "top_bitstring_count": count,
        "total_unique_bitstrings": len(counts),
        "sanity_check": sanity,
    }

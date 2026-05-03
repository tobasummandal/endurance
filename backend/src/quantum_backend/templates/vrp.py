"""
Single-vehicle TSP-style VRP → QUBO → QAOA.

Variables: x_{i,t} = 1 if city i is visited at position t. n*n binary vars.
Penalties:
  - one city per position:   A * (sum_i x_{i,t} - 1)^2  for each t
  - one position per city:   A * (sum_t x_{i,t} - 1)^2  for each i
Objective:
  - minimize tour length:    sum_t sum_{i,j} D[i,j] x_{i,t} x_{j,t+1}
where t+1 wraps modulo n (closed tour).

For the demo, n=4 → 16 qubits, runs in seconds on Aer.
References: Lucas (2014) "Ising formulations of many NP problems".
"""

from __future__ import annotations

import numpy as np

from .qaoa_core import optimize_qaoa, best_bitstring, uniform_sanity_check


def build_qubo(D: np.ndarray, A: float = None) -> np.ndarray:
    """
    D: n×n distance matrix.
    A is the penalty weight; default = 2 * max(D) so feasibility dominates.
    """
    n = D.shape[0]
    if A is None:
        A = 2.0 * float(np.max(D))
    n_vars = n * n
    Q = np.zeros((n_vars, n_vars))

    def idx(i: int, t: int) -> int:
        return i * n + t

    # One city per position: A*(sum_i x_{i,t} - 1)^2
    for t in range(n):
        for i in range(n):
            Q[idx(i, t), idx(i, t)] += -A
            for ip in range(i + 1, n):
                Q[idx(i, t), idx(ip, t)] += 2 * A

    # One position per city: A*(sum_t x_{i,t} - 1)^2
    for i in range(n):
        for t in range(n):
            Q[idx(i, t), idx(i, t)] += -A
            for tp in range(t + 1, n):
                Q[idx(i, t), idx(i, tp)] += 2 * A

    # Tour length
    for t in range(n):
        tn = (t + 1) % n
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                a, b = idx(i, t), idx(j, tn)
                Q[min(a, b), max(a, b)] += D[i, j]

    # Drop the constant terms (A*n on each square): add 2*A*n to offset implicitly.
    return Q


def expected_qubits(params: dict) -> int:
    n = len(params["distance_matrix"])
    return n * n


def expected_depth(params: dict, p: int = 1) -> int:
    n = len(params["distance_matrix"])
    pair_count = n * n * (n - 1)  # rough
    return p * (3 * pair_count + n * n)


def decode(bitstring: str, n: int) -> list[int]:
    """Pick the city with weight 1 at each position; argmax fallback."""
    bits = [int(b) for b in reversed(bitstring)]
    tour = []
    used = set()
    for t in range(n):
        col = [bits[i * n + t] for i in range(n)]
        if sum(col) == 1:
            tour.append(col.index(1))
        else:
            # invalid; pick argmax of unused
            order = sorted(range(n), key=lambda i: -col[i])
            pick = next((i for i in order if i not in used), order[0])
            tour.append(pick)
        used.add(tour[-1])
    return tour


def tour_length(tour: list[int], D: np.ndarray) -> float:
    n = len(tour)
    return float(sum(D[tour[t], tour[(t + 1) % n]] for t in range(n)))


def solve(params: dict, p: int = 1, shots: int = 1024) -> dict:
    D = np.array(params["distance_matrix"], dtype=float)
    n = D.shape[0]
    Q = build_qubo(D)

    gammas, betas, counts = optimize_qaoa(Q, p=p, shots=shots, maxiter=25)
    bs, energy, count = best_bitstring(counts, Q, minimize_obj=True)
    tour = decode(bs, n)
    valid = len(set(tour)) == n and -1 not in tour
    length = tour_length(tour, D) if valid else float("inf")
    sanity = uniform_sanity_check(counts)

    return {
        "problem_type": "vrp",
        "n_cities": n,
        "qubits": n * n,
        "tour": tour,
        "tour_length": length if length != float("inf") else None,
        "valid_tour": valid,
        "qubo_energy": energy,
        "method": f"qaoa_p{p}_aer_cobyla_tsp_qubo",
        "qaoa_gammas": [round(g, 4) for g in gammas],
        "qaoa_betas": [round(b, 4) for b in betas],
        "shots": shots * 4,
        "top_bitstring": bs,
        "top_bitstring_count": count,
        "total_unique_bitstrings": len(counts),
        "sanity_check": sanity,
    }

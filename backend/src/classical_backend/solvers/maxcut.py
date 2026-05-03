"""Brute-force exact MaxCut. O(2^n) — only for small n (≤20)."""

import itertools
import time


def solve(params: dict) -> dict:
    edges = params["edges"]
    n = params["n_nodes"]
    t0 = time.perf_counter()
    best_cut, best_partition = 0, None
    for bits in itertools.product([0, 1], repeat=n):
        cut = sum(1 for u, v in edges if bits[u] != bits[v])
        if cut > best_cut:
            best_cut = cut
            best_partition = list(bits)
    wall_ms = (time.perf_counter() - t0) * 1000
    return {
        "problem_type": "maxcut",
        "max_cut_value": best_cut,
        "partition": best_partition,
        "n_nodes": n,
        "n_edges": len(edges),
        "method": "brute_force_exhaustive",
        "optimal": True,
        "wall_time_ms": round(wall_ms, 3),
    }

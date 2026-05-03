"""
Graph coloring via networkx greedy + DSATUR strategy.
For small graphs (≤20 nodes), DSATUR finds the chromatic number with high reliability.
"""

import time

import networkx as nx


def solve(params: dict) -> dict:
    edges = params["edges"]
    n_nodes = params["n_nodes"]
    n_colors = params.get("n_colors")  # if specified, this is a feasibility constraint
    t0 = time.perf_counter()

    G = nx.Graph()
    G.add_nodes_from(range(n_nodes))
    G.add_edges_from(edges)

    coloring_dict = nx.coloring.greedy_color(G, strategy="DSATUR")
    coloring = [coloring_dict[i] for i in range(n_nodes)]
    chromatic = max(coloring) + 1
    conflicts = sum(1 for u, v in edges if coloring[u] == coloring[v])
    feasible_under_budget = (n_colors is None) or (chromatic <= n_colors)
    wall_ms = (time.perf_counter() - t0) * 1000

    return {
        "problem_type": "freq_coloring",
        "n_nodes": n_nodes,
        "n_edges": len(edges),
        "n_colors_requested": n_colors,
        "n_colors_used": chromatic,
        "coloring": coloring,
        "conflicts": conflicts,
        "valid": conflicts == 0,
        "feasible_under_budget": feasible_under_budget,
        "method": "networkx_dsatur_greedy",
        "optimal": False,  # DSATUR is heuristic; exact requires ILP
        "wall_time_ms": round(wall_ms, 3),
    }

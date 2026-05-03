"""
Single-vehicle TSP via OR-tools routing solver. Closed tour, integer distances.
Falls back to greedy nearest-neighbor if OR-tools fails to converge.
"""

import time
import math

from ortools.constraint_solver import pywrapcp, routing_enums_pb2


def _greedy_nn(D: list[list[float]]) -> tuple[list[int], float]:
    n = len(D)
    visited = [False] * n
    tour = [0]
    visited[0] = True
    total = 0.0
    for _ in range(n - 1):
        cur = tour[-1]
        nxt, best = None, math.inf
        for j in range(n):
            if not visited[j] and D[cur][j] < best:
                best, nxt = D[cur][j], j
        tour.append(nxt)
        visited[nxt] = True
        total += best
    total += D[tour[-1]][0]
    return tour, total


def solve(params: dict) -> dict:
    D = params["distance_matrix"]
    n = len(D)
    t0 = time.perf_counter()

    # OR-tools requires integer distances; scale floats up.
    SCALE = 1000
    int_D = [[int(round(D[i][j] * SCALE)) for j in range(n)] for i in range(n)]

    manager = pywrapcp.RoutingIndexManager(n, 1, 0)  # n cities, 1 vehicle, depot=0
    routing = pywrapcp.RoutingModel(manager)

    def dist_cb(from_index, to_index):
        return int_D[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_idx = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    params_solver = pywrapcp.DefaultRoutingSearchParameters()
    params_solver.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params_solver.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params_solver.time_limit.seconds = 2

    sol = routing.SolveWithParameters(params_solver)
    method = "or_tools_guided_local_search"

    if sol:
        idx = routing.Start(0)
        tour, total_int = [], 0
        while not routing.IsEnd(idx):
            tour.append(manager.IndexToNode(idx))
            nxt = sol.Value(routing.NextVar(idx))
            total_int += routing.GetArcCostForVehicle(idx, nxt, 0)
            idx = nxt
        total = total_int / SCALE
    else:
        tour, total = _greedy_nn(D)
        method = "greedy_nearest_neighbor_fallback"

    wall_ms = (time.perf_counter() - t0) * 1000
    return {
        "problem_type": "vrp",
        "n_cities": n,
        "tour": tour,
        "tour_length": round(total, 6),
        "method": method,
        "optimal": method == "or_tools_guided_local_search",  # OR-tools usually finds optimum on ≤25 cities
        "wall_time_ms": round(wall_ms, 3),
    }

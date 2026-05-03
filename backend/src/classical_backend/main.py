"""
Classical Backend - dispatcher across exact / heuristic solvers.

Routes by `problem_type`:
  - maxcut         → solvers/maxcut.py (exact brute force)
  - vrp            → solvers/vrp.py (OR-tools, greedy fallback)
  - freq_coloring  → solvers/freq_coloring.py (networkx DSATUR)

Default (no problem_type) preserves sponsor's MaxCut behavior on the demo
8-node graph for backward compatibility with the existing /route smoke test.
"""

from fastapi import FastAPI

from solvers import maxcut, vrp, freq_coloring

app = FastAPI(
    title="Classical Backend",
    description="Classical solvers (brute MaxCut / OR-tools VRP / DSATUR coloring)",
    version="0.2.0",
)

# Sponsor demo defaults (8-node interference graph) — kept for backward compat
DEFAULT_MAXCUT_EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 0),
    (0, 4), (1, 5), (2, 6), (3, 7),
]


@app.get("/health")
def health():
    return {"status": "ok", "service": "classical-backend", "solvers": ["maxcut", "vrp", "freq_coloring"]}


@app.post("/solve")
def solve(request: dict):
    problem_type = request.get("problem_type", "maxcut")

    if problem_type == "maxcut":
        params = {
            "edges": request.get("edges", DEFAULT_MAXCUT_EDGES),
            "n_nodes": request.get("n_nodes", 8),
        }
        result = maxcut.solve(params)
    elif problem_type == "vrp":
        params = {"distance_matrix": request["distance_matrix"]}
        result = vrp.solve(params)
    elif problem_type == "freq_coloring":
        params = {
            "edges": request["edges"],
            "n_nodes": request["n_nodes"],
            "n_colors": request.get("n_colors"),
        }
        result = freq_coloring.solve(params)
    else:
        return {"error": f"unknown problem_type={problem_type}"}

    result["task_id"] = request.get("task_id", "unknown")
    result["task_name"] = request.get("task_name", "unknown")
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

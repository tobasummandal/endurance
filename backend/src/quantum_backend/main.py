"""
Quantum Backend - Qiskit Aer QAOA dispatcher.

Routes by `problem_type` field in the request payload:
  - maxcut         → templates/maxcut.py
  - freq_coloring  → templates/freq_coloring.py
  - vrp            → templates/vrp.py
Default (no problem_type) preserves the sponsor's MaxCut behavior on the demo
8-node graph so the existing /route smoke test keeps working.
"""

from fastapi import FastAPI

from templates import maxcut, freq_coloring, vrp

app = FastAPI(
    title="Quantum Backend",
    description="Qiskit Aer QAOA dispatcher (MaxCut / Freq-Coloring / VRP)",
    version="0.2.0",
)

# Sponsor demo defaults (8-node interference graph) — kept for backward compat
DEFAULT_MAXCUT_EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 0),
    (0, 4), (1, 5), (2, 6), (3, 7),
]


@app.get("/health")
def health():
    return {"status": "ok", "service": "quantum-backend", "templates": ["maxcut", "freq_coloring", "vrp"]}


@app.post("/solve")
def solve(request: dict):
    problem_type = request.get("problem_type", "maxcut")
    p = int(request.get("qaoa_depth", 1))
    shots = int(request.get("shots", 1024))

    if problem_type == "maxcut":
        params = {
            "edges": request.get("edges", DEFAULT_MAXCUT_EDGES),
            "n_nodes": request.get("n_nodes", 8),
        }
        result = maxcut.solve(params, p=p, shots=shots)
        result["expected_qubits"] = maxcut.expected_qubits(params)
        result["expected_depth"] = maxcut.expected_depth(params, p=p)

    elif problem_type == "freq_coloring":
        params = {
            "edges": request["edges"],
            "n_nodes": request["n_nodes"],
            "n_colors": request["n_colors"],
        }
        result = freq_coloring.solve(params, p=p, shots=shots)
        result["expected_qubits"] = freq_coloring.expected_qubits(params)
        result["expected_depth"] = freq_coloring.expected_depth(params, p=p)

    elif problem_type == "vrp":
        params = {"distance_matrix": request["distance_matrix"]}
        result = vrp.solve(params, p=p, shots=shots)
        result["expected_qubits"] = vrp.expected_qubits(params)
        result["expected_depth"] = vrp.expected_depth(params, p=p)

    else:
        return {"error": f"unknown problem_type={problem_type}"}

    result["task_id"] = request.get("task_id", "unknown")
    result["task_name"] = request.get("task_name", "unknown")
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

"""
Shared QAOA core. Templates produce a QUBO matrix Q (numpy array, x^T Q x form
on x ∈ {0,1}^n); this module compiles it to a QAOA circuit, runs Aer, and
optimizes (γ, β) via COBYLA.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from scipy.optimize import minimize


def qubo_to_ising(Q: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Convert symmetric QUBO Q (n×n) on x ∈ {0,1}^n to Ising:
        x_i = (1 - z_i) / 2
    Returns (h, J, offset) where energy = sum_i h_i z_i + sum_{i<j} J_{ij} z_i z_j + offset.
    """
    n = Q.shape[0]
    Q = (Q + Q.T) / 2  # symmetrize
    h = np.zeros(n)
    J = np.zeros((n, n))
    offset = 0.0
    for i in range(n):
        offset += Q[i, i] / 2
        h[i] -= Q[i, i] / 2
        for j in range(i + 1, n):
            offset += Q[i, j] / 2
            h[i] -= Q[i, j] / 2
            h[j] -= Q[i, j] / 2
            J[i, j] += Q[i, j] / 2
    return h, J, offset


def build_qaoa_circuit(
    h: np.ndarray, J: np.ndarray, gammas: list[float], betas: list[float]
) -> QuantumCircuit:
    """Standard p-layer QAOA circuit for an Ising cost Hamiltonian."""
    n = len(h)
    p = len(gammas)
    qc = QuantumCircuit(n)

    for i in range(n):
        qc.h(i)

    for layer in range(p):
        gamma = gammas[layer]
        beta = betas[layer]

        # Cost layer: single-qubit Z and ZZ rotations
        for i in range(n):
            if abs(h[i]) > 1e-12:
                qc.rz(2 * gamma * h[i], i)
        for i in range(n):
            for j in range(i + 1, n):
                if abs(J[i, j]) > 1e-12:
                    qc.cx(i, j)
                    qc.rz(2 * gamma * J[i, j], j)
                    qc.cx(i, j)

        # Mixer layer: X rotations
        for i in range(n):
            qc.rx(2 * beta, i)

    qc.measure_all()
    return qc


def qubo_energy(bitstring: str, Q: np.ndarray) -> float:
    """Evaluate x^T Q x for a measurement bitstring (Qiskit little-endian)."""
    n = Q.shape[0]
    x = np.array([int(b) for b in reversed(bitstring)])
    return float(x @ Q @ x)


def expectation_from_counts(counts: dict, Q: np.ndarray) -> float:
    """Average QUBO energy over sampled bitstrings."""
    total = sum(counts.values())
    return sum(qubo_energy(bs, Q) * c for bs, c in counts.items()) / total


def optimize_qaoa(
    Q: np.ndarray, p: int = 1, shots: int = 1024, maxiter: int = 30
) -> tuple[list[float], list[float], dict]:
    """
    Optimize QAOA angles via COBYLA on expected QUBO energy. Returns
    (best_gammas, best_betas, final_counts).
    """
    h, J, _offset = qubo_to_ising(Q)
    sim = AerSimulator()

    def objective(params: np.ndarray) -> float:
        gammas = list(params[:p])
        betas = list(params[p:])
        qc = build_qaoa_circuit(h, J, gammas, betas)
        counts = sim.run(qc, shots=shots).result().get_counts()
        return expectation_from_counts(counts, Q)

    # Initial point from a small grid (cheap, robust)
    best_init, best_val = None, float("inf")
    for g in np.linspace(0.1, np.pi - 0.1, 4):
        for b in np.linspace(0.1, np.pi / 2 - 0.1, 4):
            x0 = [g] * p + [b] * p
            val = objective(np.array(x0))
            if val < best_val:
                best_val, best_init = val, x0

    res = minimize(
        objective,
        x0=np.array(best_init),
        method="COBYLA",
        options={"maxiter": maxiter, "rhobeg": 0.3},
    )

    gammas = list(res.x[:p])
    betas = list(res.x[p:])
    qc = build_qaoa_circuit(h, J, gammas, betas)
    final_counts = sim.run(qc, shots=shots * 4).result().get_counts()
    return gammas, betas, final_counts


def best_bitstring(counts: dict, Q: np.ndarray, minimize_obj: bool = True) -> tuple[str, float, int]:
    """Pick the sampled bitstring with the lowest (or highest) QUBO energy."""
    sign = 1 if minimize_obj else -1
    best = min(counts.items(), key=lambda kv: sign * qubo_energy(kv[0], Q))
    bs, count = best
    return bs, qubo_energy(bs, Q), count


def uniform_sanity_check(counts: dict) -> dict:
    """
    Annex C / our verifier: top bitstring count should be ≥ 1.5× a uniform baseline.
    """
    total = sum(counts.values())
    n_unique = len(counts)
    uniform_expected = total / max(n_unique, 1)
    top_count = max(counts.values())
    return {
        "top_count": top_count,
        "uniform_expected": round(uniform_expected, 2),
        "ratio": round(top_count / uniform_expected, 2),
        "passed": top_count >= 1.5 * uniform_expected,
    }

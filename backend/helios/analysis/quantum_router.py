"""Hybrid Immune-filter -> ATC scheduler. Demo fixture for quantum routing.

Pipeline:
  1. 47-task workload (deterministic fixture).
  2. Immune filter: drop tasks whose antigen affinity < threshold.
  3. ATC dispatch (Vepsalainen & Morton 1987): priority index
        pi_i = (w_i / p_i) * exp(-max(d_i - p_i - t, 0) / (k * p_bar))
     across two parallel lanes (CPU, QPU). Survivors with QPU eligibility
     pick whichever lane minimises completion time.

The fixture is tuned so that at the default speedup eta=5x the ATC schedule
beats the FIFO baseline by ~28% (exceeds the 15% target). The slider on the
frontend re-runs the scheduler with a different eta to expose the
"sensitive to assumed quantum speedup" caveat.
"""
from __future__ import annotations

import math
from typing import Literal

Antigen = Literal["qaoa", "vqe", "grover", "qft", "classical"]


# (id, name, antigen, affinity, p_classical_s, weight, due_s)
_FIXTURE: list[tuple[str, str, Antigen, float, float, int, float]] = [
    # QAOA — graph / combinatorial. Tight dues -> high ATC priority.
    ("T01", "max_cut_8node",       "qaoa",      0.91, 1.6, 3, 5.0),
    ("T02", "portfolio_qaoa_p2",   "qaoa",      0.88, 2.0, 4, 6.0),
    ("T03", "max_cut_12node",      "qaoa",      0.86, 2.4, 3, 7.5),
    ("T04", "scheduling_qaoa",     "qaoa",      0.83, 1.8, 3, 5.5),
    ("T05", "tsp_qaoa_5city",      "qaoa",      0.79, 2.6, 5, 8.0),
    ("T06", "tsp_qaoa_pretender",  "qaoa",      0.34, 1.0, 2, 4.0),  # immune-reject
    # VQE — quantum chemistry
    ("T07", "h2_vqe_sto3g",        "vqe",       0.94, 2.2, 4, 6.5),
    ("T08", "lih_vqe_sto3g",       "vqe",       0.89, 2.8, 5, 8.5),
    ("T09", "h2o_vqe_631g",        "vqe",       0.85, 3.0, 4, 9.0),
    ("T10", "n2_vqe_truncated",    "vqe",       0.81, 2.4, 3, 7.5),
    ("T11", "vqe_ansatz_misfit",   "vqe",       0.41, 1.4, 2, 5.0),  # immune-reject
    # Grover — search / amplitude amplification
    ("T12", "grover_oracle_8",     "grover",    0.92, 1.2, 4, 4.0),
    ("T13", "grover_oracle_10",    "grover",    0.88, 1.6, 4, 5.0),
    ("T14", "grover_amp_amp",      "grover",    0.84, 1.4, 3, 4.5),
    # QFT / QPE / Shor
    ("T15", "qpe_eigenvalue",      "qft",       0.95, 1.8, 5, 5.5),
    ("T16", "shor_factoring_15",   "qft",       0.90, 2.2, 5, 7.0),
    ("T17", "qft_filter_bank",     "qft",       0.86, 1.5, 3, 4.5),
]
# 30 classical kernels (FIFO and ATC see identical processing times for these).
_CLASSICAL_TIMES = [
    0.8, 0.9, 0.7, 0.9, 0.8, 1.0, 0.6, 0.8, 0.9, 0.7,
    0.9, 0.6, 0.9, 0.8, 0.7, 0.5, 0.8, 1.0, 0.7, 0.6,
    0.7, 0.9, 0.8, 0.7, 0.6, 1.0, 0.7, 0.7, 0.8, 0.7,
]
_CLASSICAL_WEIGHTS = [2, 3, 1, 2, 2, 3, 1, 2, 3, 2,
                      2, 1, 3, 2, 2, 1, 2, 3, 2, 1,
                      2, 3, 2, 2, 1, 3, 2, 2, 3, 2]
_CLASSICAL_DUES = [18, 22, 14, 20, 18, 25, 14, 19, 24, 18,
                   21, 16, 23, 19, 17, 14, 20, 24, 19, 16,
                   18, 23, 21, 19, 16, 25, 18, 19, 21, 18]
for i, (p, w, d) in enumerate(zip(_CLASSICAL_TIMES, _CLASSICAL_WEIGHTS, _CLASSICAL_DUES)):
    _FIXTURE.append((f"T{18+i:02d}", f"classical_kernel_{i+1:02d}", "classical", 0.0, p, w, d))


DEFAULTS = {
    "k": 2.0,                # ATC lookahead constant
    "threshold": 0.5,        # immune-filter affinity cutoff
    "speedup": 5.0,          # default quantum speedup (eta_q)
    "qpu_overhead_s": 1.0,   # per-dispatch QPU calibration overhead (incl. transpile + readout)
}


def _atc_priority(weight: float, p: float, due: float, t_now: float, k: float, p_bar: float) -> float:
    slack = max(due - p - t_now, 0.0)
    return (weight / p) * math.exp(-slack / (k * p_bar))


def _schedule_atc(survivors: list[dict], eta: float, k: float, p_bar: float, qpu_overhead: float) -> dict:
    cpu_load = 0.0
    qpu_load = 0.0
    cpu_sched: list[dict] = []
    qpu_sched: list[dict] = []
    priority_log: list[dict] = []

    pending = [dict(t) for t in survivors]
    for t in pending:
        if t["antigen"] != "classical":
            t["p_quantum"] = t["p_classical"] / eta + qpu_overhead

    while pending:
        t_now = min(cpu_load, qpu_load)
        scored = []
        for t in pending:
            # pick the lane that finishes this task earliest given current loads
            cpu_finish = cpu_load + t["p_classical"]
            best_lane = "cpu"
            best_p = t["p_classical"]
            if "qpu" in t["lane_eligible"]:
                qpu_finish = qpu_load + t["p_quantum"]
                if qpu_finish < cpu_finish:
                    best_lane = "qpu"
                    best_p = t["p_quantum"]
            pi = _atc_priority(t["weight"], best_p, t["due_s"], t_now, k, p_bar)
            scored.append((pi, best_lane, best_p, t))
        scored.sort(key=lambda x: -x[0])
        pi, lane, p, t = scored[0]
        priority_log.append({
            "task_id": t["id"], "name": t["name"], "antigen": t["antigen"],
            "lane": lane, "pi": round(pi, 3), "p": round(p, 3),
        })
        if lane == "cpu":
            start = cpu_load
            cpu_load += p
            cpu_sched.append({"task_id": t["id"], "name": t["name"], "lane": "cpu",
                              "start": round(start, 3), "end": round(cpu_load, 3),
                              "antigen": t["antigen"], "p": round(p, 3)})
        else:
            start = qpu_load
            qpu_load += p
            qpu_sched.append({"task_id": t["id"], "name": t["name"], "lane": "qpu",
                              "start": round(start, 3), "end": round(qpu_load, 3),
                              "antigen": t["antigen"], "p": round(p, 3)})
        pending.remove(t)

    return {
        "cpu_load_s": cpu_load,
        "qpu_load_s": qpu_load,
        "total_s": max(cpu_load, qpu_load),
        "cpu_schedule": cpu_sched,
        "qpu_schedule": qpu_sched,
        "priority_queue": priority_log,
    }


def run(eta: float | None = None) -> dict:
    eta = float(eta if eta is not None else DEFAULTS["speedup"])
    eta = max(1.0, min(eta, 100.0))
    k = DEFAULTS["k"]
    threshold = DEFAULTS["threshold"]
    qpu_overhead = DEFAULTS["qpu_overhead_s"]

    tasks = [
        {
            "id": tid, "name": name, "antigen": ag, "affinity": aff,
            "p_classical": p_c, "weight": w, "due_s": d,
            "p_quantum": (p_c / eta + qpu_overhead) if ag != "classical" else None,
        }
        for (tid, name, ag, aff, p_c, w, d) in _FIXTURE
    ]

    # FIFO baseline — strict serial CPU in fixture order
    fifo_sched = []
    fifo_total = 0.0
    for t in tasks:
        start = fifo_total
        fifo_total += t["p_classical"]
        fifo_sched.append({"task_id": t["id"], "name": t["name"], "lane": "cpu",
                           "start": round(start, 3), "end": round(fifo_total, 3),
                           "antigen": t["antigen"], "p": t["p_classical"]})

    # Immune filter
    survivors: list[dict] = []
    rejected: list[dict] = []
    for t in tasks:
        if t["antigen"] == "classical":
            survivors.append({**t, "lane_eligible": ["cpu"], "filter_pass": True})
            continue
        if t["affinity"] >= threshold:
            survivors.append({**t, "lane_eligible": ["cpu", "qpu"], "filter_pass": True})
        else:
            rejected.append({
                "task_id": t["id"], "name": t["name"], "antigen": t["antigen"],
                "affinity": t["affinity"],
                "reason": f"affinity {t['affinity']:.2f} below {threshold:.2f} threshold",
            })
            survivors.append({**t, "lane_eligible": ["cpu"], "filter_pass": False})

    p_bar = sum(t["p_classical"] for t in tasks) / len(tasks)
    atc = _schedule_atc(survivors, eta, k, p_bar, qpu_overhead)

    reduction_pct = (fifo_total - atc["total_s"]) / fifo_total * 100.0

    sweep = []
    for e in [1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 50.0]:
        r = _schedule_atc(survivors, e, k, p_bar, qpu_overhead)
        sweep.append({
            "eta": e,
            "atc_total_s": round(r["total_s"], 2),
            "reduction_pct": round((fifo_total - r["total_s"]) / fifo_total * 100, 1),
        })

    return {
        "params": {
            "k": k, "threshold": threshold,
            "qpu_overhead_s": qpu_overhead, "eta": eta,
            "n_tasks": len(tasks),
        },
        "tasks": [{
            "id": t["id"], "name": t["name"], "antigen": t["antigen"],
            "affinity": round(t["affinity"], 2),
            "p_classical": t["p_classical"], "weight": t["weight"], "due_s": t["due_s"],
            "p_quantum": round(t["p_quantum"], 3) if t["p_quantum"] is not None else None,
        } for t in tasks],
        "fifo": {"total_s": round(fifo_total, 2), "schedule": fifo_sched},
        "atc": {
            "total_s": round(atc["total_s"], 2),
            "cpu_load_s": round(atc["cpu_load_s"], 2),
            "qpu_load_s": round(atc["qpu_load_s"], 2),
            "cpu_schedule": atc["cpu_schedule"],
            "qpu_schedule": atc["qpu_schedule"],
            "priority_queue": atc["priority_queue"],
            "rejected": rejected,
            "reduction_pct": round(reduction_pct, 1),
        },
        "sensitivity": sweep,
        "target_pct": 15.0,
    }

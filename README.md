# Quantum Routing Brain

A demo MVP for the **Vanderbilt Dry Dock 2026 Build Week, Xtremis AI Challenge 2**.

A containerized orchestration layer that decides, in real time, which compute tasks in a tactical defense workflow get offloaded to a quantum backend versus run classically. Built on top of the [sponsor starter](https://github.com/btedman-xtremis/xtremis-drydock) (`challenge-2-quantum/`), preserving its service architecture and `task_profile.csv` schema so judges' eval still works, while adding an LLM translation layer, a real-time animated UI, and two QAOA templates beyond the starter's MaxCut.

---

## What it does

A user enters a natural-language compute task (e.g. *"Find the optimal route for 4 drones across 4 targets"*) and the system:

1. Classifies the task and extracts parameters into a row matching the sponsor's task profile schema
2. Builds a parameterized QAOA circuit from a pre-validated template
3. Verifies the circuit (gate validity, qubit count, depth, simulator sanity check, cost-benefit vs classical)
4. Runs the sponsor's **5-gate decision engine** (Annex B): problem class → classification level → latency budget → instance size → backend availability
5. Executes the chosen backend AND a classical baseline in parallel
6. Streams every step to the UI as Server-Sent Events for live animation

Three demo scenarios are wired:

- **VRP** ("4 drones, 4 targets") — routes quantum, classical OR-tools wins on this small instance (the honest framing per Annex B)
- **Frequency assignment** (5-cell graph coloring) — routes quantum, both find a valid 3-coloring
- **SECRET task** — routes classical, hard-blocked at gate 2 (no commercial QPU at IL6)

---

## Architecture

```
┌──────────────┐    ┌──────────────────────┐    ┌────────────────────┐
│  web (3000)  │───▶│  gateway (8003)      │───▶│  router (8000)     │
│  Next.js 15  │SSE │  Gemini LLM          │    │  5-gate decision   │
│  React 19    │◀───│  verifier            │    │  audit log         │
└──────────────┘    │  CoT envelope        │    └─────────┬──────────┘
                    └──────────────────────┘              │
                                                ┌─────────┴─────────┐
                                                ▼                   ▼
                                  ┌──────────────────┐ ┌──────────────────┐
                                  │ classical (8001) │ │ quantum (8002)   │
                                  │ brute MaxCut     │ │ QAOA + Aer       │
                                  │ OR-tools VRP     │ │ COBYLA optimizer │
                                  │ DSATUR coloring  │ │ MaxCut/VRP/Freq  │
                                  └──────────────────┘ └──────────────────┘
```

| Layer | Origin | Notes |
|---|---|---|
| `backend/docs/`, `backend/data/`, `backend/examples/` | sponsor | read-only |
| `backend/src/router/` | sponsor, lightly extended | added `payload` field forwarding |
| `backend/src/classical_backend/` | sponsor scaffold + our solvers | OR-tools VRP, networkx DSATUR coloring |
| `backend/src/quantum_backend/` | sponsor scaffold + our templates | VRP-QAOA, freq-coloring QAOA, COBYLA-tuned MaxCut |
| `backend/src/gateway/` | ours | LLM (Gemini, canned fallback), verifier, SSE, Cursor-on-Target XML |
| `web/` | ours | Next.js 15 + R3F + Framer Motion; brass/walnut warm palette |

---

## The 5 routing gates (Annex B)

A task is offloaded to quantum **only when all five gates pass**:

1. **Problem class** — `quantum_candidate ∈ {Y, maybe}` from the task profile CSV
2. **Classification level** — `UNCLASS` or `CUI` only; SECRET / TS-SCI is a hard block (no commercial QPU at IL6)
3. **Latency budget** — `latency_budget_ms > estimated round-trip time`
4. **Instance size** — within current QPU's feasible window (≤25 qubits gate-model)
5. **Backend availability** — live `/health` ping; auto-fallback to classical on failure

The classical baseline runs in parallel regardless. Both results are returned with full audit trail, in the spirit of "the orchestration layer's value is managing this transition intelligently, not pretending quantum is ready for everything."

---

## Run locally

Requires Python 3.11+ and Node.js 20+. (Docker Compose unification pending.)

```bash
# Backend (4 services)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install ortools networkx google-genai sse-starlette httpx scipy

export CLASSICAL_BACKEND_URL=http://localhost:8001
export QUANTUM_BACKEND_URL=http://localhost:8002
export ROUTER_URL=http://localhost:8000
# optional: export GEMINI_API_KEY=...   (canned mappings used if missing)

(cd src/classical_backend && python main.py &)
(cd src/quantum_backend && python main.py &)
(cd src/router && python main.py &)
(cd src && python -m uvicorn gateway.api:app --host 0.0.0.0 --port 8003 &)

# Web UI
cd ../web
npm install
npm run dev
```

Open http://localhost:3000.

Health checks:
```bash
for p in 8000 8001 8002 8003; do curl -s http://localhost:$p/health; echo; done
```

---

## Tech stack

**Backend:** Python 3.12, Qiskit 1.3 + Aer 0.15 (QAOA), FastAPI 0.136, Pydantic v2, OR-tools, scipy, networkx, google-genai (Gemini), sse-starlette.

**Frontend:** Next.js 15 (App Router) + React 19, Tailwind CSS v4, Framer Motion, react-three-fiber + drei, Fraunces (serif) + JetBrains Mono (mono).

**Inherited from sponsor:** the three-service Docker architecture, the 17-column `task_profile.csv` schema, the MaxCut QAOA reference, the Dockerfiles, and `docker-compose.yml`.

---

## Out of scope (deliberately)

- Real QPU hardware (Aer simulator only; IBM Open Plan stretch)
- Kubernetes (Docker Compose only, per Annex E recommendation)
- LLM generating raw circuit code (LLM produces task profile rows; templates build circuits — reliability decision for live demo)
- Production auth / multi-tenancy / closed-loop learning

---

## Sponsor

Vanderbilt Dry Dock 2026 Build Week, Xtremis AI Challenge 2.
Point of contact: B. Thomas Edman — `btedman@xtremis.ai`.
Starter repo: https://github.com/btedman-xtremis/xtremis-drydock

The annexes A–F (in `backend/docs/`) are the operative specs; this implementation conforms to them. See in particular Annex A (task profile schema), Annex B (5-gate decision rubric), Annex F (evaluation rubric: 35% tech / 25% venture / 15% present / 15% eng / 10% team).

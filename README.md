# Helios

> The correctness layer for scientific code.
> AUDIT silent bugs → FIX with a verified rewrite → ROUTE to the right hardware.

Scientific Python — written by domain scientists, not software engineers — is full of silent bugs: off-by-one in numerical integration, unit mismatches, subtractive cancellation, broken boundary conditions. They don't crash. They produce results that look right and are wrong. Helios ingests a researcher's file, flags the silent bugs, generates a fix that is **verified** against synthesized test inputs, and routes hot loops to the hardware that should run them.

## Repo layout

```
.
├── backend/    FastAPI service: audit / fix / verify / route / live / demo
├── web/        Next.js 14 reviewer app (App Router, static export)
└── Dockerfile  Single-service build that bundles backend + exported frontend
```

## Status

| Component | State |
|---|---|
| Backend API | implemented, tests pass |
| Sandboxed verification | implemented (Linux supported, macOS best-effort) |
| Gemini integration | implemented (`google-genai` SDK) |
| Frontend reviewer UI | implemented (`/`, `/session`, `/sessions`) |
| Guided demo (`/app/demo`) | implemented — six-act Monte Carlo 2D-electron-gas walkthrough |
| Live coding (`/app/live`) | implemented — stateless SSE audit with caching, dedup, rate limit |
| GPU routing | implemented — pattern-based candidate detection |
| Quantum routing | implemented as scheduling demo (immune filter + ATC, tunable speedup) |
| Deploy | single Railway service serving `/api/*`, `/`, and `/app/*` |

## Features

**AUDIT** — static checks (`ast` / `libcst`) plus an LLM pass (Gemini) over the source. Static catches off-by-one, mutable defaults, float equality, bare except, mixed division. The LLM pass goes after the silent scientific bugs: numerical instability, unit mismatch, boundary conditions, shape assumptions.

**FIX** — for each accepted issue, regenerate the file applying only that fix. Returns full new source plus a one-line diff summary.

**VERIFY** — synthesizes test inputs (random within type-inferred bounds, edge cases, large-N stress), runs original and fix in two sandboxed subprocesses with `RLIMIT_*` and a wall-clock cap, compares outputs with `numpy.allclose` tolerance and exception-class equality, returns per-test verdict + overall pass/fail.

**ROUTE (GPU)** — pattern-matches nested numeric loops, large matmuls, FFTs, elementwise ufuncs in pure-Python loops, Monte Carlo blocks. Each candidate gets an estimated speedup band, complexity rating, and one-line rationale.

**ROUTE (Quantum)** — scheduling demo: a 47-task workload runs through an immune filter (drops low-affinity antigens) then an ATC dispatcher (Vepsalainen & Morton 1987) over CPU + QPU lanes. Tuned so default eta=5× beats FIFO by ~28%; slider re-runs with different speedups to expose sensitivity.

**LIVE** — stateless interactive audit endpoints (`/api/live/audit/static`, `/audit/stream` SSE, `/fix/preview`, `/stats`). No DB writes; per-token rate limit, in-flight dedup so duplicate keystrokes share one LLM call, response cache.

## Quickstart (backend)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # set GEMINI_API_KEY
uvicorn helios.main:app --reload
```

```bash
curl localhost:8000/health
# {"ok": true}
```

Or with Postgres:

```bash
cd backend
export GEMINI_API_KEY=...
docker compose up --build
```

## Quickstart (frontend)

```bash
cd web
npm install
npm run dev   # localhost:3000 → calls backend at localhost:8000
```

For a production-style build (what Railway serves):

```bash
cd web
npm run build   # static export to web/out/
```

The backend's FastAPI app mounts `web/out/` at `/app` and the marketing page at `/`, so a single deployed service serves both.

## Tests

```bash
cd backend && pytest
```

## End-to-end demo

The slide-5 pitch (`backend/tests/fixtures/integrate_off_by_one.py`):

1. AUDIT flags `range(1, n - 1)` as off-by-one
2. FIX rewrites to `range(0, n - 1)`, returns clean diff
3. VERIFY synthesizes 12 test inputs, runs both versions in sandboxed subprocesses, reports pass/fail
4. ROUTE flags the inner loop as a GPU candidate

The longer guided walkthrough lives at `/app/demo` (six acts: hook → audit → trace → refactor → verify → route), built around a 2D-electron-gas Monte Carlo simulator.

## API contract

See `backend/helios/schemas.py` (Pydantic) — frontend mirrors these in `web/lib/types.ts`. Endpoints documented in `backend/README.md`.

## Tech

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLModel, Postgres (SQLite in dev), Gemini via `google-genai`, sandboxed subprocess execution with `RLIMIT_*`
- **Frontend:** Next.js 14 App Router (static export, `basePath="/app"`), TypeScript, Monaco editor, custom diff renderer, canvas-based reveal animations

## Deploy

The repo's top-level `Dockerfile` builds the Next.js app, copies the static export into the backend image, and runs `uvicorn`. One Railway service hosts everything; CORS is same-origin in production. To run the frontend on a separate origin (e.g. Vercel), broaden `allow_origins` in `backend/helios/main.py` (currently hard-coded to `localhost:3000`).

## Out of scope (MVP)

Languages other than Python, multi-file projects, real on-hardware quantum execution (the quantum demo is a scheduling/routing visualization, not a QPU dispatcher), auth/billing, GitHub PR integration, formal verification.

## License

TBD.

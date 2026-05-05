 # Helios

> The correctness layer for scientific code.
> AUDIT silent bugs → FIX with a verified rewrite → ROUTE to the right hardware.

Scientific Python — written by domain scientists, not software engineers — is full of silent bugs: off-by-one in numerical integration, unit mismatches, subtractive cancellation, broken boundary conditions. They don't crash. They produce results that look right and are wrong. Helios ingests a researcher's file, flags the silent bugs, generates a fix that is **verified** against synthesized test inputs, and flags hot loops that would benefit from GPU acceleration.

## Repo layout

```
.
├── backend/    FastAPI service (audit / fix / verify / route / live / demo)
├── web/        Next.js 14 reviewer app (App Router, static export)
└── Dockerfile  Single-service build: backend + exported frontend
```

## Status

| Component | State |
|---|---|
| Backend API | implemented, tests pass |
| Sandboxed verification | implemented (Linux supported, macOS best-effort) |
| Gemini integration | implemented (`google-genai` SDK) |
| Frontend reviewer UI | implemented |
| Guided demo (`/app/demo`) | implemented — Monte Carlo 2D-electron-gas walkthrough |
| Live coding (`/app/live`) | implemented — interactive coding session with audit-on-save |
| Deploy | single Railway service serving `/api/*` + static `/app/*` |

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

## End-to-end demo (the slide-5 pitch)

1. Drop `backend/tests/fixtures/integrate_off_by_one.py` into Helios
2. AUDIT flags `range(1, n - 1)` as off-by-one
3. FIX rewrites to `range(0, n - 1)`, returns clean diff
4. VERIFY synthesizes 12 test inputs, runs both versions in sandboxed subprocesses, reports pass/fail
5. ROUTE flags the inner loop as a GPU candidate

The longer guided walkthrough lives at `/app/demo` (six acts: hook → audit → trace → refactor → verify → route), built around a real 2D-electron-gas Monte Carlo simulator.

## API contract

See `backend/helios/schemas.py` (Pydantic) — frontend mirrors these in `web/lib/types.ts`. Endpoints documented in `backend/README.md`.

## Tech

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLModel, Postgres (SQLite in dev), Gemini via `google-genai`, sandboxed subprocess execution with `RLIMIT_*`
- **Frontend:** Next.js 14 App Router (static export, `basePath="/app"`), TypeScript, Monaco, custom diff renderer

## Deploy

The repo's top-level `Dockerfile` builds the Next.js app, copies the export into the backend image, and runs `uvicorn`. One Railway service hosts everything; CORS is same-origin in production. To run the frontend on a separate origin (e.g. Vercel), broaden `allow_origins` in `backend/helios/main.py`.

## Out of scope (MVP)

Languages other than Python, multi-file projects, real quantum routing, auth/billing, GitHub PR integration, formal verification.

## License

TBD.

# Helios

> The correctness layer for scientific code.
> AUDIT silent bugs → FIX with a verified rewrite → ROUTE to the right hardware.

Scientific Python — written by domain scientists, not software engineers — is full of silent bugs: off-by-one in numerical integration, unit mismatches, subtractive cancellation, broken boundary conditions. They don't crash. They produce results that look right and are wrong. Helios ingests a researcher's file, flags the silent bugs, generates a fix that is **verified** against synthesized test inputs, and flags hot loops that would benefit from GPU acceleration.

## Repo layout

```
.
├── backend/    FastAPI service (audit / fix / verify / route)
└── web/        Next.js 14 frontend (scaffold only — not implemented yet)
```

## Status

| Component | State |
|---|---|
| Backend API | implemented, tests pass |
| Sandboxed verification | implemented (Linux supported, macOS best-effort) |
| Gemini integration | implemented (`google-genai` SDK) |
| Frontend | files scaffolded, no implementation |

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

## API contract

See `backend/helios/schemas.py` (Pydantic) — frontend should mirror these in `web/lib/types.ts`. Endpoints documented in `backend/README.md`.

## Tech

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLModel, Postgres (SQLite in dev), Gemini via `google-genai`, sandboxed subprocess execution with `RLIMIT_*`
- **Frontend (planned):** Next.js 14 App Router, TypeScript, Tailwind, shadcn/ui, Monaco, react-diff-viewer-continued, TanStack Query, Zustand

## Out of scope (MVP)

Languages other than Python, multi-file projects, real quantum routing, auth/billing, GitHub PR integration, formal verification.

## License

TBD.

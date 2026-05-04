# Helios Backend

FastAPI service: ingest Python source → AUDIT silent bugs → FIX with verified rewrite → ROUTE to GPU candidates.

## Quickstart (local, SQLite)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # then edit GEMINI_API_KEY
uvicorn helios.main:app --reload
```

`curl localhost:8000/health` → `{"ok": true}`.

## Quickstart (docker, Postgres)

```bash
export GEMINI_API_KEY=...
docker compose up --build
```

## Tests

```bash
pytest
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/sessions` | create session from source |
| GET  | `/sessions` | list sessions |
| GET  | `/sessions/{id}` | get session |
| POST | `/sessions/{id}/audit` | run static + LLM audit |
| GET  | `/sessions/{id}/issues` | list issues |
| POST | `/sessions/{id}/issues/{issue_id}/fix` | generate fix |
| GET  | `/sessions/{id}/fixes/{fix_id}` | get fix |
| POST | `/sessions/{id}/fixes/{fix_id}/verify` | run verification |
| GET  | `/sessions/{id}/verifications/{verification_id}` | get verification |
| POST | `/sessions/{id}/route` | classify GPU candidates |
| GET  | `/health` | health |

## Threat model (sandbox)

User code is run in a child Python process with `RLIMIT_AS`, `RLIMIT_CPU`,
`RLIMIT_NOFILE`, a wall-clock timeout, and stdout/stderr size caps. We do
**not** run inside a network namespace or container — production deployment
must wrap this in gVisor / firecracker / `sandbox-exec` / a network-isolated
container. macOS does not honor `RLIMIT_AS` reliably; Linux is the supported
target. We never `eval` user code in the API process.

## Layout

```
helios/
  api/          FastAPI routers
  analysis/     static + LLM audit, fix gen, test synth, route classifier
  execution/    sandbox runner, numerical comparator
  prompts/      versioned LLM prompt templates
  models.py     SQLModel tables
  schemas.py    Pydantic API contract types
  main.py       app factory
```

## LLM

Gemini (`google-generativeai`). Models configurable via env. Default:
- audit + fix: `gemini-2.5-pro`
- route classification: `gemini-2.5-flash`

Prompts are plain text in `helios/prompts/` with version suffixes
(`audit.v1.txt`). Bumping a prompt = code review.

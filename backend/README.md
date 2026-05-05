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

### Live (interactive) audit

Stateless endpoints meant for an editor — no DB writes, ephemeral per-token cache.
Token is supplied via `X-Session-Token` header or `session_token` body field.

| Method | Path | Purpose |
|---|---|---|
| POST | `/live/audit/static` | AST-only audit, sub-100ms, no LLM cost |
| POST | `/live/audit/stream` | SSE stream: static event first, then LLM events |
| POST | `/live/fix/preview`  | stateless fix gen for an ephemeral finding |
| GET  | `/live/stats`        | telemetry counters |

SSE event types from `/live/audit/stream`:
- `hello` — connection acknowledged
- `static` — array of AST findings (immediate)
- `cache_hit` — whole-file hash matched, no LLM call
- `llm_partial` — findings for a subset of functions (per-function audit)
- `llm` — consolidated LLM findings
- `merged` — `merge_dedupe(static, llm)`, sorted by severity
- `done` — stream complete
- `error` — `cancelled` / `client_disconnect`

Live mode uses `gemini-2.5-flash` by default and an AST-hash cache so only
edited functions get re-audited. A new stream request with the same token
cancels any prior in-flight stream. Per-token rate limit (default 30 burst,
1/s refill, configurable via `LIVE_RATE_*` env vars).

## Agent integrations

Helios is **deliberately scoped to scientific / numerical Python** (numpy,
scipy, torch, jax, pandas, sympy, qiskit, etc.). The detector
(`helios/detector/scientific.py`) runs first and attaches a clear warning
when invoked on web handlers, ORM models, or general business logic —
findings on those files would be low-signal and we'd rather decline visibly
than spam the user.

### Pattern A — direct agent integration

A coding agent (Claude Code, Cursor, Aider, etc.) calls Helios after
generating code, via either the Python client, the CLI, or the
function-calling tool schemas.

```python
from helios.agent import HeliosClient, review_code

cl = HeliosClient(base_url="http://localhost:8000")
review = review_code(generated_source, deep=False, client=cl)
print(review.to_agent_text())   # paste into the agent's context
```

CLI:

```bash
# fast static review (default — sub-100ms, no LLM cost)
helios-review path/to/file.py

# full audit (static + Gemini Flash)
helios-review --deep path/to/file.py

# stdin + JSON output for an agent's tool runtime
cat generated.py | helios-review --json -
```

Exit codes: `0` clean, `1` high/critical findings, `2` bad args, `3` HTTP/server error.

Function-calling tool schemas (register with the agent SDK):

```python
from helios.agent import ANTHROPIC_TOOLS, OPENAI_TOOLS
# ANTHROPIC_TOOLS  -> Anthropic Messages API tool list
# OPENAI_TOOLS     -> OpenAI / Gemini function-calling shape
```

### Pattern C — MCP server

Run Helios as a Model Context Protocol server. Any MCP-aware client
(Claude Code, Cursor, Cline) discovers the tools automatically.

```bash
helios-mcp                                  # stdio transport
HELIOS_API_URL=http://localhost:8000 helios-mcp
```

Example `~/.config/claude-code/mcp.json` entry:

```json
{
  "mcpServers": {
    "helios": {
      "command": "helios-mcp",
      "env": {
        "HELIOS_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

Tools exposed:

| Tool | Purpose |
|---|---|
| `helios_detect_scientific` | classify code before deciding to call other tools |
| `helios_audit`             | static + (optional) LLM audit |
| `helios_fix_preview`       | stateless fix gen for one finding |
| `helios_session_create`    | persist source to a Helios session |
| `helios_session_audit`     | full audit with stable Issue ids |
| `helios_session_fix`       | persist a fix |
| `helios_session_verify`    | sandboxed numerical verification |
| `helios_session_route`     | flag GPU candidates |

Every tool description explicitly tells the agent the scope is scientific
Python. The detector still runs server-side, and a `warning` field is
attached to the response when the input doesn't look numerical.

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

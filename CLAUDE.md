# Helios — Build Prompt

> The correctness layer for scientific code. AUDIT silent bugs → FIX with a verified rewrite → ROUTE to the right hardware.

This document is a build spec for an MVP. It is split into:

1. **Shared context** — what Helios is, who uses it, what the MVP must do
2. **Backend prompt** — the analysis engine + API
3. **Frontend promp
t** — the review UI
4. **Shared API contract** — the seam between them, so both halves integrate without rework

Paste section 2 into one coding agent session, section 3 into another, and keep section 4 in front of both.

---

## 1. Shared Context (read before either half)

### Product in one paragraph
Scientific code — the Python/Fortran/C++ that designs drugs, predicts climate, models batteries — is mostly written by domain scientists, not software engineers. It contains silent bugs: off-by-one loops, unit mismatches, numerical instabilities, broken integrations. The bugs don't crash; they produce results that *look right and are wrong*. Helios is a tool that ingests a researcher's code, **flags the silent bugs**, **rewrites the code with a verified fix** (proven correct against test cases), and **flags when special hardware** (GPU, eventually quantum) would meaningfully accelerate the workload. Researchers see a clean before/after diff, a test-case verification report, and click "Accept."

### Three user-visible features (build all three; they are the product)
1. **AUDIT** — Static + LLM analysis of a code file. Output a list of issues, each with: location (file, line), severity, category (off-by-one, unit mismatch, numerical instability, dead code, etc.), short explanation in plain English.
2. **FIX** — For each accepted issue, generate a corrected version. Run the original and the fix on a generated set of test inputs. Compare outputs within a numerical tolerance. Surface a per-test-case pass/fail and an overall verification verdict.
3. **ROUTE** — A pattern-matching pass over the (fixed) code that flags hot loops / array operations / linear-algebra blocks as candidates for GPU acceleration, with a rough cost-benefit (estimated speedup × estimated cost). Quantum routing is **out of scope for the MVP** — leave a stub.

### MVP scope
- **Languages supported:** Python only. Single file at a time.
- **No multi-tenancy / billing.** Single user, local-ish deployment, but designed cleanly enough to scale.
- **Verification = numerical comparison.** No formal proofs. Use `numpy.allclose`-style tolerance, plus exception-equivalence checks.
- **Sandboxed execution required.** Running unknown user code in-process is unacceptable. Use a subprocess with resource limits + a non-network execution context.
- **Persist every session.** Every `(original_code, fixed_code, test_cases, verification_result)` tuple is logged to the database. This dataset is the company's moat — treat it like product, not telemetry.

### Tech choices (use these unless you have a strong reason otherwise)
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLModel + Postgres (SQLite in dev), Celery or simple in-process job queue, `ast` + `libcst` for static analysis, `subprocess` + `resource` for sandboxing, Anthropic API (`claude-opus-4-7` for analysis, `claude-sonnet-4-6` for routing classification).
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind, shadcn/ui, Monaco Editor for code, `react-diff-viewer-continued` for diffs, TanStack Query for data, Zustand for client state.
- **Both halves talk over JSON HTTP.** No tRPC, no GraphQL — keep the seam dumb so either side can be rewritten.

---

## 2. Backend Prompt

You are building **the Helios backend**: a FastAPI service that ingests Python source files, runs a multi-stage analysis pipeline, and exposes a JSON API for the frontend.

### Repository layout
```
helios-backend/
├── pyproject.toml
├── README.md
├── docker-compose.yml          # postgres + api
├── alembic/                     # db migrations
├── helios/
│   ├── main.py                  # FastAPI app + router registration
│   ├── config.py                # pydantic-settings, env-driven
│   ├── db.py                    # SQLModel engine + session
│   ├── models.py                # Session, Issue, Fix, TestCase, Verification, RouteSuggestion
│   ├── api/
│   │   ├── sessions.py          # POST /sessions, GET /sessions/{id}, GET /sessions
│   │   ├── audit.py             # POST /sessions/{id}/audit
│   │   ├── fix.py               # POST /sessions/{id}/issues/{issue_id}/fix
│   │   ├── verify.py            # POST /sessions/{id}/fixes/{fix_id}/verify
│   │   └── route.py             # POST /sessions/{id}/route
│   ├── analysis/
│   │   ├── static.py            # AST checks: off-by-one, dead code, mutable defaults, etc.
│   │   ├── llm_audit.py         # Claude prompt for "find silent scientific-code bugs"
│   │   ├── fix_generator.py     # Claude prompt for "rewrite with the fix applied"
│   │   ├── test_synthesizer.py  # generate input cases for a function (random + edge)
│   │   └── route_classifier.py  # pattern-match GPU-suitable blocks
│   ├── execution/
│   │   ├── sandbox.py           # subprocess runner with rlimit + timeout
│   │   └── compare.py           # numerical comparison of outputs
│   └── prompts/                 # plain-text prompt templates, version-tagged
└── tests/
```

### Key behaviors (build each)

**1. AUDIT pipeline (`POST /sessions/{id}/audit`)**
- Runs static checks first (`analysis/static.py`). Cheap, deterministic, runs locally. Catch:
  - `range(1, N)` over indexable arrays where `arr[0]` is unused (off-by-one suspect)
  - Mutable default args
  - Mixed integer / float division where it looks intentional but isn't
  - Bare `except:` clauses
  - `==` comparisons between floats
- Then runs LLM audit (`analysis/llm_audit.py`). Send the file to Claude with a prompt focused on **scientific** silent bugs: unit inconsistency, numerical instability (subtractive cancellation, summation order), off-by-one in numerical integration / discretization, mis-applied boundary conditions, wrong array shape assumptions.
- Merges + dedupes findings. Returns a list of `Issue` objects (see contract).

**2. FIX generation (`POST /sessions/{id}/issues/{issue_id}/fix`)**
- Sends original code + the specific issue to Claude with a "rewrite this file applying ONLY this fix" prompt.
- Stores the proposed fix. Returns it. Does **not** auto-verify (verification is a separate, more expensive step).

**3. VERIFY (`POST /sessions/{id}/fixes/{fix_id}/verify`)**
- Identifies the function(s) touched by the fix (AST diff).
- Calls `test_synthesizer` to produce N test inputs (default 12) — mix of: random within type-inferred bounds, zero / empty / one-element edge cases, large-N stress cases.
- Spawns two sandboxed subprocesses: one runs the original function on each input, one runs the fix. Each run has a wall-clock timeout (default 5s) and memory cap.
- Compares outputs with `numpy.allclose(rtol=1e-9, atol=1e-12)` for arrays, exact for ints/strings, exception-class equality for raised exceptions.
- Returns per-test-case verdict + overall pass/fail.

**4. ROUTE (`POST /sessions/{id}/route`)**
- Runs over the (fixed, if accepted, else original) code.
- Pattern-matches: nested loops over numeric arrays, large matrix multiplications, FFTs, element-wise ufuncs in pure-python loops, Monte Carlo blocks.
- For each candidate, asks Claude to estimate: rough speedup on GPU (order of magnitude), engineering complexity, and a one-line cost-benefit summary.
- Quantum: stub out — return `quantum_candidate: false` for everything in MVP.

### Sandboxing — non-negotiable details
- Use `subprocess.run` with `preexec_fn` setting `resource.RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_NOFILE`. Linux only is fine; document it.
- Block network: run inside a network namespace OR set env vars and trust them in dev, but document the threat model honestly in `README.md`.
- Never `exec` user code in the API process. Ever.
- Stdout/stderr from the sandbox must be size-capped (e.g., 1 MB) before being read back, to avoid OOMing the API.

### LLM usage rules
- All prompts live as `.txt` files under `helios/prompts/`, with a version suffix (`audit.v1.txt`). Code references them by filename. This makes prompt iteration a code review.
- Token budgets: audit ≤ 8k input, fix ≤ 12k input. Reject files larger than 4000 lines with a clear error.
- Stream responses where the frontend will benefit (audit, fix). The endpoints can support both streaming (`text/event-stream`) and buffered JSON — start with buffered, add streaming once frontend is wired.

### Acceptance criteria for the backend
- `docker-compose up` brings up postgres + api. `curl localhost:8000/health` returns `{"ok": true}`.
- A test fixture (`tests/fixtures/integrate_off_by_one.py` — the slide 5 example) produces:
  - At least one `off_by_one` issue from AUDIT
  - A FIX that changes `range(1, N)` to `range(0, N)`
  - A VERIFY result with all test cases passing and the analytical-integral test included
- Every API mutation is recorded in the `sessions` table with full input/output. Re-running the same audit on the same file returns a deterministic-ish set of static issues (LLM issues may vary).

---

## 3. Frontend Prompt

You are building **the Helios frontend**: a Next.js app that lets a researcher upload a Python file, walks them through the AUDIT → FIX → VERIFY → ROUTE flow, and shows a clear before/after with verification proof.

### Repository layout
```
helios-frontend/
├── package.json
├── next.config.js
├── tailwind.config.ts
├── app/
│   ├── layout.tsx
│   ├── page.tsx                    # landing: upload or paste code
│   ├── sessions/
│   │   ├── page.tsx                # list of past sessions
│   │   └── [id]/
│   │       ├── page.tsx            # session view: tabs for Audit / Fix / Verify / Route
│   │       ├── audit/page.tsx
│   │       ├── fix/[issueId]/page.tsx
│   │       └── route/page.tsx
├── components/
│   ├── CodeEditor.tsx              # Monaco wrapper, read-only by default
│   ├── DiffView.tsx                # side-by-side, with accept/reject controls
│   ├── IssueList.tsx               # severity-sorted, expandable rows
│   ├── VerificationPanel.tsx       # per-test-case pass/fail with input preview
│   ├── RoutePanel.tsx              # GPU candidates with speedup/cost
│   └── ui/                          # shadcn-generated primitives
├── lib/
│   ├── api.ts                      # typed fetch wrappers, one per endpoint
│   ├── types.ts                    # shared types — KEEP IN SYNC WITH BACKEND CONTRACT
│   └── query-client.ts
└── styles/globals.css
```

### Pages and what they do

**Landing (`/`)**
- One big code-input area: drag-drop a `.py` file OR paste code OR (stretch) connect a GitHub repo and pick a file.
- One primary button: **Audit this code**. POSTs to `/sessions`, then redirects to `/sessions/{id}/audit`.

**Audit view (`/sessions/{id}/audit`)**
- Left pane: read-only Monaco showing the original file, with line-number gutter highlights at issue locations.
- Right pane: `IssueList`. Each issue is a card: severity badge, category, plain-English explanation, a "Generate Fix" button.
- Empty state ("no issues found") should be celebratory but not smug — researchers will see this often and shouldn't feel stupid for asking.

**Fix view (`/sessions/{id}/fix/{issueId}`)**
- `DiffView` showing original vs proposed fix, side-by-side, with the changed function expanded and surrounding code collapsible.
- Three buttons: **Verify**, **Accept without verifying** (greyed out by default — require an explicit toggle), **Reject**.
- Verify kicks off the verification job. Show a streaming progress UI: "Generating 12 test cases…", "Running original…", "Running fix…", "Comparing…" — each step ticks green when complete.
- When verification finishes, slide in `VerificationPanel`: a table of inputs (truncated previews — these can be big arrays), original output, fix output, agreement verdict, time. Plus an overall verdict banner: green ("All 12 cases agree") or red ("3/12 cases disagree — investigate").

**Route view (`/sessions/{id}/route`)**
- A list of GPU candidate blocks. Each: code excerpt, estimated speedup ("~50–200×"), engineering complexity ("low / med / high"), one-line rationale.
- Quantum section: greyed-out card with "Coming when quantum is ready" copy. Don't hide it — it's part of the pitch.

**Sessions list (`/sessions`)**
- Table: filename, date, # issues found, # fixes accepted, # verified. Click row → session view.

### Design notes
- **Tone:** confident, technical, not cute. Researchers are the audience. Avoid "Oops!" / "Magic!" copy.
- **Color:** primary is a deep amber/sun (helios = sun) — `#E8A33D` or similar — used sparingly for CTAs and accept-state confirmations. Default UI is high-contrast neutral (near-black on near-white). Errors are a desaturated red, not crimson.
- **Code typography:** JetBrains Mono or IBM Plex Mono. 14px default in editors, 13px in diff views.
- **Diff colors:** muted — `#E6F4EA` / `#FCE8E6` backgrounds, not retina-burning green/red.
- **Loading states matter.** Verification can take 10–60 seconds. Show what's happening, not a spinner.
- **Keyboard:** `j`/`k` to move between issues, `Enter` to open fix, `v` to verify, `a` to accept. Document these in a small `?` overlay.

### Acceptance criteria for the frontend
- Uploading the slide 5 example file produces a working end-to-end demo: audit shows the off-by-one, fix shows the diff, verify shows 12/12 cases passing, route shows the loop as a GPU candidate.
- The UI never blocks on a long backend call without showing progress.
- Every API call is typed against `lib/types.ts`. No `any`, no untyped fetches.
- Works in dark mode. (Researchers work at night.)

---

## 4. Shared API Contract (the seam)

Both halves import these types. Backend defines them in Pydantic; frontend mirrors them in TypeScript. **Keep them in sync.**

```ts
// Session — the top-level container for a single file's analysis lifecycle
type Session = {
  id: string;                    // uuid
  filename: string;
  language: "python";            // mvp constraint
  source_code: string;
  created_at: string;            // iso
  status: "created" | "audited" | "fixing" | "verified" | "routed";
};

// Issue — one finding from the AUDIT step
type IssueSeverity = "low" | "medium" | "high" | "critical";
type IssueCategory =
  | "off_by_one"
  | "unit_mismatch"
  | "numerical_instability"
  | "float_equality"
  | "mutable_default"
  | "bare_except"
  | "shape_assumption"
  | "boundary_condition"
  | "other";

type Issue = {
  id: string;
  session_id: string;
  category: IssueCategory;
  severity: IssueSeverity;
  line_start: number;            // 1-indexed
  line_end: number;
  title: string;                 // <= 80 chars
  explanation: string;           // plain english, 1-3 sentences
  source: "static" | "llm";
};

// Fix — one proposed rewrite for one Issue
type Fix = {
  id: string;
  session_id: string;
  issue_id: string;
  fixed_code: string;            // full file contents after applying ONLY this fix
  diff_summary: string;          // one-line human description of what changed
  created_at: string;
};

// Verification — running original + fix on synthesized test inputs
type TestCaseResult = {
  index: number;
  input_preview: string;         // truncated repr of the input(s), <= 200 chars
  original_output_preview: string;
  fix_output_preview: string;
  agreed: boolean;               // numerically within tolerance?
  original_ms: number;
  fix_ms: number;
  notes: string | null;          // e.g. "both raised ValueError"
};

type Verification = {
  id: string;
  fix_id: string;
  test_cases: TestCaseResult[];
  passed: number;
  failed: number;
  overall_verdict: "all_agree" | "partial_disagree" | "all_disagree" | "error";
  created_at: string;
};

// Routing — hardware acceleration suggestions
type RouteCandidate = {
  line_start: number;
  line_end: number;
  pattern: "nested_numeric_loop" | "matmul" | "fft" | "elementwise_ufunc" | "monte_carlo" | "other";
  estimated_speedup: string;     // e.g. "10-50x", human readable
  complexity: "low" | "medium" | "high";
  rationale: string;             // 1-2 sentences
};

type RouteResult = {
  session_id: string;
  gpu_candidates: RouteCandidate[];
  quantum_candidates: [];        // empty in MVP, always
  created_at: string;
};
```

### Endpoints

```
POST   /sessions                                  body: { filename, source_code }   -> Session
GET    /sessions                                                                   -> Session[]
GET    /sessions/{id}                                                              -> Session

POST   /sessions/{id}/audit                                                        -> Issue[]
GET    /sessions/{id}/issues                                                       -> Issue[]

POST   /sessions/{id}/issues/{issue_id}/fix                                        -> Fix
GET    /sessions/{id}/fixes/{fix_id}                                               -> Fix

POST   /sessions/{id}/fixes/{fix_id}/verify                                        -> Verification
GET    /sessions/{id}/verifications/{verification_id}                              -> Verification

POST   /sessions/{id}/route                                                        -> RouteResult

GET    /health                                                                     -> { ok: boolean }
```

Errors are JSON: `{ "error": { "code": string, "message": string, "details"?: object } }`, with HTTP status reflecting the class (400 client, 422 validation, 500 server, 504 sandbox-timeout).

---

## 5. Out of scope for the MVP (do not build these — note them as TODO)

- Multi-file projects, monorepos, dependency graphs
- Languages other than Python
- Real quantum routing (stub only)
- Auth, billing, multi-tenancy
- GitHub PR integration (the "every paper cites Helios" flywheel) — comes after MVP
- Formal verification / proof assistants — verification = numerical agreement, that's it
- Self-hosting / air-gapped deployment for national labs — comes after we have paying biotech customers

## 6. Definition of done

The MVP is done when a researcher can:
1. Drop the slide 5 `integrate.py` file in
2. See the off-by-one flagged in under 15 seconds
3. Click "Generate fix," see a clean diff
4. Click "Verify," watch 12 test cases run, see them all agree
5. See the inner loop flagged as a GPU candidate
6. Walk away believing the result

That's the whole pitch. Build the thing that produces that 90 seconds.
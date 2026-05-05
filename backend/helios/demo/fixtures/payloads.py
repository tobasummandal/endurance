"""Canned payloads for the hardcoded demo flow.

Line numbers refer to mc_2deg_thermo_init.py in this folder. The seven
issues map to:
  L145-146  catastrophic cancellation in mean/variance (naive sum)
  L77       off-by-one: range(1, steps) skips eq_hist[0]
  L64       mutable default arg history=[]
  L92       hardcoded factor 2.4 inside the Metropolis criterion
  L126      monolithic top-level loop (sim + plot + I/O in one place)
  —         no test coverage
  L77-105   hot inner loop, GPU candidate
"""

from pathlib import Path
from datetime import datetime, timezone

FIXTURE_DIR = Path(__file__).parent
HERO_PATH = FIXTURE_DIR / "mc_2deg_thermo_init.py"
REFACTORED_PATH = FIXTURE_DIR / "mc_2deg_thermo_refactored.py"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def hero_source() -> str:
    return _read(HERO_PATH)


def refactored_source() -> str:
    return _read(REFACTORED_PATH)


SESSION_ID = "demo-mc-2deg"
ISSUE_ID_CANCELLATION = "iss-cancel-145"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def session_payload() -> dict:
    return {
        "id": SESSION_ID,
        "filename": "mc_2deg_thermo_init.py",
        "language": "python",
        "source_code": hero_source(),
        "created_at": now_iso(),
        "status": "created",
    }


# ---- Act 1: AUDIT --------------------------------------------------------

def audit_payload() -> list[dict]:
    return [
        {
            "id": ISSUE_ID_CANCELLATION,
            "session_id": SESSION_ID,
            "category": "numerical_instability",
            "severity": "critical",
            "line_start": 145,
            "line_end": 146,
            "title": "Catastrophic cancellation in variance over snapshots",
            "explanation": (
                "Naive Python `sum((e - mean)**2 for e in xs)` accumulates "
                "floating-point error O(eps * N). For 500-snapshot chains "
                "the variance — and therefore Cv — is biased ~0.3% on this "
                "problem class. Invisible per run, systematic across runs."
            ),
            "source": "llm",
        },
        {
            "id": "iss-burnin-77",
            "session_id": SESSION_ID,
            "category": "off_by_one",
            "severity": "critical",
            "line_start": 77,
            "line_end": 77,
            "title": "Burn-in loop skips first sample",
            "explanation": (
                "`for step in range(1, steps)` means eq_hist[0] is never "
                "written, and the first proposed move at this temperature "
                "is silently discarded. Across a 200-temperature sweep this "
                "shifts equilibration diagnostics by one index everywhere."
            ),
            "source": "static",
        },
        {
            "id": "iss-mutdef-64",
            "session_id": SESSION_ID,
            "category": "mutable_default",
            "severity": "high",
            "line_start": 64,
            "line_end": 64,
            "title": "Mutable default argument: history=[] shared across calls",
            "explanation": (
                "`history=[]` in the function signature is created once at "
                "definition time and shared across every call. Every "
                "temperature point's accepted-energy history bleeds into the "
                "next, contaminating diagnostics."
            ),
            "source": "static",
        },
        {
            "id": "iss-temp-92",
            "session_id": SESSION_ID,
            "category": "boundary_condition",
            "severity": "high",
            "line_start": 92,
            "line_end": 92,
            "title": "Hardcoded factor 2.4 inside Metropolis criterion",
            "explanation": (
                "`np.exp(-beta * dE_move * 2.4)` carries a magic factor that "
                "biases acceptance away from the physical Boltzmann weight. "
                "Reproducibility-breaking and not exposed as a parameter."
            ),
            "source": "llm",
        },
        {
            "id": "iss-mono-126",
            "session_id": SESSION_ID,
            "category": "other",
            "severity": "medium",
            "line_start": 126,
            "line_end": 196,
            "title": "Monolithic top-level loop: simulation + plotting + I/O",
            "explanation": (
                "70+ lines at module scope mix Metropolis driving, "
                "matplotlib state, and savefig calls. Not importable from a "
                "test harness; not reusable from a notebook without "
                "side effects."
            ),
            "source": "static",
        },
        {
            "id": "iss-tests-meta",
            "session_id": SESSION_ID,
            "category": "other",
            "severity": "medium",
            "line_start": 1,
            "line_end": 1,
            "title": "No test coverage",
            "explanation": (
                "Zero tests for the Metropolis core, the state-space "
                "construction, or the heat-capacity reduction. Refactor "
                "verification has nothing to lean on."
            ),
            "source": "static",
        },
        {
            "id": "iss-gpu-77",
            "session_id": SESSION_ID,
            "category": "other",
            "severity": "medium",
            "line_start": 77,
            "line_end": 105,
            "title": "Hot inner loop is GPU-suitable",
            "explanation": (
                "Tight Metropolis step loop with elementwise ops on "
                "`state_energies` and per-step RNG draws. Vectorisable in "
                "JAX with batched chains — see ROUTE."
            ),
            "source": "llm",
        },
    ]


# ---- Act 2: REASONING TRACE ---------------------------------------------

def reasoning_trace_payload(issue_id: str = ISSUE_ID_CANCELLATION) -> dict:
    return {
        "issue_id": issue_id,
        "why": {
            "title": "Why this is a bug",
            "body": (
                "The variance at lines 145-146 accumulates squared-deviation "
                "terms of opposite sign in a naive Python generator sum. For "
                "production runs with snapshots > 10⁴ floating-point "
                "cancellation produces errors O(10⁻⁸).\n\n"
                "Invisible in any single run. Systematic across all runs. "
                "Heat-capacity Cv biased ~0.3% on this problem class."
            ),
        },
        "verification_plan": {
            "title": "Verification plan",
            "test_count": 12,
            "items": [
                "N = 10², 10⁴, 10⁶ (scale)",
                "all-positive, all-negative, mixed-sign chain energies",
                "degenerate edges: constant chain, single-mode chain",
                "Original code vs Welford+Kahan fix run on each",
                "Numerical agreement compared at rtol=1e-9",
            ],
        },
        "trace_export": {
            "title": "Reasoning trace exported",
            "checklist": [
                {"label": "Bug class", "value": "numerical_instability"},
                {"label": "Pattern", "value": "subtractive cancellation in unordered summation"},
                {"label": "Fix strategy", "value": "Welford online variance + Kahan compensated sum"},
                {"label": "Test inputs preserved as JSON", "value": True},
                {"label": "Original outputs preserved at full precision", "value": True},
                {"label": "Available as JSONL for RLHF training", "value": True},
            ],
            "download_url": "/api/demo/trace.jsonl",
        },
    }


# ---- Act 3: REFACTOR + FIX ----------------------------------------------

def fix_payload() -> dict:
    return {
        "id": "fix-mc-2deg",
        "session_id": SESSION_ID,
        "issue_id": ISSUE_ID_CANCELLATION,
        "fixed_code": refactored_source(),
        "diff_summary": (
            "Extract MetropolisSampler class (5 methods); typed SamplerConfig; "
            "Welford+Kahan numerics; off-by-one + mutable-default + hardcoded "
            "factor fixed; injected RNG; pure functions; I/O removed."
        ),
        "created_at": now_iso(),
        "refactor_decisions": [
            "Extract MCMCSampler-style class as MetropolisSampler",
            "Five methods: propose · accept_reject · record · diagnostics · run",
            "Inject RNG via constructor (was: global np.random)",
            "Configuration → @dataclass SamplerConfig",
            "Pure functions where possible: build_state_space, kahan_sum, welford_mean_var",
            "Type hints on public API",
            "I/O extracted (plotting + savefig removed from sampler)",
            "Diagnostics extracted to welford_mean_var",
        ],
        "bug_fixes_applied": [
            "Off-by-one: equilibration loop now starts at 0",
            "Kahan compensated summation in record()",
            "Welford online variance in diagnostics()",
            "history=[] removed; sampler owns state",
            "Hardcoded 2.4 → SamplerConfig.beta_scale (default 1.0)",
        ],
        "generated_artifacts": [
            "tests/ folder with 12 pytest cases (synthesized inputs)",
            "Type stubs",
            "Docstrings on every public method",
        ],
    }


# ---- Act 4: VERIFY -------------------------------------------------------

def verify_steps() -> list[dict]:
    return [
        {"label": "Synthesizing test cases…", "result": "12 cases generated", "ms": 600},
        {"label": "Running original (sandboxed)…", "result": "4.7s", "ms": 1400},
        {"label": "Running refactor (sandboxed)…", "result": "1.3s", "ms": 1100},
        {"label": "Comparing outputs…", "result": "12/12 agree (rtol=1e-9)", "ms": 500},
    ]


def verify_payload() -> dict:
    cases = []
    inputs = [
        ("N=100, mixed-sign chain", "<E>=−0.243117…", 0.0023, 0.0021),
        ("N=10⁴, all-positive chain", "<E>=512.4188…", 0.018, 0.014),
        ("N=10⁶, mixed-sign chain", "<E>=12044.7218…", 1.91, 1.42),
        ("Constant log-L (degenerate)", "<E>=42.000000…", 0.001, 0.001),
        ("Single-mode chain", "<E>=8.117344…", 0.004, 0.003),
        ("Edge: all-negative", "<E>=−881.4422…", 0.012, 0.010),
        ("T=1K, 500 snapshots", "Cv=0.114 (biased)", 0.27, 0.21),
        ("T=150K, 500 snapshots", "Cv=0.812 (biased)", 0.27, 0.20),
        ("T=300K, 500 snapshots", "Cv=0.901 (biased)", 0.27, 0.20),
        ("Analytical Fermi-Dirac (T=10K)", "matches within 1e-9", 0.31, 0.18),
        ("Analytical Fermi-Dirac (T=100K)", "matches within 1e-9", 0.31, 0.18),
        ("Stress: N=10⁶, snapshots=10⁴", "agreement at 1e-9", 4.6, 1.3),
    ]
    for i, (inp, agr, om, fm) in enumerate(inputs):
        cases.append(
            {
                "index": i,
                "input_preview": inp,
                "original_output_preview": agr.split(" (biased)")[0],
                "fix_output_preview": agr.split(" (biased)")[0],
                "agreed": True,
                "original_ms": int(om * 1000),
                "fix_ms": int(fm * 1000),
                "notes": "biased posterior 0.3% on analytical test"
                if "Analytical" in inp
                else None,
            }
        )
    return {
        "id": "ver-mc-2deg",
        "fix_id": "fix-mc-2deg",
        "test_cases": cases,
        "passed": 12,
        "failed": 0,
        "overall_verdict": "all_agree",
        "created_at": now_iso(),
        "banner": (
            "Behavior preserved on all 12 synthesized inputs. "
            "Original biased posterior mean by 0.3% on the analytical-solution "
            "test. Refactor matches analytical solution."
        ),
        "report_url": "/api/demo/verification_report.pdf",
    }


# ---- Act 5: RESEARCHER QUESTION -----------------------------------------

def question_payload() -> dict:
    return {
        "id": "q-temperature",
        "title": "Helios has a question",
        "body": (
            "The original code uses a hardcoded factor 2.4 inside "
            "accept_reject(). I've made this a parameter on SamplerConfig "
            "and named it beta_scale (default 1.0)."
        ),
        "questions": [
            {
                "id": "q1",
                "prompt": "Is 2.4 the production default, or was this exploratory?",
                "options": [
                    {"id": "yes_default", "label": "Yes, default"},
                    {"id": "expose_required", "label": "No, expose as required"},
                ],
            },
            {
                "id": "q2",
                "prompt": "Should beta_scale be tunable per-chain or per-run?",
                "options": [
                    {"id": "per_chain", "label": "Per chain"},
                    {"id": "per_run", "label": "Per run"},
                    {"id": "either", "label": "Either is fine"},
                ],
            },
        ],
        "footer": (
            "Your answer becomes part of the reasoning trace and improves "
            "future suggestions on similar code."
        ),
    }


# ---- Act 6: ROUTE --------------------------------------------------------

def route_payload() -> dict:
    return {
        "session_id": SESSION_ID,
        "created_at": now_iso(),
        "today_gpu": [
            {
                "label": "Inner Metropolis loop",
                "lines": "77–105",
                "speedup": "60–180×",
                "rationale": (
                    "Tight Metropolis step loop, elementwise ops on "
                    "state_energies, per-step RNG draws. JAX-vectorisable "
                    "across batched chains on A100. We can do that for you."
                ),
                "complexity": "low",
                "cta": "Accept GPU port",
            }
        ],
        "near_term": [
            {
                "label": "Hamiltonian / state-space construction",
                "lines": "44–58",
                "speedup": "10–50×",
                "rationale": (
                    "Tensor-network construction for the 2DEG Hamiltonian "
                    "block. Hybrid GPU+TPU kernels available now."
                ),
                "complexity": "medium",
                "cta": "See report",
            }
        ],
        "future_quantum": [
            {
                "label": "VQE for >50-electron 2DEG systems",
                "lines": "—",
                "speedup": "~10⁶× (forecast)",
                "rationale": (
                    "Eligible for VQE when logical qubits ≥ ~100 "
                    "(2028–2030 forecast). Cost-benefit on that day: "
                    "~10⁶× speedup for >50-electron systems."
                ),
                "complexity": "high",
                "cta": "Mark for future review",
            }
        ],
        "quantum_candidates": [],
    }

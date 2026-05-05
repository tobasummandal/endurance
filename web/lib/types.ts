// Mirrors helios/schemas.py — keep in sync.

export type Language = 'python';
export type SessionStatus = 'created' | 'audited' | 'fixing' | 'verified' | 'routed';

export type Session = {
  id: string;
  filename: string;
  language: Language;
  source_code: string;
  created_at: string;
  status: SessionStatus;
};

export type IssueSeverity = 'low' | 'medium' | 'high' | 'critical';
export type IssueCategory =
  | 'off_by_one'
  | 'unit_mismatch'
  | 'numerical_instability'
  | 'float_equality'
  | 'mutable_default'
  | 'module_state'
  | 'bare_except'
  | 'shape_assumption'
  | 'boundary_condition'
  | 'other';
export type IssueSource = 'static' | 'llm';

export type Issue = {
  id: string;
  session_id: string;
  category: IssueCategory;
  severity: IssueSeverity;
  line_start: number;
  line_end: number;
  title: string;
  explanation: string;
  source: IssueSource;
};

export type Fix = {
  id: string;
  session_id: string;
  issue_id: string;
  fixed_code: string;
  diff_summary: string;
  created_at: string;
};

export type TestCaseResult = {
  index: number;
  input_preview: string;
  original_output_preview: string;
  fix_output_preview: string;
  agreed: boolean;
  original_ms: number;
  fix_ms: number;
  notes: string | null;
};

export type Verdict = 'all_agree' | 'partial_disagree' | 'all_disagree' | 'error';

export type Verification = {
  id: string;
  fix_id: string;
  test_cases: TestCaseResult[];
  passed: number;
  failed: number;
  overall_verdict: Verdict;
  created_at: string;
};

export type RoutePattern =
  | 'nested_numeric_loop'
  | 'matmul'
  | 'fft'
  | 'elementwise_ufunc'
  | 'monte_carlo'
  | 'other';
export type Complexity = 'low' | 'medium' | 'high';

export type RouteCandidate = {
  line_start: number;
  line_end: number;
  pattern: RoutePattern;
  estimated_speedup: string;
  complexity: Complexity;
  rationale: string;
};

export type RouteResult = {
  session_id: string;
  gpu_candidates: RouteCandidate[];
  quantum_candidates: never[];
  created_at: string;
};

// ---- Quantum router (hybrid Immune-filter -> ATC scheduler) demo ----

export type QuantumAntigen = 'qaoa' | 'vqe' | 'grover' | 'qft' | 'classical';
export type QuantumLane = 'cpu' | 'qpu';

export type QuantumTask = {
  id: string;
  name: string;
  antigen: QuantumAntigen;
  affinity: number;
  p_classical: number;
  weight: number;
  due_s: number;
  p_quantum: number | null;
};

export type QuantumScheduleEntry = {
  task_id: string;
  name: string;
  lane: QuantumLane;
  start: number;
  end: number;
  antigen: QuantumAntigen;
  p?: number;
};

export type QuantumPriorityEntry = {
  task_id: string;
  name: string;
  antigen: QuantumAntigen;
  lane: QuantumLane;
  pi: number;
  p: number;
};

export type QuantumRejected = {
  task_id: string;
  name: string;
  antigen: QuantumAntigen;
  affinity: number;
  reason: string;
};

export type QuantumSensitivityPoint = {
  eta: number;
  atc_total_s: number;
  reduction_pct: number;
};

export type QuantumRouterResult = {
  params: {
    k: number;
    threshold: number;
    qpu_overhead_s: number;
    eta: number;
    n_tasks: number;
  };
  tasks: QuantumTask[];
  fifo: { total_s: number; schedule: QuantumScheduleEntry[] };
  atc: {
    total_s: number;
    cpu_load_s: number;
    qpu_load_s: number;
    cpu_schedule: QuantumScheduleEntry[];
    qpu_schedule: QuantumScheduleEntry[];
    priority_queue: QuantumPriorityEntry[];
    rejected: QuantumRejected[];
    reduction_pct: number;
  };
  sensitivity: QuantumSensitivityPoint[];
  target_pct: number;
};

// Hardcoded demo flow — talks to /api/demo/*. Independent of the real session pipeline.

export type DemoIssueSeverity = 'critical' | 'high' | 'medium' | 'low';

export type DemoIssue = {
  id: string;
  session_id: string;
  category: string;
  severity: DemoIssueSeverity;
  line_start: number;
  line_end: number;
  title: string;
  explanation: string;
  source: 'static' | 'llm';
};

export type DemoSession = {
  id: string;
  filename: string;
  language: 'python';
  source_code: string;
  created_at: string;
  status: string;
};

export type DemoTrace = {
  issue_id: string;
  why: { title: string; body: string };
  verification_plan: { title: string; test_count: number; items: string[] };
  trace_export: {
    title: string;
    checklist: { label: string; value: string | boolean }[];
    download_url: string;
  };
};

export type DemoFix = {
  id: string;
  session_id: string;
  issue_id: string;
  fixed_code: string;
  diff_summary: string;
  refactor_decisions: string[];
  bug_fixes_applied: string[];
  generated_artifacts: string[];
};

export type DemoVerifyStep = { label: string; result: string; ms: number };
export type DemoVerifyCase = {
  index: number;
  input_preview: string;
  original_output_preview: string;
  fix_output_preview: string;
  agreed: boolean;
  original_ms: number;
  fix_ms: number;
  notes: string | null;
};

export type DemoVerify = {
  id: string;
  fix_id: string;
  test_cases: DemoVerifyCase[];
  passed: number;
  failed: number;
  overall_verdict: 'all_agree' | 'partial_disagree' | 'all_disagree' | 'error';
  banner: string;
  report_url: string;
};

export type DemoQuestionOption = { id: string; label: string };
export type DemoQuestion = {
  id: string;
  title: string;
  body: string;
  questions: { id: string; prompt: string; options: DemoQuestionOption[] }[];
  footer: string;
};

export type DemoRouteCandidate = {
  label: string;
  lines: string;
  speedup: string;
  rationale: string;
  complexity: 'low' | 'medium' | 'high';
  cta: string;
};

export type DemoRoute = {
  session_id: string;
  today_gpu: DemoRouteCandidate[];
  near_term: DemoRouteCandidate[];
  future_quantum: DemoRouteCandidate[];
};

const BASE = '/api/demo';

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json() as Promise<T>;
}

export const demoApi = {
  createSession: () => fetch(`${BASE}/sessions`, { method: 'POST' }).then((r) => r.json() as Promise<DemoSession>),
  getSession: (id: string) => get<DemoSession>(`/sessions/${id}`),
  audit: () => get<DemoIssue[]>('/audit'),
  trace: (issueId: string) => get<DemoTrace>(`/issues/${issueId}/trace`),
  fix: () => get<DemoFix>('/fix'),
  verify: () => get<DemoVerify>('/verify'),
  question: () => get<DemoQuestion>('/question'),
  route: () => get<DemoRoute>('/route'),
  answerQuestion: (answer: Record<string, string>) =>
    fetch(`${BASE}/question/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(answer),
    }).then((r) => r.json()),
  reportUrl: () => `${BASE}/verification_report.pdf`,
  traceJsonlUrl: () => `${BASE}/trace.jsonl`,
};

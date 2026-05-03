// Mirrors the SSE events emitted by backend/src/gateway/api.py

export type Stage =
  | "classifier" | "extractor" | "dispatcher" | "builder"
  | "verifier" | "verifier.static" | "verifier.simulator" | "verifier.cost_benefit"
  | "router"
  | "router.gate_1" | "router.gate_2" | "router.gate_3" | "router.gate_4" | "router.gate_5"
  | "execution.classical" | "execution.quantum"
  | "audit" | "pipeline";

export type Status = "start" | "done" | "pass" | "fail" | "decision" | "error" | "abort" | "complete";

export interface PipelineEvent {
  stage: Stage | string;
  status: Status | string;
  ts_ms: number;
  [extra: string]: unknown;
}

export interface ClassifierResult {
  problem_type: "vrp" | "maxcut" | "freq_coloring" | "qrng" | "unknown";
  confidence: number;
  rationale?: string;
  _source?: "gemini" | "canned" | string;
  _telemetry?: { model: string; latency_ms: number; input_tokens?: number; output_tokens?: number };
}

export interface GateResult {
  passed: boolean;
  reason: string;
  gate_name?: string;
  [k: string]: unknown;
}

export interface BackendResult {
  problem_type?: string;
  // maxcut
  max_cut_value?: number; partition?: number[];
  // vrp
  tour?: number[]; tour_length?: number | null; valid_tour?: boolean;
  // freq coloring
  coloring?: number[]; valid?: boolean; conflicts?: number; n_colors_used?: number;
  // shared
  method?: string; wall_time_ms?: number; sanity_check?: { ratio: number; passed: boolean };
  qaoa_gammas?: number[]; qaoa_betas?: number[];
  [k: string]: unknown;
}

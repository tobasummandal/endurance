// Derive UI state from the flat list of SSE events.

import type { PipelineEvent, ClassifierResult, GateResult, BackendResult } from "./types";
import type { StageState } from "./theme";

type NodeKey = "input" | "llm" | "builder" | "verifier" | "router";

export interface DerivedState {
  nodeStates: Record<NodeKey, StageState>;
  classifier?: ClassifierResult;
  extractor?: { params: Record<string, unknown> } & Record<string, unknown>;
  taskProfile?: Record<string, unknown>;
  builder?: { qubits?: number; depth?: number };
  verifier: {
    static?: { state: StageState; data: Record<string, unknown> };
    simulator?: { state: StageState; data: Record<string, unknown> };
    cost_benefit?: { state: StageState; data: Record<string, unknown> };
  };
  gates: { state: StageState; name: string; reason: string }[]; // length 0..5
  decision?: "QUANTUM" | "CLASSICAL" | "REJECTED";
  reasoning?: string;
  classicalResult?: BackendResult;
  quantumResult?: BackendResult;
  cotXml?: string;
  pipelineComplete: boolean;
}

export function derive(events: PipelineEvent[]): DerivedState {
  const s: DerivedState = {
    nodeStates: { input: "idle", llm: "idle", builder: "idle", verifier: "idle", router: "idle" },
    verifier: {},
    gates: [],
    pipelineComplete: false,
  };

  if (events.length > 0) s.nodeStates.input = "pass";

  for (const ev of events) {
    const stage = String(ev.stage);
    const status = String(ev.status);

    // ── LLM (classifier + extractor + dispatcher) ──
    if (stage === "classifier" && status === "start") s.nodeStates.llm = "active";
    if (stage === "classifier" && status === "done") {
      s.classifier = ev as unknown as ClassifierResult;
    }
    if (stage === "extractor" && status === "done") {
      s.extractor = ev as unknown as DerivedState["extractor"];
    }
    if (stage === "dispatcher" && status === "done") {
      s.taskProfile = ev.task_profile_row as Record<string, unknown>;
      s.nodeStates.llm = "pass";
    }

    // ── Builder ──
    if (stage === "builder" && status === "start") s.nodeStates.builder = "active";
    if (stage === "builder" && status === "done") {
      s.builder = { qubits: ev.qubits as number, depth: ev.depth as number };
      s.nodeStates.builder = "pass";
    }

    // ── Verifier ──
    if (stage === "verifier" && status === "start") s.nodeStates.verifier = "active";
    if (stage === "verifier.static") {
      s.verifier.static = { state: status === "pass" ? "pass" : "fail", data: ev as Record<string, unknown> };
    }
    if (stage === "verifier.simulator") {
      s.verifier.simulator = { state: status === "pass" ? "pass" : "fail", data: ev as Record<string, unknown> };
    }
    if (stage === "verifier.cost_benefit") {
      s.verifier.cost_benefit = {
        // cost_benefit failure is informational ("classical wins at this size") — not a blocker
        state: status === "pass" ? "pass" : "fail",
        data: ev as Record<string, unknown>,
      };
      // Verifier node settles on the strongest signal
      const states = [s.verifier.static, s.verifier.simulator, s.verifier.cost_benefit]
        .filter(Boolean)
        .map((v) => v!.state);
      s.nodeStates.verifier = states.includes("fail") && !states.includes("pass") ? "fail" : "pass";
    }

    // ── Router ──
    if (stage === "router" && status === "start") s.nodeStates.router = "active";
    if (stage.startsWith("router.gate_")) {
      const idx = Number(stage.split("_")[1]);
      const state: StageState = status === "pass" ? "pass" : "fail";
      s.gates[idx - 1] = {
        state,
        name: String(ev.gate_name ?? `gate_${idx}`),
        reason: String(ev.reason ?? ""),
      };
    }
    if (stage === "router" && status === "decision") {
      s.decision = ev.decision as DerivedState["decision"];
      s.reasoning = String(ev.reasoning ?? "");
      s.nodeStates.router = ev.decision === "QUANTUM" ? "pass" : "fail";
    }

    // ── Execution ──
    if (stage === "execution.classical" && status === "done") {
      s.classicalResult = ev.result as BackendResult;
    }
    if (stage === "execution.quantum" && status === "done") {
      s.quantumResult = ev.result as BackendResult;
    }

    // ── Audit / done ──
    if (stage === "audit" && status === "done") {
      s.cotXml = String(ev.cot_xml ?? "");
    }
    if (stage === "pipeline" && (status === "complete" || status === "abort")) {
      s.pipelineComplete = true;
    }
  }

  return s;
}

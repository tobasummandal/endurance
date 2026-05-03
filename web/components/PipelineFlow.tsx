"use client";

import { PipelineNode, Connector } from "./PipelineNode";
import { VerifierBars } from "./VerifierBars";
import { RoutingPillars } from "./RoutingPillars";
import type { DerivedState } from "@/lib/derive";

export function PipelineFlow({ s, onSelect }: { s: DerivedState; onSelect: (n: string) => void }) {
  const cls = s.classifier;
  const verifierStates = [
    s.verifier.static?.state,
    s.verifier.simulator?.state,
    s.verifier.cost_benefit?.state,
  ];

  return (
    <div className="flex items-stretch gap-1 h-full px-2">
      <PipelineNode index={1} title="Input" state={s.nodeStates.input} width={150} onClick={() => onSelect("input")}>
        prompt accepted
        <div className="text-[color:var(--brass)] mt-1">→ NL stream</div>
      </PipelineNode>

      <Connector active={s.nodeStates.llm !== "idle"} />

      <PipelineNode index={2} title="LLM Translation" state={s.nodeStates.llm} width={210} onClick={() => onSelect("llm")}>
        {cls ? (
          <>
            <div>type: <span className="text-[color:var(--brass)]">{cls.problem_type}</span></div>
            <div>conf: {cls.confidence?.toFixed?.(2) ?? "—"}</div>
            <div className="text-[color:var(--ash)]">src: {cls._source}</div>
          </>
        ) : "classify → extract → dispatch"}
      </PipelineNode>

      <Connector active={s.nodeStates.builder !== "idle"} />

      <PipelineNode index={3} title="Circuit Builder" state={s.nodeStates.builder} width={180} onClick={() => onSelect("builder")}>
        {s.builder ? (
          <>
            <div>qubits: <span className="text-[color:var(--brass)]">{s.builder.qubits}</span></div>
            <div>depth: <span className="text-[color:var(--brass)]">{s.builder.depth}</span></div>
            <div className="text-[color:var(--ash)]">QAOA template</div>
          </>
        ) : "QAOA template assembly"}
      </PipelineNode>

      <Connector active={s.nodeStates.verifier !== "idle"} />

      <PipelineNode index={4} title="Verifier" state={s.nodeStates.verifier} width={180} onClick={() => onSelect("verifier")}>
        <div className="flex justify-between items-end h-full">
          <div className="space-y-0.5">
            <div>static · sim · cost</div>
            {s.verifier.simulator && (
              <div className="text-[color:var(--brass)]">
                ratio {(s.verifier.simulator.data.ratio as number)?.toFixed?.(1) ?? "?"}×
              </div>
            )}
          </div>
          <VerifierBars states={verifierStates} />
        </div>
      </PipelineNode>

      <Connector active={s.nodeStates.router !== "idle"} />

      <PipelineNode index={5} title="Router · 5 gates" state={s.nodeStates.router} width={300} onClick={() => onSelect("router")}>
        <RoutingPillars gates={s.gates} decision={s.decision} />
      </PipelineNode>
    </div>
  );
}

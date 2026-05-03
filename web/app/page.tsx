"use client";

import { useMemo, useState } from "react";
import { InputBar } from "@/components/InputBar";
import { PipelineFlow } from "@/components/PipelineFlow";
import { ResultsPanel } from "@/components/ResultsPanel";
import { DetailModal } from "@/components/DetailModal";
import { useGatewayStream } from "@/lib/sse";
import { derive } from "@/lib/derive";

const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8003/solve/stream";

export default function Home() {
  const [runKey, setRunKey] = useState<number | null>(null);
  const [params, setParams] = useState<{ prompt: string; latency_budget_ms: number; classification_level?: string }>({
    prompt: "Find the optimal route for 4 drones across 4 targets",
    latency_budget_ms: 30000,
  });
  const [selected, setSelected] = useState<string | null>(null);

  const { events, status } = useGatewayStream({
    key: runKey,
    url: GATEWAY,
    prompt: params.prompt,
    latency_budget_ms: params.latency_budget_ms,
    classification_level: params.classification_level,
  });

  const state = useMemo(() => derive(events), [events]);
  const running = status === "running";

  return (
    <main className="h-screen w-full flex flex-col p-4 gap-3 overflow-hidden">
      <header className="flex items-baseline justify-between px-2">
        <div>
          <h1 className="font-serif text-[28px] font-light tracking-[0.08em] text-[color:var(--bone)]">
            Quantum Routing Brain
          </h1>
          <p className="text-[10px] uppercase tracking-[0.25em] text-[color:var(--ash)] mt-0.5">
            Tactical orchestration · Xtremis Challenge 2 · Dry Dock 2026
          </p>
        </div>
        <div className="text-[10px] font-mono text-[color:var(--ash)] flex items-center gap-3">
          <span>events: <span className="text-[color:var(--brass)]">{events.length}</span></span>
          <span>status: <span className="text-[color:var(--brass)]">{status}</span></span>
          {state.decision && (
            <span>
              decision: <span style={{ color: state.decision === "QUANTUM" ? "var(--brass)" : "var(--bronze)" }}>{state.decision}</span>
            </span>
          )}
        </div>
      </header>

      <section className="shrink-0">
        <InputBar
          running={running}
          onRun={(args) => {
            setParams(args);
            setRunKey((k) => (k ?? 0) + 1);
          }}
        />
      </section>

      <section className="frame flex-1 min-h-0 px-2 py-3">
        <PipelineFlow s={state} onSelect={setSelected} />
      </section>

      <section className="shrink-0 h-[180px]">
        <ResultsPanel classical={state.classicalResult} quantum={state.quantumResult} decision={state.decision} />
      </section>

      {state.reasoning && (
        <div className="text-[11px] font-mono text-[color:var(--ash)] px-2 truncate">
          <span className="text-[color:var(--brass)]">↳ rationale:</span> {state.reasoning}
        </div>
      )}

      <DetailModal open={selected !== null} onClose={() => setSelected(null)} selected={selected} state={state} />
    </main>
  );
}

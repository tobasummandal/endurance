"use client";

import { useState } from "react";
import { palette } from "@/lib/theme";

const PRESETS = [
  { label: "VRP", prompt: "Find the optimal route for 4 drones across 4 targets" },
  { label: "Frequency", prompt: "Assign frequencies to 5 cells with no adjacent interference" },
  { label: "MaxCut", prompt: "Partition this 8-node spectrum interference graph" },
  { label: "SECRET", prompt: "Classified VRP for SOCOM mission planning", classification: "SECRET" as const },
];

export function InputBar({
  onRun,
  running,
}: {
  onRun: (args: { prompt: string; latency_budget_ms: number; classification_level?: string }) => void;
  running: boolean;
}) {
  const [prompt, setPrompt] = useState(PRESETS[0].prompt);
  const [latency, setLatency] = useState(30000);
  const [classification, setClassification] = useState<string | undefined>(undefined);

  return (
    <div className="frame px-6 py-4 flex items-center gap-4 w-full">
      <div className="flex flex-col gap-1">
        <label className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--ash)]">Task description</label>
        <input
          className="bg-[color:var(--carbon)] border border-[color:var(--walnut)] rounded px-3 py-2 w-[420px] text-[color:var(--bone)] outline-none focus:border-[color:var(--brass)] transition-colors text-sm"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="describe a tactical compute task..."
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--ash)]">Presets</label>
        <div className="flex gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => {
                setPrompt(p.prompt);
                setClassification(p.classification);
              }}
              className="px-3 py-2 text-xs border border-[color:var(--walnut)] hover:border-[color:var(--brass)] hover:text-[color:var(--brass)] rounded transition-colors text-[color:var(--ash)]"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1 flex-1">
        <label className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--ash)]">
          Latency budget · <span className="text-[color:var(--brass)]">{(latency / 1000).toFixed(0)}s</span>
        </label>
        <input
          type="range"
          min={1000}
          max={60000}
          step={1000}
          value={latency}
          onChange={(e) => setLatency(Number(e.target.value))}
          className="w-full accent-[color:var(--brass)]"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-[10px] uppercase tracking-[0.2em] text-[color:var(--ash)]">Classification</label>
        <select
          value={classification ?? ""}
          onChange={(e) => setClassification(e.target.value || undefined)}
          className="bg-[color:var(--carbon)] border border-[color:var(--walnut)] rounded px-2 py-2 text-xs text-[color:var(--bone)] outline-none"
        >
          <option value="">CUI (default)</option>
          <option value="UNCLASS">UNCLASS</option>
          <option value="CUI">CUI</option>
          <option value="SECRET">SECRET</option>
          <option value="TS-SCI">TS-SCI</option>
        </select>
      </div>

      <button
        disabled={running || !prompt}
        onClick={() => onRun({ prompt, latency_budget_ms: latency, classification_level: classification })}
        className="self-end px-6 py-2 rounded font-serif font-light tracking-[0.15em] text-sm uppercase border transition-all"
        style={{
          background: running ? palette.walnut : palette.brass,
          color: running ? palette.ash : palette.void,
          borderColor: running ? palette.walnut : palette.champagne,
          boxShadow: running ? "none" : "0 0 24px rgba(201, 166, 107, 0.45)",
        }}
      >
        {running ? "Running…" : "Run"}
      </button>
    </div>
  );
}

"use client";

import { motion } from "framer-motion";
import type { BackendResult } from "@/lib/types";

function summarize(r: BackendResult | undefined): string {
  if (!r) return "—";
  if (r.problem_type === "maxcut" || r.max_cut_value !== undefined) return `cut = ${r.max_cut_value}`;
  if (r.problem_type === "vrp" || r.tour) {
    if (r.tour_length == null) return "no valid tour";
    return `tour len = ${r.tour_length}`;
  }
  if (r.problem_type === "freq_coloring" || r.coloring) {
    return `${r.n_colors_used ?? "?"} colors · ${r.conflicts ?? "?"} conflicts`;
  }
  return "ok";
}

function detail(r: BackendResult | undefined): string {
  if (!r) return "";
  if (r.tour) return `[${r.tour.join(" → ")}]`;
  if (r.partition) return `[${r.partition.join(",")}]`;
  if (r.coloring) return `[${r.coloring.join(",")}]`;
  return "";
}

export function ResultsPanel({
  classical,
  quantum,
  decision,
}: {
  classical?: BackendResult;
  quantum?: BackendResult;
  decision?: "QUANTUM" | "CLASSICAL" | "REJECTED";
}) {
  return (
    <div className="grid grid-cols-2 gap-4 h-full">
      {/* Classical */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: classical ? 1 : 0.4 }}
        className="surface-card px-5 py-4 flex flex-col"
        style={{
          borderColor: decision === "CLASSICAL" ? "var(--bronze)" : "var(--walnut)",
        }}
      >
        <div className="flex items-baseline justify-between mb-1">
          <h3 className="font-serif text-[18px] tracking-wide text-[color:var(--bone)] font-light">Classical</h3>
          <span className="text-[10px] font-mono uppercase tracking-[0.18em]" style={{ color: decision === "CLASSICAL" ? "var(--bronze)" : "var(--ash)" }}>
            {classical?.method ?? "—"}
          </span>
        </div>
        <div className="flex-1 flex flex-col justify-center">
          <div className="font-serif text-[28px] font-light text-[color:var(--bone)]">{summarize(classical)}</div>
          <div className="text-[11px] text-[color:var(--ash)] font-mono mt-1">{detail(classical)}</div>
        </div>
        <div className="text-[10px] font-mono text-[color:var(--ash)]">
          wall: {classical?.wall_time_ms != null ? `${classical.wall_time_ms} ms` : "—"}
        </div>
      </motion.div>

      {/* Quantum */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: quantum ? 1 : 0.4 }}
        className="surface-card px-5 py-4 flex flex-col relative overflow-hidden"
        style={{
          borderColor: decision === "QUANTUM" ? "var(--brass)" : "var(--walnut)",
          boxShadow: decision === "QUANTUM" ? "0 0 28px rgba(201, 166, 107, 0.35)" : undefined,
        }}
      >
        {decision === "QUANTUM" && (
          <div className="absolute top-0 left-0 right-0 h-[2px] shimmer-brass opacity-80" />
        )}
        <div className="flex items-baseline justify-between mb-1">
          <h3 className="font-serif text-[18px] tracking-wide text-[color:var(--bone)] font-light">Quantum (Aer)</h3>
          <span className="text-[10px] font-mono uppercase tracking-[0.18em]" style={{ color: decision === "QUANTUM" ? "var(--brass)" : "var(--ash)" }}>
            {quantum?.method ?? "—"}
          </span>
        </div>
        <div className="flex-1 flex flex-col justify-center">
          <div className="font-serif text-[28px] font-light text-[color:var(--bone)]">
            {quantum ? summarize(quantum) : "not routed quantum"}
          </div>
          <div className="text-[11px] text-[color:var(--ash)] font-mono mt-1">{detail(quantum)}</div>
        </div>
        <div className="text-[10px] font-mono text-[color:var(--ash)] flex justify-between">
          <span>sanity: {quantum?.sanity_check ? `${quantum.sanity_check.ratio}× uniform` : "—"}</span>
          <span>{quantum?.qaoa_gammas ? `γ=${quantum.qaoa_gammas[0]} β=${quantum.qaoa_betas?.[0]}` : ""}</span>
        </div>
      </motion.div>
    </div>
  );
}

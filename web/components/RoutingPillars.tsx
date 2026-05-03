"use client";

import { motion } from "framer-motion";
import type { StageState } from "@/lib/theme";
import { stateColor } from "@/lib/theme";

const GATE_LABELS = [
  { short: "PROBLEM", long: "Problem class" },
  { short: "CLASS", long: "Classification" },
  { short: "LATENCY", long: "Latency budget" },
  { short: "SIZE", long: "Instance size" },
  { short: "BACKEND", long: "Backend live" },
];

export function RoutingPillars({
  gates,
  decision,
}: {
  gates: { state: StageState; name: string; reason: string }[];
  decision?: "QUANTUM" | "CLASSICAL" | "REJECTED";
}) {
  return (
    <div className="flex flex-col gap-2 h-full justify-center">
      <div className="flex items-end justify-around gap-2 h-[150px]">
        {GATE_LABELS.map((label, i) => {
          const g = gates[i];
          const state: StageState = g?.state ?? "idle";
          const color = stateColor(state);
          const fillPct = state === "pass" ? 100 : state === "fail" ? 60 : state === "active" ? 40 : 12;
          return (
            <div key={i} className="flex flex-col items-center gap-1 flex-1">
              {/* Pillar shaft */}
              <div className="relative w-full h-[120px] rounded-t-sm overflow-hidden border border-[color:var(--walnut)]" style={{ background: "linear-gradient(180deg, rgba(58,42,26,0.3), rgba(21,18,14,0.95))" }}>
                <motion.div
                  initial={{ height: "12%" }}
                  animate={{ height: `${fillPct}%` }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  style={{
                    background: `linear-gradient(180deg, ${color}cc, ${color}55)`,
                    boxShadow: state === "pass"
                      ? `0 0 18px ${color}aa, inset 0 0 12px ${color}44`
                      : state === "fail"
                      ? `0 0 18px ${color}aa, inset 0 0 12px ${color}44`
                      : "none",
                  }}
                  className="absolute bottom-0 left-0 right-0"
                />
                {/* Capital cap on top */}
                <div
                  className="absolute top-0 left-0 right-0 h-2"
                  style={{
                    background: state === "idle" ? "var(--walnut)" : color,
                    opacity: state === "idle" ? 0.5 : 0.85,
                  }}
                />
              </div>
              <div className="text-[9px] font-mono uppercase tracking-[0.15em]" style={{ color: state === "idle" ? "var(--ash)" : color }}>
                {label.short}
              </div>
            </div>
          );
        })}
      </div>

      {/* Decision beam */}
      <div className="relative h-6 mt-1">
        {decision && (
          <motion.div
            initial={{ scaleX: 0, opacity: 0 }}
            animate={{ scaleX: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="absolute inset-x-0 h-1 origin-left"
            style={{
              top: 8,
              background: decision === "QUANTUM"
                ? "linear-gradient(90deg, var(--champagne), var(--brass), var(--champagne))"
                : "linear-gradient(90deg, var(--bronze), var(--walnut), var(--bronze))",
              boxShadow: decision === "QUANTUM"
                ? "0 0 14px rgba(232, 213, 168, 0.7)"
                : "0 0 8px rgba(139, 111, 71, 0.4)",
            }}
          />
        )}
        {decision && (
          <div
            className="absolute right-0 top-0 text-[10px] font-mono uppercase tracking-[0.2em]"
            style={{ color: decision === "QUANTUM" ? "var(--brass)" : "var(--bronze)" }}
          >
            → {decision}
          </div>
        )}
      </div>
    </div>
  );
}

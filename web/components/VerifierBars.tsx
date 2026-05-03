"use client";

import { motion } from "framer-motion";
import type { StageState } from "@/lib/theme";
import { stateColor } from "@/lib/theme";

const CHECKS = ["STATIC", "SIMULATOR", "COST/BENEFIT"];

export function VerifierBars({
  states,
}: {
  states: (StageState | undefined)[]; // length 3
}) {
  return (
    <div className="flex items-end justify-center gap-3 h-full">
      {CHECKS.map((label, i) => {
        const s = states[i] ?? "idle";
        const color = stateColor(s);
        const fill = s === "pass" ? 100 : s === "fail" ? 70 : s === "active" ? 35 : 10;
        return (
          <div key={label} className="flex flex-col items-center gap-1">
            <div className="relative w-3 h-[60px] bg-[color:var(--walnut)]/40 rounded-sm overflow-hidden border border-[color:var(--walnut)]">
              <motion.div
                initial={{ height: "10%" }}
                animate={{ height: `${fill}%` }}
                transition={{ duration: 0.5 }}
                className="absolute bottom-0 left-0 right-0"
                style={{ background: color, boxShadow: `0 0 6px ${color}88` }}
              />
            </div>
            <div className="text-[8px] font-mono uppercase tracking-[0.1em]" style={{ color: s === "idle" ? "var(--ash)" : color }}>
              {label}
            </div>
          </div>
        );
      })}
    </div>
  );
}

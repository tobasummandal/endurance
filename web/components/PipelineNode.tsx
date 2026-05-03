"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";
import type { StageState } from "@/lib/theme";
import { stateColor, stateGlow } from "@/lib/theme";

export function PipelineNode({
  index,
  title,
  state,
  width = 200,
  children,
  onClick,
}: {
  index: number;
  title: string;
  state: StageState;
  width?: number;
  children?: ReactNode;
  onClick?: () => void;
}) {
  const color = stateColor(state);
  return (
    <motion.div
      onClick={onClick}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      style={{ width, borderColor: color }}
      className={`surface-card px-4 py-3 cursor-pointer transition-all ${stateGlow(state)} ${onClick ? "hover:scale-[1.01]" : ""}`}
    >
      <div className="flex items-center gap-2 mb-2">
        <span
          className="badge-num font-mono text-[10px]"
          style={{ color, borderColor: color }}
        >
          {index}
        </span>
        <h3 className="font-serif text-[15px] font-light tracking-wide text-[color:var(--bone)]">
          {title}
        </h3>
      </div>
      <div className="text-[11px] text-[color:var(--ash)] font-mono leading-relaxed min-h-[40px]">
        {children}
      </div>
    </motion.div>
  );
}

export function Connector({ active }: { active: boolean }) {
  return (
    <div className="flex-1 connector self-center mx-1 relative overflow-hidden">
      {active && (
        <>
          <span className="particle" style={{ animationDelay: "0s" }} />
          <span className="particle" style={{ animationDelay: "0.4s" }} />
          <span className="particle" style={{ animationDelay: "0.8s" }} />
          <span className="particle" style={{ animationDelay: "1.2s" }} />
        </>
      )}
    </div>
  );
}

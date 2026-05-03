"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect } from "react";
import type { DerivedState } from "@/lib/derive";

const TITLES: Record<string, string> = {
  input: "Input",
  llm: "LLM Translation",
  builder: "Circuit Builder",
  verifier: "Verifier",
  router: "Router · 5-gate engine",
};

export function DetailModal({
  open,
  onClose,
  selected,
  state,
}: {
  open: boolean;
  onClose: () => void;
  selected: string | null;
  state: DerivedState;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && selected && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40"
          />
          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 250 }}
            className="fixed right-0 top-0 h-full w-[480px] surface-card z-50 overflow-y-auto p-6 no-scrollbar"
          >
            <div className="flex items-baseline justify-between mb-4">
              <h2 className="font-serif text-2xl font-light tracking-wide text-[color:var(--bone)]">
                {TITLES[selected] ?? selected}
              </h2>
              <button onClick={onClose} className="text-[color:var(--ash)] hover:text-[color:var(--brass)] text-xs uppercase tracking-[0.15em]">
                ESC
              </button>
            </div>
            <pre className="text-[11px] text-[color:var(--bone)] font-mono whitespace-pre-wrap leading-relaxed">
              {JSON.stringify(payloadFor(selected, state), null, 2)}
            </pre>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function payloadFor(sel: string, s: DerivedState): unknown {
  switch (sel) {
    case "input":    return { prompt_accepted: true, classifier: s.classifier };
    case "llm":      return { classifier: s.classifier, extractor: s.extractor, taskProfile: s.taskProfile };
    case "builder":  return { builder: s.builder, taskProfile: s.taskProfile };
    case "verifier": return s.verifier;
    case "router":   return { gates: s.gates, decision: s.decision, reasoning: s.reasoning, cot_xml: s.cotXml };
    default:         return s;
  }
}

"use client";

import { useEffect, useRef, useState } from "react";
import type { PipelineEvent } from "./types";

export interface SSEHookState {
  events: PipelineEvent[];
  status: "idle" | "running" | "done" | "error";
  error: string | null;
}

/**
 * useGatewayStream — opens an EventSource against /solve/stream and accumulates
 * every event the gateway emits. Pass `key` (counter incremented on each Run)
 * to (re)trigger the stream; pass null/undefined to stay idle.
 */
export function useGatewayStream(opts: {
  key: number | null;
  url: string;
  prompt: string;
  latency_budget_ms?: number;
  classification_level?: string;
}): SSEHookState {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [status, setStatus] = useState<SSEHookState["status"]>("idle");
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (opts.key == null || !opts.prompt) return;

    setEvents([]);
    setStatus("running");
    setError(null);

    const url = new URL(opts.url);
    url.searchParams.set("prompt", opts.prompt);
    if (opts.latency_budget_ms != null) url.searchParams.set("latency_budget_ms", String(opts.latency_budget_ms));
    if (opts.classification_level)      url.searchParams.set("classification_level", opts.classification_level);

    const es = new EventSource(url.toString());
    esRef.current = es;

    // Gateway sends named events (event: classifier.start). EventSource only
    // routes those if we addEventListener for each name; we use the catch-all
    // by listening for "message" for anonymous events plus a generic handler
    // attached via addEventListener for every distinct event name as it arrives.
    // sse-starlette's default emits named events with the name in `event:` line —
    // browser routes those to listeners registered on that name. We register
    // a fallback listener that wraps `es.onmessage` AND attach an event
    // handler for every event name we know about.

    const knownStages = [
      "classifier.start","classifier.done",
      "extractor.start","extractor.done",
      "dispatcher.start","dispatcher.done",
      "builder.start","builder.done",
      "verifier.start","verifier.static.pass","verifier.static.fail",
      "verifier.simulator.pass","verifier.simulator.fail",
      "verifier.cost_benefit.pass","verifier.cost_benefit.fail",
      "router.start","router.error",
      "router.gate_1.pass","router.gate_1.fail",
      "router.gate_2.pass","router.gate_2.fail",
      "router.gate_3.pass","router.gate_3.fail",
      "router.gate_4.pass","router.gate_4.fail",
      "router.gate_5.pass","router.gate_5.fail",
      "router.decision",
      "execution.classical.done","execution.quantum.done",
      "audit.done","pipeline.complete","pipeline.abort",
    ];

    const push = (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data) as PipelineEvent;
        setEvents((prev) => [...prev, data]);
        if (data.stage === "pipeline" && (data.status === "complete" || data.status === "abort")) {
          setStatus("done");
          es.close();
        }
        if (data.stage === "router" && data.status === "error") {
          setStatus("error");
          setError(String(data.error ?? "router error"));
          es.close();
        }
      } catch (e) {
        // ignore non-JSON lines
      }
    };

    knownStages.forEach((name) => es.addEventListener(name, push as EventListener));
    es.onerror = () => {
      // EventSource fires error on natural close too; only flag if not done
      setStatus((s) => (s === "running" ? "error" : s));
      setError((e) => e ?? "SSE connection error");
      es.close();
    };

    return () => { es.close(); };
  }, [opts.key]); // eslint-disable-line react-hooks/exhaustive-deps

  return { events, status, error };
}

'use client';

import QuantumDemo from './QuantumDemo';
import type { RouteResult } from '@/lib/types';

type Props = {
  result: RouteResult | null;
  loading?: boolean;
};

export default function RoutePanel({ result, loading }: Props) {
  if (loading) {
    return (
      <div className="helios-card" style={{ color: 'var(--dim)', fontSize: 13 }}>
        <span className="stage-dot active" />
        scanning for hot patterns…
      </div>
    );
  }

  if (!result) {
    return (
      <div className="helios-card" style={{ color: 'var(--dim)', fontSize: 13 }}>
        Run routing to see GPU acceleration candidates.
      </div>
    );
  }

  const candidates = result.gpu_candidates;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div>
        <div className="section-tag" style={{ marginBottom: '0.75rem' }}>GPU Candidates</div>
        {candidates.length === 0 ? (
          <div className="helios-card" style={{ color: 'var(--dim)', fontSize: 13, lineHeight: 1.7 }}>
            No GPU candidates. Function is scalar / non-array / sub-threshold; Helios doesn&apos;t recommend acceleration.
          </div>
        ) : (
          candidates.map((c, i) => (
            <div key={i} className="helios-card" style={{ marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap', marginBottom: '0.6rem' }}>
                <span style={{ fontSize: 11, color: 'var(--dim)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                  lines {c.line_start === c.line_end ? c.line_start : `${c.line_start}–${c.line_end}`}
                </span>
                <span style={{ fontSize: 11, color: 'var(--sun)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                  {c.pattern}
                </span>
                <span style={{ fontSize: 11, color: 'var(--right)', marginLeft: 'auto' }}>
                  {c.estimated_speedup} · {c.complexity}
                </span>
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--fg)', opacity: 0.85 }}>{c.rationale}</div>
            </div>
          ))
        )}
      </div>

      <div>
        <div className="section-tag" style={{ marginBottom: '0.75rem' }}>Quantum · Hybrid Immune-filter → ATC</div>
        <QuantumDemo />
      </div>
    </div>
  );
}

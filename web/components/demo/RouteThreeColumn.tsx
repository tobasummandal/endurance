'use client';

import type { DemoRoute, DemoRouteCandidate } from '@/lib/demo';

const COLS: { key: keyof Pick<DemoRoute, 'today_gpu' | 'near_term' | 'future_quantum'>; label: string; sub: string; tint: string }[] = [
  { key: 'today_gpu', label: 'Today (GPU)', sub: 'real, ship-it', tint: 'rgba(232, 163, 61, 0.12)' },
  { key: 'near_term', label: 'Near-term (specialized)', sub: 'tensor / hybrid', tint: 'rgba(110, 119, 135, 0.10)' },
  { key: 'future_quantum', label: 'Future (quantum)', sub: '~2028–2030 forecast', tint: 'rgba(91, 110, 168, 0.10)' },
];

export default function RouteThreeColumn({ route }: { route: DemoRoute }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '1rem' }}>
      {COLS.map((c) => (
        <div key={c.key} className="helios-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', background: c.tint }}>
          <div>
            <div style={{ textTransform: 'uppercase', letterSpacing: '0.12em', fontSize: 11, color: 'var(--dim)' }}>
              {c.label}
            </div>
            <div style={{ fontSize: 11, color: 'var(--dim)', opacity: 0.7 }}>{c.sub}</div>
          </div>
          {(route[c.key] as DemoRouteCandidate[]).map((cand, i) => (
            <Card key={i} cand={cand} />
          ))}
        </div>
      ))}
    </div>
  );
}

function Card({ cand }: { cand: DemoRouteCandidate }) {
  return (
    <div style={{ borderTop: '1px solid var(--line)', paddingTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div style={{ fontFamily: 'var(--serif)', fontStyle: 'italic', fontSize: 15, lineHeight: 1.3 }}>
        {cand.label}
      </div>
      <div style={{ fontSize: 11, color: 'var(--dim)', display: 'flex', gap: '0.6rem' }}>
        <span>line {cand.lines}</span>
        <span>·</span>
        <span>complexity: {cand.complexity}</span>
      </div>
      <div style={{ fontFamily: 'var(--mono, monospace)', fontSize: 18, color: 'var(--sun)' }}>{cand.speedup}</div>
      <div style={{ fontSize: 13, lineHeight: 1.6, opacity: 0.85 }}>{cand.rationale}</div>
      <button className="helios-btn" style={{ padding: '0.4rem 0.8rem', fontSize: 12, alignSelf: 'flex-start' }}>
        {cand.cta}
      </button>
    </div>
  );
}

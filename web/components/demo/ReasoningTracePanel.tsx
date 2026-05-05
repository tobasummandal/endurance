'use client';

import type { DemoTrace } from '@/lib/demo';
import { demoApi } from '@/lib/demo';

export default function ReasoningTracePanel({ trace }: { trace: DemoTrace | null }) {
  if (!trace) return null;
  return (
    <div className="helios-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <Section title={trace.why.title}>
        <p style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--prose)', fontSize: 14, lineHeight: 1.7, opacity: 0.9 }}>
          {trace.why.body}
        </p>
      </Section>

      <Divider />

      <Section title={trace.verification_plan.title}>
        <div style={{ fontSize: 12, color: 'var(--dim)', marginBottom: '0.5rem' }}>
          {trace.verification_plan.test_count} test inputs synthesized:
        </div>
        <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: 13, lineHeight: 1.7 }}>
          {trace.verification_plan.items.map((it, i) => (
            <li key={i} style={{ opacity: 0.9 }}>{it}</li>
          ))}
        </ul>
      </Section>

      <Divider />

      <Section title={trace.trace_export.title}>
        <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {trace.trace_export.checklist.map((c, i) => (
            <li key={i} style={{ display: 'flex', gap: '0.6rem', fontSize: 13 }}>
              <span style={{ color: 'var(--right, #6BAA75)' }}>✓</span>
              <span style={{ color: 'var(--dim)' }}>{c.label}:</span>
              <span style={{ opacity: 0.9 }}>{typeof c.value === 'boolean' ? (c.value ? 'yes' : 'no') : c.value}</span>
            </li>
          ))}
        </ul>
        <a
          href={demoApi.traceJsonlUrl()}
          download="reasoning_trace.jsonl"
          className="helios-btn"
          style={{ marginTop: '1rem', display: 'inline-block', padding: '0.5rem 1rem', fontSize: 12, textDecoration: 'none' }}
        >
          ↓ Download trace.jsonl
        </a>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ textTransform: 'uppercase', letterSpacing: '0.12em', fontSize: 11, color: 'var(--dim)', marginBottom: '0.6rem' }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function Divider() {
  return <div style={{ borderTop: '1px solid var(--line)', opacity: 0.6 }} />;
}

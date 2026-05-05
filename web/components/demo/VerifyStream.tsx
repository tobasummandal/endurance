'use client';

import { useEffect, useRef, useState } from 'react';
import type { DemoVerify, DemoVerifyStep } from '@/lib/demo';
import { demoApi } from '@/lib/demo';

type Step = DemoVerifyStep & { state: 'pending' | 'running' | 'done' };

const INITIAL: Step[] = [
  { label: 'Synthesizing test cases…', result: '', ms: 0, state: 'pending' },
  { label: 'Running original (sandboxed)…', result: '', ms: 0, state: 'pending' },
  { label: 'Running refactor (sandboxed)…', result: '', ms: 0, state: 'pending' },
  { label: 'Comparing outputs…', result: '', ms: 0, state: 'pending' },
];

export default function VerifyStream({ autoStart = true }: { autoStart?: boolean }) {
  const [steps, setSteps] = useState<Step[]>(INITIAL);
  const [result, setResult] = useState<DemoVerify | null>(null);
  const [showCases, setShowCases] = useState(false);
  const started = useRef(false);

  function start() {
    if (started.current) return;
    started.current = true;
    setSteps(INITIAL);
    setResult(null);
    const es = new EventSource('/api/demo/verify/stream');
    es.addEventListener('step', (e: MessageEvent) => {
      const d = JSON.parse(e.data);
      setSteps((cur) => cur.map((s, i) => (i === d.index ? { ...s, label: d.label, result: d.result, state: d.state } : s)));
    });
    es.addEventListener('result', (e: MessageEvent) => {
      setResult(JSON.parse(e.data));
    });
    es.addEventListener('end', () => es.close());
    es.onerror = () => es.close();
  }

  useEffect(() => {
    if (autoStart) start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div className="helios-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {steps.map((s, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: 13 }}>
            <span className={`stage-dot ${s.state === 'running' ? 'active' : s.state === 'done' ? 'done' : ''}`} style={{ flex: '0 0 auto' }} />
            <span style={{ flex: 1, opacity: s.state === 'pending' ? 0.5 : 1 }}>{s.label}</span>
            <span style={{ color: 'var(--dim)', fontSize: 12 }}>{s.state === 'done' ? `✓ ${s.result}` : ''}</span>
          </div>
        ))}
      </div>

      {result && (
        <>
          <div
            className="verdict-banner"
            style={{
              background: 'rgba(107, 170, 117, 0.08)',
              border: '1px solid rgba(107, 170, 117, 0.3)',
              padding: '1.25rem 1.5rem',
              borderRadius: 6,
              fontFamily: 'var(--prose)',
              fontSize: 14,
              lineHeight: 1.6,
            }}
          >
            <div style={{ textTransform: 'uppercase', letterSpacing: '0.12em', fontSize: 11, color: 'var(--right, #6BAA75)', marginBottom: '0.5rem' }}>
              ✓ {result.passed}/{result.passed + result.failed} agree (rtol=1e-9)
            </div>
            {result.banner}
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <a href={demoApi.reportUrl()} download className="helios-btn" style={{ textDecoration: 'none' }}>
              ↓ Generate verification report (PDF)
            </a>
            <button className="helios-btn" onClick={() => setShowCases((s) => !s)}>
              {showCases ? 'Hide' : 'Show'} 12 cases
            </button>
          </div>
          {showCases && (
            <div className="helios-card" style={{ padding: 0, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ background: 'rgba(110, 119, 135, 0.05)', textAlign: 'left' }}>
                    <th style={th}>#</th>
                    <th style={th}>Input</th>
                    <th style={th}>Original</th>
                    <th style={th}>Fix</th>
                    <th style={th}>Δ time</th>
                    <th style={th}>Agree</th>
                  </tr>
                </thead>
                <tbody>
                  {result.test_cases.map((c) => (
                    <tr key={c.index} style={{ borderTop: '1px solid var(--line)' }}>
                      <td style={td}>{c.index}</td>
                      <td style={td}>{c.input_preview}</td>
                      <td style={td}>{c.original_output_preview}</td>
                      <td style={td}>{c.fix_output_preview}</td>
                      <td style={td}>{c.original_ms}→{c.fix_ms}ms</td>
                      <td style={{ ...td, color: c.agreed ? 'var(--right, #6BAA75)' : '#c66' }}>{c.agreed ? '✓' : '✗'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

const th: React.CSSProperties = { padding: '0.6rem 0.8rem', fontWeight: 500, color: 'var(--dim)', textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: 10 };
const td: React.CSSProperties = { padding: '0.6rem 0.8rem', verticalAlign: 'top' };

'use client';

import { useEffect, useRef, useState } from 'react';
import CodeEditor from '@/components/CodeEditor';
import Reveal from '@/components/Reveal';

type Severity = 'low' | 'medium' | 'high' | 'critical';

type Finding = {
  category: string;
  severity: Severity;
  line_start: number;
  line_end: number;
  title: string;
  explanation: string;
  source: 'static' | 'llm';
};

const STARTER = `# Try editing — Helios audits as you type.
# Each keystroke calls /api/live/audit/static (sub-100ms, deterministic).
# Click "Run deep audit" to add LLM findings.

import numpy as np

def integrate(f_values, dx):
    n = len(f_values)
    total = 0.0
    for i in range(1, n - 1):  # off-by-one bug
        total += 0.5 * (f_values[i] + f_values[i+1]) * dx
    return total


def simulate(steps, history=[]):  # mutable default!
    state = 0.0
    for _ in range(steps):
        state += 1.0
        history.append(state)
    return history
`;

const SEV_RANK: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export default function LivePage() {
  const [code, setCode] = useState(STARTER);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [staticElapsed, setStaticElapsed] = useState<number | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sessionToken = useRef<string>('live-' + Math.random().toString(36).slice(2));
  const abortRef = useRef<AbortController | null>(null);

  // Debounced static audit on every keystroke (no LLM, sub-100ms).
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch('/api/live/audit/static', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: 'live.py',
            source_code: code,
            session_token: sessionToken.current,
          }),
        });
        if (!res.ok) {
          const text = await res.text();
          setError(`static ${res.status}: ${text}`);
          return;
        }
        const data = await res.json();
        setStaticElapsed(data.elapsed_ms);
        setError(null);
        setFindings((prev) => {
          // Replace only static findings; keep any LLM ones that came from a prior deep audit.
          const llm = prev.filter((f) => f.source === 'llm');
          const fresh = (data.findings || []).map((f: Finding) => ({ ...f, source: 'static' as const }));
          return [...fresh, ...llm];
        });
      } catch (e: any) {
        setError(e?.message || String(e));
      }
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [code]);

  async function runDeepAudit() {
    if (streaming) {
      abortRef.current?.abort();
      return;
    }
    setStreaming(true);
    setStreamLog([]);
    setError(null);

    const ac = new AbortController();
    abortRef.current = ac;

    try {
      const res = await fetch('/api/live/audit/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: 'live.py',
          source_code: code,
          session_token: sessionToken.current,
        }),
        signal: ac.signal,
      });
      if (!res.ok || !res.body) {
        setError(`stream ${res.status}`);
        setStreaming(false);
        return;
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '';

      const llmSeen = new Set<string>();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const chunks = buf.split('\n\n');
        buf = chunks.pop() || '';
        for (const chunk of chunks) {
          if (!chunk.trim()) continue;
          let event = '';
          let dataRaw = '';
          for (const ln of chunk.split('\n')) {
            if (ln.startsWith('event:')) event = ln.slice(6).trim();
            else if (ln.startsWith('data:')) dataRaw += ln.slice(5).trim();
          }
          if (!event) continue;
          let data: any = null;
          try {
            data = JSON.parse(dataRaw);
          } catch {
            data = dataRaw;
          }
          setStreamLog((prev) => [...prev, event]);

          if (event === 'llm_partial' || event === 'llm') {
            const arr: any[] = Array.isArray(data) ? data : [];
            setFindings((prev) => {
              const stat = prev.filter((f) => f.source === 'static');
              const existingLlm = prev.filter((f) => f.source === 'llm');
              const fresh: Finding[] = [];
              for (const f of arr) {
                const k = `${f.line_start}:${f.category}:${f.title}`;
                if (!llmSeen.has(k)) {
                  llmSeen.add(k);
                  fresh.push({ ...f, source: 'llm' });
                }
              }
              return [...stat, ...existingLlm, ...fresh];
            });
          } else if (event === 'merged') {
            const arr: any[] = Array.isArray(data) ? data : [];
            setFindings(arr.map((f) => ({ ...f, source: f.source || 'llm' })));
          } else if (event === 'done' || event === 'error') {
            setStreaming(false);
          }
        }
      }
      setStreaming(false);
    } catch (e: any) {
      if (e?.name !== 'AbortError') {
        setError(e?.message || String(e));
      }
      setStreaming(false);
    }
  }

  const sorted = [...findings].sort((a, b) => {
    const s = SEV_RANK[a.severity] - SEV_RANK[b.severity];
    return s !== 0 ? s : a.line_start - b.line_start;
  });

  return (
    <section className="helios-section" style={{ paddingTop: '8rem' }}>
      <Reveal>
        <div className="section-tag">Live Coding</div>
      </Reveal>
      <Reveal delay={1}>
        <h1 className="helios-h" style={{ marginBottom: '1.5rem' }}>
          Audit as you type.
        </h1>
      </Reveal>
      <Reveal delay={2}>
        <p
          style={{
            fontFamily: 'var(--prose)',
            fontSize: 16,
            color: 'var(--fg)',
            opacity: 0.85,
            maxWidth: 720,
            lineHeight: 1.6,
            letterSpacing: '-0.01em',
            marginBottom: '2.5rem',
          }}
        >
          Static checks run on every keystroke (debounced 300ms). No LLM, no cost &mdash; sub-100ms feedback. Click&nbsp;
          <em>Run deep audit</em> when you want the model to look for the bugs static analysis can&rsquo;t see.
        </p>
      </Reveal>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)',
          gap: '2rem',
          alignItems: 'start',
        }}
      >
        <div>
          <div className="section-tag" style={{ marginBottom: '0.75rem' }}>
            Editor
          </div>
          <CodeEditor value={code} onChange={setCode} height={600} />
          <div
            style={{
              marginTop: '0.75rem',
              fontSize: 11,
              color: 'var(--dim)',
              fontFamily: 'var(--mono)',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              display: 'flex',
              gap: '1.5rem',
              flexWrap: 'wrap',
            }}
          >
            <span>{code.split('\n').length} lines</span>
            {staticElapsed !== null && <span>static · {staticElapsed.toFixed(0)}ms</span>}
            <span>{findings.filter((f) => f.source === 'static').length} static · {findings.filter((f) => f.source === 'llm').length} llm</span>
          </div>
        </div>

        <div>
          <div className="section-tag" style={{ marginBottom: '0.75rem' }}>
            Findings
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <button className={`helios-btn ${streaming ? '' : 'primary'}`} onClick={runDeepAudit}>
              {streaming ? '◉ Stop' : '▶ Run deep audit (LLM)'}
            </button>
          </div>

          {streaming && (
            <div
              className="helios-card"
              style={{
                marginBottom: '1rem',
                color: 'var(--dim)',
                fontSize: 11,
                fontFamily: 'var(--mono)',
                letterSpacing: '0.05em',
              }}
            >
              <span className="stage-dot active" /> streaming · {streamLog.join(' → ') || 'connecting'}
            </div>
          )}

          {error && (
            <div className="verdict-banner red" style={{ marginBottom: '1rem' }}>
              <span>{error}</span>
            </div>
          )}

          {sorted.length === 0 ? (
            <div className="helios-card" style={{ color: 'var(--dim)', fontSize: 13, lineHeight: 1.7 }}>
              <div
                style={{
                  color: 'var(--right)',
                  marginBottom: '0.5rem',
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  fontSize: 11,
                }}
              >
                ✓ No findings
              </div>
              Static analysis is clean. Run a deep audit to look for scientific bugs the model can spot.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', maxHeight: 600, overflowY: 'auto', paddingRight: '0.25rem' }}>
              {sorted.map((f, i) => (
                <div key={i} className="helios-card" style={{ padding: '0.9rem 1rem' }}>
                  <div
                    style={{
                      display: 'flex',
                      gap: '0.5rem',
                      alignItems: 'center',
                      marginBottom: '0.5rem',
                      flexWrap: 'wrap',
                    }}
                  >
                    <span className={`sev sev-${f.severity}`} style={{ fontSize: 9, padding: '0.1rem 0.4rem' }}>
                      {f.severity}
                    </span>
                    <span style={{ fontSize: 10, color: 'var(--dim)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                      {f.category}
                    </span>
                    <span style={{ fontSize: 10, color: 'var(--dim)' }}>
                      L{f.line_start === f.line_end ? f.line_start : `${f.line_start}–${f.line_end}`}
                    </span>
                    <span
                      style={{
                        fontSize: 9,
                        color: f.source === 'llm' ? 'var(--sun)' : 'var(--dim)',
                        marginLeft: 'auto',
                        textTransform: 'uppercase',
                        letterSpacing: '0.1em',
                      }}
                    >
                      {f.source}
                    </span>
                  </div>
                  <div style={{ fontFamily: 'var(--serif)', fontSize: 14, fontStyle: 'italic', marginBottom: '0.3rem', lineHeight: 1.3 }}>
                    {f.title}
                  </div>
                  <div
                    style={{
                      fontFamily: 'var(--prose)',
                      fontSize: 13,
                      lineHeight: 1.5,
                      color: 'var(--fg)',
                      opacity: 0.85,
                      letterSpacing: '-0.01em',
                    }}
                  >
                    {f.explanation}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

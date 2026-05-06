'use client';

import { useEffect, useMemo, useState } from 'react';
import CodeEditor from '@/components/CodeEditor';
import DiffView from '@/components/DiffView';
import IssueList from '@/components/IssueList';
import Reveal from '@/components/Reveal';
import QuestionCard from '@/components/demo/QuestionCard';
import ReasoningTracePanel from '@/components/demo/ReasoningTracePanel';
import RefactorAnnotations from '@/components/demo/RefactorAnnotations';
import RouteThreeColumn from '@/components/demo/RouteThreeColumn';
import VerifyStream from '@/components/demo/VerifyStream';
import { demoApi } from '@/lib/demo';
import type {
  DemoFix,
  DemoIssue,
  DemoQuestion,
  DemoRoute,
  DemoSession,
  DemoTrace,
} from '@/lib/demo';
import type { Issue } from '@/lib/types';

type Act = 'audit' | 'trace' | 'refactor' | 'verify' | 'question' | 'route';

const ACTS: { key: Act; label: string; subtitle: string }[] = [
  { key: 'audit', label: '01 · audit', subtitle: 'silent bugs, twelve seconds' },
  { key: 'trace', label: '02 · reasoning trace', subtitle: 'the moat, made tangible' },
  { key: 'refactor', label: '03 · refactor + fix', subtitle: 'research → production' },
  { key: 'route', label: '04 · route', subtitle: 'GPU today, quantum tomorrow' },
  { key: 'verify', label: '05 · verify', subtitle: '12/12 cases agree' },
  { key: 'question', label: '06 · researcher loop', subtitle: 'Helios has a question' },
];

function toIssue(d: DemoIssue): Issue {
  return d as unknown as Issue;
}

export default function DemoPage() {
  const [act, setAct] = useState<Act>('audit');
  const [session, setSession] = useState<DemoSession | null>(null);
  const [issues, setIssues] = useState<DemoIssue[]>([]);
  const [selected, setSelected] = useState<DemoIssue | null>(null);
  const [trace, setTrace] = useState<DemoTrace | null>(null);
  const [fix, setFix] = useState<DemoFix | null>(null);
  const [question, setQuestion] = useState<DemoQuestion | null>(null);
  const [route, setRoute] = useState<DemoRoute | null>(null);

  // Boot: create session + run audit immediately so the audit pane is full on land.
  useEffect(() => {
    (async () => {
      const s = await demoApi.createSession();
      setSession(s);
      const a = await demoApi.audit();
      setIssues(a);
      setSelected(a[0] ?? null);
    })();
  }, []);

  // Lazy-load remaining acts as user clicks through.
  useEffect(() => {
    if (act === 'trace' && !trace && selected) demoApi.trace(selected.id).then(setTrace);
    if (act === 'refactor' && !fix) demoApi.fix().then(setFix);
    if (act === 'question' && !question) demoApi.question().then(setQuestion);
    if (act === 'route' && !route) demoApi.route().then(setRoute);
  }, [act, selected, trace, fix, question, route]);

  // Keyboard: j/k step through acts, 1-6 jump.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.target as HTMLElement)?.tagName?.match(/INPUT|TEXTAREA|BUTTON/)) return;
      const idx = ACTS.findIndex((a) => a.key === act);
      if (e.key === 'j' || e.key === 'ArrowRight') setAct(ACTS[Math.min(ACTS.length - 1, idx + 1)].key);
      if (e.key === 'k' || e.key === 'ArrowLeft') setAct(ACTS[Math.max(0, idx - 1)].key);
      if (e.key >= '1' && e.key <= '6') setAct(ACTS[parseInt(e.key, 10) - 1].key);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [act]);

  const highlightLines = useMemo(() => issues.map((i) => i.line_start), [issues]);
  const sourceCode = session?.source_code || '';

  return (
    <section className="helios-section" style={{ paddingTop: '6rem' }}>
      <Reveal>
        <div className="section-tag">Demo · mc_2deg_thermo_init.py</div>
      </Reveal>
      <div className="helios-tabs" role="tablist" style={{ marginBottom: '2rem', marginTop: '2rem' }}>
        {ACTS.map((a) => (
          <button
            key={a.key}
            role="tab"
            aria-selected={act === a.key}
            className={`helios-tab ${act === a.key ? 'active' : ''}`}
            onClick={() => setAct(a.key)}
            title={a.subtitle}
          >
            {a.label}
          </button>
        ))}
      </div>

      {act === 'audit' && (
        <SplitPane
          left={<CodeEditor value={sourceCode} readOnly height={620} highlightLines={highlightLines} />}
          right={
            <>
              <div className="section-tag" style={{ marginBottom: '0.75rem' }}>Issues found · {issues.length}</div>
              <div style={{ maxHeight: 620, overflowY: 'auto', paddingRight: '0.5rem' }}>
                <IssueList
                  issues={issues.map(toIssue)}
                  selectedId={selected?.id}
                  onSelect={(i) => setSelected(issues.find((x) => x.id === i.id) || null)}
                  onGenerateFix={(i) => {
                    setSelected(issues.find((x) => x.id === i.id) || null);
                    setAct('trace');
                  }}
                />
              </div>
              <div style={{ marginTop: '1rem', fontSize: 12, color: 'var(--dim)', fontStyle: 'italic' }}>
                Two are silent bugs that would have shipped to production. Three are why production
                engineers reject this code on first review. One is a hardware opportunity.
              </div>
            </>
          }
        />
      )}

      {act === 'trace' && (
        <SplitPane
          left={<CodeEditor value={sourceCode} readOnly height={620} highlightLines={selected ? [selected.line_start] : []} />}
          right={
            <>
              <div className="section-tag" style={{ marginBottom: '0.75rem' }}>
                Reasoning trace · {selected?.title ?? '—'}
              </div>
              <ReasoningTracePanel trace={trace} />
              <div style={{ marginTop: '1.25rem' }}>
                <button className="helios-btn primary" onClick={() => setAct('refactor')}>
                  → Generate fix
                </button>
              </div>
            </>
          }
        />
      )}

      {act === 'refactor' && (
        <SplitPane
          left={fix ? <DiffView original={sourceCode} fixed={fix.fixed_code} summary={fix.diff_summary} context={3} /> : <Loading />}
          right={
            <>
              <div className="section-tag" style={{ marginBottom: '0.75rem' }}>Refactor · annotations</div>
              {fix ? <RefactorAnnotations fix={fix} /> : <Loading />}
              <div style={{ marginTop: '1.25rem' }}>
                <button className="helios-btn primary" onClick={() => setAct('route')}>
                  → Hardware routing
                </button>
              </div>
            </>
          }
        />
      )}

      {act === 'verify' && (
        <SplitPane
          left={fix ? <DiffView original={sourceCode} fixed={fix.fixed_code} summary={fix.diff_summary} context={3} /> : <Loading />}
          right={
            <>
              <div className="section-tag" style={{ marginBottom: '0.75rem' }}>Verify · sandboxed</div>
              <VerifyStream />
              <div style={{ marginTop: '1.25rem' }}>
                <button className="helios-btn primary" onClick={() => setAct('question')}>
                  → Researcher loop
                </button>
              </div>
            </>
          }
        />
      )}

      {act === 'question' && (
        <SplitPane
          left={fix ? <DiffView original={sourceCode} fixed={fix.fixed_code} summary={fix.diff_summary} context={3} /> : <Loading />}
          right={
            <>
              <div className="section-tag" style={{ marginBottom: '0.75rem' }}>Researcher in the loop</div>
              {question ? <QuestionCard question={question} /> : <Loading />}
            </>
          }
        />
      )}

      {act === 'route' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="section-tag">Hardware routing — recommendations</div>
          {route ? <RouteThreeColumn route={route} /> : <Loading />}
          <div>
            <button className="helios-btn primary" onClick={() => setAct('verify')}>
              ✓ Verify
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function SplitPane({ left, right }: { left: React.ReactNode; right: React.ReactNode }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.05fr) minmax(0, 1fr)', gap: '2rem' }}>
      <div>{left}</div>
      <div>{right}</div>
    </div>
  );
}

function Loading() {
  return (
    <div className="helios-card" style={{ color: 'var(--dim)', fontSize: 13 }}>
      <span className="stage-dot active" /> loading…
    </div>
  );
}

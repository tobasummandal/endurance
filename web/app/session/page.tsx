'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useMemo, useState } from 'react';
import CodeEditor from '@/components/CodeEditor';
import DiffView from '@/components/DiffView';
import IssueList from '@/components/IssueList';
import Reveal from '@/components/Reveal';
import RoutePanel from '@/components/RoutePanel';
import VerificationPanel from '@/components/VerificationPanel';
import { api } from '@/lib/api';
import type { Fix, Issue, RouteResult, Verification } from '@/lib/types';

type Tab = 'audit' | 'fix' | 'verify' | 'route';

function SessionView() {
  const params = useSearchParams();
  const sessionId = params.get('id') || '';
  const [tab, setTab] = useState<Tab>('audit');
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const [fix, setFix] = useState<Fix | null>(null);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [route, setRoute] = useState<RouteResult | null>(null);

  const session = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => api.getSession(sessionId),
    enabled: !!sessionId,
  });

  const issuesQuery = useQuery({
    queryKey: ['issues', sessionId],
    queryFn: () => api.listIssues(sessionId),
    enabled: !!sessionId,
  });

  const auditMut = useMutation({
    mutationFn: () => api.audit(sessionId),
    onSuccess: (issues) => {
      issuesQuery.refetch();
      if (issues.length && !selectedIssue) setSelectedIssue(issues[0]);
    },
  });

  // Auto-run audit on first load if there are no issues yet.
  useEffect(() => {
    if (issuesQuery.data && issuesQuery.data.length === 0 && session.data?.status === 'created' && !auditMut.isPending) {
      auditMut.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [issuesQuery.data, session.data]);

  const fixMut = useMutation({
    mutationFn: (issueId: string) => api.generateFix(sessionId, issueId),
    onSuccess: (f) => {
      setFix(f);
      setVerification(null);
      setTab('fix');
    },
  });

  const verifyMut = useMutation({
    mutationFn: (fixId: string) => api.verify(sessionId, fixId),
    onSuccess: (v) => setVerification(v),
  });

  const routeMut = useMutation({
    mutationFn: () => api.route(sessionId),
    onSuccess: (r) => setRoute(r),
  });

  const issues: Issue[] = issuesQuery.data || [];
  const highlightLines = useMemo(() => issues.map((i) => i.line_start), [issues]);

  if (!sessionId) {
    return (
      <section className="helios-section">
        <div className="verdict-banner red">
          <span>missing session id</span>
          <span className="note">URL must include ?id=...</span>
        </div>
      </section>
    );
  }

  return (
    <section className="helios-section" style={{ paddingTop: '8rem' }}>
      <Reveal>
        <div className="section-tag">Session</div>
      </Reveal>

      <Reveal delay={1}>
        <h1 className="helios-h" style={{ marginBottom: '2rem', fontSize: 'clamp(2rem, 4vw, 3rem)' }}>
          {session.data?.filename || sessionId.slice(0, 8)}
        </h1>
      </Reveal>

      <div className="helios-tabs" role="tablist">
        {(['audit', 'fix', 'verify', 'route'] as Tab[]).map((t, i) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            className={`helios-tab ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            <StageDot stage={t} state={stateFor(t, { issues, fix, verification, route, auditPending: auditMut.isPending, fixPending: fixMut.isPending, verifyPending: verifyMut.isPending, routePending: routeMut.isPending })} />
            0{i + 1} · {t}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '2rem' }}>
        <div>
          <div className="section-tag" style={{ marginBottom: '0.75rem' }}>Source</div>
          <CodeEditor value={session.data?.source_code || ''} readOnly height={520} highlightLines={highlightLines} />
        </div>

        <div>
          <div className="section-tag" style={{ marginBottom: '0.75rem' }}>{tab}</div>

          {tab === 'audit' && (
            <>
              {auditMut.error && (
                <div className="verdict-banner red" style={{ marginBottom: '1rem' }}>
                  <span>audit failed</span>
                  <span className="note">{(auditMut.error as Error).message}</span>
                </div>
              )}
              {auditMut.isPending || (issuesQuery.isLoading && issues.length === 0) ? (
                <div className="helios-card" style={{ color: 'var(--dim)', fontSize: 13 }}>
                  <span className="stage-dot active" /> running static + LLM audit…
                </div>
              ) : (
                <IssueList
                  issues={issues}
                  selectedId={selectedIssue?.id}
                  onSelect={setSelectedIssue}
                  onGenerateFix={(iss) => {
                    setSelectedIssue(iss);
                    fixMut.mutate(iss.id);
                  }}
                />
              )}
              <div style={{ marginTop: '1.5rem' }}>
                <button
                  className="helios-btn"
                  disabled={auditMut.isPending}
                  onClick={() => auditMut.mutate()}
                >
                  {auditMut.isPending ? '◉ Auditing' : issues.length ? '↻ Re-audit' : '▶ Run audit'}
                </button>
              </div>
            </>
          )}

          {tab === 'fix' && (
            <>
              {fixMut.error && (
                <div className="verdict-banner red" style={{ marginBottom: '1rem' }}>
                  <span>fix generation failed</span>
                  <span className="note">{(fixMut.error as Error).message}</span>
                </div>
              )}
              {fixMut.isPending && (
                <div className="helios-card" style={{ color: 'var(--dim)', fontSize: 13 }}>
                  <span className="stage-dot active" /> generating minimal rewrite…
                </div>
              )}
              {!fix && !fixMut.isPending && (
                <div className="helios-card" style={{ color: 'var(--dim)', fontSize: 13, lineHeight: 1.7 }}>
                  Pick an issue from the Audit tab and click Generate fix.
                </div>
              )}
              {fix && session.data && (
                <>
                  <DiffView original={session.data.source_code} fixed={fix.fixed_code} summary={fix.diff_summary} />
                  <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem', flexWrap: 'wrap' }}>
                    <button
                      className="helios-btn primary"
                      disabled={verifyMut.isPending}
                      onClick={() => {
                        verifyMut.mutate(fix.id);
                        setTab('verify');
                      }}
                    >
                      {verifyMut.isPending ? '◉ Verifying' : '✓ Verify'}
                    </button>
                  </div>
                </>
              )}
            </>
          )}

          {tab === 'verify' && (
            <>
              {verifyMut.error && (
                <div className="verdict-banner red" style={{ marginBottom: '1rem' }}>
                  <span>verification failed</span>
                  <span className="note">{(verifyMut.error as Error).message}</span>
                </div>
              )}
              <VerificationPanel
                verification={verification}
                loading={verifyMut.isPending}
                loadingStage={verifyMut.isPending ? 'spawning sandbox A & B …' : undefined}
              />
            </>
          )}

          {tab === 'route' && (
            <>
              {routeMut.error && (
                <div className="verdict-banner red" style={{ marginBottom: '1rem' }}>
                  <span>routing failed</span>
                  <span className="note">{(routeMut.error as Error).message}</span>
                </div>
              )}
              {!route && !routeMut.isPending && (
                <div style={{ marginBottom: '1rem' }}>
                  <button className="helios-btn primary" onClick={() => routeMut.mutate()}>
                    ▶ Run routing
                  </button>
                </div>
              )}
              <RoutePanel result={route} loading={routeMut.isPending} />
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function stateFor(
  t: Tab,
  ctx: {
    issues: Issue[];
    fix: Fix | null;
    verification: Verification | null;
    route: RouteResult | null;
    auditPending: boolean;
    fixPending: boolean;
    verifyPending: boolean;
    routePending: boolean;
  },
): 'idle' | 'active' | 'done' | 'error' {
  if (t === 'audit') return ctx.auditPending ? 'active' : ctx.issues.length ? 'done' : 'idle';
  if (t === 'fix') return ctx.fixPending ? 'active' : ctx.fix ? 'done' : 'idle';
  if (t === 'verify') return ctx.verifyPending ? 'active' : ctx.verification ? 'done' : 'idle';
  if (t === 'route') return ctx.routePending ? 'active' : ctx.route ? 'done' : 'idle';
  return 'idle';
}

function StageDot({ stage, state }: { stage: Tab; state: 'idle' | 'active' | 'done' | 'error' }) {
  const cls = state === 'idle' ? '' : state;
  return <span className={`stage-dot ${cls}`} aria-label={`${stage} ${state}`} />;
}

export default function Page() {
  return (
    <Suspense fallback={<section className="helios-section"><div style={{ color: 'var(--dim)' }}>loading…</div></section>}>
      <SessionView />
    </Suspense>
  );
}

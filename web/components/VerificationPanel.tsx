'use client';

import type { Verification } from '@/lib/types';

type Props = {
  verification: Verification | null;
  loading?: boolean;
  loadingStage?: string;
};

const VERDICT_META: Record<string, { tone: 'green' | 'amber' | 'red'; label: (v: Verification) => string; note: string }> = {
  all_agree: {
    tone: 'green',
    label: (v) => `All ${v.test_cases.length} cases agree`,
    note: 'Fix preserves observed behavior on every synthesized input.',
  },
  partial_disagree: {
    tone: 'amber',
    label: (v) => `${v.passed} / ${v.test_cases.length} agree · ${v.failed} disagree`,
    note: 'Disagreements are where the bug manifests — inspect cases marked ✗.',
  },
  all_disagree: {
    tone: 'red',
    label: (v) => `0 / ${v.test_cases.length} agree`,
    note: 'Fix changes behavior on every input. Review carefully.',
  },
  error: {
    tone: 'red',
    label: () => 'Verification error',
    note: 'Sandbox or comparison failed. Check logs.',
  },
};

export default function VerificationPanel({ verification, loading, loadingStage }: Props) {
  if (loading || !verification) {
    return (
      <div className="helios-card" style={{ color: 'var(--dim)', fontSize: 13 }}>
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className="stage-dot active" />
            {loadingStage || 'verifying…'}
          </div>
        ) : (
          'Generate a fix and click Verify.'
        )}
      </div>
    );
  }

  const meta = VERDICT_META[verification.overall_verdict] || VERDICT_META.partial_disagree;

  return (
    <div>
      <table className="helios-table">
        <thead>
          <tr>
            <th>#</th>
            <th>input</th>
            <th>original</th>
            <th>fix</th>
            <th>agree</th>
            <th>time</th>
          </tr>
        </thead>
        <tbody>
          {verification.test_cases.map((tc, i) => (
            <tr key={tc.index} className="row-in" style={{ animationDelay: `${i * 30}ms` }}>
              <td style={{ color: 'var(--dim)' }}>{tc.index}</td>
              <td>{truncate(tc.input_preview, 60)}</td>
              <td>{truncate(tc.original_output_preview, 30)}</td>
              <td>{truncate(tc.fix_output_preview, 30)}</td>
              <td className={tc.agreed ? 'ok' : 'bad'}>{tc.agreed ? '✓' : '✗'}</td>
              <td style={{ color: 'var(--dim)', fontSize: 11 }}>
                {tc.original_ms.toFixed(1)} / {tc.fix_ms.toFixed(1)}ms
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className={`verdict-banner ${meta.tone}`}>
        <span>{meta.label(verification)}</span>
        <span className="note">{meta.note}</span>
      </div>
    </div>
  );
}

function truncate(s: string, n: number) {
  if (s.length <= n) return s;
  return s.slice(0, n - 1) + '…';
}

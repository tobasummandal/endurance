'use client';

import type { Issue } from '@/lib/types';

type Props = {
  issues: Issue[];
  selectedId?: string | null;
  onSelect?: (issue: Issue) => void;
  onGenerateFix?: (issue: Issue) => void;
};

const SEV_RANK: Record<Issue['severity'], number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export default function IssueList({ issues, selectedId, onSelect, onGenerateFix }: Props) {
  if (!issues.length) {
    return (
      <div className="helios-card" style={{ color: 'var(--dim)', fontSize: 13, lineHeight: 1.7 }}>
        <div style={{ color: 'var(--right)', marginBottom: '0.5rem', letterSpacing: '0.1em', textTransform: 'uppercase', fontSize: 11 }}>
          ✓ No issues found
        </div>
        Static checks and the LLM audit both came back clean. This is a good outcome — but Helios catches silent bugs, not algorithmic
        errors. Verify your tests still pass.
      </div>
    );
  }

  const sorted = [...issues].sort((a, b) => SEV_RANK[a.severity] - SEV_RANK[b.severity]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {sorted.map((iss) => {
        const isSelected = selectedId === iss.id;
        return (
          <div
            key={iss.id}
            className="helios-card"
            onClick={() => onSelect?.(iss)}
            style={{
              cursor: 'none',
              borderColor: isSelected ? 'var(--sun)' : 'var(--line)',
              transition: 'border-color 0.2s ease',
            }}
          >
            <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', marginBottom: '0.6rem', flexWrap: 'wrap' }}>
              <span className={`sev sev-${iss.severity}`}>{iss.severity}</span>
              <span style={{ fontSize: 11, color: 'var(--dim)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                {iss.category}
              </span>
              <span style={{ fontSize: 11, color: 'var(--dim)' }}>
                line {iss.line_start === iss.line_end ? iss.line_start : `${iss.line_start}–${iss.line_end}`}
              </span>
              <span style={{ fontSize: 10, color: 'var(--dim)', marginLeft: 'auto', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                {iss.source}
              </span>
            </div>
            <div style={{ fontFamily: 'var(--serif)', fontSize: 18, fontStyle: 'italic', marginBottom: '0.5rem', lineHeight: 1.3 }}>
              {iss.title}
            </div>
            <div style={{ fontFamily: 'var(--prose)', fontSize: 14, color: 'var(--fg)', lineHeight: 1.6, opacity: 0.9, letterSpacing: '-0.01em' }}>{iss.explanation}</div>
            {onGenerateFix && (
              <button
                className="helios-btn"
                style={{ marginTop: '1rem', padding: '0.6rem 1.2rem' }}
                onClick={(e) => {
                  e.stopPropagation();
                  onGenerateFix(iss);
                }}
              >
                Generate fix →
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

'use client';

import { lineDiff } from '@/lib/api';
import { useMemo } from 'react';

type Props = {
  original: string;
  fixed: string;
  summary?: string;
  context?: number; // unchanged lines to show around hunks
};

export default function DiffView({ original, fixed, summary, context = 2 }: Props) {
  const lines = useMemo(() => lineDiff(original, fixed), [original, fixed]);

  // Collapse long runs of unchanged lines, keeping `context` around hunks.
  const visible: { line: typeof lines[number]; collapsed?: number }[] = [];
  let runStart = -1;
  for (let i = 0; i < lines.length; i++) {
    const isEq = lines[i].type === 'eq';
    if (isEq) {
      if (runStart === -1) runStart = i;
    } else {
      if (runStart !== -1) {
        const runLen = i - runStart;
        if (runLen <= context * 2) {
          for (let k = runStart; k < i; k++) visible.push({ line: lines[k] });
        } else {
          for (let k = runStart; k < runStart + context; k++) visible.push({ line: lines[k] });
          visible.push({ line: { type: 'eq', text: '' }, collapsed: runLen - context * 2 });
          for (let k = i - context; k < i; k++) visible.push({ line: lines[k] });
        }
        runStart = -1;
      }
      visible.push({ line: lines[i] });
    }
  }
  if (runStart !== -1) {
    const tail = Math.min(context, lines.length - runStart);
    for (let k = runStart; k < runStart + tail; k++) visible.push({ line: lines[k] });
    if (lines.length - runStart > tail) {
      visible.push({ line: { type: 'eq', text: '' }, collapsed: lines.length - runStart - tail });
    }
  }

  return (
    <div>
      <div className="code-surface" style={{ padding: '1rem 0' }}>
        {visible.map((v, idx) => {
          if (v.collapsed) {
            return (
              <div
                key={idx}
                style={{
                  padding: '0.4rem 1.5rem',
                  color: 'var(--dim)',
                  fontSize: 11,
                  fontStyle: 'italic',
                  borderTop: '1px dashed var(--line)',
                  borderBottom: '1px dashed var(--line)',
                  background: 'rgba(110, 119, 135, 0.03)',
                }}
              >
                ⋯ {v.collapsed} unchanged line{v.collapsed === 1 ? '' : 's'}
              </div>
            );
          }
          if (v.line.type === 'eq') {
            return (
              <span key={idx} className="code-line" style={{ color: 'var(--dim)' }}>
                {v.line.text || ' '}
              </span>
            );
          }
          return (
            <span key={idx} className={`diff-line ${v.line.type}`}>
              {v.line.text || ' '}
            </span>
          );
        })}
      </div>
      {summary && (
        <div style={{ marginTop: '1rem', color: 'var(--dim)', fontSize: 12, fontStyle: 'italic', lineHeight: 1.6 }}>
          {summary}
        </div>
      )}
    </div>
  );
}

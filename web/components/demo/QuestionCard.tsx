'use client';

import { useState } from 'react';
import type { DemoQuestion } from '@/lib/demo';
import { demoApi } from '@/lib/demo';

export default function QuestionCard({ question }: { question: DemoQuestion }) {
  const [picks, setPicks] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);

  function pick(qid: string, oid: string) {
    setPicks((p) => ({ ...p, [qid]: oid }));
  }

  async function submit() {
    if (Object.keys(picks).length < question.questions.length) return;
    await demoApi.answerQuestion(picks);
    setSubmitted(true);
  }

  return (
    <div className="helios-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <div style={{ textTransform: 'uppercase', letterSpacing: '0.12em', fontSize: 11, color: 'var(--sun)', marginBottom: '0.6rem' }}>
          {question.title}
        </div>
        <p style={{ fontFamily: 'var(--prose)', fontSize: 14, lineHeight: 1.7, opacity: 0.9, margin: 0 }}>
          {question.body}
        </p>
      </div>

      {question.questions.map((q, qi) => (
        <div key={q.id}>
          <div style={{ fontFamily: 'var(--serif)', fontStyle: 'italic', fontSize: 16, marginBottom: '0.75rem', lineHeight: 1.4 }}>
            {qi + 1}. {q.prompt}
          </div>
          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
            {q.options.map((o) => {
              const active = picks[q.id] === o.id;
              return (
                <button
                  key={o.id}
                  className={`helios-btn ${active ? 'primary' : ''}`}
                  onClick={() => pick(q.id, o.id)}
                  disabled={submitted}
                  style={{ padding: '0.5rem 1rem', fontSize: 13 }}
                >
                  {active ? '✓ ' : ''}{o.label}
                </button>
              );
            })}
          </div>
        </div>
      ))}

      <div style={{ borderTop: '1px solid var(--line)', paddingTop: '1rem', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        <button
          className="helios-btn primary"
          onClick={submit}
          disabled={submitted || Object.keys(picks).length < question.questions.length}
        >
          {submitted ? '✓ Captured to trace' : 'Submit answers'}
        </button>
        <div style={{ fontSize: 12, color: 'var(--dim)', fontStyle: 'italic', flex: 1, minWidth: 280 }}>
          {question.footer}
        </div>
      </div>
    </div>
  );
}

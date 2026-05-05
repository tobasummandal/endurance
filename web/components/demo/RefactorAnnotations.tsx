'use client';

import type { DemoFix } from '@/lib/demo';

export default function RefactorAnnotations({ fix }: { fix: DemoFix }) {
  return (
    <div className="helios-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <Group title="Refactor decisions" items={fix.refactor_decisions} />
      <Divider />
      <Group title="Bug fixes applied" items={fix.bug_fixes_applied} />
      <Divider />
      <Group title="Generated artifacts" items={fix.generated_artifacts} />
    </div>
  );
}

function Group({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <div style={{ textTransform: 'uppercase', letterSpacing: '0.12em', fontSize: 11, color: 'var(--dim)', marginBottom: '0.6rem' }}>
        {title}
      </div>
      <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
        {items.map((it, i) => (
          <li key={i} style={{ display: 'flex', gap: '0.6rem', fontSize: 13, lineHeight: 1.5 }}>
            <span style={{ color: 'var(--right, #6BAA75)' }}>✓</span>
            <span style={{ opacity: 0.9 }}>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Divider() {
  return <div style={{ borderTop: '1px solid var(--line)', opacity: 0.6 }} />;
}

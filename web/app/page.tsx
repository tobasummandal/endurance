'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import Reveal from '@/components/Reveal';
import { api } from '@/lib/api';

export default function ReviewerHome() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [code, setCode] = useState('');
  const [filename, setFilename] = useState('untitled.py');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startSession(name: string, source: string) {
    if (!source.trim()) {
      setError('source is empty');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const session = await api.createSession(name, source);
      router.push(`/session?id=${encodeURIComponent(session.id)}`);
    } catch (e: any) {
      setError(e?.message || String(e));
      setLoading(false);
    }
  }

  async function onFile(file: File) {
    const text = await file.text();
    setFilename(file.name);
    setCode(text);
    await startSession(file.name, text);
  }

  return (
    <section className="helios-section">
      <Reveal>
        <div className="section-tag">Reviewer</div>
      </Reveal>
      <Reveal delay={1}>
        <h1 className="helios-h" style={{ marginBottom: '2rem' }}>
          Audit your code.
        </h1>
      </Reveal>
      <Reveal delay={2}>
        <p style={{ fontFamily: 'var(--prose)', fontWeight: 300, fontSize: 17, color: 'var(--fg)', opacity: 0.9, maxWidth: 640, lineHeight: 1.6, letterSpacing: '-0.01em', marginBottom: '3rem' }}>
          Drop a Python file or paste code below. Helios catches the silent bugs &mdash; off-by-one, unit mismatch, numerical
          instability &mdash; rewrites them, proves the fix on sandboxed test cases, and flags GPU candidates. Three jobs, one tool.
        </p>
      </Reveal>

      <Reveal delay={2}>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <Link className="helios-btn primary" href="/demo" style={{ textDecoration: 'none' }}>
            ▶ Try the demo
          </Link>
          <Link className="helios-btn" href="/live" style={{ textDecoration: 'none' }}>
            ⚡ Live coding
          </Link>
          <button className="helios-btn primary" disabled={loading} onClick={() => fileInputRef.current?.click()}>
            {loading ? '◉ Creating session…' : '↑ Drop a .py file'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".py,text/x-python"
            style={{ display: 'none' }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onFile(f);
            }}
          />
          <button
            className="helios-btn"
            disabled={loading || !code.trim()}
            onClick={() => startSession(filename, code)}
          >
            ▶ Audit pasted code
          </button>
        </div>
      </Reveal>

      <Reveal delay={3}>
        <textarea
          className="code-surface"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="# paste Python here&#10;def your_function(...):&#10;    ..."
          spellCheck={false}
          style={{
            width: '100%',
            maxWidth: 900,
            minHeight: 280,
            padding: '1.25rem 1.5rem',
            color: 'var(--fg)',
            outline: 'none',
            resize: 'vertical',
          }}
        />
      </Reveal>

      {error && (
        <div className="verdict-banner red" style={{ marginTop: '1.5rem', maxWidth: 900 }}>
          <span>error</span>
          <span className="note">{error}</span>
        </div>
      )}
    </section>
  );
}

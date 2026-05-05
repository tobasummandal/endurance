'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import Reveal from '@/components/Reveal';
import { api } from '@/lib/api';

export default function SessionsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.listSessions(),
    refetchInterval: 5000,
  });

  return (
    <section className="helios-section">
      <Reveal>
        <div className="section-tag">Archive</div>
      </Reveal>
      <Reveal delay={1}>
        <h1 className="helios-h" style={{ marginBottom: '2rem' }}>
          Sessions.
        </h1>
      </Reveal>
      <Reveal delay={2}>
        <p style={{ fontFamily: 'var(--prose)', fontWeight: 300, fontSize: 15, color: 'var(--fg)', opacity: 0.85, maxWidth: 640, lineHeight: 1.6, letterSpacing: '-0.01em', marginBottom: '3rem' }}>
          Every session writes one row to the dataset of <em>(broken, fixed, proven)</em>. Nobody else has it.
        </p>
      </Reveal>

      <Reveal delay={2}>
        <div style={{ marginBottom: '2rem' }}>
          <Link href="/" className="helios-btn primary">
            + New session
          </Link>
        </div>
      </Reveal>

      {error && (
        <div className="verdict-banner red">
          <span>could not load sessions</span>
          <span className="note">{(error as Error).message}</span>
        </div>
      )}

      <Reveal delay={3}>
        {isLoading ? (
          <div style={{ color: 'var(--dim)', fontSize: 13 }}>loading…</div>
        ) : !data || data.length === 0 ? (
          <div className="helios-card" style={{ color: 'var(--dim)', fontSize: 13, lineHeight: 1.7 }}>
            No sessions yet. Start one from the home page.
          </div>
        ) : (
          <table className="helios-table">
            <thead>
              <tr>
                <th>filename</th>
                <th>status</th>
                <th>created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.map((s) => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 500 }}>{s.filename}</td>
                  <td>
                    <span
                      className="sev"
                      style={{
                        color: s.status === 'created' ? 'var(--dim)' : 'var(--sun)',
                      }}
                    >
                      {s.status}
                    </span>
                  </td>
                  <td style={{ color: 'var(--dim)' }}>
                    {new Date(s.created_at).toLocaleString()}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <Link href={`/session?id=${encodeURIComponent(s.id)}`} className="helios-btn" style={{ padding: '0.5rem 1rem', fontSize: 10 }}>
                      Open →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Reveal>
    </section>
  );
}

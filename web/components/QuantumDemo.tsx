'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '@/lib/api';
import type {
  QuantumAntigen,
  QuantumPriorityEntry,
  QuantumRejected,
  QuantumRouterResult,
  QuantumScheduleEntry,
} from '@/lib/types';

const ANTIGEN_COLOR: Record<QuantumAntigen, string> = {
  qaoa: '#E8A33D',
  vqe: '#f4c46b',
  grover: '#7FE0E0',
  qft: '#b48cff',
  classical: '#3a4658',
};

const ANTIGEN_LABEL: Record<QuantumAntigen, string> = {
  qaoa: 'QAOA',
  vqe: 'VQE',
  grover: 'Grover',
  qft: 'QFT/QPE',
  classical: 'classical',
};

// playback animation: real seconds shown per simulated second
const PLAYBACK_RATE = 8;

export default function QuantumDemo() {
  const [eta, setEta] = useState(5);
  const [debouncedEta, setDebouncedEta] = useState(5);
  // debounce slider so we don't hammer the backend
  useEffect(() => {
    const t = setTimeout(() => setDebouncedEta(eta), 120);
    return () => clearTimeout(t);
  }, [eta]);

  const q = useQuery({
    queryKey: ['quantum-router', debouncedEta],
    queryFn: () => api.quantumRouter(debouncedEta),
    staleTime: 60_000,
  });

  if (q.isLoading && !q.data) {
    return (
      <div className="helios-card" style={{ color: 'var(--dim)', fontSize: 13 }}>
        <span className="stage-dot active" /> Spinning up Immune-filter → ATC simulation…
      </div>
    );
  }
  if (q.error || !q.data) {
    return (
      <div className="verdict-banner red">
        <span>quantum router unavailable</span>
        <span className="note">{(q.error as Error)?.message ?? 'no data'}</span>
      </div>
    );
  }
  return <DemoBody data={q.data} eta={eta} setEta={setEta} fetching={q.isFetching} />;
}

function DemoBody({
  data,
  eta,
  setEta,
  fetching,
}: {
  data: QuantumRouterResult;
  eta: number;
  setEta: (v: number) => void;
  fetching: boolean;
}) {
  const [playing, setPlaying] = useState(false);
  const [t, setT] = useState(0); // simulated seconds elapsed in playback
  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number>(0);

  const totalSim = Math.max(data.fifo.total_s, data.atc.total_s);

  // playback driver
  useEffect(() => {
    if (!playing) return;
    startRef.current = performance.now() - (t * 1000) / PLAYBACK_RATE;
    const tick = (now: number) => {
      const elapsedSim = ((now - startRef.current) / 1000) * PLAYBACK_RATE;
      if (elapsedSim >= totalSim) {
        setT(totalSim);
        setPlaying(false);
        return;
      }
      setT(elapsedSim);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing]);

  // reset playback when eta changes (data reloads)
  useEffect(() => {
    setT(0);
    setPlaying(false);
  }, [data]);

  const meetTarget = data.atc.reduction_pct >= data.target_pct;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Headline + slider */}
      <div className="helios-card" style={{ padding: '1.1rem 1.2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.9rem' }}>
          <div style={{ fontSize: 11, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--dim)' }}>
            Hybrid Immune-filter → ATC
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
            <button
              className="helios-btn primary"
              onClick={() => {
                setT(0);
                setPlaying(true);
              }}
              disabled={playing}
            >
              {playing ? '◉ Running' : t >= totalSim && t > 0 ? '↻ Replay' : '▶ Run schedule'}
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <Stat label="tasks" value={String(data.params.n_tasks)} />
          <Stat label="FIFO baseline" value={`${data.fifo.total_s.toFixed(1)} s`} />
          <Stat
            label="Immune→ATC"
            value={`${data.atc.total_s.toFixed(1)} s`}
            tone="sun"
            note={fetching ? 're-solving…' : undefined}
          />
          <Stat
            label="reduction"
            value={`${data.atc.reduction_pct.toFixed(1)}%`}
            tone={meetTarget ? 'right' : 'wrong'}
            note={`target ≥ ${data.target_pct}%`}
          />
        </div>

        <div style={{ marginTop: '1rem', display: 'flex', gap: '0.9rem', alignItems: 'center' }}>
          <div style={{ fontSize: 11, color: 'var(--dim)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            quantum speedup&nbsp;η
          </div>
          <input
            type="range"
            min={1}
            max={20}
            step={0.5}
            value={eta}
            onChange={(e) => setEta(parseFloat(e.target.value))}
            style={{ flex: 1, accentColor: 'var(--sun)' }}
          />
          <div style={{ fontFamily: 'var(--mono)', fontSize: 13, minWidth: 52, textAlign: 'right' }}>
            {eta.toFixed(1)}×
          </div>
        </div>
        <div style={{ marginTop: '0.5rem', fontSize: 11, color: 'var(--dim)', fontStyle: 'italic' }}>
          gain is highly sensitive to assumed quantum speedup and per-dispatch overhead — drag the slider.
        </div>
      </div>

      {/* Dual Gantt race */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
        <LaneRow
          label="FIFO  ·  cpu only"
          totalSim={totalSim}
          totalLabel={`${data.fifo.total_s.toFixed(1)}s`}
          bars={data.fifo.schedule}
          t={t}
          dim
        />
        <LaneRow
          label="ATC  ·  cpu lane"
          totalSim={totalSim}
          totalLabel={`${data.atc.cpu_load_s.toFixed(1)}s`}
          bars={data.atc.cpu_schedule}
          t={t}
        />
        <LaneRow
          label="ATC  ·  qpu lane"
          totalSim={totalSim}
          totalLabel={`${data.atc.qpu_load_s.toFixed(1)}s`}
          bars={data.atc.qpu_schedule}
          t={t}
          accent
        />
      </div>

      {/* Two-column: priority queue + antigen filter */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '1rem' }}>
        <PriorityPanel queue={data.atc.priority_queue.slice(0, 10)} />
        <AntigenPanel rejected={data.atc.rejected} threshold={data.params.threshold} tasks={data.tasks} />
      </div>

      {/* Sensitivity strip */}
      <SensitivityStrip data={data} eta={eta} />
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
  note,
}: {
  label: string;
  value: string;
  tone?: 'sun' | 'right' | 'wrong';
  note?: string;
}) {
  const color =
    tone === 'sun' ? 'var(--sun)' : tone === 'right' ? 'var(--right)' : tone === 'wrong' ? 'var(--wrong)' : 'var(--fg)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--dim)' }}>
        {label}
      </span>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 22, color, lineHeight: 1.1 }}>{value}</span>
      {note && <span style={{ fontSize: 10, color: 'var(--dim)' }}>{note}</span>}
    </div>
  );
}

function LaneRow({
  label,
  totalSim,
  totalLabel,
  bars,
  t,
  dim,
  accent,
}: {
  label: string;
  totalSim: number;
  totalLabel: string;
  bars: QuantumScheduleEntry[];
  t: number;
  dim?: boolean;
  accent?: boolean;
}) {
  // pixel width is 100% of container; bars positioned proportionally to totalSim
  return (
    <div className="helios-card" style={{ padding: '0.7rem 0.9rem', opacity: dim ? 0.85 : 1 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.45rem' }}>
        <span style={{ fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: dim ? 'var(--dim)' : accent ? 'var(--right)' : 'var(--fg)' }}>
          {label}
        </span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--dim)' }}>{totalLabel}</span>
      </div>
      <div
        style={{
          position: 'relative',
          height: 28,
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid var(--line)',
          borderRadius: 3,
          overflow: 'hidden',
        }}
      >
        {bars.map((b) => {
          const left = (b.start / totalSim) * 100;
          const width = ((b.end - b.start) / totalSim) * 100;
          const filled = Math.max(0, Math.min(b.end, t) - b.start);
          const fillRatio = (b.end - b.start > 0) ? filled / (b.end - b.start) : 0;
          return (
            <div
              key={b.task_id + '-' + b.start}
              title={`${b.task_id} ${b.name} · ${b.start.toFixed(2)}–${b.end.toFixed(2)}s`}
              style={{
                position: 'absolute',
                left: `${left}%`,
                width: `${Math.max(width, 0.4)}%`,
                top: 0,
                bottom: 0,
                background: 'rgba(255,255,255,0.04)',
                borderRight: '1px solid rgba(0,0,0,0.4)',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: `${fillRatio * 100}%`,
                  background: ANTIGEN_COLOR[b.antigen],
                  opacity: dim ? 0.55 : 0.92,
                  transition: 'width 30ms linear',
                }}
              />
            </div>
          );
        })}
        {/* playhead */}
        <div
          style={{
            position: 'absolute',
            left: `${(Math.min(t, totalSim) / totalSim) * 100}%`,
            top: -2,
            bottom: -2,
            width: 1,
            background: 'var(--fg)',
            opacity: t > 0 && t < totalSim ? 0.55 : 0,
            pointerEvents: 'none',
          }}
        />
      </div>
    </div>
  );
}

function PriorityPanel({ queue }: { queue: QuantumPriorityEntry[] }) {
  return (
    <div className="helios-card" style={{ padding: '0.9rem 1rem' }}>
      <div className="section-tag" style={{ marginBottom: '0.7rem' }}>ATC priority queue · top 10</div>
      <table style={{ width: '100%', fontSize: 11.5, fontFamily: 'var(--mono)', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ color: 'var(--dim)', textAlign: 'left' }}>
            <th style={{ paddingBottom: 6 }}>task</th>
            <th style={{ paddingBottom: 6 }}>antigen</th>
            <th style={{ paddingBottom: 6 }}>lane</th>
            <th style={{ paddingBottom: 6, textAlign: 'right' }}>π</th>
          </tr>
        </thead>
        <tbody>
          {queue.map((q, i) => (
            <tr key={q.task_id + i} style={{ borderTop: '1px solid var(--line)' }}>
              <td style={{ padding: '5px 0', color: 'var(--fg)' }}>
                <span style={{ color: 'var(--dim)' }}>{q.task_id}</span>&nbsp;{q.name}
              </td>
              <td>
                <span
                  style={{
                    fontSize: 10,
                    padding: '2px 6px',
                    borderRadius: 2,
                    background: ANTIGEN_COLOR[q.antigen],
                    color: q.antigen === 'classical' ? 'var(--fg)' : '#0c1118',
                    letterSpacing: '0.06em',
                  }}
                >
                  {ANTIGEN_LABEL[q.antigen]}
                </span>
              </td>
              <td style={{ color: q.lane === 'qpu' ? 'var(--right)' : 'var(--dim)', textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.12em' }}>
                {q.lane}
              </td>
              <td style={{ textAlign: 'right', color: 'var(--sun)' }}>{q.pi.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: '0.6rem', fontSize: 10, color: 'var(--dim)', fontStyle: 'italic', lineHeight: 1.5 }}>
        π = (w/p)·exp(-max(d−p−t, 0) / k·p̄)  ·  Vepsalainen & Morton 1987
      </div>
    </div>
  );
}

function AntigenPanel({
  rejected,
  threshold,
  tasks,
}: {
  rejected: QuantumRejected[];
  threshold: number;
  tasks: QuantumRouterResult['tasks'];
}) {
  // surface a few high-affinity passes alongside the rejects
  const passes = useMemo(
    () =>
      tasks
        .filter((t) => t.antigen !== 'classical' && t.affinity >= threshold)
        .sort((a, b) => b.affinity - a.affinity)
        .slice(0, 4),
    [tasks, threshold],
  );
  return (
    <div className="helios-card" style={{ padding: '0.9rem 1rem' }}>
      <div className="section-tag" style={{ marginBottom: '0.7rem' }}>Immune filter · antigen match</div>
      <table style={{ width: '100%', fontSize: 11.5, fontFamily: 'var(--mono)', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ color: 'var(--dim)', textAlign: 'left' }}>
            <th style={{ paddingBottom: 6 }}>task</th>
            <th style={{ paddingBottom: 6 }}>antigen</th>
            <th style={{ paddingBottom: 6, textAlign: 'right' }}>affinity</th>
            <th style={{ paddingBottom: 6, textAlign: 'right' }}>verdict</th>
          </tr>
        </thead>
        <tbody>
          {passes.map((t) => (
            <tr key={t.id} style={{ borderTop: '1px solid var(--line)' }}>
              <td style={{ padding: '5px 0' }}>
                <span style={{ color: 'var(--dim)' }}>{t.id}</span>&nbsp;{t.name}
              </td>
              <td>
                <span
                  style={{
                    fontSize: 10, padding: '2px 6px', borderRadius: 2,
                    background: ANTIGEN_COLOR[t.antigen], color: '#0c1118', letterSpacing: '0.06em',
                  }}
                >
                  {ANTIGEN_LABEL[t.antigen]}
                </span>
              </td>
              <td style={{ textAlign: 'right' }}>{t.affinity.toFixed(2)}</td>
              <td style={{ textAlign: 'right', color: 'var(--right)', letterSpacing: '0.12em' }}>✓ pass</td>
            </tr>
          ))}
          {rejected.map((r) => (
            <tr key={r.task_id} style={{ borderTop: '1px solid var(--line)' }}>
              <td style={{ padding: '5px 0' }}>
                <span style={{ color: 'var(--dim)' }}>{r.task_id}</span>&nbsp;{r.name}
              </td>
              <td>
                <span
                  style={{
                    fontSize: 10, padding: '2px 6px', borderRadius: 2,
                    background: 'rgba(233, 79, 55, 0.18)', color: 'var(--wrong)', letterSpacing: '0.06em',
                  }}
                >
                  {ANTIGEN_LABEL[r.antigen]}
                </span>
              </td>
              <td style={{ textAlign: 'right' }}>{r.affinity.toFixed(2)}</td>
              <td style={{ textAlign: 'right', color: 'var(--wrong)', letterSpacing: '0.12em' }}>✗ reject</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: '0.6rem', fontSize: 10, color: 'var(--dim)', fontStyle: 'italic', lineHeight: 1.5 }}>
        threshold = {threshold.toFixed(2)} cosine affinity vs antigen library (QAOA / VQE / Grover / QFT signatures)
      </div>
    </div>
  );
}

function SensitivityStrip({ data, eta }: { data: QuantumRouterResult; eta: number }) {
  // sparkline: reduction% across the sweep, with current eta marker
  const w = 100;
  const h = 28;
  const xs = data.sensitivity.map((s) => s.eta);
  const ys = data.sensitivity.map((s) => s.reduction_pct);
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const ymin = Math.min(...ys, 0), ymax = Math.max(...ys, 1);
  const norm = (x: number, lo: number, hi: number) => (hi === lo ? 0 : (x - lo) / (hi - lo));
  // log-scale x for eta
  const lx = (x: number) => norm(Math.log(x), Math.log(xmin), Math.log(xmax));
  const path = data.sensitivity
    .map((s, i) => `${i === 0 ? 'M' : 'L'} ${lx(s.eta) * w} ${h - norm(s.reduction_pct, ymin, ymax) * h}`)
    .join(' ');
  const cx = lx(Math.max(xmin, Math.min(xmax, eta))) * w;
  return (
    <div className="helios-card" style={{ padding: '0.8rem 1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--dim)' }}>
          sensitivity sweep · reduction% vs η
        </span>
        <span style={{ fontSize: 11, color: 'var(--dim)' }}>
          η ∈ [{xmin}×, {xmax}×]
        </span>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ width: '100%', height: 60, display: 'block' }}>
        <path d={path} fill="none" stroke="var(--sun)" strokeWidth={1.2} />
        {data.sensitivity.map((s, i) => (
          <circle
            key={i}
            cx={lx(s.eta) * w}
            cy={h - norm(s.reduction_pct, ymin, ymax) * h}
            r={0.9}
            fill="var(--sun-warm)"
          />
        ))}
        <line x1={cx} x2={cx} y1={0} y2={h} stroke="var(--right)" strokeWidth={0.6} strokeDasharray="1.5 1.5" />
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--dim)', marginTop: 4 }}>
        {data.sensitivity.filter((_, i) => i % 2 === 0).map((s) => (
          <span key={s.eta}>
            {s.eta}× · {s.reduction_pct.toFixed(0)}%
          </span>
        ))}
      </div>
    </div>
  );
}

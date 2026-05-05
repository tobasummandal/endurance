import type { Fix, Issue, QuantumRouterResult, RouteResult, Session, Verification } from './types';

const API_BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let body = '';
    try {
      body = JSON.stringify(await res.json());
    } catch {
      body = await res.text();
    }
    throw new Error(`${res.status} ${path} — ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  createSession: (filename: string, source_code: string) =>
    request<Session>('/sessions', {
      method: 'POST',
      body: JSON.stringify({ filename, source_code }),
    }),

  listSessions: () => request<Session[]>('/sessions'),

  getSession: (id: string) => request<Session>(`/sessions/${id}`),

  audit: (sessionId: string) =>
    request<Issue[]>(`/sessions/${sessionId}/audit`, { method: 'POST' }),

  listIssues: (sessionId: string) =>
    request<Issue[]>(`/sessions/${sessionId}/issues`),

  generateFix: (sessionId: string, issueId: string) =>
    request<Fix>(`/sessions/${sessionId}/issues/${issueId}/fix`, { method: 'POST' }),

  verify: (sessionId: string, fixId: string) =>
    request<Verification>(`/sessions/${sessionId}/fixes/${fixId}/verify`, { method: 'POST' }),

  route: (sessionId: string) =>
    request<RouteResult>(`/sessions/${sessionId}/route`, { method: 'POST' }),

  quantumRouter: (eta: number) =>
    request<QuantumRouterResult>(`/quantum-router?eta=${eta}`),
};

// LCS-based line diff for visual rendering
export type DiffLine = { type: 'del' | 'add' | 'eq'; text: string };

export function lineDiff(orig: string, fixed: string): DiffLine[] {
  const a = orig.split('\n');
  const b = fixed.split('\n');
  const m = a.length;
  const n = b.length;
  const dp = Array.from({ length: m + 1 }, () => new Int32Array(n + 1));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const out: DiffLine[] = [];
  let i = 0;
  let j = 0;
  while (i < m && j < n) {
    if (a[i] === b[j]) {
      out.push({ type: 'eq', text: a[i] });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      out.push({ type: 'del', text: a[i++] });
    } else {
      out.push({ type: 'add', text: b[j++] });
    }
  }
  while (i < m) out.push({ type: 'del', text: a[i++] });
  while (j < n) out.push({ type: 'add', text: b[j++] });
  return out;
}

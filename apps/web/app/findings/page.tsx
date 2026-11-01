'use client';

import { useCallback, useEffect, useState } from 'react';
import { Card } from '../../components/Card';
import { PageHeader } from '../../components/PageHeader';
import {
  clearStoredToken,
  fetchDashboardFindings,
  fetchFindingAnalysis,
  getStoredToken,
  loginAnalyst,
  runFindingAnalysis,
  type DashboardFinding,
  type FindingAnalysis,
} from '../../lib/dashboard-api';

const DEMO_USER = 'demo';
const DEMO_PASSWORD = 'claimguard-demo!';

export default function FindingsPage() {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState(DEMO_USER);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [findings, setFindings] = useState<DashboardFinding[]>([]);
  const [analysisById, setAnalysisById] = useState<Record<string, FindingAnalysis>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredToken());
  }, []);

  const loadFindings = useCallback(async () => {
    setLoadError(null);
    try {
      const rows = await fetchDashboardFindings();
      setFindings(rows);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : 'Failed to load findings');
      setFindings([]);
    }
  }, []);

  useEffect(() => {
    if (token) loadFindings();
  }, [token, loadFindings]);

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoginError(null);
    try {
      await loginAnalyst(username, password);
      setToken(getStoredToken());
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : 'Login failed');
    }
  }

  function onLogout() {
    clearStoredToken();
    setToken(null);
    setFindings([]);
  }

  async function onAnalyze(id: string) {
    setBusyId(id);
    try {
      const result = await runFindingAnalysis(id);
      setAnalysisById((prev) => ({ ...prev, [id]: result }));
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setBusyId(null);
    }
  }

  async function onShowCached(id: string) {
    try {
      const cached = await fetchFindingAnalysis(id);
      if (cached) setAnalysisById((prev) => ({ ...prev, [id]: cached }));
    } catch {
      /* ignore */
    }
  }

  return (
    <main className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="AI findings (demo)"
        description="Seeded payer-rule findings with optional Ollama explanations (administrative only, clinical guards active)."
      />

      {!token ? (
        <Card>
          <h2 className="font-semibold text-text">Sign in</h2>
          <p className="mt-1 text-sm text-text-muted">
            After <code className="font-mono text-xs">python scripts/seed.py</code> use demo
            credentials below. Requires Postgres + migrations +{' '}
            <code className="font-mono text-xs">CLAIMGUARD_JWT_SECRET</code> in apps/api/.env.
          </p>
          <form onSubmit={onLogin} className="mt-4 max-w-sm space-y-3">
            <label className="block text-sm">
              Username
              <input
                name="username"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 w-full rounded-xl border border-border px-3 py-2"
              />
            </label>
            <label className="block text-sm">
              Password
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-xl border border-border px-3 py-2"
              />
            </label>
            {loginError && <p className="text-sm text-critical">{loginError}</p>}
            <button
              type="submit"
              className="cursor-pointer rounded-2xl bg-primary px-4 py-2 text-sm font-medium text-on-primary"
            >
              Sign in
            </button>
          </form>
        </Card>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-text-muted">Signed in as {username}</p>
            <button
              type="button"
              onClick={onLogout}
              className="rounded-xl bg-surface px-3 py-1.5 text-sm shadow-float"
            >
              Sign out
            </button>
          </div>
          {loadError && (
            <Card className="border-critical/30">
              <p className="text-sm text-critical">{loadError}</p>
            </Card>
          )}
          {findings.length === 0 && !loadError ? (
            <Card>
              <p className="text-sm text-text-muted">
                No findings in database. Run{' '}
                <code className="font-mono text-xs">python scripts/seed.py</code> from apps/api.
              </p>
            </Card>
          ) : (
            <ul className="space-y-4">
              {findings.map((f) => (
                <li key={f.id}>
                  <Card>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-medium text-text">{f.title}</p>
                        <p className="mt-1 text-xs text-text-muted">
                          {f.ruleId} · {f.severity} · {f.detectedAt.slice(0, 10)}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          disabled={busyId === f.id}
                          onClick={() => onAnalyze(f.id)}
                          className="rounded-xl bg-primary px-3 py-1.5 text-xs font-medium text-on-primary disabled:opacity-50"
                        >
                          {busyId === f.id ? 'Analyzing…' : 'Run AI explain'}
                        </button>
                        <button
                          type="button"
                          onClick={() => onShowCached(f.id)}
                          className="rounded-xl bg-surface px-3 py-1.5 text-xs shadow-float"
                        >
                          Load saved
                        </button>
                      </div>
                    </div>
                    {f.description && (
                      <p className="mt-2 text-sm text-text-muted">{f.description}</p>
                    )}
                    {analysisById[f.id] && (
                      <div className="mt-4 rounded-2xl bg-surface-muted p-4 text-sm">
                        <p className="font-medium text-text">Explanation</p>
                        <p className="mt-1 text-text-muted">{analysisById[f.id].explanation}</p>
                        <p className="mt-3 font-medium text-text">Suggested fix</p>
                        <p className="mt-1 text-text-muted">{analysisById[f.id].suggestedFix}</p>
                      </div>
                    )}
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </main>
  );
}

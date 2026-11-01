'use client';

import { Card, StatCard } from '../../components/Card';
import { PageHeader } from '../../components/PageHeader';
import { fetchBenchmarkSplit, type BenchmarkSplit } from '../../lib/phase1-api';
import { useEffect, useState } from 'react';

type SplitMetrics = BenchmarkSplit;

export default function EvaluationPage() {
  const [validation, setValidation] = useState<SplitMetrics | null>(null);
  const [development, setDevelopment] = useState<SplitMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchBenchmarkSplit('validation'),
      fetchBenchmarkSplit('development'),
    ])
      .then(([v, d]) => {
        setValidation(v);
        setDevelopment(d);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load metrics'));
  }, []);

  return (
    <main className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="Detection quality (Phase 2)"
        description="Benchmark on the teaching validation split (50 claims, 750 claim–rule pairs). Full report: docs/evaluation/EVALUATION_REPORT.md"
      />

      {error && (
        <Card className="border-critical/30">
          <p className="text-sm text-critical">{error}</p>
          <p className="mt-2 text-xs text-text-muted">
            Regenerate: cd apps/api && python scripts/make_eval_report.py
          </p>
        </Card>
      )}

      {validation && (
        <Card>
          <h2 className="text-lg font-semibold text-text">Validation split (challenge hold-out)</h2>
          <p className="mt-1 text-sm text-text-muted">
            {validation.n_claims} claims · {validation.n_pairs} pairs · claim exact match{' '}
            {validation.claim_exact_match}/{validation.n_claims}
          </p>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Macro F1"
              value={validation.macro_f1?.toFixed(3) ?? '—'}
              sub="Across rule categories"
            />
            <StatCard
              label="Issue F1 (micro)"
              value={validation.micro.f1?.toFixed(3) ?? '—'}
            />
            <StatCard
              label="False-alarm rate"
              value={validation.micro.false_alarm_rate?.toFixed(3) ?? '—'}
            />
            <StatCard
              label="Latency p95"
              value={`${validation.latency_ms.p95?.toFixed(2) ?? '—'} ms`}
              sub={`p50 ${validation.latency_ms.p50?.toFixed(2) ?? '—'} ms`}
            />
          </div>
          <div className="mt-6 overflow-x-auto scrollbar-subtle">
            <table className="min-w-[640px] w-full text-left text-sm">
              <thead>
                <tr className="bg-surface-muted text-xs text-text-faint">
                  <th className="px-4 py-2">Rule</th>
                  <th className="px-4 py-2">F1</th>
                  <th className="px-4 py-2">Precision</th>
                  <th className="px-4 py-2">Recall</th>
                  <th className="px-4 py-2">False alarm</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(validation.per_rule ?? {})
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([ruleId, m]) => (
                    <tr key={ruleId} className="border-t border-border">
                      <td className="px-4 py-2 font-mono">{ruleId}</td>
                      <td className="px-4 py-2">{fmt(m.f1)}</td>
                      <td className="px-4 py-2">{fmt(m.precision)}</td>
                      <td className="px-4 py-2">{fmt(m.recall)}</td>
                      <td className="px-4 py-2">{fmt(m.false_alarm_rate)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {development && (
        <Card>
          <h2 className="font-semibold text-text">Development split (tuning — not generalisation proof)</h2>
          <p className="mt-2 text-sm text-text-muted">
            Macro F1 {development.macro_f1?.toFixed(3)} · false-alarm{' '}
            {development.micro.false_alarm_rate?.toFixed(3)} · {development.n_claims} claims
          </p>
        </Card>
      )}
    </main>
  );
}

function fmt(v: number | null | undefined): string {
  if (v == null) return '—';
  return v.toFixed(3);
}

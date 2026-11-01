'use client';

import { useEffect, useState } from 'react';
import { AuditTrailPanel } from '../../components/AuditTrailPanel';
import { Card } from '../../components/Card';
import { PageHeader } from '../../components/PageHeader';
import {
  downloadCsv,
  downloadJson,
  fetchHumanFeedbackExport,
} from '../../lib/dashboard-api';
import { verifyAuditChain } from '../../lib/phase1-api';

type Decision = {
  action: string;
  claim_id: string;
  rule_id: string;
  reason: string;
  recorded_at?: string;
};

export default function AuditPage() {
  const [chain, setChain] = useState<{ valid: boolean; events: number } | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);

  useEffect(() => {
    verifyAuditChain()
      .then(setChain)
      .catch(() => setChain(null));
    fetchHumanFeedbackExport().then(setDecisions);
  }, []);

  function refreshFeedback() {
    fetchHumanFeedbackExport().then(setDecisions);
  }

  return (
    <main className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Audit & active learning"
        description="Verify the hash-chained ledger, export human overrides for retraining, and inspect recent decisions."
      />
      {chain && (
        <Card>
          <p className="text-sm">
            Global chain:{' '}
            <strong className={chain.valid ? 'text-success' : 'text-critical'}>
              {chain.valid ? 'valid' : 'invalid'}
            </strong>{' '}
            · {chain.events} events
          </p>
          <p className="mt-2 text-xs text-text-muted">
            Bonus: tamper-evident audit log — each event links to the previous hash (see API{' '}
            <code className="font-mono">/v1/audit/verify</code>).
          </p>
        </Card>
      )}
      <AuditTrailPanel claimId={null} />
      <Card>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="font-semibold text-text">Human overrides (active learning export)</h2>
            <p className="mt-1 text-sm text-text-muted">
              Reviewer decisions from the validate flow are appended to the audit log. Download for
              offline retraining or analytics.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={refreshFeedback}
              className="rounded-xl bg-surface px-3 py-1.5 text-sm shadow-float"
            >
              Refresh
            </button>
            <button
              type="button"
              disabled={decisions.length === 0}
              onClick={() =>
                downloadJson(`claimguard-review-feedback-${Date.now()}.json`, {
                  exported_at: new Date().toISOString(),
                  decisions,
                })
              }
              className="rounded-xl bg-primary px-3 py-1.5 text-sm text-on-primary disabled:opacity-50"
            >
              Download JSON
            </button>
            <button
              type="button"
              disabled={decisions.length === 0}
              onClick={() => downloadCsv(`claimguard-review-feedback-${Date.now()}.csv`, decisions)}
              className="rounded-xl bg-primary px-3 py-1.5 text-sm text-on-primary disabled:opacity-50"
            >
              Download CSV
            </button>
          </div>
        </div>
        {decisions.length === 0 ? (
          <p className="mt-4 text-sm text-text-muted">
            No overrides yet. On <strong>Validate claim</strong>, submit a reviewer action (set{' '}
            <code className="font-mono text-xs">NEXT_PUBLIC_REVIEWER_API_KEY</code> in web env).
          </p>
        ) : (
          <ul className="mt-4 max-h-64 space-y-2 overflow-auto text-sm scrollbar-subtle">
            {decisions.slice(-20).reverse().map((d, i) => (
              <li key={`${d.claim_id}-${d.rule_id}-${i}`} className="rounded-xl bg-surface-muted px-3 py-2">
                <span className="font-mono font-medium">{d.claim_id}</span> · {d.rule_id} ·{' '}
                <span className="text-primary">{d.action}</span>
                <p className="mt-1 text-text-muted">{d.reason}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </main>
  );
}

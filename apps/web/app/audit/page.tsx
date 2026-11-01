'use client';

import { useEffect, useState } from 'react';
import { AuditTrailPanel } from '../../components/AuditTrailPanel';
import { Card } from '../../components/Card';
import { PageHeader } from '../../components/PageHeader';
import { fetchHumanFeedback, verifyAuditChain } from '../../lib/phase1-api';

export default function AuditPage() {
  const [chain, setChain] = useState<{ valid: boolean; events: number } | null>(null);
  const [decisions, setDecisions] = useState<
    { action: string; claim_id: string; rule_id: string; reason: string }[]
  >([]);

  useEffect(() => {
    verifyAuditChain()
      .then(setChain)
      .catch(() => setChain(null));
    fetchHumanFeedback().then(setDecisions);
  }, []);

  return (
    <main className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Audit & active learning"
        description="Verify the hash-chained ledger and inspect human override feedback used to improve routing."
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
        </Card>
      )}
      <AuditTrailPanel claimId={null} />
      <Card>
        <h2 className="font-semibold text-text">Recent human overrides (feedback loop)</h2>
        <p className="mt-1 text-sm text-text-muted">
          Exported from the audit log for active-learning pipelines.
        </p>
        {decisions.length === 0 ? (
          <p className="mt-4 text-sm text-text-muted">No human overrides recorded yet.</p>
        ) : (
          <ul className="mt-4 space-y-2 text-sm">
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

'use client';

import { useCallback, useEffect, useState } from 'react';
import { Card } from './Card';
import { fetchAuditTrace, verifyAuditChain, type AuditTraceEvent } from '../lib/phase1-api';

function eventLabel(event: Record<string, unknown>): string {
  if (typeof event.type === 'string') return event.type;
  if (typeof event.action === 'string') return `REVIEW:${event.action}`;
  return 'event';
}

type Props = {
  claimId: string | null;
  refreshToken?: number;
};

export function AuditTrailPanel({ claimId, refreshToken = 0 }: Props) {
  const [events, setEvents] = useState<AuditTraceEvent[]>([]);
  const [chain, setChain] = useState<{ valid: boolean; events: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const verify = await verifyAuditChain();
      setChain(verify);
      if (claimId) {
        setEvents(await fetchAuditTrace(claimId));
      } else {
        setEvents([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Audit load failed');
    } finally {
      setLoading(false);
    }
  }, [claimId]);

  useEffect(() => {
    load();
  }, [load, refreshToken]);

  return (
    <Card>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text">Cryptographic audit trail</h2>
          <p className="mt-1 text-sm text-text-muted">
            Hash-chained log of validation runs and human decisions for this claim.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="rounded-2xl bg-surface px-4 py-2 text-sm font-medium text-text-muted shadow-float hover:text-text disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {chain && (
        <p
          className={`mt-4 rounded-2xl px-4 py-2 text-sm ${
            chain.valid ? 'bg-success/10 text-success' : 'bg-critical/10 text-critical'
          }`}
        >
          Chain verify: {chain.valid ? 'valid' : 'broken'} · {chain.events} total events in log
        </p>
      )}

      {error && (
        <p className="mt-4 text-sm text-critical" role="alert">
          {error}
        </p>
      )}

      {!claimId ? (
        <p className="mt-4 text-sm text-text-faint">Run validation to attach audit events to a claim.</p>
      ) : loading ? (
        <p className="mt-4 text-sm text-text-muted">Loading trace…</p>
      ) : events.length === 0 ? (
        <p className="mt-4 text-sm text-text-muted">No audit events yet for {claimId}.</p>
      ) : (
        <ol className="mt-4 max-h-72 space-y-2 overflow-auto text-sm scrollbar-subtle">
          {events.map((row) => (
            <li
              key={row.sequence}
              className="rounded-xl border border-border bg-surface-muted/50 px-3 py-2 font-mono text-[11px]"
            >
              <span className="text-text-faint">#{row.sequence}</span>{' '}
              <span className="font-semibold text-primary">{eventLabel(row.event)}</span>{' '}
              <span className="text-text-muted">{row.recorded_at}</span>
              <pre className="mt-1 whitespace-pre-wrap text-text-muted">
                {JSON.stringify(row.event, null, 2)}
              </pre>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

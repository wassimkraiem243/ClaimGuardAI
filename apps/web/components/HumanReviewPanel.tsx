'use client';

import { useState } from 'react';
import { Card } from './Card';
import {
  reviewerKeyConfigured,
  submitReviewDecision,
  type ReviewAction,
  type ReviewQueueItem,
  type RouteReviewResponse,
  type RuleResultRow,
} from '../lib/phase1-api';

const ACTIONS: { id: ReviewAction; label: string; hint: string }[] = [
  { id: 'confirm_issue', label: 'Confirm issue', hint: 'Agree with the automated finding' },
  { id: 'dismiss_with_reason', label: 'Dismiss', hint: 'Override: not an issue (logged for audit)' },
  { id: 'request_information', label: 'Request info', hint: 'Route back for missing documentation' },
  { id: 'mark_corrected_for_recheck', label: 'Mark corrected', hint: 'Claim was fixed; schedule re-validation' },
];

type Props = {
  routing: RouteReviewResponse | null;
  resultsByRule: Map<string, RuleResultRow>;
  onDecisionRecorded: () => void;
};

export function HumanReviewPanel({ routing, resultsByRule, onDecisionRecorded }: Props) {
  const [busyRule, setBusyRule] = useState<string | null>(null);
  const [reasonByRule, setReasonByRule] = useState<Record<string, string>>({});
  const [recorded, setRecorded] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  if (!routing) return null;

  const queue = routing.queue.filter((q) => !recorded.has(q.rule_id));

  return (
    <Card id="human-review" className="border border-high/20 scroll-mt-24">
      <h2 className="text-lg font-semibold text-text">Human-in-the-loop review</h2>
      <p className="mt-1 text-sm text-text-muted">
        Low-confidence or high-severity items are routed for explicit reviewer approval. Decisions are
        hash-chained in the audit log.
      </p>

      {routing.escalation_required && (
        <div
          className="mt-4 rounded-2xl border border-high/30 bg-high/10 px-4 py-3 text-sm text-high"
          role="status"
        >
          <p className="font-semibold">Escalation: {routing.escalation_priority}</p>
          <ul className="mt-2 list-disc pl-5">
            {routing.escalation_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {!reviewerKeyConfigured() && (
        <p className="mt-4 rounded-2xl bg-surface-muted px-4 py-3 text-sm text-text-muted">
          Set <code className="font-mono text-xs">NEXT_PUBLIC_REVIEWER_API_KEY</code> to match{' '}
          <code className="font-mono text-xs">REVIEWER_KEYS</code> on the API to submit overrides.
        </p>
      )}

      {error && (
        <p className="mt-4 text-sm text-critical" role="alert">
          {error}
        </p>
      )}

      {queue.length === 0 ? (
        <p className="mt-4 text-sm text-success">No pending review items for this claim.</p>
      ) : (
        <ul className="mt-6 space-y-4">
          {queue.map((item) => (
            <ReviewRow
              key={item.rule_id}
              item={item}
              finding={resultsByRule.get(item.rule_id)}
              busy={busyRule === item.rule_id}
              reason={reasonByRule[item.rule_id] ?? ''}
              onReasonChange={(v) =>
                setReasonByRule((prev) => ({ ...prev, [item.rule_id]: v }))
              }
              onSubmit={async (action) => {
                const reason = (reasonByRule[item.rule_id] ?? '').trim();
                if (reason.length < 3) {
                  setError('Provide a short reason (min 3 characters) for the audit trail.');
                  return;
                }
                setError(null);
                setBusyRule(item.rule_id);
                try {
                  const finding = resultsByRule.get(item.rule_id);
                  await submitReviewDecision({
                    claim_id: item.claim_id,
                    rule_id: item.rule_id,
                    action,
                    reason,
                    original_status: item.status,
                    finding,
                  });
                  setRecorded((prev) => new Set(prev).add(item.rule_id));
                  onDecisionRecorded();
                } catch (e) {
                  setError(e instanceof Error ? e.message : 'Decision failed');
                } finally {
                  setBusyRule(null);
                }
              }}
            />
          ))}
        </ul>
      )}
    </Card>
  );
}

function ReviewRow({
  item,
  finding,
  busy,
  reason,
  onReasonChange,
  onSubmit,
}: {
  item: ReviewQueueItem;
  finding?: RuleResultRow;
  busy: boolean;
  reason: string;
  onReasonChange: (v: string) => void;
  onSubmit: (action: ReviewAction) => void;
}) {
  return (
    <li className="rounded-2xl border border-border bg-surface-muted/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-mono font-semibold text-text">
            {item.rule_id}{' '}
            <span className="text-xs font-normal text-text-muted">({item.priority} priority)</span>
          </p>
          <p className="mt-1 text-sm text-text-muted">{item.explanation}</p>
        </div>
        <span className="rounded-pill bg-high/15 px-3 py-1 text-xs font-semibold text-high">
          {item.status} · {item.severity}
        </span>
      </div>
      {finding?.evidence && finding.evidence.length > 0 && (
        <details className="mt-3 text-xs">
          <summary className="cursor-pointer font-medium text-primary">Rule-linked evidence</summary>
          <pre className="mt-2 max-h-32 overflow-auto rounded-xl bg-surface p-2 font-mono text-[11px] scrollbar-subtle">
            {JSON.stringify(finding.evidence, null, 2)}
          </pre>
        </details>
      )}
      <label className="mt-3 block text-sm">
        <span className="font-medium text-text">Reviewer rationale (audited)</span>
        <textarea
          value={reason}
          onChange={(e) => onReasonChange(e.target.value)}
          rows={2}
          className="mt-1 w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          placeholder="Why you confirm, dismiss, or request more information…"
        />
      </label>
      <div className="mt-3 flex flex-wrap gap-2">
        {ACTIONS.map((a) => (
          <button
            key={a.id}
            type="button"
            disabled={busy || !reviewerKeyConfigured()}
            title={a.hint}
            onClick={() => onSubmit(a.id)}
            className="rounded-xl bg-primary px-3 py-1.5 text-xs font-medium text-on-primary disabled:opacity-50"
          >
            {a.label}
          </button>
        ))}
      </div>
    </li>
  );
}

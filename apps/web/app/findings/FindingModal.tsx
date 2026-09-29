'use client';

import { useEffect, useState } from 'react';
import type { UnifiedFindingDto } from '@claimguard/shared-types';
import { SeverityBadge } from '../../components/SeverityBadge';
import {
  getCachedAnalysis,
  loadFindingAnalysis,
  type FindingAnalysis,
} from '../../lib/analysis-cache';

interface FindingModalProps {
  finding: UnifiedFindingDto | null;
  onClose: () => void;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export default function FindingModal({ finding, onClose }: FindingModalProps) {
  const [analysis, setAnalysis] = useState<FindingAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!finding) return;
    const findingId = finding.id;
    let cancelled = false;

    const cached = getCachedAnalysis(findingId);
    if (cached) {
      setAnalysis(cached);
      setLoading(false);
      setError(null);
      return;
    }

    setAnalysis(null);
    setError(null);
    setLoading(true);

    loadFindingAnalysis(findingId)
      .then((result) => {
        if (!cancelled) {
          setAnalysis(result);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) setError('Could not load analysis for this finding.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [finding?.id]);

  useEffect(() => {
    if (!finding) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [finding, onClose]);

  if (!finding) return null;

  const ruleLabel = finding.ruleId ?? finding.cveId ?? finding.cweId ?? '—';
  const location = finding.filePath
    ? `${finding.filePath}${finding.lineStart ? `:${finding.lineStart}` : ''}`
    : '—';

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-0 sm:items-center sm:p-6"
      onClick={onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="finding-modal-title"
        className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-t-[28px] bg-surface shadow-float-lg sm:max-h-[85vh] sm:rounded-[28px]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 px-6 pb-4 pt-6">
          <div className="min-w-0">
            <h2 id="finding-modal-title" className="text-xl font-bold leading-snug" title={finding.title}>
              {finding.title}
            </h2>
            <p className="mt-1 text-sm text-text-muted">
              {finding.tool} · {finding.category}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="shrink-0 cursor-pointer rounded-2xl bg-surface-muted p-2.5 text-text-muted hover:text-text"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <div className="scrollbar-subtle flex-1 space-y-5 overflow-y-auto px-6 pb-6">
          <div className="flex flex-wrap items-center gap-3">
            <SeverityBadge severity={finding.severity} />
            <span className="rounded-xl bg-surface-muted px-3 py-1 text-xs text-text-muted">
              {formatDate(finding.detectedAt)}
            </span>
          </div>

          <dl className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl bg-surface-muted p-4">
              <dt className="text-xs font-medium text-text-faint">File</dt>
              <dd className="mt-1 break-all font-mono text-sm text-text-muted">{location}</dd>
            </div>
            <div className="rounded-2xl bg-surface-muted p-4">
              <dt className="text-xs font-medium text-text-faint">Rule / CVE</dt>
              <dd className="mt-1 text-sm text-text-muted">{ruleLabel}</dd>
            </div>
          </dl>

          {finding.description && (
            <div className="rounded-2xl bg-surface-muted p-4">
              <p className="text-xs font-medium text-text-faint">Description</p>
              <p className="mt-2 text-sm leading-relaxed text-text-muted">{finding.description}</p>
            </div>
          )}

          <section className="rounded-2xl bg-primary-subtle p-5">
            <h3 className="font-semibold text-text">Review</h3>
            {loading && <p className="mt-3 text-sm text-text-muted">Loading review…</p>}
            {error && <p className="mt-3 text-sm text-critical">{error}</p>}
            {analysis && (
              <div className="mt-4 space-y-4 text-sm">
                <div className="rounded-2xl bg-surface p-4 shadow-float">
                  <p className="font-medium">What this means</p>
                  <p className="mt-1.5 leading-relaxed text-text-muted">{analysis.explanation}</p>
                </div>
                <div className="rounded-2xl bg-surface p-4 shadow-float">
                  <p className="font-medium">Suggested fix</p>
                  <p className="mt-1.5 leading-relaxed text-text-muted">{analysis.suggestedFix}</p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <div className="rounded-2xl bg-surface px-4 py-3 shadow-float">
                    <p className="text-xs text-text-faint">Priority</p>
                    <p className="mt-1 font-medium">{analysis.priority}</p>
                  </div>
                  <div className="rounded-2xl bg-surface px-4 py-3 shadow-float">
                    <p className="text-xs text-text-faint">Confidence</p>
                    <p className="mt-1 font-medium">{analysis.confidence}</p>
                  </div>
                </div>
                {analysis.isLikelyFalsePositive && (
                  <div className="rounded-2xl bg-surface p-4 shadow-float">
                    <p className="font-medium text-medium">Possible false positive</p>
                    {analysis.falsePositiveReasoning && (
                      <p className="mt-1.5 text-text-muted">{analysis.falsePositiveReasoning}</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

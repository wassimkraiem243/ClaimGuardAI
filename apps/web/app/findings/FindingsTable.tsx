'use client';

import { useState } from 'react';
import type { UnifiedFindingDto } from '@claimguard/shared-types';
import { SeverityBadge } from '../../components/SeverityBadge';
import FindingModal from './FindingModal';

interface FindingsTableProps {
  findings: UnifiedFindingDto[];
}

/** Fixed grid: flexible title/location/rule + fixed category, date, severity */
const DESKTOP_COLS =
  'minmax(0,2.2fr) 3.75rem minmax(0,2fr) minmax(0,1fr) 10.75rem 5.25rem';

function formatLocation(finding: UnifiedFindingDto) {
  const path = finding.filePath ?? '—';
  return finding.lineStart ? `${path}:${finding.lineStart}` : path;
}

function formatRule(finding: UnifiedFindingDto) {
  return finding.ruleId ?? finding.cveId ?? finding.cweId ?? '—';
}

function formatDate(value: string) {
  return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export default function FindingsTable({ findings }: FindingsTableProps) {
  const [selectedFinding, setSelectedFinding] = useState<UnifiedFindingDto | null>(null);

  if (findings.length === 0) {
    return (
      <div className="px-6 py-16 text-center">
        <p className="font-semibold text-text">No findings match this filter</p>
        <p className="mt-1 text-sm text-text-muted">Try a different severity filter.</p>
      </div>
    );
  }

  return (
    <>
      <div className="hidden lg:block">
        <div
          className="grid items-center gap-x-4 px-5 py-3 text-xs font-medium text-text-faint"
          style={{ gridTemplateColumns: DESKTOP_COLS }}
        >
          <span>Title</span>
          <span>Category</span>
          <span>Location</span>
          <span>Rule / CVE</span>
          <span>Detected</span>
          <span className="text-center">Severity</span>
        </div>

        {findings.map((finding) => (
          <div
            key={finding.id}
            role="button"
            tabIndex={0}
            onClick={() => setSelectedFinding(finding)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setSelectedFinding(finding);
              }
            }}
            className="grid cursor-pointer items-center gap-x-4 px-5 py-4 text-sm transition-colors hover:bg-primary-subtle"
            style={{ gridTemplateColumns: DESKTOP_COLS }}
          >
            <div className="min-w-0">
              <p className="line-clamp-2 font-medium leading-snug">{finding.title}</p>
              <p className="mt-0.5 truncate text-xs text-text-faint">{finding.tool}</p>
            </div>

            <p className="truncate text-text-muted">{finding.category}</p>

            <p
              className="truncate font-mono text-xs text-text-muted"
              title={formatLocation(finding)}
            >
              {formatLocation(finding)}
            </p>

            <p className="truncate text-text-muted" title={formatRule(finding)}>
              {formatRule(finding)}
            </p>

            <p className="whitespace-nowrap text-text-faint">{formatDate(finding.detectedAt)}</p>

            <div className="flex justify-center">
              <SeverityBadge severity={finding.severity} />
            </div>
          </div>
        ))}
      </div>

      <ul className="lg:hidden">
        {findings.map((finding) => (
          <li key={finding.id}>
            <button
              type="button"
              onClick={() => setSelectedFinding(finding)}
              className="w-full px-5 py-4 text-left transition-colors hover:bg-primary-subtle"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium leading-snug">{finding.title}</p>
                  <p className="mt-1 text-xs text-text-faint">{finding.tool}</p>
                </div>
                <SeverityBadge severity={finding.severity} className="shrink-0" />
              </div>
              <p className="mt-2 text-sm text-text-muted">{finding.category}</p>
              <p className="mt-1 truncate font-mono text-xs text-text-faint">{formatLocation(finding)}</p>
            </button>
          </li>
        ))}
      </ul>

      <FindingModal finding={selectedFinding} onClose={() => setSelectedFinding(null)} />
    </>
  );
}

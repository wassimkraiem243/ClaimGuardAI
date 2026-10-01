const STATUS_STYLES: Record<string, string> = {
  PASS: 'bg-success/15 text-success',
  FAIL: 'bg-critical/15 text-critical',
  UNABLE_TO_ASSESS: 'bg-medium/15 text-high',
  NOT_APPLICABLE: 'bg-surface-muted text-text-muted',
  WARN: 'bg-medium/15 text-medium',
};

export function RuleStatusBadge({ status, className = '' }: { status: string; className?: string }) {
  const key = status.toUpperCase();
  return (
    <span
      className={`inline-flex items-center rounded-pill px-3 py-1 text-xs font-semibold ${
        STATUS_STYLES[key] ?? 'bg-surface-muted text-text-muted'
      } ${className}`}
    >
      {status}
    </span>
  );
}

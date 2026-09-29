const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: 'bg-critical/15 text-critical',
  HIGH: 'bg-high/15 text-high',
  MEDIUM: 'bg-medium/15 text-medium',
  LOW: 'bg-low/15 text-low',
  INFO: 'bg-info/15 text-info',
  UNKNOWN: 'bg-surface-muted text-text-muted',
};

export function SeverityBadge({ severity, className = '' }: { severity: string; className?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-pill px-3 py-1 text-xs font-semibold ${
        SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.UNKNOWN
      } ${className}`}
    >
      {severity}
    </span>
  );
}

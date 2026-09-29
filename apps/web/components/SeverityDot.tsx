const DOT_COLORS: Record<string, string> = {
  CRITICAL: 'bg-critical',
  HIGH: 'bg-high',
  MEDIUM: 'bg-medium',
  LOW: 'bg-low',
  INFO: 'bg-info',
  UNKNOWN: 'bg-border-strong',
};

export function SeverityDot({ severity }: { severity: string }) {
  return <span className={`h-2 w-2 shrink-0 rounded-full ${DOT_COLORS[severity] ?? DOT_COLORS.UNKNOWN}`} />;
}
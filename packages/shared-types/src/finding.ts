export enum Severity {
  CRITICAL = 'CRITICAL',
  HIGH = 'HIGH',
  MEDIUM = 'MEDIUM',
  LOW = 'LOW',
  INFO = 'INFO',
  UNKNOWN = 'UNKNOWN',
}

export enum ScanTool {
  GITLEAKS = 'GITLEAKS',
  SEMGREP = 'SEMGREP',
  TRIVY = 'TRIVY',
  OWASP_ZAP = 'OWASP_ZAP',
}

export enum FindingCategory {
  SECRET = 'SECRET',
  SAST = 'SAST',
  SCA = 'SCA',
  CONTAINER = 'CONTAINER',
  DAST = 'DAST',
}

export interface FindingDto {
  id: string;
  scanExecutionId: string;
  fingerprint: string;
  title: string;
  description?: string | null;
  severity: Severity;
  category?: FindingCategory | null;
  rawSeverity?: string | null;
  ruleId?: string | null;
  filePath?: string | null;
  lineStart?: number | null;
  lineEnd?: number | null;
  cveId?: string | null;
  cweId?: string | null;
  packageName?: string | null;
  packageVersion?: string | null;
  fixedVersion?: string | null;
  recommendation?: string | null;
  evidence?: string | null;
  references?: string[] | null;
  metadata?: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface MetricsSnapshotDto {
  totalFindings: number;
  bySeverity: Record<Severity, number>;
}

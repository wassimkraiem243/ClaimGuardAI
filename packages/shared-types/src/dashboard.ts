import { FindingCategory, Severity } from './finding';
import { PipelineRunStatus } from './pipeline-run';

export interface ScanSummaryDto {
  tool: string;
  scanLabel: string;
  status: string;
  findingsCount: number;
  finishedAt?: string | null;
}

export interface DashboardOverviewDto {
  project: {
    id: string;
    slug: string;
    name: string;
  };
  hasData: boolean;
  lastReceivedAt?: string | null;
  latestPipelineRun?: {
    id: string;
    externalId?: string | null;
    status: PipelineRunStatus;
    branch?: string | null;
    commitSha?: string | null;
    finishedAt?: string | null;
  } | null;
  metrics: {
    totalFindings: number;
    bySeverity: Record<Severity, number>;
    byCategory: Record<FindingCategory, number>;
  };
  scans: ScanSummaryDto[];
}

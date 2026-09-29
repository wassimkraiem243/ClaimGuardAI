import { FindingCategory, ScanTool, Severity } from './finding';

/**
 * Minimal cross-tool finding shape.
 * Only fields useful for dashboard display and AI analysis.
 * Tool-specific fields are optional when not present in every scanner.
 */
export interface UnifiedFindingDto {
  id: string;
  tool: ScanTool;
  category: FindingCategory;
  severity: Severity;
  title: string;
  description?: string | null;
  filePath?: string | null;
  lineStart?: number | null;
  lineEnd?: number | null;
  ruleId?: string | null;
  cveId?: string | null;
  cweId?: string | null;
  packageName?: string | null;
  fixedVersion?: string | null;
  recommendation?: string | null;
  detectedAt: string;
}

/** Extended shape for AI export only. */
export interface AiFindingDto extends UnifiedFindingDto {
  narrative: string;
}

export interface AiFindingsExportDto {
  projectSlug: string;
  pipelineRunId?: string | null;
  generatedAt: string;
  summary: {
    totalFindings: number;
    bySeverity: Record<Severity, number>;
    byCategory: Record<FindingCategory, number>;
    byTool: Record<string, number>;
  };
  findings: AiFindingDto[];
}

from dataclasses import dataclass
from datetime import datetime

from app.db.models import Finding, ScanExecution


@dataclass
class FindingContext:
    finding: Finding
    tool: str
    scan_label: str
    pipeline_run_id: str
    project_id: str


def to_unified_finding(ctx: FindingContext) -> dict:
    f = ctx.finding
    return {
        "id": f.id,
        "tool": ctx.tool,
        "category": f.category or "SAST",
        "severity": f.severity,
        "title": f.title,
        "description": f.description,
        "filePath": f.filePath,
        "lineStart": f.lineStart,
        "lineEnd": f.lineEnd,
        "ruleId": f.ruleId,
        "cveId": f.cveId,
        "cweId": f.cweId,
        "packageName": f.packageName,
        "fixedVersion": f.fixedVersion,
        "recommendation": f.recommendation,
        "detectedAt": f.createdAt.isoformat(),
    }


def build_ai_narrative(ctx: FindingContext) -> str:
    f = ctx.finding
    parts = [f"{ctx.tool} [{f.category}] {f.severity}: {f.title}"]
    if f.filePath:
        line = f":{f.lineStart}" if f.lineStart else ""
        parts.append(f"at {f.filePath}{line}")
    if f.packageName:
        fix = f" fix: {f.fixedVersion}" if f.fixedVersion else ""
        parts.append(f"package {f.packageName}{fix}")
    if f.cveId:
        parts.append(f"CVE {f.cveId}")
    if f.recommendation:
        parts.append(f"Fix: {f.recommendation}")
    return ". ".join(parts)


def finding_context_from_row(finding: Finding, scan: ScanExecution) -> FindingContext:
    return FindingContext(
        finding=finding,
        tool=scan.tool,
        scan_label=scan.scanLabel,
        pipeline_run_id=scan.pipelineRunId,
        project_id=scan.pipelineRun.projectId,
    )

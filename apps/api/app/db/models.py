from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "Project"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String, unique=True)
    repository: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime)
    updatedAt: Mapped[datetime] = mapped_column(DateTime)

    pipelineRuns: Mapped[list["PipelineRun"]] = relationship(back_populates="project")


class PipelineRun(Base):
    __tablename__ = "PipelineRun"
    __table_args__ = (UniqueConstraint("projectId", "externalId"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    projectId: Mapped[str] = mapped_column(ForeignKey("Project.id", ondelete="CASCADE"))
    externalId: Mapped[str | None] = mapped_column(String, nullable=True)
    branch: Mapped[str | None] = mapped_column(String, nullable=True)
    commitSha: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)
    startedAt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finishedAt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime)
    updatedAt: Mapped[datetime] = mapped_column(DateTime)

    project: Mapped[Project] = relationship(back_populates="pipelineRuns")
    scanExecutions: Mapped[list["ScanExecution"]] = relationship(
        back_populates="pipelineRun"
    )


class ScanExecution(Base):
    __tablename__ = "ScanExecution"
    __table_args__ = (UniqueConstraint("pipelineRunId", "tool", "scanLabel"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    pipelineRunId: Mapped[str] = mapped_column(
        ForeignKey("PipelineRun.id", ondelete="CASCADE")
    )
    tool: Mapped[str] = mapped_column(String)
    scanLabel: Mapped[str] = mapped_column(String, default="default")
    status: Mapped[str] = mapped_column(String)
    rawReportPath: Mapped[str | None] = mapped_column(String, nullable=True)
    startedAt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finishedAt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime)
    updatedAt: Mapped[datetime] = mapped_column(DateTime)

    pipelineRun: Mapped[PipelineRun] = relationship(back_populates="scanExecutions")
    findings: Mapped[list["Finding"]] = relationship(back_populates="scanExecution")


class Finding(Base):
    __tablename__ = "Finding"
    __table_args__ = (UniqueConstraint("scanExecutionId", "fingerprint"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    scanExecutionId: Mapped[str] = mapped_column(
        ForeignKey("ScanExecution.id", ondelete="CASCADE")
    )
    fingerprint: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    rawSeverity: Mapped[str | None] = mapped_column(String, nullable=True)
    ruleId: Mapped[str | None] = mapped_column(String, nullable=True)
    filePath: Mapped[str | None] = mapped_column(String, nullable=True)
    lineStart: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lineEnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cveId: Mapped[str | None] = mapped_column(String, nullable=True)
    cweId: Mapped[str | None] = mapped_column(String, nullable=True)
    packageName: Mapped[str | None] = mapped_column(String, nullable=True)
    packageVersion: Mapped[str | None] = mapped_column(String, nullable=True)
    fixedVersion: Mapped[str | None] = mapped_column(String, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime)
    updatedAt: Mapped[datetime] = mapped_column(DateTime)

    scanExecution: Mapped[ScanExecution] = relationship(back_populates="findings")
    analysis: Mapped["FindingAnalysis | None"] = relationship(
        back_populates="finding", uselist=False
    )


class FindingAnalysis(Base):
    __tablename__ = "FindingAnalysis"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    findingId: Mapped[str] = mapped_column(
        ForeignKey("Finding.id", ondelete="CASCADE"), unique=True
    )
    explanation: Mapped[str] = mapped_column(Text)
    suggestedFix: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String)
    confidence: Mapped[str] = mapped_column(String)
    isLikelyFalsePositive: Mapped[bool] = mapped_column(Boolean, default=False)
    falsePositiveReasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    groundingSource: Mapped[str] = mapped_column(String)
    modelUsed: Mapped[str] = mapped_column(String)
    promptTokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    responseTimeMs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    errorMessage: Mapped[str | None] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime)
    updatedAt: Mapped[datetime] = mapped_column(DateTime)

    finding: Mapped[Finding] = relationship(back_populates="analysis")

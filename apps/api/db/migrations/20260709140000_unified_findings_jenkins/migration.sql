-- CreateEnum
CREATE TYPE "FindingCategory" AS ENUM ('SECRET', 'SAST', 'SCA', 'CONTAINER', 'DAST');

-- AlterTable
ALTER TABLE "ScanExecution" ADD COLUMN "scanLabel" TEXT NOT NULL DEFAULT 'default';

-- AlterTable
ALTER TABLE "Finding" ADD COLUMN "category" "FindingCategory",
ADD COLUMN "rawSeverity" TEXT,
ADD COLUMN "cweId" TEXT,
ADD COLUMN "packageName" TEXT,
ADD COLUMN "packageVersion" TEXT,
ADD COLUMN "fixedVersion" TEXT,
ADD COLUMN "recommendation" TEXT,
ADD COLUMN "evidence" TEXT,
ADD COLUMN "references" JSONB;

-- CreateIndex
CREATE INDEX "Finding_category_idx" ON "Finding"("category");

-- CreateIndex
CREATE UNIQUE INDEX "ScanExecution_pipelineRunId_tool_scanLabel_key" ON "ScanExecution"("pipelineRunId", "tool", "scanLabel");

-- CreateIndex
CREATE UNIQUE INDEX "PipelineRun_projectId_externalId_key" ON "PipelineRun"("projectId", "externalId");

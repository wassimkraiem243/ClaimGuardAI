CREATE EXTENSION IF NOT EXISTS vector;

-- CreateTable
CREATE TABLE "CveCache" (
    "id" TEXT NOT NULL,
    "cveId" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "cvssScore" DOUBLE PRECISION,
    "severity" TEXT,
    "cweIds" TEXT[],
    "fixedVersion" TEXT,
    "references" TEXT[],
    "fetchedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "CveCache_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "KnowledgeChunk" (
    "id" TEXT NOT NULL,
    "source" TEXT NOT NULL,
    "category" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "embedding" vector(768) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "KnowledgeChunk_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Analysis" (
    "id" TEXT NOT NULL,
    "pipelineRunId" TEXT NOT NULL,
    "summary" TEXT NOT NULL,
    "riskScore" INTEGER NOT NULL,
    "topIssues" JSONB NOT NULL,
    "likelyFalsePositives" JSONB NOT NULL,
    "modelUsed" TEXT NOT NULL,
    "promptTokens" INTEGER,
    "responseTimeMs" INTEGER,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "errorMessage" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Analysis_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "CveCache_cveId_key" ON "CveCache"("cveId");

-- CreateIndex
CREATE UNIQUE INDEX "Analysis_pipelineRunId_key" ON "Analysis"("pipelineRunId");

-- AddForeignKey
ALTER TABLE "Analysis" ADD CONSTRAINT "Analysis_pipelineRunId_fkey" FOREIGN KEY ("pipelineRunId") REFERENCES "PipelineRun"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- CreateTable
CREATE TABLE "FindingAnalysis" (
    "id" TEXT NOT NULL,
    "findingId" TEXT NOT NULL,
    "explanation" TEXT NOT NULL,
    "suggestedFix" TEXT NOT NULL,
    "priority" TEXT NOT NULL,
    "confidence" TEXT NOT NULL,
    "isLikelyFalsePositive" BOOLEAN NOT NULL DEFAULT false,
    "falsePositiveReasoning" TEXT,
    "groundingSource" TEXT NOT NULL,
    "modelUsed" TEXT NOT NULL,
    "promptTokens" INTEGER,
    "responseTimeMs" INTEGER,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "errorMessage" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "FindingAnalysis_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "FindingAnalysis_findingId_key" ON "FindingAnalysis"("findingId");

-- AddForeignKey
ALTER TABLE "FindingAnalysis" ADD CONSTRAINT "FindingAnalysis_findingId_fkey" FOREIGN KEY ("findingId") REFERENCES "Finding"("id") ON DELETE CASCADE ON UPDATE CASCADE;

import { apiClient } from './api-client';

export type FindingAnalysis = {
  findingId: string;
  status: string;
  explanation: string;
  suggestedFix: string;
  priority: string;
  confidence: string;
  isLikelyFalsePositive: boolean;
  falsePositiveReasoning: string | null;
  groundingSource: string;
  modelUsed: string;
  responseTimeMs: number;
};

const completed = new Map<string, FindingAnalysis>();
const inflight = new Map<string, Promise<FindingAnalysis>>();

export function getCachedAnalysis(findingId: string): FindingAnalysis | null {
  return completed.get(findingId) ?? null;
}

export function loadFindingAnalysis(findingId: string): Promise<FindingAnalysis> {
  const cached = completed.get(findingId);
  if (cached) return Promise.resolve(cached);

  const pending = inflight.get(findingId);
  if (pending) return pending;

  const promise = (async () => {
    try {
      const result = await apiClient.getFindingAnalysis(findingId);
      completed.set(findingId, result);
      return result;
    } catch {
      const result = await apiClient.analyzeFinding(findingId);
      completed.set(findingId, result);
      return result;
    }
  })();

  inflight.set(findingId, promise);

  return promise.finally(() => {
    inflight.delete(findingId);
  });
}

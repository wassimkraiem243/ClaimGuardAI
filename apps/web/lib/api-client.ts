import type { DashboardOverviewDto, PipelineRunDto, UnifiedFindingDto } from '@claimguard/shared-types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:4001';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? 'dev-local-key';
const DEFAULT_PROJECT_SLUG =
  process.env.NEXT_PUBLIC_PROJECT_SLUG ?? 'claimguard-demo';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY,
      ...init?.headers,
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  getOverview(projectSlug = DEFAULT_PROJECT_SLUG, pipelineRunId?: string) {
    const search = new URLSearchParams({ projectSlug });
    if (pipelineRunId) search.set('pipelineRunId', pipelineRunId);
    return apiFetch<DashboardOverviewDto>(`/dashboard/overview?${search}`);
  },
  getPipelineRuns(projectSlug = DEFAULT_PROJECT_SLUG) {
    return apiFetch<PipelineRunDto[]>(
      `/dashboard/pipeline-runs?projectSlug=${encodeURIComponent(projectSlug)}`,
    );
  },
  getMetrics(projectId?: string, pipelineRunId?: string) {
    const search = new URLSearchParams();
    if (projectId) search.set('projectId', projectId);
    if (pipelineRunId) search.set('pipelineRunId', pipelineRunId);
    const query = search.toString();
    return apiFetch(`/metrics${query ? `?${query}` : ''}`);
  },
  getFindings(params?: {
    projectId?: string;
    pipelineRunId?: string;
    severity?: string;
    category?: string;
    limit?: number;
    offset?: number;
  }) {
    const search = new URLSearchParams();
    if (params?.projectId) search.set('projectId', params.projectId);
    if (params?.pipelineRunId) search.set('pipelineRunId', params.pipelineRunId);
    if (params?.severity) search.set('severity', params.severity);
    if (params?.category) search.set('category', params.category);
    if (params?.limit) search.set('limit', String(params.limit));
    if (params?.offset) search.set('offset', String(params.offset));
      
    const query = search.toString();
    return apiFetch<UnifiedFindingDto[]>(
      `/findings${query ? `?${query}` : ''}`,
    );
  },
  
    getFindingAnalysis(findingId: string) {
    return apiFetch<{
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
    }>(
      `/analysis/findings/${findingId}`,
    );
  },

  analyzeFinding(findingId: string) {
    return apiFetch<{
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
    }>(
      `/analysis/findings/${findingId}`,
      {
        method: 'POST',
      },
    );
  },
};


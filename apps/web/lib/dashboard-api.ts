/**
 * JWT-authenticated dashboard API (findings + LLM analysis).
 * Uses the same /api proxy as phase1-api in the browser.
 */

const TOKEN_KEY = 'claimguard_jwt';

function getApiBase(): string {
  if (typeof window !== 'undefined') return '/api';
  const env = process.env.NEXT_PUBLIC_API_URL?.trim();
  return env?.replace(/\/$/, '') || 'http://127.0.0.1:4001';
}

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function clearStoredToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

export async function loginAnalyst(username: string, password: string): Promise<void> {
  const body = new URLSearchParams({ username, password, grant_type: 'password' });
  let response: Response;
  try {
    response = await fetch(`${getApiBase()}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
  } catch {
    throw new Error(
      'Cannot reach the API (connection failed). Is npm run dev running? Check the [api] terminal on port 4001.',
    );
  }
  if (!response.ok) {
    const text = await response.text();
    if (text.includes('database_unavailable')) {
      throw new Error(
        'Database unavailable. Run: docker compose up -d, then python scripts/apply_migrations.py and scripts/seed.py',
      );
    }
    if (text.includes('jwt_not_configured') || text.includes('CLAIMGUARD_JWT_SECRET')) {
      throw new Error(
        'Set CLAIMGUARD_JWT_SECRET (32+ characters) in apps/api/.env and restart npm run dev.',
      );
    }
    throw new Error(text.includes('detail') ? 'Invalid username or password' : text.slice(0, 200));
  }
  const data = (await response.json()) as { access_token: string };
  sessionStorage.setItem(TOKEN_KEY, data.access_token);
}

function authHeaders(): HeadersInit {
  const token = getStoredToken();
  if (!token) throw new Error('Not signed in');
  return { Authorization: `Bearer ${token}` };
}

export type DashboardFinding = {
  id: string;
  tool: string;
  category: string;
  severity: string;
  title: string;
  description?: string | null;
  ruleId?: string | null;
  recommendation?: string | null;
  detectedAt: string;
};

export async function fetchDashboardFindings(): Promise<DashboardFinding[]> {
  const response = await fetch(`${getApiBase()}/findings`, { headers: authHeaders() });
  if (!response.ok) {
    throw new Error(`Findings failed (${response.status}): ${await response.text()}`);
  }
  return response.json() as Promise<DashboardFinding[]>;
}

export type FindingAnalysis = {
  explanation: string;
  suggestedFix: string;
  priority: string;
  confidence: string;
  isLikelyFalsePositive: boolean;
  falsePositiveReasoning?: string | null;
  modelUsed?: string;
  status?: string;
};

export async function fetchFindingAnalysis(findingId: string): Promise<FindingAnalysis | null> {
  const response = await fetch(`${getApiBase()}/analysis/findings/${encodeURIComponent(findingId)}`, {
    headers: authHeaders(),
  });
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`Analysis fetch failed (${response.status})`);
  }
  return response.json() as Promise<FindingAnalysis>;
}

export async function runFindingAnalysis(findingId: string): Promise<FindingAnalysis> {
  const response = await fetch(`${getApiBase()}/analysis/findings/${encodeURIComponent(findingId)}`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `Analysis failed (${response.status}). Is Ollama running? ${text.slice(0, 300)}`,
    );
  }
  return response.json() as Promise<FindingAnalysis>;
}

export async function fetchHumanFeedbackExport(): Promise<
  { action: string; claim_id: string; rule_id: string; reason: string; recorded_at?: string }[]
> {
  const response = await fetch(`${getApiBase()}/v1/audit/feedback?limit=500`, {
    headers: { 'x-api-key': process.env.NEXT_PUBLIC_API_KEY ?? 'dev-local-key' },
  });
  if (!response.ok) return [];
  const body = (await response.json()) as { decisions: Record<string, string>[] };
  return body.decisions as {
    action: string;
    claim_id: string;
    rule_id: string;
    reason: string;
    recorded_at?: string;
  }[];
}

export function downloadJson(filename: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadCsv(filename: string, rows: Record<string, string | undefined>[]): void {
  if (rows.length === 0) return;
  const keys = Object.keys(rows[0]);
  const escape = (v: string) => `"${v.replace(/"/g, '""')}"`;
  const lines = [
    keys.join(','),
    ...rows.map((r) => keys.map((k) => escape(String(r[k] ?? ''))).join(',')),
  ];
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

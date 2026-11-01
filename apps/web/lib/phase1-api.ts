function resolveApiBase(): string {
  const env = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (env) return env.replace(/\/$/, '');
  if (typeof window !== 'undefined') return '/api';
  return 'http://127.0.0.1:4001';
}

const API_BASE_URL = resolveApiBase();

/** WebSocket must hit the API directly (Next rewrites do not upgrade WS). */
function wsApiOrigin(): string {
  const env = process.env.NEXT_PUBLIC_API_URL?.trim();
  const http = env || 'http://127.0.0.1:4001';
  return http.replace(/\/$/, '').replace(/^http/, 'ws');
}
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? 'dev-local-key';
const REVIEWER_API_KEY = process.env.NEXT_PUBLIC_REVIEWER_API_KEY ?? '';

export type NormalizedClaim = {
  envelope: Record<string, unknown>;
  source: string;
  ingestion_warnings: string[];
};

export type EvidenceItem = { path: string; value: unknown };

export type RuleResultRow = {
  claim_id: string;
  rule_id: string;
  rule_version?: string;
  status: string;
  severity: string;
  affected_line_ids?: string[];
  evidence?: EvidenceItem[];
  rule_source?: string;
  explanation: string;
  corrective_action: string;
  confidence?: number | null;
  confidence_kind?: string;
  requires_human_review: boolean;
  method?: string;
  review_status?: string;
};

export type ValidationResponse = {
  claim_id: string;
  results: RuleResultRow[];
  run: {
    run_id: string;
    input_hash: string;
    policy_id: string;
    duration_ms: number;
  };
};

export type RuleCatalogEntry = {
  rule_id: string;
  title: string;
  severity: string;
  version: string;
  source?: string;
  logic?: string;
  corrective_action?: string;
};

export type ReviewQueueItem = {
  claim_id: string;
  rule_id: string;
  status: string;
  severity: string;
  requires_human_review: boolean;
  explanation: string;
  corrective_action: string;
  priority: 'medium' | 'high';
};

export type RouteReviewResponse = {
  claim_id: string;
  escalation_required: boolean;
  escalation_priority: 'none' | 'medium' | 'high';
  escalation_reasons: string[];
  queue: ReviewQueueItem[];
};

export type ReviewAction =
  | 'confirm_issue'
  | 'dismiss_with_reason'
  | 'request_information'
  | 'mark_corrected_for_recheck';

export type AuditTraceEvent = {
  sequence: number;
  recorded_at: string;
  event: Record<string, unknown>;
  hash?: string;
};

function formatIngestDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (!detail || typeof detail !== 'object') return JSON.stringify(detail);
  const d = detail as Record<string, unknown>;
  if (d.event === 'INGESTION_REJECTED' || d.reason) {
    const parts = [String(d.reason ?? d.event ?? 'Ingestion rejected')];
    if (d.field_path) parts.push(`(${d.field_path})`);
    if (d.claim_id) parts.push(`claim: ${d.claim_id}`);
    return parts.join(' ');
  }
  return JSON.stringify(detail, null, 2);
}

async function readError(response: Response): Promise<string> {
  const text = await response.text();
  if (!text.trim()) {
    return `${response.status} ${response.statusText || 'Error'}`.trim();
  }
  try {
    const body = JSON.parse(text) as { detail?: unknown; message?: string };
    if (body?.detail !== undefined) {
      return formatIngestDetail(body.detail);
    }
    if (body?.message) {
      return String(body.message);
    }
    return text.length > 2000 ? `${text.slice(0, 2000)}…` : text;
  } catch {
    return text.length > 2000 ? `${text.slice(0, 2000)}…` : text;
  }
}

function apiHeaders(reviewer = false): HeadersInit {
  const key = reviewer && REVIEWER_API_KEY ? REVIEWER_API_KEY : API_KEY;
  return { 'x-api-key': key };
}

export async function ingestClaimFile(file: File): Promise<NormalizedClaim[]> {
  const form = new FormData();
  form.append('file', file);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/claims/ingest`, {
      method: 'POST',
      headers: apiHeaders(),
      body: form,
    });
  } catch (networkErr) {
    const hint =
      networkErr instanceof Error ? networkErr.message : String(networkErr);
    throw new Error(
      `Cannot reach the API (${API_BASE_URL}). Start the backend with npm run dev:api from the repo root. ${hint}`,
    );
  }
  if (!response.ok) {
    throw new Error(`Ingest failed (${response.status}): ${await readError(response)}`);
  }
  return response.json() as Promise<NormalizedClaim[]>;
}

export async function validateClaimEnvelope(
  claim: Record<string, unknown>,
): Promise<ValidationResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/validate`, {
    method: 'POST',
    headers: {
      ...apiHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ claim }),
  });
  if (!response.ok) {
    throw new Error(`Validate failed (${response.status}): ${await readError(response)}`);
  }
  return response.json() as Promise<ValidationResponse>;
}

/** WebSocket validation: streams one message per rule, then complete. */
export function validateClaimStreaming(
  claim: Record<string, unknown>,
  handlers: {
    onRule: (row: RuleResultRow) => void;
    onComplete: (response: ValidationResponse) => void;
    onError: (message: string) => void;
  },
): () => void {
  const url = `${wsApiOrigin()}/v1/ws/validate?api_key=${encodeURIComponent(API_KEY)}`;
  const ws = new WebSocket(url);
  let closed = false;

  ws.onopen = () => {
    ws.send(JSON.stringify({ claim }));
  };
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(String(ev.data)) as {
        type: string;
        result?: RuleResultRow;
        response?: ValidationResponse;
        message?: string;
      };
      if (msg.type === 'rule' && msg.result) handlers.onRule(msg.result);
      if (msg.type === 'complete' && msg.response) handlers.onComplete(msg.response);
      if (msg.type === 'error') handlers.onError(msg.message ?? 'Validation error');
    } catch {
      handlers.onError('Invalid WebSocket message');
    }
  };
  ws.onerror = () => handlers.onError('WebSocket connection failed');
  ws.onclose = () => {
    closed = true;
  };

  return () => {
    if (!closed) ws.close();
  };
}

export async function routeReview(claim: Record<string, unknown>): Promise<RouteReviewResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/reviews/route`, {
    method: 'POST',
    headers: {
      ...apiHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ claim }),
  });
  if (!response.ok) {
    throw new Error(`Review routing failed (${response.status}): ${await readError(response)}`);
  }
  return response.json() as Promise<RouteReviewResponse>;
}

export async function submitReviewDecision(input: {
  claim_id: string;
  rule_id: string;
  action: ReviewAction;
  reason: string;
  original_status: string;
  finding?: RuleResultRow;
}): Promise<{ recorded: boolean; audit_seq: number }> {
  if (!REVIEWER_API_KEY) {
    throw new Error(
      'Reviewer key not configured. Set NEXT_PUBLIC_REVIEWER_API_KEY (matches REVIEWER_KEYS on the API).',
    );
  }
  const response = await fetch(`${API_BASE_URL}/v1/reviews/decisions`, {
    method: 'POST',
    headers: {
      ...apiHeaders(true),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new Error(`Review decision failed (${response.status}): ${await readError(response)}`);
  }
  return response.json() as Promise<{ recorded: boolean; audit_seq: number }>;
}

export async function fetchRuleCatalog(): Promise<RuleCatalogEntry[]> {
  const response = await fetch(`${API_BASE_URL}/v1/rules`, {
    headers: apiHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Rules catalog failed (${response.status}): ${await readError(response)}`);
  }
  return response.json() as Promise<RuleCatalogEntry[]>;
}

export async function fetchPolicy(policyId: string): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE_URL}/v1/policies/${encodeURIComponent(policyId)}`, {
    headers: apiHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Policy failed (${response.status}): ${await readError(response)}`);
  }
  return response.json() as Promise<Record<string, unknown>>;
}

export async function fetchAuditTrace(claimId: string): Promise<AuditTraceEvent[]> {
  const response = await fetch(
    `${API_BASE_URL}/v1/audit/trace?claim_id=${encodeURIComponent(claimId)}&fast=true`,
    { headers: apiHeaders() },
  );
  if (!response.ok) {
    throw new Error(`Audit trace failed (${response.status}): ${await readError(response)}`);
  }
  const body = (await response.json()) as { events: AuditTraceEvent[] };
  return body.events;
}

export async function verifyAuditChain(): Promise<{ valid: boolean; events: number }> {
  const response = await fetch(`${API_BASE_URL}/v1/audit/verify`, { headers: apiHeaders() });
  if (!response.ok) {
    throw new Error(`Audit verify failed (${response.status}): ${await readError(response)}`);
  }
  const body = (await response.json()) as { valid: boolean; events: number };
  return { valid: body.valid, events: body.events };
}

export async function fetchHumanFeedback(): Promise<
  { action: string; claim_id: string; rule_id: string; reason: string; recorded_at?: string }[]
> {
  const response = await fetch(`${API_BASE_URL}/v1/audit/feedback`, { headers: apiHeaders() });
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

export function reviewerKeyConfigured(): boolean {
  return Boolean(REVIEWER_API_KEY);
}

export type BenchmarkSplit = {
  split: string;
  n_claims: number;
  n_pairs: number;
  macro_f1: number;
  micro: { f1: number; false_alarm_rate: number; precision: number; recall: number };
  status_accuracy: number;
  claim_exact_match: number;
  latency_ms: { p50: number; p95: number; max: number };
  per_rule: Record<
    string,
    {
      f1: number | null;
      precision: number | null;
      recall: number | null;
      false_alarm_rate: number;
    }
  >;
};

export async function fetchBenchmarkSplit(split: string): Promise<BenchmarkSplit> {
  const response = await fetch(
    `${API_BASE_URL}/v1/benchmark/splits/${encodeURIComponent(split)}`,
    { headers: apiHeaders() },
  );
  if (!response.ok) {
    throw new Error(`Benchmark failed (${response.status}): ${await readError(response)}`);
  }
  return response.json() as Promise<BenchmarkSplit>;
}

export async function fetchSecurityOverview(): Promise<{
  markdown: string;
  controls: Record<string, unknown>;
}> {
  const response = await fetch(`${API_BASE_URL}/v1/security/overview`, {
    headers: apiHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Security overview failed (${response.status}): ${await readError(response)}`);
  }
  return response.json() as Promise<{ markdown: string; controls: Record<string, unknown> }>;
}

export async function fetchReviewActions(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/v1/reviews/actions`, { headers: apiHeaders() });
  if (!response.ok) return [];
  const body = (await response.json()) as { actions: string[] };
  return body.actions;
}

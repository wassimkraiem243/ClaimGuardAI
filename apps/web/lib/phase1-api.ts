const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:4001';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? 'dev-local-key';

export type NormalizedClaim = {
  envelope: Record<string, unknown>;
  source: string;
  ingestion_warnings: string[];
};

export type RuleResultRow = {
  claim_id: string;
  rule_id: string;
  status: string;
  severity: string;
  explanation: string;
  corrective_action: string;
  requires_human_review: boolean;
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
};

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (body?.detail) {
      return typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    }
    return JSON.stringify(body);
  } catch {
    return response.statusText;
  }
}

export async function ingestClaimFile(file: File): Promise<NormalizedClaim[]> {
  const form = new FormData();
  form.append('file', file);
  const response = await fetch(`${API_BASE_URL}/claims/ingest`, {
    method: 'POST',
    headers: { 'x-api-key': API_KEY },
    body: form,
  });
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
      'Content-Type': 'application/json',
      'x-api-key': API_KEY,
    },
    body: JSON.stringify({ claim }),
  });
  if (!response.ok) {
    throw new Error(`Validate failed (${response.status}): ${await readError(response)}`);
  }
  return response.json() as Promise<ValidationResponse>;
}

export async function fetchRuleCatalog(): Promise<RuleCatalogEntry[]> {
  const response = await fetch(`${API_BASE_URL}/v1/rules`, {
    headers: { 'x-api-key': API_KEY },
  });
  if (!response.ok) {
    throw new Error(`Rules catalog failed (${response.status}): ${await readError(response)}`);
  }
  return response.json() as Promise<RuleCatalogEntry[]>;
}

export async function fetchPolicy(policyId: string): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE_URL}/v1/policies/${encodeURIComponent(policyId)}`, {
    headers: { 'x-api-key': API_KEY },
  });
  if (!response.ok) {
    throw new Error(`Policy failed (${response.status}): ${await readError(response)}`);
  }
  return response.json() as Promise<Record<string, unknown>>;
}

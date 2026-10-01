'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import {
  fetchPolicy,
  fetchRuleCatalog,
  ingestClaimFile,
  validateClaimEnvelope,
  type NormalizedClaim,
  type RuleCatalogEntry,
  type ValidationResponse,
} from '../../lib/phase1-api';

function statusCounts(results: ValidationResponse['results']) {
  const counts: Record<string, number> = {};
  for (const r of results) {
    counts[r.status] = (counts[r.status] ?? 0) + 1;
  }
  return counts;
}

export function Phase1Flow() {
  const [claims, setClaims] = useState<NormalizedClaim[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [pasteJson, setPasteJson] = useState('');
  const [validation, setValidation] = useState<ValidationResponse | null>(null);
  const [rules, setRules] = useState<RuleCatalogEntry[] | null>(null);
  const [policyPreview, setPolicyPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selected = claims[selectedIdx] ?? null;
  const envelope = selected?.envelope ?? null;

  const unresolved = useMemo(() => {
    if (!validation) return 0;
    return validation.results.filter(
      (r) => r.status === 'FAIL' || r.status === 'UNABLE_TO_ASSESS',
    ).length;
  }, [validation]);

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setValidation(null);
    setPolicyPreview(null);
    setBusy('Ingesting…');
    try {
      const normalized = await ingestClaimFile(file);
      setClaims(normalized);
      setSelectedIdx(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ingest failed');
      setClaims([]);
    } finally {
      setBusy(null);
      e.target.value = '';
    }
  }

  async function onPasteIngest() {
    setError(null);
    setValidation(null);
    setBusy('Parsing pasted JSON…');
    try {
      const parsed = JSON.parse(pasteJson) as Record<string, unknown>;
      const blob = new Blob([JSON.stringify(parsed) + '\n'], { type: 'application/jsonl' });
      const file = new File([blob], 'pasted.jsonl', { type: 'application/jsonl' });
      const normalized = await ingestClaimFile(file);
      setClaims(normalized);
      setSelectedIdx(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid JSON');
    } finally {
      setBusy(null);
    }
  }

  async function onValidate() {
    if (!envelope) {
      setError('Ingest a claim first.');
      return;
    }
    setError(null);
    setBusy('Running R001–R015…');
    setPolicyPreview(null);
    try {
      const resp = await validateClaimEnvelope(envelope);
      setValidation(resp);
      const pid = resp.run.policy_id;
      if (pid) {
        const pol = await fetchPolicy(pid);
        setPolicyPreview(JSON.stringify(pol, null, 2));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Validation failed');
      setValidation(null);
    } finally {
      setBusy(null);
    }
  }

  async function onLoadRules() {
    setError(null);
    setBusy('Loading rule catalog…');
    try {
      setRules(await fetchRuleCatalog());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load rules');
    } finally {
      setBusy(null);
    }
  }

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: 16, fontFamily: 'sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700 }}>Phase 1 — Claim flow (functional shell)</h1>
      <p style={{ marginTop: 8, color: '#444' }}>
        Ingest → normalized envelope → run 15 payer rules. Styling is intentionally minimal.
      </p>

      {busy && (
        <p style={{ marginTop: 12, padding: 8, border: '1px solid #999' }} role="status">
          {busy}
        </p>
      )}
      {error && (
        <pre
          style={{ marginTop: 12, padding: 8, border: '1px solid #c00', whiteSpace: 'pre-wrap' }}
        >
          {error}
        </pre>
      )}

      <section style={{ marginTop: 24, padding: 12, border: '1px solid #ccc' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>1. Ingest</h2>
        <p style={{ marginTop: 8, fontSize: 14 }}>
          Upload: <strong>.jsonl</strong> (pack envelope), <strong>.zip</strong> (pack CSV folder),
          <strong> .json</strong> (pack FHIR bundle or single envelope). Legacy demo{' '}
          <strong>.csv</strong> supported with warnings.
        </p>
        <input type="file" onChange={onFileChange} style={{ marginTop: 8, display: 'block' }} />

        <p style={{ marginTop: 16, fontSize: 14 }}>Or paste one claim envelope JSON:</p>
        <textarea
          value={pasteJson}
          onChange={(e) => setPasteJson(e.target.value)}
          rows={6}
          style={{ width: '100%', marginTop: 8, fontFamily: 'monospace', fontSize: 12 }}
          placeholder='{"schema_version":"1.0.0","claim_id":"...", ...}'
        />
        <button type="button" onClick={onPasteIngest} style={{ marginTop: 8 }}>
          Ingest pasted JSON
        </button>

        {claims.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <p>
              <strong>{claims.length}</strong> claim(s) normalized.
            </p>
            {claims.length > 1 && (
              <label style={{ display: 'block', marginTop: 8 }}>
                Select claim:{' '}
                <select
                  value={selectedIdx}
                  onChange={(e) => {
                    setSelectedIdx(Number(e.target.value));
                    setValidation(null);
                  }}
                >
                  {claims.map((c, i) => (
                    <option key={i} value={i}>
                      {String(c.envelope.claim_id)} ({c.source})
                    </option>
                  ))}
                </select>
              </label>
            )}
            {selected && (
              <div style={{ marginTop: 12, fontSize: 14 }}>
                <div>Source: {selected.source}</div>
                <div>Claim ID: {String(selected.envelope.claim_id)}</div>
                <div>Policy: {String(selected.envelope.policy_id)}</div>
                {selected.ingestion_warnings.length > 0 && (
                  <details style={{ marginTop: 8 }}>
                    <summary>Ingestion warnings ({selected.ingestion_warnings.length})</summary>
                    <ul>
                      {selected.ingestion_warnings.map((w) => (
                        <li key={w}>{w}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            )}
          </div>
        )}
      </section>

      <section style={{ marginTop: 16, padding: 12, border: '1px solid #ccc' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>2. Envelope (immutable input for rules)</h2>
        {envelope ? (
          <pre
            style={{
              marginTop: 8,
              maxHeight: 240,
              overflow: 'auto',
              fontSize: 11,
              border: '1px solid #eee',
              padding: 8,
            }}
          >
            {JSON.stringify(envelope, null, 2)}
          </pre>
        ) : (
          <p style={{ marginTop: 8, color: '#666' }}>No claim loaded.</p>
        )}
      </section>

      <section style={{ marginTop: 16, padding: 12, border: '1px solid #ccc' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>3. Validate (15 rules)</h2>
        <button type="button" onClick={onValidate} disabled={!envelope}>
          Run validation
        </button>
        {validation && (
          <div style={{ marginTop: 16, fontSize: 14 }}>
            <p>
              Run ID: <code>{validation.run.run_id}</code>
            </p>
            <p>
              Input hash: <code>{validation.run.input_hash}</code>
            </p>
            <p>Duration: {validation.run.duration_ms} ms</p>
            <p>
              Status summary:{' '}
              {Object.entries(statusCounts(validation.results))
                .map(([k, v]) => `${k}: ${v}`)
                .join(' · ')}
            </p>
            <p>
              Needs attention (FAIL + UNABLE): <strong>{unresolved}</strong>
            </p>
            <table style={{ marginTop: 12, width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={{ border: '1px solid #ccc', padding: 4, textAlign: 'left' }}>Rule</th>
                  <th style={{ border: '1px solid #ccc', padding: 4, textAlign: 'left' }}>Status</th>
                  <th style={{ border: '1px solid #ccc', padding: 4, textAlign: 'left' }}>Severity</th>
                  <th style={{ border: '1px solid #ccc', padding: 4, textAlign: 'left' }}>Explanation</th>
                </tr>
              </thead>
              <tbody>
                {validation.results.map((r) => (
                  <tr key={r.rule_id}>
                    <td style={{ border: '1px solid #ccc', padding: 4 }}>{r.rule_id}</td>
                    <td style={{ border: '1px solid #ccc', padding: 4 }}>{r.status}</td>
                    <td style={{ border: '1px solid #ccc', padding: 4 }}>{r.severity}</td>
                    <td style={{ border: '1px solid #ccc', padding: 4 }}>{r.explanation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section style={{ marginTop: 16, padding: 12, border: '1px solid #ccc' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>4. Rule catalog &amp; policy</h2>
        <button type="button" onClick={onLoadRules} style={{ marginRight: 8 }}>
          Load R001–R015 catalog
        </button>
        {rules && (
          <p style={{ marginTop: 8 }}>
            Loaded <strong>{rules.length}</strong> rules (see console or expand in a future UI).
          </p>
        )}
        {rules && (
          <ul style={{ marginTop: 8, fontSize: 13, maxHeight: 160, overflow: 'auto' }}>
            {rules.map((r) => (
              <li key={r.rule_id}>
                {r.rule_id} — {r.title} ({r.severity})
              </li>
            ))}
          </ul>
        )}
        {policyPreview && (
          <details style={{ marginTop: 12 }}>
            <summary>Resolved policy JSON</summary>
            <pre style={{ fontSize: 11, overflow: 'auto' }}>{policyPreview}</pre>
          </details>
        )}
      </section>

      <section style={{ marginTop: 16, padding: 12, border: '1px solid #ccc' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>5. Optional — seeded dashboard &amp; LLM</h2>
        <p style={{ fontSize: 14, marginTop: 8 }}>
          Pre-seeded pipeline findings (not pack rule results): review list and request LLM analysis
          per finding (requires Ollama).
        </p>
        <Link href="/findings" style={{ display: 'inline-block', marginTop: 8 }}>
          Open validations / findings →
        </Link>
        <Link href="/" style={{ display: 'inline-block', marginTop: 8, marginLeft: 16 }}>
          Dashboard →
        </Link>
      </section>
    </div>
  );
}

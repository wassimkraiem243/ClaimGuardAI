'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Card, StatCard } from './Card';
import { PageHeader } from './PageHeader';
import { RuleStatusBadge } from './RuleStatusBadge';
import {
  fetchPolicy,
  fetchRuleCatalog,
  ingestClaimFile,
  validateClaimEnvelope,
  type NormalizedClaim,
  type RuleCatalogEntry,
  type RuleResultRow,
  type ValidationResponse,
} from '../lib/phase1-api';

type FlowStep = 'ingest' | 'review' | 'validate' | 'results';

const STEPS: { id: FlowStep; label: string; hint: string }[] = [
  { id: 'ingest', label: 'Upload claim', hint: 'JSONL, ZIP, FHIR, or legacy CSV' },
  { id: 'review', label: 'Review envelope', hint: 'Confirm normalized claim data' },
  { id: 'validate', label: 'Run rules', hint: '15 payer pre-submission checks' },
  { id: 'results', label: 'Review results', hint: 'Fix issues before submission' },
];

function statusCounts(results: RuleResultRow[]) {
  const counts: Record<string, number> = {};
  for (const r of results) {
    counts[r.status] = (counts[r.status] ?? 0) + 1;
  }
  return counts;
}

/** Matches rule_engine/reporting/findings.py claim-level outcome. */
type ClaimOutcome = 'ISSUES_FOUND' | 'UNRESOLVED_CHECKS' | 'NO_ISSUES_DETECTED';

function isAmbiguousRuleResult(r: RuleResultRow): boolean {
  return r.status === 'UNABLE_TO_ASSESS' || r.status === 'NOT_IMPLEMENTED';
}

function deriveClaimOutcome(results: RuleResultRow[]): ClaimOutcome {
  if (results.some((r) => r.status === 'FAIL')) return 'ISSUES_FOUND';
  if (results.some(isAmbiguousRuleResult)) return 'UNRESOLVED_CHECKS';
  return 'NO_ISSUES_DETECTED';
}

function needsMandatoryHumanReview(results: RuleResultRow[]): boolean {
  return results.some(isAmbiguousRuleResult);
}

function humanReviewRoutingMessage(
  outcome: ClaimOutcome,
  failCount: number,
  passCount: number,
  humanReviewCount: number,
): string {
  if (humanReviewCount === 0) return '';
  if (outcome === 'ISSUES_FOUND') {
    return `Route to a human reviewer: ${humanReviewCount} ambiguous rule(s) sit alongside ${failCount} failure(s). Fix FAIL items, then have a reviewer assess the ambiguous rules before submit.`;
  }
  return `Route to a human reviewer: ${humanReviewCount} ambiguous rule(s) with ${passCount} passing check(s). Passing rules do not remove the need for human review on unresolved items.`;
}

const OUTCOME_DISPLAY: Record<
  ClaimOutcome,
  { title: string; sub: string; banner: string; bannerClass: string }
> = {
  ISSUES_FOUND: {
    title: 'Failed',
    sub: 'Deterministic rule failures',
    banner: 'Issues found. Correct the failed rules before submission.',
    bannerClass: 'border-critical/30 bg-critical/10 text-critical',
  },
  UNRESOLVED_CHECKS: {
    title: 'Human review required',
    sub: 'Ambiguous or incomplete checks (no proven FAIL)',
    banner:
      'At least one rule could not be decided automatically. A human must review these findings before submit.',
    bannerClass: 'border-high/30 bg-high/10 text-high',
  },
  NO_ISSUES_DETECTED: {
    title: 'Cleared',
    sub: 'No issues from these checks',
    banner:
      'No issues detected by these payer rules. This is not a payer approval or clinical decision.',
    bannerClass: 'border-success/30 bg-success/10 text-success',
  },
};

function stepIndex(step: FlowStep): number {
  return STEPS.findIndex((s) => s.id === step);
}

function resolveActiveStep(
  claimsLength: number,
  envelope: Record<string, unknown> | null,
  validation: ValidationResponse | null,
): FlowStep {
  if (validation) return 'results';
  if (envelope) return 'validate';
  if (claimsLength > 0) return 'review';
  return 'ingest';
}

function PrimaryButton({
  children,
  onClick,
  disabled,
  type = 'button',
}: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  type?: 'button' | 'submit';
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center justify-center rounded-2xl bg-primary px-5 py-2.5 text-sm font-medium text-on-primary shadow-float transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
    >
      {children}
    </button>
  );
}

function SecondaryButton({
  children,
  onClick,
  disabled,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center justify-center rounded-2xl bg-surface px-5 py-2.5 text-sm font-medium text-text-muted shadow-float transition-colors hover:text-text disabled:cursor-not-allowed disabled:opacity-50"
    >
      {children}
    </button>
  );
}

export function PreSubmissionFlow() {
  const [claims, setClaims] = useState<NormalizedClaim[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [pasteJson, setPasteJson] = useState('');
  const [ingestMode, setIngestMode] = useState<'file' | 'paste'>('file');
  const [validation, setValidation] = useState<ValidationResponse | null>(null);
  const [rules, setRules] = useState<RuleCatalogEntry[] | null>(null);
  const [policyPreview, setPolicyPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resultFilter, setResultFilter] = useState<'all' | 'issues'>('issues');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  const selected = claims[selectedIdx] ?? null;
  const envelope = selected?.envelope ?? null;
  const activeStep = resolveActiveStep(claims.length, envelope, validation);
  const activeIdx = stepIndex(activeStep);

  const ruleTitleById = useMemo(() => {
    const map = new Map<string, string>();
    if (rules) {
      for (const r of rules) map.set(r.rule_id, r.title);
    }
    return map;
  }, [rules]);

  const failCount = useMemo(() => {
    if (!validation) return 0;
    return validation.results.filter((r) => r.status === 'FAIL').length;
  }, [validation]);

  const humanReviewCount = useMemo(() => {
    if (!validation) return 0;
    return validation.results.filter(isAmbiguousRuleResult).length;
  }, [validation]);

  const mandatoryHumanReview = useMemo(
    () => (validation ? needsMandatoryHumanReview(validation.results) : false),
    [validation],
  );

  const claimOutcome = useMemo(
    () => (validation ? deriveClaimOutcome(validation.results) : null),
    [validation],
  );

  const passCount = validation?.results.filter((r) => r.status === 'PASS').length ?? 0;

  const outcomeBannerText = useMemo(() => {
    if (!claimOutcome || !validation) return '';
    return OUTCOME_DISPLAY[claimOutcome].banner;
  }, [claimOutcome, validation]);

  const humanReviewMessage = useMemo(() => {
    if (!claimOutcome || !mandatoryHumanReview) return '';
    return humanReviewRoutingMessage(claimOutcome, failCount, passCount, humanReviewCount);
  }, [claimOutcome, mandatoryHumanReview, failCount, passCount, humanReviewCount]);
  const counts = validation ? statusCounts(validation.results) : null;

  const filteredResults = useMemo(() => {
    if (!validation) return [];
    if (resultFilter === 'all') return validation.results;
    return validation.results.filter(
      (r) => r.status === 'FAIL' || isAmbiguousRuleResult(r),
    );
  }, [validation, resultFilter]);

  useEffect(() => {
    fetchRuleCatalog()
      .then(setRules)
      .catch(() => {
        /* catalog is optional for the flow */
      });
  }, []);

  const scrollToResults = useCallback(() => {
    resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setValidation(null);
    setPolicyPreview(null);
    setBusy('Normalizing your claim…');
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
    setPolicyPreview(null);
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
      setError('Upload or paste a claim first.');
      return;
    }
    setError(null);
    setBusy('Running payer rules R001–R015…');
    setPolicyPreview(null);
    try {
      const resp = await validateClaimEnvelope(envelope);
      setValidation(resp);
      const pid = resp.run.policy_id;
      if (pid) {
        const pol = await fetchPolicy(pid);
        setPolicyPreview(JSON.stringify(pol, null, 2));
      }
      window.requestAnimationFrame(() => scrollToResults());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Validation failed');
      setValidation(null);
    } finally {
      setBusy(null);
    }
  }

  function resetFlow() {
    setClaims([]);
    setSelectedIdx(0);
    setPasteJson('');
    setValidation(null);
    setPolicyPreview(null);
    setError(null);
    setResultFilter('issues');
  }

  return (
    <main className="mx-auto max-w-6xl">
      <PageHeader
        title="Pre-submission validation"
        description="Upload a claim, review the normalized envelope, then run payer rules before you submit."
      />

      {/* Step progress */}
      <nav aria-label="Validation progress" className="mb-8">
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => {
            const done = i < activeIdx;
            const current = i === activeIdx;
            return (
              <li
                key={step.id}
                className={`rounded-2xl border p-4 transition-colors ${
                  current
                    ? 'border-primary bg-primary-subtle shadow-float'
                    : done
                      ? 'border-success/30 bg-surface'
                      : 'border-border bg-surface-muted/60'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-sm font-bold ${
                      current
                        ? 'bg-primary text-on-primary'
                        : done
                          ? 'bg-success/15 text-success'
                          : 'bg-surface text-text-faint'
                    }`}
                    aria-hidden="true"
                  >
                    {done ? '✓' : i + 1}
                  </span>
                  <div className="min-w-0">
                    <p
                      className={`text-sm font-semibold ${current ? 'text-primary' : 'text-text'}`}
                    >
                      {step.label}
                    </p>
                    <p className="mt-0.5 text-xs text-text-muted">{step.hint}</p>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      </nav>

      {busy && (
        <div
          role="status"
          className="mb-6 flex items-center gap-3 rounded-2xl border border-primary/20 bg-primary-subtle px-4 py-3 text-sm text-primary"
        >
          <span
            className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent"
            aria-hidden="true"
          />
          {busy}
        </div>
      )}

      {error && (
        <Card className="mb-6 border border-critical/20">
          <p className="font-medium text-critical">Something went wrong</p>
          <p className="mt-2 whitespace-pre-wrap font-mono text-xs text-text-muted">{error}</p>
        </Card>
      )}

      <div className="space-y-6">
        {/* Step 1: Ingest */}
        <Card>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-text">1. Bring in a claim</h2>
              <p className="mt-1 text-sm text-text-muted">
                Use <strong className="font-medium text-text">claims.jsonl</strong> or{' '}
                <strong className="font-medium text-text">fhir_bundles.jsonl</strong> from the pack, a
                single envelope or FHIR bundle as <strong className="font-medium text-text">.json</strong>,
                or zip the whole <strong className="font-medium text-text">csv/</strong> folder (all five
                CSV files). Do not upload <strong className="font-medium text-text">claims.csv</strong>{' '}
                alone; legacy wide <strong className="font-medium text-text">.csv</strong> is a separate
                demo format.
              </p>
            </div>
            {claims.length > 0 && (
              <SecondaryButton onClick={resetFlow}>Start over</SecondaryButton>
            )}
          </div>

          <div
            className="mt-5 inline-flex rounded-2xl bg-surface-muted p-1"
            role="tablist"
            aria-label="Ingest method"
          >
            <button
              type="button"
              role="tab"
              aria-selected={ingestMode === 'file'}
              onClick={() => setIngestMode('file')}
              className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
                ingestMode === 'file'
                  ? 'bg-primary text-on-primary'
                  : 'text-text-muted hover:text-text'
              }`}
            >
              Upload file
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={ingestMode === 'paste'}
              onClick={() => setIngestMode('paste')}
              className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
                ingestMode === 'paste'
                  ? 'bg-primary text-on-primary'
                  : 'text-text-muted hover:text-text'
              }`}
            >
              Paste JSON
            </button>
          </div>

          {ingestMode === 'file' ? (
            <div className="mt-5">
              <input
                ref={fileInputRef}
                type="file"
                accept=".jsonl,.json,.zip,.csv"
                onChange={onFileChange}
                className="sr-only"
                id="claim-file-input"
              />
              <label
                htmlFor="claim-file-input"
                className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-surface-muted/50 px-6 py-12 transition-colors hover:border-primary hover:bg-primary-subtle/40"
              >
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-subtle text-primary">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path
                      d="M12 16V8m0 0l-3 3m3-3l3 3M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
                <span className="mt-4 text-sm font-semibold text-text">
                  Drop a file here or click to browse
                </span>
                <span className="mt-1 text-xs text-text-muted">
                  Max 5 MB. Examples:{' '}
                  <code className="rounded bg-surface px-1 font-mono">claims.jsonl</code>,{' '}
                  <code className="rounded bg-surface px-1 font-mono">fhir_bundles.jsonl</code>, or{' '}
                  <code className="rounded bg-surface px-1 font-mono">development.zip</code> (zipped
                  csv folder)
                </span>
              </label>
              <div className="mt-4 flex flex-wrap gap-2">
                <SecondaryButton onClick={() => fileInputRef.current?.click()}>
                  Choose file
                </SecondaryButton>
              </div>
            </div>
          ) : (
            <div className="mt-5">
              <label htmlFor="paste-json" className="text-sm font-medium text-text">
                Claim envelope JSON
              </label>
              <p className="mt-1 text-xs text-text-muted">
                One normalized envelope only. For FHIR bundles, JSONL files, or CSV packs, use Upload
                file.
              </p>
              <textarea
                id="paste-json"
                value={pasteJson}
                onChange={(e) => setPasteJson(e.target.value)}
                rows={8}
                className="mt-2 w-full rounded-2xl border border-border bg-surface-muted/30 px-4 py-3 font-mono text-xs text-text focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                placeholder='{"schema_version":"1.0.0","claim_id":"...", ...}'
              />
              <div className="mt-4">
                <PrimaryButton onClick={onPasteIngest} disabled={!pasteJson.trim()}>
                  Parse and normalize
                </PrimaryButton>
              </div>
            </div>
          )}

          {claims.length > 0 && (
            <div className="mt-6 rounded-2xl bg-success/10 px-4 py-3 text-sm text-success">
              <strong>{claims.length}</strong> claim{claims.length === 1 ? '' : 's'} ready for
              review, then continue to step 2 below.
            </div>
          )}
        </Card>

        {/* Step 2: Review */}
        <Card className={claims.length === 0 ? 'opacity-60' : ''}>
          <h2 className="text-lg font-semibold text-text">2. Review normalized claim</h2>
          <p className="mt-1 text-sm text-text-muted">
            The rule engine runs on this immutable envelope. Check IDs, policy, and warnings before
            validating.
          </p>

          {claims.length === 0 ? (
            <p className="mt-6 text-sm text-text-faint">Upload a claim in step 1 to continue.</p>
          ) : (
            <div className="mt-6 space-y-4">
              {claims.length > 1 && (
                <label className="block text-sm">
                  <span className="font-medium text-text">Select claim</span>
                  <select
                    value={selectedIdx}
                    onChange={(e) => {
                      setSelectedIdx(Number(e.target.value));
                      setValidation(null);
                      setPolicyPreview(null);
                    }}
                    className="mt-2 block w-full max-w-md rounded-2xl border border-border bg-surface px-4 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
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
                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="rounded-2xl bg-surface-muted p-4">
                    <p className="text-xs text-text-muted">Claim ID</p>
                    <p className="mt-1 font-mono text-sm font-semibold">
                      {String(selected.envelope.claim_id)}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-surface-muted p-4">
                    <p className="text-xs text-text-muted">Source</p>
                    <p className="mt-1 text-sm font-semibold">{selected.source}</p>
                  </div>
                  <div className="rounded-2xl bg-surface-muted p-4">
                    <p className="text-xs text-text-muted">Policy</p>
                    <p className="mt-1 font-mono text-sm font-semibold">
                      {String(selected.envelope.policy_id ?? '-')}
                    </p>
                  </div>
                </div>
              )}

              {selected && selected.ingestion_warnings.length > 0 && (
                <details className="rounded-2xl border border-medium/30 bg-medium/5 px-4 py-3">
                  <summary className="cursor-pointer text-sm font-medium text-high">
                    Ingestion warnings ({selected.ingestion_warnings.length})
                  </summary>
                  <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-text-muted">
                    {selected.ingestion_warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                </details>
              )}

              <details className="rounded-2xl border border-border bg-surface-muted/30">
                <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-text">
                  View full envelope JSON
                </summary>
                <pre className="max-h-64 overflow-auto border-t border-border px-4 py-3 font-mono text-[11px] text-text-muted scrollbar-subtle">
                  {envelope ? JSON.stringify(envelope, null, 2) : '-'}
                </pre>
              </details>
            </div>
          )}
        </Card>

        {/* Step 3: Validate */}
        <Card className={!envelope ? 'opacity-60' : ''}>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-text">3. Run payer rules</h2>
              <p className="mt-1 text-sm text-text-muted">
                Executes R001–R015 against the envelope and records an auditable run (hash + policy).
              </p>
            </div>
            <PrimaryButton onClick={onValidate} disabled={!envelope || !!busy}>
              {validation ? 'Run again' : 'Run validation'}
            </PrimaryButton>
          </div>

          {rules && rules.length > 0 && (
            <p className="mt-4 text-xs text-text-faint">
              {rules.length} rules loaded from catalog.{' '}
              <button
                type="button"
                className="font-medium text-primary hover:underline"
                onClick={() => {
                  const el = document.getElementById('rule-catalog-panel');
                  el?.scrollIntoView({ behavior: 'smooth' });
                }}
              >
                view rule list
              </button>
            </p>
          )}
        </Card>

        {/* Step 4: Results */}
        <div ref={resultsRef}>
          <Card className={!validation ? 'opacity-60' : ''}>
            <h2 className="text-lg font-semibold text-text">4. Results &amp; next steps</h2>
            {!validation ? (
              <p className="mt-4 text-sm text-text-faint">
                Run validation in step 3 to see rule outcomes here.
              </p>
            ) : (
              <div className="mt-6 space-y-6">
                {claimOutcome && (
                  <div
                    className={`rounded-2xl border px-5 py-4 ${OUTCOME_DISPLAY[claimOutcome].bannerClass}`}
                    role="status"
                  >
                    <p className="text-sm font-semibold">{OUTCOME_DISPLAY[claimOutcome].title}</p>
                    <p className="mt-1 text-sm opacity-90">{outcomeBannerText}</p>
                  </div>
                )}

                {mandatoryHumanReview && humanReviewMessage && (
                  <div
                    className="rounded-2xl border border-high/30 bg-high/10 px-5 py-4 text-high"
                    role="status"
                  >
                    <p className="text-sm font-semibold">Routed to human review</p>
                    <p className="mt-1 text-sm opacity-90">{humanReviewMessage}</p>
                  </div>
                )}

                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <StatCard label="Failed rules" value={failCount} sub="Clear FAIL (fix data)" />
                  <StatCard
                    label="Human review queue"
                    value={humanReviewCount}
                    sub={
                      mandatoryHumanReview
                        ? 'Ambiguity: must go to a reviewer'
                        : 'No ambiguous rules'
                    }
                  />
                  <StatCard label="Passed" value={passCount} />
                  <StatCard label="Duration" value={`${validation.run.duration_ms} ms`} />
                </div>

                {claimOutcome && (
                  <div className="rounded-2xl bg-surface-muted px-4 py-3 text-sm">
                    <span className="font-medium text-text">Claim outcome: </span>
                    <span className="font-semibold text-text">
                      {OUTCOME_DISPLAY[claimOutcome].title}
                    </span>
                    <span className="text-text-muted"> · {OUTCOME_DISPLAY[claimOutcome].sub}</span>
                    {mandatoryHumanReview && (
                      <span className="text-text-muted">
                        {' '}
                        · <span className="font-medium text-high">Routed to human review</span> (
                        {humanReviewCount} ambiguous rule
                        {humanReviewCount === 1 ? '' : 's'})
                      </span>
                    )}
                  </div>
                )}

                <div className="rounded-2xl bg-surface-muted px-4 py-3 text-xs text-text-muted">
                  <span className="font-medium text-text">Audit trail:</span> run{' '}
                  <code className="font-mono">{validation.run.run_id}</code> · input hash{' '}
                  <code className="font-mono">{validation.run.input_hash.slice(0, 16)}…</code>
                </div>

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div
                    className="inline-flex flex-wrap items-center gap-0.5 rounded-2xl bg-surface-muted p-1"
                    role="group"
                    aria-label="Filter results"
                  >
                    <button
                      type="button"
                      onClick={() => setResultFilter('issues')}
                      className={`rounded-xl px-3.5 py-1.5 text-sm font-medium transition-colors ${
                        resultFilter === 'issues'
                          ? 'bg-primary text-on-primary'
                          : 'text-text-muted hover:bg-surface hover:text-text'
                      }`}
                    >
                      Issues only
                    </button>
                    <button
                      type="button"
                      onClick={() => setResultFilter('all')}
                      className={`rounded-xl px-3.5 py-1.5 text-sm font-medium transition-colors ${
                        resultFilter === 'all'
                          ? 'bg-primary text-on-primary'
                          : 'text-text-muted hover:bg-surface hover:text-text'
                      }`}
                    >
                      All rules
                    </button>
                  </div>
                  {counts && (
                    <span className="text-sm text-text-muted">
                      {Object.entries(counts)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(' · ')}
                    </span>
                  )}
                </div>

                <div className="overflow-hidden rounded-2xl border border-border">
                  {filteredResults.length === 0 ? (
                    <div className="px-6 py-12 text-center">
                      <p className="font-semibold text-success">No open issues</p>
                      <p className="mt-1 text-sm text-text-muted">
                        All evaluated rules passed or were not applicable.
                      </p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto scrollbar-subtle">
                      <table className="min-w-[640px] w-full text-left text-sm">
                        <thead>
                          <tr className="bg-surface-muted text-xs font-medium text-text-faint">
                            <th className="px-5 py-3">Rule</th>
                            <th className="px-5 py-3">Status</th>
                            <th className="px-5 py-3">Explanation</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredResults.map((r) => (
                            <tr
                              key={r.rule_id}
                              className="border-t border-border transition-colors hover:bg-primary-subtle/50"
                            >
                              <td className="px-5 py-4">
                                <p className="font-medium">{r.rule_id}</p>
                                {ruleTitleById.get(r.rule_id) && (
                                  <p className="mt-0.5 text-xs text-text-muted">
                                    {ruleTitleById.get(r.rule_id)}
                                  </p>
                                )}
                              </td>
                              <td className="px-5 py-4">
                                <div className="flex flex-col gap-2">
                                  <RuleStatusBadge status={r.status} />
                                  {isAmbiguousRuleResult(r) && (
                                    <span
                                      className="inline-flex w-fit items-center rounded-pill bg-high/15 px-3 py-1 text-xs font-semibold text-high"
                                    >
                                      Human review
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="max-w-md px-5 py-4 text-text-muted">
                                <p>{r.explanation}</p>
                                {r.corrective_action && (
                                  <p className="mt-2 text-xs text-text-faint">
                                    <span className="font-medium text-text">Fix:</span>{' '}
                                    {r.corrective_action}
                                  </p>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {policyPreview && (
                  <details className="rounded-2xl border border-border">
                    <summary className="cursor-pointer px-4 py-3 text-sm font-medium">
                      Resolved policy JSON
                    </summary>
                    <pre className="max-h-48 overflow-auto border-t border-border px-4 py-3 font-mono text-[11px] scrollbar-subtle">
                      {policyPreview}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </Card>
        </div>

        {/* Rule catalog reference */}
        <div id="rule-catalog-panel">
        <Card>
          <h2 className="font-semibold text-text">Rule catalog (reference)</h2>
          <p className="mt-1 text-sm text-text-muted">
            What each payer rule checks, loaded automatically from the API.
          </p>
          {!rules ? (
            <p className="mt-4 text-sm text-text-faint">Loading catalog…</p>
          ) : (
            <ul className="mt-4 max-h-48 space-y-2 overflow-auto text-sm scrollbar-subtle">
              {rules.map((r) => (
                <li
                  key={r.rule_id}
                  className="flex flex-wrap items-center gap-2 rounded-xl bg-surface-muted px-3 py-2"
                >
                  <span className="font-mono font-medium">{r.rule_id}</span>
                  <span className="text-text-muted">{r.title}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        </div>
      </div>
    </main>
  );
}

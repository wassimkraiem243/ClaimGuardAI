'use client';

import { useEffect, useState } from 'react';
import { Card } from '../../components/Card';
import { PageHeader } from '../../components/PageHeader';
import { fetchSecurityOverview } from '../../lib/phase1-api';

export default function SecurityPage() {
  const [markdown, setMarkdown] = useState<string>('');
  const [controls, setControls] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSecurityOverview()
      .then((data) => {
        setMarkdown(data.markdown);
        setControls(data.controls);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Load failed'));
  }, []);

  return (
    <main className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Privacy & security (Phase 2)"
        description="Threat model, access control, data minimization, and auditability for the teaching prototype."
      />

      {error && (
        <Card>
          <p className="text-sm text-critical">{error}</p>
        </Card>
      )}

      {controls && (
        <Card>
          <h2 className="font-semibold text-text">Active controls</h2>
          <ul className="mt-3 space-y-2 text-sm text-text-muted">
            <li>
              Upload limit:{' '}
              <strong className="text-text">
                {Math.round(Number(controls.upload_max_bytes) / (1024 * 1024))} MB
              </strong>
            </li>
            <li>
              Auth:{' '}
              {(controls.auth_modes as string[])?.map((m) => (
                <code key={m} className="mr-2 rounded bg-surface-muted px-1 font-mono text-xs">
                  {m}
                </code>
              ))}
            </li>
            <li>
              JWT roles: {(controls.roles as string[])?.join(', ')}
            </li>
            <li>FHIR preflight: {controls.fhir_preflight ? 'enabled' : 'off'}</li>
            <li>LLM clinical guards: {controls.llm_clinical_guards ? 'enabled' : 'off'}</li>
            <li>
              Verify audit chain:{' '}
              <code className="font-mono text-xs">{String(controls.audit_verify_path)}</code>
            </li>
          </ul>
        </Card>
      )}

      {markdown && (
        <Card>
          <h2 className="font-semibold text-text">Privacy & security note</h2>
          <article className="prose prose-sm mt-4 max-w-none whitespace-pre-wrap text-sm text-text-muted">
            {markdown}
          </article>
        </Card>
      )}
    </main>
  );
}

'use client';

import Link from 'next/link';
import { Card } from '../../components/Card';
import { PageHeader } from '../../components/PageHeader';

const LINKS = [
  {
    title: 'Data flow',
    local: 'docs/architecture/data-flow.md',
    description: 'Ingest → normalize → rules → findings → audit (Markdown in repo).',
  },
  {
    title: 'OpenAPI',
    href: 'http://localhost:4001/docs',
    description: 'Interactive API reference when the API is running locally.',
  },
  {
    title: 'Evaluation report',
    local: 'docs/evaluation/EVALUATION_REPORT.md',
    description: 'F1, false-alarm rate, latency, limitations.',
  },
  {
    title: 'Challenge brief',
    local: 'docs/challenge/CSTAM_VELODOC_BRIEF.md',
    description: 'CSTAM-VELODOC scoring rubric.',
  },
];

export default function GuidesPage() {
  return (
    <main className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title="Architecture & deliverables"
        description="Phase 1 documentation links (source files in the repository)."
      />
      <Card>
        <ul className="space-y-4 text-sm">
          {LINKS.map((item) => (
            <li key={item.title} className="rounded-2xl bg-surface-muted px-4 py-3">
              <p className="font-semibold text-text">{item.title}</p>
              <p className="mt-1 text-text-muted">{item.description}</p>
              {'local' in item && item.local && (
                <p className="mt-2 font-mono text-xs text-primary">{item.local}</p>
              )}
              {'href' in item && item.href && (
                <Link
                  href={item.href}
                  className="mt-2 inline-block text-sm font-medium text-primary hover:underline"
                  target={item.href.startsWith('http') ? '_blank' : undefined}
                >
                  Open {item.title}
                </Link>
              )}
            </li>
          ))}
        </ul>
        <p className="mt-6 text-xs text-text-faint">
          Architecture diagram: export from docs/architecture/data-flow.md or draw.io in your pitch deck.
        </p>
      </Card>
    </main>
  );
}

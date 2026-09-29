import type { UnifiedFindingDto } from '@claimguard/shared-types';
import { BuildSelector } from '../../components/BuildSelector';
import { Card } from '../../components/Card';
import { FilterChipLink, PageHeader, SecondaryButtonLink } from '../../components/PageHeader';
import { apiClient } from '../../lib/api-client';
import { buildPageUrl, resolveBuildId } from '../../lib/build-params';
import FindingsTable from './FindingsTable';

export const dynamic = 'force-dynamic';

const PAGE_SIZE = 25;

const severityFilters = [
  { label: 'All', value: '' },
  { label: 'Critical', value: 'CRITICAL' },
  { label: 'High', value: 'HIGH' },
  { label: 'Medium', value: 'MEDIUM' },
  { label: 'Low', value: 'LOW' },
  { label: 'Info', value: 'INFO' },
  { label: 'Unknown', value: 'UNKNOWN' },
];

export default async function FindingsPage({
  searchParams,
}: {
  searchParams?: Promise<{ severity?: string; offset?: string; build?: string }>;
}) {
  const params = await searchParams;
  const severity = params?.severity;
  const offset = Number(params?.offset ?? 0);

  const builds = await apiClient.getPipelineRuns().catch(() => []);
  const selectedBuildId = resolveBuildId(params?.build, builds);
  const isLatestBuild =
    !params?.build || (builds.length > 0 && selectedBuildId === builds[0]?.id);
  const buildForUrl = isLatestBuild ? undefined : selectedBuildId;

  let findings: UnifiedFindingDto[] = [];
  let error: string | null = null;

  try {
    findings = await apiClient.getFindings({
      pipelineRunId: selectedBuildId,
      severity: severity || undefined,
      limit: PAGE_SIZE,
      offset,
    });
  } catch (err) {
    error = err instanceof Error ? err.message : 'Unable to retrieve findings.';
  }

  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const activeFilter = severityFilters.find((f) => f.value === (severity ?? ''))?.label ?? 'All';
  const selectedBuild = builds.find((build) => build.id === selectedBuildId);
  const buildLabel = selectedBuild?.externalId
    ? `#${selectedBuild.externalId}`
    : selectedBuild
      ? 'Selected build'
      : null;

  return (
    <main className="mx-auto max-w-6xl">
      <PageHeader
        title="Findings"
        description={`Page ${currentPage} · ${findings.length} shown${activeFilter !== 'All' ? ` · ${activeFilter} only` : ''}${buildLabel ? ` · ${buildLabel}` : ''}`}
      />

      {error ? (
        <Card>
          <p className="font-medium text-critical">Findings API unavailable</p>
          <p className="mt-2 text-sm text-text-muted">{error}</p>
        </Card>
      ) : (
        <div className="space-y-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div
              className="inline-flex flex-wrap items-center gap-0.5 rounded-2xl bg-surface p-1 shadow-float"
              role="group"
              aria-label="Filter by severity"
            >
              {severityFilters.map((filter) => (
                <FilterChipLink
                  key={filter.label}
                  grouped
                  href={buildPageUrl('/findings', {
                    build: buildForUrl,
                    severity: filter.value || undefined,
                  })}
                  active={(severity ?? '') === filter.value}
                >
                  {filter.label}
                </FilterChipLink>
              ))}
            </div>

            <BuildSelector builds={builds} selectedId={selectedBuildId} />
          </div>

          <Card className="overflow-hidden !p-0">
            <FindingsTable findings={findings} />
          </Card>

          <div className="flex items-center justify-between rounded-2xl bg-surface px-4 py-3 shadow-float">
            <SecondaryButtonLink
              href={buildPageUrl('/findings', {
                build: buildForUrl,
                severity: severity || undefined,
                offset: Math.max(0, offset - PAGE_SIZE),
              })}
              disabled={offset === 0}
            >
              Previous
            </SecondaryButtonLink>
            <span className="rounded-xl bg-surface-muted px-4 py-1.5 text-sm font-medium text-text-muted">
              Page {currentPage}
            </span>
            <SecondaryButtonLink
              href={buildPageUrl('/findings', {
                build: buildForUrl,
                severity: severity || undefined,
                offset: offset + PAGE_SIZE,
              })}
              disabled={findings.length < PAGE_SIZE}
            >
              Next
            </SecondaryButtonLink>
          </div>
        </div>
      )}
    </main>
  );
}

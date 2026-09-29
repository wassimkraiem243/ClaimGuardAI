import Link from 'next/link';
import type { DashboardOverviewDto } from '@claimguard/shared-types';
import { BuildSelector } from '../components/BuildSelector';
import { Card, StatCard } from '../components/Card';
import { SeverityDot } from '../components/SeverityDot';
import { PageHeader } from '../components/PageHeader';
import { apiClient } from '../lib/api-client';
import { buildPageUrl, resolveBuildId } from '../lib/build-params';

export const dynamic = 'force-dynamic';

const SEVERITY_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', 'UNKNOWN'];
const SEGMENT_COLORS: Record<string, string> = {
  CRITICAL: 'bg-critical',
  HIGH: 'bg-high',
  MEDIUM: 'bg-medium',
  LOW: 'bg-low',
  INFO: 'bg-info',
  UNKNOWN: 'bg-border',
};

function formatDate(iso: string | null | undefined) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function scanStatusClass(status: string) {
  const s = status.toUpperCase();
  if (s === 'SUCCESS' || s === 'PASSED') return 'text-success';
  if (s === 'FAILED' || s === 'FAILURE') return 'text-critical';
  return 'text-text-muted';
}

export default async function Home({
  searchParams,
}: {
  searchParams?: Promise<{ build?: string }>;
}) {
  const params = await searchParams;
  let overview: DashboardOverviewDto | null = null;
  let error: string | null = null;

  const builds = await apiClient.getPipelineRuns().catch(() => []);
  const selectedBuildId = resolveBuildId(params?.build, builds);

  try {
    overview = await apiClient.getOverview(undefined, selectedBuildId);
  } catch (err) {
    error = err instanceof Error ? err.message : 'Unable to reach the dashboard API.';
  }

  const total = overview?.metrics.totalFindings ?? 0;
  const critical = overview?.metrics.bySeverity.CRITICAL ?? 0;
  const high = overview?.metrics.bySeverity.HIGH ?? 0;
  const isLatestBuild =
    !params?.build ||
    (builds.length > 0 && selectedBuildId === builds[0]?.id);

  return (
    <main className="mx-auto max-w-6xl">
      <PageHeader
        title="Overview"
        description={overview ? `${overview.project.name} · ${overview.project.slug}` : 'Loading project'}
        trailing={<BuildSelector builds={builds} selectedId={selectedBuildId} />}
      />

      {error ? (
        <Card className="border border-critical/20">
          <p className="font-medium text-critical">Dashboard API unavailable</p>
          <p className="mt-2 text-sm text-text-muted">{error}</p>
        </Card>
      ) : overview ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total findings" value={total} />
            <StatCard label="Critical" value={critical} sub="Needs immediate attention" />
            <StatCard label="High" value={high} />
            <StatCard label="Scanners" value={overview.scans.length} sub="Reports received" />
          </div>

          <Card>
            <div className="mb-5 flex items-center justify-between">
              <h2 className="font-semibold text-text">Findings by severity</h2>
              <span className="rounded-xl bg-primary-subtle px-3 py-1 text-sm font-medium text-primary">
                {total} total
              </span>
            </div>

            {total > 0 ? (
              <>
                <div
                  className="flex h-3 overflow-hidden rounded-pill bg-surface-muted"
                  role="img"
                  aria-label="Findings distribution by severity"
                >
                  {SEVERITY_ORDER.map((severity) => {
                    const count =
                      overview.metrics.bySeverity[severity as keyof typeof overview.metrics.bySeverity] ?? 0;
                    if (count === 0) return null;
                    return (
                      <div
                        key={severity}
                        className={SEGMENT_COLORS[severity]}
                        style={{ width: `${(count / total) * 100}%` }}
                        title={`${severity}: ${count}`}
                      />
                    );
                  })}
                </div>

                <ul className="mt-6 flex flex-wrap gap-3">
                  {SEVERITY_ORDER.map((severity) => {
                    const count =
                      overview.metrics.bySeverity[severity as keyof typeof overview.metrics.bySeverity] ?? 0;
                    if (count === 0) return null;
                    return (
                      <li key={severity}>
                        <Link
                          href={buildPageUrl('/findings', {
                            build: isLatestBuild ? undefined : selectedBuildId,
                            severity,
                          })}
                          className="flex items-center gap-2 rounded-2xl bg-surface-muted px-4 py-2 text-sm transition-colors hover:bg-primary-subtle"
                        >
                          <SeverityDot severity={severity} />
                          <span className="text-text-muted">{severity}</span>
                          <span className="font-semibold tabular-nums">{count}</span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </>
            ) : (
              <p className="text-sm text-text-muted">No scan reports stored yet.</p>
            )}
          </Card>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl bg-surface p-5 shadow-float">
              <p className="text-sm text-text-muted">Last report received</p>
              <p className="mt-2 text-lg font-semibold">{formatDate(overview.lastReceivedAt)}</p>
            </div>
            {overview.latestPipelineRun && (
              <div className="rounded-2xl bg-surface p-5 shadow-float">
                <p className="text-sm text-text-muted">
                  {isLatestBuild ? 'Latest build' : 'Selected build'}
                </p>
                <p className="mt-2 text-2xl font-semibold tracking-tight">
                  #{overview.latestPipelineRun.externalId ?? '—'}
                </p>
                <p className={`mt-1 text-sm font-medium ${scanStatusClass(overview.latestPipelineRun.status)}`}>
                  {overview.latestPipelineRun.status}
                </p>
              </div>
            )}
          </div>

          {overview.scans.length > 0 && (
            <Card className="overflow-hidden !p-0">
              <div className="px-6 pb-2 pt-6">
                <h2 className="font-semibold text-text">Received reports</h2>
              </div>
              <div className="overflow-x-auto scrollbar-subtle">
                <table className="min-w-[640px] w-full text-left text-sm">
                  <thead>
                    <tr className="text-xs font-medium text-text-faint">
                      <th className="px-6 py-3">Tool</th>
                      <th className="px-6 py-3">Label</th>
                      <th className="px-6 py-3">Status</th>
                      <th className="px-6 py-3">Findings</th>
                      <th className="px-6 py-3">Finished</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.scans.map((scan) => (
                      <tr key={`${scan.tool}-${scan.scanLabel}`} className="transition-colors hover:bg-surface-muted">
                        <td className="px-6 py-4 font-medium">{scan.tool}</td>
                        <td className="max-w-xs truncate px-6 py-4 text-text-muted" title={scan.scanLabel}>
                          {scan.scanLabel}
                        </td>
                        <td className={`px-6 py-4 font-medium ${scanStatusClass(scan.status)}`}>{scan.status}</td>
                        <td className="px-6 py-4 tabular-nums text-text-muted">{scan.findingsCount}</td>
                        <td className="whitespace-nowrap px-6 py-4 text-text-faint">{formatDate(scan.finishedAt)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      ) : null}
    </main>
  );
}

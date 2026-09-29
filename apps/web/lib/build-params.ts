export const BUILD_PARAM = 'build';

export function resolveBuildId(
  buildParam: string | undefined,
  builds: { id: string }[],
): string | undefined {
  if (buildParam) {
    const exists = builds.some((build) => build.id === buildParam);
    return exists ? buildParam : builds[0]?.id;
  }
  return builds[0]?.id;
}

export function buildPageUrl(
  pathname: string,
  params: { build?: string; severity?: string; offset?: number },
) {
  const search = new URLSearchParams();
  if (params.build) search.set(BUILD_PARAM, params.build);
  if (params.severity) search.set('severity', params.severity);
  if (params.offset && params.offset > 0) search.set('offset', String(params.offset));
  const qs = search.toString();
  return qs ? `${pathname}?${qs}` : pathname;
}

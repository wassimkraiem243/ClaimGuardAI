'use client';

import type { PipelineRunDto } from '@claimguard/shared-types';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useId, useRef, useState } from 'react';
import { BUILD_PARAM } from '../lib/build-params';

function formatBuildDate(iso: string | null | undefined) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function buildNumber(run: PipelineRunDto) {
  return run.externalId ? `#${run.externalId}` : run.id.slice(0, 8);
}

function statusDotClass(status: string) {
  const s = status.toUpperCase();
  if (s === 'SUCCESS') return 'bg-success';
  if (s === 'FAILED') return 'bg-critical';
  if (s === 'RUNNING') return 'bg-primary';
  return 'bg-text-faint';
}

function statusTextClass(status: string) {
  const s = status.toUpperCase();
  if (s === 'SUCCESS') return 'text-success';
  if (s === 'FAILED') return 'text-critical';
  if (s === 'RUNNING') return 'text-primary';
  return 'text-text-muted';
}

interface BuildSelectorProps {
  builds: PipelineRunDto[];
  selectedId?: string;
  resetParams?: string[];
}

function BuildSelectorInner({ builds, selectedId, resetParams = ['offset'] }: BuildSelectorProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const listboxId = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };

    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  if (builds.length === 0) {
    return (
      <div className="rounded-2xl bg-surface px-4 py-2.5 text-sm text-text-faint shadow-float">
        No builds yet
      </div>
    );
  }

  const effectiveId = selectedId ?? builds[0]?.id ?? '';
  const selected = builds.find((build) => build.id === effectiveId) ?? builds[0];
  const selectedIndex = builds.findIndex((build) => build.id === effectiveId);

  const selectBuild = (nextId: string) => {
    const params = new URLSearchParams(searchParams.toString());

    if (nextId && nextId === builds[0]?.id) {
      params.delete(BUILD_PARAM);
    } else if (nextId) {
      params.set(BUILD_PARAM, nextId);
    } else {
      params.delete(BUILD_PARAM);
    }

    for (const key of resetParams) {
      params.delete(key);
    }

    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
    setOpen(false);
  };

  return (
    <div ref={containerRef} className="relative">
      <div className="flex items-center gap-2.5 rounded-2xl bg-surface px-3 py-2 shadow-float">
        <span className="hidden text-xs font-medium uppercase tracking-wide text-text-faint sm:inline">
          Build
        </span>

        <button
          type="button"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={listboxId}
          onClick={() => setOpen((value) => !value)}
          className="flex min-w-0 items-center gap-2 rounded-xl border border-primary/15 bg-surface-muted px-3 py-1.5 text-left text-sm font-medium text-text transition-colors hover:border-primary/30 hover:bg-primary-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary sm:min-w-[13rem]"
        >
          <span className={`h-2 w-2 shrink-0 rounded-full ${statusDotClass(selected.status)}`} />
          <span className="min-w-0 flex-1 truncate">
            {buildNumber(selected)}
            <span className="mx-1.5 text-text-faint">·</span>
            <span className={statusTextClass(selected.status)}>{selected.status}</span>
            <span className="mx-1.5 hidden text-text-faint sm:inline">·</span>
            <span className="hidden text-text-muted sm:inline">
              {formatBuildDate(selected.finishedAt ?? selected.createdAt)}
            </span>
          </span>
          <svg
            className={`h-4 w-4 shrink-0 text-text-muted transition-transform ${open ? 'rotate-180' : ''}`}
            viewBox="0 0 20 20"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M5 7.5l5 5 5-5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>

      {open && (
        <ul
          id={listboxId}
          role="listbox"
          aria-label="Select build"
          aria-activedescendant={builds[selectedIndex] ? `build-option-${builds[selectedIndex].id}` : undefined}
          className="absolute right-0 z-50 mt-2 max-h-72 w-[min(100vw-2rem,22rem)] overflow-auto rounded-2xl border border-border bg-surface p-1.5 shadow-float-lg scrollbar-subtle"
        >
          {builds.map((build, index) => {
            const isSelected = build.id === effectiveId;
            const isLatest = index === 0;

            return (
              <li key={build.id} role="presentation">
                <button
                  id={`build-option-${build.id}`}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => selectBuild(build.id)}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-colors ${
                    isSelected
                      ? 'bg-primary-subtle text-text'
                      : 'text-text-muted hover:bg-surface-muted hover:text-text'
                  }`}
                >
                  <span className={`h-2 w-2 shrink-0 rounded-full ${statusDotClass(build.status)}`} />
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
                      <span className="font-semibold text-text">{buildNumber(build)}</span>
                      {isLatest && (
                        <span className="rounded-lg bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary">
                          Latest
                        </span>
                      )}
                    </span>
                    <span className="mt-0.5 block text-xs text-text-faint">
                      <span className={statusTextClass(build.status)}>{build.status}</span>
                      <span className="mx-1.5">·</span>
                      {formatBuildDate(build.finishedAt ?? build.createdAt)}
                    </span>
                  </span>
                  {isSelected && (
                    <svg
                      className="h-4 w-4 shrink-0 text-primary"
                      viewBox="0 0 20 20"
                      fill="none"
                      aria-hidden="true"
                    >
                      <path
                        d="M5 10l3 3 7-7"
                        stroke="currentColor"
                        strokeWidth="1.75"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function BuildSelectorFallback() {
  return (
    <div className="h-[42px] w-48 animate-pulse rounded-2xl bg-surface shadow-float" />
  );
}

export function BuildSelector(props: BuildSelectorProps) {
  return (
    <Suspense fallback={<BuildSelectorFallback />}>
      <BuildSelectorInner {...props} />
    </Suspense>
  );
}

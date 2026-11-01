'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

const NAV_ITEMS = [
  {
    href: '/',
    label: 'Validate claim',
    section: 'Phase 1 & 3',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path
          d="M10 2L3 6v8l7 4 7-4V6l-7-4z"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        <path d="M7 10l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    href: '/audit',
    label: 'Audit trail',
    section: 'Phase 1',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M4 4h12v12H4V4z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M7 8h6M7 11h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    href: '/evaluation',
    label: 'Benchmark metrics',
    section: 'Phase 2',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M4 14V8M8 14V4M12 14v-6M16 14v-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    href: '/security',
    label: 'Privacy & security',
    section: 'Phase 2',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path
          d="M10 3l6 3v5c0 4-2.5 6.5-6 8-3.5-1.5-6-4-6-8V6l6-3z"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    href: '/guides',
    label: 'Architecture docs',
    section: 'Deliverables',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M6 4h8v12H6V4z" stroke="currentColor" strokeWidth="1.5" />
        <path d="M6 7h8M6 10h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open]);

  const navContent = (
    <nav className="flex flex-col gap-1 px-3" aria-label="Main">
      {NAV_ITEMS.map((item, index) => {
        const showSection =
          index === 0 || NAV_ITEMS[index - 1]?.section !== item.section;
        const active =
          pathname === item.href ||
          (item.href === '/' && pathname === '/phase1') ||
          (item.href !== '/' && pathname.startsWith(item.href));
        return (
          <div key={item.href}>
            {showSection && (
              <p className="mb-1 mt-3 px-3 text-[10px] font-semibold uppercase tracking-wide text-white/45 first:mt-0">
                {item.section}
              </p>
            )}
            <Link
              href={item.href}
              aria-current={active ? 'page' : undefined}
              className={`flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium transition-all ${
                active
                  ? 'bg-white/20 text-on-primary shadow-sm'
                  : 'text-white/70 hover:bg-white/10 hover:text-on-primary'
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          </div>
        );
      })}
    </nav>
  );

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-40 flex h-14 items-center justify-between bg-primary px-4 shadow-sidebar md:hidden">
        <p className="text-sm font-semibold text-on-primary">ClaimGuard AI</p>
        <button
          type="button"
          aria-expanded={open}
          aria-controls="sidebar-nav"
          aria-label={open ? 'Close menu' : 'Open menu'}
          onClick={() => setOpen((v) => !v)}
          className="rounded-xl bg-white/15 p-2 text-on-primary"
        >
          {open ? (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          )}
        </button>
      </header>

      {open && (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-40 bg-black/20 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        id="sidebar-nav"
        className={`fixed z-50 flex flex-col bg-primary transition-transform duration-200 ${
          open ? 'translate-x-0' : '-translate-x-full'
        } inset-y-0 left-0 w-64 shadow-sidebar md:translate-x-0 md:inset-y-4 md:left-4 md:w-[220px] md:rounded-[28px]`}
      >
        <div className="hidden px-6 pt-8 md:block">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/20 text-lg font-bold text-on-primary">
            C
          </div>
          <p className="mt-4 text-base font-semibold text-on-primary">ClaimGuard AI</p>
          <p className="text-xs text-white/60">Claim pre-validation</p>
        </div>

        <div className="flex-1 pt-16 md:pt-8">{navContent}</div>
      </aside>
    </>
  );
}

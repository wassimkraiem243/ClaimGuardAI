'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

const NAV_ITEMS = [
  {
    href: '/',
    label: 'Dashboard',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <rect x="2" y="2" width="7" height="7" rx="2" stroke="currentColor" strokeWidth="1.5" />
        <rect x="11" y="2" width="7" height="7" rx="2" stroke="currentColor" strokeWidth="1.5" />
        <rect x="2" y="11" width="7" height="7" rx="2" stroke="currentColor" strokeWidth="1.5" />
        <rect x="11" y="11" width="7" height="7" rx="2" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    ),
  },
  {
    href: '/phase1',
    label: 'Phase 1 flow',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M4 4h12v12H4z" stroke="currentColor" strokeWidth="1.5" />
        <path d="M7 8h6M7 12h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    href: '/findings',
    label: 'Validations',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path
          d="M10 2L3 6v8l7 4 7-4V6l-7-4z"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        <path d="M10 10l7-4M10 10v8M10 10L3 6" stroke="currentColor" strokeWidth="1.5" />
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
    <nav className="flex flex-col gap-2 px-3" aria-label="Main">
      {NAV_ITEMS.map((item) => {
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
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

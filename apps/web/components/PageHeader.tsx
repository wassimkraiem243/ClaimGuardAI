import Link from 'next/link';
import type { ReactNode } from 'react';

export function PrimaryButtonLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center justify-center rounded-2xl bg-primary px-5 py-2.5 text-sm font-medium text-on-primary shadow-float transition-colors hover:bg-primary-hover"
    >
      {children}
    </Link>
  );
}

export function SecondaryButtonLink({
  href,
  children,
  disabled,
}: {
  href: string;
  children: ReactNode;
  disabled?: boolean;
}) {
  if (disabled) {
    return (
      <span
        aria-disabled="true"
        className="inline-flex cursor-not-allowed items-center justify-center rounded-2xl bg-surface-muted px-5 py-2.5 text-sm font-medium text-text-faint shadow-float"
      >
        {children}
      </span>
    );
  }

  return (
    <Link
      href={href}
      className="inline-flex items-center justify-center rounded-2xl bg-surface px-5 py-2.5 text-sm font-medium text-text-muted shadow-float transition-colors hover:text-text"
    >
      {children}
    </Link>
  );
}

export function FilterChipLink({
  href,
  active,
  children,
  grouped,
}: {
  href: string;
  active: boolean;
  children: ReactNode;
  grouped?: boolean;
}) {
  if (grouped) {
    return (
      <Link
        href={href}
        aria-current={active ? 'true' : undefined}
        className={
          active
            ? 'rounded-xl bg-primary px-3.5 py-1.5 text-sm font-medium text-on-primary'
            : 'rounded-xl px-3.5 py-1.5 text-sm font-medium text-text-muted transition-colors hover:bg-surface-muted hover:text-text'
        }
      >
        {children}
      </Link>
    );
  }

  return (
    <Link
      href={href}
      aria-current={active ? 'true' : undefined}
      className={
        active
          ? 'rounded-2xl bg-primary px-4 py-2 text-sm font-medium text-on-primary shadow-float'
          : 'rounded-2xl bg-surface px-4 py-2 text-sm font-medium text-text-muted shadow-float transition-colors hover:text-text'
      }
    >
      {children}
    </Link>
  );
}

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: { href: string; label: string };
  trailing?: ReactNode;
  children?: ReactNode;
}

export function PageHeader({ title, description, action, trailing, children }: PageHeaderProps) {
  return (
    <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text sm:text-3xl">{title}</h1>
        {description && <p className="mt-1.5 text-sm text-text-muted">{description}</p>}
        {children}
      </div>
      {trailing ?? (action ? <PrimaryButtonLink href={action.href}>{action.label}</PrimaryButtonLink> : null)}
    </header>
  );
}

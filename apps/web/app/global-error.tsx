'use client';

import './globals.css';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg p-8 text-text">
        <h2 className="text-xl font-semibold">Something went wrong</h2>
        <p className="mt-2 text-sm text-text-muted">{error.message}</p>
        <button
          type="button"
          onClick={() => reset()}
          className="mt-4 inline-flex rounded-md bg-primary px-4 py-2 text-sm font-medium text-on-primary shadow-sm hover:bg-primary-hover"
        >
          Try again
        </button>
      </body>
    </html>
  );
}

'use client';

import { Logo } from '@/components/Logo';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ reset }: ErrorProps) {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="flex flex-col items-center text-center">
        <Logo size={72} animated />

        <h1 className="mt-6 text-7xl font-bold tracking-tight text-text-1">
          Oops
        </h1>

        <p className="mt-3 text-2xl font-semibold text-text-1">
          Something went wrong
        </p>

        <p className="mt-3 max-w-xl text-base text-text-2">
          An unexpected error occurred. You can try again or return to the home
          page.
        </p>

        <button onClick={reset} className="btn-primary mt-8">
          Try again
        </button>
      </div>
    </main>
  );
}

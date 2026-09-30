import Link from 'next/link';
import { Logo } from '@/components/Logo';

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="flex flex-col items-center text-center">
        <Logo size={72} animated/>

        <h1 className="mt-6 text-7xl font-bold tracking-tight text-text-1">
            404
        </h1>

        <p className="mt-3 text-2xl font-semibold text-text-1">
            Page not found
        </p>

        <p className="mt-3 max-w-xl text-base text-text-2">
            The page you&#39;re looking for doesn&#39;t exist or may have been moved.
        </p>

        <Link href="/" className="btn-primary mt-8">
          Back to Home
        </Link>
      </div>
    </main>
  );
}
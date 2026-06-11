import Link from 'next/link';
import { Logo } from '../components/Logo';

export default function NotFound() {
  return (
    <div className="flex justify-center items-center h-screen dark:bg-gray-900">
      <div className="text-center">
        <Logo className="mx-auto mb-4" />
        <h1 className="text-3xl font-bold dark:text-white">404 — Page not found</h1>
        <p className="text-lg dark:text-gray-400">
          The page you are looking for does not exist.
        </p>
        <Link href="/">
          <a className="text-blue-600 dark:text-blue-400 hover:underline">
            Back to home
          </a>
        </Link>
      </div>
    </div>
  );
}
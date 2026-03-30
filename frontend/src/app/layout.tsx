import type { Metadata } from 'next';
import './globals.css';
import { LoadingWrapper } from '@/components/LoadingScreen';

export const metadata: Metadata = {
  title: 'PRISM',
  description: 'OSINT Intelligence Platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg text-text-1 antialiased prism-ready">
        <LoadingWrapper>{children}</LoadingWrapper>
      </body>
    </html>
  );
}

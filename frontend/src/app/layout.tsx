import type { Metadata } from 'next';
import './globals.css';
import { LoadingWrapper } from '@/components/LoadingScreen';

export const metadata: Metadata = {
  title: 'PRISM — Open Source Intelligence Platform',
  description: 'Professional OSINT toolkit for domain reconnaissance, email verification, username search, threat intelligence, and more. Powered by AI analysis.',
  keywords: ['OSINT', 'intelligence', 'reconnaissance', 'cybersecurity', 'threat intelligence', 'email verification', 'domain lookup', 'username search'],
  authors: [{ name: 'NovaCode37' }],
  openGraph: {
    title: 'PRISM — Open Source Intelligence Platform',
    description: 'Professional OSINT toolkit for domain reconnaissance, email verification, username search, threat intelligence, and more.',
    url: 'https://getprism.su',
    siteName: 'PRISM OSINT',
    type: 'website',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary',
    title: 'PRISM — Open Source Intelligence Platform',
    description: 'Professional OSINT toolkit with AI-powered analysis.',
  },
  robots: {
    index: true,
    follow: true,
  },
  metadataBase: new URL('https://getprism.su'),
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="canonical" href="https://getprism.su/" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'WebApplication',
              name: 'PRISM',
              url: 'https://getprism.su',
              description: 'Professional OSINT toolkit for domain reconnaissance, email verification, username search, threat intelligence, and AI-powered analysis.',
              applicationCategory: 'SecurityApplication',
              operatingSystem: 'Web',
              author: {
                '@type': 'Person',
                name: 'NovaCode37',
                url: 'https://github.com/NovaCode37',
              },
              offers: {
                '@type': 'Offer',
                price: '0',
                priceCurrency: 'USD',
              },
            }),
          }}
        />
      </head>
      <body className="min-h-screen bg-bg text-text-1 antialiased prism-ready">
        <LoadingWrapper>{children}</LoadingWrapper>
      </body>
    </html>
  );
}

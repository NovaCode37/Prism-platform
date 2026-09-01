import type { Metadata } from 'next';
import './globals.css';
import { LoadingWrapper } from '@/components/LoadingScreen';
import { I18nProvider } from '@/lib/i18n';

const SITE_URL = 'https://getprism.su';
const OG_IMAGE = 'https://raw.githubusercontent.com/NovaCode37/Prism-platform/main/docs/pics/main_showcase/main_showcase.png';
const TITLE = 'PRISM - Self-Hosted OSINT Platform';
const DESCRIPTION =
  'Self-hosted OSINT platform with 22+ modules. Recon any domain, IP, email, phone, or username in one real-time dashboard with an entity graph, OPSEC score, and HTML/PDF reports. Free, open source, runs with one docker compose up.';

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  keywords: [
    'OSINT',
    'self-hosted OSINT',
    'OSINT platform',
    'OSINT dashboard',
    'open source OSINT',
    'SpiderFoot alternative',
    'Maltego alternative',
    'reconnaissance',
    'threat intelligence',
    'cybersecurity',
    'domain recon',
    'IP lookup',
    'email breach check',
    'username search',
    'self-hosted security tools',
  ],
  authors: [{ name: 'Savelii Golubev', url: 'https://github.com/NovaCode37' }],
  creator: 'Savelii Golubev',
  applicationName: 'PRISM',
  alternates: { canonical: SITE_URL },
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    url: SITE_URL,
    siteName: 'PRISM OSINT',
    type: 'website',
    locale: 'en_US',
    images: [{ url: OG_IMAGE, alt: 'PRISM OSINT dashboard' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: TITLE,
    description: 'Self-hosted OSINT platform - recon domains, IPs, emails, phones, and usernames in one dashboard. Free & open source.',
    images: [OG_IMAGE],
  },
  robots: {
    index: true,
    follow: true,
  },
  metadataBase: new URL(SITE_URL),
};

const JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'PRISM',
  url: SITE_URL,
  description: DESCRIPTION,
  applicationCategory: 'SecurityApplication',
  operatingSystem: 'Web, Docker, Linux',
  softwareVersion: '2.7.0',
  license: 'https://opensource.org/licenses/MIT',
  sameAs: ['https://github.com/NovaCode37/Prism-platform'],
  author: {
    '@type': 'Person',
    name: 'Savelii Golubev',
    url: 'https://github.com/NovaCode37',
  },
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'USD',
  },
  featureList: [
    'WHOIS and DNS lookup',
    'Subdomain discovery (crt.sh)',
    'GeoIP mapping',
    'Threat intelligence (Shodan, VirusTotal, AbuseIPDB, Censys)',
    'Email breach checks',
    'Username search across 3000+ sites',
    'Dark web mirror checks',
    'OPSEC exposure scoring',
    'HTML, PDF, CSV and Markdown reports',
  ],
};

const THEME_INIT = `(function(){try{var t=localStorage.getItem('theme')||(window.matchMedia('(prefers-color-scheme: light)').matches?'light':'dark');document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }} />
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
      </head>
      <body className="min-h-screen bg-bg text-text-1 antialiased prism-ready">
        <I18nProvider>
          <LoadingWrapper>{children}</LoadingWrapper>
        </I18nProvider>
      </body>
    </html>
  );
}

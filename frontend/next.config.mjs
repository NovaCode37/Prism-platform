import { PHASE_DEVELOPMENT_SERVER } from 'next/constants.js';

function normalizeBasePath(value = '') {
  const trimmed = value.trim();
  if (!trimmed || trimmed === '/') return '';
  const path = trimmed.replace(/^\/+/, '').replace(/\/+$/, '');
  return path ? `/${path}` : '';
}

export default function nextConfig(phase) {
  const isDevServer = phase === PHASE_DEVELOPMENT_SERVER;
  const basePath = normalizeBasePath(process.env.NEXT_PUBLIC_BASE_PATH || '');

  return {
    ...(isDevServer ? {} : { output: 'export' }),
    ...(basePath ? { basePath } : {}),
    images: { unoptimized: true },
    allowedDevOrigins: ['127.0.0.1', 'localhost'],
    ...(isDevServer ? {
      async rewrites() {
        const apiBase = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080').replace(/\/+$/, '');
        return [
          { source: '/api/:path*', destination: `${apiBase}/api/:path*` },
        ];
      },
    } : {}),
  };
}

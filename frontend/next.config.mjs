const isProd = process.env.NODE_ENV === 'production';

function normalizeBasePath(value = '') {
  const trimmed = value.trim();
  if (!trimmed || trimmed === '/') return '';
  const path = trimmed.replace(/^\/+/, '').replace(/\/+$/, '');
  return path ? `/${path}` : '';
}

const basePath = normalizeBasePath(process.env.NEXT_PUBLIC_BASE_PATH || '');

const nextConfig = {
  ...(isProd ? { output: 'export' } : {}),
  ...(basePath ? { basePath } : {}),
  images: { unoptimized: true },
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
  ...(!isProd ? {
    async rewrites() {
      const apiBase = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080').replace(/\/+$/, '');
      return [
        { source: '/api/:path*', destination: `${apiBase}/api/:path*` },
      ];
    },
  } : {}),
};

export default nextConfig;

const isProd = process.env.NODE_ENV === 'production';

const nextConfig = {
  ...(isProd ? { output: 'export' } : {}),
  images: { unoptimized: true },
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
  ...(!isProd ? {
    async rewrites() {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      return [
        { source: '/api/:path*', destination: `${apiBase}/api/:path*` },
        { source: '/static/:path*', destination: `${apiBase}/static/:path*` },
      ];
    },
  } : {}),
};

export default nextConfig;

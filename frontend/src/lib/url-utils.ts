export function normalizeBasePath(value = ''): string {
  const trimmed = value.trim();
  if (!trimmed || trimmed === '/') return '';
  const path = trimmed.replace(/^\/+/, '').replace(/\/+$/, '');
  return path ? `/${path}` : '';
}

function normalizePath(path: string): string {
  return path.startsWith('/') ? path : `/${path}`;
}

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '');
}

export function buildApiUrl(path: string, apiBase = '', basePath = ''): string {
  const normalizedPath = normalizePath(path);
  const normalizedApiBase = stripTrailingSlash(apiBase.trim());
  if (normalizedApiBase) {
    return `${normalizedApiBase}${normalizedPath}`;
  }
  return `${normalizeBasePath(basePath)}${normalizedPath}`;
}

export type BuildWsUrlOptions = {
  apiBase?: string;
  apiKey?: string;
  basePath?: string;
  currentOrigin?: string;
};

export function buildWsUrl(scanId: string, options: BuildWsUrlOptions = {}): string {
  const path = buildApiUrl(`/ws/${encodeURIComponent(scanId)}`, options.apiBase, options.basePath);
  const origin = options.currentOrigin || (
    typeof window !== 'undefined' && window.location?.origin
      ? window.location.origin
      : 'http://localhost:3000'
  );
  const url = new URL(path, origin);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  if (options.apiKey) {
    url.searchParams.set('api_key', options.apiKey);
  }
  return url.toString();
}

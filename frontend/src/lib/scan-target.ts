import type { ScanType } from './types';

export function normalizeScanTarget(value: string): string {
  let normalized = value.trim();
  
  // Handle URLs with scheme
  const schemeSep = normalized.indexOf('://');
  if (schemeSep !== -1) {
    const scheme = normalized.slice(0, schemeSep).toLowerCase();
    if (scheme === 'http' || scheme === 'https') {
      // Extract host:port (strip path, query, hash)
      const afterScheme = normalized.slice(schemeSep + 3);
      const pathMatch = afterScheme.match(/^([^/?#]+)/);
      if (pathMatch) {
        normalized = pathMatch[1];
      } else {
        normalized = afterScheme;
      }
    }
  }
  
  // Remove trailing slash from host (if any)
  normalized = normalized.replace(/\/+$/, '');
  
  // Strip port if present
  const portMatch = normalized.match(/^([^:]+):\d+$/);
  if (portMatch) {
    normalized = portMatch[1];
  }

  // Email detection: lowercase the whole thing if it looks like an email
  if (normalized.includes('@') && !normalized.startsWith('@')) {
    return normalized.toLowerCase();
  }
  
  // Domain detection: lowercase if it contains a dot and no spaces
  if (normalized.includes('.') && !/\s/.test(normalized)) {
    return normalized.toLowerCase();
  }
  
  return normalized;
}

export function detectScanType(value: string): ScanType {
  const s = normalizeScanTarget(value);
  if (/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(s)) return 'email';
  // IPv6 detection (basic)
  if (/^([0-9a-fA-F]{1,4}:){1,7}[0-9a-fA-F]{1,4}$/.test(s) || /^::[0-9a-fA-F]{0,4}$/.test(s) || /^[0-9a-fA-F:]+:[0-9a-fA-F:]+$/.test(s)) return 'ip';
  if (/^(\d{1,3}\.){3}\d{1,3}$/.test(s)) return 'ip';
  if (/^\+?[\d][\d\s().-]{6,}$/.test(s)) return 'phone';
  if (s.startsWith('@')) return 'username';
  // mailto: detection
  if (s.toLowerCase().startsWith('mailto:')) return 'email';
  if (s.includes('.') && !/\s/.test(s)) return 'domain';
  return 'username';
}
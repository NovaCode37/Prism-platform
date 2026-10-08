import type { ScanResults } from './types';

// Fields that change on every run without the target changing.
// Mirrors _VOLATILE_KEYS in web/watchlist.py; scripts/test-scan-diff.mjs fails if they drift apart.
export const VOLATILE_KEYS: ReadonlySet<string> = new Set([
  'response_time', 'started_at', 'completed_at', 'timestamp', 'generated_at',
  'duration', 'scan_id', 'report_path', 'graph', 'last_snapshot', 'first_snapshot',
  'status_reason', 'total_urls', 'scanned_at', 'elapsed', 'took',
]);

const SKIPPED_MODULES = new Set(['report_path', 'map_data', 'graph']);

export type DiffStatus = 'added' | 'removed' | 'changed' | 'same';

export interface DiffRow {
  key: string;
  status: DiffStatus;
  valA?: string;
  valB?: string;
}

function stripVolatile(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stripVolatile);
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {};
    for (const k of Object.keys(value).sort()) {
      if (VOLATILE_KEYS.has(k)) continue;
      out[k] = stripVolatile((value as Record<string, unknown>)[k]);
    }
    return out;
  }
  return value;
}

function stringify(value: unknown): string {
  if (value && typeof value === 'object') return JSON.stringify(stripVolatile(value));
  return String(value ?? '');
}

// Accounts found by blackbird / maigret are identified by site and url.
function identity(item: unknown): string | null {
  if (!item || typeof item !== 'object' || Array.isArray(item)) return null;
  const { site, url } = item as { site?: unknown; url?: unknown };
  const parts = [site, url].filter(p => typeof p === 'string' && p !== '');
  return parts.length ? parts.join(' ') : null;
}

function flattenValue(flat: Record<string, string>, key: string, value: unknown) {
  if (Array.isArray(value) && value.length > 0 && value.every(item => identity(item) !== null)) {
    for (const item of value) {
      let itemKey = `${key}[${identity(item)}]`;
      for (let n = 2; itemKey in flat; n++) itemKey = `${key}[${identity(item)} #${n}]`;
      flat[itemKey] = stringify(item);
    }
    return;
  }
  flat[key] = stringify(value);
}

export function flattenResults(results: ScanResults): Record<string, string> {
  const flat: Record<string, string> = {};
  for (const [mod, data] of Object.entries(results)) {
    if (!data || SKIPPED_MODULES.has(mod)) continue;
    if (typeof data === 'object' && !Array.isArray(data)) {
      for (const [k, v] of Object.entries(data as Record<string, unknown>)) {
        if (VOLATILE_KEYS.has(k)) continue;
        flattenValue(flat, `${mod}.${k}`, v);
      }
    } else {
      flattenValue(flat, mod, data);
    }
  }
  return flat;
}

export function diffResults(a: Record<string, string>, b: Record<string, string>): DiffRow[] {
  const allKeys = Array.from(new Set([...Object.keys(a), ...Object.keys(b)]));
  const rows: DiffRow[] = [];
  for (const key of allKeys.sort()) {
    const inA = key in a;
    const inB = key in b;
    if (inA && inB) {
      rows.push({ key, status: a[key] === b[key] ? 'same' : 'changed', valA: a[key], valB: b[key] });
    } else if (inA) {
      rows.push({ key, status: 'removed', valA: a[key] });
    } else {
      rows.push({ key, status: 'added', valB: b[key] });
    }
  }
  return rows;
}

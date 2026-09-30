import type { ScanType, ScanResults, ScanMeta, UrlScanResult, CryptoResult, DarkWebResult, QrResult, HeaderAnalysisResult, MetaResult, Watchlist, WatchlistAlert, UsageData } from './types';
import { getPrismApiKey, getPrismApiUrl, getPrismBasePath } from './prism-config';
import { buildApiUrl, buildWsUrl, normalizeBasePath } from './url-utils';

function apiUrl(path: string): string {
  return buildApiUrl(path, getPrismApiUrl(), getPrismBasePath());
}

function backendLabel(): string {
  return getPrismApiUrl() || normalizeBasePath(getPrismBasePath()) || 'same-origin backend';
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const apiKey = getPrismApiKey();
  return apiKey ? { 'X-API-Key': apiKey, ...extra } : extra;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  let r: Response;
  try {
    r = await fetch(apiUrl(path), {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new Error(`Cannot reach backend at ${backendLabel()} - is it running?`);
  }
  const text = await r.text();
  if (!r.ok) {
    let detail = text.slice(0, 200);
    try { detail = JSON.parse(text)?.detail ?? detail; } catch {}
    throw new Error(`HTTP ${r.status}: ${detail}`);
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`Invalid JSON from server: ${text.slice(0, 120)}`);
  }
}

export async function startScan(target: string, scan_type: ScanType, modules: string[], force_refresh = false): Promise<{ scan_id: string }> {
  return post('/api/scan', { target, scan_type, modules, force_refresh });
}

export async function getScan(id: string): Promise<ScanMeta & { results: ScanResults }> {
  const r = await fetch(apiUrl(`/api/scan/${id}`), { headers: authHeaders() });
  return r.json();
}

export async function scanUrl(url: string): Promise<UrlScanResult> {
  return post('/api/url-scan', { url });
}

export async function lookupMac(mac: string): Promise<import('./types').MacResult> {
  return post('/api/mac-lookup', { mac });
}

export async function lookupCrypto(address: string): Promise<CryptoResult> {
  return post('/api/crypto', { address });
}

export async function searchDarkweb(query: string): Promise<DarkWebResult> {
  return post('/api/darkweb', { query });
}

export async function decodeQr(file: File): Promise<QrResult> {
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch(apiUrl('/api/qr-decode'), { method: 'POST', headers: authHeaders(), body: fd });
  return r.json();
}

export async function analyzeHeaders(headers: string): Promise<HeaderAnalysisResult> {
  return post('/api/email-headers', { headers });
}

export async function extractMetadata(file: File): Promise<MetaResult> {
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch(apiUrl('/api/metadata'), { method: 'POST', headers: authHeaders(), body: fd });
  return r.json();
}

export async function generateAiSummary(scan_id: string): Promise<{ summary: string; model: string; error?: string }> {
  return post('/api/ai/summary', { scan_id });
}

export async function sendAiChat(scan_id: string, message: string): Promise<{ reply: string; error?: string }> {
  return post('/api/ai/chat', { scan_id, message });
}

export async function getMapData(scanId: string): Promise<unknown> {
  const r = await fetch(apiUrl(`/api/scan/${scanId}/map`), { headers: authHeaders() });
  return r.json();
}

export async function getGraphData(scanId: string): Promise<unknown> {
  const r = await fetch(apiUrl(`/api/scan/${scanId}/graph`), { headers: authHeaders() });
  return r.json();
}

export function getUsage(): Promise<UsageData> {
  return get('/api/usage');
}

export function getWsUrl(scanId: string): string {
  return buildWsUrl(scanId, {
    apiBase: getPrismApiUrl(),
    apiKey: getPrismApiKey(),
    basePath: getPrismBasePath(),
  });
}

export type ScanListItem = {
  scan_id: string;
  target: string;
  scan_type: string;
  status: string;
  started_at: string;
};

export async function listScans(): Promise<ScanListItem[]> {
  const r = await fetch(apiUrl('/api/scans'), { headers: authHeaders() });
  if (!r.ok) return [];
  return r.json();
}

export async function clearScans(): Promise<{ deleted: number }> {
  const r = await fetch(apiUrl('/api/scans'), {
    method: 'DELETE',
    headers: authHeaders(),
  });

  if (!r.ok) {
    throw new Error('Failed to clear scan history');
  }

  return r.json();
}


export async function fetchReportBlob(scanId: string, format: 'html' | 'pdf', lang?: string): Promise<Blob> {
  const suffix = format === 'pdf' ? '/pdf' : '';
  const q = lang ? `?lang=${encodeURIComponent(lang)}` : '';
  const r = await fetch(apiUrl(`/api/scan/${scanId}/report${suffix}${q}`), { headers: authHeaders() });
  if (!r.ok) {
    const text = await r.text();
    let detail = text.slice(0, 200);
    try { detail = JSON.parse(text)?.detail ?? detail; } catch {}
    throw new Error(`HTTP ${r.status}: ${detail}`);
  }
  return r.blob();
}

export async function fetchGraphExport(scanId: string, fmt: 'graphml' | 'gexf'): Promise<Blob> {
  const r = await fetch(apiUrl(`/api/scan/${scanId}/graph/export?fmt=${fmt}`), { headers: authHeaders() });
  if (!r.ok) {
    const text = await r.text();
    let detail = text.slice(0, 200);
    try { detail = JSON.parse(text)?.detail ?? detail; } catch {}
    throw new Error(`HTTP ${r.status}: ${detail}`);
  }
  return r.blob();
}

async function get<T>(path: string): Promise<T> {
  let r: Response;
  try {
    r = await fetch(apiUrl(path), { headers: authHeaders() });
  } catch {
    throw new Error(`Cannot reach backend at ${backendLabel()} - is it running?`);
  }
  const text = await r.text();
  if (!r.ok) {
    let detail = text.slice(0, 200);
    try { detail = JSON.parse(text)?.detail ?? detail; } catch {}
    throw new Error(`HTTP ${r.status}: ${detail}`);
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`Invalid JSON from server: ${text.slice(0, 120)}`);
  }
}

async function del(path: string): Promise<void> {
  const r = await fetch(apiUrl(path), { method: 'DELETE', headers: authHeaders() });
  if (!r.ok) {
    const text = await r.text();
    let detail = text.slice(0, 200);
    try { detail = JSON.parse(text)?.detail ?? detail; } catch {}
    throw new Error(`HTTP ${r.status}: ${detail}`);
  }
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  let r: Response;
  try {
    r = await fetch(apiUrl(path), {
      method: 'PATCH',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(`Cannot reach backend at ${backendLabel()} - is it running?`);
  }
  const text = await r.text();
  if (!r.ok) {
    let detail = text.slice(0, 200);
    try { detail = JSON.parse(text)?.detail ?? detail; } catch {}
    throw new Error(`HTTP ${r.status}: ${detail}`);
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`Invalid JSON from server: ${text.slice(0, 120)}`);
  }
}

export function listWatchlists(): Promise<{ watchlists: Watchlist[] }> {
  return get('/api/watchlist');
}

export function createWatchlist(body: {
  target: string;
  scan_type: ScanType | 'auto';
  modules: string[];
  interval_hours: number;
  webhook_url?: string;
}): Promise<Watchlist> {
  return post('/api/watchlist', body);
}

export function deleteWatchlist(id: string): Promise<void> {
  return del(`/api/watchlist/${id}`);
}

export function setWatchlistPaused(id: string, paused: boolean): Promise<Watchlist> {
  return patch(`/api/watchlist/${id}`, { paused });
}

export function testWebhook(webhook_url: string): Promise<{ ok: boolean; url: string }> {
  return post('/api/watchlist/test-webhook', { webhook_url });
}

export function getWatchlistAlerts(id: string): Promise<{ id: string; alerts: WatchlistAlert[] }> {
  return get(`/api/watchlist/${id}/alerts`);
}


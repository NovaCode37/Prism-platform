import type { ScanType, ScanResults, ScanMeta, UrlScanResult, CryptoResult, DarkWebResult, QrResult, HeaderAnalysisResult, MetaResult } from './types';

const API = process.env.NEXT_PUBLIC_API_URL || '';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return API_KEY ? { 'X-API-Key': API_KEY, ...extra } : extra;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`${API}${path}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new Error(`Cannot reach backend at ${API || 'http://localhost:8080'} — is it running?`);
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

export async function startScan(target: string, scan_type: ScanType, modules: string[]): Promise<{ scan_id: string }> {
  return post('/api/scan', { target, scan_type, modules });
}

export async function getScan(id: string): Promise<ScanMeta & { results: ScanResults }> {
  const r = await fetch(`${API}/api/scan/${id}`, { headers: authHeaders() });
  return r.json();
}

export async function scanUrl(url: string): Promise<UrlScanResult> {
  return post('/api/url-scan', { url });
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
  const r = await fetch(`${API}/api/qr-decode`, { method: 'POST', headers: authHeaders(), body: fd });
  return r.json();
}

export async function analyzeHeaders(headers: string): Promise<HeaderAnalysisResult> {
  return post('/api/email-headers', { headers });
}

export async function extractMetadata(file: File): Promise<MetaResult> {
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch(`${API}/api/metadata`, { method: 'POST', headers: authHeaders(), body: fd });
  return r.json();
}

export async function generateAiSummary(scan_id: string): Promise<{ summary: string; model: string; error?: string }> {
  return post('/api/ai/summary', { scan_id });
}

export async function sendAiChat(scan_id: string, message: string): Promise<{ reply: string; error?: string }> {
  return post('/api/ai/chat', { scan_id, message });
}

export async function getMapData(scanId: string): Promise<unknown> {
  const r = await fetch(`${API}/api/scan/${scanId}/map`, { headers: authHeaders() });
  return r.json();
}

export async function getGraphData(scanId: string): Promise<unknown> {
  const r = await fetch(`${API}/api/scan/${scanId}/graph`, { headers: authHeaders() });
  return r.json();
}

export function getWsUrl(scanId: string): string {
  const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
  const ws = base.replace(/^http/, 'ws');
  return API_KEY ? `${ws}/ws/${scanId}?api_key=${API_KEY}` : `${ws}/ws/${scanId}`;
}

export function getReportUrl(scanId: string): string {
  return API_KEY
    ? `${API}/api/scan/${scanId}/report?api_key=${API_KEY}`
    : `${API}/api/scan/${scanId}/report`;
}

export function getReportPdfUrl(scanId: string): string {
  return API_KEY
    ? `${API}/api/scan/${scanId}/report/pdf?api_key=${API_KEY}`
    : `${API}/api/scan/${scanId}/report/pdf`;
}

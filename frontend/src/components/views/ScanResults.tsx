'use client';
import { useState, useEffect, useRef } from 'react';
import { ExternalLink, Printer, Download, Shield, AlertTriangle, Globe, Server, Lock, User, Clock, Zap, Phone, MessageCircle, Map, GitBranch, Code, Brain, ChevronDown, ChevronUp, SendHorizontal, Mail, Copy, Eye, ShieldAlert, ArrowUp, FileSpreadsheet, FileText, Search, RefreshCw, Loader2, Github } from 'lucide-react';
import type { ScanResults, ScanMeta, OpsecFinding, ModuleStatus, ModuleStatusFields, ScanType } from '@/lib/types';
import { fetchReportBlob, generateAiSummary, sendAiChat, getMapData, getGraphData, startScan, getScan } from '@/lib/api';
import { useTranslations } from '@/lib/i18n';

type MapMarker = {
  lat: number;
  lng: number;
  label: string;
  city?: string;
  country?: string;
  org?: string;
  ip?: string;
  approximate?: boolean;
  precision?: string;
  bbox?: number[];
};

type MapData = {
  markers: MapMarker[];
  center: { lat: number; lng: number } | null;
  zoom?: number | null;
  info?: { reason?: string; country?: string | null; carrier?: string | null; region?: string | null } | null;
};

let leafletLoader: Promise<any> | null = null;

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string));
}

function filenameSegment(value: string): string {
  return value.trim().replace(/[^a-z0-9._-]+/gi, '-').replace(/^-+|-+$/g, '') || 'scan';
}

function loadLeaflet(): Promise<any> {
  const w = window as any;
  if (w.L) return Promise.resolve(w.L);
  if (leafletLoader) return leafletLoader;
  leafletLoader = new Promise((resolve, reject) => {
    if (!document.querySelector('link[data-leaflet]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      link.setAttribute('data-leaflet', '1');
      document.head.appendChild(link);
    }
    const existing = document.querySelector('script[data-leaflet]') as HTMLScriptElement | null;
    if (existing) {
      existing.addEventListener('load', () => resolve((window as any).L), { once: true });
      existing.addEventListener('error', () => reject(new Error('Failed to load Leaflet')), { once: true });
      return;
    }
    const s = document.createElement('script');
    s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    s.setAttribute('data-leaflet', '1');
    s.onload = () => resolve((window as any).L);
    s.onerror = () => reject(new Error('Failed to load Leaflet'));
    document.head.appendChild(s);
  });
  return leafletLoader;
}

function MapView({ scanId, onCopy }: { scanId: string; onCopy: (value: string) => void }) {
  const [data, setData] = useState<MapData | null>(null);
  const [error, setError] = useState('');
  const mapHostRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markersRef = useRef<any>(null);

  useEffect(() => {
    getMapData(scanId)
      .then((d: any) => { if (d.error) setError(d.error); else setData(d as MapData); })
      .catch(e => setError(e.message));
  }, [scanId]);

  useEffect(() => {
    if (!data?.markers?.length || !mapHostRef.current) return;
    let cancelled = false;
    loadLeaflet()
      .then((L) => {
        if (cancelled || !mapHostRef.current) return;
        if (!mapRef.current) {
          mapRef.current = L.map(mapHostRef.current, { zoomControl: true });
          mapRef.current.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener noreferrer">Leaflet</a>');
          L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap', maxZoom: 18,
          }).addTo(mapRef.current);
        }

        if (markersRef.current) markersRef.current.clearLayers();
        else markersRef.current = L.layerGroup().addTo(mapRef.current);

        const bounds: [number, number][] = [];
        for (const m of data.markers) {
          if (!Number.isFinite(m.lat) || !Number.isFinite(m.lng)) continue;
          const parts = [
            m.ip ? `IP: ${escapeHtml(m.ip)}` : '',
            m.city || m.country ? `Location: ${escapeHtml([m.city, m.country].filter(Boolean).join(', '))}` : '',
            m.org ? `Organization: ${escapeHtml(m.org)}` : '',
            m.precision ? `Precision: ${escapeHtml(m.precision)}` : '',
          ].filter(Boolean);
          const popup = `<b>${escapeHtml(m.label || m.ip || 'Location')}</b><br/>${parts.join('<br/>')}`;
          const hasBbox = m.approximate && Array.isArray(m.bbox) && m.bbox.length === 4;
          if (hasBbox) {
            const sw: [number, number] = [m.bbox![0], m.bbox![2]];
            const ne: [number, number] = [m.bbox![1], m.bbox![3]];
            L.rectangle([sw, ne], { color: '#4f8ef7', weight: 1, fillColor: '#4f8ef7', fillOpacity: 0.10 })
              .bindPopup(`${popup}<br/><i>Approximate ${escapeHtml(m.precision || 'area')}-level — phone numbers don't expose an exact location</i>`)
              .addTo(markersRef.current);
            bounds.push(sw, ne);
          } else if (m.approximate) {
            const radius = m.precision === 'country' ? 250000 : 70000;
            L.circle([m.lat, m.lng], { radius, color: '#4f8ef7', weight: 1, fillColor: '#4f8ef7', fillOpacity: 0.12 })
              .bindPopup(`${popup}<br/><i>Approximate ${escapeHtml(m.precision || 'area')}-level location</i>`)
              .addTo(markersRef.current);
            bounds.push([m.lat, m.lng]);
          } else {
            L.marker([m.lat, m.lng]).bindPopup(popup).addTo(markersRef.current);
            bounds.push([m.lat, m.lng]);
          }
        }

        if (bounds.length === 1) {
          mapRef.current.setView(bounds[0], typeof data.zoom === 'number' ? data.zoom : 10);
        } else if (bounds.length > 1) {
          mapRef.current.fitBounds(bounds, { padding: [24, 24] });
        }

        requestAnimationFrame(() => {
          if (!cancelled && mapRef.current) mapRef.current.invalidateSize();
        });
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to render map'));

    return () => {
      cancelled = true;
    };
  }, [data]);

  useEffect(() => () => {
    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
      markersRef.current = null;
    }
  }, []);

  if (error) return <div className="text-red text-sm">{error}</div>;
  if (!data) return <div className="text-text-3 text-sm animate-pulse">Loading map…</div>;
  if (!data.markers?.length) {
    if (data.info && (data.info.country || data.info.carrier || data.info.region)) {
      return (
        <div className="text-[12px]">
          <div className="text-text-2 mb-2">{data.info.reason || 'No precise coordinates available.'}</div>
          <div className="grid grid-cols-2 gap-x-8 gap-y-1 max-w-md">
            {data.info.country && <div className="dt-row"><span className="dt-label">Country</span><span className="dt-value">{data.info.country}</span></div>}
            {data.info.region && <div className="dt-row"><span className="dt-label">Region</span><span className="dt-value">{data.info.region}</span></div>}
            {data.info.carrier && <div className="dt-row"><span className="dt-label">Carrier</span><span className="dt-value">{data.info.carrier}</span></div>}
          </div>
        </div>
      );
    }
    return <div className="text-text-3 text-sm">No geolocation data available</div>;
  }

  const m = data.markers[0];

  return (
    <div>
      <div ref={mapHostRef} className="w-full rounded-md border border-border-1 h-64 sm:h-[360px]" />
      <div className="mt-3 grid grid-cols-2 gap-x-8 gap-y-1 text-[12px]">
        {m.ip && (
          <div className="dt-row">
            <span className="dt-label">IP</span>
            <div className="flex items-center gap-1.5">
              <span className="dt-value font-mono">{m.ip}</span>
              <CopyIconButton onClick={() => onCopy(m.ip ?? '')} label="Copy IP" />
            </div>
          </div>
        )}
        {(m.city || m.country) && <div className="dt-row"><span className="dt-label">Location</span><span className="dt-value">{[m.city, m.country].filter(Boolean).join(', ')}</span></div>}
        {m.org && <div className="dt-row"><span className="dt-label">Organization</span><span className="dt-value">{m.org}</span></div>}
        <div className="dt-row"><span className="dt-label">Coordinates</span><span className="dt-value font-mono">{m.lat.toFixed(4)}, {m.lng.toFixed(4)}</span></div>
        {m.precision && <div className="dt-row"><span className="dt-label">Precision</span><span className="dt-value">{m.precision}</span></div>}
        {m.approximate && <div className="dt-row"><span className="dt-label">Approximate</span><span className="dt-value">Yes</span></div>}
      </div>
      {data.markers.length > 1 && (
        <div className="mt-3 text-[10px] text-text-3">{data.markers.length} locations found</div>
      )}
    </div>
  );
}

function GraphView({ scanId }: { scanId: string }) {
  const { t } = useTranslations();
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'empty' | 'error'>('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const init = async () => {
      try {
        const graphData: any = await getGraphData(scanId);
        if (!graphData.nodes?.length) { setStatus('empty'); return; }

        const loadVis = () => new Promise<void>((resolve, reject) => {
          if ((window as { vis?: unknown }).vis) { resolve(); return; }
          const s = document.createElement('script');
          s.src = 'https://unpkg.com/vis-network/standalone/umd/vis-network.min.js';
          s.onload = () => resolve();
          s.onerror = () => reject(new Error('Failed to load vis-network'));
          document.head.appendChild(s);
        });
        await loadVis();

        if (cancelled || !containerRef.current) return;
        const vis = (window as any).vis;
        new vis.Network(
          containerRef.current,
          { nodes: new vis.DataSet(graphData.nodes), edges: new vis.DataSet(graphData.edges || []) },
          {
            nodes: { font: { color: '#e6edf3', size: 11, face: 'Inter' }, borderWidth: 2, borderWidthSelected: 3 },
            edges: { color: { color: '#4a5568', highlight: '#4f8ef7' }, font: { color: '#94a3b8', size: 9 }, smooth: { type: 'dynamic' } },
            physics: { stabilization: { iterations: 300 }, barnesHut: { gravitationalConstant: -8000 } },
            background: { color: 'transparent' },
            interaction: { hover: true, tooltipDelay: 100 },
          }
        );
        setStatus('ready');
      } catch (e) { if (!cancelled) { setError(e instanceof Error ? e.message : 'Error'); setStatus('error'); } }
    };
    init();
    return () => { cancelled = true; };
  }, [scanId]);

  return (
    <div>
      {status === 'loading' && <div className="text-text-3 text-sm animate-pulse py-4">Loading graph…</div>}
      {status === 'empty' && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <GitBranch size={28} className="text-text-3 opacity-40 mb-2" />
          <div className="text-text-3 text-sm">{t('results.graph.empty')}</div>
        </div>
      )}
      {status === 'error' && <div className="text-red text-sm py-4">{error}</div>}
      <div ref={containerRef} className="h-72 sm:h-[480px]" style={{ height: status === 'ready' ? undefined : 0, background: 'transparent' }} />
    </div>
  );
}

const RISK_COLOR: Record<string, string> = {
  CRITICAL: '#f85149', HIGH: '#f85149', MEDIUM: '#d29922', LOW: '#3fb950', MINIMAL: '#3fb950'
};

function DtRow({ label, value }: { label: string; value?: string | number | null }) {
  if (!value && value !== 0) return null;
  return (
    <div className="dt-row">
      <span className="dt-label">{label}</span>
      <span className="dt-value font-mono text-[11px]">{String(value)}</span>
    </div>
  );
}

function Card({ title, extra, children, onRefresh, refreshing = false }: { title?: string; extra?: React.ReactNode; children: React.ReactNode; onRefresh?: () => void; refreshing?: boolean }) {
  return (
    <div className="card mb-3">
      {title && (
        <div className="card-head flex items-center justify-between gap-2">
          <span>{title}</span>
          <div className="flex items-center gap-2">
            {extra}
            {onRefresh && (
              <button
                type="button"
                onClick={onRefresh}
                disabled={refreshing}
                className="text-text-3 hover:text-text-1 transition-colors p-1 rounded-sm hover:bg-surface-2 disabled:cursor-wait disabled:opacity-70"
                title={refreshing ? 'Refreshing…' : 'Refresh module'}
                aria-label={refreshing ? 'Refreshing module' : 'Refresh module'}
              >
                {refreshing ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
              </button>
            )}
          </div>
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}

function modStatus(m?: (ModuleStatusFields & { error?: string | null }) | null): ModuleStatus {
  if (!m) return 'ok';
  if (m.status === 'skipped' || m.status === 'rate_limited' || m.status === 'error') return m.status;
  if (m.error) return 'error';
  return 'ok';
}

const STATUS_BADGE: Record<Exclude<ModuleStatus, 'ok'>, { label: string; color: string; hint: string }> = {
  skipped: { label: 'SKIPPED', color: '#8b949e', hint: 'No API key configured' },
  rate_limited: { label: 'RATE LIMITED', color: '#d29922', hint: 'Provider rate limit reached' },
  error: { label: 'ERROR', color: '#f85149', hint: 'Module failed' },
};

function ModuleStatusBadge({ status, label }: { status: ModuleStatus; label?: string }) {
  if (status === 'ok') return null;
  const b = STATUS_BADGE[status];
  return (
    <span
      className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border"
      style={{ color: b.color, borderColor: `${b.color}55`, background: `${b.color}11` }}
    >
      {label ?? b.label}
    </span>
  );
}

function ModuleNotice({ status, reason }: { status: 'skipped' | 'rate_limited'; reason?: string }) {
  const b = STATUS_BADGE[status];
  return (
    <div className="text-[12px]" style={{ color: status === 'rate_limited' ? b.color : undefined }}>
      <span className="text-text-2">{reason || b.hint}</span>
      {status === 'skipped' && (
        <span className="text-text-3"> — add the key to <code className="font-mono">.env</code> to enable this module.</span>
      )}
    </div>
  );
}

function KeyModuleCard({ title, mod, children, onRefresh, refreshing = false }: {
  title: string;
  mod?: (ModuleStatusFields & { error?: string | null }) | null;
  children: React.ReactNode;
  onRefresh?: () => void;
  refreshing?: boolean;
}) {
  if (!mod) return null;
  const st = modStatus(mod);
  if (st === 'ok') return <Card title={title} onRefresh={onRefresh} refreshing={refreshing}>{children}</Card>;
  if (st === 'skipped' || st === 'rate_limited') {
    return (
      <Card title={title} extra={<ModuleStatusBadge status={st} />} onRefresh={onRefresh} refreshing={refreshing}>
        <ModuleNotice status={st} reason={mod.status_reason} />
      </Card>
    );
  }
  return null;
}

function CopyIconButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-text-3 hover:text-text-1 transition-colors p-0.5 rounded-sm hover:bg-surface-2"
      title={label}
      aria-label={label}
    >
      <Copy size={11} />
    </button>
  );
}

function FindingRow({ f }: { f: OpsecFinding }) {
  const cls = f.severity === 'HIGH' ? 'badge badge-high' : f.severity === 'MEDIUM' ? 'badge badge-med' : 'badge badge-low';
  return (
    <div className="finding-row">
      <span className={cls}>{f.severity}</span>
      <div className="flex-1 min-w-0">
        <div className="text-[12px] text-text-1">{f.message}</div>
        <div className="text-[10px] text-text-3">−{f.deduction} pts · {f.category}</div>
      </div>
    </div>
  );
}

const OPSEC_CATEGORY_INFO: Record<string, { label: string; tooltip: string }> = {
  data_exposure: {
    label: 'Data Exposure',
    tooltip: 'Sensitive data leaks: breached credentials, exposed emails, public PII.',
  },
  identity_opsec: {
    label: 'Identity OPSEC',
    tooltip: 'Re-use of identifiers across platforms: same username/email across many sites.',
  },
  infrastructure: {
    label: 'Infrastructure',
    tooltip: 'Exposed services, open ports, weak DNS/WHOIS hygiene, threat-intel hits.',
  },
  web_security: {
    label: 'Web Security',
    tooltip: 'TLS, security headers, certificate transparency, archived sensitive paths.',
  },
};

const TABS = [
  { id: 'findings', label: 'Findings', icon: Shield },
  { id: 'whois', label: 'WHOIS', icon: Globe },
  { id: 'dns', label: 'DNS', icon: Server },
  { id: 'subdomains', label: 'Subdomains', icon: Lock },
  { id: 'accounts', label: 'Accounts', icon: User },
  { id: 'github', label: 'GitHub', icon: Github },
  { id: 'threats', label: 'Threats', icon: AlertTriangle },
  { id: 'censys', label: 'Censys', icon: Eye },
  { id: 'darkweb', label: 'Dark Web', icon: ShieldAlert },
  { id: 'wayback', label: 'Wayback', icon: Clock },
  { id: 'email', label: 'Email', icon: Mail },
  { id: 'dorks', label: 'Dorks', icon: Zap },
  { id: 'phone', label: 'Phone', icon: Phone },
  { id: 'telegram', label: 'Telegram', icon: MessageCircle },
  { id: 'map', label: 'Map', icon: Map },
  { id: 'graph', label: 'Graph', icon: GitBranch },
  { id: 'json', label: 'JSON', icon: Code },
  { id: 'ai', label: 'AI', icon: Brain },
];

interface Props { scan: ScanMeta & { results: ScanResults }; }

export function ScanResults({ scan }: Props) {
  const { t: i18n, locale } = useTranslations();
  const [tab, setTab] = useState('findings');
  const [aiSummary, setAiSummary] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState('');
  const [aiModel, setAiModel] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState<{role:'user'|'ai'; text:string}[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [showJson, setShowJson] = useState(false);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const [copyToast, setCopyToast] = useState('');
  const [reportLoading, setReportLoading] = useState<'html' | 'pdf' | null>(null);
  const [localResults, setLocalResults] = useState<ScanResults>(scan.results);
  const [refreshingModules, setRefreshingModules] = useState<Record<string, boolean>>({});
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const contentRef = useRef<HTMLDivElement | null>(null);
  const r = localResults;
  const opsec = r.opsec;

  const showToast = (message: string) => {
    setCopyToast(message);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setCopyToast(''), 1200);
  };

  useEffect(() => {
    setLocalResults(scan.results);
    setRefreshingModules({});
  }, [scan.id, scan.results]);

  const isRefreshing = (module: string) => Boolean(refreshingModules[module]);

  const refreshModule = async (module: string, keys: string[] = [module]) => {
    if (isRefreshing(module)) return;
    setRefreshingModules(prev => ({ ...prev, [module]: true }));
    try {
      const { scan_id } = await startScan(scan.target, scan.scan_type as ScanType, [module], true);
      let done: { status: string; results: ScanResults; error?: string } | null = null;
      for (let i = 0; i < 90; i += 1) {
        await new Promise(res => setTimeout(res, 1500));
        const d = await getScan(scan_id) as unknown as { status: string; results: ScanResults; error?: string };
        if (d.status === 'completed') { done = d; break; }
        if (d.status === 'failed' || d.status === 'error') throw new Error(d.error || 'Module refresh failed');
      }
      if (!done) throw new Error('Module refresh timed out');
      const src = done.results as unknown as Record<string, unknown>;
      setLocalResults(prev => {
        const next = { ...prev } as Record<string, unknown>;
        for (const k of keys) if (k in src) next[k] = src[k];
        return next as ScanResults;
      });
      showToast('Module refreshed');
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Module refresh failed');
    } finally {
      setRefreshingModules(prev => ({ ...prev, [module]: false }));
    }
  };

  const copyValue = async (value: string | number | null | undefined) => {
    const text = String(value ?? '').trim();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      showToast('Copied!');
    } catch {
      showToast('Copy failed');
    }
  };

  useEffect(() => () => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
  }, []);

  useEffect(() => {
    const host = contentRef.current;
    if (!host) return;
    const onScroll = () => setShowBackToTop(host.scrollTop > 300);
    onScroll();
    host.addEventListener('scroll', onScroll, { passive: true });
    return () => host.removeEventListener('scroll', onScroll as EventListener);
  }, []);

  const sendChat = async () => {
    const msg = chatInput.trim();
    if (!msg || chatLoading) return;
    setChatInput('');
    setChatHistory(prev => [...prev, { role: 'user', text: msg }]);
    setChatLoading(true);
    try {
      const d = await sendAiChat(scan.id, msg);
      setChatHistory(prev => [...prev, { role: 'ai', text: d.reply || d.error || 'No response' }]);
    } catch (e) {
      setChatHistory(prev => [...prev, { role: 'ai', text: e instanceof Error ? e.message : 'Error' }]);
    }
    setChatLoading(false);
  };

  const runAi = async () => {
    setAiLoading(true); setAiError(''); setAiSummary('');
    try {
      const d = await generateAiSummary(scan.id);
      if (d.error) setAiError(d.error);
      else { setAiSummary(d.summary); setAiModel(d.model || ''); }
    } catch (e: unknown) {
      setAiError(e instanceof Error ? e.message : 'Unknown error');
    } finally { setAiLoading(false); }
  };

  const openReport = async (format: 'html' | 'pdf') => {
    if (reportLoading) return;
    setReportLoading(format);
    try {
      const blob = await fetchReportBlob(scan.id, format, locale);
      const url = URL.createObjectURL(blob);
      const opened = window.open(url, '_blank', 'noopener,noreferrer');
      if (!opened) {
        const a = document.createElement('a');
        a.href = url;
        a.download = `prism-report-${scan.id}.${format === 'pdf' ? 'pdf' : 'html'}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : 'Report open failed');
    } finally {
      setReportLoading(null);
    }
  };

  const downloadJson = () => {
    try {
      const blob = new Blob([JSON.stringify(scan.results, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `prism-${filenameSegment(scan.target)}-${filenameSegment(scan.id)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : 'JSON download failed');
    }
  };

  const downloadCsv = () => {
    try {
      const rows: string[][] = [['Module', 'Key', 'Value']];
      const flatten = (obj: unknown, prefix: string) => {
        if (obj === null || obj === undefined) return;
        if (Array.isArray(obj)) {
          obj.forEach((item, i) => flatten(item, `${prefix}[${i}]`));
        } else if (typeof obj === 'object') {
          for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
            flatten(v, prefix ? `${prefix}.${k}` : k);
          }
        } else {
          const parts = prefix.split('.');
          const mod = parts[0] || '';
          const key = parts.slice(1).join('.') || prefix;
          const val = String(obj).replace(/"/g, '""');
          rows.push([mod, key, `"${val}"`]);
        }
      };
      flatten(scan.results, '');
      const csv = rows.map(r => r.join(',')).join('\n');
      const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `prism-${filenameSegment(scan.target)}-${filenameSegment(scan.id)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : 'CSV download failed');
    }
  };

  const downloadMarkdown = () => {
    try {
      const lines: string[] = [];
      lines.push(`# PRISM Scan Report`);
      lines.push(`**Target:** ${scan.target}`);
      lines.push(`**Type:** ${scan.scan_type}`);
      if (scan.started_at) lines.push(`**Started:** ${scan.started_at.slice(0, 19).replace('T', ' ')}`);
      if (scan.completed_at) lines.push(`**Completed:** ${scan.completed_at.slice(0, 19).replace('T', ' ')}`);
      lines.push('');
      if (opsec) {
        lines.push(`## OPSEC Score: ${opsec.score}/100 (${opsec.risk_level})`);
        for (const [k, cat] of Object.entries(opsec.categories)) {
          lines.push(`- **${k.replace(/_/g, ' ')}:** ${cat.score}/${cat.max} (${cat.percent}%)`);
        }
        lines.push('');
      }
      if (opsec?.all_findings?.length) {
        lines.push('## Security Findings');
        for (const f of opsec.all_findings) {
          lines.push(`- [${f.severity}] ${f.message} (-${f.deduction} pts)`);
        }
        lines.push('');
      }
      if (r.whois && !r.whois.error) {
        lines.push('## WHOIS');
        if (r.whois.registrar) lines.push(`- Registrar: ${r.whois.registrar}`);
        if (r.whois.org) lines.push(`- Organization: ${r.whois.org}`);
        if (r.whois.country) lines.push(`- Country: ${r.whois.country}`);
        if (r.whois.creation_date) lines.push(`- Created: ${r.whois.creation_date.slice(0, 10)}`);
        lines.push('');
      }
      if (r.dns?.records) {
        lines.push('## DNS Records');
        for (const [type, recs] of Object.entries(r.dns.records)) {
          if (Array.isArray(recs) && recs.length) {
            lines.push(`### ${type}`);
            recs.forEach(rec => lines.push(`- ${typeof rec === 'object' ? JSON.stringify(rec) : rec}`));
          }
        }
        lines.push('');
      }
      if (r.cert_transparency?.subdomains?.length) {
        lines.push(`## Subdomains (${r.cert_transparency.subdomains.length})`);
        r.cert_transparency.subdomains.forEach(s => lines.push(`- ${s}`));
        lines.push('');
      }
      if (r.blackbird?.some(b => b.status === 'found')) {
        lines.push('## Accounts Found');
        lines.push('| Platform | URL |');
        lines.push('|----------|-----|');
        r.blackbird.filter(b => b.status === 'found').forEach(b => lines.push(`| ${b.site} | ${b.url} |`));
        lines.push('');
      }
      const md = lines.join('\n');
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `prism-${filenameSegment(scan.target)}-${filenameSegment(scan.id)}.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : 'Markdown download failed');
    }
  };

  const scanDuration = (() => {
    if (!scan.started_at || !scan.completed_at) return null;
    const ms = new Date(scan.completed_at).getTime() - new Date(scan.started_at).getTime();
    if (ms < 0 || !Number.isFinite(ms)) return null;
    if (ms < 1000) return `${ms}ms`;
    const s = ms / 1000;
    return s < 60 ? `${s.toFixed(1)}s` : `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
  })();

  const allEmails = (() => {
    const set = new Set<string>();
    if (r.whois?.emails) r.whois.emails.forEach(e => set.add(e));
    if (r.emailrep?.email) set.add(r.emailrep.email);
    if (r.breaches?.breaches) {
      for (const b of r.breaches.breaches) {
        if (typeof b === 'string' && b.includes('@')) set.add(b);
        if (typeof b === 'object' && b && 'email' in b) set.add((b as any).email);
      }
    }
    // Scan target if it looks like email
    if (scan.scan_type === 'email' && scan.target?.includes('@')) set.add(scan.target);
    return Array.from(set);
  })();

  const copyAllEmails = async () => {
    if (!allEmails.length) return;
    try {
      await navigator.clipboard.writeText(allEmails.join('\n'));
      showToast(i18n('results.emailsCopied') || 'Emails copied!');
    } catch {
      showToast(i18n('common.copyFailed') || 'Copy failed');
    }
  };

  const [accountFilter, setAccountFilter] = useState('');

  const skippedIpProviders = [
    { name: 'Shodan', mod: r.shodan, key: 'SHODAN_API_KEY' },
    { name: 'VirusTotal', mod: r.virustotal, key: 'VIRUSTOTAL_API_KEY' },
    { name: 'AbuseIPDB', mod: r.abuseipdb, key: 'ABUSEIPDB_API_KEY' },
    { name: 'Censys', mod: r.censys, key: 'CENSYS_API_ID / CENSYS_API_SECRET' },
  ].filter(({ mod }) => mod && modStatus(mod) === 'skipped');

  const showLimitedIpNotice = scan.scan_type === 'ip' && skippedIpProviders.length > 0;

  const visibleTabs = TABS.filter(t => {
    if (t.id === 'whois') return r.whois && !r.whois.error;
    if (t.id === 'dns') return r.dns?.records && Object.keys(r.dns.records).length > 0;
    if (t.id === 'subdomains') return r.cert_transparency?.subdomains?.length;
    if (t.id === 'accounts') return r.blackbird?.some(b => b.status === 'found');
    if (t.id === 'github') return r.github && modStatus(r.github) === 'ok';
    if (t.id === 'threats') return [r.virustotal, r.abuseipdb, r.shodan].some(m => m && modStatus(m) !== 'error');
    if (t.id === 'censys') return r.censys && modStatus(r.censys) !== 'error';
    if (t.id === 'darkweb') return r.onion && !r.onion.error && (r.onion.total_found ?? 0) > 0;
    if (t.id === 'wayback') return r.wayback;
    if (t.id === 'email') return r.emailrep || r.smtp || r.breaches;
    if (t.id === 'dorks') return r.dorks?.length;
    if (t.id === 'phone') return r.phone;
    if (t.id === 'telegram') return r.telegram;
    return true;
  });

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        const idx = visibleTabs.findIndex(t => t.id === tab);
        if (idx === -1) return;
        const next = e.key === 'ArrowRight'
          ? (idx + 1) % visibleTabs.length
          : (idx - 1 + visibleTabs.length) % visibleTabs.length;
        setTab(visibleTabs[next].id);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [tab, visibleTabs]);

  return (
    <div className="flex flex-col h-[calc(100vh-48px)] animate-fade-in">
      <div className="px-4 sm:px-5 py-3 border-b border-border-1 bg-surface-1 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-1.5">
            <div className="font-bold text-text-1 text-[15px] break-all">{scan.target}</div>
            <CopyIconButton onClick={() => copyValue(scan.target)} label="Copy target" />
          </div>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <span className="badge badge-info">{scan.scan_type?.toUpperCase()}</span>
            {scan.started_at && (
              <span className="text-[10px] text-text-3 hidden sm:inline">{scan.started_at.slice(0, 19).replace('T', ' ')}</span>
            )}
            {scanDuration && (
              <span className="text-[10px] text-green font-medium">{i18n('results.duration').replace('{duration}', scanDuration) !== `results.duration` ? i18n('results.duration').replace('{duration}', scanDuration) : `Completed in ${scanDuration}`}</span>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2 sm:justify-end">
          <button type="button" onClick={() => openReport('html')} disabled={reportLoading !== null}
            className="btn-ghost text-[11px] h-8 px-3">
            {reportLoading === 'html' ? '…' : <ExternalLink size={11} />} {i18n('results.htmlReport')}
          </button>
          <button type="button" onClick={() => openReport('pdf')} disabled={reportLoading !== null}
            className="btn-ghost text-[11px] h-8 px-3">
            {reportLoading === 'pdf' ? '…' : <Printer size={11} />} {i18n('results.pdfReport')}
          </button>
          <button type="button" onClick={downloadJson}
            className="btn-ghost text-[11px] h-8 px-3">
            <Download size={11} /> {i18n('results.jsonReport')}
          </button>
          <button type="button" onClick={downloadCsv}
            className="btn-ghost text-[11px] h-8 px-3">
            <FileSpreadsheet size={11} /> {i18n('results.csvReport') !== 'results.csvReport' ? i18n('results.csvReport') : 'CSV'}
          </button>
          <button type="button" onClick={downloadMarkdown}
            className="btn-ghost text-[11px] h-8 px-3">
            <FileText size={11} /> {i18n('results.mdReport') !== 'results.mdReport' ? i18n('results.mdReport') : 'Markdown'}
          </button>
          {allEmails.length >= 2 && (
            <button type="button" onClick={copyAllEmails}
              className="btn-ghost text-[11px] h-8 px-3">
              <Mail size={11} /> {i18n('results.copyAllEmails') !== 'results.copyAllEmails' ? i18n('results.copyAllEmails') : 'Copy emails'}
            </button>
          )}
        </div>
      </div>

      {showLimitedIpNotice && (
        <div className="px-4 sm:px-5 py-3 border-b border-border-1 bg-yellow/5">
          <div className="flex items-start gap-2.5 max-w-5xl">
            <AlertTriangle size={15} className="text-yellow mt-0.5 shrink-0" />
            <div className="min-w-0">
              <div className="text-[12px] font-semibold text-text-1">
                IP scan completed with limited provider data
              </div>
              <div className="text-[11px] text-text-2 mt-0.5 leading-relaxed">
                {skippedIpProviders.map(p => p.name).join(', ')} skipped because provider keys are missing. Add{' '}
                <code className="font-mono text-text-1">
                  {skippedIpProviders.map(p => p.key).join(', ')}
                </code>{' '}
                to <code className="font-mono text-text-1">.env</code> and recreate the container for deeper IP intelligence.
              </div>
            </div>
          </div>
        </div>
      )}

      {opsec && (
        <div className="px-4 sm:px-5 py-2.5 bg-surface-2 border-b border-border-1 flex items-center gap-4 sm:gap-6 overflow-x-auto scrollbar-hide">
          <div className="flex items-center gap-3">
            <div className="text-3xl font-black" style={{ color: RISK_COLOR[opsec.risk_level] }}>
              {opsec.score}
            </div>
            <div>
              <div className="text-[10px] text-text-3">OPSEC Score</div>
              <div className="text-[11px] font-bold" style={{ color: RISK_COLOR[opsec.risk_level] }}>
                {opsec.risk_level} RISK
              </div>
            </div>
          </div>
          {Object.entries(opsec.categories).map(([k, cat]) => {
            const info = OPSEC_CATEGORY_INFO[k];
            const label = info?.label ?? k.replace(/_/g, ' ');
            const tooltip = info?.tooltip ?? '';
            return (
              <div key={k} className="flex items-center gap-2" title={tooltip}>
                <div className="text-[10px] text-text-3 capitalize flex items-center gap-1 cursor-help">
                  {label}
                  {tooltip && <span aria-hidden className="opacity-60">ⓘ</span>}
                </div>
                <div className="w-20 h-1.5 rounded-full bg-surface-3 overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${cat.percent}%`, background: cat.percent > 60 ? '#3fb950' : cat.percent > 30 ? '#d29922' : '#f85149' }} />
                </div>
                <div className="text-[10px] font-mono text-text-2">{cat.score}/{cat.max}</div>
              </div>
            );
          })}
        </div>
      )}

      <div className="border-b border-border-1 bg-surface-1 flex overflow-x-auto scrollbar-hide">
        {visibleTabs.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`tab-btn ${tab === id ? 'active' : ''}`}>
            <Icon size={11} />{i18n(`results.tabs.${id}`) === `results.tabs.${id}` ? label : i18n(`results.tabs.${id}`)}
          </button>
        ))}
      </div>

      <div ref={contentRef} className={`flex-1 overflow-y-auto p-5 ${showBackToTop ? 'pb-24' : ''}`}>

        {tab === 'findings' && (
          <div>
            {opsec?.all_findings?.length ? (
              <Card title="Security Findings">
                {opsec.all_findings.map((f, i) => <FindingRow key={i} f={f} />)}
              </Card>
            ) : (
              <div className="card p-6 text-center text-text-3 text-sm">No security findings</div>
            )}
          </div>
        )}

        {tab === 'whois' && r.whois && (
          <Card title="WHOIS Registration" onRefresh={() => refreshModule('whois')} refreshing={isRefreshing('whois')}>
            <div className="space-y-1.5">
              <DtRow label="Registrar" value={r.whois.registrar} />
              <DtRow label="Organization" value={r.whois.org} />
              <DtRow label="Country" value={r.whois.country} />
              <DtRow label="Created" value={r.whois.creation_date?.slice(0, 10)} />
              <DtRow label="Expires" value={r.whois.expiration_date?.slice(0, 10)} />
              {r.whois.emails?.length && (
                <div className="dt-row"><span className="dt-label">Emails</span>
                  <div className="flex flex-wrap gap-1">
                    {r.whois.emails.map(e => (
                      <span key={e} className="inline-flex items-center gap-1">
                        <span className="tag tag-red">{e}</span>
                        <CopyIconButton onClick={() => copyValue(e)} label="Copy email" />
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {r.whois.name_servers?.length && (
                <div className="dt-row"><span className="dt-label">Name Servers</span>
                  <div className="flex flex-wrap gap-1">
                    {r.whois.name_servers.slice(0, 4).map(ns => (
                      <span key={ns} className="inline-flex items-center gap-1">
                        <span className="tag">{ns}</span>
                        <CopyIconButton onClick={() => copyValue(ns)} label="Copy domain" />
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>
        )}

        {tab === 'dns' && r.dns?.records && (
          <Card title="DNS Records" onRefresh={() => refreshModule('dns')} refreshing={isRefreshing('dns')}>
            {Object.entries(r.dns.records).filter(([, v]) => Array.isArray(v) && v.length > 0).map(([type, records]) => (
              <div key={type} className="mb-4">
                <div className="text-[11px] font-bold text-blue mb-1.5 uppercase tracking-wider">{type}</div>
                {(records as unknown[]).map((rec, i) => {
                  const text = typeof rec === 'object' ? JSON.stringify(rec) : String(rec);
                  return (
                    <div key={i} className="flex items-center gap-1.5 py-0.5">
                      <div className="font-mono text-[11px] text-text-2 break-all flex-1">{text}</div>
                      <CopyIconButton onClick={() => copyValue(text)} label="Copy DNS record" />
                    </div>
                  );
                })}
              </div>
            ))}
          </Card>
        )}

        {tab === 'subdomains' && r.cert_transparency && (
          <Card title={`Certificate Transparency — ${r.cert_transparency.subdomains?.length} subdomains`} onRefresh={() => refreshModule('cert_transparency')} refreshing={isRefreshing('cert_transparency')}>
            <div className="text-[11px] text-text-3 mb-3">{r.cert_transparency.total_certs} certificate(s) analysed</div>
            <div className="flex flex-wrap gap-1">
              {r.cert_transparency.subdomains?.map(s => (
                <span key={s} className="inline-flex items-center gap-1">
                  <span className="tag">{s}</span>
                  <CopyIconButton onClick={() => copyValue(s)} label="Copy subdomain" />
                </span>
              ))}
            </div>
          </Card>
        )}

        {tab === 'accounts' && (
          <Card title="Username Search" onRefresh={() => refreshModule('blackbird')} refreshing={isRefreshing('blackbird')}>
            <div className="mb-3">
              <div className="relative">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-3" />
                <input
                  type="text"
                  value={accountFilter}
                  onChange={e => setAccountFilter(e.target.value)}
                  placeholder={i18n('results.filterPlatforms') !== 'results.filterPlatforms' ? i18n('results.filterPlatforms') : 'Filter platforms...'}
                  className="input-field w-full pl-9 text-[12px] h-9"
                />
              </div>
            </div>
            <div className="overflow-x-auto -mx-4 px-4">
            <table className="w-full text-[12px] min-w-[400px]">
              <thead><tr className="text-left text-text-3 text-[10px] uppercase tracking-wider border-b border-border-1">
                <th className="pb-2">Platform</th><th className="pb-2">URL</th><th className="pb-2 text-right">Time</th>
              </tr></thead>
              <tbody>{r.blackbird?.filter(b => b.status === 'found' && (!accountFilter || b.site.toLowerCase().includes(accountFilter.toLowerCase()))).map(b => (
                <tr key={b.site} className="border-b border-border-1 last:border-0">
                  <td className="py-2 font-medium text-text-1">{b.site}</td>
                  <td className="py-2">
                    <div className="flex items-center gap-1.5">
                      <a href={b.url} target="_blank" rel="noreferrer" className="text-blue hover:underline truncate block max-w-xs">{b.url}</a>
                      <CopyIconButton onClick={() => copyValue(b.url)} label="Copy username URL" />
                    </div>
                  </td>
                  <td className="py-2 text-right font-mono text-text-3">{b.response_time?.toFixed(2)}s</td>
                </tr>
              ))}</tbody>
            </table>
            </div>
          </Card>
        )}

        {tab === 'github' && (
          <KeyModuleCard title="GitHub Recon" mod={r.github} onRefresh={() => refreshModule('github')} refreshing={isRefreshing('github')}>
            <div className="space-y-1.5">
              {r.github?.profile?.html_url && (
                <div className="dt-row"><span className="dt-label">Profile</span>
                  <a href={r.github.profile.html_url} target="_blank" rel="noreferrer" className="text-blue hover:underline">{r.github.profile.html_url}</a>
                </div>
              )}
              <DtRow label="Name" value={r.github?.profile?.name} />
              <DtRow label="Type" value={r.github?.profile?.type} />
              <DtRow label="Bio" value={r.github?.profile?.bio} />
              <DtRow label="Company" value={r.github?.profile?.company} />
              <DtRow label="Location" value={r.github?.profile?.location} />
              <DtRow label="Blog" value={r.github?.profile?.blog} />
              <DtRow label="Twitter" value={r.github?.profile?.twitter} />
              <DtRow label="Followers" value={r.github?.profile?.followers} />
              <DtRow label="Public Repos" value={r.github?.profile?.public_repos} />
              <DtRow label="Total Stars" value={r.github?.total_stars} />
              <DtRow label="Joined" value={r.github?.profile?.created_at} />
            </div>
            {(r.github?.top_languages?.length ?? 0) > 0 && (
              <div className="mt-3">
                <div className="text-[10px] text-text-3 uppercase tracking-wider mb-2">Top Languages</div>
                <div className="flex flex-wrap gap-1">
                  {r.github?.top_languages?.map(l => (
                    <span key={l.language} className="tag tag-blue">{l.language} ({l.count})</span>
                  ))}
                </div>
              </div>
            )}
            {(r.github?.emails?.length ?? 0) > 0 && (
              <div className="mt-3">
                <div className="text-[10px] text-text-3 uppercase tracking-wider mb-2">Emails Found</div>
                <div className="flex flex-wrap gap-1">
                  {r.github?.emails?.map(e => (
                    <span key={e} className="inline-flex items-center gap-1">
                      <span className="tag tag-red">{e}</span>
                      <CopyIconButton onClick={() => copyValue(e)} label="Copy email" />
                    </span>
                  ))}
                </div>
              </div>
            )}
          </KeyModuleCard>
        )}

        {tab === 'threats' && (
          <div>
            <KeyModuleCard title="VirusTotal" mod={r.virustotal} onRefresh={() => refreshModule('virustotal')} refreshing={isRefreshing('virustotal')}>
              <div className="grid grid-cols-2 sm:flex sm:gap-6 mb-4 gap-3">
                {[['Malicious', r.virustotal?.malicious, '#f85149'], ['Suspicious', r.virustotal?.suspicious, '#d29922'], ['Harmless', r.virustotal?.harmless, '#3fb950'], ['Undetected', r.virustotal?.undetected, '#484f58']].map(([l, v, c]) => (
                  <div key={String(l)} className="text-center">
                    <div className="text-2xl font-black" style={{ color: String(c) }}>{v}</div>
                    <div className="text-[10px] text-text-3">{l}</div>
                  </div>
                ))}
              </div>
              <div className="space-y-1.5">
                <DtRow label="Country" value={r.virustotal?.country} />
                <DtRow label="ASN" value={r.virustotal?.as_owner} />
              </div>
            </KeyModuleCard>
            <KeyModuleCard title="AbuseIPDB" mod={r.abuseipdb} onRefresh={() => refreshModule('abuseipdb')} refreshing={isRefreshing('abuseipdb')}>
              <div className="space-y-1.5">
                <div className="dt-row"><span className="dt-label">Abuse Score</span>
                  <span className="font-black" style={{ color: (r.abuseipdb?.abuse_score ?? 0) >= 50 ? '#f85149' : (r.abuseipdb?.abuse_score ?? 0) >= 10 ? '#d29922' : '#3fb950' }}>
                    {r.abuseipdb?.abuse_score}/100
                  </span>
                </div>
                <DtRow label="Total Reports" value={r.abuseipdb?.total_reports} />
                <DtRow label="ISP" value={r.abuseipdb?.isp} />
                <DtRow label="Usage Type" value={r.abuseipdb?.usage_type} />
                {r.abuseipdb?.is_tor && <div className="text-red text-[12px] font-semibold mt-1">⚠ TOR Exit Node</div>}
              </div>
            </KeyModuleCard>
            <KeyModuleCard title="Shodan" mod={r.shodan} onRefresh={() => refreshModule('shodan')} refreshing={isRefreshing('shodan')}>
              {r.shodan?.open_ports?.length ? (
                <div className="mb-3">
                  <div className="text-[10px] text-text-3 uppercase tracking-wider mb-2">Open Ports</div>
                  {r.shodan.open_ports.map(p => (
                    <span key={p} className="inline-flex items-center gap-1 mr-1">
                      <span className={`tag ${[21,22,23,3389,5900,445,3306,5432,27017,6379].includes(p) ? 'tag-red' : ''}`}>{p}</span>
                      <CopyIconButton onClick={() => copyValue(p)} label="Copy Shodan port" />
                    </span>
                  ))}
                </div>
              ) : null}
              {r.shodan?.vulns?.length ? (
                <div className="mb-3">
                  <div className="text-[10px] text-text-3 uppercase tracking-wider mb-2 text-red">CVEs Found</div>
                  {r.shodan.vulns.map(v => <span key={v} className="tag tag-red">{v}</span>)}
                </div>
              ) : null}
            </KeyModuleCard>
          </div>
        )}

        {tab === 'censys' && (
          <KeyModuleCard title={`Censys — ${r.censys?.domain ? 'Certificate Search' : 'Host Info'}`} mod={r.censys} onRefresh={() => refreshModule('censys')} refreshing={isRefreshing('censys')}>
            <div className="space-y-1.5">
              {r.censys?.ip && <div className="dt-row"><span className="dt-label">IP</span><span className="dt-value">{r.censys.ip}</span></div>}
              {r.censys?.asn && <div className="dt-row"><span className="dt-label">ASN</span><span className="dt-value">AS{r.censys.asn} {r.censys.as_name ?? ''}</span></div>}
              {r.censys?.country && <div className="dt-row"><span className="dt-label">Location</span><span className="dt-value">{[r.censys.city, r.censys.country].filter(Boolean).join(', ')}</span></div>}
              {r.censys?.open_ports && r.censys.open_ports.length > 0 && (
                <div className="dt-row"><span className="dt-label">Open Ports</span>
                  <div className="flex flex-wrap gap-1">
                    {r.censys.open_ports.map(p => (
                      <span key={p} className="inline-flex items-center gap-1">
                        <span className="tag">{p}</span>
                        <CopyIconButton onClick={() => copyValue(p)} label="Copy port" />
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {r.censys?.subdomains && r.censys.subdomains.length > 0 && (
                <div className="dt-row"><span className="dt-label">Subdomains ({r.censys.subdomains.length})</span>
                  <div className="flex flex-wrap gap-1">
                    {r.censys.subdomains.map(s => (
                      <span key={s} className="inline-flex items-center gap-1">
                        <span className="tag tag-blue">{s}</span>
                        <CopyIconButton onClick={() => copyValue(s)} label="Copy subdomain" />
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {r.censys?.services && r.censys.services.length > 0 && (
                <div className="mt-3">
                  <div className="text-[10px] text-text-3 uppercase tracking-wider mb-2">Services</div>
                  <table className="w-full text-[12px]">
                    <thead><tr className="text-left text-text-3 text-[10px] uppercase tracking-wider border-b border-border-1">
                      <th className="pb-2">Port</th><th className="pb-2">Service</th><th className="pb-2">Software</th>
                    </tr></thead>
                    <tbody>{r.censys.services.map((s, i) => (
                      <tr key={i} className="border-b border-border-1 last:border-0">
                        <td className="py-1.5 font-mono">{s.port}/{s.transport ?? 'tcp'}</td>
                        <td className="py-1.5">{s.service ?? '—'}</td>
                        <td className="py-1.5 text-text-3">{s.software ?? '—'}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              )}
            </div>
          </KeyModuleCard>
        )}

        {tab === 'darkweb' && r.onion && (
          <Card title={`Dark Web Mirrors — ${r.onion.total_found} found`} onRefresh={() => refreshModule('onion')} refreshing={isRefreshing('onion')}>
            <div className="text-[11px] text-text-3 mb-3">
              Sources: Ahmia ({r.onion.sources?.ahmia ?? 0}) · DarkSearch ({r.onion.sources?.darksearch ?? 0})
            </div>
            <div className="space-y-2">
              {r.onion.results?.map((item, i) => (
                <div key={i} className="border border-border-1 rounded p-2.5 bg-surface-2">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] tag tag-red uppercase">{item.source}</span>
                    <span className="font-mono text-[11px] text-text-1 break-all flex-1">{item.url}</span>
                    <CopyIconButton onClick={() => copyValue(item.url)} label="Copy onion URL" />
                  </div>
                  {item.title && <div className="text-[12px] text-text-2 mt-1.5">{item.title}</div>}
                  {item.description && <div className="text-[11px] text-text-3 mt-0.5">{item.description}</div>}
                </div>
              ))}
            </div>
          </Card>
        )}

        {tab === 'wayback' && r.wayback && (
          <Card title="Wayback Machine" onRefresh={() => refreshModule('wayback')} refreshing={isRefreshing('wayback')}>
            {r.wayback.total_snapshots && (
              <div className="text-[12px] text-text-2 mb-4">
                {r.wayback.total_snapshots} snapshots · First: {r.wayback.first_snapshot} · Last: {r.wayback.last_snapshot}
              </div>
            )}
            {r.wayback.snapshots?.length && (
              <div className="mb-4">
                <div className="text-[11px] font-semibold text-blue mb-2">Recent Snapshots</div>
                <div className="space-y-1">
                  {r.wayback.snapshots.slice(0, 10).map(s => (
                    <div key={s.timestamp} className="flex items-center gap-2 text-[10px]">
                      <span className="text-text-3 font-mono">{s.date}</span>
                      <a href={s.wayback_url} target="_blank" rel="noreferrer" className="text-blue hover:underline truncate flex-1">
                        {s.wayback_url}
                      </a>
                      <span className="text-text-3">{s.mime}</span>
                      {s.size > 0 && <span className="text-text-3">{Math.round(s.size/1024)}KB</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {r.wayback.interesting?.length && (
              <div>
                <div className="text-[11px] font-semibold text-red mb-2">Sensitive URLs in Archive</div>
                {r.wayback.interesting.slice(0, 15).map(url => (
                  <div key={url} className="font-mono text-[10px] text-text-2 py-0.5 truncate">
                    <a href={url} target="_blank" rel="noreferrer" className="hover:text-blue">{url}</a>
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {tab === 'email' && (
          <div>
            {r.emailrep && !r.emailrep.error && (
              <Card title="Email Reputation" onRefresh={() => refreshModule('emailrep')} refreshing={isRefreshing('emailrep')}>
                <div className="space-y-1.5">
                  <div className="dt-row"><span className="dt-label">Reputation</span>
                    <span className={`font-bold ${r.emailrep.reputation === 'high' ? 'text-green' : r.emailrep.reputation === 'medium' ? 'text-yellow' : 'text-red'}`}>
                      {(r.emailrep.reputation || 'N/A').toUpperCase()}
                    </span>
                  </div>
                  <div className="dt-row"><span className="dt-label">Suspicious</span>
                    <span className={r.emailrep.suspicious ? 'text-red' : 'text-green'}>{r.emailrep.suspicious ? 'Yes' : 'No'}</span>
                  </div>
                  <div className="dt-row"><span className="dt-label">Valid MX</span>
                    <span className={r.emailrep.valid_mx ? 'text-green' : 'text-red'}>{r.emailrep.valid_mx ? 'Yes' : 'No'}</span>
                  </div>
                  <div className="dt-row"><span className="dt-label">Deliverable</span>
                    <span className={r.emailrep.deliverable ? 'text-green' : r.emailrep.deliverable === false ? 'text-red' : 'text-text-3'}>
                      {r.emailrep.deliverable === true ? 'Yes' : r.emailrep.deliverable === false ? 'No' : 'Unknown'}
                    </span>
                  </div>
                  <div className="dt-row"><span className="dt-label">SPF</span>
                    <span className={r.emailrep.spf ? 'text-green' : 'text-red'}>{r.emailrep.spf ? 'Yes' : 'No'}</span>
                  </div>
                  <div className="dt-row"><span className="dt-label">DMARC</span>
                    <span className={r.emailrep.dmarc ? 'text-green' : 'text-red'}>{r.emailrep.dmarc ? 'Yes' : 'No'}</span>
                  </div>
                  <DtRow label="Domain Reputation" value={r.emailrep.domain_reputation?.toUpperCase()} />
                  {r.emailrep.disposable && <div className="text-red text-[12px] font-semibold mt-1">⚠ Disposable email detected</div>}
                  {r.emailrep.spoofable && <div className="text-yellow text-[12px] font-semibold mt-1">⚠ Domain is spoofable (missing SPF/DMARC)</div>}
                  {r.emailrep.free_provider && <div className="text-text-3 text-[12px] mt-1">Free email provider</div>}
                  {(r.emailrep.mx_records?.length ?? 0) > 0 && (
                    <div className="dt-row"><span className="dt-label">MX Records</span>
                      <div>{r.emailrep.mx_records?.map((mx: string) => <span key={mx} className="tag">{mx}</span>)}</div>
                    </div>
                  )}
                </div>
              </Card>
            )}
            {r.emailrep?.error && (
              <Card title="Email Reputation" onRefresh={() => refreshModule('emailrep')} refreshing={isRefreshing('emailrep')}>
                <div className="text-red text-sm">{r.emailrep.error}</div>
              </Card>
            )}
            {r.smtp && !r.smtp.error && (
              <Card title="SMTP Verification" onRefresh={() => refreshModule('smtp')} refreshing={isRefreshing('smtp')}>
                <div className="space-y-1.5">
                  <div className="dt-row"><span className="dt-label">Exists</span>
                    <span className={r.smtp.exists === true ? 'text-green' : r.smtp.exists === false ? 'text-red' : 'text-text-3'}>
                      {r.smtp.exists === true ? 'Yes' : r.smtp.exists === false ? 'No' : 'Unknown'}
                    </span>
                  </div>
                  <div className="dt-row"><span className="dt-label">SMTP Connect</span>
                    <span className={r.smtp.smtp_connect ? 'text-green' : 'text-red'}>{r.smtp.smtp_connect ? 'Yes' : 'No'}</span>
                  </div>
                  {r.smtp.catch_all && <div className="text-yellow text-[12px] font-semibold mt-1">⚠ Catch-all server (accepts any address)</div>}
                  {(r.smtp.details?.length ?? 0) > 0 && (
                    <div className="mt-2">
                      <div className="text-[10px] text-text-3 uppercase tracking-wider mb-1">Details</div>
                      {r.smtp.details?.map((d: string, i: number) => (
                        <div key={i} className="text-[11px] text-text-2 py-0.5">• {d}</div>
                      ))}
                    </div>
                  )}
                </div>
              </Card>
            )}
            <KeyModuleCard title="Breach Check" mod={r.breaches} onRefresh={() => refreshModule('leaks', ['breaches'])} refreshing={isRefreshing('leaks')}>
              <div className="space-y-1.5">
                {r.breaches?.found !== undefined && (
                  <div className="dt-row"><span className="dt-label">Breaches Found</span>
                    <span className={r.breaches?.found ? 'text-red font-bold' : 'text-green'}>{r.breaches?.found ? 'Yes' : 'No'}</span>
                  </div>
                )}
                {(r.breaches?.breaches?.length ?? 0) > 0 && (
                  <div className="mt-2">
                    <div className="text-[10px] text-text-3 uppercase tracking-wider mb-2">Breached Services</div>
                    <div className="flex flex-wrap gap-1">
                      {r.breaches?.breaches?.map((b: any, i: number) => (
                        <span key={i} className="tag tag-red">{typeof b === 'string' ? b : b.name || b.title || JSON.stringify(b)}</span>
                      ))}
                    </div>
                  </div>
                )}
                {r.breaches?.total !== undefined && <DtRow label="Total Breaches" value={r.breaches.total} />}
              </div>
            </KeyModuleCard>
          </div>
        )}

        {tab === 'dorks' && r.dorks && (
          <Card title="Google Dorks">
            {r.dorks.map((d, i) => (
              <div key={i} className="flex items-center gap-2 py-1.5 border-b border-border-1 last:border-0">
                <code className="font-mono text-[11px] text-text-1 flex-1 truncate">{d}</code>
                <a href={`https://www.google.com/search?q=${encodeURIComponent(d)}`} target="_blank" rel="noreferrer"
                  className="text-blue hover:text-white transition-colors flex-shrink-0">
                  <ExternalLink size={11} />
                </a>
              </div>
            ))}
          </Card>
        )}

        {tab === 'phone' && r.phone && (
          <Card title="Phone Intelligence" onRefresh={() => refreshModule('hlr', ['hlr', 'phone_owner', 'phone'])} refreshing={isRefreshing('hlr')}>
            <div className="space-y-1.5">
              <div className="dt-row"><span className="dt-label">Valid</span>
                <span className={r.phone.valid ? 'text-green' : 'text-red'}>{r.phone.valid ? 'Yes' : 'No'}</span>
              </div>
              <DtRow label="Country" value={r.phone.country_name} />
              <DtRow label="Country Code" value={r.phone.country_code} />
              <DtRow label="Region" value={r.phone.region} />
              <DtRow label="Carrier" value={r.phone.carrier} />
              <DtRow label="Line Type" value={r.phone.line_type} />
              {r.phone.timezones?.length && (
                <div className="dt-row"><span className="dt-label">Timezones</span>
                  <div>{r.phone.timezones.map(tz => <span key={tz} className="tag">{tz}</span>)}</div>
                </div>
              )}
              {r.phone.reverse && (
                <>
                  <DtRow label="Owner Name" value={r.phone.reverse.name} />
                  <DtRow label="Address" value={r.phone.reverse.address} />
                </>
              )}
            </div>
          </Card>
        )}

        {tab === 'telegram' && r.telegram && (
          <Card title="Telegram Profile" onRefresh={() => refreshModule('telegram')} refreshing={isRefreshing('telegram')}>
            {r.telegram.error ? (
              <div className="text-red text-sm">{r.telegram.error}</div>
            ) : (
              <div className="space-y-1.5">
                <div className="dt-row"><span className="dt-label">Found</span>
                  <span className={r.telegram.found ? 'text-green' : 'text-red'}>{r.telegram.found ? 'Yes' : 'No'}</span>
                </div>
                <DtRow label="Username" value={r.telegram.username} />
                <DtRow label="Name" value={r.telegram.name} />
                <DtRow label="Bio" value={r.telegram.bio} />
                <DtRow label="Type" value={r.telegram.type} />
                {r.telegram.followers && <DtRow label="Followers" value={r.telegram.followers} />}
              </div>
            )}
          </Card>
        )}

        {tab === 'map' && (
          <Card title="IP Geolocation Map">
            <MapView scanId={scan.id} onCopy={copyValue} />
          </Card>
        )}

        {tab === 'graph' && (
          <Card title="Entity Graph">
            <GraphView scanId={scan.id} />
          </Card>
        )}

        {tab === 'json' && (
          <Card title="Raw JSON Results">
            <button onClick={() => setShowJson(v => !v)} className="flex items-center gap-1.5 text-[11px] text-text-3 hover:text-text-2 mb-3">
              {showJson ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {showJson ? 'Hide' : 'Show'} raw data
            </button>
            {showJson && (
              <pre className="font-mono text-[10px] text-text-2 overflow-auto max-h-[60vh] bg-surface-1 rounded p-3">
                {JSON.stringify(r, null, 2)}
              </pre>
            )}
          </Card>
        )}

        {tab === 'ai' && (
          <div>
            <Card title="AI OSINT Analysis · Nvidia Nemotron">
              {!aiSummary && !aiLoading && (
                <button onClick={runAi} className="btn-primary w-full">
                  <Brain size={13} /> Generate AI Summary
                </button>
              )}
              {aiLoading && (
                <div className="flex items-center gap-2 text-text-2 text-sm">
                  <span className="inline-block w-2 h-2 rounded-full bg-blue animate-pulse" />
                  Generating analysis…
                </div>
              )}
              {aiError && <div className="text-red text-sm">{aiError}</div>}
              {aiSummary && (
                <div>
                  {aiModel && <div className="text-[10px] text-text-3 mb-3 font-mono">Model: {aiModel}</div>}
                  <div className="mb-2 flex items-center justify-end">
                    <CopyIconButton onClick={() => copyValue(aiSummary)} label="Copy summary" />
                  </div>
                  <div className="text-[13px] text-text-1 leading-relaxed whitespace-pre-wrap">{aiSummary}</div>
                  <button onClick={runAi} className="btn-ghost h-8 px-3 text-[11px] mt-4">Regenerate</button>
                </div>
              )}
            </Card>

            <Card title="Ask the AI">
              {chatHistory.length > 0 && (
                <div className="space-y-3 mb-4 max-h-72 overflow-y-auto pr-1">
                  {chatHistory.map((m, i) => (
                    <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] rounded-lg px-3 py-2 text-[12px] leading-relaxed whitespace-pre-wrap ${
                        m.role === 'user'
                          ? 'bg-blue/20 text-text-1 border border-blue/30'
                          : 'bg-surface-3 text-text-1 border border-border-1'
                      }`}>
                        {m.text}
                      </div>
                    </div>
                  ))}
                  {chatLoading && (
                    <div className="flex gap-2 justify-start">
                      <div className="bg-surface-3 border border-border-1 rounded-lg px-3 py-2">
                        <span className="inline-flex gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-text-3 animate-pulse" />
                          <span className="w-1.5 h-1.5 rounded-full bg-text-3 animate-pulse delay-75" />
                          <span className="w-1.5 h-1.5 rounded-full bg-text-3 animate-pulse delay-150" />
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}
              <div className="flex gap-2">
                <input
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendChat()}
                  placeholder="Ask anything about this scan…"
                  className="input-field flex-1 text-[12px]"
                  disabled={chatLoading}
                />
                <button
                  onClick={sendChat}
                  disabled={!chatInput.trim() || chatLoading}
                  className="btn-primary px-3 h-9 shrink-0"
                >
                  <SendHorizontal size={13} />
                </button>
              </div>
            </Card>
          </div>
        )}
      </div>
      {showBackToTop && (
        <div className="fixed bottom-8 right-8 z-50 group">
          <button
            type="button"
            onClick={() => {
              const el = contentRef.current;
              if (el) el.scrollTo({ top: 0, behavior: 'smooth' });
              else window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            aria-label="Back to top"
            title="Back to top"
            className="flex items-center justify-center w-12 h-12 rounded-full bg-blue hover:bg-blue/90 text-white shadow-lg hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-blue/50 focus:ring-offset-2 focus:ring-offset-surface-1 transition-all duration-200 hover:scale-110 active:scale-95"
          >
            <ArrowUp size={20} strokeWidth={2.5} />
            <span className="sr-only">Back to top</span>
          </button>
          <div className="absolute -top-12 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none whitespace-nowrap">
            <div className="px-3 py-1.5 rounded-md bg-surface-1 border border-border-1 text-[11px] font-semibold text-text-1 shadow-lg">Back to top</div>
          </div>
        </div>
      )}

      {copyToast && (
        <div className={`fixed ${showBackToTop ? 'bottom-20' : 'bottom-4'} right-4 z-[70] px-3 py-1.5 rounded border border-border-1 bg-surface-2 text-[11px] font-semibold text-text-1 shadow-xl`}>
          {copyToast}
        </div>
      )}
    </div>
  );
}

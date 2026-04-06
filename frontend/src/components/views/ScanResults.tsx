'use client';
import { useState, useEffect, useRef } from 'react';
import { ExternalLink, Printer, Shield, AlertTriangle, Globe, Server, Lock, User, Clock, Zap, Phone, MessageCircle, Map, GitBranch, Code, Brain, ChevronDown, ChevronUp, SendHorizontal, Mail } from 'lucide-react';
import type { ScanResults, ScanMeta, OpsecFinding } from '@/lib/types';
import { getReportUrl, generateAiSummary, sendAiChat, getMapData, getGraphData } from '@/lib/api';

function MapView({ scanId }: { scanId: string }) {
  const [data, setData] = useState<{ markers: { lat: number; lng: number; label: string; city?: string; country?: string; org?: string; ip?: string }[]; center: { lat: number; lng: number } | null } | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getMapData(scanId)
      .then((d: any) => { if (d.error) setError(d.error); else setData(d); })
      .catch(e => setError(e.message));
  }, [scanId]);

  if (error) return <div className="text-red text-sm">{error}</div>;
  if (!data) return <div className="text-text-3 text-sm animate-pulse">Loading map…</div>;
  if (!data.markers?.length) return <div className="text-text-3 text-sm">No geolocation data available</div>;

  const m = data.markers[0];
  const pad = 0.15;
  const bbox = `${m.lng - pad},${m.lat - pad},${m.lng + pad},${m.lat + pad}`;
  const iframeSrc = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${m.lat},${m.lng}`;

  return (
    <div>
      <iframe src={iframeSrc} className="w-full rounded-md border border-border-1" style={{ height: 360, border: 0 }}
        title="IP Geolocation Map" loading="lazy" />
      <div className="mt-3 grid grid-cols-2 gap-x-8 gap-y-1 text-[12px]">
        {m.ip && <div className="dt-row"><span className="dt-label">IP</span><span className="dt-value font-mono">{m.ip}</span></div>}
        {(m.city || m.country) && <div className="dt-row"><span className="dt-label">Location</span><span className="dt-value">{[m.city, m.country].filter(Boolean).join(', ')}</span></div>}
        {m.org && <div className="dt-row"><span className="dt-label">Organization</span><span className="dt-value">{m.org}</span></div>}
        <div className="dt-row"><span className="dt-label">Coordinates</span><span className="dt-value font-mono">{m.lat.toFixed(4)}, {m.lng.toFixed(4)}</span></div>
      </div>
      {data.markers.length > 1 && (
        <div className="mt-3 text-[10px] text-text-3">{data.markers.length} locations found</div>
      )}
    </div>
  );
}

function GraphView({ scanId }: { scanId: string }) {
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
      {status === 'empty' && <div className="text-text-3 text-sm py-4">No graph data available for this scan</div>}
      {status === 'error' && <div className="text-red text-sm py-4">{error}</div>}
      <div ref={containerRef} style={{ height: status === 'ready' ? 480 : 0, background: 'transparent' }} />
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

function Card({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <div className="card mb-3">
      {title && <div className="card-head">{title}</div>}
      <div className="p-4">{children}</div>
    </div>
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

const TABS = [
  { id: 'findings', label: 'Findings', icon: Shield },
  { id: 'whois', label: 'WHOIS', icon: Globe },
  { id: 'dns', label: 'DNS', icon: Server },
  { id: 'subdomains', label: 'Subdomains', icon: Lock },
  { id: 'accounts', label: 'Accounts', icon: User },
  { id: 'threats', label: 'Threats', icon: AlertTriangle },
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
  const [tab, setTab] = useState('findings');
  const [aiSummary, setAiSummary] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState('');
  const [aiModel, setAiModel] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState<{role:'user'|'ai'; text:string}[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [showJson, setShowJson] = useState(false);
  const r = scan.results;
  const opsec = r.opsec;

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

  const visibleTabs = TABS.filter(t => {
    if (t.id === 'whois') return r.whois && !r.whois.error;
    if (t.id === 'dns') return r.dns?.records && Object.keys(r.dns.records).length > 0;
    if (t.id === 'subdomains') return r.cert_transparency?.subdomains?.length;
    if (t.id === 'accounts') return r.blackbird?.some(b => b.status === 'found');
    if (t.id === 'threats') return r.virustotal || r.abuseipdb || r.shodan;
    if (t.id === 'wayback') return r.wayback;
    if (t.id === 'email') return r.emailrep || r.smtp || r.breaches;
    if (t.id === 'dorks') return r.dorks?.length;
    if (t.id === 'phone') return r.phone;
    if (t.id === 'telegram') return r.telegram;
    return true;
  });

  return (
    <div className="flex flex-col h-[calc(100vh-48px)] animate-fade-in">
      <div className="px-5 py-3 border-b border-border-1 bg-surface-1 flex items-center justify-between gap-4">
        <div>
          <div className="font-bold text-text-1 text-[15px]">{scan.target}</div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="badge badge-info">{scan.scan_type?.toUpperCase()}</span>
            {scan.started_at && (
              <span className="text-[10px] text-text-3">{scan.started_at.slice(0, 19).replace('T', ' ')}</span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <a href={getReportUrl(scan.id)} target="_blank" rel="noreferrer"
            className="btn-ghost text-[11px] h-8 px-3">
            <ExternalLink size={11} /> HTML Report
          </a>
          <button onClick={() => window.print()} className="btn-ghost text-[11px] h-8 px-3">
            <Printer size={11} /> Print PDF
          </button>
        </div>
      </div>

      {opsec && (
        <div className="px-5 py-2.5 bg-surface-2 border-b border-border-1 flex items-center gap-6 flex-wrap">
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
          {Object.entries(opsec.categories).map(([k, cat]) => (
            <div key={k} className="flex items-center gap-2">
              <div className="text-[10px] text-text-3 capitalize">{k.replace('_', ' ')}</div>
              <div className="w-20 h-1.5 rounded-full bg-surface-3 overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${cat.percent}%`, background: cat.percent > 60 ? '#3fb950' : cat.percent > 30 ? '#d29922' : '#f85149' }} />
              </div>
              <div className="text-[10px] font-mono text-text-2">{cat.score}/{cat.max}</div>
            </div>
          ))}
        </div>
      )}

      <div className="border-b border-border-1 bg-surface-1 flex overflow-x-auto scrollbar-hide">
        {visibleTabs.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`tab-btn ${tab === id ? 'active' : ''}`}>
            <Icon size={11} />{label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-5">

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
          <Card title="WHOIS Registration">
            <div className="space-y-1.5">
              <DtRow label="Registrar" value={r.whois.registrar} />
              <DtRow label="Organization" value={r.whois.org} />
              <DtRow label="Country" value={r.whois.country} />
              <DtRow label="Created" value={r.whois.creation_date?.slice(0, 10)} />
              <DtRow label="Expires" value={r.whois.expiration_date?.slice(0, 10)} />
              {r.whois.emails?.length && (
                <div className="dt-row"><span className="dt-label">Emails</span>
                  <div>{r.whois.emails.map(e => <span key={e} className="tag tag-red">{e}</span>)}</div>
                </div>
              )}
              {r.whois.name_servers?.length && (
                <div className="dt-row"><span className="dt-label">Name Servers</span>
                  <div>{r.whois.name_servers.slice(0, 4).map(ns => <span key={ns} className="tag">{ns}</span>)}</div>
                </div>
              )}
            </div>
          </Card>
        )}

        {tab === 'dns' && r.dns?.records && (
          <Card title="DNS Records">
            {Object.entries(r.dns.records).filter(([, v]) => Array.isArray(v) && v.length > 0).map(([type, records]) => (
              <div key={type} className="mb-4">
                <div className="text-[11px] font-bold text-blue mb-1.5 uppercase tracking-wider">{type}</div>
                {(records as unknown[]).map((rec, i) => (
                  <div key={i} className="font-mono text-[11px] text-text-2 py-0.5">
                    {typeof rec === 'object' ? JSON.stringify(rec) : String(rec)}
                  </div>
                ))}
              </div>
            ))}
          </Card>
        )}

        {tab === 'subdomains' && r.cert_transparency && (
          <Card title={`Certificate Transparency — ${r.cert_transparency.subdomains?.length} subdomains`}>
            <div className="text-[11px] text-text-3 mb-3">{r.cert_transparency.total_certs} certificate(s) analysed</div>
            <div className="flex flex-wrap gap-1">
              {r.cert_transparency.subdomains?.map(s => <span key={s} className="tag">{s}</span>)}
            </div>
          </Card>
        )}

        {tab === 'accounts' && (
          <Card title="Username Search">
            <table className="w-full text-[12px]">
              <thead><tr className="text-left text-text-3 text-[10px] uppercase tracking-wider border-b border-border-1">
                <th className="pb-2">Platform</th><th className="pb-2">URL</th><th className="pb-2 text-right">Time</th>
              </tr></thead>
              <tbody>{r.blackbird?.filter(b => b.status === 'found').map(b => (
                <tr key={b.site} className="border-b border-border-1 last:border-0">
                  <td className="py-2 font-medium text-text-1">{b.site}</td>
                  <td className="py-2"><a href={b.url} target="_blank" rel="noreferrer" className="text-blue hover:underline truncate block max-w-xs">{b.url}</a></td>
                  <td className="py-2 text-right font-mono text-text-3">{b.response_time?.toFixed(2)}s</td>
                </tr>
              ))}</tbody>
            </table>
          </Card>
        )}

        {tab === 'threats' && (
          <div>
            {r.virustotal && !r.virustotal.error && (
              <Card title="VirusTotal">
                <div className="flex gap-6 mb-4">
                  {[['Malicious', r.virustotal.malicious, '#f85149'], ['Suspicious', r.virustotal.suspicious, '#d29922'], ['Harmless', r.virustotal.harmless, '#3fb950'], ['Undetected', r.virustotal.undetected, '#484f58']].map(([l, v, c]) => (
                    <div key={String(l)} className="text-center">
                      <div className="text-2xl font-black" style={{ color: String(c) }}>{v}</div>
                      <div className="text-[10px] text-text-3">{l}</div>
                    </div>
                  ))}
                </div>
                <div className="space-y-1.5">
                  <DtRow label="Country" value={r.virustotal.country} />
                  <DtRow label="ASN" value={r.virustotal.as_owner} />
                </div>
              </Card>
            )}
            {r.abuseipdb && !r.abuseipdb.error && (
              <Card title="AbuseIPDB">
                <div className="space-y-1.5">
                  <div className="dt-row"><span className="dt-label">Abuse Score</span>
                    <span className="font-black" style={{ color: (r.abuseipdb.abuse_score ?? 0) >= 50 ? '#f85149' : (r.abuseipdb.abuse_score ?? 0) >= 10 ? '#d29922' : '#3fb950' }}>
                      {r.abuseipdb.abuse_score}/100
                    </span>
                  </div>
                  <DtRow label="Total Reports" value={r.abuseipdb.total_reports} />
                  <DtRow label="ISP" value={r.abuseipdb.isp} />
                  <DtRow label="Usage Type" value={r.abuseipdb.usage_type} />
                  {r.abuseipdb.is_tor && <div className="text-red text-[12px] font-semibold mt-1">⚠ TOR Exit Node</div>}
                </div>
              </Card>
            )}
            {r.shodan && !r.shodan.error && (
              <Card title="Shodan">
                {r.shodan.open_ports?.length && (
                  <div className="mb-3">
                    <div className="text-[10px] text-text-3 uppercase tracking-wider mb-2">Open Ports</div>
                    {r.shodan.open_ports.map(p => (
                      <span key={p} className={`tag ${[21,22,23,3389,5900,445,3306,5432,27017,6379].includes(p) ? 'tag-red' : ''}`}>{p}</span>
                    ))}
                  </div>
                )}
                {r.shodan.vulns?.length && (
                  <div className="mb-3">
                    <div className="text-[10px] text-text-3 uppercase tracking-wider mb-2 text-red">CVEs Found</div>
                    {r.shodan.vulns.map(v => <span key={v} className="tag tag-red">{v}</span>)}
                  </div>
                )}
              </Card>
            )}
          </div>
        )}

        {tab === 'wayback' && r.wayback && (
          <Card title="Wayback Machine">
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
              <Card title="Email Reputation">
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
              <Card title="Email Reputation">
                <div className="text-red text-sm">{r.emailrep.error}</div>
              </Card>
            )}
            {r.smtp && !r.smtp.error && (
              <Card title="SMTP Verification">
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
            {r.breaches && !r.breaches.error && (
              <Card title="Breach Check">
                <div className="space-y-1.5">
                  {r.breaches.found !== undefined && (
                    <div className="dt-row"><span className="dt-label">Breaches Found</span>
                      <span className={r.breaches.found ? 'text-red font-bold' : 'text-green'}>{r.breaches.found ? 'Yes' : 'No'}</span>
                    </div>
                  )}
                  {(r.breaches.breaches?.length ?? 0) > 0 && (
                    <div className="mt-2">
                      <div className="text-[10px] text-text-3 uppercase tracking-wider mb-2">Breached Services</div>
                      <div className="flex flex-wrap gap-1">
                        {r.breaches.breaches?.map((b: any, i: number) => (
                          <span key={i} className="tag tag-red">{typeof b === 'string' ? b : b.name || b.title || JSON.stringify(b)}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {r.breaches.total !== undefined && <DtRow label="Total Breaches" value={r.breaches.total} />}
                </div>
              </Card>
            )}
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
          <Card title="Phone Intelligence">
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
          <Card title="Telegram Profile">
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
            <MapView scanId={scan.id} />
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
    </div>
  );
}

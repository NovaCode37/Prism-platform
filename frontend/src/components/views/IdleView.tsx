'use client';
import { useEffect, useState } from 'react';
import { FileText, Mail, Bitcoin, QrCode, ChevronRight, Globe, User, Phone, Shield, Database, Zap, Eye, Activity } from 'lucide-react';
import { Logo } from '../Logo';
import type { ToolMode } from '@/lib/types';

const TOOLS = [
  { id: 'metadata', label: 'File Metadata', desc: 'EXIF, GPS, PDF, DOCX', icon: FileText },
  { id: 'headers', label: 'Email Headers', desc: 'SPF, DKIM, routing hops', icon: Mail },
  { id: 'crypto', label: 'Crypto Address', desc: 'Bitcoin & Ethereum', icon: Bitcoin },
  { id: 'qr', label: 'QR Decode', desc: 'Decode & analyze', icon: QrCode },
] as const;

const CAPS = [
  { title: 'Domain / IP',      icon: Globe,  items: ['WHOIS · DNS · GeoIP', 'Subdomains · Shodan', 'VirusTotal · Wayback'] },
  { title: 'Email',            icon: User,   items: ['DNS reputation · SMTP', 'Breach check · Disposable', 'SPF · DKIM · DMARC'] },
  { title: 'Phone',            icon: Phone,  items: ['Validation · Carrier', 'Country · Reverse lookup'] },
  { title: 'Username',         icon: Shield, items: ['Blackbird · Maigret', '50+ / 3000+ platforms', 'OPSEC Score'] },
];

const TARGETS = ['domain.com', '192.168.1.1', 'user@example.com', '@username', '+1 555 000 0000'];

const STATS = [
  { label: 'Modules',  value: 15, icon: Database },
  { label: 'Sources',  value: 10, icon: Zap },
  { label: 'Scan types', value: 5, icon: Eye },
  { label: 'Status',   value: 0,  icon: Activity, text: 'ONLINE' },
];

interface Props { onTool: (mode: ToolMode) => void; }

export function IdleView({ onTool }: Props) {
  const [targetIdx, setTargetIdx]   = useState(0);
  const [displayed, setDisplayed]   = useState('');
  const [deleting, setDeleting]     = useState(false);
  const [counters, setCounters]     = useState(STATS.map(() => 0));

  useEffect(() => {
    const target = TARGETS[targetIdx];
    let t: ReturnType<typeof setTimeout>;
    if (!deleting && displayed.length < target.length) {
      t = setTimeout(() => setDisplayed(target.slice(0, displayed.length + 1)), 75);
    } else if (!deleting && displayed.length === target.length) {
      t = setTimeout(() => setDeleting(true), 1600);
    } else if (deleting && displayed.length > 0) {
      t = setTimeout(() => setDisplayed(displayed.slice(0, -1)), 35);
    } else {
      setDeleting(false);
      setTargetIdx(i => (i + 1) % TARGETS.length);
    }
    return () => clearTimeout(t);
  }, [displayed, deleting, targetIdx]);

  useEffect(() => {
    const timers = STATS.map((s, i) =>
      s.text ? null : setTimeout(() => {
        let cur = 0;
        const iv = setInterval(() => {
          cur = Math.min(cur + 1, s.value);
          setCounters(prev => { const n = [...prev]; n[i] = cur; return n; });
          if (cur >= s.value) clearInterval(iv);
        }, 100);
      }, i * 180)
    );
    return () => timers.forEach(t => t && clearTimeout(t));
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-48px)] px-6 py-10">

      <div className="relative mb-5">
        <div className="absolute inset-0 rounded-full blur-2xl opacity-25" style={{ background: 'radial-gradient(circle, #4f8ef7 0%, #7c5cfc 100%)', transform: 'scale(2)' }} />
        <Logo size={54} animated />
      </div>

      <h1 className="text-xl font-bold tracking-widest text-text-1 mb-1">PRISM</h1>
      <div className="text-[10px] text-text-3 uppercase tracking-widest mb-5 opacity-50">Open Source Intelligence Platform</div>

      <div className="flex items-center gap-2 mb-7 font-mono text-[12px] px-4 py-2 rounded border border-border-1 bg-surface-2">
        <span className="text-text-3">target://</span>
        <span className="text-blue min-w-[140px]">{displayed}</span>
        <span className="text-blue opacity-80" style={{ animation: 'cursor-blink 0.8s step-end infinite' }}>▌</span>
      </div>

      <div className="flex gap-3 mb-8">
        {STATS.map((s, i) => (
          <div key={s.label} className="flex flex-col items-center px-4 py-2.5 rounded border border-border-1 bg-surface-2 min-w-[70px]">
            <s.icon size={11} className="text-blue mb-1.5 opacity-60" />
            {s.text ? (
              <div className="relative flex items-center justify-center">
                <span className="absolute -left-3 w-1.5 h-1.5 rounded-full bg-green-500" style={{ animation: 'cursor-blink 1.5s ease-in-out infinite' }} />
                <span className="text-[10px] font-bold text-green-400 font-mono">{s.text}</span>
              </div>
            ) : (
              <div className="text-[15px] font-bold text-text-1 font-mono leading-none">{counters[i]}</div>
            )}
            <div className="text-[9px] text-text-3 uppercase tracking-wider mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full max-w-2xl mb-8">
        {CAPS.map(c => (
          <div key={c.title} className="card p-3 hover:border-border-3 transition-colors">
            <div className="flex items-center gap-1.5 mb-2">
              <c.icon size={10} className="text-blue shrink-0 opacity-80" />
              <div className="text-[10px] font-bold text-blue uppercase tracking-wider">{c.title}</div>
            </div>
            {c.items.map(item => (
              <div key={item} className="text-[11px] text-text-3 leading-relaxed">{item}</div>
            ))}
          </div>
        ))}
      </div>

      <div className="w-full max-w-2xl">
        <div className="text-[10px] font-semibold text-text-3 uppercase tracking-wider mb-2">Standalone Tools</div>
        <div className="grid grid-cols-2 gap-1.5">
          {TOOLS.map(({ id, label, desc, icon: Icon }) => (
            <button
              key={id}
              onClick={() => onTool(id as ToolMode)}
              className="card px-3 py-2 text-left hover:border-border-3 hover:bg-surface-3 transition-all group flex items-center gap-2.5 cursor-pointer"
            >
              <Icon size={13} className="text-blue shrink-0" />
              <div className="min-w-0">
                <div className="text-[11px] font-semibold text-text-1 leading-tight">{label}</div>
                <div className="text-[9px] text-text-3 truncate">{desc}</div>
              </div>
              <ChevronRight size={10} className="text-text-3 group-hover:text-text-2 transition-colors ml-auto shrink-0" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

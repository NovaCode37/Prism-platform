'use client';
import { useState, useEffect } from 'react';
import { Play, Loader2, ChevronDown, ChevronUp, Lightbulb, RotateCcw, Trash2 } from 'lucide-react';
import { useTranslations } from '@/lib/i18n';
import type { ScanType } from '@/lib/types';

const TYPE_COLOR: Record<ScanType, string> = {
  domain:   'bg-blue/15 text-blue',
  ip:       'bg-purple/15 text-purple',
  email:    'bg-yellow/15 text-yellow',
  phone:    'bg-green/15 text-green',
  username: 'bg-red/15 text-red',
};

interface RecentScan { target: string; type: ScanType; ts: number; }

const TIPS = [
  'Scan domains, IPs, emails, phones & usernames',
  'Toggle modules to customize each scan',
  'Download HTML reports from scan results',
  'Graph tab shows entity relationships',
  'Map tab shows GeoIP location data',
  'Use Dorks module to find exposed files',
  'OPSEC score rates target exposure risk',
];

function useTip() {
  const [idx, setIdx] = useState(0);
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const iv = setInterval(() => {
      setVisible(false);
      setTimeout(() => { setIdx(i => (i + 1) % TIPS.length); setVisible(true); }, 350);
    }, 4000);
    return () => clearInterval(iv);
  }, []);
  return { tip: TIPS[idx], visible };
}

function useRecentScans() {
  const KEY = 'prism_recent_scans';
  const [recents, setRecents] = useState<RecentScan[]>([]);

  useEffect(() => {
    try { setRecents(JSON.parse(localStorage.getItem(KEY) || '[]')); } catch {}
  }, []);

  const add = (target: string, type: ScanType) => {
    setRecents(prev => {
      const next = [{ target, type, ts: Date.now() }, ...prev.filter(r => r.target !== target)].slice(0, 6);
      localStorage.setItem(KEY, JSON.stringify(next));
      return next;
    });
  };

  const clear = () => { localStorage.removeItem(KEY); setRecents([]); };

  return { recents, add, clear };
}

const MODULE_MAP: Record<ScanType, { id: string; label: string }[]> = {
  domain: [
    { id: 'whois', label: 'WHOIS' }, { id: 'dns', label: 'DNS' },
    { id: 'geoip', label: 'GeoIP' }, { id: 'cert_transparency', label: 'Cert CT' },
    { id: 'website', label: 'Website' }, { id: 'wayback', label: 'Wayback' },
    { id: 'shodan', label: 'Shodan' }, { id: 'virustotal', label: 'VirusTotal' },
    { id: 'censys', label: 'Censys' }, { id: 'onion', label: 'Dark Web' },
  ],
  ip: [
    { id: 'geoip', label: 'GeoIP' }, { id: 'shodan', label: 'Shodan' },
    { id: 'virustotal', label: 'VirusTotal' }, { id: 'abuseipdb', label: 'AbuseIPDB' },
    { id: 'censys', label: 'Censys' },
  ],
  email: [
    { id: 'emailrep', label: 'Email Rep' }, { id: 'smtp', label: 'SMTP Verify' },
    { id: 'leaks', label: 'Breach Check' },
  ],
  phone: [
    { id: 'hlr', label: 'Phone Lookup' },
  ],
  username: [
    { id: 'blackbird', label: 'Blackbird' }, { id: 'maigret', label: 'Maigret' },
  ],
};

interface Props {
  onScan: (target: string, type: ScanType, modules: string[]) => void;
  isRunning: boolean;
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ onScan, isRunning, isOpen, onClose }: Props) {
  const { t } = useTranslations();
  const [target, setTarget] = useState('');
  const [scanType, setScanType] = useState<ScanType>('domain');
  const [modules, setModules] = useState<string[]>(MODULE_MAP.domain.map(m => m.id));
  const [showModules, setShowModules] = useState(false);
  const { tip, visible } = useTip();
  const { recents, add: addRecent, clear: clearRecents } = useRecentScans();

  const handleTypeChange = (t: ScanType) => {
    setScanType(t);
    setModules(MODULE_MAP[t].map(m => m.id));
  };

  const toggleModule = (id: string) => {
    setModules(prev => prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (target.trim() && !isRunning) {
      addRecent(target.trim(), scanType);
      onScan(target.trim(), scanType, modules);
    }
  };

  const loadRecent = (r: RecentScan) => {
    setTarget(r.target);
    handleTypeChange(r.type);
  };

  return (
    <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-surface-1 border-r border-border-1 flex flex-col h-screen transform transition-transform duration-200 ease-in-out md:relative md:z-auto md:transform-none ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
      <button onClick={onClose} className="absolute top-3 right-3 md:hidden text-text-3 hover:text-text-1 p-1">✕</button>
      <form onSubmit={handleSubmit} className="p-4 flex flex-col gap-3">
        <div>
          <label className="text-[10px] font-semibold text-text-3 uppercase tracking-wider block mb-1.5">{t('sidebar.target')}</label>
          <input
            value={target}
            onChange={e => setTarget(e.target.value)}
            placeholder={t('sidebar.targetPlaceholder')}
            className="input-field"
            disabled={isRunning}
          />
        </div>

        <div>
          <label className="text-[10px] font-semibold text-text-3 uppercase tracking-wider block mb-1.5">{t('sidebar.scanType')}</label>
          <div className="grid grid-cols-3 gap-1">
            {(['domain','ip','email','phone','username'] as ScanType[]).map(t => (
              <button
                key={t}
                type="button"
                onClick={() => handleTypeChange(t)}
                className={`text-[10px] font-semibold py-1.5 rounded transition-all ${
                  scanType === t ? 'text-white' : 'bg-surface-3 text-text-3 hover:text-text-2'
                }`}
                style={scanType === t ? { background: 'linear-gradient(135deg,#4f8ef7,#7c5cfc)' } : {}}
              >
                {t.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowModules(v => !v)}
          className="flex items-center justify-between text-[10px] font-semibold text-text-3 uppercase tracking-wider hover:text-text-2 transition-colors"
        >
          {t('sidebar.modules')} ({modules.length}/{MODULE_MAP[scanType].length})
          {showModules ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        {showModules && (
          <div className="flex flex-wrap gap-1.5 animate-fade-in">
            {MODULE_MAP[scanType].map(m => (
              <button
                key={m.id}
                type="button"
                onClick={() => toggleModule(m.id)}
                className={`text-[10px] px-2 py-1 rounded transition-all font-medium ${
                  modules.includes(m.id)
                    ? 'bg-blue/20 text-blue border border-blue/30'
                    : 'bg-surface-3 text-text-3 border border-border-1 hover:text-text-2'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        )}

        <button
          type="submit"
          disabled={!target.trim() || isRunning || modules.length === 0}
          className="btn-primary mt-1"
        >
          {isRunning ? <Loader2 size={13} className="spin" /> : <Play size={13} />}
          {isRunning ? t('sidebar.scanning') : t('sidebar.runScan')}
        </button>
      </form>

      <div className="px-4 pb-3 flex-1">
        <div className="border-t border-border-1 pt-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5 text-[10px] font-semibold text-text-3 uppercase tracking-wider">
              <RotateCcw size={9} />
              {t('sidebar.recent')}
            </div>
            {recents.length > 0 && (
              <button onClick={clearRecents} className="text-text-3 hover:text-red transition-colors">
                <Trash2 size={10} />
              </button>
            )}
          </div>

          {recents.length === 0 ? (
            <div className="text-[10px] text-text-3 opacity-40 italic">{t('sidebar.noRecent')}</div>
          ) : (
            <div className="flex flex-col gap-1">
              {recents.map((r, i) => (
                <button
                  key={i}
                  onClick={() => loadRecent(r)}
                  className="flex items-center gap-2 w-full text-left px-2 py-1.5 rounded hover:bg-surface-3 transition-colors group"
                >
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase shrink-0 ${TYPE_COLOR[r.type]}`}>
                    {r.type.slice(0, 2)}
                  </span>
                  <span className="text-[11px] text-text-2 truncate font-mono group-hover:text-text-1 transition-colors">
                    {r.target}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border-1 px-3 py-2.5">
        <div className="flex items-start gap-1.5">
          <Lightbulb size={9} className="text-yellow opacity-60 mt-0.5 shrink-0" />
          <span
            className="text-[9px] text-text-3 leading-relaxed"
            style={{ opacity: visible ? 0.6 : 0, transition: 'opacity 0.3s ease' }}
          >
            {tip}
          </span>
        </div>
      </div>
    </aside>
  );
}

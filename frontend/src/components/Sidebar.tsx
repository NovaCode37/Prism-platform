'use client';
import { useState, useEffect, useRef } from 'react';
import { Play, Loader2, ChevronDown, ChevronUp, Lightbulb, RotateCcw, Trash2, History, GitCompare } from 'lucide-react';
import { useTranslations } from '@/lib/i18n';
import { listScans, clearScans, type ScanListItem } from '@/lib/api';
import type { ScanType } from '@/lib/types';

const TYPE_COLOR: Record<ScanType, string> = {
  domain:   'bg-blue/15 text-blue',
  ip:       'bg-purple/15 text-purple',
  email:    'bg-yellow/15 text-yellow',
  phone:    'bg-green/15 text-green',
  username: 'bg-red/15 text-red',
};

interface RecentScan { target: string; type: ScanType; ts: number; }

const SCAN_TYPES: ScanType[] = ['domain', 'ip', 'email', 'phone', 'username'];

const MODULE_MAP: Record<ScanType, string[]> = {
  domain:   ['whois', 'dns', 'geoip', 'cert_transparency', 'website', 'wayback', 'shodan', 'virustotal', 'censys', 'onion'],
  ip:       ['geoip', 'shodan', 'virustotal', 'abuseipdb', 'censys'],
  email:    ['emailrep', 'smtp', 'leaks'],
  phone:    ['hlr'],
  username: ['blackbird', 'maigret', 'github'],
};

interface Props {
  onScan: (target: string, type: ScanType, modules: string[]) => void;
  onLoadScan?: (scanId: string) => void;
  onCompare?: (a: string, b: string) => void;
  isRunning: boolean;
  isOpen: boolean;
  onClose: () => void;
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

export function Sidebar({ onScan, onLoadScan, onCompare, isRunning, isOpen, onClose }: Props) {
  const { t } = useTranslations();
  const [target, setTarget] = useState('');
  const [scanType, setScanType] = useState<ScanType>('domain');
  const [modules, setModules] = useState<string[]>(MODULE_MAP.domain);
  const [showModules, setShowModules] = useState(false);
  const [tipIdx, setTipIdx] = useState(0);
  const [tipVisible, setTipVisible] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<ScanListItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [compareSelection, setCompareSelection] = useState<string[]>([]);
  const { recents, add: addRecent, clear: clearRecents } = useRecentScans();

  useEffect(() => {
    const iv = setInterval(() => {
      setTipVisible(false);
      setTimeout(() => { setTipIdx(i => (i + 1) % SCAN_TYPES.length); setTipVisible(true); }, 350);
    }, 4000);
    return () => clearInterval(iv);
  }, []);

  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const items = await listScans();
      setHistory(items);
    } catch {
      setHistory([]);
    }
    setHistoryLoading(false);
  };

  const handleClearHistory = async () => {
  const confirmed = window.confirm(
    'Are you sure you want to clear your scan history?'
  );

  if (!confirmed) return;

  try {
    await clearScans();
    await fetchHistory();
  } catch (err) {
    console.error(err);
    alert('Failed to clear scan history');
  }
};

  const toggleHistory = () => {
    const next = !showHistory;
    setShowHistory(next);
    if (next) fetchHistory();
  };

  const prevRunning = useRef(isRunning);
  useEffect(() => {
    if (prevRunning.current && !isRunning && showHistory) fetchHistory();
    prevRunning.current = isRunning;
  }, [isRunning, showHistory]);

  const toggleCompareSelect = (id: string) => {
    setCompareSelection(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 2 ? [...prev, id] : [prev[1], id]
    );
  };

  const handleTypeChange = (type: ScanType) => {
    setScanType(type);
    setModules(MODULE_MAP[type]);
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

  const tip = t(`sidebar.tips.${tipIdx}`) || t('sidebar.tips.0');

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
            {SCAN_TYPES.map(type => (
              <button
                key={type}
                type="button"
                onClick={() => handleTypeChange(type)}
                className={`text-[10px] font-semibold py-1.5 rounded transition-all ${
                  scanType === type ? 'text-white' : 'bg-surface-3 text-text-3 hover:text-text-2'
                }`}
                style={scanType === type ? { background: 'linear-gradient(135deg,#4f8ef7,#7c5cfc)' } : {}}
              >
                {t(`sidebar.scanTypes.${type}`)}
              </button>
            ))}
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowModules(v => !v)}
          className="flex items-center justify-between text-[10px] font-semibold text-text-3 uppercase tracking-wider hover:text-text-2 transition-colors"
        >
          {t('sidebar.modulesTitle')} ({modules.length}/{MODULE_MAP[scanType].length})
          {showModules ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        {showModules && (
          <div className="flex flex-wrap gap-1.5 animate-fade-in">
            {MODULE_MAP[scanType].map(moduleId => (
              <button
                key={moduleId}
                type="button"
                onClick={() => toggleModule(moduleId)}
                className={`text-[10px] px-2 py-1 rounded transition-all font-medium ${
                  modules.includes(moduleId)
                    ? 'bg-blue/20 text-blue border border-blue/30'
                    : 'bg-surface-3 text-text-3 border border-border-1 hover:text-text-2'
                }`}
              >
                {t(`sidebar.modules.${moduleId}`)}
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
            <div className="text-[10px] text-text-3 italic text-center py-1">{t('sidebar.noRecent')}</div>
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

      <div className="border-t border-border-1 px-4 py-2">
        <button
          onClick={toggleHistory}
          className="flex items-center justify-between w-full text-[10px] font-semibold text-text-3 uppercase tracking-wider hover:text-text-2 transition-colors mb-1"
        >
          <span className="flex items-center gap-1.5"><History size={10} /> {t('sidebar.history')}</span>
          {showHistory ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>
        {showHistory && (
          <div className="animate-fade-in">
            {compareMode && compareSelection.length === 2 && onCompare && (
              <button
                onClick={() => { onCompare(compareSelection[0], compareSelection[1]); setCompareMode(false); setCompareSelection([]); }}
                className="btn-primary w-full text-[10px] py-1 mb-2"
              >
                <GitCompare size={10} /> {t('sidebar.compareSelected')}
              </button>
            )}




            <div className="flex items-center gap-1 mb-1.5">
              <button
                onClick={() => { setCompareMode(v => !v); setCompareSelection([]); }}
                className={`text-[9px] px-1.5 py-0.5 rounded transition-all font-medium ${
                  compareMode ? 'bg-purple/20 text-purple border border-purple/30' : 'bg-surface-3 text-text-3 border border-border-1 hover:text-text-2'
                }`}
              >
                
                <span className="flex items-center gap-1"><GitCompare size={8} /> {t('sidebar.compare')}</span>
              </button>

  <button
    onClick={handleClearHistory}
    className="text-text-3 hover:text-red transition-colors"
  >
    <Trash2 size={10} />
  </button>


              <button onClick={fetchHistory} className="text-text-3 hover:text-text-2 transition-colors ml-auto">
                <RotateCcw size={10} className={historyLoading ? 'spin' : ''} />
              </button>
            </div>






            {historyLoading ? (
              <div className="flex justify-center py-2"><Loader2 size={14} className="spin text-text-3" /></div>
            ) : history.length === 0 ? (
              <div className="text-[10px] text-text-3 opacity-40 italic">{t('sidebar.noHistory')}</div>
            ) : (
              <div className="flex flex-col gap-0.5 max-h-40 overflow-y-auto">
                {history.map(h => {
                  const selected = compareSelection.includes(h.scan_id);
                  return (
                    <button
                      key={h.scan_id}
                      onClick={() => compareMode ? toggleCompareSelect(h.scan_id) : onLoadScan?.(h.scan_id)}
                      className={`flex items-center gap-2 w-full text-left px-2 py-1.5 rounded transition-colors group ${
                        selected ? 'bg-purple/15 border border-purple/30' : 'hover:bg-surface-3'
                      }`}
                    >
                      {compareMode && (
                        <span className={`w-3 h-3 rounded-sm border shrink-0 flex items-center justify-center text-[8px] ${
                          selected ? 'bg-purple border-purple text-white' : 'border-border-1'
                        }`}>
                          {selected ? '✓' : ''}
                        </span>
                      )}
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase shrink-0 ${
                        TYPE_COLOR[h.scan_type as ScanType] || 'bg-surface-3 text-text-3'
                      }`}>
                        {h.scan_type.slice(0, 2)}
                      </span>
                      <div className="flex flex-col min-w-0">
                        <span className="text-[11px] text-text-2 truncate font-mono group-hover:text-text-1 transition-colors">
                          {h.target}
                        </span>
                        <span className="text-[8px] text-text-3">
                          {h.status === 'completed' ? '✓' : h.status === 'running' ? '…' : '✗'}{' '}
                          {new Date(h.started_at).toLocaleDateString()}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="border-t border-border-1 px-3 py-2.5">
        <div className="flex items-center justify-center gap-1.5">
          <Lightbulb size={10} className="text-yellow mt-0.5 shrink-0" />
          <span
            className="text-[10px] text-text-2 leading-relaxed text-center"
            style={{ opacity: tipVisible ? 1 : 0, transition: 'opacity 0.3s ease' }}
          >
            {tip}
          </span>
        </div>
      </div>
    </aside>
  );
}

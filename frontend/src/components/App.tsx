'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Topbar } from './Topbar';
import { useShortcutsPanel } from '@/lib/useShortcutsPanel';
import { KeyboardShortcutsPanel } from './KeyboardShortcutsPanel';
import { Sidebar } from './Sidebar';
import { IdleView } from './views/IdleView';
import { ScanProgress } from './views/ScanProgress';
import { ScanResults } from './views/ScanResults';
import { ResultsSkeleton } from './ResultsSkeleton';
import { ToolPanels } from './tools/ToolPanels';
import { ScanComparison } from './views/ScanComparison';
import { WatchlistView } from './views/WatchlistView';
import { startScan, getWsUrl, getScan, getUsage } from '@/lib/api';
import { detectScanType, normalizeScanTarget } from '@/lib/scan-target';
import { MODULE_MAP } from './Sidebar';
import type { ScanType, ScanStatus, ToolMode, ScanResults as ScanResultsType, ScanMeta, LiveModuleStatus, UsageData } from '@/lib/types';

type View = 'idle' | 'tool' | 'scanning' | 'results' | 'compare' | 'watchlist';

const LIVE_STATUSES: readonly LiveModuleStatus[] = ['ok', 'skipped', 'rate_limited', 'error', 'running'];

function toLiveStatus(status: unknown): LiveModuleStatus {
  return typeof status === 'string' && (LIVE_STATUSES as readonly string[]).includes(status)
    ? (status as LiveModuleStatus)
    : 'ok';
}

function moduleDoneLine(msg: { module: string; status?: string; reason?: string; error?: string }): string {
  const detail = msg.reason || msg.error;
  switch (msg.status) {
    case 'skipped': return `⊘ ${msg.module}: skipped${detail ? ` - ${detail}` : ''}`;
    case 'rate_limited': return `⏳ ${msg.module}: rate limited${detail ? ` - ${detail}` : ''}`;
    case 'error': return `✗ ${msg.module}: ${detail || 'error'}`;
    default: return `✓ ${msg.module}`;
  }
}

export function App() {
  const [view, setView] = useState<View>('idle');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toolMode, setToolMode] = useState<ToolMode>(null);
  const [scanId, setScanId] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<ScanStatus>('idle');
  const [scanMeta, setScanMeta] = useState<(ScanMeta & { results: ScanResultsType }) | null>(null);
  const [progressLog, setProgressLog] = useState<string[]>([]);
  const [scanTarget, setScanTarget] = useState('');
  const [moduleStatuses, setModuleStatuses] = useState<Record<string, LiveModuleStatus>>({});
  const [totalModules, setTotalModules] = useState(0);
  const [compareIds, setCompareIds] = useState<[string, string] | null>(null);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const { isOpen: isShortcutsOpen, open: openShortcuts, close: closeShortcuts } = useShortcutsPanel();
  const wsRef = useRef<WebSocket | null>(null);
  const urlScanStarted = useRef(false);
  const usageLimitedRef = useRef(true);

  const handleHome = useCallback(() => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    setView('idle');
    setToolMode(null);
    setScanId(null);
    setScanStatus('idle');
    setScanMeta(null);
    setProgressLog([]);
    setScanTarget('');
    setModuleStatuses({});
    setTotalModules(0);
    setCompareIds(null);
  }, []);

  const handleTool = useCallback((mode: ToolMode) => {
    setToolMode(mode);
    setView('tool');
  }, []);

  const handleWatchlist = useCallback(() => {
    setView('watchlist');
  }, []);

  const handleUsageRefresh = useCallback(async () => {
    if (!usageLimitedRef.current) return;

    try {
      const data = await getUsage();
      setUsage(data);

      if (data.limit === null) {
        usageLimitedRef.current = false;
      }
    } catch {
      setUsage(null);
    }
  }, []);

  const fetchAndShowResults = useCallback(async (id: string) => {
    try {
      const raw = await getScan(id) as any;
      const normalized = {
        ...raw,
        id: raw.scan_id ?? raw.id ?? id,
        results: raw.results ? {
          ...raw.results,
          opsec: raw.results.opsec ?? raw.results.opsec_score ?? undefined,
        } : {},
      };
      setScanStatus('completed');
      setScanMeta(normalized);
      setView('results');
      // handleUsageRefresh();
    } catch {
      setScanStatus('failed');
      setProgressLog(prev => [...prev, 'Failed to fetch results after scan completed']);
    }
  }, []);
  // TODO
  // }, [handleUsageRefresh]);

  const handleLoadScan = useCallback((scanId: string) => {
    fetchAndShowResults(scanId);
  }, [fetchAndShowResults]);

  const handleCompare = useCallback((a: string, b: string) => {
    setCompareIds([a, b]);
    setView('compare');
  }, []);

  const pollForResults = useCallback(async (id: string) => {
    let seenProgress = 0;
    for (let i = 0; i < 120; i++) {
      await new Promise(r => setTimeout(r, 1500));
      try {
        const data = await getScan(id) as any;
        const progress: any[] = data.progress ?? [];
        if (progress.length > seenProgress) {
          const newMsgs = progress.slice(seenProgress);
          seenProgress = progress.length;
          setProgressLog(prev => {
            const lines = [...prev];
            for (const msg of newMsgs) {
              if (msg.type === 'module_start') lines.push(`→ ${msg.module}`);
              else if (msg.type === 'module_done') lines.push(moduleDoneLine(msg));
            }
            return lines;
          });
          setModuleStatuses(prev => {
            const next = { ...prev };
            for (const msg of newMsgs) {
              if (msg.type === 'module_start') next[msg.module] = 'running';
              else if (msg.type === 'module_done') next[msg.module] = toLiveStatus(msg.status);
            }
            return next;
          });
        }
        if (data.status === 'completed') {
          const normalized = {
            ...data,
            id: data.scan_id ?? data.id ?? id,
            results: data.results ? {
              ...data.results,
              opsec: data.results.opsec ?? data.results.opsec_score ?? undefined,
            } : {},
          };
          setScanStatus('completed');
          setScanMeta(normalized);
          setView('results');
          return;
        }
        if (data.status === 'error') {
          setScanStatus('failed');
          setProgressLog(prev => [...prev, `Error: ${data.error || 'unknown'}`]);
          return;
        }
      } catch {}
    }
    setScanStatus('failed');
  }, []);

  const connectWs = useCallback((id: string) => {
    if (wsRef.current) wsRef.current.close();
    const url = getWsUrl(id);
    const ws = new WebSocket(url);
    wsRef.current = ws;
    let done = false;

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);

        if (msg.type === 'module_start') {
          setProgressLog(prev => [...prev, `→ ${msg.module}`]);
          setModuleStatuses(prev => ({ ...prev, [msg.module]: 'running' }));

        } else if (msg.type === 'module_done') {
          setModuleStatuses(prev => ({ ...prev, [msg.module]: toLiveStatus(msg.status) }));
          setProgressLog(prev => [...prev, moduleDoneLine(msg)]);

        } else if (msg.type === '_done') {
          done = true;
          ws.close();
          fetchAndShowResults(id);

        } else if (msg.type === 'scan_error') {
          done = true;
          setScanStatus('failed');
          setProgressLog(prev => [...prev, `SCAN ERROR: ${msg.error}`]);

        } else if (msg.type === 'error') {
          done = true;
          setScanStatus('failed');
          setProgressLog(prev => [...prev, `ERROR: ${msg.error ?? msg.message}`]);
        }
      } catch {
        setProgressLog(prev => [...prev, e.data]);
      }
    };

    ws.onerror = () => {
      if (!done) {
        setProgressLog(prev => [...prev, 'WebSocket unavailable - switching to polling...']);
      }
    };

    ws.onclose = () => {
      if (!done) {
        pollForResults(id);
      }
    };
  }, [fetchAndShowResults, pollForResults]);

  const handleScan = useCallback(async (target: string, type: ScanType, modules: string[]) => {
    setScanTarget(target);
    setProgressLog([]);
    setModuleStatuses({});
    setTotalModules(modules.length);
    setScanMeta(null);
    setIsStarting(true);
    try {
      const { scan_id } = await startScan(target, type, modules);
      setIsStarting(false);
      setScanStatus('running');
      setView('scanning');
      setScanId(scan_id);
      connectWs(scan_id);
      handleUsageRefresh();
    } catch (e: unknown) {
      setIsStarting(false);
      setScanStatus('failed');
      setProgressLog([`Failed to start scan: ${e instanceof Error ? e.message : 'Unknown error'}`]);
    }
  }, [connectWs, handleUsageRefresh]);

  useEffect(() => {
    if (urlScanStarted.current) return;
    try {
      const raw = new URLSearchParams(window.location.search).get('target');
      if (!raw) return;
      urlScanStarted.current = true;
      const target = normalizeScanTarget(raw);
      if (!target) return;
      const type = detectScanType(target);
      window.history.replaceState({}, '', window.location.pathname);
      handleScan(target, type, MODULE_MAP[type]);
    } catch {}
  }, [handleScan]);

  useEffect(() => {
    handleUsageRefresh();
  }, [handleUsageRefresh]);

  useEffect(() => {
    return () => { wsRef.current?.close(); };
  }, []);

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar status={scanStatus} usage={usage} onHome={handleHome} onWatchlist={handleWatchlist} onMenuToggle={() => setSidebarOpen(v => !v)} onShortcuts={openShortcuts} />
      <div className="flex flex-1 relative">
        {sidebarOpen && <div onClick={() => setSidebarOpen(false)} className="fixed inset-0 bg-black/50 z-40 md:hidden" />}
        <Sidebar onScan={handleScan} onLoadScan={handleLoadScan} onCompare={handleCompare} isRunning={scanStatus === 'running'} isStarting={isStarting} isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <main className="flex-1 min-w-0 relative z-10">
          {view === 'idle' && <IdleView onTool={handleTool} onScan={handleScan} isStarting={isStarting} />}
          {view === 'tool' && toolMode && (
            <ToolPanels mode={toolMode} onBack={() => setView('idle')} />
          )}
          {view === 'scanning' && (
            <>
              <ScanProgress log={progressLog} target={scanTarget} moduleStatuses={moduleStatuses} totalModules={totalModules} />
              <ResultsSkeleton />
            </>
          )}
          {view === 'results' && scanMeta && (
            <ScanResults scan={scanMeta} onHome={handleHome} />
          )}
          {view === 'compare' && compareIds && (
            <ScanComparison scanIdA={compareIds[0]} scanIdB={compareIds[1]} onBack={handleHome} />
          )}
          {view === 'watchlist' && <WatchlistView onBack={handleHome} />}
        </main>
      </div>
      <KeyboardShortcutsPanel isOpen={isShortcutsOpen} onClose={closeShortcuts} />
    </div>
  );
}
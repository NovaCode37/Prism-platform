'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Topbar } from './Topbar';
import { Sidebar } from './Sidebar';
import { IdleView } from './views/IdleView';
import { ScanProgress } from './views/ScanProgress';
import { ScanResults } from './views/ScanResults';
import { ToolPanels } from './tools/ToolPanels';
import { startScan, getWsUrl, getScan } from '@/lib/api';
import type { ScanType, ScanStatus, ToolMode, ScanResults as ScanResultsType, ScanMeta } from '@/lib/types';

type View = 'idle' | 'tool' | 'scanning' | 'results';

export function App() {
  const [view, setView] = useState<View>('idle');
  const [toolMode, setToolMode] = useState<ToolMode>(null);
  const [scanId, setScanId] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<ScanStatus>('idle');
  const [scanMeta, setScanMeta] = useState<(ScanMeta & { results: ScanResultsType }) | null>(null);
  const [progressLog, setProgressLog] = useState<string[]>([]);
  const [scanTarget, setScanTarget] = useState('');
  const wsRef = useRef<WebSocket | null>(null);

  const handleHome = useCallback(() => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    setView('idle');
    setToolMode(null);
    setScanId(null);
    setScanStatus('idle');
    setScanMeta(null);
    setProgressLog([]);
    setScanTarget('');
  }, []);

  const handleTool = useCallback((mode: ToolMode) => {
    setToolMode(mode);
    setView('tool');
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
    } catch {
      setScanStatus('failed');
      setProgressLog(prev => [...prev, 'Failed to fetch results after scan completed']);
    }
  }, []);

  const connectWs = useCallback((id: string) => {
    if (wsRef.current) wsRef.current.close();
    const url = getWsUrl(id);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);

        if (msg.type === 'module_start') {
          setProgressLog(prev => [...prev, `→ ${msg.module}`]);

        } else if (msg.type === 'module_done') {
          if (msg.status === 'error') {
            setProgressLog(prev => [...prev, `✗ ${msg.module}: ${msg.error || 'error'}`]);
          } else {
            setProgressLog(prev => [...prev, `✓ ${msg.module}`]);
          }

        } else if (msg.type === '_done') {
          ws.close();
          fetchAndShowResults(id);

        } else if (msg.type === 'scan_error') {
          setScanStatus('failed');
          setProgressLog(prev => [...prev, `SCAN ERROR: ${msg.error}`]);

        } else if (msg.type === 'error') {
          setScanStatus('failed');
          setProgressLog(prev => [...prev, `ERROR: ${msg.error ?? msg.message}`]);
        }
      } catch {
        setProgressLog(prev => [...prev, e.data]);
      }
    };

    ws.onerror = () => {
      setScanStatus('failed');
      setProgressLog(prev => [...prev, 'WebSocket connection error — is the backend running on port 8080?']);
    };

    ws.onclose = (e) => {
      if (!e.wasClean && scanStatus === 'running') {
        setProgressLog(prev => [...prev, 'WebSocket closed — polling for results…']);
        pollForResults(id);
      }
    };
  }, [scanStatus, fetchAndShowResults]);

  const pollForResults = useCallback(async (id: string) => {
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 3000));
      try {
        const data = await getScan(id) as any;
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
          return;
        }
      } catch { /* keep polling */ }
    }
    setScanStatus('failed');
  }, []);

  const handleScan = useCallback(async (target: string, type: ScanType, modules: string[]) => {
    setScanTarget(target);
    setProgressLog([]);
    setScanStatus('running');
    setView('scanning');
    setScanMeta(null);
    try {
      const { scan_id } = await startScan(target, type, modules);
      setScanId(scan_id);
      connectWs(scan_id);
    } catch (e: unknown) {
      setScanStatus('failed');
      setProgressLog([`Failed to start scan: ${e instanceof Error ? e.message : 'Unknown error'}`]);
    }
  }, [connectWs]);

  useEffect(() => {
    return () => { wsRef.current?.close(); };
  }, []);

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar status={scanStatus} onHome={handleHome} />
      <div className="flex flex-1 relative">
        <Sidebar onScan={handleScan} isRunning={scanStatus === 'running'} />
        <main className="flex-1 min-w-0 relative z-10">
          {view === 'idle' && <IdleView onTool={handleTool} />}
          {view === 'tool' && toolMode && (
            <ToolPanels mode={toolMode} onBack={() => setView('idle')} />
          )}
          {view === 'scanning' && (
            <ScanProgress log={progressLog} target={scanTarget} />
          )}
          {view === 'results' && scanMeta && (
            <ScanResults scan={scanMeta} />
          )}
        </main>
      </div>
    </div>
  );
}

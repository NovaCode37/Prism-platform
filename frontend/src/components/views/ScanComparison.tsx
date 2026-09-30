'use client';
import { useState, useEffect } from 'react';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { getScan } from '@/lib/api';
import type { ScanMeta, ScanResults as ScanResultsType } from '@/lib/types';

type FullScan = ScanMeta & { results: ScanResultsType };

interface Props {
  scanIdA: string;
  scanIdB: string;
  onBack: () => void;
}

function flattenResults(results: ScanResultsType): Record<string, string> {
  const flat: Record<string, string> = {};
  for (const [mod, data] of Object.entries(results)) {
    if (!data || mod === 'report_path' || mod === 'map_data' || mod === 'graph') continue;
    if (typeof data === 'object' && !Array.isArray(data)) {
      for (const [k, v] of Object.entries(data as Record<string, unknown>)) {
        flat[`${mod}.${k}`] = typeof v === 'object' ? JSON.stringify(v) : String(v ?? '');
      }
    } else {
      flat[mod] = typeof data === 'object' ? JSON.stringify(data) : String(data);
    }
  }
  return flat;
}

type DiffStatus = 'added' | 'removed' | 'changed' | 'same';

function diffResults(a: Record<string, string>, b: Record<string, string>): { key: string; status: DiffStatus; valA?: string; valB?: string }[] {
  const allKeys = Array.from(new Set([...Object.keys(a), ...Object.keys(b)]));
  const rows: { key: string; status: DiffStatus; valA?: string; valB?: string }[] = [];
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

const STATUS_STYLE: Record<DiffStatus, string> = {
  added: 'bg-green/10 text-green',
  removed: 'bg-red/10 text-red',
  changed: 'bg-yellow/10 text-yellow',
  same: '',
};

export function ScanComparison({ scanIdA, scanIdB, onBack }: Props) {
  const [scanA, setScanA] = useState<FullScan | null>(null);
  const [scanB, setScanB] = useState<FullScan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showUnchanged, setShowUnchanged] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const [a, b] = await Promise.all([getScan(scanIdA), getScan(scanIdB)]);
        if (cancelled) return;
        setScanA(a as FullScan);
        setScanB(b as FullScan);
      } catch {
        if (!cancelled) setError('Failed to load one or both scans');
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [scanIdA, scanIdB]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 size={24} className="spin text-blue" />
      </div>
    );
  }

  if (error || !scanA || !scanB) {
    return (
      <div className="p-6">
        <button onClick={onBack} className="flex items-center gap-1 text-text-3 hover:text-text-1 text-sm mb-4">
          <ArrowLeft size={14} /> Back
        </button>
        <div className="text-red text-sm">{error || 'Scans not found'}</div>
      </div>
    );
  }

  const flatA = flattenResults(scanA.results);
  const flatB = flattenResults(scanB.results);
  const diff = diffResults(flatA, flatB);
  const filtered = showUnchanged ? diff : diff.filter(r => r.status !== 'same');
  const stats = {
    added: diff.filter(r => r.status === 'added').length,
    removed: diff.filter(r => r.status === 'removed').length,
    changed: diff.filter(r => r.status === 'changed').length,
    same: diff.filter(r => r.status === 'same').length,
  };

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      <button onClick={onBack} className="flex items-center gap-1 text-text-3 hover:text-text-1 text-sm mb-4">
        <ArrowLeft size={14} /> Back
      </button>

      <h2 className="text-lg font-bold text-text-1 mb-4">Scan Comparison</h2>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-surface-2 rounded-lg p-3 border border-border-1">
          <div className="text-[10px] font-semibold text-text-3 uppercase mb-1">Scan A</div>
          <div className="text-sm font-mono text-text-1">{scanA.target}</div>
          <div className="text-[10px] text-text-3">{scanA.scan_type} &middot; {scanA.started_at ? new Date(scanA.started_at).toLocaleString() : 'N/A'}</div>
        </div>
        <div className="bg-surface-2 rounded-lg p-3 border border-border-1">
          <div className="text-[10px] font-semibold text-text-3 uppercase mb-1">Scan B</div>
          <div className="text-sm font-mono text-text-1">{scanB.target}</div>
          <div className="text-[10px] text-text-3">{scanB.scan_type} &middot; {scanB.started_at ? new Date(scanB.started_at).toLocaleString() : 'N/A'}</div>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-3 text-[10px]">
        <span className="text-green font-semibold">+{stats.added} added</span>
        <span className="text-red font-semibold">-{stats.removed} removed</span>
        <span className="text-yellow font-semibold">~{stats.changed} changed</span>
        <span className="text-text-3">{stats.same} unchanged</span>
        <label className="flex items-center gap-1 ml-auto text-text-3 cursor-pointer">
          <input type="checkbox" checked={showUnchanged} onChange={e => setShowUnchanged(e.target.checked)} className="rounded" />
          Show unchanged
        </label>
      </div>

      {filtered.length === 0 ? (
        <div className="text-text-3 text-sm text-center py-8">No differences found</div>
      ) : (
        <div className="border border-border-1 rounded-lg overflow-hidden">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="bg-surface-2 text-text-3">
                <th className="text-left px-3 py-2 font-semibold w-1/4">Field</th>
                <th className="text-left px-3 py-2 font-semibold w-[37.5%]">Scan A</th>
                <th className="text-left px-3 py-2 font-semibold w-[37.5%]">Scan B</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(row => (
                <tr key={row.key} className={`border-t border-border-1 ${STATUS_STYLE[row.status]}`}>
                  <td className="px-3 py-1.5 font-mono font-medium">{row.key}</td>
                  <td className="px-3 py-1.5 font-mono break-all max-w-0">
                    <span className="line-clamp-2">{row.valA ?? '-'}</span>
                  </td>
                  <td className="px-3 py-1.5 font-mono break-all max-w-0">
                    <span className="line-clamp-2">{row.valB ?? '-'}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

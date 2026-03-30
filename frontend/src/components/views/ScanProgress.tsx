'use client';
import { Terminal } from 'lucide-react';

export function ScanProgress({ log, target }: { log: string[]; target: string }) {
  return (
    <div className="p-6 animate-fade-in">
      <div className="mb-4">
        <div className="text-xs text-text-3 uppercase tracking-wider font-semibold mb-1">Scanning</div>
        <div className="text-lg font-bold text-text-1">{target}</div>
      </div>
      <div className="card overflow-hidden">
        <div className="card-head flex items-center gap-2">
          <Terminal size={11} />
          Progress Log
        </div>
        <div className="p-3 font-mono text-[11px] min-h-[200px] max-h-[60vh] overflow-y-auto space-y-0.5">
          {log.length === 0 ? (
            <div className="text-text-3">Initializing scan…</div>
          ) : (
            log.map((line, i) => {
              const isErr = line.toLowerCase().includes('error') || line.toLowerCase().includes('fail');
              const isOk = line.includes('✓') || line.toLowerCase().includes('found') || line.toLowerCase().includes('complete');
              return (
                <div key={i} className={isErr ? 'text-red' : isOk ? 'text-green' : 'text-text-2'}>
                  <span className="text-text-3 select-none mr-2">{String(i + 1).padStart(2, '0')}</span>
                  {line}
                </div>
              );
            })
          )}
          <div className="flex items-center gap-1.5 text-blue mt-2">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue animate-pulse" />
            <span className="animate-pulse">Running…</span>
          </div>
        </div>
      </div>
    </div>
  );
}

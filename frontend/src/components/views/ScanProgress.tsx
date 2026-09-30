'use client';
import { Terminal, Check, X, Loader2, Circle, Ban, Hourglass } from 'lucide-react';
import { useTranslations } from '@/lib/i18n';
import type { LiveModuleStatus } from '@/lib/types';

interface Props {
  log: string[];
  target: string;
  moduleStatuses?: Record<string, LiveModuleStatus>;
  totalModules?: number;
}

const STATUS_STYLE: Record<LiveModuleStatus, { cls: string; Icon: typeof Check; spin?: boolean }> = {
  ok: { cls: 'text-green border-green/30 bg-green/5', Icon: Check },
  error: { cls: 'text-red border-red/30 bg-red/5', Icon: X },
  skipped: { cls: 'text-text-3 border-border-1 bg-surface-2', Icon: Ban },
  rate_limited: { cls: 'text-yellow border-yellow/30 bg-yellow/5', Icon: Hourglass },
  running: { cls: 'text-blue border-blue/30 bg-blue/5', Icon: Loader2, spin: true },
};

export function ScanProgress({ log, target, moduleStatuses = {}, totalModules = 0 }: Props) {
  const { t } = useTranslations();
  const entries = Object.entries(moduleStatuses) as [string, LiveModuleStatus][];
  const completed = entries.filter(([, s]) => s !== 'running').length;
  const cap = Math.max(totalModules, entries.length);
  const percent = cap > 0 ? Math.min(100, Math.round((completed / cap) * 100)) : 0;

  return (
    <div className="p-6 animate-fade-in">
      <div className="mb-4">
        <div className="text-xs text-text-3 uppercase tracking-wider font-semibold mb-1">{t('topbar.scanning')}</div>
        <div className="text-lg font-bold text-text-1">{target}</div>
      </div>

      {cap > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2 text-[11px]">
            <span className="text-text-2 font-semibold">
              {completed}/{cap} {t('progress.modulesLabel')}
            </span>
            <span className="text-text-3 font-mono">{percent}%</span>
          </div>
          <div className="w-full h-2 bg-surface-2 rounded-full overflow-hidden border border-border-1">
            <div
              className="h-full transition-all duration-300"
              style={{ width: `${percent}%`, background: 'linear-gradient(90deg, #4f8ef7, #7c5cfc)' }}
            />
          </div>
          {entries.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {entries.map(([mod, status]) => {
                const style = STATUS_STYLE[status] ?? { cls: 'text-blue border-blue/30 bg-blue/5', Icon: Circle };
                const Icon = style.Icon;
                const label = status === 'rate_limited' ? `${mod} (rate limited)` : status === 'skipped' ? `${mod} (skipped)` : mod;
                return (
                  <span key={mod} title={label} className={`inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded border ${style.cls}`}>
                    <Icon size={10} className={style.spin ? 'spin' : ''} />
                    {mod}
                  </span>
                );
              })}
            </div>
          )}
        </div>
      )}
      <div className="card overflow-hidden">
        <div className="card-head flex items-center gap-2">
          <Terminal size={11} />
          {t('progress.log')}
        </div>
        <div role="log" aria-live="polite" aria-relevant="additions" aria-label={t('progress.log')} className="p-3 font-mono text-[11px] min-h-[200px] max-h-[60vh] overflow-y-auto space-y-0.5">
          {log.length === 0 ? (
            <div className="text-text-3">{t('progress.initializing')}</div>
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
            <span className="animate-pulse">{t('progress.running')}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

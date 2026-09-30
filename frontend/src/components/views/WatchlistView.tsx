'use client';
import { useState, useEffect, useCallback } from 'react';
import { Eye, Plus, Trash2, Bell, Clock, RefreshCw, ChevronDown, ChevronUp, AlertTriangle, ArrowLeft, Pause, Play } from 'lucide-react';
import { useTranslations } from '@/lib/i18n';
import type { Watchlist, ScanType } from '@/lib/types';
import { formatWatchlistChange } from '@/lib/watchlist-alert-utils';
import { listWatchlists, createWatchlist, deleteWatchlist, setWatchlistPaused, testWebhook } from '@/lib/api';

const SCAN_TYPES: (ScanType | 'auto')[] = ['auto', 'domain', 'ip', 'email', 'phone', 'username'];

function fmtTime(ts: number | null): string {
  if (!ts) return '—';
  return new Date(ts * 1000).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

const RELATIVE_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 31536000],
  ['month', 2592000],
  ['day', 86400],
  ['hour', 3600],
  ['minute', 60],
  ['second', 1],
];

function fmtRelative(ts: number | null, locale: string): string {
  if (!ts) return '—';
  const diff = ts - Date.now() / 1000;
  const abs = Math.abs(diff);
  try {
    const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
    for (const [unit, secs] of RELATIVE_UNITS) {
      if (abs >= secs || unit === 'second') return rtf.format(Math.round(diff / secs), unit);
    }
  } catch {}
  return fmtTime(ts);
}

function StatusDot({ status, paused }: { status: string; paused?: boolean }) {
  const color = paused ? 'bg-text-3' : status === 'completed' ? 'bg-green' : status === 'error' ? 'bg-red' : 'bg-text-3';
  return <span className={`inline-block w-2 h-2 rounded-full ${color}`} />;
}

export function WatchlistView({ onBack }: { onBack: () => void }) {
  const { t, locale } = useTranslations();
  const [, setTick] = useState(0);
  const [items, setItems] = useState<Watchlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const [target, setTarget] = useState('');
  const [scanType, setScanType] = useState<ScanType | 'auto'>('auto');
  const [interval, setIntervalHours] = useState(24);
  const [webhook, setWebhook] = useState('');
  const [testingWebhook, setTestingWebhook] = useState(false);
  const [webhookTestResult, setWebhookTestResult] = useState<{ ok: boolean; message: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { watchlists } = await listWatchlists();
      setItems(watchlists);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('watchlist.failedToLoad'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const id = setInterval(() => setTick(n => n + 1), 60000);
    return () => clearInterval(id);
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!target.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await createWatchlist({
        target: target.trim(),
        scan_type: scanType,
        modules: [],
        interval_hours: interval,
        webhook_url: webhook.trim() || undefined,
      });
      setTarget('');
      setWebhook('');
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('watchlist.failedToCreate'));
    } finally {
      setCreating(false);
    }
  };

const handleTestWebhook = async () => {
  if (!webhook.trim()) return;
  setTestingWebhook(true);
  setWebhookTestResult(null);
  try {
    await testWebhook(webhook.trim());
    setWebhookTestResult({ ok: true, message: 'Test webhook delivered successfully.' });
  } catch (e: unknown) {
    setWebhookTestResult({ ok: false, message: e instanceof Error ? e.message : 'Test failed.' });
  } finally {
    setTestingWebhook(false);
  }
};

  const remove = async (id: string) => {
    try {
      await deleteWatchlist(id);
      setItems(prev => prev.filter(w => w.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('watchlist.failedToDelete'));
    }
  };

  const exportAlertsJson = (w: Watchlist) => {
  try {
    const blob = new Blob([JSON.stringify(w.alerts, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `prism-watchlist-${w.target}-alerts.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  } catch (e: unknown) {
    setError(e instanceof Error ? e.message : 'JSON download failed');
  }
};

const exportAlertsCsv = (w: Watchlist) => {
  try {
    const rows = w.alerts.map(a => [
      fmtTime(a.at),
      a.added_count,
      a.removed_count,
      a.added.join('; '),
      a.removed.join('; '),
    ]);
    const header = ['time', 'added_count', 'removed_count', 'added', 'removed'];
    const csv = [header, ...rows].map(r => r.join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `prism-watchlist-${w.target}-alerts.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  } catch (e: unknown) {
    setError(e instanceof Error ? e.message : 'CSV download failed');
  }
};

  const togglePause = async (w: Watchlist) => {
    try {
      const updated = await setWatchlistPaused(w.id, !w.paused);
      setItems(prev => prev.map(item => item.id === w.id ? { ...item, ...updated } : item));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('watchlist.failedToToggle'));
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-5 py-6">
      <div className="flex items-center gap-3 mb-5">
        <button onClick={onBack} className="text-text-3 hover:text-text-1 transition-colors" aria-label={t('watchlist.back')}>
          <ArrowLeft size={18} />
        </button>
        <Eye size={18} className="text-blue" />
        <h1 className="text-lg font-semibold text-text-1">{t('watchlist.title')}</h1>
        <button onClick={load} className="ml-auto text-text-3 hover:text-text-1 transition-colors" title={t('watchlist.refresh')} aria-label={t('watchlist.refresh')}>
          <RefreshCw size={14} />
        </button>
      </div>

      <p className="text-[12px] text-text-3 mb-5 leading-relaxed">
        {t('watchlist.description')}
      </p>

      <form onSubmit={submit} className="bg-surface-1 border border-border-1 rounded-lg p-4 mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="sm:col-span-2">
            <label className="block text-[10px] uppercase tracking-wider text-text-3 mb-1">{t('watchlist.target')}</label>
            <input
              value={target}
              onChange={e => setTarget(e.target.value)}
              placeholder={t('watchlist.targetPlaceholder')}
              className="w-full bg-surface-2 border border-border-1 rounded px-3 py-2 text-sm text-text-1 font-mono focus:outline-none focus:border-blue"
            />
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-text-3 mb-1">{t('watchlist.scanType')}</label>
            <select
              value={scanType}
              onChange={e => setScanType(e.target.value as ScanType | 'auto')}
              className="w-full bg-surface-2 border border-border-1 rounded px-3 py-2 text-sm text-text-1 focus:outline-none focus:border-blue"
            >
              {SCAN_TYPES.map(st => <option key={st} value={st}>{st}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-text-3 mb-1">{t('watchlist.intervalHours')}</label>
            <input
              type="number"
              min={1}
              max={720}
              value={interval}
              onChange={e => setIntervalHours(Number(e.target.value))}
              className="w-full bg-surface-2 border border-border-1 rounded px-3 py-2 text-sm text-text-1 focus:outline-none focus:border-blue"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-[10px] uppercase tracking-wider text-text-3 mb-1">{t('watchlist.webhookUrl')}</label>
            <div className="flex gap-2">
              <input
                value={webhook}
                onChange={e => { setWebhook(e.target.value); setWebhookTestResult(null); }}
                placeholder="https://hooks.slack.com/…"
                className="flex-1 bg-surface-2 border border-border-1 rounded px-3 py-2 text-sm text-text-1 font-mono focus:outline-none focus:border-blue"
              />
              <button
                type="button"
                disabled={!webhook.trim() || testingWebhook}
                onClick={handleTestWebhook}
                className="px-3 py-2 text-xs rounded border border-border-1 bg-surface-2 text-text-2 hover:border-blue hover:text-blue disabled:opacity-40 whitespace-nowrap"
              >
                {testingWebhook ? 'Sending…' : 'Send test'}
              </button>
            </div>
            {webhookTestResult && (
              <p className={`text-xs mt-1 ${webhookTestResult.ok ? 'text-green' : 'text-red'}`}>
                {webhookTestResult.message}
              </p>
            )}
          </div>
        </div>
        <button type="submit" disabled={creating || !target.trim()} className="btn-primary mt-3 disabled:opacity-50">
          <Plus size={13} /> {creating ? t('watchlist.adding') : t('watchlist.addToWatchlist')}
        </button>
      </form>

      {error && (
        <div className="flex items-center gap-2 text-red text-sm mb-4">
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {loading ? (
        <div className="text-text-3 text-sm">{t('watchlist.loading')}</div>
      ) : items.length === 0 ? (
        <div className="text-text-3 text-sm text-center py-10">{t('watchlist.emptyState')}</div>
      ) : (
        <div className="space-y-2">
          {items.map(w => (
            <div key={w.id} className="bg-surface-1 border border-border-1 rounded-lg">
              <div className="flex items-center gap-3 p-3">
                <StatusDot status={w.last_status} paused={w.paused} />
                <div className="min-w-0 flex-1">
                  <div className="font-mono text-sm text-text-1 truncate">{w.target}</div>
                  <div className="text-[11px] text-text-3 flex items-center gap-2 flex-wrap">
                    <span className="uppercase">{w.scan_type}</span>
                    <span className="flex items-center gap-1"><Clock size={10} /> {t('watchlist.everyNHours').replace('{n}', String(w.interval_hours))}</span>
                    <span>· {w.run_count === 1 ? t('watchlist.runCountOne').replace('{n}', String(w.run_count)) : t('watchlist.runCount').replace('{n}', String(w.run_count))}</span>
                    <span title={fmtTime(w.last_run)}>· {t('watchlist.lastRun')} {fmtRelative(w.last_run, locale)}</span>
                    {w.paused ? (
                      <span className="text-text-2">· {t('watchlist.paused')}</span>
                    ) : (
                      <span title={fmtTime(w.next_run)}>· {t('watchlist.nextRun')} {fmtRelative(w.next_run, locale)}</span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => setExpanded(expanded === w.id ? null : w.id)}
                  className="flex items-center gap-1 text-[11px] text-text-2 hover:text-text-1 transition-colors px-2 py-1 rounded hover:bg-surface-2"
                  title={t('watchlist.alerts')}
                >
                  <Bell size={12} />
                  {w.alerts.length}
                  {expanded === w.id ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>
                <button
                  onClick={() => togglePause(w)}
                  className="text-text-3 hover:text-text-1 transition-colors p-1"
                  title={w.paused ? t('watchlist.resume') : t('watchlist.pause')}
                  aria-label={w.paused ? t('watchlist.resume') : t('watchlist.pause')}
                >
                  {w.paused ? <Play size={14} /> : <Pause size={14} />}
                </button>
                <button onClick={() => remove(w.id)} className="text-text-3 hover:text-red transition-colors p-1" title={t('watchlist.delete')} aria-label={t('watchlist.delete')}>
                  <Trash2 size={14} />
                </button>
              </div>

              {expanded === w.id && (
                <div className="border-t border-border-1 p-3">
                  {w.alerts.length > 0 && (
                <div className="flex gap-2 mb-3">
                  <button
                    onClick={() => exportAlertsJson(w)}
                    className="px-3 py-1 text-xs rounded border border-border-1 text-text-2 hover:text-text-1 hover:bg-surface-2 transition-colors"
                  >
                    Export JSON
                  </button>
                  <button
                    onClick={() => exportAlertsCsv(w)}
                    className="px-3 py-1 text-xs rounded border border-border-1 text-text-2 hover:text-text-1 hover:bg-surface-2 transition-colors"
                  >
                    Export CSV
                  </button>
                </div>
                )}
                  {w.alerts.length === 0 ? (
                    <div className="text-[12px] text-text-3">{t('watchlist.noAlerts')}</div>
                  ) : (
                    <div className="space-y-3">
                      {w.alerts.map((a, i) => (
                        <div key={i} className="text-[11px]">
                          <div className="text-text-3 mb-1">
                            <span title={fmtTime(a.at)}>{fmtRelative(a.at, locale)}</span> · <span className="text-green">+{a.added_count}</span> / <span className="text-red">−{a.removed_count}</span> {t('watchlist.changes')}
                          </div>
                          <div className="font-mono space-y-0.5">
                            {a.added.map((c, j) => <div key={`a${j}`} className="text-green break-all">+ {formatWatchlistChange(c)}</div>)}
                            {a.removed.map((c, j) => <div key={`r${j}`} className="text-red break-all">− {c}</div>)}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

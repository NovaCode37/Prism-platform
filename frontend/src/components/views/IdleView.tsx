'use client';
import { useEffect, useState } from 'react';
import { FileText, Mail, Bitcoin, QrCode, ChevronRight, Globe, User, Phone, Shield, Database, Zap, Eye, Activity, Network, Hash, Binary, KeyRound } from 'lucide-react';
import { useTranslations } from '@/lib/i18n';
import { getPrismDemoMode } from '@/lib/prism-config';
import { Logo } from '../Logo';
import type { ToolMode } from '@/lib/types';

const TOOL_IDS = ['metadata', 'headers', 'crypto', 'qr', 'mac', 'subnet', 'hash', 'encoder', 'jwt'] as const;
type ToolId = typeof TOOL_IDS[number];

const ICONS: Record<ToolId, React.ElementType> = {
  subnet: Globe,
  metadata: FileText,
  headers: Mail,
  crypto: Bitcoin,
  qr: QrCode,
  mac: Network,
  hash: Hash,
  encoder: Binary,
  jwt: KeyRound,
};

const CAPS_KEYS = ['domain', 'email', 'phone', 'username'] as const;
type CapsKey = typeof CAPS_KEYS[number];

interface Props { onTool: (mode: ToolMode) => void; }

export function IdleView({ onTool }: Props) {
  const { t } = useTranslations();
  const demoMode = getPrismDemoMode();
  const [targetIdx, setTargetIdx] = useState(0);
  const [displayed, setDisplayed] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [counters, setCounters] = useState([0, 0, 0, 0]);

  const statValues = [22, 12, 5, 0];
  const TARGETS = ['domain.com', '192.168.1.1', 'user@example.com', '@username', '+1 555 000 0000'];

  useEffect(() => {
    const target = TARGETS[targetIdx];
    let timer: ReturnType<typeof setTimeout>;
    if (!deleting && displayed.length < target.length) {
      timer = setTimeout(() => setDisplayed(target.slice(0, displayed.length + 1)), 75);
    } else if (!deleting && displayed.length === target.length) {
      timer = setTimeout(() => setDeleting(true), 1600);
    } else if (deleting && displayed.length > 0) {
      timer = setTimeout(() => setDisplayed(displayed.slice(0, -1)), 35);
    } else {
      setDeleting(false);
      setTargetIdx(i => (i + 1) % TARGETS.length);
    }
    return () => clearTimeout(timer);
  }, [displayed, deleting, targetIdx]);

  useEffect(() => {
    const timers = statValues.map((val, i) =>
      setTimeout(() => {
        let cur = 0;
        const iv = setInterval(() => {
          cur = Math.min(cur + 1, val);
          setCounters(prev => { const n = [...prev]; n[i] = cur; return n; });
          if (cur >= val) clearInterval(iv);
        }, 100);
      }, i * 180)
    );
    return () => timers.forEach(timer => timer && clearTimeout(timer));
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-48px)] px-6 py-10">

      <div className="relative mb-5">
        <div className="absolute inset-0 rounded-full blur-2xl opacity-25" style={{ background: 'radial-gradient(circle, #4f8ef7 0%, #7c5cfc 100%)', transform: 'scale(2)' }} />
        <Logo size={54} animated />
      </div>

      <h1 className="text-xl font-bold tracking-widest text-text-1 mb-1">{t('idle.title')}</h1>
      <div className="text-[10px] text-text-2 uppercase tracking-widest mb-5">{t('idle.subtitle')}</div>

      <div className="flex items-center gap-2 mb-7 font-mono text-[12px] px-4 py-2 rounded border border-border-1 bg-surface-2">
        <span className="text-text-3">target://</span>
        <span className="text-blue min-w-[140px]">{displayed}</span>
        <span className="text-blue opacity-80" style={{ animation: 'cursor-blink 0.8s step-end infinite' }}>▌</span>
      </div>

      <div className="flex flex-wrap justify-center gap-2 sm:gap-3 mb-8">
        {[
          { key: 'modules', icon: Database },
          { key: 'sources', icon: Zap },
          { key: 'scanTypes', icon: Eye },
          { key: 'status', icon: Activity, text: t('idle.stats.online') },
        ].map((s, i) => (
          <div key={s.key} className="flex flex-col items-center px-4 py-2.5 rounded border border-border-1 bg-surface-2 min-w-[70px]">
            <s.icon size={11} className="text-blue mb-1.5 opacity-60" />
            {s.text ? (
              <div className="relative flex items-center justify-center">
                <span className="absolute -left-3 w-1.5 h-1.5 rounded-full bg-green-500" style={{ animation: 'cursor-blink 1.5s ease-in-out infinite' }} />
                <span className="text-[10px] font-bold text-green-400 font-mono">{s.text}</span>
              </div>
            ) : (
              <div className="text-[15px] font-bold text-text-1 font-mono leading-none">{counters[i]}</div>
            )}
            <div className="text-[9px] text-text-3 uppercase tracking-wider mt-1">{t(`idle.stats.${s.key}`)}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 w-full max-w-2xl mb-8">
        {CAPS_KEYS.map(capKey => (
            <div key={capKey} className="card p-3 hover:border-border-3 transition-colors">
              <div className="flex items-center gap-1.5 mb-2">
                {capKey === 'domain' && <Globe size={10} className="text-blue shrink-0 opacity-80" />}
                {capKey === 'email' && <User size={10} className="text-blue shrink-0 opacity-80" />}
                {capKey === 'phone' && <Phone size={10} className="text-blue shrink-0 opacity-80" />}
                {capKey === 'username' && <Shield size={10} className="text-blue shrink-0 opacity-80" />}
                <div className="text-[10px] font-bold text-blue uppercase tracking-wider">{t(`idle.caps.${capKey}.title`)}</div>
              </div>
              <div className="text-[11px] text-text-3 leading-relaxed">{t(`idle.caps.${capKey}.item1`)}</div>
              <div className="text-[11px] text-text-3 leading-relaxed">{t(`idle.caps.${capKey}.item2`)}</div>
              {capKey !== 'phone' && <div className="text-[11px] text-text-3 leading-relaxed">{t(`idle.caps.${capKey}.item3`)}</div>}
            </div>
          ))}
      </div>

      <div className="w-full max-w-2xl">
        <div className="text-[10px] font-semibold text-text-3 uppercase tracking-wider mb-2">{t('idle.standaloneTools')}</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
          {TOOL_IDS.map(toolId => {
            const Icon = ICONS[toolId];
            return (
              <button
                key={toolId}
                onClick={() => onTool(toolId as ToolMode)}
                className="card px-3 py-2 text-left hover:border-border-3 hover:bg-surface-3 transition-all group flex items-center gap-2.5 cursor-pointer"
              >
                <Icon size={13} className="text-blue shrink-0" />
                <div className="min-w-0">
                  <div className="text-[11px] font-semibold text-text-1 leading-tight">{t(`idle.tools.${toolId}.label`)}</div>
                  <div className="text-[9px] text-text-3 truncate">{t(`idle.tools.${toolId}.desc`)}</div>
                </div>
                <ChevronRight size={10} className="text-text-3 group-hover:text-text-2 transition-colors ml-auto shrink-0" />
              </button>
            );
          })}
        </div>
      </div>

      {demoMode && (
        <div className="w-full max-w-2xl mt-6 px-4 py-3 rounded border border-border-1 bg-surface-2 text-center">
          <p className="text-[11px] text-text-3">{t('idle.demo.line1')}</p>
          <p className="text-[11px] text-text-3 mt-1">
            {t('idle.demo.line2Prefix')}{' '}
            <a href="https://github.com/NovaCode37/Prism-platform" target="_blank" rel="noopener noreferrer" className="text-blue hover:underline">
              {t('idle.demo.selfHost')}
            </a>
            {' '}{t('idle.demo.line2Suffix')}
          </p>
        </div>
      )}
    </div>
  );
}

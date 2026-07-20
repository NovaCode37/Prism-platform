'use client';
import { useEffect, useState } from 'react';
import { Loader2, CheckCircle, XCircle, Github, Star, Terminal, Sun, Moon, Menu, Languages, Book, Eye, Puzzle, AlertCircle } from 'lucide-react';
import { useTheme } from '@/lib/useTheme';
import { useTranslations, SUPPORTED_LOCALES } from '@/lib/i18n';
import { Logo } from './Logo';
import type { ScanStatus, UsageData } from '@/lib/types';

interface Props {
  status: ScanStatus;
  usage: UsageData | null;
  onHome: () => void;
  onWatchlist: () => void;
  onMenuToggle: () => void;
}

function useDateTime() {
  const [dt, setDt] = useState({ date: '', time: '' });
  useEffect(() => {
    const fmt = () => {
      const now = new Date();
      return {
        date: now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
        time: now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      };
    };
    setDt(fmt());
    const iv = setInterval(() => setDt(fmt()), 1000);
    return () => clearInterval(iv);
  }, []);
  return dt;
}

export function Topbar({ status, usage, onHome, onWatchlist, onMenuToggle }: Props) {
  const { date, time } = useDateTime();
  const { theme, toggleTheme, mounted } = useTheme();
  const { locale, setLocale, t } = useTranslations();

  return (
    <header className="h-12 flex items-center px-5 border-b border-border-1 bg-surface-1/80 backdrop-blur-sm sticky top-0 z-50">
      <button onClick={onMenuToggle} className="md:hidden text-text-3 hover:text-text-1 transition-colors p-1 -ml-1" aria-label="Toggle menu">
        <Menu size={18} />
      </button>

      <button onClick={onHome} className="flex items-center gap-2.5 cursor-pointer group shrink-0">
        <Logo size={26} />
        <span className="font-brand text-[15px] tracking-tight text-text-1 group-hover:text-white transition-colors">
          PRISM
        </span>
        <span
          className="text-[9px] font-bold tracking-widest px-1.5 py-0.5 rounded-full text-white"
          style={{ background: 'linear-gradient(135deg,#4f8ef7,#7c5cfc)' }}
        >
          v2.5.0
        </span>
      </button>

      <div className="flex-1 flex items-center justify-center gap-4">
        <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-text-2 uppercase tracking-widest">
          <Terminal size={10} />
          {t('topbar.tagline')}
        </div>
        <div className="w-px h-4 bg-border-1 hidden sm:block" />
        <div className="flex items-center gap-2 font-mono text-[10px] text-text-2">
          <span className="hidden md:block">{date}</span>
          <span className="text-text-1">{time}</span>
        </div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        {usage?.limit != null && usage.remaining != null && (
          <div className="flex items-center gap-1 text-text-3 p-1.5 text-[11px]">
              <span>{t('topbar.remainingScans')}:</span>
              <span className="text-text-1 font-mono">
                {usage.remaining}/{usage.limit}
              </span>
          </div>
        )}
        {status === 'running' && (
          <div className="flex items-center gap-1.5 text-yellow text-[11px] font-medium">
            <Loader2 size={12} className="spin" />
            {t('topbar.scanning')}
          </div>
        )}
        {status === 'completed' && (
          <div className="flex items-center gap-1.5 text-green text-[11px] font-medium">
            <CheckCircle size={12} />
            {t('topbar.complete')}
          </div>
        )}
        {status === 'failed' && (
          <div className="flex items-center gap-1.5 text-red text-[11px] font-medium">
            <XCircle size={12} />
            {t('topbar.failed')}
          </div>
        )}
        <div className="w-px h-4 bg-border-1" />
        <button
          onClick={onWatchlist}
          className="flex items-center gap-1 text-text-3 hover:text-text-1 transition-colors p-1.5 rounded-sm hover:bg-surface-2 text-[11px]"
          title="Watchlists"
          aria-label="Watchlists"
        >
          <Eye size={15} />
          <span className="hidden sm:inline">Watch</span>
        </button>
        <button
          onClick={() => {
            const idx = SUPPORTED_LOCALES.indexOf(locale);
            const next = SUPPORTED_LOCALES[(idx + 1) % SUPPORTED_LOCALES.length];
            setLocale(next);
          }}
          className="flex items-center gap-1 text-text-3 hover:text-text-1 transition-colors p-1.5 rounded-sm hover:bg-surface-2 text-[10px] font-bold uppercase tracking-wider"
          title={t('lang.label')}
          aria-label="Toggle language"
        >
          <Languages size={13} />
          <span className="hidden sm:inline">{locale.toUpperCase()}</span>
        </button>
        <button
          onClick={toggleTheme}
          className="text-text-3 hover:text-text-1 transition-colors p-1.5 rounded-sm hover:bg-surface-2"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme (Alt+T)`}
          aria-label="Toggle theme"
        >
          {mounted ? (theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />) : <Sun size={15} />}
        </button>
        <a
          href="https://addons.mozilla.org/en-US/firefox/addon/prism-osint/"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-text-3 hover:text-[#ff7139] transition-colors text-[11px]"
          title="Get the Firefox extension"
          aria-label="Get the Firefox extension"
        >
          <Puzzle size={15} />
          <span className="hidden sm:inline">Extension</span>
        </a>
        <a
          href="https://github.com/NovaCode37/Prism-platform#api"
          target="_blank"
          rel="noopener noreferrer"
          className="text-text-3 hover:text-text-1 transition-colors"
          title="API Documentation"
          aria-label="API Documentation"
        >
          <Book size={15} />
        </a>
        <a
          href="https://github.com/NovaCode37/Prism-platform/issues/new"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-text-3 hover:text-text-1 transition-colors text-[11px]"
          title="Report an issue"
          aria-label="Report an issue"
        >
          <AlertCircle size={15} />
          <span className="hidden sm:inline">Report</span>
        </a>
        <a
          href="https://github.com/NovaCode37/Prism-platform"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-text-3 hover:text-text-1 transition-colors text-[11px]"
          title="Star on GitHub"
          aria-label="Star on GitHub"
        >
          <Star size={15} />
          <span className="hidden sm:inline">Star</span>
        </a>
        <a
          href="https://github.com/NovaCode37/Prism-platform"
          target="_blank"
          rel="noopener noreferrer"
          className="text-text-3 hover:text-text-1 transition-colors"
          title="GitHub"
          aria-label="GitHub repository"
        >
          <Github size={15} />
        </a>
      </div>

    </header>
  );
}

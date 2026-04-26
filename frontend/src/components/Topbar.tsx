'use client';
import { useEffect, useState } from 'react';
import { Loader2, CheckCircle, XCircle, Github, Terminal, Sun, Moon, Menu, Languages } from 'lucide-react';
import { useTheme } from '@/lib/useTheme';
import { useTranslations } from '@/lib/i18n';
import { Logo } from './Logo';
import type { ScanStatus } from '@/lib/types';

interface Props {
  status: ScanStatus;
  onHome: () => void;
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

export function Topbar({ status, onHome, onMenuToggle }: Props) {
  const { date, time } = useDateTime();
  const { theme, toggleTheme, mounted } = useTheme();
  const { locale, setLocale, t } = useTranslations();

  return (
    <header className="h-12 flex items-center px-5 border-b border-border-1 bg-surface-1/80 backdrop-blur-sm sticky top-0 z-50">
      <button onClick={onMenuToggle} className="md:hidden text-text-3 hover:text-text-1 transition-colors p-1 -ml-1">
        <Menu size={18} />
      </button>

      <button onClick={onHome} className="flex items-center gap-2.5 cursor-pointer group shrink-0">
        <Logo size={26} />
        <span className="font-bold text-[15px] tracking-tight text-text-1 group-hover:text-white transition-colors">
          PRISM
        </span>
        <span
          className="text-[9px] font-bold tracking-widest px-1.5 py-0.5 rounded-full text-white"
          style={{ background: 'linear-gradient(135deg,#4f8ef7,#7c5cfc)' }}
        >
          v2.0
        </span>
      </button>

      <div className="flex-1 flex items-center justify-center gap-4">
        <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-text-3 uppercase tracking-widest opacity-40">
          <Terminal size={9} />
          {t('topbar.tagline')}
        </div>
        <div className="w-px h-4 bg-border-1 hidden sm:block" />
        <div className="flex items-center gap-2 font-mono text-[10px] text-text-3">
          <span className="hidden md:block opacity-50">{date}</span>
          <span className="opacity-70">{time}</span>
        </div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
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
          onClick={() => setLocale(locale === 'en' ? 'ru' : 'en')}
          className="flex items-center gap-1 text-text-3 hover:text-text-1 transition-colors p-1.5 rounded-sm hover:bg-surface-2 text-[10px] font-bold uppercase tracking-wider"
          title={t('lang.label')}
          aria-label="Toggle language"
        >
          <Languages size={13} />
          <span className="hidden sm:inline">{locale === 'en' ? 'EN' : 'RU'}</span>
        </button>
        <button
          onClick={toggleTheme}
          className="text-text-3 hover:text-text-1 transition-colors p-1.5 rounded-sm hover:bg-surface-2"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          aria-label="Toggle theme"
        >
          {mounted ? (theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />) : <Sun size={15} />}
        </button>
        <a
          href="https://github.com/NovaCode37/Prism-platform"
          target="_blank"
          rel="noopener noreferrer"
          className="text-text-3 hover:text-text-1 transition-colors"
          title="GitHub"
        >
          <Github size={15} />
        </a>
      </div>

    </header>
  );
}

'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  Search,
  Clock,
  Settings,
  FileText,
  Bell,
  Moon,
  Sun,
  Globe,
  Shield,
  Users,
  Mail,
  Phone,
  Server,
  Network,
  AlertTriangle,
  Lock,
  Key,
  BarChart3,
  Activity,
  Database,
  Cloud,
  Code,
  Eye,
  EyeOff,
  Menu,
  X,
  HelpCircle,
  Keyboard,
} from 'lucide-react';
import { useTheme } from '@/lib/useTheme';
import { useTranslations } from '@/lib/i18n';
import { Logo } from '@/components/Logo';

// Map of module names to display labels
export const MODULE_MAP: Record<string, { label: string; icon: string }> = {
  whois: { label: 'WHOIS', icon: '📋' },
  dns: { label: 'DNS', icon: '🌐' },
  rdap: { label: 'RDAP', icon: '🔍' },
  cert_transparency: { label: 'CT Logs', icon: '🔏' },
  shodan: { label: 'Shodan', icon: '🔎' },
  virustotal: { label: 'VirusTotal', icon: '🦠' },
  abuseipdb: { label: 'AbuseIPDB', icon: '🚫' },
  censys: { label: 'Censys', icon: '📡' },
  geoip: { label: 'GeoIP', icon: '🗺️' },
  gravatar: { label: 'Gravatar', icon: '👤' },
  breach: { label: 'Breaches', icon: '💥' },
  github: { label: 'GitHub', icon: '🐙' },
  darkweb: { label: 'Dark Web', icon: '🌑' },
  onion: { label: 'Onion Sites', icon: '🧅' },
  wayback: { label: 'Wayback', icon: '🕰️' },
  graph: { label: 'Graph', icon: '📊' },
  opsec: { label: 'OPSEC', icon: '🛡️' },
};

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();
  const { theme, toggleTheme, mounted } = useTheme();
  const { t } = useTranslations();
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Handle responsive collapse
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setIsCollapsed(true);
      } else {
        setIsCollapsed(false);
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Close sidebar on route change (mobile)
  useEffect(() => {
    if (window.innerWidth < 768) {
      onClose();
    }
  }, [pathname, onClose]);

  if (!mounted) return null;

  const navItems = [
    { href: '/', icon: Home, label: t('sidebar.home') },
    { href: '/scan', icon: Search, label: t('sidebar.scan') },
    { href: '/watchlist', icon: Bell, label: t('sidebar.watchlist') },
    { href: '/reports', icon: FileText, label: t('sidebar.reports') },
    { href: '/settings', icon: Settings, label: t('sidebar.settings') },
  ];

  const moduleItems = Object.entries(MODULE_MAP).map(([key, value]) => ({
    key,
    icon: value.icon,
    label: value.label,
  }));

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 z-50 h-full bg-surface-1 border-r border-border-1 transition-all duration-300
          ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
          ${isCollapsed ? 'w-16' : 'w-64'}
        `}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between h-16 px-4 border-b border-border-1">
            {!isCollapsed ? (
              <Link href="/" className="flex items-center gap-2" onClick={onClose}>
                <Logo size={32} />
                <span className="font-bold text-lg bg-gradient-to-r from-blue to-purple bg-clip-text text-transparent">
                  PRISM
                </span>
              </Link>
            ) : (
              <Link href="/" className="mx-auto" onClick={onClose}>
                <Logo size={32} />
              </Link>
            )}
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="hidden md:flex p-1 rounded hover:bg-surface-2 text-text-3"
            >
              {isCollapsed ? <Menu size={18} /> : <X size={18} />}
            </button>
            <button
              onClick={onClose}
              className="md:hidden p-1 rounded hover:bg-surface-2 text-text-3"
            >
              <X size={20} />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-2 space-y-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onClose}
                  className={`
                    flex items-center gap-3 px-3 py-2 rounded transition-colors
                    ${isActive ? 'bg-surface-2 text-text-1' : 'text-text-2 hover:bg-surface-2 hover:text-text-1'}
                    ${isCollapsed ? 'justify-center' : ''}
                  `}
                  title={isCollapsed ? item.label : undefined}
                >
                  <item.icon size={isCollapsed ? 20 : 18} />
                  {!isCollapsed && <span>{item.label}</span>}
                </Link>
              );
            })}

            {!isCollapsed && (
              <>
                <div className="h-px bg-border-1 my-2" />
                <div className="px-3 py-1 text-xs font-semibold text-text-3 uppercase tracking-wider">
                  {t('sidebar.modules')}
                </div>
              </>
            )}

            {moduleItems.map((item) => (
              <Link
                key={item.key}
                href={`/scan?module=${item.key}`}
                onClick={onClose}
                className={`
                  flex items-center gap-3 px-3 py-2 rounded transition-colors text-text-2 hover:bg-surface-2 hover:text-text-1
                  ${isCollapsed ? 'justify-center' : ''}
                `}
                title={isCollapsed ? item.label : undefined}
              >
                <span className="text-base">{item.icon}</span>
                {!isCollapsed && <span className="text-sm">{item.label}</span>}
              </Link>
            ))}
          </nav>

          {/* Footer */}
          <div className="border-t border-border-1 p-2 space-y-1">
            <button
              onClick={toggleTheme}
              className={`
                flex items-center gap-3 px-3 py-2 rounded w-full transition-colors text-text-2 hover:bg-surface-2 hover:text-text-1
                ${isCollapsed ? 'justify-center' : ''}
              `}
              title={isCollapsed ? (theme === 'dark' ? 'Light mode' : 'Dark mode') : undefined}
            >
              {theme === 'dark' ? (
                <Sun size={isCollapsed ? 20 : 18} />
              ) : (
                <Moon size={isCollapsed ? 20 : 18} />
              )}
              {!isCollapsed && <span>{theme === 'dark' ? t('sidebar.lightMode') : t('sidebar.darkMode')}</span>}
            </button>

            <button
              className={`
                flex items-center gap-3 px-3 py-2 rounded w-full transition-colors text-text-2 hover:bg-surface-2 hover:text-text-1
                ${isCollapsed ? 'justify-center' : ''}
              `}
              title={isCollapsed ? t('sidebar.shortcuts') : undefined}
            >
              <Keyboard size={isCollapsed ? 20 : 18} />
              {!isCollapsed && <span>{t('sidebar.shortcuts')}</span>}
            </button>

            <Link
              href="https://github.com/NovaCode37/Prism-platform"
              target="_blank"
              rel="noopener noreferrer"
              className={`
                flex items-center gap-3 px-3 py-2 rounded w-full transition-colors text-text-2 hover:bg-surface-2 hover:text-text-1
                ${isCollapsed ? 'justify-center' : ''}
              `}
              title={isCollapsed ? 'GitHub' : undefined}
            >
              <Code size={isCollapsed ? 20 : 18} />
              {!isCollapsed && <span>GitHub</span>}
            </Link>

            {!isCollapsed && (
              <div className="px-3 py-2 text-[10px] text-text-3 text-center">
                v2.8.0 · MIT License
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
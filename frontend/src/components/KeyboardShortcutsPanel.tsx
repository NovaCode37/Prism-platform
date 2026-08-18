'use client';
import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { useTranslations } from '@/lib/i18n';
import { SHORTCUT_ENTRIES } from '@/lib/shortcutKeys';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function KeyboardShortcutsPanel({ isOpen, onClose }: Props) {
  const { t } = useTranslations();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleMouseDown = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    window.addEventListener('mousedown', handleMouseDown);
    return () => window.removeEventListener('mousedown', handleMouseDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Group shortcuts by their group i18n key
  const grouped = SHORTCUT_ENTRIES.reduce((acc, entry) => {
    if (!acc[entry.group]) acc[entry.group] = [];
    acc[entry.group].push(entry);
    return acc;
  }, {} as Record<string, typeof SHORTCUT_ENTRIES>);

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50 backdrop-blur-sm transition-opacity" />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 pointer-events-none">
        <div 
          ref={panelRef} 
          className="card w-full max-w-md p-0 shadow-card animate-fade-in border border-border-1 bg-surface-2 rounded-card pointer-events-auto flex flex-col max-h-[90vh]"
        >
          <div className="flex items-center justify-between p-4 sm:p-5 border-b border-border-1 shrink-0">
            <h3 className="card-head text-[13px] font-semibold text-text-1 m-0">{t('shortcuts.title')}</h3>
            <button 
              onClick={onClose} 
              className="text-text-3 hover:text-text-1 transition-colors p-1 rounded-sm hover:bg-surface-3"
              aria-label={t('shortcuts.close')}
            >
              <X size={16} />
            </button>
          </div>
          
          <div className="p-4 sm:p-5 overflow-y-auto">
            <div className="flex flex-col gap-6">
              {Object.entries(grouped).map(([groupKey, entries]) => (
                <div key={groupKey}>
                  <h4 className="text-[11px] font-bold text-text-3 uppercase tracking-wider mb-3">
                    {t(groupKey)}
                  </h4>
                  <div className="flex flex-col gap-2.5">
                    {entries.map(entry => (
                      <div key={entry.i18nKey} className="flex items-center justify-between">
                        <span className="text-[13px] text-text-2">{t(entry.i18nKey)}</span>
                        <div className="flex gap-1">
                          {entry.keys.map((key, idx) => (
                            <kbd 
                              key={idx} 
                              className="bg-surface-3 border border-border-2 rounded px-1.5 py-0.5 text-[11px] font-mono text-text-1 shadow-sm min-w-[20px] text-center inline-block"
                            >
                              {key}
                            </kbd>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

'use client';
import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import en from '@/messages/en.json';
import ru from '@/messages/ru.json';

export type Locale = 'en' | 'ru';
type Messages = typeof en;

const MESSAGES: Record<Locale, Messages> = { en, ru: ru as Messages };
const STORAGE_KEY = 'prism_locale';

interface I18nContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function lookup(messages: Messages, key: string): string {
  const parts = key.split('.');
  let cur: unknown = messages;
  for (const p of parts) {
    if (cur && typeof cur === 'object' && p in (cur as Record<string, unknown>)) {
      cur = (cur as Record<string, unknown>)[p];
    } else {
      return key;
    }
  }
  return typeof cur === 'string' ? cur : key;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>('en');

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
      if (stored === 'en' || stored === 'ru') {
        setLocaleState(stored);
        return;
      }
      // Fallback: detect from browser
      if (typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('ru')) {
        setLocaleState('ru');
      }
    } catch { /* ignore */ }
  }, []);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    try { localStorage.setItem(STORAGE_KEY, l); } catch { /* ignore */ }
  }, []);

  const t = useCallback((key: string) => lookup(MESSAGES[locale], key), [locale]);

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useTranslations() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    // Fallback: return key as-is when used outside provider
    return { locale: 'en' as Locale, setLocale: () => {}, t: (key: string) => key };
  }
  return ctx;
}

export interface ShortcutEntry {
  i18nKey: string;
  keys: string[];
  group: string;
}

export const SHORTCUT_ENTRIES: ShortcutEntry[] = [
  // Navigation
  { i18nKey: 'shortcuts.focusSearch',   keys: ['/'],           group: 'shortcuts.groupNavigation' },
  { i18nKey: 'shortcuts.showShortcuts', keys: ['?'],           group: 'shortcuts.groupNavigation' },
  // Appearance
  { i18nKey: 'shortcuts.toggleTheme',   keys: ['Alt', 'T'],    group: 'shortcuts.groupAppearance' },
  // Results
  { i18nKey: 'shortcuts.prevTab',       keys: ['←'],           group: 'shortcuts.groupResults' },
  { i18nKey: 'shortcuts.nextTab',       keys: ['→'],           group: 'shortcuts.groupResults' },
];

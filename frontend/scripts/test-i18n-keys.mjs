import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';

const messagesUrl = new URL('../src/messages/', import.meta.url);

async function loadLocale(file) {
  const source = await readFile(new URL(file, messagesUrl), 'utf8');
  return JSON.parse(source);
}

const files = (await readdir(messagesUrl)).filter(f => f.endsWith('.json')).sort();
assert.ok(files.length > 0, 'no locale files found in src/messages');

// Keys that every locale must define for the results screen to render correctly.
const REQUIRED_RESULTS_KEYS = ['htmlReport', 'pdfReport', 'jsonReport', 'csvReport', 'mdReport', 'scanAnother'];

// Keys the shortcuts panel renders.
const REQUIRED_SHORTCUT_KEYS = [
  'title', 'close', 'groupNavigation', 'groupAppearance', 'groupResults',
  'focusSearch', 'showShortcuts', 'toggleTheme', 'prevTab', 'nextTab',
];

// Single words legitimately collide across languages - "Navigation" is the same
// in English, German and French - so only a block that matches English on every
// key counts as one that was added and never translated.
const SHORTCUT_SENTENCE_KEYS = ['focusSearch', 'showShortcuts', 'toggleTheme', 'prevTab', 'nextTab'];

const english = await loadLocale('en.json');

for (const file of files) {
  const messages = await loadLocale(file);
  const results = messages.results ?? {};
  for (const key of REQUIRED_RESULTS_KEYS) {
    const value = results[key];
    assert.equal(typeof value, 'string', `${file}: results.${key} must be a string`);
    assert.ok(value.trim().length > 0, `${file}: results.${key} must not be empty`);
  }

  const shortcuts = messages.shortcuts ?? {};
  for (const key of REQUIRED_SHORTCUT_KEYS) {
    const value = shortcuts[key];
    assert.equal(typeof value, 'string', `${file}: shortcuts.${key} must be a string`);
    assert.ok(value.trim().length > 0, `${file}: shortcuts.${key} must not be empty`);
  }

  if (file !== 'en.json') {
    const untouched = SHORTCUT_SENTENCE_KEYS.every(
      key => shortcuts[key].trim() === english.shortcuts[key].trim(),
    );
    assert.ok(!untouched, `${file}: the shortcuts block is still the English text`);
  }
}

console.log(`i18n key tests passed (${files.length} locales)`);

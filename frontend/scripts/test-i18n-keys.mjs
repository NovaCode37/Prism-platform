import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

// The directory is overridable so the check can be run against a scratch copy of
// the locales; CI runs it with no argument, against src/messages.
const messagesUrl = process.argv[2]
  ? pathToFileURL(`${process.argv[2].replace(/\/?$/, '/')}`)
  : new URL('../src/messages/', import.meta.url);

async function loadLocale(file) {
  const source = await readFile(new URL(file, messagesUrl), 'utf8');
  return JSON.parse(source);
}

const files = (await readdir(messagesUrl)).filter(f => f.endsWith('.json')).sort();
assert.ok(files.includes('en.json'), 'no en.json found in src/messages');

// Differences from en.json that are deliberate. Every entry needs a reason, so
// the list explains itself instead of silently widening what the check skips:
//
//   'tr.json': { 'results.someKey': 'why Turkish does not need this key' },
//
// An entry that no longer matches a real difference fails the check too, so the
// list cannot outlive the gap it was added for.
const ALLOWED_DIFFERENCES = {};

// Single words legitimately collide across languages - "Navigation" is the same
// in English, German and French - so only a block that matches English on every
// key counts as one that was added and never translated.
const SHORTCUT_SENTENCE_KEYS = ['focusSearch', 'showShortcuts', 'toggleTheme', 'prevTab', 'nextTab'];

// Flatten nested objects into dotted keys. Arrays are leaves: they are rendered
// as a list, so their length is compared rather than their contents.
function flatten(value, prefix = '', out = new Map()) {
  for (const [key, child] of Object.entries(value)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (child !== null && typeof child === 'object' && !Array.isArray(child)) {
      flatten(child, path, out);
    } else {
      out.set(path, child);
    }
  }
  return out;
}

function describe(value) {
  if (Array.isArray(value)) return `array of ${value.length}`;
  return value === null ? 'null' : typeof value;
}

function compareLocale(english, messages) {
  const missing = [];
  const extra = [];
  const mismatched = [];
  const empty = [];

  for (const [key, expected] of english) {
    if (!messages.has(key)) {
      missing.push(key);
      continue;
    }
    const actual = messages.get(key);
    if (describe(actual) !== describe(expected)) {
      mismatched.push(`${key} (${describe(actual)}, en.json has ${describe(expected)})`);
    } else if (typeof actual === 'string' && actual.trim().length === 0) {
      empty.push(key);
    }
  }
  for (const key of messages.keys()) {
    if (!english.has(key)) extra.push(key);
  }
  return { missing, extra, mismatched, empty };
}

// en.json is the reference every other locale is compared against, so a key
// dropped from it would vanish from the comparison too. These are the keys the
// results screen and the shortcuts panel cannot render without.
const REQUIRED_ENGLISH_KEYS = [
  ...['htmlReport', 'pdfReport', 'jsonReport', 'csvReport', 'mdReport', 'scanAnother'].map(k => `results.${k}`),
  ...['title', 'close', 'groupNavigation', 'groupAppearance', 'groupResults', ...SHORTCUT_SENTENCE_KEYS]
    .map(k => `shortcuts.${k}`),
];

const englishMessages = await loadLocale('en.json');
const english = flatten(englishMessages);
const problems = [];

const droppedFromEnglish = REQUIRED_ENGLISH_KEYS.filter(key => typeof english.get(key) !== 'string');
if (droppedFromEnglish.length > 0) {
  problems.push(`en.json\n  required keys missing (${droppedFromEnglish.length}): ${droppedFromEnglish.join(', ')}`);
}

for (const file of files) {
  const raw = await loadLocale(file);
  const allowed = ALLOWED_DIFFERENCES[file] ?? {};
  const { missing, extra, mismatched, empty } = compareLocale(english, flatten(raw));
  const lines = [];

  const report = (label, keys) => {
    const unexplained = keys.filter(entry => !(entry.split(' ')[0] in allowed));
    if (unexplained.length > 0) {
      lines.push(`  ${label} (${unexplained.length}): ${unexplained.join(', ')}`);
    }
  };
  report('missing', missing);
  report('extra', extra);
  report('different type or length', mismatched);
  report('empty string', empty);

  const differing = new Set([...missing, ...extra, ...mismatched, ...empty].map(entry => entry.split(' ')[0]));
  for (const [key, reason] of Object.entries(allowed)) {
    if (typeof reason !== 'string' || reason.trim().length === 0) {
      lines.push(`  allowlist entry ${key} has no reason`);
    } else if (!differing.has(key)) {
      lines.push(`  stale allowlist entry ${key}: it matches en.json now, remove it`);
    }
  }

  if (file !== 'en.json') {
    const shortcuts = raw.shortcuts ?? {};
    const untouched = SHORTCUT_SENTENCE_KEYS.every(
      key => typeof shortcuts[key] === 'string'
        && shortcuts[key].trim() === englishMessages.shortcuts?.[key]?.trim(),
    );
    if (untouched) lines.push('  the shortcuts block is still the English text');
  }

  if (lines.length > 0) problems.push(`${file}\n${lines.join('\n')}`);
}

for (const file of Object.keys(ALLOWED_DIFFERENCES)) {
  if (!files.includes(file)) problems.push(`allowlist names ${file}, which does not exist`);
}

assert.equal(
  problems.length,
  0,
  `locales differ from en.json:\n\n${problems.join('\n\n')}\n`,
);

console.log(`i18n key tests passed (${files.length} locales, ${english.size} keys each)`);

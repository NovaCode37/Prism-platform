import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';

const sourcePath = path.resolve('src/lib/i18n-lookup.ts');
const compiled = ts.transpileModule(
  await readFile(sourcePath, 'utf8'),
  {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      isolatedModules: true,
    },
    fileName: sourcePath,
  },
).outputText;

const tmp = await mkdtemp(path.join(tmpdir(), 'prism-i18n-lookup-test-'));

try {
  const modulePath = path.join(tmp, 'i18n-lookup.mjs');
  await writeFile(modulePath, compiled, 'utf8');
  const { makeLookup } = await import(pathToFileURL(modulePath).href);

  const en = {
    sidebar: { modules: { whois: 'WHOIS' } },
    results: { tabs: { findings: 'Findings' } },
  };
  const tr = { sidebar: { modules: { whois: 'WHOIS' } } };

  const lookup = makeLookup(en);

  // Found in the requested locale
  assert.equal(lookup(tr, 'sidebar.modules.whois'), 'WHOIS');

  // Missing in the locale, present in English -> falls back to English
  assert.equal(lookup(tr, 'results.tabs.findings'), 'Findings');

  // Missing everywhere -> returns the raw key, does not recurse
  assert.equal(lookup(tr, 'sidebar.modules.rdap'), 'sidebar.modules.rdap');
  assert.equal(lookup(en, 'sidebar.modules.rdap'), 'sidebar.modules.rdap');

  // Namespace request (resolves to an object, not a string) -> raw key
  assert.equal(lookup(tr, 'sidebar'), 'sidebar');
  assert.equal(lookup(en, 'sidebar'), 'sidebar');

  // Empty string value is preserved, not treated as a miss
  const withEmpty = { a: { b: '' } };
  assert.equal(lookup(withEmpty, 'a.b'), '');

  console.log('i18n lookup tests passed');
} finally {
  await rm(tmp, { recursive: true, force: true });
}
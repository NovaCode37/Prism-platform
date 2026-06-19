import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

async function loadTsModule(path) {
  const sourceUrl = new URL(path, import.meta.url);
  const source = await readFile(sourceUrl, 'utf8');
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  return import(`data:text/javascript;charset=utf-8,${encodeURIComponent(output)}`);
}

const utils = await loadTsModule('../src/lib/url-utils.ts');
const config = await loadTsModule('../src/lib/prism-config.ts');

assert.equal(utils.normalizeBasePath(''), '');
assert.equal(utils.normalizeBasePath('/'), '');
assert.equal(utils.normalizeBasePath('prism'), '/prism');
assert.equal(utils.normalizeBasePath('/prism/'), '/prism');

assert.equal(utils.buildApiUrl('/api/scan'), '/api/scan');
assert.equal(utils.buildApiUrl('/api/scan', '', '/prism'), '/prism/api/scan');
assert.equal(
  utils.buildApiUrl('/api/scan', 'https://api.example.com/prism/', '/ignored'),
  'https://api.example.com/prism/api/scan',
);

assert.equal(
  utils.buildWsUrl('scan-1', {
    basePath: '/prism',
    currentOrigin: 'https://app.example.com',
  }),
  'wss://app.example.com/prism/ws/scan-1',
);

assert.equal(
  utils.buildWsUrl('scan-1', {
    apiBase: 'http://localhost:8080',
    apiKey: 'secret',
    currentOrigin: 'https://app.example.com',
  }),
  'ws://localhost:8080/ws/scan-1?api_key=secret',
);

assert.equal(config.getPrismApiUrl({ apiUrl: '' }, 'http://localhost:8080'), '');
assert.equal(config.getPrismApiUrl({ apiUrl: 'https://api.example.com' }, ''), 'https://api.example.com');
assert.equal(config.getPrismApiKey({ apiKey: 'runtime-key' }, 'build-key'), 'runtime-key');
assert.equal(config.getPrismBasePath({ basePath: '/prism' }, ''), '/prism');
assert.equal(config.getPrismDemoMode({ demoMode: true }, ''), true);
assert.equal(config.getPrismDemoMode({ demoMode: false }, 'true'), false);
assert.equal(config.getPrismDemoMode({}, 'yes'), true);

console.log('api url tests passed');

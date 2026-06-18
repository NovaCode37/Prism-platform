import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const sourceUrl = new URL('../src/lib/url-utils.ts', import.meta.url);
const source = await readFile(sourceUrl, 'utf8');
const output = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;

const utils = await import(`data:text/javascript;charset=utf-8,${encodeURIComponent(output)}`);

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

console.log('api url tests passed');

import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';

const sourcePath = path.resolve('src/lib/scan-target.ts');
const compiled = ts.transpileModule(
  await (await import('node:fs/promises')).readFile(sourcePath, 'utf8'),
  {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      isolatedModules: true,
    },
    fileName: sourcePath,
  },
).outputText;

const tmp = await mkdtemp(path.join(tmpdir(), 'prism-scan-target-test-'));
try {
  const modulePath = path.join(tmp, 'scan-target.mjs');
  await writeFile(modulePath, compiled, 'utf8');
  const { detectScanType, normalizeScanTarget } = await import(pathToFileURL(modulePath).href);

  assert.equal(normalizeScanTarget(' Example.COM '), 'example.com');
  assert.equal(normalizeScanTarget('https://Example.COM/'), 'example.com');
  assert.equal(normalizeScanTarget('HTTP://Example.COM//'), 'example.com');
  assert.equal(normalizeScanTarget(' User@Example.COM '), 'user@example.com');
  assert.equal(normalizeScanTarget('+1 555 000 0000'), '+1 555 000 0000');
  assert.equal(normalizeScanTarget('@MixedCaseUser'), '@MixedCaseUser');

  assert.equal(detectScanType(' https://Example.COM/ '), 'domain');
  assert.equal(detectScanType(' USER@Example.COM '), 'email');
  assert.equal(detectScanType('+1 555 000 0000'), 'phone');
  assert.equal(detectScanType('@MixedCaseUser'), 'username');

  console.log('scan target normalization tests passed');
} finally {
  await rm(tmp, { recursive: true, force: true });
}

import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';

const sourcePath = path.resolve('src/lib/encoder-utils.ts');
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

const tmp = await mkdtemp(path.join(tmpdir(), 'prism-encoder-test-'));

try {
  const modulePath = path.join(tmp, 'encoder-utils.mjs');
  await writeFile(modulePath, compiled, 'utf8');

  const { runEncoder } = await import(pathToFileURL(modulePath).href);

  assert.equal(runEncoder('', 'base64', 'encode'), '');
  assert.equal(runEncoder('', 'base64', 'decode'), '');
  assert.equal(runEncoder('', 'url', 'encode'), '');
  assert.equal(runEncoder('', 'url', 'decode'), '');

  assert.equal(runEncoder('hello', 'base64', 'encode'), 'aGVsbG8=');
  assert.equal(runEncoder('aGVsbG8=', 'base64', 'decode'), 'hello');

  const base64Cases = [
    'hello world',
    'café 🚀',
    'symbols + % / = ? &',
  ];

  for (const value of base64Cases) {
    const encoded = runEncoder(value, 'base64', 'encode');
    const decoded = runEncoder(encoded, 'base64', 'decode');
    assert.equal(decoded, value, `Base64 round trip failed for: ${value}`);
  }

  assert.throws(
    () => runEncoder('not-valid-base64%%%', 'base64', 'decode'),
    undefined,
    'Invalid Base64 input should throw',
  );

  const urlCases = [
    'hello world',
    'café 🚀',
    'a+b%c',
    'email=test@example.com&redirect=/a b',
  ];

  for (const value of urlCases) {
    const encoded = runEncoder(value, 'url', 'encode');
    const decoded = runEncoder(encoded, 'url', 'decode');
    assert.equal(decoded, value, `URL round trip failed for: ${value}`);
  }

  assert.equal(runEncoder('hello world', 'url', 'encode'), 'hello%20world');
  assert.equal(runEncoder('a+b%c', 'url', 'encode'), 'a%2Bb%25c');
  assert.equal(runEncoder('café', 'url', 'encode'), 'caf%C3%A9');
  assert.equal(runEncoder('a+b', 'url', 'decode'), 'a+b');

  assert.throws(
    () => runEncoder('%E0%A4%A', 'url', 'decode'),
    undefined,
    'Malformed URL encoding should throw',
  );

  console.log('encoder tests passed');
} finally {
  await rm(tmp, { recursive: true, force: true });
}

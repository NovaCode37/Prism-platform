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

  assert.equal(
    normalizeScanTarget('https://example.com:8443/path/to/resource'),
    'example.com',
    'URL with path and port should return host only'
  );
  assert.equal(
    normalizeScanTarget('http://sub.domain.com:8080/api/v1'),
    'sub.domain.com',
    'Subdomain URL with port should return host only'
  );
  assert.equal(
    normalizeScanTarget('HTTPS://EXAMPLE.COM:443/secure'),
    'example.com',
    'Uppercase URL with port should be lowercased'
  );

  assert.equal(
    normalizeScanTarget('mailto:user@example.com'),
    'mailto:user@example.com',
    'mailto: prefix should be preserved'
  );
  assert.equal(
    normalizeScanTarget('MAILTO:USER@EXAMPLE.COM'),
    'mailto:user@example.com',
    'mailto: prefix should be lowercased and email lowercased'
  );

  assert.equal(
    normalizeScanTarget('@username'),
    '@username',
    'Username with @ should be preserved'
  );
  assert.equal(
    normalizeScanTarget(' @username '),
    '@username',
    'Username with @ and whitespace should be trimmed'
  );

  assert.equal(
    normalizeScanTarget('2001:0db8:85a3:0000:0000:8a2e:0370:7334'),
    '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
    'Full IPv6 address should be preserved'
  );
  assert.equal(
    normalizeScanTarget('::1'),
    '::1',
    'IPv6 loopback should be preserved'
  );
  assert.equal(
    normalizeScanTarget('fe80::1'),
    'fe80::1',
    'IPv6 link-local should be preserved'
  );

  assert.equal(
    normalizeScanTarget('  example.com  '),
    'example.com',
    'Whitespace should be trimmed'
  );
  assert.equal(
    normalizeScanTarget('example.com.'),
    'example.com',
    'Trailing dot should be removed'
  );
  assert.equal(
    normalizeScanTarget('  example.com.  '),
    'example.com',
    'Whitespace + trailing dot should be trimmed and dot removed'
  );
  assert.equal(
    normalizeScanTarget('sub.example.com.'),
    'sub.example.com',
    'Subdomain with trailing dot should be trimmed'
  );

  assert.equal(
    normalizeScanTarget('EXAMPLE.COM'),
    'example.com',
    'Uppercase domain should be lowercased'
  );
  assert.equal(
    normalizeScanTarget('Sub.Example.COM'),
    'sub.example.com',
    'Mixed-case domain should be lowercased'
  );

  assert.equal(
    normalizeScanTarget('  user@example.com  '),
    'user@example.com',
    'Email with whitespace should be trimmed and lowercased'
  );

  assert.equal(detectScanType(' https://Example.COM/ '), 'domain');
  assert.equal(detectScanType(' USER@Example.COM '), 'email');
  assert.equal(detectScanType('+1 555 000 0000'), 'phone');
  assert.equal(detectScanType('@MixedCaseUser'), 'username');

  assert.equal(
    detectScanType('https://example.com:8443/path'),
    'domain',
    'URL with path and port should detect as domain'
  );
  assert.equal(
    detectScanType('http://sub.domain.com:8080'),
    'domain',
    'Subdomain URL with port should detect as domain'
  );

  assert.equal(
    detectScanType('mailto:user@example.com'),
    'email',
    'mailto: should detect as email'
  );
  assert.equal(
    detectScanType('MAILTO:USER@EXAMPLE.COM'),
    'email',
    'mailto: uppercase should detect as email'
  );

  assert.equal(
    detectScanType('@username'),
    'username',
    'Username with @ should detect as username'
  );
  assert.equal(
    detectScanType(' @username '),
    'username',
    'Username with @ and whitespace should detect as username'
  );

  assert.equal(
    detectScanType('2001:0db8:85a3:0000:0000:8a2e:0370:7334'),
    'ip',
    'Full IPv6 address should detect as ip'
  );
  assert.equal(
    detectScanType('::1'),
    'ip',
    'IPv6 loopback should detect as ip'
  );
  assert.equal(
    detectScanType('fe80::1'),
    'ip',
    'IPv6 link-local should detect as ip'
  );
  assert.equal(
    detectScanType('2001:db8::1'),
    'ip',
    'IPv6 shorthand should detect as ip'
  );

  assert.equal(
    detectScanType('  user@example.com  '),
    'email',
    'Email with whitespace should detect as email'
  );

  assert.equal(
    detectScanType('example.com.'),
    'domain',
    'Domain with trailing dot should detect as domain'
  );

  assert.equal(
    detectScanType('EXAMPLE.COM'),
    'domain',
    'Uppercase domain should detect as domain'
  );

  console.log('scan target normalization tests passed');
} finally {
  await rm(tmp, { recursive: true, force: true });
}
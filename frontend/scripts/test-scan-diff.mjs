import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';

const sourcePath = path.resolve('src/lib/scan-diff.ts');
const compiled = ts.transpileModule(await readFile(sourcePath, 'utf8'), {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
    isolatedModules: true,
  },
  fileName: sourcePath,
}).outputText;

const tmp = await mkdtemp(path.join(tmpdir(), 'prism-scan-diff-test-'));

try {
  const modulePath = path.join(tmp, 'scan-diff.mjs');
  await writeFile(modulePath, compiled, 'utf8');
  const { VOLATILE_KEYS, diffResults, flattenResults } = await import(pathToFileURL(modulePath).href);

  const compare = (a, b) => diffResults(flattenResults(a), flattenResults(b)).filter(r => r.status !== 'same');

  const account = (site, responseTime, status = 'found') => ({
    site,
    url: `https://${site.toLowerCase()}.com/johndoe`,
    status,
    response_time: responseTime,
  });

  // Two username scans that found the same accounts, only timings and timestamps differ.
  const usernameA = {
    blackbird: [account('GitHub', 0.41), account('Reddit', 1.2)],
    maigret: {
      username: 'johndoe',
      timestamp: '2026-10-01T10:00:00',
      accounts: [{ site: 'GitHub', url: 'https://github.com/johndoe', status: 'found' }],
      total_found: 1,
      status: 'ok',
      status_reason: 'maigret finished in 41s',
    },
  };
  const usernameB = {
    blackbird: [account('Reddit', 0.9), account('GitHub', 0.77)],
    maigret: {
      status_reason: 'maigret finished in 38s',
      status: 'ok',
      total_found: 1,
      accounts: [{ url: 'https://github.com/johndoe', site: 'GitHub', status: 'found' }],
      timestamp: '2026-10-08T17:30:00',
      username: 'johndoe',
    },
  };
  assert.deepEqual(compare(usernameA, usernameB), [], 'same accounts with different timings should show no changes');

  const withAddedAccount = { ...usernameB, blackbird: [...usernameB.blackbird, account('Mastodon', 2.5)] };
  const added = compare(usernameA, withAddedAccount);
  assert.equal(added.length, 1, 'one new account should be exactly one row');
  assert.equal(added[0].status, 'added');
  assert.equal(added[0].key, 'blackbird[Mastodon https://mastodon.com/johndoe]');
  assert.ok(!added[0].valB.includes('response_time'), 'row value should not carry the timing');

  const removed = compare(withAddedAccount, usernameA);
  assert.deepEqual(removed.map(r => [r.key, r.status]), [['blackbird[Mastodon https://mastodon.com/johndoe]', 'removed']]);

  const lostAccount = { ...usernameB, blackbird: [account('GitHub', 0.5), account('Reddit', 0.5, 'not_found')] };
  const changed = compare(usernameA, lostAccount);
  assert.deepEqual(changed.map(r => [r.key, r.status]), [['blackbird[Reddit https://reddit.com/johndoe]', 'changed']]);

  const maigretAdded = {
    ...usernameB,
    maigret: {
      ...usernameB.maigret,
      accounts: [...usernameB.maigret.accounts, { site: 'Keybase', url: 'https://keybase.io/johndoe', status: 'found' }],
      total_found: 2,
    },
  };
  assert.deepEqual(
    compare(usernameA, maigretAdded).map(r => [r.key, r.status]),
    [
      ['maigret.accounts[Keybase https://keybase.io/johndoe]', 'added'],
      ['maigret.total_found', 'changed'],
    ],
  );

  // Volatile fields nested inside a module are ignored too, real changes next to them are not.
  const nestedA = { whois: { registrar: 'Gandi', raw: { checked: { elapsed: 0.3, ok: true } } } };
  const nestedB = { whois: { registrar: 'Gandi', raw: { checked: { ok: true, elapsed: 1.9 } } } };
  assert.deepEqual(compare(nestedA, nestedB), []);
  const nestedChanged = { whois: { registrar: 'Namecheap', raw: { checked: { elapsed: 0.1, ok: true } } } };
  assert.deepEqual(compare(nestedA, nestedChanged).map(r => r.key), ['whois.registrar']);

  // Lists without an identity are still compared as a whole.
  assert.deepEqual(
    compare({ dns: { a: ['1.1.1.1'] } }, { dns: { a: ['1.1.1.1', '8.8.8.8'] } }).map(r => [r.key, r.status]),
    [['dns.a', 'changed']],
  );

  // A blackbird failure object is compared as fields, not accounts.
  assert.deepEqual(
    compare({ blackbird: { error: 'timeout' } }, { blackbird: usernameA.blackbird }).map(r => r.status).sort(),
    ['added', 'added', 'removed'],
  );

  assert.deepEqual(
    Object.keys(flattenResults({ report_path: '/tmp/r.html', map_data: { x: 1 }, graph: { nodes: [] } })),
    [],
    'report, map and graph data are not compared',
  );

  // The list must match the one the backend watchlist uses for its fingerprints.
  const watchlist = await readFile(path.resolve('../web/watchlist.py'), 'utf8');
  const pyBlock = watchlist.match(/_VOLATILE_KEYS\s*=\s*\{([\s\S]*?)\}/);
  assert.ok(pyBlock, '_VOLATILE_KEYS not found in web/watchlist.py');
  const pyKeys = [...pyBlock[1].matchAll(/"([^"]+)"/g)].map(m => m[1]).sort();
  assert.deepEqual([...VOLATILE_KEYS].sort(), pyKeys, 'VOLATILE_KEYS in src/lib/scan-diff.ts and web/watchlist.py differ');

  console.log('scan diff tests passed');
} finally {
  await rm(tmp, { recursive: true, force: true });
}

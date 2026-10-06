import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const frontend = join(here, '..');
const repo = join(frontend, '..');

const failures = [];

function read(path) {
  return readFileSync(path, 'utf8');
}

function block(label, text, pattern) {
  const match = text.match(pattern);
  if (!match) {
    failures.push(`could not find ${label}`);
    return '';
  }
  return match[1];
}

function names(text, pattern) {
  return new Set([...text.matchAll(pattern)].map(m => m[1]));
}

const python = read(join(repo, 'modules', 'opsec_score.py'));
const riskLevels = block('RISK_LEVELS in modules/opsec_score.py', python, /^RISK_LEVELS\s*=\s*\{([\s\S]*?)^\}/m);
// RISK_LEVELS only holds the score bands; NOT_ASSESSED is a literal returned when nothing was scored.
const backend = new Set([
  ...names(riskLevels, /\(\s*"([A-Z_]+)"/g),
  ...names(python, /"risk_level"\s*:\s*"([A-Z_]+)"/g),
]);

const typesFile = 'src/lib/types.ts';
const union = block(`the risk_level union in ${typesFile}`, read(join(frontend, typesFile)), /risk_level\s*:\s*([^;]+);/);
const typed = names(union, /'([A-Z_]+)'/g);

const resultsFile = 'src/components/views/ScanResults.tsx';
const colorMap = block(`RISK_COLOR in ${resultsFile}`, read(join(frontend, resultsFile)), /const RISK_COLOR\b[^=]*=\s*\{([^}]*)\}/);
const colored = names(colorMap, /([A-Z_]+)\s*:/g);

if (!failures.length) {
  const sources = [
    ['modules/opsec_score.py', backend],
    [`${typesFile} risk_level`, typed],
    [`${resultsFile} RISK_COLOR`, colored],
  ];
  const all = new Set(sources.flatMap(([, set]) => [...set]));
  for (const [label, set] of sources) {
    if (!set.size) {
      failures.push(`${label} has no risk levels; the pattern this check uses no longer matches`);
      continue;
    }
    const missing = [...all].filter(level => !set.has(level));
    if (missing.length) {
      failures.push(`${label} is missing ${missing.join(', ')}`);
    }
  }
}

if (failures.length) {
  for (const f of failures) console.error(`  ${f}`);
  process.exit(1);
}

console.log(`risk level tests passed (${[...backend].join(', ')})`);

#!/usr/bin/env node
/**
 * Lighthouse on the lite (2D) Experience, using Playwright's Chromium as CHROME_PATH.
 * Runs `npx -y lighthouse@12.2.1` (fetched on first use) → merges `lighthouse_lite` into
 * majlis/results/frontend_perf.json. Env: LH_PORT (4178), LH_QUERY (?lite=1), NO_BUILD=1, PERF_OUT.
 */
import { chromium } from '@playwright/test';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { buildIfStale, mergePerf, PERF_JSON, startPreview } from './lib.mjs';

const PORT = Number(process.env.LH_PORT || 4178);
const QUERY = process.env.LH_QUERY || '?lite=1';

async function main() {
  buildIfStale();
  const server = await startPreview(PORT);
  const out = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'majlis-lh-')), 'lh.json');
  try {
    const chromePath = process.env.CHROME_PATH || chromium.executablePath();
    const r = spawnSync(
      'npx',
      ['-y', 'lighthouse@12.2.1', server.url + QUERY, '--quiet', '--output=json', `--output-path=${out}`,
        '--only-categories=performance,accessibility,best-practices', '--chrome-flags=--headless=new --no-first-run', '--preset=desktop'],
      { stdio: 'inherit', env: { ...process.env, CHROME_PATH: chromePath } },
    );
    if (r.status !== 0 || !fs.existsSync(out)) throw new Error('lighthouse failed');
    const lh = JSON.parse(fs.readFileSync(out, 'utf8'));
    const score = (k) => (lh.categories[k]?.score == null ? null : Math.round(lh.categories[k].score * 100));
    const audits = lh.audits || {};
    const result = {
      timestamp: new Date().toISOString(),
      tool: `lighthouse ${lh.lighthouseVersion} (desktop preset)`,
      browser: lh.environment?.hostUserAgent ?? 'chromium',
      url_query: QUERY,
      performance: score('performance'),
      accessibility: score('accessibility'),
      best_practices: score('best-practices'),
      fcp_ms: Math.round(audits['first-contentful-paint']?.numericValue ?? 0),
      lcp_ms: Math.round(audits['largest-contentful-paint']?.numericValue ?? 0),
      tbt_ms: Math.round(audits['total-blocking-time']?.numericValue ?? 0),
      cls: +(audits['cumulative-layout-shift']?.numericValue ?? 0).toFixed(3),
      targets: { performance_min: 85, accessibility_min: 95 },
      failing_a11y_audits: Object.values(audits)
        .filter((a) => a.score === 0 && lh.categories.accessibility.auditRefs.some((ref) => ref.id === a.id && ref.weight > 0))
        .map((a) => a.id),
      how_measured: `vite preview of web/dist on localhost, Playwright Chromium ${chromePath.includes('ms-playwright') ? '(bundled)' : ''}, headless=new`,
    };
    console.log(`lighthouse lite: perf ${result.performance} · a11y ${result.accessibility} · best ${result.best_practices}${result.failing_a11y_audits.length ? ' · failing a11y: ' + result.failing_a11y_audits.join(', ') : ''}`);
    mergePerf({ lighthouse_lite: result });
    console.log(`written → ${PERF_JSON}`);
  } finally {
    server.stop();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

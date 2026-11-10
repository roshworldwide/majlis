#!/usr/bin/env node
/**
 * Soak: loop Story mode (speed 4) for SOAK_MIN minutes (default 10), restarting at the end,
 * sampling the JS heap (after a forced GC) every 30 s and counting console errors.
 * Writes the `soak` key into majlis/results/frontend_perf.json.
 * Env: SOAK_MIN (10), SOAK_QUERY (?force3d=1&speed=4), SOAK_HEADLESS=1, SOAK_PORT (4177), NO_BUILD=1, PERF_OUT.
 */
import { chromium } from '@playwright/test';
import os from 'node:os';
import { buildIfStale, CHROMIUM_ARGS, mergePerf, PERF_JSON, startPreview, waitReady } from './lib.mjs';

const MIN = Number(process.env.SOAK_MIN || 10);
const QUERY = process.env.SOAK_QUERY || '?force3d=1&speed=4';
const PORT = Number(process.env.SOAK_PORT || 4177);
const HEADLESS = process.env.SOAK_HEADLESS === '1';
const TOTAL_S = MIN * 60;
const SAMPLE_S = Math.min(30, Math.max(2, TOTAL_S / 6));

async function heap(page) {
  return page.evaluate(() => {
    if (window.gc) window.gc();
    return performance.memory ? performance.memory.usedJSHeapSize : null;
  });
}

async function main() {
  buildIfStale();
  const server = await startPreview(PORT);
  const browser = await chromium.launch({
    headless: HEADLESS,
    args: [...CHROMIUM_ARGS, '--enable-precise-memory-info', '--js-flags=--expose-gc'],
  });
  const errors = [];
  let loops = 0;
  const samples = [];
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(server.url + QUERY);
    await waitReady(page);
    await page.waitForTimeout(2000);
    const t0 = Date.now();
    let nextSample = 0;
    while ((Date.now() - t0) / 1000 < TOTAL_S) {
      const el = (Date.now() - t0) / 1000;
      const ended = await page.evaluate(() => window.__majlis.ended);
      if (ended) {
        loops++;
        await page.evaluate(() => {
          window.__majlis.seek(0);
          window.__majlis.play();
        });
      }
      if (el >= nextSample) {
        const h = await heap(page);
        samples.push([+el.toFixed(1), h === null ? null : +(h / 1048576).toFixed(2)]);
        nextSample += SAMPLE_S;
      }
      await page.waitForTimeout(500);
    }
    const hEnd = await heap(page);
    samples.push([+((Date.now() - t0) / 1000).toFixed(1), hEnd === null ? null : +(hEnd / 1048576).toFixed(2)]);
    const renderer = await page.evaluate(() => `${window.__majlis.renderer} (${window.__majlis.rendererReason}), quality ${window.__majlis.quality}`);
    await context.close();
    const vals = samples.map((x) => x[1]).filter((x) => x !== null);
    // baseline after the first loop has warmed every lazy path (galaxy, shaders, finale)
    const warmIdx = Math.min(samples.length - 1, Math.max(1, Math.floor(samples.length / 4)));
    const base = samples[warmIdx][1];
    const end = vals[vals.length - 1];
    const drift = base ? ((end - base) / base) * 100 : null;
    const result = {
      timestamp: new Date().toISOString(),
      browser: `chromium ${browser.version()}`,
      mode: QUERY,
      renderer,
      duration_min: MIN,
      loops_completed: loops,
      heap_samples_mb: samples,
      heap_first_mb: vals[0],
      heap_baseline_mb: base,
      heap_end_mb: end,
      heap_min_mb: Math.min(...vals),
      heap_max_mb: Math.max(...vals),
      drift_pct_vs_baseline: drift === null ? null : +drift.toFixed(2),
      console_errors: errors.length,
      first_errors: errors.slice(0, 5),
      pass: errors.length === 0 && drift !== null && Math.abs(drift) <= 10,
      how_measured: `${HEADLESS ? 'headless' : 'headed'} Playwright Chromium on ${os.cpus()[0]?.model ?? os.arch()}; performance.memory.usedJSHeapSize after window.gc() every ${SAMPLE_S}s; baseline = sample #${warmIdx} (after warm-up).`,
    };
    console.log(`soak ${MIN} min: loops ${loops}, heap ${result.heap_baseline_mb} → ${end} MB (${result.drift_pct_vs_baseline}%), errors ${errors.length}, pass ${result.pass}`);
    mergePerf({ [process.env.SOAK_KEY || 'soak']: result });
    console.log(`written → ${PERF_JSON}`);
  } finally {
    await browser.close();
    server.stop();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

#!/usr/bin/env node
/**
 * FPS probe: rAF sampling over 20 s of Story mode, 3D and 2D, in HEADED Chromium (real GPU)
 * on this machine, plus the gzip bundle size → merged into majlis/results/frontend_perf.json.
 * Env: PERF_SECONDS (20), PERF_DPR (2 = Retina), PERF_CHANNEL (e.g. chrome), PERF_HEADLESS=1,
 *      PERF_PORT (4175), PERF_OUT (alternate JSON path), NO_BUILD=1, PERF_START_ACT (2),
 *      PERF_PER_ACT=0 to skip the per-act 3D probe, PERF_ACT_SECONDS (8).
 */
import { chromium } from '@playwright/test';
import os from 'node:os';
import { buildIfStale, bundleStats, CHROMIUM_ARGS, gpuString, mergePerf, PERF_JSON, startPreview, stats, waitReady } from './lib.mjs';

const SECONDS = Number(process.env.PERF_SECONDS || 20);
const DPR = Number(process.env.PERF_DPR || 2);
const PORT = Number(process.env.PERF_PORT || 4175);
const HEADLESS = process.env.PERF_HEADLESS === '1';
const START_ACT = process.env.PERF_START_ACT || '2';

async function sample(page, seconds) {
  return page.evaluate(
    (ms) =>
      new Promise((resolve) => {
        const ts = [];
        const m = window.__majlis;
        const s0 = m.s;
        const a0 = m.act;
        let t0 = -1;
        const f = (t) => {
          if (t0 < 0) t0 = t;
          ts.push(t);
          if (t - t0 < ms) requestAnimationFrame(f);
          else resolve({ ts, s0, s1: m.s, a0, a1: m.act, renderer: m.renderer, quality: m.quality, reason: m.rendererReason });
        };
        requestAnimationFrame(f);
      }),
    seconds * 1000,
  );
}

async function pass(browser, base, label, query) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: DPR });
  const page = await context.newPage();
  const errors = [];
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(base + query);
  await waitReady(page);
  await page.waitForTimeout(3000); // warm-up: lazy chunks, shader compile, quality probe
  const gpu = await gpuString(page);
  const r = await sample(page, SECONDS);
  const deltas = [];
  for (let i = 1; i < r.ts.length; i++) deltas.push(r.ts[i] - r.ts[i - 1]);
  const st = stats(deltas);
  await context.close();
  const result = {
    timestamp: new Date().toISOString(),
    browser: `${browser.browserType().name()} ${browser.version()}${process.env.PERF_CHANNEL ? ` (channel ${process.env.PERF_CHANNEL})` : ''}`,
    mode: label,
    url_query: query,
    renderer: r.renderer,
    renderer_reason: r.reason,
    quality_tier: r.quality,
    gpu,
    viewport: '1440x900',
    device_scale_factor: DPR,
    story_seconds_covered: [+r.s0.toFixed(1), +r.s1.toFixed(1)],
    acts_covered: [r.a0, r.a1],
    ...st,
    targets: { median_fps_min: 55, p95_frame_ms_max: 25 },
    meets_targets: st.median_fps >= 55 && st.p95_frame_ms <= 25,
    console_errors: errors.length,
    how_measured: `${HEADLESS ? 'headless' : 'headed'} Playwright Chromium on ${os.cpus()[0]?.model ?? os.arch()} (${os.platform()} ${os.release()}), ${SECONDS}s of requestAnimationFrame timestamps in Story mode after a 3s warm-up, starting at act ${START_ACT}; rAF is capped by the display refresh rate.`,
  };
  console.log(`${label}: median ${st.median_fps} fps · p95 ${st.p95_frame_ms} ms · renderer ${r.renderer}/${r.quality} · gpu ${gpu}`);
  return result;
}

/** Per-act probe (supports the freeze rule: any act that isn't smooth ships in 2D). */
async function perAct(browser, base) {
  const ACT_S = Number(process.env.PERF_ACT_SECONDS || 8);
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: DPR });
  const page = await context.newPage();
  await page.goto(base + '?force3d=1&act=1');
  await waitReady(page);
  await page.waitForTimeout(3000);
  const acts = await page.evaluate(() => window.__majlis.acts);
  const out = {};
  for (const a of acts.filter((x) => x.act >= 1)) {
    await page.evaluate((s) => {
      window.__majlis.seek(s);
      window.__majlis.setSpeed(1);
      window.__majlis.play();
    }, a.s);
    await page.waitForTimeout(1500);
    const r = await sample(page, ACT_S);
    const deltas = [];
    for (let i = 1; i < r.ts.length; i++) deltas.push(r.ts[i] - r.ts[i - 1]);
    const st = stats(deltas);
    out[`act${a.act}`] = { label: a.label, story_seconds: [+r.s0.toFixed(1), +r.s1.toFixed(1)], renderer: r.renderer, quality_tier: r.quality, median_fps: st.median_fps, p95_frame_ms: st.p95_frame_ms, frames_over_25ms: st.frames_over_25ms, meets_targets: st.median_fps >= 55 && st.p95_frame_ms <= 25 };
    console.log(`  act ${a.act} ${a.label}: median ${st.median_fps} fps · p95 ${st.p95_frame_ms} ms · ${r.renderer}/${r.quality}`);
  }
  await context.close();
  return { timestamp: new Date().toISOString(), seconds_per_act: ACT_S, device_scale_factor: DPR, how_measured: `headed Chromium, seek to each act start, 1.5s settle, ${ACT_S}s rAF sample at speed 1`, ...out };
}

async function main() {
  buildIfStale();
  const server = await startPreview(PORT);
  const browser = await chromium.launch({ headless: HEADLESS, channel: process.env.PERF_CHANNEL || undefined, args: CHROMIUM_ARGS });
  try {
    const story3d = await pass(browser, server.url, 'story_3d', `?force3d=1&act=${START_ACT}`);
    const story2d = await pass(browser, server.url, 'story_2d', `?lite=1&act=${START_ACT}`);
    const patch = { story_3d: story3d, story_2d: story2d };
    if (process.env.PERF_PER_ACT !== '0') {
      console.log('per-act (3D):');
      patch.story_3d_per_act = await perAct(browser, server.url);
    }
    const bundle = bundleStats();
    console.log(`bundle: ${bundle.total_gz_mb_excluding_data} MB gz (JS/CSS/HTML ${bundle.js_css_html_gz_kb} KB gz)`);
    mergePerf({ ...patch, bundle });
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

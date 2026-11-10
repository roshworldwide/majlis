/** Shared helpers for perf / snapshot / soak scripts. */
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { distIsStale } from './e2e-server.mjs';

export const WEB_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const REPO_DIR = path.resolve(WEB_DIR, '..');
export const PERF_JSON = process.env.PERF_OUT || path.join(REPO_DIR, 'results', 'frontend_perf.json');
export const MEDIA_DIR = path.join(REPO_DIR, 'docs', 'media');

/** Chromium flags: real GPU (Metal via ANGLE) and no throttling of occluded/background windows. */
export const CHROMIUM_ARGS = [
  '--use-angle=metal',
  '--enable-gpu',
  '--ignore-gpu-blocklist',
  '--disable-backgrounding-occluded-windows',
  '--disable-renderer-backgrounding',
  '--disable-background-timer-throttling',
];

export function buildIfStale() {
  if (process.env.NO_BUILD) return;
  if (distIsStale()) {
    console.log('[build] dist/ missing or stale → vite build');
    const r = spawnSync('npx', ['vite', 'build'], { cwd: WEB_DIR, stdio: 'inherit' });
    if (r.status !== 0) throw new Error('vite build failed');
  }
}

export async function startPreview(port) {
  const child = spawn('npx', ['vite', 'preview', '--host', '127.0.0.1', '--port', String(port), '--strictPort'], {
    cwd: WEB_DIR,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let out = '';
  child.stdout.on('data', (d) => (out += d));
  child.stderr.on('data', (d) => (out += d));
  const url = `http://127.0.0.1:${port}/`;
  const t0 = Date.now();
  for (;;) {
    try {
      const r = await fetch(url);
      if (r.ok) break;
    } catch {
      /* not up yet */
    }
    if (child.exitCode !== null) throw new Error(`vite preview exited: ${out}`);
    if (Date.now() - t0 > 30_000) throw new Error(`vite preview did not start: ${out}`);
    await new Promise((r) => setTimeout(r, 200));
  }
  return { url, stop: () => child.kill('SIGTERM') };
}

export function readPerf() {
  try {
    return JSON.parse(fs.readFileSync(PERF_JSON, 'utf8'));
  } catch {
    return {};
  }
}

/** Merge keys into results/frontend_perf.json (never deletes other keys). */
export function mergePerf(patch) {
  const cur = readPerf();
  const next = { ...cur, ...patch, updated_at: new Date().toISOString() };
  fs.mkdirSync(path.dirname(PERF_JSON), { recursive: true });
  fs.writeFileSync(PERF_JSON, JSON.stringify(next, null, 2) + '\n');
  return next;
}

function walk(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).flatMap((e) => {
    const p = path.join(dir, e);
    return fs.statSync(p).isDirectory() ? walk(p) : [p];
  });
}

/** gzip sizes of the shipped bundle (JS + CSS + fonts), excluding replay data. */
export function bundleStats() {
  const dist = path.join(WEB_DIR, 'dist');
  const files = walk(dist).filter((f) => !path.relative(dist, f).startsWith('data' + path.sep));
  let jsCssRaw = 0;
  let jsCssGz = 0;
  let otherRaw = 0;
  let otherGz = 0;
  const largest = [];
  for (const f of files) {
    const buf = fs.readFileSync(f);
    const gz = zlib.gzipSync(buf, { level: 9 }).length;
    const rel = path.relative(dist, f);
    if (/\.(js|css|html)$/.test(f)) {
      jsCssRaw += buf.length;
      jsCssGz += gz;
      largest.push({ file: rel, raw_kb: +(buf.length / 1024).toFixed(1), gz_kb: +(gz / 1024).toFixed(1) });
    } else {
      otherRaw += buf.length;
      otherGz += gz;
    }
  }
  largest.sort((a, b) => b.gz_kb - a.gz_kb);
  const single = path.join(WEB_DIR, 'dist-single', 'majlis_experience.html');
  let singleStats = null;
  if (fs.existsSync(single)) {
    const buf = fs.readFileSync(single);
    singleStats = { raw_mb: +(buf.length / 1048576).toFixed(2), gz_mb: +(zlib.gzipSync(buf, { level: 9 }).length / 1048576).toFixed(2), includes_data: true };
  }
  const dataDir = path.join(dist, 'data');
  const dataRaw = walk(dataDir).reduce((s, f) => s + fs.statSync(f).size, 0);
  return {
    timestamp: new Date().toISOString(),
    js_css_html_raw_kb: +(jsCssRaw / 1024).toFixed(1),
    js_css_html_gz_kb: +(jsCssGz / 1024).toFixed(1),
    fonts_assets_raw_kb: +(otherRaw / 1024).toFixed(1),
    fonts_assets_gz_kb: +(otherGz / 1024).toFixed(1),
    total_gz_mb_excluding_data: +((jsCssGz + otherGz) / 1048576).toFixed(3),
    budget_gz_mb: 3,
    within_budget: (jsCssGz + otherGz) / 1048576 <= 3,
    replay_data_raw_kb: +(dataRaw / 1024).toFixed(1),
    largest_files: largest.slice(0, 6),
    single_file_build: singleStats,
    notes: 'gzip level 9 via Node zlib over web/dist (excluding web/dist/data). Fonts are woff2 (already compressed).',
  };
}

export function stats(deltas) {
  const d = [...deltas].sort((a, b) => a - b);
  const q = (p) => d[Math.min(d.length - 1, Math.max(0, Math.ceil((p / 100) * d.length) - 1))];
  const total = deltas.reduce((s, x) => s + x, 0);
  return {
    frames: deltas.length,
    seconds: +(total / 1000).toFixed(2),
    median_fps: +(1000 / q(50)).toFixed(1),
    mean_fps: +((deltas.length * 1000) / total).toFixed(1),
    median_frame_ms: +q(50).toFixed(2),
    p95_frame_ms: +q(95).toFixed(2),
    p99_frame_ms: +q(99).toFixed(2),
    max_frame_ms: +d[d.length - 1].toFixed(2),
    frames_over_25ms: deltas.filter((x) => x > 25).length,
    frames_over_50ms: deltas.filter((x) => x > 50).length,
  };
}

export async function waitReady(page, timeout = 60_000) {
  await page.waitForFunction(() => window.__majlis && window.__majlis.ready === true, null, { timeout, polling: 100 });
}

export async function settle(page, ms = 800) {
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
  await page.waitForTimeout(ms);
}

export async function gpuString(page) {
  return page.evaluate(() => {
    try {
      const gl = document.createElement('canvas').getContext('webgl2');
      if (!gl) return 'no webgl2';
      const ext = gl.getExtension('WEBGL_debug_renderer_info');
      return String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
    } catch (e) {
      return 'error ' + e;
    }
  });
}

export function hasFfmpeg() {
  return spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' }).status === 0;
}

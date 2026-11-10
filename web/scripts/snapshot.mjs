#!/usr/bin/env node
/**
 * Snapshot mode: renders 6 hero frames (1920×1080) to majlis/docs/media/hero_*.png, then
 * records the magic moment (Playwright recordVideo, 1280×720) → docs/media/magic_moment.webm
 * and converts it with ffmpeg → docs/media/magic_moment.gif (≤ 8 MB).
 * Headed Chromium by default (real GPU). Env: SNAP_HEADLESS=1, SNAP_PORT (4176), NO_BUILD=1,
 * SNAP_SKIP_VIDEO=1, SNAP_DIR (alternate output dir).
 */
import { chromium } from '@playwright/test';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { buildIfStale, CHROMIUM_ARGS, hasFfmpeg, MEDIA_DIR, settle, startPreview, waitReady } from './lib.mjs';

const OUT = process.env.SNAP_DIR || MEDIA_DIR;
const PORT = Number(process.env.SNAP_PORT || 4176);
const HEADLESS = process.env.SNAP_HEADLESS === '1';
const MAGIC_CARD_IN = 2.3; // beat-local time at which the Gap Card arrives (src/data/story.ts MAGIC.cardIn)

async function seek(page, s, ms = 1200) {
  await page.evaluate((t) => {
    const m = window.__majlis;
    m.pause();
    m.seek(t);
  }, s);
  await settle(page, ms);
}

async function heroes(browser, base) {
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const errors = [];
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(base + '?force3d=1&paused=1&t=8');
  await waitReady(page);
  await page.waitForTimeout(3500);
  const story = await page.evaluate(() => window.__majlis.story);
  const acts = Object.fromEntries(story.acts.map((a) => [a.act, a.s]));
  const magic = story.gapCards.find((c) => c.style === 'magic');
  const frames = [
    ['hero_1_city.png', acts[1] + 0.75 * ((acts[2] ?? acts[1] + 12) - acts[1])],
    ['hero_2_council.png', magic ? Math.max(acts[2] + 3, magic.sIn - MAGIC_CARD_IN - 0.4) : acts[2] + 6],
    ['hero_3_magic_moment.png', magic ? magic.sIn + 0.8 : acts[2] + 10],
    ['hero_4_evidence.png', story.drawerCue ? story.drawerCue.s0 + 1.6 : story.act3At + 6],
    ['hero_5_audit_verified.png', story.verifyAt + 3.4 + 0.5],
    ['hero_6_reform_finale.png', Math.min(story.finaleAt + 6, story.duration)],
  ];
  fs.mkdirSync(OUT, { recursive: true });
  const written = [];
  for (const [name, s] of frames) {
    await seek(page, s, name.includes('audit') ? 1800 : 1200);
    const r = await page.evaluate(() => ({ renderer: window.__majlis.renderer, act: window.__majlis.act, gap: !!document.querySelector('[data-testid="gap-card"]') }));
    if (r.renderer !== '3d') console.warn(`!! ${name}: renderer is ${r.renderer} (not 3D)`);
    if (name.includes('magic') && !r.gap) console.warn(`!! ${name}: Gap Card not in the DOM at s=${s.toFixed(2)}`);
    const file = path.join(OUT, name);
    await page.screenshot({ path: file });
    written.push({ file, s: +s.toFixed(2), ...r });
    console.log(`${name}  s=${s.toFixed(2)}  act=${r.act}  renderer=${r.renderer}${name.includes('magic') ? `  gapCard=${r.gap}` : ''}`);
  }
  await context.close();
  if (errors.length) console.warn(`console errors during heroes: ${errors.length}\n  ${errors.slice(0, 5).join('\n  ')}`);
  return { story, magic, written };
}

async function video(browser, base, magic) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'majlis-video-'));
  const start = Math.max(0, magic.sIn - MAGIC_CARD_IN - 1.5);
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
    recordVideo: { dir: tmp, size: { width: 1280, height: 720 } },
  });
  const t0 = Date.now();
  const page = await context.newPage();
  await page.goto(base + `?force3d=1&paused=1&t=${start.toFixed(2)}`);
  await waitReady(page);
  await page.waitForTimeout(3000);
  await settle(page, 200);
  const playAt = (Date.now() - t0) / 1000;
  await page.evaluate(() => {
    window.__majlis.setSpeed(1);
    window.__majlis.play();
  });
  await page.waitForTimeout(8500);
  await page.evaluate(() => window.__majlis.pause());
  const vid = page.video();
  await context.close();
  const raw = await vid.path();
  console.log(`raw video ${raw} (play at ${playAt.toFixed(2)} s)`);
  if (!hasFfmpeg()) {
    const dst = path.join(OUT, 'magic_moment_raw.webm');
    fs.copyFileSync(raw, dst);
    console.warn(`ffmpeg not found — copied the untrimmed recording to ${dst} (playback starts at ${playAt.toFixed(2)} s)`);
    return;
  }
  const webm = path.join(OUT, 'magic_moment.webm');
  let r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-ss', playAt.toFixed(2), '-i', raw, '-t', '8', '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '33', '-deadline', 'realtime', '-cpu-used', '8', '-an', webm], { stdio: 'inherit' });
  if (r.status !== 0) {
    const mp4 = path.join(OUT, 'magic_moment.mp4');
    r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-ss', playAt.toFixed(2), '-i', raw, '-t', '8', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '23', '-an', mp4], { stdio: 'inherit' });
    console.log(r.status === 0 ? `video → ${mp4}` : 'ffmpeg video encode failed');
  } else console.log(`video → ${webm}`);
  const gif = path.join(OUT, 'magic_moment.gif');
  const attempts = [
    { fps: 15, w: 960, colors: 128 },
    { fps: 12, w: 800, colors: 96 },
    { fps: 10, w: 720, colors: 64 },
  ];
  for (const a of attempts) {
    const vf = `fps=${a.fps},scale=${a.w}:-1:flags=lanczos,split[x][y];[x]palettegen=max_colors=${a.colors}:stats_mode=diff[p];[y][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle`;
    r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-ss', playAt.toFixed(2), '-t', '8', '-i', raw, '-vf', vf, '-loop', '0', gif], { stdio: 'inherit' });
    if (r.status !== 0) break;
    const mb = fs.statSync(gif).size / 1048576;
    console.log(`gif → ${gif} (${mb.toFixed(2)} MB, ${a.fps} fps, ${a.w}px)`);
    if (mb <= 8) break;
  }
}

async function main() {
  buildIfStale();
  const server = await startPreview(PORT);
  const browser = await chromium.launch({ headless: HEADLESS, args: CHROMIUM_ARGS });
  try {
    const { magic } = await heroes(browser, server.url);
    if (!process.env.SNAP_SKIP_VIDEO) {
      if (magic) await video(browser, server.url, magic);
      else console.warn('no magic-moment cue in this replay — skipping the video');
    }
  } finally {
    await browser.close();
    server.stop();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

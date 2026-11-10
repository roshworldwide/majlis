import type { Page, TestInfo } from '@playwright/test';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const WEB_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const DATA_DIR = path.join(WEB_DIR, 'public', 'data');

export interface StoryInfo {
  duration: number;
  acts: { act: number; s: number; label: string }[];
  gapCards: { gap_id: string; sIn: number; sOut: number; style: string }[];
  verifyAt: number;
  finaleAt: number;
  rewindAt: number;
  reformAt: number;
  act3At: number;
  helixAt: number;
  drawerCue: { s0: number; s1: number; cite_id: string } | null;
}

/** Collects console errors and uncaught page errors (the suite requires zero). */
export function collectErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
  });
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
  return errors;
}

export async function waitReady(page: Page, timeout = 60_000): Promise<void> {
  await page.waitForFunction(() => {
    const m = (window as unknown as { __majlis?: { ready?: boolean } }).__majlis;
    return !!m && m.ready === true;
  }, null, { timeout, polling: 100 });
}

/** Two animation frames + a pause for DOM transitions (200–600 ms) to finish. */
export async function settle(page: Page, ms = 700): Promise<void> {
  await page.evaluate(
    () => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))),
  );
  await page.waitForTimeout(ms);
}

export async function majlis<T>(page: Page, expr: string): Promise<T> {
  return page.evaluate((e) => {
    // eslint-disable-next-line no-new-func
    const fn = new Function('m', `return (${e});`);
    return fn((window as unknown as { __majlis: unknown }).__majlis);
  }, expr) as Promise<T>;
}

export async function seekPaused(page: Page, s: number, ms = 700): Promise<void> {
  await page.evaluate((t) => {
    const m = (window as unknown as { __majlis: { pause: () => void; seek: (s: number) => void } }).__majlis;
    m.pause();
    m.seek(t);
  }, s);
  await settle(page, ms);
}

export function readReplay(): any {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'replay.json'), 'utf8'));
}

export function auditPath(): string {
  const r = readReplay();
  return path.join(DATA_DIR, (r.audit && r.audit.href) || 'audit.jsonl');
}

/** Byte-exact chain verification in Node — the same recipe as `majlis verify` and the browser. */
export function nodeVerify(text: string): { ok: boolean; entries: number; head: string; first: string; bad: number[] } {
  const lines = text
    .split('\n')
    .filter((l) => l.trim().length > 0)
    .map((l) => (l.endsWith('\r') ? l.slice(0, -1) : l));
  let prev = '0'.repeat(64);
  const bad: number[] = [];
  let first = '';
  lines.forEach((L, i) => {
    const o = JSON.parse(L);
    const h = String(o.hash);
    if (i === 0) first = h;
    const needle = `"hash":"${h}",`;
    const at = L.indexOf(needle);
    const body = at >= 0 ? L.slice(0, at) + L.slice(at + needle.length) : L;
    const d = crypto.createHash('sha256').update(body, 'utf8').digest('hex');
    if (at < 0 || d !== h || o.prev_hash !== prev) bad.push(i);
    prev = h;
  });
  return { ok: bad.length === 0 && lines.length > 0, entries: lines.length, head: prev, first, bad };
}

export function shotPath(info: TestInfo, variant: string, name: string): string {
  const dir = path.join(WEB_DIR, 'test-results', 'screens', info.project.name, variant);
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, name);
}

/** 5 evenly spaced story times inside each act 1–4. */
export function actPoints(story: StoryInfo): { act: number; points: number[] }[] {
  const acts = [...story.acts].sort((a, b) => a.s - b.s);
  const out: { act: number; points: number[] }[] = [];
  for (let i = 0; i < acts.length; i++) {
    const a = acts[i];
    if (a.act < 1) continue;
    const end = i + 1 < acts.length ? acts[i + 1].s : story.duration;
    const pts: number[] = [];
    for (let k = 0; k < 5; k++) pts.push(a.s + ((end - a.s) * (k + 0.5)) / 5);
    out.push({ act: a.act, points: pts });
  }
  return out;
}

export async function hasWebGL2(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    try {
      return !!document.createElement('canvas').getContext('webgl2');
    } catch {
      return false;
    }
  });
}

export async function glRenderer(page: Page): Promise<string> {
  return page.evaluate(() => {
    try {
      const gl = document.createElement('canvas').getContext('webgl2') || document.createElement('canvas').getContext('webgl');
      if (!gl) return 'none';
      const ext = gl.getExtension('WEBGL_debug_renderer_info');
      return String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
    } catch (e) {
      return 'error: ' + String(e);
    }
  });
}

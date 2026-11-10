#!/usr/bin/env node
/**
 * Web server for Playwright: builds web/dist if it is missing or older than the sources
 * (src/, public/data/, index.html, vite.config.ts), then serves it with `vite preview`.
 * Env: E2E_PORT (default 4173), E2E_NO_BUILD=1 to skip the staleness build.
 */
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const webDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const port = process.env.E2E_PORT || '4173';

export function newestMtime(p) {
  if (!fs.existsSync(p)) return 0;
  const st = fs.statSync(p);
  if (!st.isDirectory()) return st.mtimeMs;
  let m = 0;
  for (const e of fs.readdirSync(p)) m = Math.max(m, newestMtime(path.join(p, e)));
  return m;
}

export function distIsStale(outDir = 'dist', entry = 'index.html') {
  const out = path.join(webDir, outDir, entry);
  if (!fs.existsSync(out)) return true;
  const built = fs.statSync(out).mtimeMs;
  const srcs = ['src', 'public/data', 'index.html', 'vite.config.ts', 'package.json'].map((p) => path.join(webDir, p));
  return srcs.some((p) => newestMtime(p) > built);
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  if (!process.env.E2E_NO_BUILD && distIsStale()) {
    console.log('[e2e-server] dist/ missing or stale → vite build');
    const r = spawnSync('npx', ['vite', 'build'], { cwd: webDir, stdio: 'inherit' });
    if (r.status !== 0) process.exit(r.status ?? 1);
  }
  const child = spawn('npx', ['vite', 'preview', '--host', '127.0.0.1', '--port', port, '--strictPort'], {
    cwd: webDir,
    stdio: 'inherit',
  });
  const stop = () => {
    child.kill('SIGTERM');
    process.exit(0);
  };
  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);
  child.on('exit', (code) => process.exit(code ?? 0));
}

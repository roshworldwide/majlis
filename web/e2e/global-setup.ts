import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { WEB_DIR } from './helpers';

function newest(p: string): number {
  if (!fs.existsSync(p)) return 0;
  const st = fs.statSync(p);
  if (!st.isDirectory()) return st.mtimeMs;
  return fs.readdirSync(p).reduce((m, e) => Math.max(m, newest(path.join(p, e))), 0);
}

/** Builds the single-file Experience (dist-single/majlis_experience.html) if missing or stale. */
export default async function globalSetup(): Promise<void> {
  if (process.env.E2E_NO_BUILD) return;
  const out = path.join(WEB_DIR, 'dist-single', 'majlis_experience.html');
  const built = fs.existsSync(out) ? fs.statSync(out).mtimeMs : 0;
  const src = Math.max(...['src', 'public/data', 'index.html', 'vite.config.ts', 'package.json'].map((p) => newest(path.join(WEB_DIR, p))));
  if (built && built >= src) return;
  console.log('[global-setup] building the single-file Experience (vite build --mode single)…');
  const r = spawnSync('npx', ['vite', 'build', '--mode', 'single'], { cwd: WEB_DIR, stdio: 'inherit' });
  if (r.status !== 0) console.warn('[global-setup] single-file build failed; single.spec will be skipped');
}

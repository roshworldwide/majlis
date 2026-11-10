import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.resolve(here, 'public/data');

/**
 * `virtual:majlis-inline` — in the single-file build the three data files are
 * inlined at build time (file:// cannot fetch). In the normal build it is null
 * and the app fetches data/replay.json etc. at runtime.
 * audit.jsonl is inlined as an exact string (never re-serialised) so the
 * in-browser hash verification stays byte-exact.
 */
function inlineData(single: boolean): Plugin {
  const id = 'virtual:majlis-inline';
  return {
    name: 'majlis-inline-data',
    resolveId(src) {
      if (src === id) return '\0' + id;
      return null;
    },
    load(src) {
      if (src !== '\0' + id) return null;
      if (!single) return 'export default null;';
      const replay = fs.readFileSync(path.join(dataDir, 'replay.json'), 'utf8');
      const parsed = JSON.parse(replay);
      const auditName = (parsed.audit && parsed.audit.href) || 'audit.jsonl';
      const kbName = (parsed.kb_points && parsed.kb_points.href) || 'kb_points.bin';
      const audit = fs.existsSync(path.join(dataDir, auditName))
        ? fs.readFileSync(path.join(dataDir, auditName), 'utf8')
        : null;
      const kb = fs.existsSync(path.join(dataDir, kbName))
        ? fs.readFileSync(path.join(dataDir, kbName)).toString('base64')
        : null;
      return `export default ${JSON.stringify({ replay, audit, kb })};`;
    },
  };
}

function renameSingle(): Plugin {
  return {
    name: 'majlis-rename-single',
    apply: 'build',
    closeBundle() {
      const from = path.resolve(here, 'dist-single/index.html');
      const to = path.resolve(here, 'dist-single/majlis_experience.html');
      if (fs.existsSync(from)) fs.renameSync(from, to);
    },
  };
}

export default defineConfig(({ mode }) => {
  const single = mode === 'single';
  return {
    base: './',
    plugins: [react(), inlineData(single), ...(single ? [viteSingleFile(), renameSingle()] : [])],
    publicDir: single ? false : 'public',
    define: {
      __MAJLIS_SINGLE__: JSON.stringify(single),
    },
    build: {
      outDir: single ? 'dist-single' : 'dist',
      emptyOutDir: true,
      target: 'es2020',
      chunkSizeWarningLimit: 4000,
      sourcemap: false,
    },
    server: { port: 5173 },
    preview: { port: 4173 },
  };
});

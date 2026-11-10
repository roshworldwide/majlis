/**
 * Loads replay.json, audit.jsonl and kb_points.bin.
 * - Single-file build: the three files are inlined at build time (virtual:majlis-inline).
 * - Normal build / dev: fetched at runtime from ./data/ (relative, works on GitHub Pages).
 * Validation never blanks the screen: a schema mismatch is reported as a warning and the
 * renderer continues best-effort; only a missing/corrupt replay is fatal (friendly screen).
 */
import inline from 'virtual:majlis-inline';
import { ReplaySchema, type Replay } from './replay.schema';

export interface KbPoints {
  count: number;
  positions: Float32Array; // xyz interleaved
  clusters: Uint8Array; // 0 uae, 1 global, 2 itu, 3 other
}

export interface LoadedData {
  replay: Replay;
  schemaIssues: string[];
  auditText: string | null;
}

const DATA_BASE = 'data/';

function b64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export function parseKb(buf: ArrayBuffer | Uint8Array, declaredCount: number): KbPoints | null {
  const bytes = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  // N*12 bytes of float32 xyz + N bytes of cluster codes => N = len/13
  let n = declaredCount;
  if (!n || n * 13 !== bytes.byteLength) n = Math.floor(bytes.byteLength / 13);
  if (n <= 0) return null;
  // copy into aligned buffers (little-endian)
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const positions = new Float32Array(n * 3);
  for (let i = 0; i < n * 3; i++) positions[i] = dv.getFloat32(i * 4, true);
  const clusters = new Uint8Array(n);
  clusters.set(bytes.subarray(n * 12, n * 12 + n));
  return { count: n, positions, clusters };
}

function validate(raw: unknown): { replay: Replay; issues: string[] } {
  const res = ReplaySchema.safeParse(raw);
  if (res.success) return { replay: res.data, issues: [] };
  const issues = res.error.issues.slice(0, 8).map((i) => `${i.path.join('.')}: ${i.message}`);
  const r = raw as Partial<Replay> | null;
  if (!r || typeof r !== 'object' || !Array.isArray(r.timeline) || !Array.isArray(r.agents) || !r.meta) {
    throw new Error('replay.json is missing required sections (meta, agents, timeline).');
  }
  // best effort: fill in defaults for missing optional-ish sections
  const fixed = {
    channels: [],
    facts: [],
    waves: [],
    gaps: [],
    citations: {},
    kpis: { cells_asleep_pct: [], call_setup_success: [], ambulance_delta_min: [] },
    kb_points: { href: 'kb_points.bin', count: 0, clusters: [] },
    audit: { href: 'audit.jsonl', root: '' },
    compare: { baseline_run: '', reform_run: null, metrics: {} },
    ...r,
  } as Replay;
  return { replay: fixed, issues };
}

export async function loadReplay(): Promise<LoadedData> {
  let rawText: string;
  let auditText: string | null = null;
  if (inline) {
    rawText = inline.replay;
    auditText = inline.audit;
  } else {
    const res = await fetch(DATA_BASE + 'replay.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(`Could not load data/replay.json (${res.status}).`);
    rawText = await res.text();
  }
  const raw = JSON.parse(rawText);
  const { replay, issues } = validate(raw);
  if (!inline) {
    try {
      const href = replay.audit?.href || 'audit.jsonl';
      const res = await fetch(DATA_BASE + href, { cache: 'no-cache' });
      if (res.ok) auditText = await res.text();
    } catch {
      auditText = null;
    }
  }
  return { replay, schemaIssues: issues, auditText };
}

export async function loadKb(replay: Replay): Promise<KbPoints | null> {
  const count = replay.kb_points?.count ?? 0;
  try {
    if (inline) {
      if (!inline.kb) return null;
      return parseKb(b64ToBytes(inline.kb), count);
    }
    const href = replay.kb_points?.href || 'kb_points.bin';
    const res = await fetch(DATA_BASE + href, { cache: 'no-cache' });
    if (!res.ok) return null;
    return parseKb(await res.arrayBuffer(), count);
  } catch {
    return null;
  }
}

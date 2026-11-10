import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { ReplaySchema } from '../src/data/replay.schema';
import { DATA_DIR, nodeVerify, readReplay } from './helpers';

/**
 * Data-contract check for the three data files the Experience renders (run it after swapping in a
 * new golden run: `npx playwright test e2e/data.spec.ts --project=chromium`). Pure Node, no browser.
 */
test.describe('replay data contract', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'data checks run once');
  const replay = readReplay();

  test('replay.json matches the zod mirror of replay.schema.json', () => {
    const r = ReplaySchema.safeParse(replay);
    const issues = r.success ? [] : r.error.issues.slice(0, 12).map((i) => `${i.path.join('.')}: ${i.message}`);
    expect(issues, issues.join('\n')).toEqual([]);
  });

  test('referential integrity (gaps, citations, agents, channels, stars)', ({}, info) => {
    const problems: string[] = [];
    const warnings: string[] = [];
    const byChunk = new Set<string>(Object.values<any>(replay.citations ?? {}).map((c) => c.chunk_id).filter(Boolean));
    const agents = new Set<string>(replay.agents.map((a: any) => a.id));
    const gaps = new Set<string>(replay.gaps.map((g: any) => g.gap_id));
    const reformGaps = new Set<string>((replay.compare?.reform?.gaps ?? []).map((g: any) => g.gap_id));
    const cites = replay.citations ?? {};
    const count = replay.kb_points?.count ?? 0;
    const checkEvents = (evs: any[], label: string, gapSet: Set<string>) => {
      let lastT = -Infinity;
      for (const e of evs) {
        if (e.t < lastT) problems.push(`${label}: timeline not sorted by t at seq ${e.seq}`);
        lastT = Math.max(lastT, e.t);
        if (e.agent && !agents.has(e.agent)) problems.push(`${label}: unknown agent ${e.agent} (seq ${e.seq})`);
        const gid = e.payload?.gap_id;
        if (gid && !gaps.has(gid) && !gapSet.has(gid)) problems.push(`${label}: gap_id ${gid} not in gaps[] (seq ${e.seq})`);
        if (e.type === 'message') {
          for (const k of ['from', 'to']) if (e.payload?.[k] && !agents.has(e.payload[k])) problems.push(`${label}: message ${k} ${e.payload[k]} unknown`);
          if (typeof e.payload?.deliver_t === 'number' && typeof e.payload?.sent_t === 'number' && e.payload.deliver_t < e.payload.sent_t) problems.push(`${label}: message delivers before it is sent (seq ${e.seq})`);
        }
        // event-level cite ids that are not citations{} keys: the UI can only resolve them via chunk_id (soft)
        for (const k of ['cite_ids', 'global_cite_ids'])
          for (const c of e.payload?.[k] ?? [])
            if (!cites[c]) warnings.push(`${label} ${e.type} seq ${e.seq}: ${k} '${c}' is not a citations{} key${byChunk.has(c) ? ' (matches a chunk_id)' : ' (unresolvable)'}`);
      }
    };
    checkEvents(replay.timeline, 'baseline', gaps);
    if (replay.compare?.reform) checkEvents(replay.compare.reform.timeline, 'reform', reformGaps);
    for (const g of [...replay.gaps, ...(replay.compare?.reform?.gaps ?? [])]) {
      if (!g.global_examples?.length) problems.push(`gap ${g.gap_id}: no global example`);
      for (const x of g.global_examples ?? []) if (!cites[x.cite_id]) problems.push(`gap ${g.gap_id}: global example cite ${x.cite_id} missing`);
    }
    for (const ch of replay.channels) for (const k of ['from', 'to']) if (!agents.has(ch[k])) problems.push(`channel ${ch.from}->${ch.to}: unknown ${k}`);
    for (const a of replay.agents) for (const m of a.mandates) for (const c of m.citations) if (!cites[c]) problems.push(`agent ${a.id} mandate ${m.id}: cite ${c} missing`);
    for (const [id, c] of Object.entries<any>(cites)) if (c.star_index != null && (c.star_index < 0 || c.star_index >= count)) problems.push(`citation ${id}: star_index ${c.star_index} outside kb_points (count ${count})`);
    if (warnings.length) {
      const unresolvable = warnings.filter((w) => w.endsWith('(unresolvable)')).length;
      const msg = `${warnings.length} event citation refs are not citations{} keys (${warnings.length - unresolvable} match a chunk_id, ${unresolvable} unresolvable), e.g. ${warnings[0]}`;
      info.annotations.push({ type: 'warning', description: msg });
      console.warn('[data] ' + msg);
    }
    expect(problems, problems.slice(0, 30).join('\n')).toEqual([]);
  });

  test('kb_points.bin and audit.jsonl match their declarations', () => {
    const kb = path.join(DATA_DIR, replay.kb_points?.href || 'kb_points.bin');
    const n = replay.kb_points?.count ?? 0;
    expect(fs.existsSync(kb)).toBe(true);
    expect(fs.statSync(kb).size, 'kb_points.bin must be N*12 float32 bytes + N cluster bytes').toBe(n * 13);
    const codes = fs.readFileSync(kb).subarray(n * 12);
    expect(codes.every((c) => c <= 3), 'cluster codes must be 0..3').toBe(true);
    const audit = nodeVerify(fs.readFileSync(path.join(DATA_DIR, replay.audit?.href || 'audit.jsonl'), 'utf8'));
    expect(audit.bad).toEqual([]);
    expect(audit.head).toBe(replay.audit.root);
    if (replay.audit.entries != null) expect(audit.entries).toBe(replay.audit.entries);
    if (replay.meta?.audit_root) expect(audit.head).toBe(replay.meta.audit_root);
    const ra = replay.compare?.reform?.audit;
    if (ra?.href && fs.existsSync(path.join(DATA_DIR, ra.href))) {
      const r = nodeVerify(fs.readFileSync(path.join(DATA_DIR, ra.href), 'utf8'));
      expect(r.bad, 'reform audit chain').toEqual([]);
      expect(r.head).toBe(ra.root);
    }
  });
});

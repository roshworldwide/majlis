/**
 * The story schedule: one continuous, scrubbable timeline.
 * Scene state = f(s) where s = story seconds. Everything (sim clock, beats, captions,
 * Gap Cards, camera shots, evidence beams, rewind) is derived from replay.json, so the
 * same s always renders the same frame (deterministic, works for snapshots and tests).
 */
import type { Model, RunModel } from './derive';
import { KNOW_THRESHOLD, agentName, factLabel, tLabel, clockLabel } from './derive';
import type { ReplayEvent } from './replay.schema';

export type Act = 0 | 1 | 2 | 3 | 4;
export type RunKind = 'baseline' | 'reform';
export type SegKind = 'cold' | 'city' | 'run' | 'beat' | 'evidence' | 'rewind' | 'inscribe' | 'finale';
export type BeatKind =
  | 'magic'
  | 'block'
  | 'block_plain'
  | 'flag'
  | 'inject'
  | 'belief'
  | 'proposal'
  | 'action'
  | 'pass'
  | 'message'
  | 'gap'
  | 'gap_card'
  | 'qa'
  | 'restore'
  | 'kpi';

export interface Segment {
  s0: number;
  s1: number;
  act: Act;
  run: RunKind;
  kind: SegKind;
  t0: number;
  t1: number;
  ev: number; // event index for beats, else -1
  beat?: BeatKind;
}

export interface GapCardCue {
  gap_id: string;
  sIn: number;
  sOut: number;
  style: 'magic' | 'light' | 'recorded';
  run: RunKind;
  ev: number;
}

export interface CaptionCue {
  s0: number;
  s1: number;
  text: string;
  tone: 'info' | 'block' | 'flag' | 'ok' | 'act';
}

export interface EvidenceCue {
  s0: number;
  agent: string | null;
  cite_id: string;
  why: string;
}

export interface CamKey {
  s: number;
  shot: Shot;
}

export type Shot =
  | 'cold'
  | 'city'
  | 'rise'
  | 'council'
  | 'magic'
  | 'glance'
  | 'galaxy'
  | 'helix'
  | 'rewind'
  | 'reform'
  | 'finale';

export interface Story {
  segments: Segment[];
  duration: number;
  acts: { act: Act; s: number; label: string }[];
  evS: Record<RunKind, number[]>; // story time at which each event's beat starts
  evD: Record<RunKind, number[]>; // beat duration per event
  beatKind: Record<RunKind, (BeatKind | null)[]>;
  captions: CaptionCue[];
  gapCards: GapCardCue[];
  evidence: EvidenceCue[];
  drawerCue: { s0: number; s1: number; cite_id: string } | null;
  verifyAt: number;
  verifyDur: number;
  helixAt: number;
  cam: CamKey[];
  finaleAt: number;
  rewindAt: number;
  inscribeAt: number;
  reformAt: number;
  act3At: number;
  markers: { s: number; kind: 'wave' | 'block' | 'gap' | 'flag' | 'restore'; label: string }[];
  slowWindows: { a: number; b: number; rate: number }[];
}

/** Magic-moment choreography, in beat-local seconds (shared by 3D and 2D). */
export const MAGIC = { fireEnd: 0.9, slowStart: 0.9, slowEnd: 2.1, slowRate: 0.25, cardIn: 2.3, dur: 6.4 };
export const LIGHT = { fireEnd: 0.7, slowStart: 0.7, slowEnd: 1.1, slowRate: 0.5, cardIn: 1.3, dur: 3.8 };
export const PLAIN = { fireEnd: 0.7, slowStart: 0.7, slowEnd: 0.7, slowRate: 1, cardIn: 99, dur: 2.6 };
export const CARD_HOLD = 6.5;

export type BeatTiming = typeof MAGIC;
export function timingFor(kind: BeatKind | null | undefined): BeatTiming {
  if (kind === 'magic') return MAGIC;
  if (kind === 'block') return LIGHT;
  return PLAIN;
}

/** Local animation clock of an impact beat: runs at slowRate inside the slow-mo window. */
export function impactClock(kind: BeatKind | null | undefined, u: number): number {
  const T = timingFor(kind);
  if (u <= T.slowStart) return u;
  if (u <= T.slowEnd) return T.slowStart + (u - T.slowStart) * T.slowRate;
  return T.slowStart + (T.slowEnd - T.slowStart) * T.slowRate + (u - T.slowEnd);
}

const BASE: Record<BeatKind, number> = {
  magic: MAGIC.dur,
  block: LIGHT.dur,
  block_plain: PLAIN.dur,
  flag: 2.6,
  inject: 2.6,
  belief: 0.45,
  proposal: 1.5,
  action: 1.0,
  pass: 0.6,
  message: 1.1,
  gap: 0.5,
  gap_card: 3.6,
  qa: 3.4,
  restore: 3.6,
  kpi: 0.3,
};
const MAJOR = new Set<BeatKind>(['magic', 'block', 'block_plain', 'flag', 'inject', 'gap_card', 'qa', 'restore']);

function classify(run: RunModel, i: number, magicUsed: { v: boolean }, carded: Set<string>, reformRun: boolean): BeatKind {
  const e = run.events[i];
  const p = e.payload || {};
  switch (e.type) {
    case 'gate_block':
      if (p.gap_id) {
        carded.add(String(p.gap_id));
        if (!magicUsed.v && !reformRun) {
          magicUsed.v = true;
          return 'magic';
        }
        return 'block';
      }
      return 'block_plain';
    case 'gate_flag':
      return 'flag';
    case 'inject':
      return 'inject';
    case 'belief':
      return 'belief';
    case 'proposal':
      return 'proposal';
    case 'action':
      return 'action';
    case 'gate_pass':
      return 'pass';
    case 'message':
      return 'message';
    case 'gap': {
      const id = String(p.gap_id ?? '');
      if (carded.has(id)) return 'gap';
      carded.add(id);
      return 'gap_card';
    }
    case 'adviser_qa':
      return 'qa';
    case 'kpi':
      return p.event === 'service_restored' ? 'restore' : 'kpi';
    default:
      return 'kpi';
  }
}

function beatBase(run: RunModel, i: number, kind: BeatKind): number {
  if (kind === 'belief') {
    const e = run.events[i];
    const c = Number(e.payload?.confidence ?? 0);
    const prev = Number(e.payload?.prev ?? 0);
    return c >= KNOW_THRESHOLD && prev < KNOW_THRESHOLD ? 0.55 : 0.25;
  }
  return BASE[kind];
}

function runDur(dt: number, scale: number): number {
  if (dt <= 0) return 0;
  return Math.min(0.5 * dt, 2.0 + 0.12 * dt) * scale;
}

function trunc(s: string, n: number): string {
  const x = s.replace(/\s+/g, ' ').trim();
  return x.length > n ? x.slice(0, n - 1) + '…' : x;
}

export function captionFor(model: Model, run: RunModel, i: number, kind: BeatKind): { text: string; tone: CaptionCue['tone'] } {
  const e: ReplayEvent = run.events[i];
  const p = e.payload || {};
  const who = agentName(model, e.agent);
  const when = `${tLabel(e.t)} · ${clockLabel(e.t)}`;
  switch (kind) {
    case 'inject': {
      const to = Array.isArray(p.visible_to) ? p.visible_to.map((a: string) => agentName(model, a)).join(', ') : '';
      return { text: `${p.wave ?? e.wave} · ${when} — ${to ? to + ' sees: ' : ''}${trunc(String(p.content ?? ''), 150)}`, tone: 'info' };
    }
    case 'belief': {
      const f = factLabel(model, String(p.fact ?? ''));
      const c = Number(p.confidence ?? 0);
      const knows = c >= KNOW_THRESHOLD;
      return { text: `${who} ${knows ? 'now knows' : 'suspects'}: ${trunc(f, 110)} (confidence ${c.toFixed(2)})`, tone: knows ? 'ok' : 'info' };
    }
    case 'proposal': {
      const chosen = Array.isArray(p.chosen) ? p.chosen.join(', ') : '';
      return { text: `${who} proposes: ${trunc(chosen || String(p.situation ?? ''), 140)}`, tone: 'info' };
    }
    case 'action':
      return { text: `${who} acts: ${String(p.type ?? 'action').replace(/_/g, ' ')}${p.status ? ` (${p.status})` : ''}`, tone: 'info' };
    case 'pass':
      return { text: `Policy gate passed ${who}'s ${p.kind ?? 'item'}${Array.isArray(p.cite_ids) && p.cite_ids.length ? ` — cited ${p.cite_ids.join(', ')}` : ''}`, tone: 'ok' };
    case 'message': {
      const to = agentName(model, String(p.to ?? ''));
      const legal = p.route !== 'informal' && p.legal !== false;
      const del = typeof p.deliver_t === 'number' ? ` · arrives ${tLabel(p.deliver_t)}` : '';
      return {
        text: `${who} → ${to}: ${legal ? 'legal channel' : 'no legal channel — informal route'}${del}`,
        tone: legal ? 'info' : 'flag',
      };
    }
    case 'magic':
    case 'block': {
      const act = String(p.action_type ?? p.kind ?? 'action').replace(/_/g, ' ');
      return { text: `BLOCKED by the policy gate (${p.rule ?? 'P'}): ${who} — ${act}. ${trunc(String(p.reason ?? ''), 140)}`, tone: 'block' };
    }
    case 'block_plain': {
      const act = String(p.action_type ?? p.kind ?? 'item').replace(/_/g, ' ');
      return { text: `Policy gate stopped ${who}'s ${act} (${p.rule ?? 'P'}): ${trunc(String(p.reason ?? ''), 150)}`, tone: 'block' };
    }
    case 'flag':
      return { text: `Conflict flagged (${p.rule ?? 'G4'}), not blocked: ${String(p.action_type ?? '').replace(/_/g, ' ')} — ${trunc(String(p.reason ?? ''), 140)}`, tone: 'flag' };
    case 'gap':
    case 'gap_card': {
      const g = model.gapsById.get(String(p.gap_id ?? ''));
      return { text: `Gap recorded: ${g ? g.title : p.gap_id}`, tone: 'flag' };
    }
    case 'qa':
      return { text: `${agentName(model, String(p.asked_by ?? ''))} asks the Adviser: “${trunc(String(p.question ?? ''), 150)}”`, tone: 'info' };
    case 'restore':
      return { text: `${when} — Service restored${p.detail ? `: ${trunc(String(p.detail), 120)}` : ''}. The city relights.`, tone: 'ok' };
    default:
      return { text: `${when} — ${e.type}`, tone: 'info' };
  }
}

interface BuildCtx {
  segs: Segment[];
  s: number;
}

function scheduleRun(
  ctx: BuildCtx,
  model: Model,
  run: RunModel,
  act: Act,
  budget: number,
  out: { evS: number[]; evD: number[]; kinds: (BeatKind | null)[] },
  captions: CaptionCue[],
  gapCards: GapCardCue[],
  cam: CamKey[],
  markers: Story['markers'],
  tStart: number,
  tEnd: number,
  runScale: number,
): void {
  const n = run.events.length;
  const magicUsed = { v: run.kind === 'reform' };
  const carded = new Set<string>();
  const kinds: BeatKind[] = [];
  for (let i = 0; i < n; i++) kinds.push(classify(run, i, magicUsed, carded, run.kind === 'reform'));
  const base = kinds.map((k, i) => beatBase(run, i, k));
  // run time between distinct t values
  let runTotal = 0;
  let prevT = tStart;
  for (let i = 0; i < n; i++) {
    runTotal += runDur(run.events[i].t - prevT, runScale);
    prevT = Math.max(prevT, run.events[i].t);
  }
  runTotal += runDur(tEnd - prevT, runScale);
  let majorSum = 0;
  let minorSum = 0;
  let fixed = 0;
  kinds.forEach((k, i) => {
    if (k === 'magic') fixed += base[i];
    else if (MAJOR.has(k)) majorSum += base[i];
    else minorSum += base[i];
  });
  let minorK = 1;
  let majorK = 1;
  const avail = budget - runTotal - fixed;
  if (majorSum + minorSum > avail) {
    minorK = Math.max(0.15, (avail - majorSum) / Math.max(minorSum, 1e-6));
    if (majorSum + minorSum * minorK > avail) majorK = Math.max(0.55, (avail - minorSum * minorK) / Math.max(majorSum, 1e-6));
  }
  const dur = kinds.map((k, i) => (k === 'magic' ? base[i] : MAJOR.has(k) ? Math.max(base[i] * majorK, Math.min(base[i], 1.6)) : Math.max(0.08, base[i] * minorK)));

  let t = tStart;
  for (let i = 0; i < n; i++) {
    const e = run.events[i];
    if (e.t > t) {
      const d = runDur(e.t - t, runScale);
      ctx.segs.push({ s0: ctx.s, s1: ctx.s + d, act, run: run.kind, kind: 'run', t0: t, t1: e.t, ev: -1 });
      ctx.s += d;
      t = e.t;
    }
    const k = kinds[i];
    const d = dur[i];
    out.evS[i] = ctx.s;
    out.evD[i] = d;
    out.kinds[i] = k;
    ctx.segs.push({ s0: ctx.s, s1: ctx.s + d, act, run: run.kind, kind: 'beat', t0: t, t1: t, ev: i, beat: k });
    // captions for beats that carry meaning
    if (k !== 'kpi' && !(k === 'gap')) {
      const c = captionFor(model, run, i, k);
      captions.push({ s0: ctx.s, s1: ctx.s + Math.max(d, MAJOR.has(k) ? d : 1.6), text: c.text, tone: c.tone });
    }
    const gid = String(e.payload?.gap_id ?? '');
    if ((k === 'magic' || k === 'block') && gid) {
      const T = timingFor(k);
      gapCards.push({ gap_id: gid, sIn: ctx.s + T.cardIn, sOut: ctx.s + T.cardIn + CARD_HOLD, style: k === 'magic' ? 'magic' : 'light', run: run.kind, ev: i });
    } else if (k === 'gap_card' && gid) {
      gapCards.push({ gap_id: gid, sIn: ctx.s + 0.35, sOut: ctx.s + 0.35 + CARD_HOLD * 0.8, style: 'recorded', run: run.kind, ev: i });
    }
    if (act === 2) {
      if (k === 'magic') cam.push({ s: ctx.s, shot: 'magic' }, { s: ctx.s + d + 0.2, shot: 'council' });
      if (k === 'restore') cam.push({ s: ctx.s, shot: 'glance' }, { s: ctx.s + d + 0.4, shot: 'council' });
      if (k === 'inject') markers.push({ s: ctx.s, kind: 'wave', label: `${e.payload?.wave ?? e.wave} · ${tLabel(e.t)}` });
      if (k === 'magic' || k === 'block' || k === 'block_plain') markers.push({ s: ctx.s, kind: 'block', label: `Blocked · ${tLabel(e.t)}` });
      if (k === 'gap_card') markers.push({ s: ctx.s, kind: 'gap', label: `Gap · ${gid}` });
      if (k === 'flag') markers.push({ s: ctx.s, kind: 'flag', label: `Conflict flagged · ${tLabel(e.t)}` });
      if (k === 'restore') markers.push({ s: ctx.s, kind: 'restore', label: `Service restored · ${tLabel(e.t)}` });
    }
    ctx.s += d;
  }
  if (tEnd > t) {
    const d = runDur(tEnd - t, runScale);
    ctx.segs.push({ s0: ctx.s, s1: ctx.s + d, act, run: run.kind, kind: 'run', t0: t, t1: tEnd, ev: -1 });
    ctx.s += d;
  }
}

export function buildStory(model: Model): Story {
  const ctx: BuildCtx = { segs: [], s: 0 };
  const captions: CaptionCue[] = [];
  const gapCards: GapCardCue[] = [];
  const cam: CamKey[] = [];
  const markers: Story['markers'] = [];
  const acts: Story['acts'] = [];
  const t0 = model.t0;
  const H = model.horizon;
  const title = model.replay.meta.title || 'A fictional simulation';
  const origin = model.replay.meta.clock_origin || '';

  // Act 0 — cold open
  const COLD = 6.5;
  acts.push({ act: 0, s: 0, label: 'Cold open' });
  ctx.segs.push({ s0: 0, s1: COLD, act: 0, run: 'baseline', kind: 'cold', t0: model.tCityStart, t1: model.tCityStart, ev: -1 });
  cam.push({ s: 0, shot: 'cold' });
  ctx.s = COLD;

  // Act I — the city
  const CITY = 12;
  acts.push({ act: 1, s: ctx.s, label: 'The City' });
  cam.push({ s: ctx.s - 1.2, shot: 'city' });
  ctx.segs.push({ s0: ctx.s, s1: ctx.s + CITY, act: 1, run: 'baseline', kind: 'city', t0: model.tCityStart, t1: t0, ev: -1 });
  captions.push({
    s0: ctx.s,
    s1: ctx.s + CITY * 0.5,
    text: `${title}. ${origin ? origin + '. ' : ''}An illustrative city of ${model.cellsTotal.toLocaleString('en-US')} 5G cells (scenario parameter).`,
    tone: 'act',
  });
  captions.push({
    s0: ctx.s + CITY * 0.5,
    s1: ctx.s + CITY,
    text: 'An ML energy-saving model starts putting cells to sleep as the crowd peaks. Red arcs are emergency calls.',
    tone: 'act',
  });
  ctx.s += CITY;

  // Act II — the council (baseline run)
  acts.push({ act: 2, s: ctx.s, label: 'The Council' });
  cam.push({ s: ctx.s, shot: 'rise' }, { s: ctx.s + 2.6, shot: 'council' });
  const evS: Story['evS'] = { baseline: [], reform: [] };
  const evD: Story['evD'] = { baseline: [], reform: [] };
  const beatKind: Story['beatKind'] = { baseline: [], reform: [] };
  const outB = { evS: evS.baseline, evD: evD.baseline, kinds: beatKind.baseline };
  scheduleRun(ctx, model, model.baseline, 2, 96, outB, captions, gapCards, cam, markers, t0, H, 1);

  // Act III — evidence galaxy + audit helix
  const act3At = ctx.s;
  acts.push({ act: 3, s: ctx.s, label: 'The Evidence' });
  cam.push({ s: ctx.s, shot: 'galaxy' });
  captions.push({ s0: ctx.s, s1: ctx.s + 3.2, text: 'Every claim rests on a cited source. Each star is one chunk of law or standard in the knowledge base.', tone: 'act' });
  const evidence: EvidenceCue[] = [];
  let s = ctx.s + 3.0;
  const uses = model.citeUses.filter((u) => model.citations[u.cite_id]).slice(0, 8);
  for (const u of uses) {
    evidence.push({ s0: s, agent: u.agent, cite_id: u.cite_id, why: u.why });
    s += uses.length > 5 ? 0.9 : 1.3;
  }
  const drawerCue = uses.length ? { s0: ctx.s + 3.6, s1: Math.max(s, ctx.s + 3.6 + 5.0), cite_id: pickDrawerCite(model, uses) } : null;
  if (drawerCue) {
    const c = model.citations[drawerCue.cite_id];
    captions.push({ s0: ctx.s + 3.2, s1: drawerCue.s1, text: `Beams run from each agent to the exact source it cited. Open: ${c.title}, ${c.article}.`, tone: 'act' });
  }
  s = Math.max(s, (drawerCue?.s1 ?? s)) + 0.4;
  const helixAt = s;
  cam.push({ s: helixAt, shot: 'helix' });
  const verifyAt = helixAt + 1.6;
  const verifyDur = 3.4;
  captions.push({ s0: helixAt, s1: verifyAt + verifyDur + 2.2, text: 'The audit chain: every event is hash-linked. Verification runs live in this browser (WebCrypto SHA-256).', tone: 'act' });
  ctx.segs.push({ s0: ctx.s, s1: verifyAt + verifyDur + 2.4, act: 3, run: 'baseline', kind: 'evidence', t0: H, t1: H, ev: -1 });
  ctx.s = verifyAt + verifyDur + 2.4;

  // Act IV — rewind & reform
  const rewindAt = ctx.s;
  acts.push({ act: 4, s: ctx.s, label: 'Rewind & Reform' });
  cam.push({ s: ctx.s, shot: 'rewind' });
  const REW = 5.5;
  ctx.segs.push({ s0: ctx.s, s1: ctx.s + REW, act: 4, run: 'baseline', kind: 'rewind', t0: H, t1: t0, ev: -1 });
  captions.push({ s0: ctx.s, s1: ctx.s + REW, text: 'Rewind. Same night, same crowd — now with the reform pack in force.', tone: 'act' });
  ctx.s += REW;
  const inscribeAt = ctx.s;
  const INS = model.reform ? 3.4 : 0;
  if (model.reform) {
    ctx.segs.push({ s0: ctx.s, s1: ctx.s + INS, act: 4, run: 'reform', kind: 'inscribe', t0: t0, t1: t0, ev: -1 });
    const clauses = model.reformClauses.map((c) => [c.id, c.title].filter(Boolean).join(' ')).join(' · ');
    captions.push({ s0: ctx.s, s1: ctx.s + INS, text: `Reform pack inscribed on the policy shield${clauses ? ': ' + clauses : ''}.`, tone: 'act' });
    ctx.s += INS;
  }
  const reformAt = ctx.s;
  if (model.reform) {
    cam.push({ s: reformAt, shot: 'reform' });
    const outR = { evS: evS.reform, evD: evD.reform, kinds: beatKind.reform };
    scheduleRun(ctx, model, model.reform, 4, 34, outR, captions, gapCards, cam, markers, t0, H, 0.55);
  }
  const finaleAt = ctx.s;
  cam.push({ s: finaleAt, shot: 'finale' });
  const FIN = 13;
  ctx.segs.push({ s0: ctx.s, s1: ctx.s + FIN, act: 4, run: model.reform ? 'reform' : 'baseline', kind: 'finale', t0: H, t1: H, ev: -1 });
  ctx.s += FIN;

  // Clean camera keys: sort, drop keys closer than 1.0s (keep the later one)
  cam.sort((a, b) => a.s - b.s);
  const camClean: CamKey[] = [];
  for (const k of cam) {
    const last = camClean[camClean.length - 1];
    if (last && k.s - last.s < 1.0) camClean[camClean.length - 1] = k;
    else camClean.push(k);
  }

  const slowWindows: Story['slowWindows'] = [];
  (['baseline', 'reform'] as RunKind[]).forEach((rk) => {
    beatKind[rk].forEach((k, i) => {
      if (k === 'magic' || k === 'block') {
        const T = timingFor(k);
        if (T.slowEnd > T.slowStart) slowWindows.push({ a: evS[rk][i] + T.slowStart, b: evS[rk][i] + T.slowEnd, rate: T.slowRate });
      }
    });
  });
  slowWindows.sort((x, y) => x.a - y.a);

  return {
    segments: ctx.segs,
    duration: ctx.s,
    slowWindows,
    acts,
    evS,
    evD,
    beatKind,
    captions,
    gapCards,
    evidence,
    drawerCue,
    verifyAt,
    verifyDur,
    helixAt,
    cam: camClean,
    finaleAt,
    rewindAt,
    inscribeAt,
    reformAt,
    act3At,
    markers,
  };
}

function pickDrawerCite(model: Model, uses: { cite_id: string }[]): string {
  // Prefer the first global example of the first magic-moment gap (the story's hero evidence).
  const ev = model.baseline.firstMagicEv;
  if (ev >= 0) {
    const g = model.gapsById.get(String(model.baseline.events[ev].payload?.gap_id ?? ''));
    const c = g?.global_examples.find((x) => model.citations[x.cite_id]);
    if (c) return c.cite_id;
  }
  return uses[0].cite_id;
}

// ---------------------------------------------------------------------------
// Frame evaluation

export interface Cursor {
  run: RunKind;
  simT: number;
  done: number; // events [0, done) fully completed
  active: number; // event index whose beat is in progress, or -1
  u: number; // seconds into the active beat
  d: number; // active beat duration
  kind: BeatKind | null;
}

export interface Frame {
  s: number;
  segIndex: number;
  seg: Segment;
  act: Act;
  run: RunKind;
  simT: number;
  cursor: Cursor;
  rewindK: number; // 0..1 progress of the rewind segment (0 when not rewinding)
  slow: number; // current time-rate multiplier (1 normal, <1 slow-mo)
}

export function segmentAt(story: Story, s: number): number {
  const segs = story.segments;
  if (s <= segs[0].s0) return 0;
  let lo = 0;
  let hi = segs.length - 1;
  if (s >= segs[hi].s0) return hi;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (segs[mid].s0 <= s) lo = mid;
    else hi = mid;
  }
  return lo;
}

function countDoneBySimT(model: Model, run: RunKind, simT: number): number {
  const r = run === 'reform' ? model.reform : model.baseline;
  if (!r) return 0;
  let lo = 0;
  let hi = r.events.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (r.events[mid].t <= simT + 1e-9) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

function doneByS(story: Story, run: RunKind, s: number): number {
  const arr = story.evS[run];
  let lo = 0;
  let hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (arr[mid] + story.evD[run][mid] <= s) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

export function frameAt(model: Model, story: Story, sIn: number): Frame {
  const s = Math.max(0, Math.min(story.duration, sIn));
  const segIndex = segmentAt(story, s);
  const seg = story.segments[segIndex];
  const len = Math.max(1e-6, seg.s1 - seg.s0);
  const k = Math.max(0, Math.min(1, (s - seg.s0) / len));
  let simT = seg.t0 + (seg.t1 - seg.t0) * k;
  let rewindK = 0;
  let slow = 1;
  const run = seg.run;
  let cursor: Cursor;
  if (seg.kind === 'rewind') {
    // ease the sweep so it starts and lands gently
    const e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
    simT = seg.t0 + (seg.t1 - seg.t0) * e;
    rewindK = k;
    cursor = { run, simT, done: countDoneBySimT(model, run, simT), active: -1, u: 0, d: 0, kind: null };
  } else if (seg.kind === 'cold' || seg.kind === 'city' || seg.kind === 'inscribe') {
    cursor = { run, simT, done: seg.kind === 'inscribe' ? 0 : 0, active: -1, u: 0, d: 0, kind: null };
  } else if (seg.kind === 'evidence' || seg.kind === 'finale') {
    const r = run === 'reform' ? model.reform : model.baseline;
    cursor = { run, simT, done: r ? r.events.length : 0, active: -1, u: 0, d: 0, kind: null };
  } else if (seg.kind === 'beat') {
    const u = s - seg.s0;
    cursor = { run, simT, done: seg.ev, active: seg.ev, u, d: len, kind: seg.beat ?? null };
    if (seg.beat === 'magic' || seg.beat === 'block') {
      const T = timingFor(seg.beat);
      if (u > T.slowStart && u < T.slowEnd) slow = T.slowRate;
    }
  } else {
    cursor = { run, simT, done: doneByS(story, run, s), active: -1, u: 0, d: 0, kind: null };
  }
  return { s, segIndex, seg, act: seg.act, run, simT, cursor, rewindK, slow };
}

export function runOf(model: Model, run: RunKind): RunModel {
  return run === 'reform' && model.reform ? model.reform : model.baseline;
}

/** Index of the act whose start is <= s. */
export function actAt(story: Story, s: number): Act {
  let a: Act = 0;
  for (const x of story.acts) if (x.s <= s + 1e-6) a = x.act;
  return a;
}

export function activeCue<T extends { s0: number; s1: number }>(cues: T[], s: number): T | null {
  let found: T | null = null;
  for (const c of cues) {
    if (c.s0 <= s && s < c.s1) found = c;
    if (c.s0 > s) break;
  }
  return found;
}

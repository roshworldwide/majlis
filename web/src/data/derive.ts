/**
 * Derived, render-ready model built once from replay.json.
 * Nothing here invents content: every value comes from the replay.
 */
import type { Agent, Citation, Fact, Gap, Kpis, Replay, ReplayEvent } from './replay.schema';

export interface MessageInfo {
  ev: number; // index of the message event in run.events
  id: string;
  from: string;
  to: string;
  fromIdx: number;
  toIdx: number;
  sent: number;
  deliver: number;
  legal: boolean;
  informal: boolean;
  status: string;
  facts: string[];
  content: string;
}

export interface BeliefStep {
  ev: number;
  conf: number;
  prev: number;
}

export interface RunModel {
  id: string;
  kind: 'baseline' | 'reform';
  events: ReplayEvent[];
  kpis: Kpis;
  gaps: Gap[];
  messages: MessageInfo[];
  /** beliefs[agentIdx][factIdx] = steps sorted by event index */
  beliefs: BeliefStep[][][];
  restoreT: number | null;
  restoreEv: number;
  firstMagicEv: number; // first gate_block with a gap_id, -1 if none
  blocks: number[]; // indices of gate_block events
  flags: number[];
}

export interface CiteUse {
  agent: string | null;
  cite_id: string;
  t: number;
  why: string;
}

export interface Model {
  replay: Replay;
  agents: Agent[];
  agentIdx: Map<string, number>;
  facts: Fact[];
  factIdx: Map<string, number>;
  horizon: number;
  t0: number;
  tCityStart: number;
  baseline: RunModel;
  reform: RunModel | null;
  gapsById: Map<string, Gap>;
  citations: Record<string, Citation>;
  citeUses: CiteUse[];
  cellsTotal: number;
  kpiMax: { asleep: number };
  reformClauses: { id: string; title: string }[];
}

export const KNOW_THRESHOLD = 0.7;

function sortEvents(evs: ReplayEvent[]): ReplayEvent[] {
  return evs
    .map((e, i) => ({ e, i }))
    .sort((a, b) => a.e.t - b.e.t || (a.e.seq ?? a.i) - (b.e.seq ?? b.i) || a.i - b.i)
    .map((x) => x.e);
}

export function seriesAt(series: [number, number][] | undefined, t: number, fallback = 0): number {
  if (!series || series.length === 0) return fallback;
  if (t <= series[0][0]) return series[0][1];
  const last = series[series.length - 1];
  if (t >= last[0]) return last[1];
  let lo = 0;
  let hi = series.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (series[mid][0] <= t) lo = mid;
    else hi = mid;
  }
  const [ta, va] = series[lo];
  const [tb, vb] = series[hi];
  const k = tb === ta ? 0 : (t - ta) / (tb - ta);
  return va + (vb - va) * k;
}

function buildRun(
  kind: 'baseline' | 'reform',
  id: string,
  rawEvents: ReplayEvent[],
  kpis: Kpis,
  gaps: Gap[],
  agentIdx: Map<string, number>,
  factIdx: Map<string, number>,
  nAgents: number,
  nFacts: number,
): RunModel {
  const events = sortEvents(rawEvents || []);
  const messages: MessageInfo[] = [];
  const beliefs: BeliefStep[][][] = Array.from({ length: nAgents }, () => Array.from({ length: nFacts }, () => []));
  let restoreT: number | null = null;
  let restoreEv = -1;
  let firstMagicEv = -1;
  const blocks: number[] = [];
  const flags: number[] = [];
  events.forEach((e, i) => {
    const p = e.payload || {};
    if (e.type === 'message') {
      const from = String(p.from ?? e.agent ?? '');
      const to = String(p.to ?? '');
      const fromIdx = agentIdx.get(from) ?? -1;
      const toIdx = agentIdx.get(to) ?? -1;
      const sent = typeof p.sent_t === 'number' ? p.sent_t : e.t;
      const deliver = typeof p.deliver_t === 'number' ? p.deliver_t : sent;
      messages.push({
        ev: i,
        id: String(p.msg_id ?? `MSG@${i}`),
        from,
        to,
        fromIdx,
        toIdx,
        sent,
        deliver: Math.max(deliver, sent),
        legal: p.legal !== false && p.route !== 'informal',
        informal: p.route === 'informal' || p.legal === false,
        status: String(p.status ?? ''),
        facts: Array.isArray(p.facts) ? p.facts.map(String) : [],
        content: String(p.content ?? ''),
      });
    } else if (e.type === 'belief') {
      const a = agentIdx.get(String(e.agent ?? ''));
      const f = factIdx.get(String(p.fact ?? ''));
      if (a !== undefined && f !== undefined) {
        const conf = Number(p.confidence ?? 0);
        const list = beliefs[a][f];
        const prev = typeof p.prev === 'number' ? p.prev : list.length ? list[list.length - 1].conf : 0;
        list.push({ ev: i, conf, prev });
      }
    } else if (e.type === 'kpi' && p.event === 'service_restored') {
      if (restoreT === null) {
        restoreT = e.t;
        restoreEv = i;
      }
    } else if (e.type === 'gate_block') {
      blocks.push(i);
      if (firstMagicEv < 0 && p.gap_id) firstMagicEv = i;
    } else if (e.type === 'gate_flag') {
      flags.push(i);
    }
  });
  return { id, kind, events, kpis, gaps: gaps || [], messages, beliefs, restoreT, restoreEv, firstMagicEv, blocks, flags };
}

export function buildModel(replay: Replay): Model {
  const agents = replay.agents;
  const agentIdx = new Map(agents.map((a, i) => [a.id, i] as const));
  const facts = replay.facts;
  const factIdx = new Map(facts.map((f, i) => [f.id, i] as const));
  const baseline = buildRun(
    'baseline',
    replay.meta.run_id,
    replay.timeline,
    replay.kpis,
    replay.gaps,
    agentIdx,
    factIdx,
    agents.length,
    facts.length,
  );
  const r = replay.compare?.reform;
  const reform = r
    ? buildRun('reform', r.run_id, r.timeline, r.kpis, r.gaps, agentIdx, factIdx, agents.length, facts.length)
    : null;
  const lastT = baseline.events.length ? baseline.events[baseline.events.length - 1].t : 0;
  const horizon = Math.max(replay.meta.horizon_min ?? 0, lastT, 1);
  const t0 = baseline.events.length ? baseline.events[0].t : 0;
  const firstKpiT = replay.kpis.cells_asleep_pct?.[0]?.[0] ?? t0 - 10;
  const tCityStart = Math.min(t0, Math.max(firstKpiT, t0 - 10));
  const gapsById = new Map<string, Gap>();
  for (const g of replay.gaps) gapsById.set(g.gap_id, g);
  if (r) for (const g of r.gaps) if (!gapsById.has(g.gap_id)) gapsById.set(g.gap_id, g);

  // Evidence actually used in the run, in timeline order (agent -> cited chunk).
  const citations = replay.citations || {};
  const seen = new Set<string>();
  const citeUses: CiteUse[] = [];
  const push = (agent: string | null, cite: unknown, t: number, why: string) => {
    if (typeof cite !== 'string' || !citations[cite]) return;
    const key = `${agent}|${cite}`;
    if (seen.has(key)) return;
    seen.add(key);
    citeUses.push({ agent, cite_id: cite, t, why });
  };
  for (const e of baseline.events) {
    const p = e.payload || {};
    if (e.type === 'gate_pass' && Array.isArray(p.cite_ids)) p.cite_ids.forEach((c: unknown) => push(e.agent, c, e.t, 'passed the policy gate'));
    if (e.type === 'action' && Array.isArray(p.cite_ids)) p.cite_ids.forEach((c: unknown) => push(e.agent, c, e.t, 'action legal basis'));
    if (e.type === 'adviser_qa') {
      const ids = [...(Array.isArray(p.cite_ids) ? p.cite_ids : []), ...(Array.isArray(p.global_cite_ids) ? p.global_cite_ids : [])];
      ids.forEach((c: unknown) => push(e.agent, c, e.t, 'cited by the Adviser'));
    }
    if (e.type === 'gap') {
      const g = gapsById.get(String(p.gap_id ?? ''));
      g?.global_examples.forEach((x) => push(e.agent, x.cite_id, e.t, `global example for ${g.gap_id}`));
    }
  }
  for (const a of agents) for (const m of a.mandates) for (const c of m.citations) push(a.id, c, 0, `mandate ${m.id}`);

  let asleepMax = 0;
  for (const [, v] of replay.kpis.cells_asleep_pct || []) asleepMax = Math.max(asleepMax, v);

  // Optional reform clauses (rendered as inscriptions if the engine provides them).
  const clausesRaw: unknown =
    (r as Record<string, unknown> | undefined)?.clauses ??
    (r as Record<string, unknown> | undefined)?.reform_pack ??
    (replay.compare as Record<string, unknown>)?.reform_clauses ??
    (replay.meta as Record<string, unknown>)?.reform_clauses;
  const reformClauses: { id: string; title: string }[] = [];
  if (Array.isArray(clausesRaw)) {
    for (const c of clausesRaw) {
      if (c && typeof c === 'object') {
        const o = c as Record<string, unknown>;
        reformClauses.push({ id: String(o.id ?? o.rule_id ?? ''), title: String(o.title ?? o.name ?? o.label ?? '') });
      } else if (typeof c === 'string') reformClauses.push({ id: c, title: '' });
    }
  }

  return {
    replay,
    agents,
    agentIdx,
    facts,
    factIdx,
    horizon,
    t0,
    tCityStart,
    baseline,
    reform,
    gapsById,
    citations,
    citeUses,
    cellsTotal: Math.max(60, Math.min(4000, Math.round(replay.meta.cells_total ?? 1500))),
    kpiMax: { asleep: Math.max(asleepMax, 1) },
    reformClauses,
  };
}

/** Confidence of agent a in fact f, given that events [0, done) have completed. */
export function beliefAt(run: RunModel, a: number, f: number, done: number, activeEv = -1, activeK = 0): number {
  const steps = run.beliefs[a]?.[f];
  if (!steps || steps.length === 0) return 0;
  let val = 0;
  for (let i = 0; i < steps.length; i++) {
    const st = steps[i];
    if (st.ev < done) val = st.conf;
    else if (st.ev === activeEv) {
      val = st.prev + (st.conf - st.prev) * activeK;
      break;
    } else break;
  }
  return val;
}

export function agentName(model: Model, id: string | null | undefined, lang: 'en' | 'ar' = 'en'): string {
  if (!id) return '—';
  const i = model.agentIdx.get(id);
  if (i === undefined) return id;
  const a = model.agents[i];
  return lang === 'ar' ? a.name_ar : a.name;
}

export function factLabel(model: Model, id: string, lang: 'en' | 'ar' = 'en'): string {
  const i = model.factIdx.get(id);
  if (i === undefined) return id;
  return lang === 'ar' ? model.facts[i].label_ar : model.facts[i].label;
}

export function clockLabel(t: number): string {
  // T+0 = 22:30 (fictional)
  const base = 22 * 60 + 30;
  const m = Math.round(base + t);
  const hh = Math.floor((((m / 60) % 24) + 24) % 24);
  const mm = ((m % 60) + 60) % 60;
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
}

export function tLabel(t: number): string {
  const r = Math.round(t);
  return r >= 0 ? `T+${r}` : `T−${Math.abs(r)}`;
}

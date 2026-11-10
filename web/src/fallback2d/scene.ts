/**
 * Imperative SVG + canvas renderer for the 2D Experience.
 * Static geometry is built once per (model, story); every frame only mutates attributes.
 * Pure function of story time `s` (plus the real-time manual "Verify chain" animation).
 */
import type { Model, RunModel, MessageInfo } from '../data/derive';
import { beliefAt, seriesAt, KNOW_THRESHOLD } from '../data/derive';
import type { Story, Frame, BeatKind } from '../data/story';
import { frameAt, runOf, impactClock, timingFor } from '../data/story';
import { ambientTime } from '../state/clock';
import { useStore } from '../state/store';
import type { KbPoints } from '../data/load';
import * as G from './geometry';

const NS = 'http://www.w3.org/2000/svg';
const CYAN = '#4CC9F0';
const GOLD = '#E9C46A';
const GREEN = '#2EE6A6';
const RED = '#FF4D6D';
const VIOLET = '#9D7CFF';
const AMBER = '#F4B860';
const NEUTRAL = '#8A97AD';
const CLUSTER_COLORS = [GOLD, CYAN, VIOLET, NEUTRAL];
const CLUSTER_BY_NAME: Record<string, string> = { uae: GOLD, global: CYAN, itu: VIOLET, other: NEUTRAL };

type Attrs = Record<string, string | number>;

function el<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Attrs, parent?: Element): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, tag) as SVGElementTagNameMap[K];
  for (const k in attrs) e.setAttribute(k, String(attrs[k]));
  if (parent) parent.appendChild(e);
  return e;
}

function set(e: Element, k: string, v: string | number): void {
  const val = typeof v === 'number' ? (Number.isFinite(v) ? v.toFixed(2) : '0') : v;
  const cache = ((e as unknown as { __a?: Record<string, string> }).__a ??= {});
  if (cache[k] === val) return;
  cache[k] = val;
  e.setAttribute(k, val);
}

function show(e: Element, on: boolean): void {
  const want = on ? '' : 'none';
  const cur = (e as SVGElement).style.display;
  if (cur !== want) (e as SVGElement).style.display = want;
}

function shortName(name: string, max = 22): string {
  if (name.length <= max) return name;
  const cut = name.slice(0, max);
  const sp = cut.lastIndexOf(' ');
  return (sp > 8 ? cut.slice(0, sp) : cut).replace(/[\s,&(]+$/, '') + '…';
}

function rgba(hex: string, a: number): string {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h.padEnd(6, '0');
  const n = parseInt(full.slice(0, 6), 16);
  if (Number.isNaN(n)) return `rgba(76,201,240,${a.toFixed(3)})`;
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a.toFixed(3)})`;
}

function safeColor(c: string | undefined): string {
  return typeof c === 'string' && /^#[0-9a-fA-F]{3,8}$/.test(c) ? c : CYAN;
}

interface AgentEls {
  g: SVGGElement;
  pulse: SVGCircleElement;
  aura: SVGPathElement[];
  node: SVGCircleElement;
  fog: SVGCircleElement;
  id: SVGTextElement;
  label: SVGTextElement;
  pos: G.Pt;
  color: string;
}

interface MsgEls {
  m: MessageInfo;
  run: 'baseline' | 'reform';
  route: SVGPathElement;
  pulse: SVGCircleElement;
  at: (t: number) => G.Pt;
  len: number;
}

interface BeamEls {
  line: SVGLineElement;
  hit: SVGLineElement;
  star: SVGCircleElement;
  cite: string;
  agentIdx: number;
  s0: number;
  color: string;
}

export interface Scene {
  requestRender: () => void;
  dispose: () => void;
}

export function createScene(
  host: HTMLDivElement,
  svgBack: SVGSVGElement,
  svgFront: SVGSVGElement,
  canvas: HTMLCanvasElement,
  model: Model,
  story: Story,
  reduced: boolean,
): Scene {
  svgBack.replaceChildren();
  svgFront.replaceChildren();
  const disposers: (() => void)[] = [];
  const nAgents = model.agents.length;
  const nFacts = Math.max(1, model.facts.length);

  // ---------------------------------------------------------------- back: city
  const defsB = el('defs', {}, svgBack);
  const heatGrad = el('radialGradient', { id: 's2d-heat', cx: '50%', cy: '50%', r: '50%' }, defsB);
  el('stop', { offset: '0%', 'stop-color': GOLD, 'stop-opacity': 0.55 }, heatGrad);
  el('stop', { offset: '55%', 'stop-color': '#C9A24A', 'stop-opacity': 0.16 }, heatGrad);
  el('stop', { offset: '100%', 'stop-color': '#C9A24A', 'stop-opacity': 0 }, heatGrad);
  const warpB = makeWarp(defsB, 's2d-warp-b');

  const cityRoot = el('g', {}, svgBack);
  const city = el('g', { class: 's2d-city' }, cityRoot);
  const cityGeom = G.buildCity(Math.min(model.cellsTotal, 320));
  const heat = el('ellipse', { cx: G.DOWNTOWN.x, cy: G.DOWNTOWN.y, rx: 210, ry: 150, fill: 'url(#s2d-heat)', opacity: 0.3 }, city);
  const cellsG = el('g', { class: 's2d-cells' }, city);
  const cellEls: SVGPolygonElement[] = [];
  const cellState: number[] = [];
  const ghostState: number[] = [];
  cityGeom.cells.forEach((c, i) => {
    const load = 0.26 + 0.42 * Math.pow(1 - c.dist, 1.3) + 0.14 * G.hash(i * 13 + 5);
    const p = el('polygon', { points: G.hexPoints(cityGeom.r * 0.8, c.x, c.y), fill: 'rgb(76,201,240)', 'fill-opacity': load.toFixed(3), stroke: 'none' }, cellsG);
    cellEls.push(p);
    cellState.push(-1);
    ghostState.push(-1);
  });
  // palette: awake cyan → asleep slate
  const PAL: string[] = [];
  for (let q = 0; q <= 12; q++) {
    const k = q / 12;
    const r = Math.round(G.lerp(76, 62, k));
    const g = Math.round(G.lerp(201, 76, k));
    const b = Math.round(G.lerp(240, 104, k));
    PAL.push(`rgb(${r},${g},${b})`);
  }
  const relight = el('circle', { cx: G.DOWNTOWN.x, cy: G.DOWNTOWN.y, r: 10, fill: 'none', stroke: CYAN, 'stroke-width': 3, opacity: 0 }, city);
  // crowd + ambulance nodes, emergency-call arcs
  const ecArc: G.Quad = {
    p0: { x: G.DOWNTOWN.x, y: G.DOWNTOWN.y },
    p1: { x: (G.DOWNTOWN.x + G.AMBULANCE.x) / 2, y: Math.min(G.DOWNTOWN.y, G.AMBULANCE.y) - 150 },
    p2: { x: G.AMBULANCE.x, y: G.AMBULANCE.y },
  };
  el('path', { d: G.quadPath(ecArc), fill: 'none', stroke: RED, 'stroke-opacity': 0.12, 'stroke-width': 1.2, 'stroke-dasharray': '2 6' }, city);
  el('circle', { cx: G.DOWNTOWN.x, cy: G.DOWNTOWN.y, r: 7, fill: GOLD, opacity: 0.85 }, city);
  const amb = el('g', { transform: `translate(${G.AMBULANCE.x},${G.AMBULANCE.y})` }, city);
  el('circle', { r: 11, fill: 'rgba(255,77,109,0.14)', stroke: RED, 'stroke-width': 1.5 }, amb);
  el('path', { d: 'M-5,0 H5 M0,-5 V5', stroke: RED, 'stroke-width': 2.2, 'stroke-linecap': 'round' }, amb);
  const P = reduced ? 10 : 30;
  const ecEls: SVGCircleElement[] = [];
  for (let i = 0; i < P; i++) ecEls.push(el('circle', { r: 2.6, fill: RED, opacity: 0 }, city));

  // ---------------------------------------------------------------- front
  const defsF = el('defs', {}, svgFront);
  const fogGrad = el('radialGradient', { id: 's2d-fog', cx: '50%', cy: '50%', r: '50%' }, defsF);
  el('stop', { offset: '0%', 'stop-color': '#8A9BB8', 'stop-opacity': 0.34 }, fogGrad);
  el('stop', { offset: '60%', 'stop-color': '#5D6F8E', 'stop-opacity': 0.2 }, fogGrad);
  el('stop', { offset: '100%', 'stop-color': '#0A1222', 'stop-opacity': 0 }, fogGrad);
  const shieldGrad = el('radialGradient', { id: 's2d-shield', cx: '50%', cy: '45%', r: '60%' }, defsF);
  el('stop', { offset: '0%', 'stop-color': CYAN, 'stop-opacity': 0.02 }, shieldGrad);
  el('stop', { offset: '80%', 'stop-color': CYAN, 'stop-opacity': 0.08 }, shieldGrad);
  el('stop', { offset: '100%', 'stop-color': CYAN, 'stop-opacity': 0.22 }, shieldGrad);
  const sweepGrad = el('linearGradient', { id: 's2d-sweep', x1: '0', x2: '1', y1: '0', y2: '0' }, defsF);
  el('stop', { offset: '0%', 'stop-color': CYAN, 'stop-opacity': 0 }, sweepGrad);
  el('stop', { offset: '50%', 'stop-color': CYAN, 'stop-opacity': 0.28 }, sweepGrad);
  el('stop', { offset: '100%', 'stop-color': CYAN, 'stop-opacity': 0 }, sweepGrad);
  const warpF = makeWarp(defsF, 's2d-warp-f');

  const frontRoot = el('g', {}, svgFront);
  const council = el('g', { class: 's2d-council' }, frontRoot);
  // chamber floor ring
  el('ellipse', { cx: 0, cy: 0, rx: G.COUNCIL_R + 34, ry: (G.COUNCIL_R + 34) * G.SQUASH, fill: 'rgba(10,18,34,0.55)', stroke: GOLD, 'stroke-opacity': 0.22, 'stroke-width': 1 }, council);
  el('ellipse', { cx: 0, cy: 0, rx: G.COUNCIL_R, ry: G.COUNCIL_R * G.SQUASH, fill: 'none', stroke: GOLD, 'stroke-opacity': 0.12, 'stroke-width': 1, 'stroke-dasharray': '2 5' }, council);

  // channels (static)
  const chanG = el('g', { class: 's2d-channels' }, council);
  const missingEls: SVGPathElement[] = [];
  const drawn = new Set<string>();
  const legalCurveFor = new Map<string, G.Quad>();
  for (const ch of model.replay.channels || []) {
    const ia = model.agentIdx.get(ch.from);
    const ib = model.agentIdx.get(ch.to);
    if (ia === undefined || ib === undefined || ia === ib) continue;
    const key = `${Math.min(ia, ib)}-${Math.max(ia, ib)}-${ch.legal ? 1 : 0}`;
    const q = G.channelCurve(ia, ib, nAgents);
    if (ch.legal) legalCurveFor.set(`${ia}>${ib}`, q);
    if (drawn.has(key)) continue;
    drawn.add(key);
    if (ch.legal) {
      el('path', { d: G.quadPath(q), fill: 'none', stroke: CYAN, 'stroke-opacity': 0.3, 'stroke-width': 1.4 }, chanG);
    } else {
      const a = el('path', { d: G.quadSubPath(q, 0, 0.4), fill: 'none', stroke: RED, 'stroke-opacity': 0.55, 'stroke-width': 1.4, 'stroke-dasharray': '3 6' }, chanG);
      const b = el('path', { d: G.quadSubPath(q, 0.6, 1), fill: 'none', stroke: RED, 'stroke-opacity': 0.55, 'stroke-width': 1.4, 'stroke-dasharray': '3 6' }, chanG);
      const mid = G.quadAt(q, 0.5);
      const x = el('path', { d: `M${mid.x - 4},${mid.y - 4} L${mid.x + 4},${mid.y + 4} M${mid.x + 4},${mid.y - 4} L${mid.x - 4},${mid.y + 4}`, stroke: RED, 'stroke-opacity': 0.7, 'stroke-width': 1.4 }, chanG);
      missingEls.push(a, b, x);
    }
  }

  // message routes + pulses (both runs)
  const routesG = el('g', { class: 's2d-routes' }, council);
  const msgEls: MsgEls[] = [];
  const addMsgs = (run: RunModel | null) => {
    if (!run) return;
    for (const m of run.messages) {
      if (m.fromIdx < 0 || m.toIdx < 0 || m.fromIdx === m.toIdx) continue;
      let at: (t: number) => G.Pt;
      let d: string;
      if (m.informal) {
        const c = G.detourCurve(m.fromIdx, m.toIdx, nAgents);
        at = (t) => G.cubicAt(c, t);
        d = G.cubicPath(c);
      } else {
        const q = legalCurveFor.get(`${m.fromIdx}>${m.toIdx}`) ?? G.channelCurve(m.fromIdx, m.toIdx, nAgents);
        at = (t) => G.quadAt(q, t);
        d = G.quadPath(q);
      }
      const len = G.curveLength(at);
      const color = m.informal ? AMBER : CYAN;
      const route = el('path', { d, fill: 'none', stroke: color, 'stroke-width': m.informal ? 2 : 2.4, 'stroke-linecap': 'round', 'stroke-dasharray': `0 ${len + 1}`, opacity: 0 }, routesG);
      const pulse = el('circle', { r: 5.5, fill: color, opacity: 0 }, routesG);
      msgEls.push({ m, run: run.kind, route, pulse, at, len });
    }
  };
  addMsgs(model.baseline);
  addMsgs(model.reform);

  // shield
  const shieldG = el('g', { class: 's2d-shield' }, council);
  const shieldPoly = el('polygon', { points: G.hexPoints(G.SHIELD_R), fill: 'url(#s2d-shield)', stroke: CYAN, 'stroke-width': 2, 'stroke-opacity': 0.7 }, shieldG);
  el('polygon', { points: G.hexPoints(G.SHIELD_R * 0.62), fill: 'none', stroke: CYAN, 'stroke-width': 1, 'stroke-opacity': 0.25 }, shieldG);
  const shieldText = el('text', { x: 0, y: 5, 'text-anchor': 'middle', class: 's2d-shield-label' }, shieldG);
  shieldText.textContent = 'P';
  const redPulse = el('polygon', { points: G.hexPoints(G.SHIELD_R), fill: RED, opacity: 0 }, shieldG);
  const goldRing = el('polygon', { points: G.hexPoints(G.SHIELD_R + 9), fill: 'none', stroke: GOLD, 'stroke-width': 2, opacity: 0 }, shieldG);
  const flagRing = el('polygon', { points: G.hexPoints(G.SHIELD_R), fill: 'none', stroke: AMBER, 'stroke-width': 2.5, opacity: 0 }, shieldG);
  const tick = el('path', { d: 'M-14,2 L-4,12 L16,-10', fill: 'none', stroke: GREEN, 'stroke-width': 4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', opacity: 0 }, shieldG);
  const crackEls: { p: SVGPathElement; len: number }[] = [];
  for (let k = 0; k < 6; k++) crackEls.push({ p: el('path', { d: 'M0,0', fill: 'none', stroke: '#FFF1F4', 'stroke-width': 2, 'stroke-linecap': 'round', opacity: 0 }, shieldG), len: 1 });
  const ripple = el('circle', { r: 0, fill: 'none', stroke: RED, 'stroke-width': 2.5, opacity: 0 }, shieldG);
  const flash = el('circle', { r: 0, fill: '#FFE3E8', opacity: 0 }, shieldG);
  const inscG = el('g', { class: 's2d-inscriptions' }, shieldG);
  const inscEls: SVGTextElement[] = [];
  const nCl = model.reformClauses.length;
  model.reformClauses.forEach((c) => {
    const t = el('text', { 'text-anchor': 'middle', class: 's2d-inscription', opacity: 0 }, inscG);
    t.textContent = c.id || shortName(c.title, 16);
    inscEls.push(t);
  });
  let crackFor = -2;

  // projectile
  const projTrail = el('line', { x1: 0, y1: 0, x2: 0, y2: 0, stroke: RED, 'stroke-width': 3, 'stroke-linecap': 'round', opacity: 0 }, council);
  const proj = el('circle', { r: 7, fill: '#FFE3E8', stroke: RED, 'stroke-width': 3, opacity: 0 }, council);
  const qaLine = el('line', { x1: 0, y1: 0, x2: 0, y2: 0, stroke: CYAN, 'stroke-width': 1.6, 'stroke-dasharray': '4 5', opacity: 0 }, council);

  // agents
  const agentsG = el('g', { class: 's2d-agents' }, council);
  const agentEls: AgentEls[] = [];
  const selRing = el('circle', { r: G.AURA_R + 8, fill: 'none', stroke: GOLD, 'stroke-width': 2, opacity: 0 }, council);
  model.agents.forEach((a, i) => {
    const pos = G.nodePos(i, nAgents);
    const color = safeColor(a.color);
    const g = el('g', { transform: `translate(${pos.x.toFixed(1)},${pos.y.toFixed(1)})`, class: 's2d-agent', role: 'button', tabindex: 0, 'aria-label': `${a.name}, modelled on ${a.modelled_on}` }, agentsG);
    const pulse = el('circle', { r: G.NODE_R, fill: 'none', stroke: CYAN, 'stroke-width': 2, opacity: 0 }, g);
    const aura: SVGPathElement[] = [];
    const gapA = nFacts > 1 ? 0.12 : 0;
    for (let f = 0; f < nFacts; f++) {
      const a0 = -Math.PI / 2 + (f * 2 * Math.PI) / nFacts + gapA / 2;
      const a1 = -Math.PI / 2 + ((f + 1) * 2 * Math.PI) / nFacts - gapA / 2;
      aura.push(el('path', { d: nFacts === 1 ? G.arcPath(0, 0, G.AURA_R, -Math.PI / 2, Math.PI * 1.499) : G.arcPath(0, 0, G.AURA_R, a0, a1), fill: 'none', stroke: '#3A4A66', 'stroke-width': 4, 'stroke-linecap': 'butt', opacity: 0.4 }, g));
    }
    el('circle', { r: G.NODE_R + 3, fill: rgba(color, 0.1) }, g);
    const node = el('circle', { r: G.NODE_R, fill: '#0B1424', stroke: color, 'stroke-width': 2.2 }, g);
    const id = el('text', { x: 0, y: 4.5, 'text-anchor': 'middle', class: 's2d-agent-id', fill: color }, g);
    id.textContent = a.id;
    const fog = el('circle', { r: G.AURA_R + 10, fill: 'url(#s2d-fog)', opacity: 0, 'pointer-events': 'none' }, g);
    const ang = G.nodeAngle(i, nAgents);
    const cx = Math.cos(ang);
    const sy = Math.sin(ang);
    const anchor = cx > 0.35 ? 'start' : cx < -0.35 ? 'end' : 'middle';
    const lx = cx * (G.AURA_R + 12);
    const ly = sy > 0.35 ? G.AURA_R + 22 : sy < -0.35 ? -(G.AURA_R + 26) : 5;
    const label = el('text', { x: anchor === 'middle' ? 0 : lx, y: anchor === 'middle' ? ly : 5, 'text-anchor': anchor, class: 's2d-agent-label' }, g);
    label.textContent = shortName(a.name);
    const onAct = () => useStore.getState().select({ kind: 'agent', id: a.id });
    const onKey = (e: Event) => {
      const k = (e as KeyboardEvent).key;
      if (k === 'Enter' || k === ' ') {
        e.preventDefault();
        e.stopPropagation();
        onAct();
      }
    };
    g.addEventListener('click', onAct);
    g.addEventListener('keydown', onKey);
    disposers.push(() => {
      g.removeEventListener('click', onAct);
      g.removeEventListener('keydown', onKey);
    });
    agentEls.push({ g, pulse, aura, node, fog, id, label, pos, color });
  });

  // galaxy foreground: beams + cited stars (viewBox coords)
  const galaxyFront = el('g', { class: 's2d-galaxy-front' }, frontRoot);
  const beamEls: BeamEls[] = [];
  for (const cue of story.evidence) {
    const c = model.citations[cue.cite_id];
    if (!c) continue;
    const color = CLUSTER_BY_NAME[c.cluster ?? ''] ?? CYAN;
    const ai = cue.agent ? model.agentIdx.get(cue.agent) ?? -1 : -1;
    const line = el('line', { x1: 0, y1: 0, x2: 0, y2: 0, stroke: color, 'stroke-width': 1.8, 'stroke-linecap': 'round', opacity: 0, 'pointer-events': 'none' }, galaxyFront);
    const hit = el('line', { x1: 0, y1: 0, x2: 0, y2: 0, stroke: 'transparent', 'stroke-width': 12, class: 's2d-hit', role: 'button', tabindex: -1, 'aria-label': `Evidence: ${c.title}, ${c.article}` }, galaxyFront);
    const star = el('circle', { r: 4, fill: color, stroke: '#fff', 'stroke-width': 1, opacity: 0, class: 's2d-star', role: 'button', tabindex: -1, 'aria-label': `Cited source: ${c.title}, ${c.article}` }, galaxyFront);
    const onSel = () => useStore.getState().select({ kind: 'cite', id: cue.cite_id });
    const onKey = (e: Event) => {
      const k = (e as KeyboardEvent).key;
      if (k === 'Enter' || k === ' ') {
        e.preventDefault();
        onSel();
      }
    };
    for (const t of [hit, star]) {
      t.addEventListener('click', onSel);
      t.addEventListener('keydown', onKey);
    }
    disposers.push(() => {
      for (const t of [hit, star]) {
        t.removeEventListener('click', onSel);
        t.removeEventListener('keydown', onKey);
      }
    });
    beamEls.push({ line, hit, star, cite: cue.cite_id, agentIdx: ai, s0: cue.s0, color });
  }

  // audit chain (built lazily when results arrive)
  const auditG = el('g', { class: 's2d-audit' }, frontRoot);
  const auditLink = el('path', { d: 'M0,0', fill: 'none', stroke: '#3B5275', 'stroke-width': 1, opacity: 0.8 }, auditG);
  let auditBlocks: SVGRectElement[] = [];
  let auditBuiltFor: unknown = null;

  // particles (viewBox coords)
  const partG = el('g', { class: 's2d-particles', 'pointer-events': 'none' }, frontRoot);
  const NP = reduced ? 0 : 64;
  const partEls: SVGCircleElement[] = [];
  for (let i = 0; i < NP; i++) partEls.push(el('circle', { r: 2.2, fill: '#FFC2CE', opacity: 0 }, partG));

  // rewind sweep band
  const sweep = el('rect', { x: 0, y: -40, width: 260, height: G.VB_H + 80, fill: 'url(#s2d-sweep)', opacity: 0, 'pointer-events': 'none' }, svgFront);

  // ---------------------------------------------------------------- layout / sizing
  let vw = 1;
  let vh = 1;
  let scale = 1;
  let offX = 0;
  let offY = 0;
  let dpr = 1;
  const measure = () => {
    const r = host.getBoundingClientRect();
    vw = Math.max(1, r.width);
    vh = Math.max(1, r.height);
    scale = Math.min(vw / G.VB_W, vh / G.VB_H);
    offX = (vw - G.VB_W * scale) / 2;
    offY = (vh - G.VB_H * scale) / 2;
    dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(vw * dpr);
    canvas.height = Math.round(vh * dpr);
    canvas.style.width = `${vw}px`;
    canvas.style.height = `${vh}px`;
    // keep agent labels >= ~12px on screen
    const fs = Math.min(22, Math.max(13, 14 / Math.max(0.3, scale)));
    host.style.setProperty('--s2d-label', `${fs.toFixed(1)}px`);
    host.style.setProperty('--s2d-id', `${Math.min(14, fs * 0.86).toFixed(1)}px`);
  };
  measure();
  let ro: ResizeObserver | null = null;
  try {
    ro = new ResizeObserver(() => {
      measure();
      requestRender();
    });
    ro.observe(host);
  } catch {
    const onR = () => {
      measure();
      requestRender();
    };
    window.addEventListener('resize', onR);
    disposers.push(() => window.removeEventListener('resize', onR));
  }

  // Gap Card target (upper-right of the screen) in viewBox coordinates
  const cardTarget = (): G.Pt => {
    const r = host.getBoundingClientRect();
    const px = window.innerWidth - Math.min(260, window.innerWidth * 0.2);
    const py = Math.max(r.top + 30, 120);
    return { x: (px - r.left - offX) / scale, y: (py - r.top - offY) / scale };
  };

  // ---------------------------------------------------------------- kb (galaxy) cache
  let kbRef: KbPoints | null = null;
  let kbNorm: Float32Array | null = null;
  const normKb = (kb: KbPoints) => {
    const n = kb.count;
    const p = kb.positions;
    let cx = 0;
    let cy = 0;
    let cz = 0;
    for (let i = 0; i < n; i++) {
      cx += p[i * 3];
      cy += p[i * 3 + 1];
      cz += p[i * 3 + 2];
    }
    cx /= n;
    cy /= n;
    cz /= n;
    let maxR = 1e-6;
    const ds: number[] = [];
    for (let i = 0; i < n; i++) {
      const d = Math.hypot(p[i * 3] - cx, p[i * 3 + 1] - cy, p[i * 3 + 2] - cz);
      ds.push(d);
    }
    // robust radius: 98th percentile so outliers don't shrink the galaxy
    const sorted = ds.slice().sort((a, b) => a - b);
    maxR = Math.max(1e-6, sorted[Math.floor(sorted.length * 0.98)] || sorted[sorted.length - 1] || 1);
    const out = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      out[i * 3] = (p[i * 3] - cx) / maxR;
      out[i * 3 + 1] = (p[i * 3 + 1] - cy) / maxR;
      out[i * 3 + 2] = (p[i * 3 + 2] - cz) / maxR;
    }
    kbNorm = out;
    kbRef = kb;
  };
  const GAL_C: G.Pt = { x: 500, y: 225 };
  const GAL_R = 205;
  const project = (i: number, rot: number): { x: number; y: number; z: number } => {
    if (!kbNorm) return { x: GAL_C.x, y: GAL_C.y, z: 0 };
    const x = kbNorm[i * 3];
    const y = kbNorm[i * 3 + 1];
    const z = kbNorm[i * 3 + 2];
    const c = Math.cos(rot);
    const s = Math.sin(rot);
    const xr = x * c + z * s;
    const zr = -x * s + z * c;
    return { x: GAL_C.x + xr * GAL_R, y: GAL_C.y - y * GAL_R * 0.72 + zr * GAL_R * 0.12, z: zr };
  };
  let canvasDirty = true;

  // ---------------------------------------------------------------- render
  let pending = false;
  let disposed = false;
  let lastLang = '';
  let warpOn = false;
  let lastCssFilter = '';

  function requestRender(): void {
    if (pending || disposed) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      if (disposed) return;
      try {
        render();
      } catch (err) {
        // never throw out of the 2D stage
        if (!(window as unknown as { __s2dWarned?: boolean }).__s2dWarned) {
          (window as unknown as { __s2dWarned?: boolean }).__s2dWarned = true;
          console.warn('[majlis] 2D stage frame skipped:', err instanceof Error ? err.message : err);
        }
      }
    });
  }

  function render(): void {
    const st = useStore.getState();
    const s = st.s;
    const f: Frame = frameAt(model, story, s);
    const run = runOf(model, f.run);
    const amb = ambientTime(s, story.slowWindows);
    const cur = f.cursor;
    const kind: BeatKind | null = cur.active >= 0 ? cur.kind : null;
    const ev = cur.active >= 0 ? run.events[cur.active] : null;
    const u = cur.u;
    const d = Math.max(1e-3, cur.d);

    // ---------- layout ("camera")
    const a1 = story.acts.find((a) => a.act === 1)?.s ?? 6.5;
    const a2 = story.acts.find((a) => a.act === 2)?.s ?? a1 + 12;
    const a3 = story.act3At;
    const rw = story.rewindAt;
    const fin = story.finaleAt;
    let cityScale = G.lerp(1.36, 1.1, G.ramp(s, 0, a1 + 1.5));
    cityScale = G.lerp(cityScale, 1.0, G.ramp(s, a2, 2.4));
    let cityOp = G.lerp(0.18, 1, G.ramp(s, 0, a1 * 0.9));
    cityOp = G.lerp(cityOp, 0.34, G.ramp(s, a2, 2.4));
    cityOp = G.lerp(cityOp, 0.07, G.ramp(s, a3, 2.0));
    cityOp = G.lerp(cityOp, 0.6, G.ramp(s, rw, 2.0));
    cityOp = G.lerp(cityOp, 1.0, G.ramp(s, fin, 2.5));
    let councilOp = G.ramp(s, a2 + 0.2, 2.0);
    councilOp = G.lerp(councilOp, 0.14, G.ramp(s, fin, 2.5));
    const m3 = G.ramp(s, a3, 2.4) * (1 - G.ramp(s, rw, 2.0));
    const galaxyOp = G.ramp(s, a3 + 0.6, 2.0) * (1 - G.ramp(s, rw, 1.2));
    const auditOp = G.ramp(s, story.helixAt - 0.6, 1.4) * (1 - G.ramp(s, rw, 1.2));
    const rise = G.ramp(s, a2, 2.6);
    let ccy = G.lerp(G.lerp(372, 300, rise), 515, m3);
    let ck = G.lerp(G.lerp(0.82, 1, rise), 0.56, m3);
    const ccx = 500;
    if (kind === 'restore') {
      const glance = Math.sin(Math.PI * G.clamp01(u / d));
      cityOp = G.lerp(cityOp, 1, glance);
      councilOp *= 1 - 0.55 * glance;
    }
    set(city, 'transform', `translate(${G.CITY_C.x},${G.CITY_C.y}) scale(${cityScale.toFixed(4)}) translate(${-G.CITY_C.x},${-G.CITY_C.y})`);
    set(city, 'opacity', cityOp);
    set(council, 'transform', `translate(${ccx},${ccy.toFixed(2)}) scale(${ck.toFixed(4)})`);
    set(council, 'opacity', councilOp);
    show(council, councilOp > 0.005);

    // ---------- city
    const asleep = G.clamp01(seriesAt(run.kpis?.cells_asleep_pct, f.simT, 0) / 100);
    const ghostOn = f.run === 'reform';
    const ghost = ghostOn ? G.clamp01(seriesAt(model.baseline.kpis?.cells_asleep_pct, f.simT, 0) / 100) : -1;
    const cells = cityGeom.cells;
    for (let i = 0; i < cells.length; i++) {
      const v = G.clamp01((asleep - cells[i].rank) / 0.035 + 0.5);
      const q = Math.round(v * 12);
      if (cellState[i] !== q) {
        cellState[i] = q;
        cellEls[i].setAttribute('fill', PAL[q]);
      }
      const gq = ghostOn && cells[i].rank < ghost && v < 0.5 ? 1 : 0;
      if (ghostState[i] !== gq) {
        ghostState[i] = gq;
        if (gq) {
          cellEls[i].setAttribute('stroke', 'rgba(255,77,109,0.55)');
          cellEls[i].setAttribute('stroke-width', '1.3');
        } else cellEls[i].setAttribute('stroke', 'none');
      }
    }
    const span = Math.max(1, model.horizon - model.tCityStart);
    const heatK = 0.28 + 0.5 * G.clamp01((f.simT - model.tCityStart) / span) + (reduced ? 0 : 0.05 * Math.sin(amb * 1.7));
    set(heat, 'opacity', heatK);
    // emergency calls
    const ecs = run.kpis?.emergency_call_success ?? run.kpis?.call_setup_success;
    const success = seriesAt(ecs as [number, number][] | undefined, f.simT, 100);
    const failFrac = G.clamp01(1 - success / 100);
    for (let i = 0; i < ecEls.length; i++) {
      const cyc = amb * 0.3 + i / ecEls.length;
      const p = cyc - Math.floor(cyc);
      const n = Math.floor(cyc);
      const fails = G.hash2(i, n) < failFrac;
      const e = ecEls[i];
      if (fails && p > 0.45) {
        const q = (p - 0.45) / 0.16;
        if (q >= 1) {
          set(e, 'opacity', 0);
          continue;
        }
        const pos = G.quadAt(ecArc, 0.45 + q * 0.04);
        set(e, 'cx', pos.x);
        set(e, 'cy', pos.y);
        set(e, 'r', 2.6 + 7 * q);
        set(e, 'opacity', 0.7 * (1 - q));
      } else {
        const pos = G.quadAt(ecArc, p);
        set(e, 'cx', pos.x);
        set(e, 'cy', pos.y);
        set(e, 'r', 2.6);
        set(e, 'opacity', 0.85 * Math.sqrt(Math.sin(Math.PI * p)));
      }
    }
    if (kind === 'restore' && !reduced) {
      const q = G.clamp01(u / d);
      set(relight, 'r', 20 + 600 * G.easeOutExpo(q));
      set(relight, 'opacity', 0.9 * (1 - q));
    } else set(relight, 'opacity', 0);

    // ---------- council: agents & beliefs
    const activeK = cur.active >= 0 ? G.clamp01((u / d) * 1.4) : 1;
    const lang = st.lang;
    if (lang !== lastLang) {
      lastLang = lang;
      model.agents.forEach((a, i) => {
        agentEls[i].label.textContent = shortName(lang === 'ar' ? a.name_ar || a.name : a.name);
      });
    }
    const vis = new Set<string>();
    if (kind === 'inject' && ev && Array.isArray(ev.payload?.visible_to)) for (const x of ev.payload.visible_to) vis.add(String(x));
    for (let ai = 0; ai < agentEls.length; ai++) {
      const A = agentEls[ai];
      let maxC = 0;
      for (let fi = 0; fi < A.aura.length; fi++) {
        const c = model.facts.length ? beliefAt(run, ai, fi, cur.done, cur.active, activeK) : 0;
        maxC = Math.max(maxC, c);
        const seg = A.aura[fi];
        if (c >= KNOW_THRESHOLD) {
          set(seg, 'stroke', CYAN);
          set(seg, 'opacity', 0.95);
          set(seg, 'stroke-width', 5);
        } else if (c > 0) {
          set(seg, 'stroke', CYAN);
          set(seg, 'opacity', 0.22 + (0.45 * c) / KNOW_THRESHOLD);
          set(seg, 'stroke-width', 4);
        } else {
          set(seg, 'stroke', '#3A4A66');
          set(seg, 'opacity', 0.4);
          set(seg, 'stroke-width', 3);
        }
      }
      const knows = maxC >= KNOW_THRESHOLD;
      set(A.fog, 'opacity', knows ? 0 : maxC > 0 ? 0.55 : 1);
      set(A.node, 'opacity', knows ? 1 : 0.5);
      set(A.id, 'opacity', knows ? 1 : 0.6);
      set(A.label, 'opacity', (1 - m3) * (knows ? 1 : 0.75));
      // pulses
      let pr = 0;
      let pc = CYAN;
      if (ev && kind) {
        const isAgent = ev.agent === model.agents[ai].id;
        if (kind === 'inject' && vis.has(model.agents[ai].id)) {
          pr = G.clamp01(u / Math.min(d, 1.8));
          pc = CYAN;
        } else if ((kind === 'proposal' || kind === 'action' || kind === 'message' || kind === 'pass') && isAgent) {
          pr = G.clamp01(u / Math.min(d, 1.2));
          pc = A.color;
        } else if (kind === 'qa' && (isAgent || String(ev.payload?.asked_by ?? '') === model.agents[ai].id)) {
          pr = G.clamp01(u / Math.min(d, 1.8));
          pc = CYAN;
        }
      }
      if (pr > 0 && pr < 1 && !reduced) {
        set(A.pulse, 'r', G.NODE_R + 4 + 30 * G.easeOutExpo(pr));
        set(A.pulse, 'opacity', 0.85 * (1 - pr));
        set(A.pulse, 'stroke', pc);
      } else if (pr > 0 && reduced) {
        set(A.pulse, 'r', G.NODE_R + 8);
        set(A.pulse, 'opacity', 0.7);
        set(A.pulse, 'stroke', pc);
      } else set(A.pulse, 'opacity', 0);
    }
    // selection
    const sel = st.selection;
    if (sel && sel.kind === 'agent') {
      const si = model.agentIdx.get(sel.id);
      if (si !== undefined && agentEls[si]) {
        set(selRing, 'cx', agentEls[si].pos.x);
        set(selRing, 'cy', agentEls[si].pos.y);
        set(selRing, 'opacity', 0.9);
      } else set(selRing, 'opacity', 0);
    } else set(selRing, 'opacity', 0);
    // missing channels breathe ("missing light")
    const mOp = 0.42 + (reduced ? 0 : 0.16 * Math.sin(amb * 2.1));
    for (const m of missingEls) set(m, 'opacity', mOp / 0.55);

    // ---------- messages
    for (const M of msgEls) {
      const m = M.m;
      const live = M.run === f.run && f.seg.kind !== 'cold' && f.seg.kind !== 'city' && f.seg.kind !== 'inscribe' && (m.ev < cur.done || m.ev === cur.active) && f.simT >= m.sent - 1e-6;
      if (!live) {
        set(M.route, 'opacity', 0);
        set(M.pulse, 'opacity', 0);
        continue;
      }
      let p: number;
      if (m.deliver > m.sent + 1e-6) p = G.clamp01((f.simT - m.sent) / (m.deliver - m.sent));
      else p = m.ev === cur.active ? G.clamp01(u / d) : 1;
      if (m.ev === cur.active && m.deliver > m.sent) p = Math.max(p, 0.02 * G.clamp01(u / d));
      const fade = p >= 1 ? 1 - G.clamp01((f.simT - m.deliver) / 8) : 1;
      set(M.route, 'stroke-dasharray', `${(p * M.len).toFixed(1)} ${(M.len + 1).toFixed(1)}`);
      set(M.route, 'opacity', (m.informal ? 0.75 : 0.85) * fade);
      if (p < 1) {
        const pt = M.at(p);
        set(M.pulse, 'cx', pt.x);
        set(M.pulse, 'cy', pt.y);
        set(M.pulse, 'opacity', 1);
      } else set(M.pulse, 'opacity', 0);
    }

    // ---------- shield effects
    let shieldStroke = CYAN;
    let shieldShake = 0;
    set(tick, 'opacity', 0);
    set(flagRing, 'opacity', 0);
    set(redPulse, 'opacity', 0);
    set(ripple, 'opacity', 0);
    set(flash, 'opacity', 0);
    set(proj, 'opacity', 0);
    set(projTrail, 'opacity', 0);
    set(qaLine, 'opacity', 0);
    let crackOp = 0;
    let crackReveal = 0;
    let partOn = false;
    if (ev && kind) {
      const ai = model.agentIdx.get(String(ev.agent ?? ''));
      const node = ai !== undefined ? G.nodePos(ai, nAgents) : { x: 0, y: -G.COUNCIL_R * G.SQUASH };
      const len = Math.hypot(node.x, node.y) || 1;
      const dir = { x: node.x / len, y: node.y / len };
      const I = { x: dir.x * G.SHIELD_R, y: dir.y * G.SHIELD_R };
      if (kind === 'magic' || kind === 'block') {
        const T = timingFor(kind);
        const ic = impactClock(kind, u);
        const fe = T.fireEnd;
        const big = kind === 'magic';
        if (crackFor !== cur.active + (f.run === 'reform' ? 100000 : 0)) {
          crackFor = cur.active + (f.run === 'reform' ? 100000 : 0);
          const cracks = G.buildCracks(cur.active * 31 + 7, I, dir, 6);
          cracks.forEach((c, k) => {
            crackEls[k].p.setAttribute('d', c.d);
            crackEls[k].len = c.len;
          });
        }
        if (u < fe && !reduced) {
          const pp = G.easeInCubic(u / fe);
          const pos = { x: G.lerp(node.x, I.x, pp), y: G.lerp(node.y, I.y, pp) };
          const tail = Math.max(0, pp - 0.28);
          set(proj, 'cx', pos.x);
          set(proj, 'cy', pos.y);
          set(proj, 'opacity', 1);
          set(projTrail, 'x1', G.lerp(node.x, I.x, tail));
          set(projTrail, 'y1', G.lerp(node.y, I.y, tail));
          set(projTrail, 'x2', pos.x);
          set(projTrail, 'y2', pos.y);
          set(projTrail, 'opacity', 0.7);
        }
        const q = ic - fe; // impact clock since impact
        if (q >= 0 || reduced) {
          const qq = reduced ? 0.6 : q;
          set(ripple, 'cx', I.x);
          set(ripple, 'cy', I.y);
          set(ripple, 'r', 6 + (big ? 150 : 95) * G.easeOutExpo(qq / 0.9));
          set(ripple, 'opacity', (reduced ? 0.4 : 0.95) * (1 - G.clamp01(qq / 0.9)));
          set(flash, 'cx', I.x);
          set(flash, 'cy', I.y);
          set(flash, 'r', 3 + (big ? 13 : 9) * G.easeOutExpo(qq / 0.2));
          set(flash, 'opacity', reduced ? 0 : 0.9 * (1 - G.clamp01(qq / 0.3)));
          set(redPulse, 'opacity', (big ? 0.5 : 0.32) * Math.exp(-Math.max(0, qq) * 1.6) + 0.06);
          shieldStroke = RED;
          crackReveal = reduced ? 1 : G.clamp01(qq / 0.55);
          crackOp = (big ? 1 : 0.75) * (1 - G.clamp01((u - (T.cardIn + 1.6)) / 1.2));
          if (!reduced && big) shieldShake = 3.2 * Math.exp(-qq * 4) * Math.sin(qq * 55);
          partOn = !reduced;
        }
        if (partOn) {
          const Iv = { x: ccx + I.x * ck, y: ccy + I.y * ck };
          const tgt = cardTarget();
          const cardClock = impactClock(kind, T.cardIn);
          const burstEnd = fe + 0.35;
          const nUse = big ? partEls.length : Math.round(partEls.length * 0.55);
          const baseA = Math.atan2(dir.y, dir.x);
          for (let i = 0; i < partEls.length; i++) {
            const pe = partEls[i];
            if (i >= nUse) {
              set(pe, 'opacity', 0);
              continue;
            }
            const h1 = G.hash2(i, 1);
            const h2 = G.hash2(i, 2);
            const h3 = G.hash2(i, 3);
            const ang = baseA + (h1 - 0.5) * 2.8;
            const sp = (big ? 40 : 28) + h2 * (big ? 80 : 50);
            const qa = G.clamp01((ic - fe) / 0.35);
            const bx = Iv.x + Math.cos(ang) * sp * G.easeOutExpo(qa) * ck;
            const by = Iv.y + Math.sin(ang) * sp * G.easeOutExpo(qa) * ck;
            const stagger = h3 * 0.25;
            const qb = G.easeInOutCubic((ic - burstEnd - stagger) / Math.max(0.2, cardClock - burstEnd));
            const jx = (G.hash2(i, 4) - 0.5) * 60;
            const jy = (G.hash2(i, 5) - 0.5) * 30;
            const x = G.lerp(bx, tgt.x + jx, qb);
            const y = G.lerp(by, tgt.y + jy, qb);
            const after = G.clamp01((u - T.cardIn) / 0.6);
            set(pe, 'cx', x);
            set(pe, 'cy', y);
            set(pe, 'r', (1.4 + h2 * 2.2) * (1 - 0.5 * qb));
            set(pe, 'fill', qb > 0.5 ? '#FFD9A8' : '#FFC2CE');
            set(pe, 'opacity', qa > 0 ? 0.95 * (1 - after) : 0);
          }
        }
      } else if (kind === 'block_plain') {
        const k = Math.sin(Math.PI * G.clamp01(u / d));
        set(redPulse, 'opacity', 0.32 * k);
        set(ripple, 'cx', I.x);
        set(ripple, 'cy', I.y);
        set(ripple, 'r', 6 + 60 * G.easeOutExpo(u / d));
        set(ripple, 'opacity', 0.6 * (1 - G.clamp01(u / d)));
        shieldStroke = RED;
      } else if (kind === 'flag') {
        const q = G.clamp01(u / Math.min(d, 1.8));
        set(flagRing, 'transform', `scale(${(1 + 0.55 * G.easeOutExpo(q)).toFixed(3)})`);
        set(flagRing, 'opacity', 0.85 * (1 - q));
        shieldStroke = AMBER;
      } else if (kind === 'pass') {
        set(tick, 'opacity', Math.sin(Math.PI * G.clamp01(u / d)));
        shieldStroke = GREEN;
      } else if (kind === 'gap_card') {
        const q = G.clamp01(u / Math.min(d, 2.2));
        set(flagRing, 'transform', `scale(${(1 + 0.4 * G.easeOutExpo(q)).toFixed(3)})`);
        set(flagRing, 'stroke', GOLD);
        set(flagRing, 'opacity', 0.7 * (1 - q));
        shieldStroke = GOLD;
      } else if (kind === 'qa') {
        const asker = model.agentIdx.get(String(ev.payload?.asked_by ?? ''));
        if (asker !== undefined && ai !== undefined) {
          const pa = G.nodePos(asker, nAgents);
          set(qaLine, 'x1', pa.x);
          set(qaLine, 'y1', pa.y);
          set(qaLine, 'x2', node.x);
          set(qaLine, 'y2', node.y);
          set(qaLine, 'opacity', 0.8 * Math.sin(Math.PI * G.clamp01(u / d)));
        }
      }
    }
    if (kind !== 'flag' && kind !== 'gap_card') set(flagRing, 'stroke', AMBER);
    if (!partOn) for (const pe of partEls) set(pe, 'opacity', 0);
    for (const c of crackEls) {
      set(c.p, 'stroke-dasharray', `${(c.len * crackReveal).toFixed(1)} ${(c.len + 1).toFixed(1)}`);
      set(c.p, 'opacity', crackOp);
    }
    set(shieldPoly, 'stroke', shieldStroke);
    set(shieldG, 'transform', shieldShake ? `translate(${shieldShake.toFixed(2)},0)` : 'translate(0,0)');

    // reform inscriptions + gold ring
    const reformOn = f.run === 'reform';
    set(goldRing, 'opacity', reformOn ? (f.seg.kind === 'inscribe' ? 0.9 * G.clamp01((s - story.inscribeAt) / 0.6) : 0.55) : 0);
    for (let i = 0; i < inscEls.length; i++) {
      const t = inscEls[i];
      if (!reformOn) {
        set(t, 'opacity', 0);
        continue;
      }
      const ui = s - story.inscribeAt;
      const k = f.seg.kind === 'inscribe' ? G.easeOutExpo((ui - 0.3 * i) / 0.5) : 1;
      const spread = nCl <= 1 ? 0 : Math.min(Math.PI * 1.6, (nCl - 1) * 0.75);
      const ang = -Math.PI / 2 + (nCl <= 1 ? 0 : -spread / 2 + (spread * i) / (nCl - 1));
      const rad = G.SHIELD_R + 26 + 70 * (1 - k);
      set(t, 'x', Math.cos(ang) * rad);
      set(t, 'y', Math.sin(ang) * rad + 4);
      set(t, 'opacity', k * (f.seg.kind === 'inscribe' ? 1 : 0.85));
    }

    // ---------- galaxy (canvas) + beams + audit chain
    const ctx = canvas.getContext('2d');
    const kb = st.kb;
    if (kb && kb !== kbRef) {
      normKb(kb);
      canvasDirty = true;
    }
    const rot = amb * 0.045;
    if (ctx) {
      if (galaxyOp > 0.005 && kbNorm && kbRef) {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.setTransform(dpr * scale, 0, 0, dpr * scale, dpr * offX, dpr * offY);
        const n = kbRef.count;
        const cl = kbRef.clusters;
        const sz = n > 10000 ? 1.25 : 1.7;
        const cr = Math.cos(rot);
        const sr = Math.sin(rot);
        for (let bin = 0; bin < 2; bin++) {
          for (let c = 0; c < 4; c++) {
            ctx.beginPath();
            for (let i = 0; i < n; i++) {
              const cc = cl[i] > 3 ? 3 : cl[i];
              if (cc !== c) continue;
              const x = kbNorm[i * 3];
              const y = kbNorm[i * 3 + 1];
              const z = kbNorm[i * 3 + 2];
              const zr = -x * sr + z * cr;
              if ((zr > 0 ? 1 : 0) !== bin) continue;
              const xr = x * cr + z * sr;
              ctx.rect(GAL_C.x + xr * GAL_R, GAL_C.y - y * GAL_R * 0.72 + zr * GAL_R * 0.12, sz, sz);
            }
            ctx.globalAlpha = galaxyOp * (c === 3 ? 0.35 : 0.85) * (bin ? 1 : 0.55);
            ctx.fillStyle = CLUSTER_COLORS[c];
            ctx.fill();
          }
        }
        ctx.globalAlpha = 1;
        canvasDirty = true;
      } else if (canvasDirty) {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        canvasDirty = false;
      }
    }
    for (const B of beamEls) {
      const c = model.citations[B.cite];
      const si = c?.star_index;
      const valid = galaxyOp > 0.01 && s >= B.s0 && kbNorm && kbRef && typeof si === 'number' && si >= 0 && si < kbRef.count;
      if (!valid) {
        set(B.line, 'opacity', 0);
        set(B.star, 'opacity', 0);
        show(B.hit, false);
        show(B.star, false);
        continue;
      }
      const start = B.agentIdx >= 0 ? G.nodePos(B.agentIdx, nAgents) : { x: 0, y: 0 };
      const sx = ccx + start.x * ck;
      const sy = ccy + start.y * ck;
      const pt = project(si as number, rot);
      const q = G.easeOutExpo((s - B.s0) / 0.6);
      const ex = G.lerp(sx, pt.x, q);
      const ey = G.lerp(sy, pt.y, q);
      set(B.line, 'x1', sx);
      set(B.line, 'y1', sy);
      set(B.line, 'x2', ex);
      set(B.line, 'y2', ey);
      const settle = 0.55 + 0.4 * (1 - G.clamp01((s - B.s0 - 0.6) / 1.5));
      set(B.line, 'opacity', galaxyOp * settle);
      show(B.hit, true);
      show(B.star, true);
      set(B.hit, 'x1', sx);
      set(B.hit, 'y1', sy);
      set(B.hit, 'x2', ex);
      set(B.hit, 'y2', ey);
      set(B.star, 'cx', pt.x);
      set(B.star, 'cy', pt.y);
      set(B.star, 'r', 3 + 3 * q);
      set(B.star, 'opacity', galaxyOp * q);
    }
    // audit chain
    const res = st.audit.result;
    if (res && res !== auditBuiltFor) {
      auditBuiltFor = res;
      for (const b of auditBlocks) b.remove();
      auditBlocks = res.results.map(() => el('rect', { x: 0, y: 0, width: 6, height: 6, rx: 1.2, fill: '#16233A', stroke: '#2E4466', 'stroke-width': 0.8 }, auditG));
    }
    show(auditG, auditOp > 0.005 && auditBlocks.length > 0);
    if (auditOp > 0.005 && res && auditBlocks.length) {
      set(auditG, 'opacity', auditOp);
      const N = auditBlocks.length;
      const storyProg = G.clamp01((s - story.verifyAt) / Math.max(0.1, story.verifyDur));
      const man = st.audit.manualAt;
      const manProg = man !== null ? G.clamp01((performance.now() - man) / 2500) : 0;
      const prog = Math.max(storyProg, manProg);
      const lit = st.audit.state === 'done' ? Math.floor(prog * N + 1e-6) : 0;
      const rx = GAL_R * 1.32;
      const ry = GAL_R * 0.3;
      const size = Math.max(3, Math.min(11, ((2 * Math.PI * rx) / N) * 0.5));
      let dPath = '';
      const orbit = rot * 0.6;
      for (let i = 0; i < N; i++) {
        const a = (i / N) * Math.PI * 2 - Math.PI / 2 + orbit;
        const x = GAL_C.x + Math.cos(a) * rx;
        const y = GAL_C.y + 8 + Math.sin(a) * ry;
        const front = Math.sin(a) > 0;
        const sz = size * (front ? 1 : 0.72);
        const b = auditBlocks[i];
        set(b, 'x', x - sz / 2);
        set(b, 'y', y - sz / 2);
        set(b, 'width', sz);
        set(b, 'height', sz);
        const r = res.results[i];
        if (i < lit) {
          set(b, 'fill', r && r.ok ? GREEN : RED);
          set(b, 'stroke', r && r.ok ? '#A8FFE0' : '#FFC2CE');
        } else {
          set(b, 'fill', '#16233A');
          set(b, 'stroke', '#2E4466');
        }
        set(b, 'opacity', front ? 1 : 0.55);
        dPath += `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)} `;
      }
      set(auditLink, 'd', dPath);
      if (man !== null && manProg < 1) requestRender();
    }

    // ---------- rewind
    if (f.seg.kind === 'rewind') {
      const k = f.rewindK;
      const str = Math.sin(Math.PI * k);
      if (!reduced) {
        if (!warpOn) {
          city.setAttribute('filter', 'url(#s2d-warp-b)');
          council.setAttribute('filter', 'url(#s2d-warp-f)');
          warpOn = true;
        }
        warpB.disp.setAttribute('scale', (24 * str).toFixed(2));
        warpF.disp.setAttribute('scale', (9 * str).toFixed(2));
        warpB.off.setAttribute('dx', (-k * 320).toFixed(1));
        warpF.off.setAttribute('dx', (-k * 320).toFixed(1));
        set(sweep, 'x', G.lerp(G.VB_W + 40, -300, k));
        set(sweep, 'opacity', 0.9 * str);
      }
      const css = `saturate(${(1 - 0.65 * str).toFixed(3)}) hue-rotate(${(-28 * str).toFixed(1)}deg) brightness(${(1 + 0.08 * str).toFixed(3)})`;
      if (css !== lastCssFilter) {
        host.style.filter = css;
        lastCssFilter = css;
      }
    } else {
      if (warpOn) {
        city.removeAttribute('filter');
        council.removeAttribute('filter');
        warpOn = false;
      }
      set(sweep, 'opacity', 0);
      if (lastCssFilter !== '') {
        host.style.filter = '';
        lastCssFilter = '';
      }
    }
  }

  function dispose(): void {
    disposed = true;
    ro?.disconnect();
    for (const d of disposers) d();
    svgBack.replaceChildren();
    svgFront.replaceChildren();
    host.style.filter = '';
    const ctx = canvas.getContext('2d');
    ctx?.clearRect(0, 0, canvas.width, canvas.height);
  }

  return { requestRender, dispose };
}

function makeWarp(defs: SVGDefsElement, id: string): { disp: SVGFEDisplacementMapElement; off: SVGFEOffsetElement } {
  const f = el('filter', { id, x: '-5%', y: '-5%', width: '110%', height: '110%' }, defs);
  el('feTurbulence', { type: 'fractalNoise', baseFrequency: '0.006 0.035', numOctaves: 1, seed: 7, result: 'n', stitchTiles: 'stitch' }, f);
  const off = el('feOffset', { in: 'n', dx: 0, dy: 0, result: 'n2' }, f);
  const disp = el('feDisplacementMap', { in: 'SourceGraphic', in2: 'n2', scale: 0, xChannelSelector: 'R', yChannelSelector: 'G' }, f);
  return { disp, off };
}

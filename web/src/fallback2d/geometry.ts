/**
 * Pure geometry + easing helpers for the 2D Experience. Deterministic (no Math.random).
 */

export interface Pt {
  x: number;
  y: number;
}

export const clamp01 = (x: number): number => (x <= 0 ? 0 : x >= 1 ? 1 : x);
export const lerp = (a: number, b: number, k: number): number => a + (b - a) * k;
export const smooth = (x: number): number => {
  const t = clamp01(x);
  return t * t * (3 - 2 * t);
};
/** 0 before `start`, smooth 0→1 over `dur`, 1 after. */
export const ramp = (s: number, start: number, dur: number): number => smooth((s - start) / Math.max(1e-6, dur));
export const easeOutExpo = (x: number): number => {
  const t = clamp01(x);
  return t >= 1 ? 1 : 1 - Math.pow(2, -10 * t);
};
export const easeInCubic = (x: number): number => {
  const t = clamp01(x);
  return t * t * t;
};
export const easeInOutCubic = (x: number): number => {
  const t = clamp01(x);
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
};

/** Integer hash → [0, 1). */
export function hash(n: number): number {
  let x = Math.imul((n | 0) ^ 0x9e3779b9, 0x85ebca6b);
  x ^= x >>> 13;
  x = Math.imul(x, 0xc2b2ae35);
  x ^= x >>> 16;
  return (x >>> 0) / 4294967296;
}
export const hash2 = (a: number, b: number): number => hash(Math.imul(a, 73856093) ^ Math.imul(b + 1, 19349663));

// ---------------------------------------------------------------------------
// Scene constants (viewBox units)

export const VB_W = 1000;
export const VB_H = 640;
export const CITY_C: Pt = { x: 500, y: 330 };
export const DOWNTOWN: Pt = { x: 560, y: 335 };
export const AMBULANCE: Pt = { x: 175, y: 480 };
export const COUNCIL_R = 210; // ring radius (local units)
export const SQUASH = 0.78; // ellipse ratio of the chamber ring (perspective hint)
export const NODE_R = 20;
export const AURA_R = 31;
export const SHIELD_R = 62;

// ---------------------------------------------------------------------------
// City hex grid

export interface Cell {
  x: number;
  y: number;
  rank: number; // 0..1 order of falling asleep (ripple from downtown)
  dist: number; // normalised distance from downtown (relight wave)
}

export interface CityGeom {
  cells: Cell[];
  r: number; // circumradius
  hexPath: string; // relative hex path (centred at 0,0)
}

export function hexPoints(r: number, cx = 0, cy = 0): string {
  const out: string[] = [];
  for (let k = 0; k < 6; k++) {
    const a = (Math.PI / 3) * k + Math.PI / 6; // pointy-top
    out.push(`${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`);
  }
  return out.join(' ');
}

export function buildCity(n: number, rx = 470, ry = 292): CityGeom {
  const count = Math.max(24, Math.min(400, Math.round(n)));
  const area = Math.PI * rx * ry;
  const r = Math.sqrt(area / count / 2.598);
  const w = Math.sqrt(3) * r;
  const h = 1.5 * r;
  const cand: { x: number; y: number; m: number }[] = [];
  const qn = Math.ceil(rx / w) + 3;
  const rn = Math.ceil(ry / h) + 3;
  for (let rr = -rn; rr <= rn; rr++) {
    for (let q = -qn; q <= qn; q++) {
      const x = CITY_C.x + w * (q + (rr & 1 ? 0.5 : 0));
      const y = CITY_C.y + h * rr;
      const dx = (x - CITY_C.x) / rx;
      const dy = (y - CITY_C.y) / ry;
      cand.push({ x, y, m: dx * dx + dy * dy });
    }
  }
  cand.sort((a, b) => a.m - b.m);
  const chosen = cand.slice(0, count);
  let maxD = 1;
  for (const c of chosen) maxD = Math.max(maxD, Math.hypot(c.x - DOWNTOWN.x, c.y - DOWNTOWN.y));
  const keyed = chosen.map((c, i) => {
    const d = Math.hypot(c.x - DOWNTOWN.x, c.y - DOWNTOWN.y) / maxD;
    return { c, d, key: d + (hash(i * 7 + 3) - 0.5) * 0.2 };
  });
  const order = keyed.map((k, i) => i).sort((a, b) => keyed[a].key - keyed[b].key);
  const rank = new Array<number>(count);
  order.forEach((idx, pos) => (rank[idx] = pos / count));
  const cells: Cell[] = keyed.map((k, i) => ({ x: k.c.x, y: k.c.y, rank: rank[i], dist: k.d }));
  return { cells, r, hexPath: hexPoints(r * 0.84) };
}

// ---------------------------------------------------------------------------
// Council ring (local coordinates: centre 0,0)

export function nodeAngle(i: number, n: number): number {
  return -Math.PI / 2 + (i * 2 * Math.PI) / Math.max(1, n);
}

export function nodePos(i: number, n: number, R = COUNCIL_R): Pt {
  const a = nodeAngle(i, n);
  return { x: R * Math.cos(a), y: R * Math.sin(a) * SQUASH };
}

export interface Quad {
  p0: Pt;
  p1: Pt;
  p2: Pt;
}
export interface Cubic {
  p0: Pt;
  p1: Pt;
  p2: Pt;
  p3: Pt;
}

export function quadAt(q: Quad, t: number): Pt {
  const u = 1 - t;
  return {
    x: u * u * q.p0.x + 2 * u * t * q.p1.x + t * t * q.p2.x,
    y: u * u * q.p0.y + 2 * u * t * q.p1.y + t * t * q.p2.y,
  };
}

export function cubicAt(c: Cubic, t: number): Pt {
  const u = 1 - t;
  const a = u * u * u;
  const b = 3 * u * u * t;
  const d = 3 * u * t * t;
  const e = t * t * t;
  return {
    x: a * c.p0.x + b * c.p1.x + d * c.p2.x + e * c.p3.x,
    y: a * c.p0.y + b * c.p1.y + d * c.p2.y + e * c.p3.y,
  };
}

/** Channel filament between two ring nodes, bowing around the shield. */
export function channelCurve(ia: number, ib: number, n: number, R = COUNCIL_R): Quad {
  const a = nodeAngle(ia, n);
  const b = nodeAngle(ib, n);
  let d = b - a;
  while (d > Math.PI) d -= 2 * Math.PI;
  while (d < -Math.PI) d += 2 * Math.PI;
  const sep = Math.abs(d);
  let m = a + d / 2;
  if (sep > Math.PI - 0.05) m = Math.min(a, b) + Math.PI / 2;
  const c = 0.95 - 0.5 * (sep / Math.PI);
  return {
    p0: nodePos(ia, n, R),
    p1: { x: Math.cos(m) * R * c, y: Math.sin(m) * R * c * SQUASH },
    p2: nodePos(ib, n, R),
  };
}

/** Informal detour: loops outside the ring (visibly longer route). */
export function detourCurve(ia: number, ib: number, n: number, R = COUNCIL_R): Cubic {
  const a = nodeAngle(ia, n);
  const b = nodeAngle(ib, n);
  const k = 2.05;
  return {
    p0: nodePos(ia, n, R),
    p1: { x: Math.cos(a) * R * k, y: Math.sin(a) * R * k * SQUASH },
    p2: { x: Math.cos(b) * R * k, y: Math.sin(b) * R * k * SQUASH },
    p3: nodePos(ib, n, R),
  };
}

export function quadPath(q: Quad): string {
  return `M${q.p0.x.toFixed(1)},${q.p0.y.toFixed(1)} Q${q.p1.x.toFixed(1)},${q.p1.y.toFixed(1)} ${q.p2.x.toFixed(1)},${q.p2.y.toFixed(1)}`;
}

export function cubicPath(c: Cubic): string {
  return `M${c.p0.x.toFixed(1)},${c.p0.y.toFixed(1)} C${c.p1.x.toFixed(1)},${c.p1.y.toFixed(1)} ${c.p2.x.toFixed(1)},${c.p2.y.toFixed(1)} ${c.p3.x.toFixed(1)},${c.p3.y.toFixed(1)}`;
}

/** Sub-path of a quadratic from t0 to t1, sampled as a polyline. */
export function quadSubPath(q: Quad, t0: number, t1: number, steps = 14): string {
  const pts: string[] = [];
  for (let i = 0; i <= steps; i++) {
    const p = quadAt(q, t0 + ((t1 - t0) * i) / steps);
    pts.push(`${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`);
  }
  return pts.join(' ');
}

export function curveLength(f: (t: number) => Pt, steps = 32): number {
  let L = 0;
  let prev = f(0);
  for (let i = 1; i <= steps; i++) {
    const p = f(i / steps);
    L += Math.hypot(p.x - prev.x, p.y - prev.y);
    prev = p;
  }
  return L;
}

/** Arc segment path (ellipse-squashed) for the knowledge aura. */
export function arcPath(cx: number, cy: number, r: number, a0: number, a1: number): string {
  const p0 = { x: cx + r * Math.cos(a0), y: cy + r * Math.sin(a0) };
  const p1 = { x: cx + r * Math.cos(a1), y: cy + r * Math.sin(a1) };
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return `M${p0.x.toFixed(2)},${p0.y.toFixed(2)} A${r},${r} 0 ${large} 1 ${p1.x.toFixed(2)},${p1.y.toFixed(2)}`;
}

/** Deterministic crack polylines spreading from impact point `I` (direction `dir` points outwards). */
export function buildCracks(seed: number, I: Pt, dir: Pt, count = 6): { d: string; len: number }[] {
  const out: { d: string; len: number }[] = [];
  const base = Math.atan2(-dir.y, -dir.x);
  for (let k = 0; k < count; k++) {
    let a = base + (hash2(seed, k) - 0.5) * 2.4;
    let x = I.x;
    let y = I.y;
    let d = `M${x.toFixed(1)},${y.toFixed(1)}`;
    let len = 0;
    const segs = 3 + Math.floor(hash2(seed + 11, k) * 3);
    for (let j = 0; j < segs; j++) {
      const l = 7 + hash2(seed * 3 + j, k) * 11;
      a += (hash2(seed + j * 17, k + 5) - 0.5) * 1.1;
      x += Math.cos(a) * l;
      y += Math.sin(a) * l;
      len += l;
      d += ` L${x.toFixed(1)},${y.toFixed(1)}`;
    }
    out.push({ d, len });
  }
  return out;
}

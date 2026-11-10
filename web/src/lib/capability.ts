/** Renderer selection: 3D when WebGL2 is available and nothing asks for the 2D Experience. */
export interface Decision {
  renderer: '3d' | '2d';
  reason: string;
}

export function params(): URLSearchParams {
  try {
    return new URLSearchParams(window.location.search);
  } catch {
    return new URLSearchParams();
  }
}

export function hasWebGL2(strict: boolean): boolean {
  try {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl2', strict ? { failIfMajorPerformanceCaveat: true } : undefined) as WebGL2RenderingContext | null;
    if (!gl) return false;
    const lose = gl.getExtension('WEBGL_lose_context');
    lose?.loseContext();
    return true;
  } catch {
    return false;
  }
}

export function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
}

export function decideRenderer(): Decision {
  const q = params();
  if (q.get('lite') === '1' || q.get('2d') === '1') return { renderer: '2d', reason: 'lite mode requested (?lite=1)' };
  const force = q.get('force3d') === '1';
  if (!force && prefersReducedMotion()) return { renderer: '2d', reason: 'prefers-reduced-motion' };
  if (!hasWebGL2(false)) return { renderer: '2d', reason: 'WebGL2 unavailable' };
  if (!force && !hasWebGL2(true)) return { renderer: '2d', reason: 'software rendering only (major performance caveat)' };
  const nav = navigator as Navigator & { deviceMemory?: number };
  if (!force && ((nav.hardwareConcurrency && nav.hardwareConcurrency <= 2) || (nav.deviceMemory && nav.deviceMemory <= 2))) {
    return { renderer: '2d', reason: 'low-power device' };
  }
  return { renderer: '3d', reason: force ? 'forced 3D (?force3d=1)' : 'WebGL2' };
}

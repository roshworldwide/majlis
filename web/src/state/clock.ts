/**
 * The single story clock. Advances `s` in real time × speed while playing.
 * Pauses when the tab is hidden. Everything else is a pure function of `s`.
 */
import { useStore } from './store';

let started = false;
let last = 0;

export function startClock(): void {
  if (started) return;
  started = true;
  last = performance.now();
  const tick = (now: number) => {
    const dt = Math.min(0.1, Math.max(0, (now - last) / 1000));
    last = now;
    const st = useStore.getState();
    if (st.status === 'ready' && st.story && st.playing && !document.hidden) {
      const d = st.story.duration;
      let s = st.s + dt * st.speed;
      if (s >= d) {
        s = d;
        useStore.setState({ s, playing: false, ended: true });
      } else {
        useStore.setState({ s });
      }
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  document.addEventListener('visibilitychange', () => {
    last = performance.now();
  });
}

/** Ambient (decorative motion) time: story time with slow-mo windows slowed, deterministic in s. */
export function ambientTime(s: number, windows: { a: number; b: number; rate: number }[]): number {
  let t = s;
  for (const w of windows) {
    if (s <= w.a) break;
    const ov = Math.min(s, w.b) - w.a;
    t -= ov * (1 - w.rate);
  }
  return t;
}

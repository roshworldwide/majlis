import { useEffect } from 'react';
import { useStore } from '../state/store';
import { runVerify } from '../boot';

/** Space play/pause · ←/→ seek · 1–4 acts · R rewind & reform · F present · E explore · V verify · Esc close. */
export function useKeyboard(): void {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const st = useStore.getState();
      if (!st.story) return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
        if (e.key !== 'Escape') return;
      }
      if (!st.coldOpenDone && st.s < (st.story.acts[1]?.s ?? 0)) {
        // any key skips the cold open
        useStore.setState({ coldOpenDone: true, s: st.story.acts[1]?.s ?? 0 });
        e.preventDefault();
        return;
      }
      const jump = (act: number) => {
        const a = st.story!.acts.find((x) => x.act === act);
        if (a) useStore.setState({ s: a.s, ended: false, playing: true });
      };
      switch (e.key) {
        case ' ':
          if (tag === 'BUTTON') return;
          e.preventDefault();
          st.togglePlay();
          break;
        case 'ArrowRight':
          e.preventDefault();
          st.seek(st.s + (e.shiftKey ? 15 : 5));
          break;
        case 'ArrowLeft':
          e.preventDefault();
          st.seek(st.s - (e.shiftKey ? 15 : 5));
          break;
        case '1':
        case '2':
        case '3':
        case '4':
          jump(Number(e.key));
          break;
        case 'r':
        case 'R':
          useStore.setState({ s: st.story.rewindAt, playing: true, ended: false });
          break;
        case 'f':
        case 'F':
          togglePresent();
          break;
        case 'e':
        case 'E':
          useStore.setState({ mode: st.mode === 'story' ? 'explore' : 'story' });
          break;
        case 'v':
        case 'V':
          runVerify(true);
          break;
        case 'Escape':
          if (st.selection) useStore.setState({ selection: null });
          else if (st.present) togglePresent(false);
          break;
        default:
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
}

export function togglePresent(force?: boolean): void {
  const st = useStore.getState();
  const next = force ?? !st.present;
  useStore.setState({ present: next });
  try {
    if (next && !document.fullscreenElement) document.documentElement.requestFullscreen?.().catch(() => undefined);
    if (!next && document.fullscreenElement) document.exitFullscreen?.().catch(() => undefined);
  } catch {
    /* fullscreen not available: present mode still hides chrome */
  }
}

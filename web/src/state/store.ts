import { create } from 'zustand';
import type { Model } from '../data/derive';
import type { Story } from '../data/story';
import type { AuditResult } from '../data/audit';
import type { KbPoints } from '../data/load';

export type Renderer = '3d' | '2d';
export type Quality = 'high' | 'medium' | 'low';
export type Selection =
  | { kind: 'agent'; id: string }
  | { kind: 'gap'; id: string }
  | { kind: 'cite'; id: string }
  | { kind: 'node'; id: string }
  | null;

export interface AuditState {
  state: 'idle' | 'running' | 'done';
  result: AuditResult | null;
  /** performance.now() when a manual verification animation started (null = story-driven) */
  manualAt: number | null;
}

export interface State {
  status: 'loading' | 'ready' | 'error';
  error: string | null;
  model: Model | null;
  story: Story | null;
  schemaIssues: string[];
  auditText: string | null;
  renderer: Renderer;
  rendererReason: string;
  quality: Quality;
  s: number;
  playing: boolean;
  speed: number;
  ended: boolean;
  mode: 'story' | 'explore';
  present: boolean;
  lang: 'en' | 'ar';
  sound: boolean;
  coldOpenDone: boolean;
  selection: Selection;
  audit: AuditState;
  kb: KbPoints | null;
  kbState: 'idle' | 'loading' | 'ready' | 'none';
  fps: number;
  set: (p: Partial<State>) => void;
  seek: (s: number) => void;
  togglePlay: () => void;
  select: (sel: Selection) => void;
  fallbackTo2D: (reason: string) => void;
}

export const useStore = create<State>((set, get) => ({
  status: 'loading',
  error: null,
  model: null,
  story: null,
  schemaIssues: [],
  auditText: null,
  renderer: '2d',
  rendererReason: 'initialising',
  quality: 'high',
  s: 0,
  playing: true,
  speed: 1,
  ended: false,
  mode: 'story',
  present: false,
  lang: 'en',
  sound: false,
  coldOpenDone: false,
  selection: null,
  audit: { state: 'idle', result: null, manualAt: null },
  kb: null,
  kbState: 'idle',
  fps: 0,
  set: (p) => set(p),
  seek: (s) => {
    const st = get();
    const d = st.story?.duration ?? 0;
    const ns = Math.max(0, Math.min(d, s));
    set({ s: ns, ended: ns >= d - 1e-6 && d > 0 ? st.ended : false });
  },
  togglePlay: () => {
    const st = get();
    if (!st.playing && st.story && st.s >= st.story.duration - 0.01) set({ s: 0, playing: true, ended: false });
    else set({ playing: !st.playing });
  },
  select: (selection) => set({ selection }),
  fallbackTo2D: (reason) => {
    if (get().renderer === '2d') return;
    // eslint-disable-next-line no-console
    console.warn(`[majlis] switching to the 2D Experience: ${reason}`);
    set({ renderer: '2d', rendererReason: reason });
  },
}));

export const getState = () => useStore.getState();

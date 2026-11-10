import { loadKb, loadReplay } from './data/load';
import { buildModel } from './data/derive';
import { buildStory, frameAt, actAt } from './data/story';
import { verifyAudit } from './data/audit';
import { useStore } from './state/store';
import { startClock } from './state/clock';
import { decideRenderer, params } from './lib/capability';

declare global {
  interface Window {
    __majlis?: Record<string, unknown>;
  }
}

export async function runVerify(manual: boolean): Promise<void> {
  const st = useStore.getState();
  useStore.setState({ audit: { ...st.audit, state: 'running', manualAt: manual ? performance.now() : st.audit.manualAt } });
  const result = await verifyAudit(st.auditText);
  useStore.setState({ audit: { state: 'done', result, manualAt: manual ? performance.now() : useStore.getState().audit.manualAt } });
}

export function ensureKb(): void {
  const st = useStore.getState();
  if (!st.model || st.kbState !== 'idle') return;
  useStore.setState({ kbState: 'loading' });
  loadKb(st.model.replay).then((kb) => useStore.setState({ kb, kbState: kb ? 'ready' : 'none' }));
}

export async function boot(): Promise<void> {
  const decision = decideRenderer();
  useStore.setState({ renderer: decision.renderer, rendererReason: decision.reason });
  installHooks();
  try {
    const { replay, schemaIssues, auditText } = await loadReplay();
    if (schemaIssues.length) console.warn('[majlis] replay.json schema issues (rendering best-effort):', schemaIssues);
    const model = buildModel(replay);
    const story = buildStory(model);
    const q = params();
    const tParam = q.get('t');
    const actParam = q.get('act');
    let s0 = 0;
    if (tParam !== null && !Number.isNaN(Number(tParam))) s0 = Number(tParam);
    else if (actParam !== null) {
      const a = story.acts.find((x) => String(x.act) === actParam);
      if (a) s0 = a.s;
    } else if (q.get('skip') === '1') s0 = story.acts[1]?.s ?? 0;
    const sp = Number(q.get('speed') ?? '1');
    const speed = Number.isFinite(sp) && sp > 0 ? Math.min(32, Math.max(0.25, sp)) : 1;
    useStore.setState({
      status: 'ready',
      model,
      story,
      schemaIssues,
      auditText,
      s: Math.max(0, Math.min(story.duration, s0)),
      speed,
      playing: q.get('paused') !== '1',
      mode: q.get('mode') === 'explore' ? 'explore' : 'story',
      lang: q.get('lang') === 'ar' ? 'ar' : 'en',
      coldOpenDone: s0 > 0.5,
      sound: false,
    });
    startClock();
    // the badge is real computation from the first second
    runVerify(false);
    // galaxy data is lazy: fetch once the first frame is up
    setTimeout(ensureKb, 1200);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    console.warn('[majlis] failed to load the replay:', msg);
    useStore.setState({ status: 'error', error: msg });
  }
}

function installHooks(): void {
  const api = {
    get ready() {
      return useStore.getState().status === 'ready';
    },
    get status() {
      return useStore.getState().status;
    },
    get s() {
      return useStore.getState().s;
    },
    get duration() {
      return useStore.getState().story?.duration ?? 0;
    },
    get acts() {
      return useStore.getState().story?.acts ?? [];
    },
    get act() {
      const st = useStore.getState();
      return st.story ? actAt(st.story, st.s) : 0;
    },
    get renderer() {
      return useStore.getState().renderer;
    },
    get rendererReason() {
      return useStore.getState().rendererReason;
    },
    get ended() {
      return useStore.getState().ended;
    },
    get quality() {
      return useStore.getState().quality;
    },
    get audit() {
      const a = useStore.getState().audit;
      return { state: a.state, ok: a.result?.ok ?? null, entries: a.result?.entries ?? 0, head: a.result?.head ?? '' };
    },
    get story() {
      const st = useStore.getState().story;
      if (!st) return null;
      return {
        duration: st.duration,
        acts: st.acts,
        gapCards: st.gapCards,
        verifyAt: st.verifyAt,
        finaleAt: st.finaleAt,
        rewindAt: st.rewindAt,
        reformAt: st.reformAt,
        act3At: st.act3At,
        helixAt: st.helixAt,
        drawerCue: st.drawerCue,
      };
    },
    frame() {
      const st = useStore.getState();
      if (!st.model || !st.story) return null;
      const f = frameAt(st.model, st.story, st.s);
      return { s: f.s, act: f.act, simT: f.simT, run: f.run, seg: f.seg.kind, beat: f.seg.beat ?? null };
    },
    seek(s: number) {
      useStore.getState().seek(s);
    },
    play() {
      useStore.setState({ playing: true });
    },
    pause() {
      useStore.setState({ playing: false });
    },
    setSpeed(x: number) {
      useStore.setState({ speed: x });
    },
    setMode(m: 'story' | 'explore') {
      useStore.setState({ mode: m });
    },
    verify() {
      return runVerify(true).then(() => (window.__majlis as { audit: unknown }).audit);
    },
    force2D(reason = 'test') {
      useStore.getState().fallbackTo2D(reason);
    },
  };
  window.__majlis = api as unknown as Record<string, unknown>;
}

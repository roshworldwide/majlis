/**
 * The 2D Experience stage: the same story and the same magic moment, drawn in SVG (+ a canvas
 * layer for the evidence galaxy). Auto-selected when WebGL2 is unavailable, on context loss,
 * on low-power/low-fps devices, with ?lite=1, or with prefers-reduced-motion.
 * A pure function of story time `s` — all meaning lives in the DOM overlay.
 */
import { useEffect, useRef } from 'react';
import './stage2d.css';
import { useStore } from '../state/store';
import { ensureKb } from '../boot';
import { prefersReducedMotion } from '../lib/capability';
import { createScene, type Scene } from './scene';
import { VB_H, VB_W } from './geometry';

export default function Stage2D() {
  const host = useRef<HTMLDivElement>(null);
  const back = useRef<SVGSVGElement>(null);
  const front = useRef<SVGSVGElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const model = useStore((s) => s.model);
  const story = useStore((s) => s.story);

  useEffect(() => {
    try {
      ensureKb();
    } catch {
      /* galaxy stays empty; the story continues */
    }
  }, []);

  useEffect(() => {
    if (!model || !story || !host.current || !back.current || !front.current || !canvas.current) return;
    let scene: Scene | null = null;
    try {
      scene = createScene(host.current, back.current, front.current, canvas.current, model, story, prefersReducedMotion());
    } catch (e) {
      console.warn('[majlis] 2D stage could not initialise:', e instanceof Error ? e.message : e);
      return;
    }
    const sc = scene;
    const unsub = useStore.subscribe(() => sc.requestRender());
    sc.requestRender();
    return () => {
      unsub();
      sc.dispose();
    };
  }, [model, story]);

  const vb = `0 0 ${VB_W} ${VB_H}`;
  return (
    <div className="stage2d" data-testid="stage-2d" ref={host}>
      <svg ref={back} className="s2d-layer s2d-back" viewBox={vb} preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false" />
      <canvas ref={canvas} className="s2d-layer s2d-canvas" aria-hidden="true" />
      <svg
        ref={front}
        className="s2d-layer s2d-front"
        viewBox={vb}
        preserveAspectRatio="xMidYMid meet"
        role="group"
        aria-label="Council of AI institutions around the policy shield (2D view). Select an agent to see its beliefs, mandates and messages."
      />
    </div>
  );
}

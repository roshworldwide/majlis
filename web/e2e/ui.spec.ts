import { test, expect } from '@playwright/test';
import { collectErrors, seekPaused, settle, waitReady, type StoryInfo } from './helpers';

/** Overlay contract, modes, language, keyboard, reduced motion and WebGL context loss. */

test('overlay contract: chrome, labels, modes, language, keyboard', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto('?force3d=1&paused=1');
  await waitReady(page);
  const story = (await page.evaluate(() => (window as any).__majlis.story)) as StoryInfo;
  const act2 = story.acts.find((a) => a.act === 2)!.s;
  await seekPaused(page, act2 + 4);
  for (const id of ['app', 'topbar', 'fictional-pill', 'audit-badge', 'verify-btn', 'mode-story', 'mode-explore', 'lang-toggle', 'present-btn', 'sound-btn', 'scrubber', 'play-btn', 'speed-select', 'captions', 'act-label', 'hud', 'pipeline-rail']) {
    await expect.soft(page.getByTestId(id).first(), `missing data-testid="${id}"`).toBeVisible();
  }
  await expect.soft(page.getByTestId('fictional-pill').first()).toContainText(/fictional/i);

  // Explore mode shows the Adviser console
  await page.getByTestId('mode-explore').first().click();
  await settle(page, 600);
  await expect.soft(page.getByTestId('adviser').first(), 'Explore mode should show the Adviser console').toBeVisible();
  await page.getByTestId('mode-story').first().click();

  // EN / عربي
  await page.getByTestId('lang-toggle').first().click();
  await expect.poll(() => page.evaluate(() => document.documentElement.lang)).toBe('ar');
  await page.getByTestId('lang-toggle').first().click();
  await expect.poll(() => page.evaluate(() => document.documentElement.lang)).toBe('en');

  // keyboard: 1–4 jump between acts
  await page.locator('body').click({ position: { x: 5, y: 450 } }).catch(() => undefined);
  for (const k of ['3', '1', '4', '2']) {
    await page.keyboard.press(k);
    await expect.poll(() => page.evaluate(() => (window as any).__majlis.act)).toBe(Number(k));
  }
  expect(errors, errors.join('\n')).toEqual([]);
});

test('prefers-reduced-motion selects the 2D Experience', async ({ page }) => {
  const errors = collectErrors(page);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('?speed=8');
  await waitReady(page);
  const r = await page.evaluate(() => ({ renderer: (window as any).__majlis.renderer, reason: (window as any).__majlis.rendererReason }));
  expect(r.renderer).toBe('2d');
  expect(r.reason).toMatch(/reduced/i);
  await expect(page.getByTestId('stage-2d').first()).toBeVisible();
  expect(errors, errors.join('\n')).toEqual([]);
});

test('WebGL context loss: restores or falls back to 2D, never blank', async ({ page }, info) => {
  test.skip(info.project.name === 'chromium-nogl', 'no WebGL in this project');
  const errors = collectErrors(page);
  await page.goto('?force3d=1&speed=2');
  await waitReady(page);
  await page.waitForTimeout(2500);
  const lost = await page.evaluate(() => {
    const c = (document.querySelector('[data-testid="stage-3d"] canvas') || document.querySelector('canvas')) as HTMLCanvasElement | null;
    if (!c) return 'no canvas';
    const gl = (c.getContext('webgl2') || c.getContext('webgl')) as WebGLRenderingContext | null;
    const ext = gl?.getExtension('WEBGL_lose_context');
    if (!ext) return 'no WEBGL_lose_context';
    ext.loseContext();
    return 'lost';
  });
  test.skip(lost !== 'lost', `could not simulate context loss: ${lost}`);
  await page.waitForTimeout(4000);
  const r = await page.evaluate(() => ({ renderer: (window as any).__majlis.renderer, reason: (window as any).__majlis.rendererReason, s: (window as any).__majlis.s }));
  info.annotations.push({ type: 'context-loss', description: `${r.renderer} (${r.reason})` });
  console.log(`[${info.project.name}] after context loss: renderer=${r.renderer} reason="${r.reason}"`);
  const stage = r.renderer === '2d' ? page.getByTestId('stage-2d').first() : page.getByTestId('stage-3d').first();
  await expect(stage).toBeVisible();
  // the story clock keeps running
  const s2 = await page.waitForFunction((s0) => (window as any).__majlis.s > s0 + 0.5, r.s, { timeout: 10_000 }).then(() => true).catch(() => false);
  expect(s2).toBe(true);
  expect(errors.filter((e) => !/context lost/i.test(e)), errors.join('\n')).toEqual([]);
});

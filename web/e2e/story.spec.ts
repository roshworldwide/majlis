import { test, expect } from '@playwright/test';
import { actPoints, collectErrors, glRenderer, hasWebGL2, readReplay, seekPaused, shotPath, waitReady, type StoryInfo } from './helpers';

/**
 * Story mode plays to the end with zero console errors, in 3D (?force3d=1) and in the
 * 2D Experience (?lite=1). In the chromium-nogl project (WebGL disabled) the 3D variant
 * must fall back to 2D on its own. 5 screenshots per act are written to
 * test-results/screens/<project>/<variant>/.
 */
const VARIANTS = [
  { name: '3d', query: '?force3d=1&speed=8' },
  { name: 'lite', query: '?lite=1&speed=8' },
] as const;

for (const v of VARIANTS) {
  test.describe(`story · ${v.name}`, () => {
    test('plays to the end with zero console errors', async ({ page }, info) => {
      const errors = collectErrors(page);
      await page.goto(v.query);
      await waitReady(page);
      const webgl2 = await hasWebGL2(page);
      const gpu = await glRenderer(page);
      const initial = await page.evaluate(() => {
        const m = (window as any).__majlis;
        return { renderer: m.renderer as string, reason: m.rendererReason as string, duration: m.duration as number };
      });
      expect(initial.duration).toBeGreaterThan(30);

      await page.waitForFunction(() => (window as any).__majlis.ended === true, null, { timeout: 280_000, polling: 500 });
      const end = await page.evaluate(() => {
        const m = (window as any).__majlis;
        return { renderer: m.renderer as string, reason: m.rendererReason as string, s: m.s as number, duration: m.duration as number, quality: m.quality as string };
      });
      info.annotations.push({ type: 'renderer', description: `${end.renderer} (${end.reason}); quality=${end.quality}; webgl2=${webgl2}; gl="${gpu}"` });
      console.log(`[${info.project.name}/${v.name}] renderer=${end.renderer} reason="${end.reason}" quality=${end.quality} webgl2=${webgl2} gl="${gpu}"`);

      expect(end.s).toBeGreaterThanOrEqual(end.duration - 0.05);
      if (v.name === 'lite') {
        expect(end.renderer).toBe('2d');
      } else if (info.project.name === 'chromium-nogl' || !webgl2) {
        expect(end.renderer).toBe('2d');
        expect(end.reason.toLowerCase()).toContain('webgl');
      } else {
        // WebGL2 available + force3d: the 3D stage must survive the whole story (a fallback here means it crashed)
        expect.soft(end.renderer, `3D fell back to 2D: ${end.reason}`).toBe('3d');
      }
      expect(errors, errors.join('\n')).toEqual([]);
    });

    test('5 screenshots per act, magic moment, finale', async ({ page }, info) => {
      const errors = collectErrors(page);
      await page.goto(v.query + '&paused=1');
      await waitReady(page);
      await page.waitForTimeout(2500); // lazy 3D chunk, shader warm-up, kb_points
      const story = (await page.evaluate(() => (window as any).__majlis.story)) as StoryInfo;
      expect(story).toBeTruthy();

      for (const { act, points } of actPoints(story)) {
        for (let k = 0; k < points.length; k++) {
          await seekPaused(page, points[k]);
          await page.screenshot({ path: shotPath(info, v.name, `act${act}_${k + 1}.png`) });
        }
      }

      // THE MAGIC MOMENT: the first gate_block with a gap → Gap Card (DOM)
      const magic = story.gapCards.find((c) => c.style === 'magic');
      if (magic) {
        await seekPaused(page, magic.sIn + 0.6, 900);
        const card = page.getByTestId('gap-card').first();
        await expect(card).toBeVisible();
        await expect(card).toHaveAttribute('data-gap-id', magic.gap_id);
        await page.screenshot({ path: shotPath(info, v.name, 'magic_moment.png') });
      } else {
        info.annotations.push({ type: 'note', description: 'replay has no gate_block with a gap_id → no magic moment cue' });
      }

      // Finale: comparison bars + the quotable sentence
      await seekPaused(page, Math.min(story.finaleAt + 6, story.duration), 1200);
      await expect(page.getByTestId('finale')).toBeVisible();
      if (readReplay().meta?.quotable) await expect(page.getByTestId('quotable')).toBeVisible();
      await page.screenshot({ path: shotPath(info, v.name, 'finale.png') });

      // labels that must always be present
      await expect(page.getByTestId('fictional-pill')).toBeVisible();
      expect(errors, errors.join('\n')).toEqual([]);
    });
  });
}

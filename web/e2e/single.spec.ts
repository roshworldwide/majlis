import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { collectErrors, nodeVerify, auditPath, WEB_DIR } from './helpers';

/** The single-file build must open from file:// offline (data inlined at build time). */
const file = path.join(WEB_DIR, 'dist-single', 'majlis_experience.html');

test.use({ trace: 'off' });

test.describe('single-file build (file://)', () => {
  test('opens offline, verifies the audit chain, reaches the finale', async ({ page, context }) => {
    test.skip(!fs.existsSync(file), 'dist-single/majlis_experience.html not built');
    const errors = collectErrors(page);
    // offline: any http(s) request is a failure
    const external: string[] = [];
    await context.route(/^https?:\/\//, (route) => {
      external.push(route.request().url());
      return route.abort();
    });
    await page.goto(pathToFileURL(file).href + '?speed=8');
    await page.waitForFunction(() => (window as any).__majlis?.ready === true, null, { timeout: 60_000 });
    await page.waitForFunction(() => (window as any).__majlis.audit.state === 'done', null, { timeout: 30_000 });
    const a = await page.evaluate(() => (window as any).__majlis.audit);
    const expected = nodeVerify(fs.readFileSync(auditPath(), 'utf8'));
    expect(a.ok).toBe(true);
    expect(a.head).toBe(expected.head);
    const story = await page.evaluate(() => (window as any).__majlis.story);
    await page.evaluate((t) => { const m = (window as any).__majlis; m.pause(); m.seek(t); }, story.finaleAt + 6);
    await page.waitForTimeout(1200);
    await expect(page.getByTestId('finale')).toBeVisible();
    const r = await page.evaluate(() => ({ renderer: (window as any).__majlis.renderer, reason: (window as any).__majlis.rendererReason }));
    console.log(`[single/${test.info().project.name}] renderer=${r.renderer} (${r.reason})`);
    expect(external, external.join('\n')).toEqual([]);
    expect(errors, errors.join('\n')).toEqual([]);
  });
});

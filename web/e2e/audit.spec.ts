import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import { auditPath, collectErrors, nodeVerify, readReplay, waitReady } from './helpers';

/**
 * The in-browser audit verification (WebCrypto SHA-256) must match the CLI recipe exactly.
 * Expected values are computed here in Node from public/data/audit.jsonl — never hardcoded.
 */
const text = fs.readFileSync(auditPath(), 'utf8');
const expected = nodeVerify(text);

test.describe('audit chain', () => {
  test('Node recipe verifies the shipped chain', () => {
    expect(expected.bad).toEqual([]);
    expect(expected.ok).toBe(true);
    const root = readReplay().audit?.root;
    if (root) expect.soft(expected.head, 'replay.audit.root should be the chain head').toBe(root);
  });

  test('browser verification matches Node (badge + hooks)', async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto('?lite=1&paused=1&t=1');
    await waitReady(page);
    const btn = page.getByTestId('verify-btn').first();
    if (await btn.count()) await btn.click();
    else await page.evaluate(() => (window as any).__majlis.verify());
    await page.waitForFunction(() => (window as any).__majlis.audit.state === 'done', null, { timeout: 30_000 });
    const a = await page.evaluate(() => (window as any).__majlis.audit);
    expect(a.ok).toBe(true);
    expect(a.entries).toBe(expected.entries);
    expect(a.head).toBe(expected.head);
    const badge = page.getByTestId('audit-badge').first();
    await expect(badge).toContainText(`✓ ${expected.entries} entries verified`);
    await expect(badge).toContainText(new RegExp(`root\\s*${expected.head.slice(0, 4)}`));
    expect(errors, errors.join('\n')).toEqual([]);
  });

  test('a single edited byte is detected', async ({ page }) => {
    const lines = text.split('\n');
    const idx = lines.findIndex((l, i) => i >= Math.floor(lines.length / 2) && /"sim_minute":\d/.test(l));
    expect(idx).toBeGreaterThanOrEqual(0);
    // flip one digit of sim_minute (still valid JSON, so only the hash can catch it)
    lines[idx] = lines[idx].replace(/"sim_minute":(\d)/, (_m, d) => `"sim_minute":${(Number(d) + 1) % 10}`);
    const tampered = lines.join('\n');
    expect(nodeVerify(tampered).ok).toBe(false);
    const href = readReplay().audit?.href || 'audit.jsonl';
    await page.route(`**/data/${href}*`, (route) => route.fulfill({ status: 200, contentType: 'application/x-ndjson', body: tampered }));
    await page.goto('?lite=1&paused=1&t=1');
    await waitReady(page);
    await page.evaluate(() => (window as any).__majlis.verify());
    await page.waitForFunction(() => (window as any).__majlis.audit.state === 'done', null, { timeout: 30_000 });
    const a = await page.evaluate(() => (window as any).__majlis.audit);
    expect(a.ok).toBe(false);
    const badge = page.getByTestId('audit-badge').first();
    await expect(badge).not.toContainText(`✓ ${expected.entries} entries verified`);
    await expect(badge).toContainText(/not verified|✗|failed/i);
  });
});

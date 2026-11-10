/**
 * Live, in-browser audit-chain verification with WebCrypto SHA-256.
 * Byte-exact recipe (matches `majlis verify`): for each line L of audit.jsonl,
 *   h = JSON.parse(L).hash
 *   body = L with the exact substring `"hash":"<h>",` removed
 *   assert hex(sha256(utf8(body))) == h
 *   assert JSON.parse(L).prev_hash == previous h (genesis = 64 zeros)
 * JSON is never re-serialised.
 */
export interface AuditEntryResult {
  index: number;
  ok: boolean;
  hash: string;
  reason?: string;
}

export interface AuditResult {
  ok: boolean;
  entries: number;
  head: string; // hash of the last entry
  first: string; // hash of the first entry
  results: AuditEntryResult[];
  error?: string;
  ms: number;
}

const GENESIS = '0'.repeat(64);

function hex(buf: ArrayBuffer): string {
  const b = new Uint8Array(buf);
  let s = '';
  for (let i = 0; i < b.length; i++) s += b[i].toString(16).padStart(2, '0');
  return s;
}

export function splitLines(text: string): string[] {
  return text.split('\n').filter((l) => l.trim().length > 0).map((l) => (l.endsWith('\r') ? l.slice(0, -1) : l));
}

export async function verifyAudit(text: string | null): Promise<AuditResult> {
  const t0 = performance.now();
  if (!text) return { ok: false, entries: 0, head: '', first: '', results: [], error: 'audit.jsonl not available', ms: 0 };
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) {
    return { ok: false, entries: 0, head: '', first: '', results: [], error: 'WebCrypto unavailable in this context', ms: 0 };
  }
  const lines = splitLines(text);
  const enc = new TextEncoder();
  const results: AuditEntryResult[] = [];
  let prev = GENESIS;
  let allOk = true;
  for (let i = 0; i < lines.length; i++) {
    const L = lines[i];
    let h = '';
    let prevHash = '';
    try {
      const obj = JSON.parse(L) as { hash?: string; prev_hash?: string };
      h = String(obj.hash ?? '');
      prevHash = String(obj.prev_hash ?? '');
    } catch {
      results.push({ index: i, ok: false, hash: '', reason: 'line is not valid JSON' });
      allOk = false;
      prev = '';
      continue;
    }
    const needle = `"hash":"${h}",`;
    const at = L.indexOf(needle);
    if (at < 0) {
      results.push({ index: i, ok: false, hash: h, reason: 'hash field not found in canonical form' });
      allOk = false;
      prev = h;
      continue;
    }
    const body = L.slice(0, at) + L.slice(at + needle.length);
    const digest = hex(await subtle.digest('SHA-256', enc.encode(body)));
    let ok = digest === h;
    let reason: string | undefined;
    if (!ok) reason = 'content hash mismatch';
    if (prevHash !== prev) {
      ok = false;
      reason = reason ? reason + '; broken link' : 'broken link (prev_hash)';
    }
    if (!ok) allOk = false;
    results.push({ index: i, ok, hash: h, reason });
    prev = h;
  }
  return {
    ok: allOk && lines.length > 0,
    entries: lines.length,
    head: results.length ? results[results.length - 1].hash : '',
    first: results.length ? results[0].hash : '',
    results,
    ms: performance.now() - t0,
  };
}

"""The hash chain detects a single edited byte."""
from majlis.audit.chain import AuditLog, verify


def test_chain_detects_single_byte_edit(tmp_path):
    p = tmp_path / "audit.jsonl"
    log = AuditLog(p)
    for i in range(20):
        log.append("event", {"i": i, "text": f"payload {i}"}, sim_minute=i)
    ok, n, root, _ = verify(p)
    assert ok and n == 20 and root == log.root
    raw = bytearray(p.read_bytes())
    idx = raw.index(b"payload 7")
    raw[idx + 8] = ord("8")  # "payload 7" -> "payload 8": one byte
    p.write_bytes(bytes(raw))
    ok2, n2, _, msg = verify(p)
    assert not ok2 and n2 == 7 and "hash" in msg


def test_browser_recipe_matches(tmp_path):
    """Removing the exact `"hash":"<h>",` member from a line gives the hashed body (the Experience verifies this way)."""
    import hashlib
    import json

    p = tmp_path / "a.jsonl"
    log = AuditLog(p)
    log.append("x", {"ü": 1.5, "nested": {"b": [1, 2]}}, sim_minute=3)
    line = p.read_text().splitlines()[0]
    h = json.loads(line)["hash"]
    body = line.replace(f'"hash":"{h}",', "")
    assert hashlib.sha256(body.encode()).hexdigest() == h

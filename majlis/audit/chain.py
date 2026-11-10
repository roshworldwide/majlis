"""Append-only, SHA-256 hash-chained audit log (E3 / R6, Readiness d10_m09).

Each entry carries ``prev_hash``; its own ``hash`` is the SHA-256 of the
canonical JSON of the entry without the ``hash`` field. Editing a single byte
anywhere breaks verification from that entry onwards.

Wall-clock timestamps are deliberately *not* hashed: entries are stamped with
simulation time and a sequence number so that replays are bit-for-bit
reproducible (identical root hashes).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def entry_hash(entry: dict[str, Any]) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


class AuditLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")
        self.prev = GENESIS
        self.seq = 0
        self.counts: dict[str, int] = {}

    def append(self, event: str, payload: dict[str, Any], sim_minute: float | int | None = None) -> str:
        entry = {
            "seq": self.seq,
            "sim_minute": sim_minute,
            "event": event,
            "payload": payload,
            "prev_hash": self.prev,
        }
        entry["hash"] = entry_hash(entry)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(canonical(entry) + "\n")
        self.prev = entry["hash"]
        self.seq += 1
        self.counts[event] = self.counts.get(event, 0) + 1
        return entry["hash"]

    @property
    def root(self) -> str:
        return self.prev


def verify(path: Path) -> tuple[bool, int, str, str]:
    """Recompute the chain. Returns (ok, n_entries, root_hash, message)."""
    prev = GENESIS
    n = 0
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                return False, n, prev, f"line {lineno}: invalid JSON ({exc})"
            if entry.get("prev_hash") != prev:
                return False, n, prev, f"line {lineno}: prev_hash mismatch (chain broken)"
            if entry_hash(entry) != entry.get("hash"):
                return False, n, prev, f"line {lineno}: entry hash mismatch (entry was modified)"
            if canonical(entry) != line:
                return False, n, prev, f"line {lineno}: non-canonical serialisation (bytes modified)"
            prev = entry["hash"]
            n += 1
    return True, n, prev, "ok"

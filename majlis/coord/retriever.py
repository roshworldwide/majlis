"""Retrieval wrapper with an on-disk cache so ``--replay`` is offline and exact.

Live runs write ``cache/retrieval/<hash>.json`` (chunk ids + scores). Replay
reads them back and rebuilds hits from ``kb/export/chunks.jsonl``; a cache
miss in replay falls back to BM25-only retrieval and is logged.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from majlis import config
from majlis.kb.store import KB, Hit

CACHE_DIR = config.ROOT / "cache" / "retrieval"


class Retriever:
    def __init__(self, kb: KB, replay: bool = False):
        self.kb = kb
        self.replay = replay
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.stats = {"queries": 0, "cache_hits": 0, "misses": 0}

    def search(self, query: str, k: int = 5, collections: list[str] | None = None, agent: str = "", t: int | None = None,
               audit=None, mode: str = "hybrid") -> list[Hit]:
        self.stats["queries"] += 1
        key = hashlib.sha256(json.dumps([query, k, sorted(collections or []), mode]).encode()).hexdigest()[:32]
        path = CACHE_DIR / f"{key}.json"
        hits: list[Hit] | None = None
        source = "live"
        if path.exists():
            data = json.loads(path.read_text())
            hits = []
            for r in data["hits"]:
                c = self.kb.get(r["chunk_id"])
                if c is None:
                    hits = None
                    break
                hits.append(Hit(chunk_id=c["chunk_id"], doc_id=c["doc_id"], score=r["score"], rank=r["rank"], text=c["text"],
                                meta={k2: v for k2, v in c.items() if k2 != "text"}))
            if hits is not None:
                self.stats["cache_hits"] += 1
                source = "cache"
        if hits is None:
            if self.replay:
                self.stats["misses"] += 1
                hits = self.kb.search(query, k=k, collections=collections, mode="bm25")
                source = "bm25 (replay cache miss)"
            else:
                hits = self.kb.search(query, k=k, collections=collections, mode=mode)
                path.write_text(json.dumps({"query": query, "k": k, "collections": collections, "mode": mode,
                                            "hits": [{"chunk_id": h.chunk_id, "score": round(float(h.score), 6),
                                                      "rank": h.rank} for h in hits]}))
        if audit is not None:
            audit.append("retrieval", {"agent": agent, "query": query[:300], "collections": collections or [],
                                       "mode": mode, "source": source,
                                       "top_k": [{"chunk_id": h.chunk_id, "score": round(float(h.score), 5)} for h in hits]},
                         sim_minute=t)
        return hits

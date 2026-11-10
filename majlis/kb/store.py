"""Knowledge base: ingest (PP node) and hybrid retrieval (part of the M node).

* Canonical chunk store: ``kb/export/chunks.jsonl`` (verbatim text + metadata).
  The P-node gate validates every quote against this file.
* Vector store: ChromaDB persistent collections with the reference names
  (kb_main, kb_framework, kb_usecase, kb_decisions) plus kb_uae,
  kb_global_examples, kb_mandates. Embeddings: Ollama nomic-embed-text.
* Retrieval: BM25 (rank-bm25) + dense cosine, fused with reciprocal rank
  fusion (k=60); filters by collection, country and doc_type. Offline
  fallback for the dense side: TF-IDF + LSA (scikit-learn).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import httpx
import numpy as np

from majlis import config
from majlis.kb.textnorm import tokens

RRF_K = 60
QUERY_CACHE = config.ROOT / "cache" / "emb_queries.json"


@dataclass
class Hit:
    chunk_id: str
    doc_id: str
    score: float
    rank: int
    text: str
    meta: dict[str, Any]

    def cite(self) -> dict[str, Any]:
        m = self.meta
        return {"doc_id": self.doc_id, "chunk_id": self.chunk_id, "title": m.get("title"), "page": m.get("page"),
                "article": m.get("article"), "url": m.get("url"), "score": round(float(self.score), 5)}


def index_text(c: dict[str, Any]) -> str:
    head = " — ".join(x for x in [c.get("title", ""), c.get("article", ""), c.get("section", "")] if x)
    return f"{head}\n{c['text']}"


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:24]


# ----------------------------------------------------------------------------
# Embeddings
# ----------------------------------------------------------------------------

class Embedder:
    """nomic-embed-text through Ollama, with an on-disk cache keyed by text hash."""

    def __init__(self, model: str = config.EMBED_MODEL, base_url: str = config.OLLAMA_BASE_URL, offline: bool = False):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.offline = offline
        self._qcache: dict[str, list[float]] | None = None

    def available(self) -> bool:
        if self.offline:
            return False
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=3)
            names = [m.get("name", "") for m in r.json().get("models", [])]
            return any(n.split(":")[0] == self.model.split(":")[0] for n in names)
        except Exception:
            return False

    def _embed(self, texts: list[str]) -> list[list[float]]:
        r = httpx.post(f"{self.base_url}/api/embed", json={"model": self.model, "input": texts, "truncate": True,
                                                            "options": {"num_ctx": 2048}}, timeout=600)
        r.raise_for_status()
        return r.json()["embeddings"]

    def embed_documents(self, texts: list[str], batch: int = 32, progress=None) -> np.ndarray:
        config.EMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = config.EMB_CACHE_DIR / f"docs_{self.model.replace(':', '_')}.npz"
        cache: dict[str, np.ndarray] = {}
        if cache_path.exists():
            z = np.load(cache_path, allow_pickle=False)
            cache = {k: v for k, v in zip(z["keys"], z["vecs"])}
        keys = [_h("search_document: " + t[:3000]) for t in texts]
        todo = [i for i, k in enumerate(keys) if k not in cache]
        for s in range(0, len(todo), batch):
            idx = todo[s:s + batch]
            vecs = self._embed(["search_document: " + texts[i][:3000] for i in idx])
            for i, v in zip(idx, vecs):
                cache[keys[i]] = np.asarray(v, dtype=np.float32)
            if progress:
                progress(min(s + batch, len(todo)), len(todo))
            if (s // batch) % 25 == 24:  # save progress incrementally
                np.savez(cache_path, keys=np.array(list(cache.keys())), vecs=np.stack(list(cache.values())))
        if todo:
            np.savez(cache_path, keys=np.array(list(cache.keys())), vecs=np.stack(list(cache.values())))
        return np.stack([cache[k] for k in keys]) if keys else np.zeros((0, 768), dtype=np.float32)

    def embed_query(self, q: str) -> np.ndarray | None:
        if self._qcache is None:
            self._qcache = json.loads(QUERY_CACHE.read_text()) if QUERY_CACHE.exists() else {}
        key = _h(self.model + "|search_query: " + q)
        if key in self._qcache:
            return np.asarray(self._qcache[key], dtype=np.float32)
        if self.offline:
            return None
        try:
            v = self._embed(["search_query: " + q])[0]
        except Exception:
            return None
        self._qcache[key] = [round(float(x), 6) for x in v]
        QUERY_CACHE.parent.mkdir(parents=True, exist_ok=True)
        QUERY_CACHE.write_text(json.dumps(self._qcache))
        return np.asarray(v, dtype=np.float32)


# ----------------------------------------------------------------------------
# Knowledge base
# ----------------------------------------------------------------------------

class KB:
    def __init__(self, chunks_path: Path = config.CHUNKS_PATH, offline: bool = False, load_dense: bool = True):
        self.chunks: list[dict[str, Any]] = load_chunks(chunks_path)
        self.by_id = {c["chunk_id"]: c for c in self.chunks}
        self.ids = [c["chunk_id"] for c in self.chunks]
        self._col = np.array([c.get("collection", "") for c in self.chunks])
        self._country = np.array([str(c.get("country", "")) for c in self.chunks])
        self._doctype = np.array([str(c.get("doc_type", "")) for c in self.chunks])
        self._docid = np.array([c["doc_id"] for c in self.chunks])
        from rank_bm25 import BM25Okapi

        self._bm25 = BM25Okapi([tokens(index_text(c)) or ["_"] for c in self.chunks]) if self.chunks else None
        self.embedder = Embedder(offline=offline)
        self.dense_backend = "none"
        self._mat: np.ndarray | None = None
        self._lsa = None
        if load_dense and self.chunks:
            self._load_dense()

    # -- dense side --------------------------------------------------------
    def _load_dense(self) -> None:
        mpath = config.EMB_CACHE_DIR / "matrix.npy"
        ipath = config.EMB_CACHE_DIR / "matrix_ids.json"
        if mpath.exists() and ipath.exists():
            ids = json.loads(ipath.read_text())
            if ids == self.ids:
                m = np.load(mpath)
                self._mat = m / np.clip(np.linalg.norm(m, axis=1, keepdims=True), 1e-9, None)
                self.dense_backend = "nomic-embed-text"
                return
        self._fit_lsa()

    def _fit_lsa(self) -> None:
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer

        texts = [index_text(c) for c in self.chunks]
        vec = TfidfVectorizer(max_features=60000, sublinear_tf=True, ngram_range=(1, 2), min_df=1)
        X = vec.fit_transform(texts)
        n_comp = max(2, min(256, X.shape[1] - 1, X.shape[0] - 1))
        svd = TruncatedSVD(n_components=n_comp, random_state=0)
        Z = svd.fit_transform(X)
        self._mat = Z / np.clip(np.linalg.norm(Z, axis=1, keepdims=True), 1e-9, None)
        self._lsa = (vec, svd)
        self.dense_backend = "tfidf-lsa (offline fallback)"

    def _qvec(self, q: str) -> np.ndarray | None:
        if self._lsa is not None:
            vec, svd = self._lsa
            z = svd.transform(vec.transform([q]))[0]
            return z / max(np.linalg.norm(z), 1e-9)
        v = self.embedder.embed_query(q)
        if v is None:
            # dense unavailable for this query (offline, uncached): fit LSA lazily
            self._fit_lsa()
            return self._qvec(q)
        return v / max(np.linalg.norm(v), 1e-9)

    # -- search --------------------------------------------------------------
    def _mask(self, collections: Iterable[str] | None, country: str | None, doc_type: str | None,
              doc_ids: Iterable[str] | None = None) -> np.ndarray:
        m = np.ones(len(self.chunks), dtype=bool)
        if collections:
            m &= np.isin(self._col, list(collections))
        if country:
            m &= self._country == country
        if doc_type:
            m &= self._doctype == doc_type
        if doc_ids:
            m &= np.isin(self._docid, list(doc_ids))
        return m

    def _rank_bm25(self, q: str, mask: np.ndarray, n: int) -> list[tuple[int, float]]:
        scores = np.asarray(self._bm25.get_scores(tokens(q) or ["_"]), dtype=np.float64)
        scores[~mask] = -np.inf
        order = np.argsort(-scores, kind="stable")[:n]
        return [(int(i), float(scores[i])) for i in order if np.isfinite(scores[i]) and scores[i] > 0]

    def _rank_dense(self, q: str, mask: np.ndarray, n: int) -> list[tuple[int, float]]:
        if self._mat is None:
            return []
        v = self._qvec(q)
        if v is None or v.shape[0] != self._mat.shape[1]:
            return []
        sims = self._mat @ v
        sims = np.where(mask, sims, -np.inf)
        order = np.argsort(-sims, kind="stable")[:n]
        return [(int(i), float(sims[i])) for i in order if np.isfinite(sims[i])]

    def search(self, query: str, k: int = 5, collections: Iterable[str] | None = None, country: str | None = None,
               doc_type: str | None = None, mode: str = "hybrid", doc_ids: Iterable[str] | None = None) -> list[Hit]:
        if not self.chunks:
            return []
        mask = self._mask(collections, country, doc_type, doc_ids)
        pool = max(50, k * 10)
        if mode == "bm25":
            ranked = self._rank_bm25(query, mask, k)
        elif mode == "dense":
            ranked = self._rank_dense(query, mask, k)
        else:
            fused: dict[int, float] = {}
            for lst in (self._rank_bm25(query, mask, pool), self._rank_dense(query, mask, pool)):
                for r, (i, _) in enumerate(lst):
                    fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + r + 1)
            ranked = sorted(fused.items(), key=lambda t: (-t[1], self.ids[t[0]]))[:k]
        hits = []
        for r, (i, s) in enumerate(ranked[:k]):
            c = self.chunks[i]
            hits.append(Hit(chunk_id=c["chunk_id"], doc_id=c["doc_id"], score=s, rank=r + 1, text=c["text"],
                            meta={k2: v for k2, v in c.items() if k2 != "text"}))
        return hits

    def get(self, chunk_id: str) -> dict[str, Any] | None:
        return self.by_id.get(chunk_id)

    def stats(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for c in self.chunks:
            col = c.get("collection", "?")
            out.setdefault(col, {"chunks": 0, "docs": set()})
            out[col]["chunks"] += 1
            out[col]["docs"].add(c["doc_id"])
        return {k: {"chunks": v["chunks"], "docs": len(v["docs"])} for k, v in sorted(out.items())}


def load_chunks(path: Path = config.CHUNKS_PATH) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    paths: list[Path] = []
    if path.exists():
        paths = [path]
    else:  # per-collection export files (possibly gzipped)
        paths = sorted(path.parent.glob("chunks_*.jsonl")) + sorted(path.parent.glob("chunks_*.jsonl.gz"))
    for p in paths:
        if p.suffix == ".gz":
            import gzip

            fh = gzip.open(p, "rt", encoding="utf-8")
        else:
            fh = p.open(encoding="utf-8")
        with fh:
            for line in fh:
                if line.strip():
                    chunks.append(json.loads(line))
    return chunks

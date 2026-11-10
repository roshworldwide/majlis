"""Ingest pipeline: manifest → parse → chunk → tag → chunks.jsonl → embeddings → ChromaDB.

Mirrors the reference ``server/knowledge/ingest.py`` (document_category tags,
kb_framework from dimensions.json, kb_usecase for AI_Use_Cases) and extends it
with legal-structure-aware chunking, page/article metadata, SHA-256
provenance and three new collections (kb_uae, kb_global_examples, kb_mandates).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from majlis import config
from majlis.kb import tags
from majlis.kb.chunk import chunk_document, profile_for
from majlis.kb.collect import local_path, read_manifest
from majlis.kb.parse import parse_file
from majlis.kb.store import Embedder, index_text

META_FIELDS = ["doc_id", "title", "issuer", "country", "doc_type", "document_category", "collection", "date", "url",
               "retrieved_at", "sha256", "license_note"]


def build_document_chunks(row: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    pages = parse_file(path, strip_running=not row["doc_id"].startswith("REF-"))
    if not any(t.strip() for _, t in pages):
        return []
    profile = profile_for(row["doc_id"], row.get("doc_type", ""), row.get("country", ""))
    sidecar = path.parent / (path.name + ".ocr.json")
    ocr_pages = {int(k) for k in json.loads(sidecar.read_text()).get("pages", {})} if sidecar.exists() else set()
    out = []
    for i, ch in enumerate(chunk_document(pages, profile)):
        if len(ch.text.split()) < 12:
            continue
        rec = {k: row.get(k, "") for k in META_FIELDS}
        rec.update({
            "chunk_id": f"{row['doc_id']}::{i:04d}",
            "text": ch.text,
            "page": ch.page,
            "page_end": ch.page_end,
            "section": ch.section,
            "article": ch.article,
            "articles": ch.articles,
            "n_words": len(ch.text.split()),
        })
        if ocr_pages and any(pg in ocr_pages for pg in range(ch.page, ch.page_end + 1)):
            rec["ocr"] = True  # text from tesseract OCR of a scanned page — re-check quotes against the page image
        rec["readiness_dims"] = tags.readiness_dims(ch.text)
        rec["y3172_nodes"] = tags.y3172_nodes(ch.text)
        out.append(rec)
    return out


def framework_chunks() -> list[dict[str, Any]]:
    data = tags.dimensions()
    src = "https://github.com/CrashingGuru/ITUAIReadiness/blob/main/simulation/data/framework/dimensions.json"
    out = []
    for dim in data["dimensions"]:
        metrics = "\n".join(f"- {m['id']} {m['name']}: {m['description']}" for m in dim["metrics"])
        text = (f"Dimension {dim['id']}: {dim['name']} ({dim['short_name']})\n\n{dim['description']}\n\n"
                f"Mapped Factors: {', '.join(dim['mapped_factors'])}\n\nMetrics:\n{metrics}")
        out.append({
            "doc_id": "ITU-AIREADY-DIMENSIONS", "title": f"ITU AI Readiness Framework — {data.get('framework_version', '')} dimensions",
            "issuer": "ITU (via CrashingGuru/ITUAIReadiness, MIT)", "country": "ITU", "doc_type": "framework",
            "document_category": "Framework", "collection": "kb_framework", "date": "2025", "url": src,
            "retrieved_at": "", "sha256": "", "license_note": "MIT (reference repository)",
            "chunk_id": f"ITU-AIREADY-DIMENSIONS::d{dim['id']:02d}", "text": text, "page": 1, "page_end": 1,
            "section": "", "article": f"Dimension {dim['id']}", "articles": [f"Dimension {dim['id']}"],
            "n_words": len(text.split()), "readiness_dims": [f"d{dim['id']}"], "y3172_nodes": [],
        })
    for f in data["factors"]:
        text = f"Factor: {f['name']}\n\n{f['description']}"
        out.append({
            "doc_id": "ITU-AIREADY-DIMENSIONS", "title": "ITU AI Readiness Framework — factors", "issuer": "ITU",
            "country": "ITU", "doc_type": "framework", "document_category": "Framework", "collection": "kb_framework",
            "date": "2025", "url": src, "retrieved_at": "", "sha256": "", "license_note": "MIT (reference repository)",
            "chunk_id": f"ITU-AIREADY-DIMENSIONS::factor-{f['id']}", "text": text, "page": 1, "page_end": 1,
            "section": "", "article": f"Factor {f['id']}", "articles": [f"Factor {f['id']}"],
            "n_words": len(text.split()), "readiness_dims": [], "y3172_nodes": [],
        })
    return out


def run_ingest(skip_main: bool = False, embed: bool = True, chroma: bool = True, verbose: bool = True) -> dict[str, Any]:
    rows = read_manifest()
    chunks: list[dict[str, Any]] = []
    skipped = []
    for row in rows:
        if skip_main and row.get("collection") == "kb_main":
            continue
        p = local_path(row)
        if p is None:
            skipped.append((row["doc_id"], row.get("status", "no local file")))
            continue
        try:
            recs = build_document_chunks(row, p)
        except Exception as exc:
            skipped.append((row["doc_id"], f"parse error: {exc}"))
            continue
        if not recs:
            skipped.append((row["doc_id"], "no text extracted (scanned/empty)"))
            continue
        chunks.extend(recs)
        if verbose:
            print(f"  {row['doc_id']:<44} {row.get('collection',''):<20} {len(recs):>5} chunks")
    chunks.extend(framework_chunks())
    # kb_mandates: derived chunks, appended after mandates validation (see majlis.agents.mandates)
    from majlis.agents.mandates import mandate_chunks

    chunks.extend(mandate_chunks(chunks))
    config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    with config.CHUNKS_PATH.open("w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    info: dict[str, Any] = {"chunks": len(chunks), "skipped": skipped}
    if embed:
        emb = Embedder()
        if emb.available():
            texts = [index_text(c) for c in chunks]

            def prog(done, total):
                if verbose and (done % 512 < 32 or done == total):
                    print(f"    embedded {done}/{total}")

            mat = emb.embed_documents(texts, progress=prog)
            config.EMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            np.save(config.EMB_CACHE_DIR / "matrix.npy", mat)
            (config.EMB_CACHE_DIR / "matrix_ids.json").write_text(json.dumps([c["chunk_id"] for c in chunks]))
            info["dense"] = "nomic-embed-text"
            if chroma:
                info["chroma"] = persist_chroma(chunks, mat)
        else:
            info["dense"] = "unavailable (Ollama not reachable) — retrieval falls back to TF-IDF/LSA"
    return info


def persist_chroma(chunks: list[dict[str, Any]], mat: np.ndarray) -> dict[str, int]:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR), settings=ChromaSettings(anonymized_telemetry=False))
    counts: dict[str, int] = {}
    by_col: dict[str, list[int]] = {}
    for i, c in enumerate(chunks):
        by_col.setdefault(c["collection"], []).append(i)
    for name in config.COLLECTIONS:
        try:
            client.delete_collection(name)
        except Exception:
            pass
        col = client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
        idx = by_col.get(name, [])
        for s in range(0, len(idx), 2000):
            part = idx[s:s + 2000]
            col.add(
                ids=[chunks[i]["chunk_id"] for i in part],
                documents=[chunks[i]["text"] for i in part],
                embeddings=[mat[i].tolist() for i in part],
                metadatas=[_flat_meta(chunks[i]) for i in part],
            )
        counts[name] = col.count()
    return counts


def _flat_meta(c: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in c.items():
        if k == "text":
            continue
        if isinstance(v, list):
            v = ";".join(str(x) for x in v)
        if v is None:
            v = ""
        out[k] = v if isinstance(v, (str, int, float, bool)) else str(v)
    # reference-compatible keys
    out.setdefault("source_file", c.get("doc_id", ""))
    out["source_type"] = c.get("doc_type", "")
    return out

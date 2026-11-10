"""Load the MAJLIS KB export into the ITU reference server (CrashingGuru/ITUAIReadiness, MIT).

Uses the reference code's own ``KnowledgeBase`` and ``embed_texts`` (Ollama
nomic-embed-text), so the chunks land in its ChromaDB exactly as its own ingest
would store them: reference metadata keys (source_file, source_type, country,
document_category, chunk_index) are filled, MAJLIS provenance keys (doc_id,
article, page, url, sha256, licence) are kept alongside.

    python scripts/load_into_ituaireadiness.py --ref ../_ref/ITUAIReadiness/simulation \
        --collections kb_uae,kb_global_examples,kb_mandates [--limit N] [--persist DIR]

The reference server then serves them through its normal routes; kb_uae etc. are
new collections next to its kb_main / kb_framework / kb_usecase / kb_decisions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=Path, default=ROOT.parent / "_ref" / "ITUAIReadiness" / "simulation")
    ap.add_argument("--chunks", type=Path, default=ROOT / "kb" / "export" / "chunks.jsonl")
    ap.add_argument("--collections", default="kb_uae,kb_global_examples,kb_mandates")
    ap.add_argument("--limit", type=int, default=0, help="max chunks per collection (0 = all)")
    ap.add_argument("--persist", type=Path, default=None, help="ChromaDB dir (default: the reference server's data/chromadb)")
    args = ap.parse_args()

    sys.path.insert(0, str(args.ref))
    from server.knowledge.ingest import embed_texts  # reference code
    from server.knowledge.kb import KnowledgeBase  # reference code

    kb = KnowledgeBase(persist_dir=str(args.persist) if args.persist else None)
    wanted = [c.strip() for c in args.collections.split(",") if c.strip()]
    rows = [json.loads(l) for l in args.chunks.read_text(encoding="utf-8").splitlines() if l.strip()]
    report = {}
    for col in wanted:
        sel = [r for r in rows if r.get("collection") == col]
        if args.limit:
            sel = sel[: args.limit]
        if not sel:
            continue
        texts = [r["text"] for r in sel]
        metas = []
        for i, r in enumerate(sel):
            m = {"source_file": r["doc_id"], "source_type": r.get("doc_type", ""), "country": str(r.get("country", "")),
                 "document_category": r.get("document_category", ""), "chunk_index": str(i), "total_chunks": str(len(sel))}
            for k in ("doc_id", "chunk_id", "title", "issuer", "article", "page", "url", "sha256", "license_note", "date"):
                v = r.get(k)
                m[k] = "" if v is None else str(v)
            metas.append(m)
        emb = embed_texts(texts)
        kb.add_documents(texts=texts, embeddings=emb, metadatas=metas, collection_name=col,
                         ids=[r["chunk_id"] for r in sel])
        report[col] = kb.count(col)
        # prove retrieval works through the reference KnowledgeBase API
        q = embed_texts(["Which authority oversees the telecommunications sector and licensees?"])[0]
        hit = kb.search(q, n_results=1, collection_name=col)
        report[col + ":top1"] = (hit.get("metadatas") or [[{}]])[0][0].get("chunk_id", "")
    print(json.dumps({"loaded": report, "reference_stats": kb.stats()}, indent=1))


if __name__ == "__main__":
    main()

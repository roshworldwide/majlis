"""KB retrieval evaluation: hit@1/3/5 and MRR for BM25, dense and hybrid (RRF).

A hit = a retrieved chunk whose doc_id matches a gold doc and, when the gold
names an article, whose article labels include it. Results → results/kb_eval.json.
"""

from __future__ import annotations

import json
from typing import Any

from majlis import config
from majlis.kb.store import KB


def _is_hit(hit, gold: list[dict[str, str]]) -> bool:
    arts = set(hit.meta.get("articles") or []) | {hit.meta.get("article") or ""}
    for g in gold:
        if hit.doc_id == g["doc_id"] and (not g.get("article") or g["article"] in arts):
            return True
    return False


def run_eval(k: int = 5, kb: KB | None = None) -> dict[str, Any]:
    kb = kb or KB()
    qs = [json.loads(l) for l in (config.EVAL_DIR / "kb_questions.jsonl").read_text().splitlines() if l.strip()]
    present = {(c["doc_id"], a) for c in kb.chunks for a in (c.get("articles") or [""])} | {(c["doc_id"], "") for c in kb.chunks}
    unreachable = [q["id"] for q in qs if not any((g["doc_id"], g.get("article", "")) in present for g in q["gold"])]
    out: dict[str, Any] = {"n_questions": len(qs), "k": k, "dense_backend": kb.dense_backend,
                           "unreachable_gold": unreachable, "retrievers": {}, "per_question": []}
    per_q: dict[str, dict[str, Any]] = {q["id"]: {"id": q["id"], "layer": q["layer"], "question": q["question"]} for q in qs}
    for mode in ("bm25", "dense", "hybrid"):
        h1 = h3 = h5 = 0
        rr = 0.0
        by_layer: dict[str, list[int]] = {}
        for q in qs:
            hits = kb.search(q["question"], k=10, mode=mode,
                             collections=["kb_uae", "kb_global_examples", "kb_usecase", "kb_framework", "kb_main"])
            rank = next((h.rank for h in hits if _is_hit(h, q["gold"])), None)
            h1 += rank is not None and rank <= 1
            h3 += rank is not None and rank <= 3
            h5 += rank is not None and rank <= 5
            rr += 1.0 / rank if rank else 0.0
            by_layer.setdefault(q["layer"], []).append(1 if (rank and rank <= 5) else 0)
            per_q[q["id"]][f"{mode}_rank"] = rank
            if mode == "hybrid":
                per_q[q["id"]]["hybrid_top1"] = hits[0].chunk_id if hits else None
        n = len(qs)
        out["retrievers"][mode] = {"hit@1": round(h1 / n, 3), "hit@3": round(h3 / n, 3), "hit@5": round(h5 / n, 3),
                                   "mrr": round(rr / n, 3),
                                   "hit@5_by_layer": {l: round(sum(v) / len(v), 3) for l, v in by_layer.items()}}
    out["per_question"] = list(per_q.values())
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.RESULTS_DIR / "kb_eval.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out

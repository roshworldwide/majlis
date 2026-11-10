"""export-replay: runs/<id>/ → web/public/data/{replay.json, audit.jsonl, kb_points.bin}.

Citations are keyed ``<chunk_id>|<sha8(quote)>`` so every beam in the front
end lands on one exact, gate-verified quote. kb_points.bin is a 3-D PCA of
the real chunk embeddings (nomic-embed-text), or of TF-IDF/LSA vectors when
embeddings are unavailable; the layout used is recorded in replay.json.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from majlis import config
from majlis.agents.mandates import load_registry
from majlis.kb.store import load_chunks
from majlis.kb.textnorm import quote_in
from majlis.report.replay import validate, write_points
from majlis.scenario.loader import load_reform, load_scenario

CLUSTER = {"kb_uae": 0, "kb_mandates": 0, "kb_global_examples": 1, "kb_usecase": 2, "kb_framework": 2, "kb_main": 3}
CLUSTER_NAME = {0: "uae", 1: "global", 2: "itu", 3: "other"}


def _load(run: str) -> dict[str, Any] | None:
    d = config.RUNS_DIR / run
    if not (d / "timeline.json").exists():
        return None
    r = lambda n: json.loads((d / n).read_text(encoding="utf-8"))
    return {"dir": d, "timeline": r("timeline.json"), "gaps": r("gaps.json"), "kpis": r("kpis.json"), "meta": r("meta.json"),
            "metrics": r("metrics.json"), "qa": r("adviser_qa.json")}


class Cites:
    def __init__(self, chunks: list[dict[str, Any]]):
        self.by_id = {c["chunk_id"]: c for c in chunks}
        self.index = {c["chunk_id"]: i for i, c in enumerate(chunks)}
        self.items: dict[str, dict[str, Any]] = {}
        self.first: dict[str, str] = {}

    def add(self, chunk_id: str | None, quote: str, article: str = "") -> str | None:
        if not chunk_id or chunk_id not in self.by_id:
            return None
        c = self.by_id[chunk_id]
        cid = f"{chunk_id}|{hashlib.sha256(quote.encode()).hexdigest()[:8]}"
        if cid not in self.items:
            self.items[cid] = {"doc_id": c["doc_id"], "chunk_id": chunk_id, "title": c.get("title", ""),
                               "issuer": c.get("issuer", ""), "article": article or c.get("article") or "",
                               "page": c.get("page"), "quote": quote, "url": c.get("url", ""),
                               "verified": quote_in(quote, c["text"]),
                               "cluster": CLUSTER_NAME[CLUSTER.get(c.get("collection", ""), 3)],
                               "star_index": self.index.get(chunk_id), "ocr": bool(c.get("ocr"))}
        self.first.setdefault(chunk_id, cid)
        return cid


def kb_points(chunks: list[dict[str, Any]], out: Path) -> tuple[int, str]:
    mpath = config.EMB_CACHE_DIR / "matrix.npy"
    ipath = config.EMB_CACHE_DIR / "matrix_ids.json"
    layout = "pca3(nomic-embed-text)"
    X = None
    if mpath.exists() and ipath.exists() and json.loads(ipath.read_text()) == [c["chunk_id"] for c in chunks]:
        X = np.load(mpath).astype(np.float64)
    if X is None:
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer

        X = TruncatedSVD(n_components=32, random_state=0).fit_transform(
            TfidfVectorizer(max_features=30000, sublinear_tf=True).fit_transform([c["text"] for c in chunks]))
        layout = "pca3(tfidf-lsa)"
    X = X - X.mean(axis=0)
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    P = U[:, :3] * S[:3]
    P = P / (np.abs(P).max(axis=0) + 1e-9) * 1.6
    write_points(out / "kb_points.bin", [tuple(map(float, p)) for p in P],
                 [CLUSTER.get(c.get("collection", ""), 3) for c in chunks])
    return len(chunks), layout


def export(run: str = "golden", compare: str | None = "reform", out: Path | None = None) -> dict[str, Any]:
    out = out or (config.ROOT / "web" / "public" / "data")
    out.mkdir(parents=True, exist_ok=True)
    base = _load(run)
    if base is None:
        raise SystemExit(f"run {run!r} not found")
    rf = _load(compare) if compare else None
    sc = load_scenario(base["meta"]["scenario"])
    chunks = load_chunks()
    cites = Cites(chunks)
    reg = load_registry(sc.country, chunks)

    agents = []
    for aid, a in sc.agents.items():
        mands = [{"id": m.mandate_id, "title": m.title, "action_types": m.action_types,
                  "citations": [cites.add(c.chunk_id, c.quote, c.article) for c in m.legal_basis]} for m in reg.mandates_for(aid)]
        agents.append({"id": aid, "name": a["name"], "name_ar": a["name_ar"], "role_type": a["role_type"],
                       "modelled_on": a["modelled_on"], "color": a["color"], "mandates": mands,
                       "note": reg.institutions.get(aid, {}).get("note", "")})

    def channels_for(r: dict[str, Any], reform_doc: dict[str, Any] | None) -> list[dict[str, Any]]:
        out_ch = [{"from": c.src, "to": c.dst, "legal": True, "citation": cites.add(c.legal_basis[0].chunk_id, c.legal_basis[0].quote, c.legal_basis[0].article),
                   "type": c.type, "latency_min": c.latency_min, "origin": "law", "id": c.channel_id} for c in reg.channels]
        if reform_doc:
            by_doc: dict[str, list] = {}
            for ch in chunks:
                by_doc.setdefault(ch["doc_id"], []).append(ch)
            from majlis.agents.mandates import resolve_citation

            for rule in reform_doc.get("rules", []):
                basis = [resolve_citation(b, by_doc) for b in rule.get("global_basis", [])]
                basis = [b for b in basis if b.valid]
                for ch in rule.get("adds_channels", []):
                    out_ch.append({"from": ch["from"], "to": ch["to"], "legal": True,
                                   "citation": cites.add(basis[0].chunk_id, basis[0].quote, basis[0].article) if basis else None,
                                   "type": ch.get("type", rule["id"]), "latency_min": ch.get("latency_min", 5), "origin": "reform",
                                   "id": ch["channel_id"], "rule": rule["id"]})
        for p in r["metrics"].get("missing_channel_pairs", []):
            a, b = p.split("→")
            if not any(c["from"] == a and c["to"] == b for c in out_ch):
                out_ch.append({"from": a, "to": b, "legal": False, "citation": None, "type": "none",
                               "latency_min": sc.params.get("informal_latency_min", 35), "origin": "missing"})
        return out_ch

    def tl_for(r: dict[str, Any]) -> list[dict[str, Any]]:
        tl = []
        for e in r["timeline"]:
            p = dict(e["payload"])
            if e["type"] == "proposal":
                for ar in p.get("applicable_rules", []):
                    ar["cite_id"] = cites.add(ar.get("chunk_id"), ar.get("quote") or "") if ar.get("valid") else None
            if e["type"] in ("gate_pass", "action"):
                p["cite_ids"] = [cites.first.get(c) or cites.add(c, (cites.by_id.get(c) or {}).get("text", "")[:200]) for c in p.get("cite_ids", []) if c]
            tl.append({**e, "payload": p})
        return tl

    def qa_cites(r: dict[str, Any]) -> list[dict[str, Any]]:
        out_q = []
        for qa in r["qa"]:
            u = [cites.add(i["chunk_id"], i["quote"]) for i in qa["uae_basis"] if i.get("valid")]
            g = [cites.add(i["chunk_id"], i["quote"]) for i in qa["global_examples"] if i.get("valid")]
            out_q.append({"qa_id": qa["qa_id"], "preset_id": qa.get("preset_id"), "asked_by": qa["asked_by"], "wave": qa["wave"],
                          "t": qa["t"], "question": qa["question"], "answer": qa["answer"], "cite_ids": [c for c in u if c],
                          "global_cite_ids": [c for c in g if c], "gap": qa.get("gap", ""), "confidence": qa.get("confidence", ""),
                          "invalid_quotes": sum(1 for p in ("uae_basis", "global_examples") for i in qa[p] if not i.get("valid"))})
        return out_q

    def gaps_for(r: dict[str, Any]) -> list[dict[str, Any]]:
        out_g = []
        for g in r["gaps"]:
            ex = []
            for e in g["global_examples"]:
                cid = cites.add(e["chunk_id"], e["quote"], e.get("article") or "")
                if cid:
                    ex.append({"label": e.get("label") or e["doc_id"], "cite_id": cid, "how": e.get("how", "")})
            ue = [cites.add(c["chunk_id"], c["quote"], c.get("article") or "") for c in g["evidence"].get("uae_citations", [])]
            out_g.append({"gap_id": g["gap_id"], "type": g["type"], "title": g["title"], "description": g["description"],
                          "domain": g["domain"], "trigger": g["trigger"], "global_examples": ex,
                          "uae_evidence": [c for c in ue if c], "absence_queries": g["evidence"]["absence"]["queries"],
                          "evidence_statement": g["evidence"].get("statement", ""),
                          "readiness_ids": g["affected_readiness_metrics"], "y3172_nodes": g["y3172_nodes"],
                          "recommendation": g["domain_recommendation"], "confidence": g["confidence"]["level"],
                          "confidence_reason": g["confidence"]["reason"], "t": g["t"]})
        return out_g

    n_points, layout = kb_points(chunks, out)
    shutil.copyfile(base["dir"] / "audit.jsonl", out / "audit.jsonl")
    bm, rm = base["metrics"], (rf["metrics"] if rf else None)

    def pair(key):
        return [bm.get(key), rm.get(key) if rm else None]

    # Root cause only: in the reform run the emergency-call failure never occurs (wave suppressed), so comparing
    # time-to-awareness of F_EMERG would read "never" for a fact that did not happen.
    tta = {a: {"F_ROOT": [bm["time_to_awareness"][a].get("F_ROOT"), (rm["time_to_awareness"][a].get("F_ROOT") if rm else None)]}
           for a in ("A2", "A3", "A4", "A5")}
    metrics = {"time_to_awareness": tta, "blocked_actions": pair("blocked_actions"), "conflicting_actions": pair("conflicting_actions"),
               "coordination_messages": pair("coordination_messages"), "missing_channels": pair("missing_channels"),
               "rerouted_messages": pair("rerouted_messages"), "service_restored_min": pair("service_restored_min"),
               "degraded_minutes": pair("degraded_minutes"), "gaps_total": pair("gaps_total"),
               "awareness_convergence_min": pair("awareness_convergence_min")}
    a4b, a4r = tta["A4"]["F_ROOT"]
    quotable = (f"No mandate, no action: the P node blocked {bm['blocked_actions']} uncited actions and turned them into "
                f"{bm['gaps_total']} typed policy gaps, each with a verified global example"
                + (f"; with the reform pack, the ambulance service learned the root cause at T+{a4r} instead of "
                   f"{'T+' + str(a4b) if a4b is not None else 'never'}" if rf else "") + ".")
    llm_label = base["meta"]["llm"]
    provider, _, model = llm_label.partition(":")
    replay = {
        "meta": {"run_id": base["meta"]["run_id"], "scenario": sc.id, "title": sc.title, "reform": None,
                 "created_at": dt.datetime.fromtimestamp((base["dir"] / "timeline.json").stat().st_mtime, dt.timezone.utc).isoformat(),
                 "llm": {"provider": provider.split(" ")[0], "model": model or llm_label,
                         "adviser_model": (base["meta"].get("llm_adviser") or llm_label).partition(":")[2] or None,
                         "mode": "replay" if base["meta"].get("llm_stats", {}).get("live_calls", 0) == 0 else "live"},
                 "audit_root": base["meta"]["audit_root"], "disclaimer": sc.label, "label": "FICTIONAL SIMULATION",
                 "clock_origin": sc.raw.get("clock_origin", ""), "horizon_min": sc.horizon, "mock": False,
                 "cells_total": sc.params["kpi"]["cells_total"], "quotable": quotable},
        "agents": agents,
        "channels": channels_for(base, None),
        "facts": [{"id": k, "label": v["label"], "label_ar": v["label_ar"]} for k, v in sc.facts.items()],
        "waves": [{"id": w.id, "t": w.t, "visible_to": w.visible_to, "content": w.content, "hidden_fact": w.hidden_fact} for w in sc.waves],
        "timeline": tl_for(base),
        "kpis": base["kpis"],
        "gaps": gaps_for(base),
        "citations": {},
        "kb_points": {"href": "kb_points.bin", "count": n_points, "clusters": ["uae", "global", "itu", "other"], "layout": layout},
        "audit": {"href": "audit.jsonl", "root": base["meta"]["audit_root"], "entries": base["meta"]["audit_entries"]},
        "compare": {"baseline_run": base["meta"]["run_id"], "reform_run": rf["meta"]["run_id"] if rf else None, "metrics": metrics},
        "adviser_presets": qa_cites(base),
    }
    if rf:
        replay["compare"]["reform"] = {"run_id": rf["meta"]["run_id"], "timeline": tl_for(rf), "kpis": rf["kpis"],
                                       "gaps": gaps_for(rf), "channels": channels_for(rf, load_reform("uae_reform_pack")),
                                       "audit": {"href": "audit_reform.jsonl", "root": rf["meta"]["audit_root"],
                                                 "entries": rf["meta"]["audit_entries"]},
                                       "rules": [{"id": r["id"], "title": r["title"]} for r in (load_reform("uae_reform_pack") or {}).get("rules", [])]}
        shutil.copyfile(rf["dir"] / "audit.jsonl", out / "audit_reform.jsonl")
    replay["citations"] = cites.items
    errs = validate(replay)
    if errs:
        raise SystemExit("replay.json failed schema validation:\n" + "\n".join(errs))
    (out / "replay.json").write_text(json.dumps(replay, ensure_ascii=False), encoding="utf-8")
    unverified = [k for k, v in cites.items.items() if not v["verified"]]
    return {"events": len(replay["timeline"]), "gaps": len(replay["gaps"]), "citations": len(cites.items),
            "unverified_citations": len(unverified), "points": n_points, "layout": layout,
            "bytes": (out / "replay.json").stat().st_size}

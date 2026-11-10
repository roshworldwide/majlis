"""Gap engine: gate verdicts + scenario triggers → typed, evidenced policy gaps.

Six types (the brief's words): unclear_responsibility · standards_gap ·
technology_gap · legislative_gap · coordination_problem · conflicting_objectives.

For every gap: trigger (wave/event), evidence (the failed gate check and/or
absence evidence = the queries run over the UAE corpus with their top-k hits
and scores), ≥1 global example whose quote is verified verbatim against an
ingested chunk, Readiness metric IDs, Y.3172 nodes, a domain-level
recommendation (A7, cited) and a confidence with its reason.
Gaps are emitted only when the run triggers them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from majlis import config
from majlis.agents.mandates import resolve_citation
from majlis.kb.textnorm import norm

CATALOG_PATH = Path(__file__).with_name("catalog.yaml")


def load_catalog() -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")) or []
    return {g["key"]: g for g in data}


class GapEngine:
    def __init__(self, scenario, retriever, runtime, kb, audit, reform_ids: set[str]):
        self.sc = scenario
        self.retriever = retriever
        self.runtime = runtime
        self.kb = kb
        self.audit = audit
        self.reform_ids = reform_ids
        self.catalog = load_catalog()
        self.found: dict[str, dict[str, Any]] = {}
        self.order: list[str] = []
        self._by_doc: dict[str, list[dict[str, Any]]] | None = None

    # ------------------------------------------------------------- mapping
    def key_for(self, cand: dict[str, Any]) -> str:
        rule, at, a, tgt = cand.get("rule"), cand.get("action_type"), cand.get("agent"), cand.get("target")
        if rule == "trigger" and at in self.catalog:
            return at
        if rule == "G3":
            return "operator_ems_channel" if {a, tgt} == {"A1", "A4"} else "missing_channel"
        if rule == "G4":
            return "energy_vs_availability" if at == "keep_ml_energy_saving" else "objective_conflict"
        if rule in ("lead_conflict", "no_lead") or at == "claim_incident_lead":
            return "incident_lead"
        if at == "public_rumour_rebuttal":
            return "rumour_mandate"
        if at == "cross_border_log_transfer":
            return "offshore_model_logs"
        if at == "investigate_cyber_incident":
            return "cyber_investigation_mandate"
        if at in ("request_information", "issue_directive"):
            return "information_powers"
        return f"{cand.get('type')}:{at}"

    def gap_id(self, key: str) -> str:
        if key not in self.order:
            self.order.append(key)
        return f"GAP-{self.order.index(key) + 1:02d}"

    def candidate(self, cand: dict[str, Any], t: float, wave: str) -> str:
        key = self.key_for(cand)
        gid = self.gap_id(key)
        g = self.found.setdefault(key, {"key": key, "gap_id": gid, "t": t, "wave": wave, "occurrences": []})
        occ = {"t": t, "wave": wave, **{k: cand.get(k) for k in ("rule", "agent", "target", "action_type", "reason")}}
        if occ not in g["occurrences"]:
            g["occurrences"].append(occ)
            self.audit.append("gap_candidate", {"gap_id": gid, "key": key, **occ}, sim_minute=t)
        return gid

    def trigger(self, key: str, t: float, wave: str, registry=None) -> str | None:
        if key in self.found:
            return self.found[key]["gap_id"]
        if key == "ai_incident_notification" and registry is not None:
            if any("duty_notify_incident" in m.action_types for m in registry.mandates_for("A1")):
                return None
        if key in ("ml_update_validation", "offshore_model_logs") and "RF3" in self.reform_ids:
            return None
        reason = {
            "ai_incident_notification": "operator aware of an AI-caused incident; no notification duty or deadline citable",
            "ml_update_validation": "change log shows an ML model update deployed with no sandbox-validation or change-notification record",
            "offshore_model_logs": "rollback and forensics depend on a foreign vendor holding the model and logs offshore",
            "pdata_retraining": "retraining data included subscriber location traces",
        }.get(key, "scenario trigger")
        return self.candidate({"type": self.catalog.get(key, {}).get("type", "legislative_gap"), "rule": "trigger",
                               "agent": "A8", "target": None, "action_type": key, "reason": reason}, t, wave) if key in self.catalog \
            else None

    # ------------------------------------------------------------- finalize
    def _docs(self) -> dict[str, list[dict[str, Any]]]:
        if self._by_doc is None:
            self._by_doc = {}
            for c in self.kb.chunks:
                self._by_doc.setdefault(c["doc_id"], []).append(c)
        return self._by_doc

    def finalize(self, horizon: int) -> list[dict[str, Any]]:
        out = []
        for key in self.order:
            g = self.found[key]
            cat = self.catalog.get(key) or self.catalog.get(key.split(":")[0]) or {}
            rec = {
                "gap_id": g["gap_id"], "key": key, "type": cat.get("type") or g["occurrences"][0].get("rule", "legislative_gap"),
                "domain": self.sc.domain, "title": cat.get("title", key), "description": cat.get("description", ""),
                "trigger": f"{g['wave']} (T+{int(g['t'])}): " + (g["occurrences"][0].get("reason") or ""),
                "t": g["t"], "occurrences": g["occurrences"],
                "affected_readiness_metrics": cat.get("readiness", []), "y3172_nodes": cat.get("y3172_nodes", []),
                "recommendation_seed": cat.get("recommendation_seed", ""),
            }
            if rec["type"] not in ("unclear_responsibility", "standards_gap", "technology_gap", "legislative_gap",
                                   "coordination_problem", "conflicting_objectives"):
                rec["type"] = "coordination_problem" if g["occurrences"][0].get("rule") == "G3" else "legislative_gap"
            # evidence: gate checks + absence evidence over the UAE corpus
            absence = {"queries": [], "hits": [], "presence_found": []}
            for q in cat.get("absence_queries", []):
                hits = self.retriever.search(q, k=3, collections=["kb_uae"], agent="gap_engine", t=horizon, audit=self.audit)
                absence["queries"].append(q)
                for h in hits:
                    absence["hits"].append({"query": q, "doc_id": h.doc_id, "chunk_id": h.chunk_id,
                                            "article": h.meta.get("article"), "page": h.meta.get("page"),
                                            "score": round(float(h.score), 5), "snippet": " ".join(h.text.split())[:220]})
                    low = norm(h.text)
                    for group in cat.get("presence_terms", []):
                        if all(norm(term) in low for term in group):
                            absence["presence_found"].append({"chunk_id": h.chunk_id, "terms": group})
            uae_cites = []
            for raw in cat.get("uae_evidence", []):
                c = resolve_citation(raw, self._docs())
                if c.valid:
                    uae_cites.append(c.as_dict())
            rec["evidence"] = {"gate": [o for o in g["occurrences"] if o.get("rule") not in ("trigger",)],
                               "uae_citations": uae_cites, "absence": absence,
                               "statement": cat.get("evidence_statement", config.NOT_FOUND)}
            # global examples (verified)
            exs = []
            for raw in cat.get("global_examples", []):
                c = resolve_citation(raw, self._docs())
                if c.valid:
                    exs.append({**c.as_dict(), "how": raw.get("how", ""), "label": raw.get("label") or f"{c.doc_id} {c.article}",
                                "curated": True})
                else:
                    self.audit.append("example_rejected", {"gap": key, "doc_id": raw.get("doc_id"),
                                                           "reason": "quote not found verbatim"}, sim_minute=horizon)
            if exs:
                q = cat.get("example_query") or rec["title"]
                hits = self.retriever.search(q, k=10, collections=["kb_global_examples", "kb_usecase"], agent="gap_engine",
                                             t=horizon, audit=self.audit)
                ranks = {h.chunk_id: h.rank for h in hits}
                for e in exs:
                    e["retrieval_rank"] = ranks.get(e["chunk_id"])
            else:
                from majlis.agents.runtime import best_sentence

                q = cat.get("example_query") or rec["title"]
                hits = self.retriever.search(q, k=1, collections=["kb_global_examples"], agent="gap_engine", t=horizon,
                                             audit=self.audit)
                for h in hits:
                    exs.append({"doc_id": h.doc_id, "chunk_id": h.chunk_id, "article": h.meta.get("article"),
                                "page": h.meta.get("page"), "quote": best_sentence(h.text, q), "url": h.meta.get("url"),
                                "title": h.meta.get("title"), "how": "retrieved (not curated)", "curated": False,
                                "label": f"{h.doc_id} {h.meta.get('article') or ''}".strip(), "retrieval_rank": 1})
            rec["global_examples"] = exs
            reco = self.runtime.recommend({**rec, "key": key}, exs, self.audit, horizon)
            text = reco["recommendation"]
            from majlis.gate.gate import NORMATIVE, CITE_MARK

            country = re.search(r"\b(UAE|United Arab Emirates|Emirati|EU|European|US|United States|India|UK|United Kingdom|Singapore|"
                                r"[A-Z]{2,5}-[A-Z0-9]{2,}-?[A-Z0-9-]*)\b", text)
            if any(NORMATIVE.search(s) and not CITE_MARK.search(s) for s in text.split(". ")) or len(text) < 40 or country:
                text = rec["recommendation_seed"]
                reco["llm"]["source"] = reco["llm"].get("source", "") + " → seed (failed G5 or empty)"
            rec["domain_recommendation"] = text
            rec["recommendation_llm"] = reco["llm"]
            n_ok = sum(1 for e in exs if e.get("curated"))
            if n_ok >= 2 and not absence["presence_found"]:
                conf, why = "high", f"{n_ok} verified global examples; absence queries found no covering UAE provision"
            elif n_ok >= 1:
                conf, why = "med", f"{n_ok} verified global example(s)" + ("; partial UAE coverage found" if absence["presence_found"] else "")
            else:
                conf, why = "low", "no curated global example verified"
            rec["confidence"] = {"level": conf, "reason": why}
            out.append(rec)
            self.audit.append("gap", {"gap_id": rec["gap_id"], "type": rec["type"], "title": rec["title"],
                                      "examples": [e["chunk_id"] for e in exs], "confidence": conf}, sim_minute=horizon)
        return out

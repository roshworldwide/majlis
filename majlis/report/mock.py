"""MOCK replay for the front-end track (M1). Replaced by the golden run at M4.

Everything here is clearly marked mock: quotes read "MOCK QUOTE …" so no
placeholder text can be mistaken for law. The audit chain is real (same
AuditLog class) so in-browser verification can be built against the exact
canonical format.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from majlis.audit.chain import AuditLog
from majlis.report.replay import kpi_series, mock_points, validate, write_points
from majlis.scenario.loader import load_scenario

MOCK_Q = "MOCK QUOTE — placeholder until the golden run replaces this file."


def build_mock(out_dir: Path) -> dict[str, Any]:
    sc = load_scenario("uae_nye_cells")
    cites = {
        "C-UAE-1": {"doc_id": "UAE-TELECOM-LAW", "title": "MOCK — UAE telecom law", "issuer": "mock", "article": "Article X",
                    "page": 1, "quote": MOCK_Q, "url": "https://example.invalid/mock", "verified": False, "cluster": "uae", "star_index": 10},
        "C-UAE-2": {"doc_id": "UAE-NCEMA-LAW", "title": "MOCK — crisis authority law", "issuer": "mock", "article": "Article Y",
                    "page": 2, "quote": MOCK_Q, "url": "https://example.invalid/mock", "verified": False, "cluster": "uae", "star_index": 40},
        "C-G-1": {"doc_id": "EU-AIACT-2024", "title": "MOCK — EU AI Act", "issuer": "mock", "article": "Art. 73",
                  "page": 3, "quote": MOCK_Q, "url": "https://example.invalid/mock", "verified": False, "cluster": "global", "star_index": 2100},
        "C-G-2": {"doc_id": "EU-NIS2-2022", "title": "MOCK — NIS2", "issuer": "mock", "article": "Art. 23",
                  "page": 4, "quote": MOCK_Q, "url": "https://example.invalid/mock", "verified": False, "cluster": "global", "star_index": 2300},
        "C-G-3": {"doc_id": "US-47CFR-PART4", "title": "MOCK — 47 CFR Part 4", "issuer": "mock", "article": "§ 4.9",
                  "page": 1, "quote": MOCK_Q, "url": "https://example.invalid/mock", "verified": False, "cluster": "global", "star_index": 2500},
        "C-ITU-1": {"doc_id": "ITU-T-Y3172", "title": "MOCK — ITU-T Y.3172", "issuer": "mock", "article": "clause 7",
                    "page": 9, "quote": MOCK_Q, "url": "https://example.invalid/mock", "verified": False, "cluster": "itu", "star_index": 3200},
    }
    tl: list[dict[str, Any]] = []

    def ev(t, w_id, typ, agent, **payload):
        tl.append({"seq": len(tl), "t": t, "wave": w_id, "type": typ, "agent": agent, "payload": payload})

    # W0
    ev(0, "W0", "inject", "A8", wave="W0", visible_to=["A1"], content=sc.waves[0].content, reveals={"F_ROOT": 0.4})
    ev(0, "W0", "belief", "A1", fact="F_ROOT", confidence=0.4, prev=0.0, source="inject")
    ev(0, "W0", "proposal", "A1", proposal_id="P-A1-W0", situation="MOCK: KPI anomaly aligned with v2.3 sleep decisions.",
       why="MOCK rationale.", chosen=["root_cause_analysis", "notify_incident→A2", "notify_incident→A4", "keep_ml_energy_saving"],
       applicable_rules=[{"cite_id": "C-UAE-1", "valid": False}], llm={"source": "mock", "cache_hit": False})
    ev(0, "W0", "belief", "A1", fact="F_ROOT", confidence=0.85, prev=0.4, source="analysis")
    ev(0, "W0", "action", "A1", action_id="ACT-1", type="root_cause_analysis", target=None, internal=True, status="executed", cite_ids=[])
    ev(0, "W0", "gate_flag", "A1", item_id="ACT-2", kind="action", rule="G4", action_type="keep_ml_energy_saving",
       reason="Promotes energy_efficiency but harms service_availability/public_safety declared by A2, A3", gap_id="GAP-04")
    ev(0, "W0", "gate_pass", "A1", item_id="MSG-1", kind="message", rules=["G1", "G3", "G5"], cite_ids=["C-UAE-1"])
    ev(0, "W0", "message", "A1", msg_id="MSG-1", **{"from": "A1"}, to="A2", channel_id="CH-A1-A2", legal=True, sent_t=0,
       deliver_t=10, facts=["F_ROOT"], content="MOCK: v2.3 is the likely root cause.", status="delivered", route="legal")
    ev(0, "W0", "gate_block", "A1", item_id="MSG-2", kind="message", rule="G3", action_type="notify_incident", target="A4",
       reason="No legal channel operator→emergency service in the corpus; message re-routed informally (+35 min)", gap_id="GAP-01")
    ev(0, "W0", "message", "A1", msg_id="MSG-2", **{"from": "A1"}, to="A4", channel_id=None, legal=False, sent_t=0,
       deliver_t=35, facts=["F_ROOT"], content="MOCK: network fault may affect emergency calls.", status="delayed", route="informal")
    ev(0, "W0", "gap", "A8", gap_id="GAP-01")
    ev(0, "W0", "gap", "A8", gap_id="GAP-04")
    # W1
    ev(10, "W1", "inject", "A8", wave="W1", visible_to=["A4"], content=sc.waves[1].content, reveals={"F_EMERG": 0.8})
    ev(10, "W1", "belief", "A4", fact="F_EMERG", confidence=0.8, prev=0.0, source="inject")
    ev(10, "W1", "belief", "A2", fact="F_ROOT", confidence=0.85, prev=0.0, source="message", via="MSG-1")
    ev(10, "W1", "message", "A4", msg_id="MSG-3", **{"from": "A4"}, to="A3", channel_id="CH-A4-A3", legal=True, sent_t=10,
       deliver_t=20, facts=["F_EMERG"], content="MOCK: emergency-call volume collapsed.", status="delivered", route="legal")
    ev(10, "W1", "gate_block", "A4", item_id="MSG-4", kind="message", rule="G3", action_type="request_information", target="A1",
       reason="No legal channel emergency service→operator in the corpus", gap_id="GAP-01")
    ev(10, "W1", "message", "A4", msg_id="MSG-4", **{"from": "A4"}, to="A1", channel_id=None, legal=False, sent_t=10,
       deliver_t=45, facts=["F_EMERG"], content="MOCK: are networks down in Downtown?", status="delayed", route="informal")
    # W2
    ev(15, "W2", "inject", "A8", wave="W2", visible_to=["A1"], content=sc.waves[2].content, reveals={"F_ROOT": 0.95})
    ev(15, "W2", "belief", "A1", fact="F_ROOT", confidence=0.95, prev=0.85, source="inject")
    ev(15, "W2", "adviser_qa", "A7", qa_id="Q1", asked_by="A1", question=sc.adviser_questions[0]["question"],
       answer="MOCK answer citing [C-UAE-1] and global examples [C-G-1] [C-G-2].", cite_ids=["C-UAE-1"], global_cite_ids=["C-G-1", "C-G-2"])
    # W3
    ev(20, "W3", "inject", "A8", wave="W3", visible_to=["A5", "A2"], content=sc.waves[3].content, reveals={"F_RUMOUR": 0.9})
    ev(20, "W3", "belief", "A5", fact="F_RUMOUR", confidence=0.9, prev=0.0, source="inject")
    ev(20, "W3", "belief", "A2", fact="F_RUMOUR", confidence=0.9, prev=0.0, source="inject")
    ev(20, "W3", "belief", "A3", fact="F_EMERG", confidence=0.8, prev=0.0, source="message", via="MSG-3")
    ev(20, "W3", "gate_block", "A2", item_id="ACT-9", kind="action", rule="G2", action_type="claim_incident_lead", target=None,
       reason="No cited mandate gives the regulator incident lead for a public emergency", gap_id="GAP-02")
    ev(20, "W3", "gap", "A8", gap_id="GAP-02")
    ev(20, "W3", "gate_block", "A1", item_id="CLM-1", kind="claim", rule="G5", action_type="normative_claim", target=None,
       reason="Uncited normative claim redacted: 'the operator must notify within 24 hours'", gap_id=None)
    # W4..W8 (sparser)
    ev(30, "W4", "inject", "A8", wave="W4", visible_to=["A4"], content=sc.waves[4].content, reveals={"F_HARM": 0.9})
    ev(30, "W4", "belief", "A4", fact="F_HARM", confidence=0.9, prev=0.0, source="inject")
    ev(35, "W4", "belief", "A4", fact="F_ROOT", confidence=0.85, prev=0.0, source="message", via="MSG-2")
    ev(40, "W5", "inject", "A8", wave="W5", visible_to=["A1"], content=sc.waves[5].content, reveals={"F_XBORDER": 0.95})
    ev(40, "W5", "belief", "A1", fact="F_XBORDER", confidence=0.95, prev=0.0, source="inject")
    ev(40, "W5", "gate_block", "A1", item_id="ACT-12", kind="action", rule="G2", action_type="cross_border_log_transfer", target="vendor",
       reason="No cited basis for transferring subscriber-bearing logs to the offshore vendor", gap_id="GAP-05")
    ev(40, "W5", "gap", "A8", gap_id="GAP-05")
    ev(45, "W5", "belief", "A1", fact="F_EMERG", confidence=0.8, prev=0.0, source="message", via="MSG-4")
    ev(50, "W6", "inject", "A8", wave="W6", visible_to=["A6"], content=sc.waves[6].content, reveals={"F_PDATA": 0.8})
    ev(50, "W6", "belief", "A6", fact="F_PDATA", confidence=0.8, prev=0.0, source="inject")
    ev(50, "W6", "gap", "A8", gap_id="GAP-06")
    ev(60, "W7", "inject", "A8", wave="W7", visible_to=["A3"], content=sc.waves[7].content, reveals={"F_LEAD": 0.8})
    ev(60, "W7", "action", "A3", action_id="ACT-15", type="claim_incident_lead", target=None, internal=False, status="executed", cite_ids=["C-UAE-2"])
    ev(60, "W7", "gap", "A8", gap_id="GAP-03")
    ev(85, "W7", "kpi", "A1", event="service_restored", detail="MOCK vendor rollback completed")
    ev(90, "W8", "inject", "A8", wave="W8", visible_to=["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"], content=sc.waves[8].content, reveals={})

    def gap(gid, typ, title, t, ex, rids, nodes):
        return {"gap_id": gid, "type": typ, "title": title, "description": "MOCK description", "domain": sc.domain,
                "trigger": "mock", "global_examples": [{"label": cites[c]["doc_id"] + " " + cites[c]["article"], "cite_id": c,
                                                        "how": "MOCK how they closed it"} for c in ex],
                "uae_evidence": [], "absence_queries": ["mock query"], "readiness_ids": rids, "y3172_nodes": nodes,
                "recommendation": "MOCK recommendation", "confidence": "low", "t": t}

    gaps = [
        gap("GAP-01", "coordination_problem", "No channel between operator and emergency dispatch", 0, ["C-G-3"], ["d7_m01", "d9_m08"], ["D", "P"]),
        gap("GAP-02", "unclear_responsibility", "Who leads when a telecom AI fault becomes a public emergency", 20, ["C-G-2"], ["d7_m01"], ["MLFO"]),
        gap("GAP-03", "legislative_gap", "No AI-incident notification duty or deadline", 60, ["C-G-1", "C-G-2", "C-G-3"], ["d10_m09", "d9_m08"], ["P", "SINK"]),
        gap("GAP-04", "conflicting_objectives", "Energy efficiency vs availability during mass events", 0, ["C-G-1"], ["d13_m07"], ["P"]),
        gap("GAP-05", "technology_gap", "Vendor-held offshore model logs block forensics and rollback", 40, ["C-G-1"], ["d13_m07"], ["M", "SINK"]),
        gap("GAP-06", "standards_gap", "No mandated pre-deployment ML sandbox validation or incident interface", 50, ["C-ITU-1"], ["d10_m01"], ["ML Sandbox"]),
    ]
    base_kpis = kpi_series(sc.params, 85, sc.horizon)
    reform_kpis = kpi_series(sc.params, 20, sc.horizon)
    reform_tl = [dict(e) for e in tl if e["type"] in ("inject", "belief")]
    for e in reform_tl:
        if e["type"] == "belief" and e["payload"].get("fact") == "F_ROOT" and e["agent"] in ("A4", "A2"):
            e["t"] = 5
    reform_tl.append({"seq": 999, "t": 20, "wave": "W3", "type": "kpi", "agent": "A1",
                      "payload": {"event": "service_restored", "detail": "MOCK safe-mode (RF2)"}})
    reform_tl.sort(key=lambda e: (e["t"], e["seq"]))

    out_dir.mkdir(parents=True, exist_ok=True)
    audit = AuditLog(out_dir / "audit.jsonl")
    for e in tl:
        audit.append(e["type"], {"agent": e["agent"], "wave": e["wave"], **e["payload"]}, sim_minute=e["t"])
    xyz, cl = mock_points()
    write_points(out_dir / "kb_points.bin", xyz, cl)
    agents = []
    for aid, a in sc.agents.items():
        mand = [{"id": f"M-{aid}-MOCK", "title": "MOCK mandate", "action_types": ["notify_incident"], "citations": ["C-UAE-1"]}] if aid in ("A2", "A3") else []
        agents.append({"id": aid, "name": a["name"], "name_ar": a["name_ar"], "role_type": a["role_type"],
                       "modelled_on": a["modelled_on"], "color": a["color"], "mandates": mand})
    channels = [
        {"from": "A1", "to": "A2", "legal": True, "citation": "C-UAE-1", "type": "licensee_report", "latency_min": 10, "origin": "law"},
        {"from": "A2", "to": "A3", "legal": True, "citation": "C-UAE-2", "type": "coordination", "latency_min": 10, "origin": "law"},
        {"from": "A4", "to": "A3", "legal": True, "citation": "C-UAE-2", "type": "coordination", "latency_min": 10, "origin": "law"},
        {"from": "A3", "to": "A4", "legal": True, "citation": "C-UAE-2", "type": "coordination", "latency_min": 10, "origin": "law"},
        {"from": "A1", "to": "A4", "legal": False, "citation": None, "type": "none", "latency_min": 35, "origin": "missing"},
        {"from": "A4", "to": "A1", "legal": False, "citation": None, "type": "none", "latency_min": 35, "origin": "missing"},
    ]
    replay = {
        "meta": {"run_id": "mock", "scenario": sc.id, "title": sc.title, "reform": None, "created_at": "2026-11-10T00:00:00Z",
                 "llm": {"provider": "mock", "model": "mock", "mode": "mock"}, "audit_root": audit.root,
                 "disclaimer": sc.label, "label": "FICTIONAL SIMULATION", "clock_origin": sc.raw.get("clock_origin", ""),
                 "horizon_min": sc.horizon, "mock": True, "cells_total": sc.params["kpi"]["cells_total"],
                 "quotable": "MOCK — No mandate, no action: every blocked action became a typed policy gap with a global example."},
        "agents": agents,
        "channels": channels,
        "facts": [{"id": k, "label": v["label"], "label_ar": v["label_ar"]} for k, v in sc.facts.items()],
        "waves": [{"id": w.id, "t": w.t, "visible_to": w.visible_to, "content": w.content, "hidden_fact": w.hidden_fact} for w in sc.waves],
        "timeline": tl,
        "kpis": base_kpis,
        "gaps": gaps,
        "citations": cites,
        "kb_points": {"href": "kb_points.bin", "count": len(cl), "clusters": ["uae", "global", "itu", "other"], "layout": "mock"},
        "audit": {"href": "audit.jsonl", "root": audit.root, "entries": audit.seq},
        "compare": {"baseline_run": "mock-baseline", "reform_run": "mock-reform",
                    "metrics": {
                        "time_to_awareness": {"A2": {"F_ROOT": [10, 5]}, "A3": {"F_ROOT": [None, 5]}, "A4": {"F_ROOT": [35, 5]},
                                              "A5": {"F_ROOT": [None, 5]}, "A1": {"F_EMERG": [45, 15]}},
                        "blocked_actions": [4, 1], "conflicting_actions": [1, 0], "coordination_messages": [4, 9],
                        "missing_channels": [2, 0], "service_restored_min": [85, 20], "mock": True},
                    "reform": {"run_id": "mock-reform", "timeline": reform_tl, "kpis": reform_kpis, "gaps": gaps[:2]}},
        "adviser_presets": [{"qa_id": "Q1", "asked_by": "A1", "wave": "W2", "question": sc.adviser_questions[0]["question"],
                             "answer": "MOCK answer.", "cite_ids": ["C-UAE-1"], "global_cite_ids": ["C-G-1", "C-G-2"]}],
    }
    errs = validate(replay)
    if errs:
        raise SystemExit("mock replay invalid:\n" + "\n".join(errs))
    (out_dir / "replay.json").write_text(json.dumps(replay, ensure_ascii=False, indent=1), encoding="utf-8")
    return replay

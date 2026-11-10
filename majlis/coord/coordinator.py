"""A8 — Coordinator (Y.3172 MLFO) and D (Distributor/router).

Discrete-event simulation over simulation minutes. Per tick: deliver injects
(per visibility) and due messages → agents with new information take a turn →
the P-node gate checks every action/message/claim → the router (D) schedules
allowed messages with channel latency (or informal latency if no legal channel)
→ adviser Q&A → belief propagation. Facts move ONLY through injects, delivered
messages and A1's telemetry analysis, so time-to-awareness is exact and
replayable. The LLM writes text; the core decides who knows what.
"""

from __future__ import annotations

import heapq
import json
import statistics
from pathlib import Path
from typing import Any

import yaml

from majlis import config
from majlis.agents.mandates import Channel, Mandate, load_registry, resolve_citation
from majlis.agents.runtime import AgentRuntime
from majlis.audit.chain import AuditLog
from majlis.coord.retriever import Retriever
from majlis.gate.gate import Gate
from majlis.gaps.engine import GapEngine
from majlis.kb.store import KB
from majlis.report.replay import kpi_series
from majlis.scenario.loader import Scenario, load_reform, load_scenario

ORDER = ["A1", "A2", "A3", "A4", "A5", "A6"]
POWER_ACTIONS = {"request_information", "issue_directive", "investigate_cyber_incident", "claim_incident_lead",
                 "public_rumour_rebuttal", "cross_border_log_transfer"}
VOLUNTARY = {"notify_incident", "share_information", "respond_information", "query_status"}


class Coordinator:
    def __init__(self, scenario: Scenario, reform: dict[str, Any] | None, kb: KB, llm, run_dir: Path,
                 gate_on: bool = True, replay: bool = False, llm_adviser=None):
        self.sc = scenario
        self.reform = reform
        self.reform_ids = {r["id"] for r in (reform or {}).get("rules", [])}
        self.kb = kb
        self.llm = llm
        self.llm_adviser = llm_adviser or llm
        self.run_dir = run_dir
        self.gate_on = gate_on
        self.params = scenario.params
        self.thr = float(self.params.get("awareness_threshold", 0.7))
        run_dir.mkdir(parents=True, exist_ok=True)
        self.audit = AuditLog(run_dir / "audit.jsonl")
        self.registry = load_registry(scenario.country, kb.chunks)
        self.priority_rules: list[dict[str, Any]] = []
        self._apply_reform()
        self.objectives = self._load_objectives()
        self.gate = Gate(self.registry, kb.by_id, self.objectives, self.params, enforce=gate_on,
                         priority_rules=self.priority_rules)
        self.retriever = Retriever(kb, replay=replay)
        self.runtime = AgentRuntime(scenario, self.retriever, llm, self.registry, scenario.facts, llm_adviser=self.llm_adviser)
        self.gaps = GapEngine(scenario, self.retriever, self.runtime, kb, self.audit, self.reform_ids)
        agents = [a for a in scenario.agents]
        self.beliefs: dict[str, dict[str, float]] = {a: {} for a in agents}
        self.known_at: dict[str, dict[str, int]] = {a: {} for a in agents}
        self.obs: dict[str, list[str]] = {a: [] for a in agents}
        self.dirty: dict[str, bool] = {a: False for a in agents}
        self.fired: set[str] = set()
        self.timeline: list[dict[str, Any]] = []
        self.proposals: list[dict[str, Any]] = []
        self.verdicts: list[dict[str, Any]] = []
        self.messages: list[dict[str, Any]] = []
        self.qa: list[dict[str, Any]] = []
        self.iaps: list[dict[str, Any]] = []
        self.actions: list[dict[str, Any]] = []
        self.queue: list[tuple] = []
        self._seq = 0
        self.restore_t: float | None = None
        self.rollback_requested_t: int | None = None
        self.lead_claims: list[tuple[str, int]] = []
        self.rumour_rebutted_t: int | None = None
        self.adviser_live_used: set[str] = set()
        self.counters = {"msg": 0, "act": 0, "claims_total": 0, "claims_supported": 0, "invalid_quotes": 0,
                         "redacted": 0, "g1_checked": 0}
        self.harm_iap_done = False
        self._turn_lookup: dict[str, dict[str, str]] = {}
        self.missing_pairs: set[tuple[str, str]] = set()

    # ------------------------------------------------------------------ setup
    def _apply_reform(self) -> None:
        if not self.reform:
            return
        by_doc: dict[str, list[dict[str, Any]]] = {}
        for c in self.kb.chunks:
            by_doc.setdefault(c["doc_id"], []).append(c)
        for rule in self.reform.get("rules", []):
            basis = [resolve_citation(b, by_doc) for b in rule.get("global_basis", [])]
            basis = [b for b in basis if b.valid]
            rule["_basis_valid"] = len(basis)
            for m in rule.get("adds_mandates", []):
                self.registry.mandates.append(Mandate(mandate_id=m["mandate_id"], agent=m["agent"], title=m["title"],
                                                      action_types=list(m["action_types"]), legal_basis=basis,
                                                      note=f"reform {rule['id']} (design proposal, not law)"))
            for ch in rule.get("adds_channels", []):
                self.registry.channels.append(Channel(channel_id=ch["channel_id"], src=ch["from"], dst=ch["to"],
                                                      type=ch.get("type", rule["id"]), latency_min=int(ch.get("latency_min", 5)),
                                                      legal_basis=basis, origin="reform"))
            for pr in rule.get("priority_rules", []):
                self.priority_rules.append(pr)

    def _load_objectives(self) -> dict[str, list[str]]:
        path = config.COUNTRIES_DIR / self.sc.country / "objectives.yaml"
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            return {a: [o["id"] for o in v.get("objectives", [])] for a, v in data.get("agents", {}).items()}
        return {a: list(v.get("objectives", [])) for a, v in self.sc.agents.items()}

    # ---------------------------------------------------------------- helpers
    def wave_at(self, t: float) -> str:
        w = [x.id for x in self.sc.waves if x.t <= t]
        return w[-1] if w else self.sc.waves[0].id

    def ev(self, t: float, typ: str, agent: str | None, **payload: Any) -> None:
        wave = self.wave_at(t)
        e = {"seq": len(self.timeline), "t": t, "wave": wave, "type": typ, "agent": agent, "payload": payload}
        self.timeline.append(e)
        self.audit.append(typ, {"agent": agent, "wave": wave, **payload}, sim_minute=t)

    def push(self, t: float, prio: int, kind: str, data: dict[str, Any]) -> None:
        self._seq += 1
        heapq.heappush(self.queue, (t, prio, self._seq, kind, data))

    def learn(self, aid: str, fact: str, conf: float, t: float, source: str, via: str | None = None) -> None:
        prev = self.beliefs[aid].get(fact, 0.0)
        if conf <= prev + 1e-9:
            return
        self.beliefs[aid][fact] = conf
        self.ev(t, "belief", aid, fact=fact, confidence=round(conf, 2), prev=round(prev, 2), source=source, via=via)
        if prev < self.thr <= conf and fact not in self.known_at[aid]:
            self.known_at[aid][fact] = t
        self.dirty[aid] = True
        if aid == "A1" and fact == "F_XBORDER" and self.restore_t is not None and "RF3" not in self.reform_ids:
            self._set_restore(self.restore_t + int(self.params["xborder_extra_delay_min"]), t, "offshore dependency adds delay")
        if "RF3" in self.reform_ids and aid == "A2" and fact in ("F_RUMOUR", "F_EMERG") and self.beliefs[aid].get("F_ROOT", 0) < self.thr:
            # RF3 change register: the regulator was notified of the v2.3 update before deployment
            self.learn("A2", "F_ROOT", 0.75, t, "change_register (RF3)")

    def knows(self, aid: str, fact: str) -> bool:
        return self.beliefs[aid].get(fact, 0.0) >= self.thr

    def _set_restore(self, new_t: float, t_now: float, why: str) -> None:
        if self.restore_t is None or new_t != self.restore_t:
            self.restore_t = new_t
            self.push(new_t, 2, "restore", {"t": new_t, "why": why})
            self.audit.append("restoration_estimate", {"restore_t": new_t, "why": why}, sim_minute=t_now)

    # ---------------------------------------------------------------- playbook
    def eligible(self, aid: str, t: float) -> list[dict[str, Any]]:
        out = []
        for r in self.sc.playbook:
            if r.agent != aid or r.id in self.fired or t < r.min_t:
                continue
            if r.reform and r.reform not in self.reform_ids:
                continue
            if r.no_reform and r.no_reform in self.reform_ids:
                continue
            if any(not self.knows(aid, f) for f in r.knows):
                continue
            if r.knows_any and not any(self.knows(aid, f) for f in r.knows_any):
                continue
            if any(self.knows(aid, f) for f in r.not_knows):
                continue
            if r.signal and not any(self.beliefs[aid].get(f, 0) > 0 for f in r.signal):
                continue
            if r.min_conf and not all(self.beliefs[aid].get(f, 0) >= float(r.min_conf) for f in r.knows):
                continue
            out.append({**r.action, "_rule": r.id})
        return out

    # ------------------------------------------------------------------- run
    def start(self) -> None:
        self.audit.append("run_start", {"scenario": self.sc.id, "reform": sorted(self.reform_ids), "gate": self.gate_on,
                                        "llm": self.llm.label, "llm_adviser": self.llm_adviser.label, "label": self.sc.label,
                                        "mandates": [m.mandate_id for m in self.registry.mandates],
                                        "channels": [c.channel_id for c in self.registry.channels],
                                        "rejected": self.registry.rejected}, sim_minute=None)
        for w in self.sc.waves:
            self.push(w.t, 1, "wave", {"id": w.id})

    def step(self) -> float | None:
        """Process the next simulation tick. Returns its time, or None when the run is over."""
        if not self.queue or self.queue[0][0] > self.sc.horizon:
            return None
        t = self.queue[0][0]
        batch = []
        while self.queue and self.queue[0][0] == t:
            batch.append(heapq.heappop(self.queue))
        wave_ids = []
        for (_, prio, _, kind, data) in sorted(batch, key=lambda b: (b[1], b[2])):
            if kind == "deliver":
                self._deliver(data, t)
            elif kind == "wave":
                self._inject(data["id"], t)
                wave_ids.append(data["id"])
            elif kind == "custom":
                self._custom_inject(data, t)
            elif kind == "restore" and data["t"] == self.restore_t:
                self.ev(t, "kpi", "A1", event="service_restored", detail=data["why"])
        for _ in range(4):
            acted = False
            for aid in ORDER:
                opts = self.eligible(aid, t)
                if not opts:
                    self.dirty[aid] = False
                    continue
                self._agent_turn(aid, t, opts)
                acted = True
            if not acted:
                break
        for wid in wave_ids:
            for q in self.sc.adviser_questions:
                if q["wave"] == wid:
                    self._ask(q["question"], q["as"], t, preset_id=q["id"])
        self._checks(t)
        return t

    def run(self) -> dict[str, Any]:
        self.start()
        while self.step() is not None:
            pass
        self._debrief()
        return self._finish()

    def _custom_inject(self, data: dict[str, Any], t: float) -> None:
        """Facilitator inject (majlis play): delivered only to the named agents, logged like any wave."""
        self.ev(t, "inject", "A8", wave=self.wave_at(t), visible_to=data["to"], content=data["content"],
                reveals=data.get("reveals", {}), custom=True)
        for aid in data["to"]:
            self.obs[aid].append(f"[facilitator T+{int(t)}] {data['content']}")
            self.dirty[aid] = True
            for fact, conf in (data.get("reveals") or {}).items():
                self.learn(aid, fact, float(conf), t, "inject")

    def _inject(self, wid: str, t: float) -> None:
        w = next(x for x in self.sc.waves if x.id == wid)
        cond = w.condition
        suppressed = None
        if cond == "degraded" and self.restore_t is not None and self.restore_t <= t:
            suppressed = f"not released: service already restored at T+{int(self.restore_t)}"
        elif isinstance(cond, dict) and cond.get("no_reform") in self.reform_ids:
            suppressed = f"not released: condition removed by reform {cond['no_reform']}"
        if suppressed:
            self.ev(t, "inject", "A8", wave=w.id, visible_to=w.visible_to, content=w.content, reveals={},
                    suppressed=True, reason=suppressed)
            return
        self.ev(t, "inject", "A8", wave=w.id, visible_to=w.visible_to, content=w.content, reveals=w.reveals)
        for aid in w.visible_to:
            self.obs[aid].append(f"[{w.id} T+{w.t}] {w.content}")
            self.dirty[aid] = True
            for fact, conf in w.reveals.items():
                self.learn(aid, fact, conf, t, "inject")
        if w.telemetry and "A1" in w.visible_to:
            self._rca(w, t)

    def _rca(self, w, t: float) -> None:
        """A1's copilot analysis of Y.3172 pipeline telemetry (SRC→C→PP→M): correlation + change-log match."""
        tel = w.telemetry
        x, y = tel["cells_asleep_pct"], tel["call_setup_success_pct"]
        mx, my = statistics.fmean(x), statistics.fmean(y)
        cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
        sx = sum((a - mx) ** 2 for a in x) ** 0.5
        sy = sum((b - my) ** 2 for b in y) ** 0.5
        corr = cov / (sx * sy) if sx and sy else 0.0
        base = x[:4]
        mu, sd = statistics.fmean(base), (statistics.pstdev(base) or 0.05)
        onset = next((m for m, v in zip(tel["kpi_window_min"], x) if v > mu + 3 * sd), None)
        cands = [c for c in tel.get("change_log", []) if -4320 <= c["t"] <= 0 and "ML" in c["component"]]
        conf = round(min(0.9, 0.5 + 0.4 * abs(corr)), 2) if cands else 0.5
        self.counters["act"] += 1
        self.ev(t, "action", "A1", action_id=f"ACT-{self.counters['act']:03d}", type="root_cause_analysis", target=None,
                internal=True, status="executed", cite_ids=[],
                analysis={"pearson_sleep_vs_cssr": round(corr, 3), "anomaly_onset_min": onset,
                          "candidate": cands[0]["item"] if cands else None, "confidence": conf,
                          "pipeline": "SRC→C→PP→M (Y.3172)"})
        self.learn("A1", "F_ROOT", conf, t, "analysis")

    def _deliver(self, msg: dict[str, Any], t: float) -> None:
        msg["status_final"] = "delivered"
        dst = msg["to"]
        self.obs[dst].append(f"[T+{t} message from {msg['from']}] {msg['content']}")
        self.dirty[dst] = True
        for f in msg.get("facts", []):
            conf = min(self.beliefs[msg["from"]].get(f, 0.8), 0.9) if f in self.beliefs[msg["from"]] else 0.8
            self.learn(dst, f, conf, t, "message", via=msg["msg_id"])
        if msg.get("kind") in ("request_information", "query_status", "examine_complaint") and msg["from"] in self.sc.agents:
            # the recipient answers with what it knows, through whatever channel exists
            known = [f for f in ("F_ROOT", "F_EMERG", "F_HARM") if self.knows(dst, f)]
            self._send(dst, msg["from"], {"type": "respond_information", "target": msg["from"], "facts": known},
                       t, content=f"Response from {self.sc.agents[dst]['name']}: " +
                       ("; ".join(self.sc.facts[f]["label"] for f in known) if known else "no confirmed information yet."))

    # ------------------------------------------------------------------ turns
    def _agent_turn(self, aid: str, t: float, opts: list[dict[str, Any]]) -> None:
        for o in opts:
            self.fired.add(o["_rule"])
        prop = self.runtime.turn(aid, int(t), self.wave_at(t), self.obs[aid], self.beliefs[aid], opts, self.audit)
        self.dirty[aid] = False
        # G1 on applicable rules
        rules_out = []
        for r in prop["reasoning_trace"]["applicable_rules"]:
            self.counters["claims_total"] += 1
            self.counters["g1_checked"] += 1
            chk = self.gate.check_quote(r["chunk_id"] or "", r["quote"])
            r["valid"] = chk.ok
            r["gate"] = chk.detail
            if chk.ok:
                self.counters["claims_supported"] += 1
            else:
                self.counters["invalid_quotes"] += 1
                self.gate.stats["g1_fail"] += 1
                self.ev(t, "gate_block", aid, item_id=f"{prop['proposal_id']}-R", kind="claim", rule="G1",
                        action_type="citation", target=None, reason=chk.detail, gap_id=None,
                        enforced=self.gate_on, quote=r["quote"][:200])
            rules_out.append(r)
        # G5 on situation / why
        lookup = {k: v for k, v in prop.pop("_lookup", {}).items()}
        self._turn_lookup[aid] = lookup
        for fld in ("situation", "why"):
            clean, red = self.gate.scan_text(prop["reasoning_trace"][fld], lookup)
            self.counters["claims_total"] += len(red)
            if red:
                self.counters["redacted"] += len(red)
                for s in red:
                    self.ev(t, "gate_block", aid, item_id=f"{prop['proposal_id']}-{fld}", kind="claim", rule="G5",
                            action_type="normative_claim", target=None, reason=f"uncited normative claim: {s[:160]}",
                            gap_id=None, enforced=self.gate_on)
                if self.gate_on:
                    prop["reasoning_trace"][fld] = clean
        mapping = prop.pop("_mapping", {})
        self.proposals.append(prop)
        self.ev(t, "proposal", aid, proposal_id=prop["proposal_id"], situation=prop["reasoning_trace"]["situation"],
                why=prop["reasoning_trace"]["why"], options=prop["reasoning_trace"]["options"],
                chosen=prop["reasoning_trace"]["chosen"],
                applicable_rules=[{"chunk_id": r["chunk_id"], "doc_id": r["doc_id"], "quote": r["quote"], "valid": r["valid"]}
                                  for r in rules_out],
                llm={"source": prop["llm"]["source"], "cache_hit": prop["llm"]["cache_hit"], "model": prop["llm"]["model"]})
        for o in opts:
            self._execute(aid, o, t, prop)
        for q in prop.get("questions_to_adviser", [])[:1]:
            if self.llm.provider != "none" and aid not in self.adviser_live_used:
                self.adviser_live_used.add(aid)
                self._ask(q, aid, t)

    def _execute(self, aid: str, o: dict[str, Any], t: float, prop: dict[str, Any]) -> None:
        atype = o["type"]
        self.counters["act"] += 1
        act_id = f"ACT-{self.counters['act']:03d}"
        action = {k: v for k, v in o.items() if not k.startswith("_")}
        voluntary = atype in VOLUNTARY
        if voluntary:
            action["internal"] = True  # G2 not required: voluntary information sharing (duty checked separately)
        involved = [a for a in ORDER if a != aid]
        v = self.gate.check_action(act_id, aid, action, involved)
        mandate = self.registry.find_mandate(aid, atype)
        cite_ids = [c.chunk_id for c in mandate.legal_basis] if mandate and not voluntary else []
        rec = {"action_id": act_id, "agent": aid, "t": t, "type": atype, "target": o.get("target"), "rule": o["_rule"],
               "mandate_id": mandate.mandate_id if mandate else None, "allowed": v.allowed, "flagged": v.flagged,
               "failed_rule": v.failed_rule, "voluntary": voluntary,
               "duty": bool(mandate and voluntary and "reform" in (mandate.note or ""))}
        self.actions.append(rec)
        self.verdicts.append({"t": t, **v.as_dict()})
        if v.gap_candidate:
            gid = self.gaps.candidate(v.gap_candidate, t, self.wave_at(t))
        else:
            gid = None
        if not v.allowed:
            self.ev(t, "gate_block", aid, item_id=act_id, kind="action", rule=v.failed_rule, action_type=atype,
                    target=o.get("target"), reason=v.reason, gap_id=gid, enforced=True,
                    checks=[c.as_dict() for c in v.checks])
            return
        if v.flagged:
            self.ev(t, "gate_flag", aid, item_id=act_id, kind="action", rule="G4", action_type=atype,
                    target=o.get("target"), reason=v.reason, gap_id=gid)
        elif v.failed_rule and not self.gate_on:
            self.ev(t, "gate_pass", aid, item_id=act_id, kind="action", rules=[c.rule for c in v.checks],
                    cite_ids=cite_ids, unenforced_failure=v.failed_rule, reason=v.reason)
        else:
            self.ev(t, "gate_pass", aid, item_id=act_id, kind="action", rules=[c.rule for c in v.checks], cite_ids=cite_ids)
        self.ev(t, "action", aid, action_id=act_id, type=atype, target=o.get("target"), internal=bool(o.get("internal")),
                status="executed", cite_ids=cite_ids, mandate_id=rec["mandate_id"], voluntary=voluntary)
        # world effects
        if atype == "request_vendor_rollback":
            self.rollback_requested_t = int(t)
            if "RF3" in self.reform_ids:
                nt, why = t + int(self.params["local_rollback_latency_min"]), "local rollback artefact (RF3)"
            else:
                extra = int(self.params["xborder_extra_delay_min"]) if self.knows("A1", "F_XBORDER") else 0
                nt, why = t + int(self.params["vendor_rollback_delay_min"]) + extra, "offshore vendor rollback"
            if self.restore_t is None or nt < self.restore_t:  # the earliest available remedy wins
                self._set_restore(nt, t, why)
        elif atype == "ml_safe_mode":
            nt = t + int(self.params["safe_mode_latency_min"])
            if self.restore_t is None or nt < self.restore_t:
                self._set_restore(nt, t, "mass-event safe-mode (RF2)")
        elif o.get("claims_lead"):
            others = [a for a, _ in self.lead_claims if a != aid]
            self.lead_claims.append((aid, int(t)))
            if others:
                self.counters.setdefault("lead_conflicts", 0)
                self.counters["lead_conflicts"] += 1
                gid2 = self.gaps.candidate({"type": "unclear_responsibility", "rule": "lead_conflict", "agent": aid,
                                            "action_type": atype, "target": None,
                                            "reason": f"{aid} and {', '.join(others)} both claim incident lead"},
                                           t, self.wave_at(t))
                self.ev(t, "gate_flag", aid, item_id=act_id, kind="action", rule="LEAD", action_type=atype, target=None,
                        reason=f"Lead conflict: {aid} and {', '.join(others)} both claim the incident lead", gap_id=gid2)
        elif atype == "public_rumour_rebuttal":
            self.rumour_rebutted_t = int(t)
        if o.get("target") in self.sc.agents:
            self._send(aid, o["target"], o, t, content=prop["messages_draft"].get(o["target"]) or
                       self.runtime._template_msg(aid, o))

    def _send(self, src: str, dst: str, o: dict[str, Any], t: float, content: str) -> None:
        self.counters["msg"] += 1
        mid = f"MSG-{self.counters['msg']:03d}"
        v = self.gate.check_message(mid, src, dst, content, lookup=self._turn_lookup.get(src))
        self.verdicts.append({"t": t, **v.as_dict()})
        if v.redacted:
            self.counters["claims_total"] += len(v.redacted)
            self.counters["redacted"] += len(v.redacted)
            for s in v.redacted:
                self.ev(t, "gate_block", src, item_id=mid, kind="claim", rule="G5", action_type="normative_claim",
                        target=dst, reason=f"uncited normative claim: {s[:160]}", gap_id=None, enforced=self.gate_on)
            if self.gate_on:
                content, _ = self.gate.scan_text(content, self._turn_lookup.get(src))
        facts = [f for f in (o.get("facts") or []) if self.beliefs[src].get(f, 0) > 0]
        if v.failed_rule == "G3":
            self.missing_pairs.add((src, dst))
        gid = None
        if v.gap_candidate:
            gid = self.gaps.candidate(v.gap_candidate, t, self.wave_at(t))
        if v.failed_rule == "G3" and self.gate_on:
            self.ev(t, "gate_block", src, item_id=mid, kind="message", rule="G3", action_type=o["type"], target=dst,
                    reason=v.reason + (f"; re-routed informally (+{v.latency} min)" if v.route == "informal" else "; dropped"),
                    gap_id=gid, enforced=True)
        else:
            self.ev(t, "gate_pass", src, item_id=mid, kind="message", rules=[c.rule for c in v.checks],
                    cite_ids=[c.chunk_id for c in (self.registry.channel(src, dst).legal_basis if self.registry.channel(src, dst) else [])],
                    **({"unenforced_failure": "G3"} if v.failed_rule == "G3" else {}))
        if v.route == "dropped":
            self.ev(t, "message", src, msg_id=mid, **{"from": src}, to=dst, channel_id=None, legal=False, sent_t=t,
                    deliver_t=None, facts=facts, content=content, status="dropped", route="dropped", kind=o["type"])
            return
        deliver_t = t + max(1, v.latency)
        msg = {"msg_id": mid, "from": src, "to": dst, "channel_id": v.channel_id, "legal": v.route in ("legal", "reform"),
               "sent_t": t, "deliver_t": deliver_t, "facts": facts, "content": content,
               "status": "delivered" if v.route in ("legal", "reform", "unchecked") else "delayed",
               "route": v.route, "kind": o["type"]}
        self.messages.append(msg)
        self.ev(t, "message", src, **msg)
        self.push(deliver_t, 0, "deliver", msg)

    def _ask(self, question: str, asked_by: str, t: float, preset_id: str | None = None) -> None:
        qa = self.runtime.adviser(question, asked_by, int(t), self.wave_at(t), self.audit)
        qa.pop("_map", None)
        sents = qa.pop("_sents", {})
        for part in ("uae_basis", "global_examples"):
            for it in qa[part]:
                self.counters["claims_total"] += 1
                chk = self.gate.check_quote(it["chunk_id"] or "", it["quote"])
                it["valid"] = chk.ok
                if chk.ok:
                    self.counters["claims_supported"] += 1
                else:
                    self.counters["invalid_quotes"] += 1
                    self.gate.stats["g1_fail"] += 1
        clean, red = self.gate.scan_text(qa["answer"], sents)
        if red:
            self.counters["claims_total"] += len(red)
            self.counters["redacted"] += len(red)
            if self.gate_on:
                qa["answer"] = clean
        qa["redacted"] = red
        qa["preset_id"] = preset_id
        self.qa.append(qa)
        self.ev(t, "adviser_qa", "A7", qa_id=qa["qa_id"], preset_id=preset_id, asked_by=asked_by, question=question,
                answer=qa["answer"], cite_ids=[i["chunk_id"] for i in qa["uae_basis"] if i.get("valid")],
                global_cite_ids=[i["chunk_id"] for i in qa["global_examples"] if i.get("valid")],
                invalid_quotes=sum(1 for p in ("uae_basis", "global_examples") for i in qa[p] if not i.get("valid")),
                gap=qa["gap"], confidence=qa["confidence"])

    def _checks(self, t: float) -> None:
        # Gap triggers that come from scenario facts rather than gate verdicts
        if self.knows("A1", "F_ROOT"):
            self.gaps.trigger("ai_incident_notification", t, self.wave_at(t), registry=self.registry)
            self.gaps.trigger("ml_update_validation", t, self.wave_at(t), registry=self.registry)
        if self.knows("A1", "F_XBORDER"):
            self.gaps.trigger("offshore_model_logs", t, self.wave_at(t), registry=self.registry)
        if self.knows("A6", "F_PDATA"):
            self.gaps.trigger("pdata_retraining", t, self.wave_at(t), registry=self.registry)
        if t >= int(self.params.get("lead_conflict_threshold_min", 60)) and not self.lead_claims:
            self.gaps.candidate({"type": "unclear_responsibility", "rule": "no_lead", "agent": "A8",
                                 "action_type": "claim_incident_lead", "target": None,
                                 "reason": "no authority has validly claimed the incident lead by the threshold"},
                                t, self.wave_at(t))
        if not self.harm_iap_done and any(self.knows(a, "F_HARM") for a in ORDER):
            self.harm_iap_done = True
            self._iap(t, "mid-crisis (harm detected)")

    def _iap(self, t: float, label: str) -> None:
        tasks = []
        for a in self.actions:
            if a["t"] > t:
                continue
            m = self.registry.mandate(a["mandate_id"]) if a["mandate_id"] else None
            tasks.append({"who": a["agent"], "what": a["type"] + (f" → {a['target']}" if a["target"] else ""),
                          "status": "done" if a["allowed"] else f"blocked ({a['failed_rule']}) — needs legal basis",
                          "legal_basis": [c.as_dict() for c in m.legal_basis] if m else [],
                          "by_when": f"T+{int(t) + 30}" if not a["allowed"] else f"T+{int(a['t'])}"})
        iap = {"iap_id": f"IAP-{len(self.iaps) + 1}", "t": t, "label": label, "tasks": tasks,
               "service_restored_estimate": self.restore_t}
        self.iaps.append(iap)
        self.ev(t, "action", "A8", action_id=iap["iap_id"], type="incident_action_plan", target=None, internal=True,
                status="issued", cite_ids=[], label=label, n_tasks=len(tasks))

    def _debrief(self) -> None:
        t = self.sc.horizon
        self._iap(t, "debrief (W8)")

    # ------------------------------------------------------------------ finish
    def _finish(self) -> dict[str, Any]:
        gaps = self.gaps.finalize(self.sc.horizon)
        for g in gaps:
            self.ev(g["t"], "gap", "A8", gap_id=g["gap_id"], type=g["type"], title=g["title"])
        self.timeline.sort(key=lambda e: (e["t"], e["seq"]))
        restored = self.restore_t if (self.restore_t is not None and self.restore_t <= self.sc.horizon) else None
        kpis = kpi_series(self.params, restored, self.sc.horizon)
        metrics = self._metrics(gaps, restored)
        out = {"meta": {"run_id": self.run_dir.name, "scenario": self.sc.id, "reform": sorted(self.reform_ids) or None,
                        "gate": self.gate_on, "llm": self.llm.label, "llm_adviser": self.llm_adviser.label,
                        "llm_stats": self.llm.stats,
                        "llm_adviser_stats": self.llm_adviser.stats if self.llm_adviser is not self.llm else None,
                        "retrieval_stats": self.retriever.stats, "audit_root": self.audit.root,
                        "audit_entries": self.audit.seq, "label": self.sc.label,
                        "mandates_loaded": len(self.registry.mandates), "channels_loaded": len(self.registry.channels),
                        "registry_rejected": self.registry.rejected},
               "metrics": metrics}
        w = lambda name, obj: (self.run_dir / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str),
                                                                encoding="utf-8")
        w("timeline.json", self.timeline)
        w("gaps.json", gaps)
        w("iap.json", self.iaps)
        w("metrics.json", metrics)
        w("adviser_qa.json", self.qa)
        w("gate.json", {"stats": self.gate.stats, "verdicts": self.verdicts})
        w("kpis.json", kpis)
        w("meta.json", out["meta"])
        with (self.run_dir / "proposals.jsonl").open("w", encoding="utf-8") as fh:
            for p in self.proposals:
                fh.write(json.dumps(p, ensure_ascii=False, default=str) + "\n")
        return out

    def _metrics(self, gaps: list[dict[str, Any]], restored: float | None) -> dict[str, Any]:
        tta = {a: {f: self.known_at[a].get(f) for f in self.sc.facts} for a in ORDER}
        pairs_missing = sorted(self.missing_pairs)
        by_type: dict[str, int] = {}
        for g in gaps:
            by_type[g["type"]] = by_type.get(g["type"], 0) + 1
        ops = ["A1", "A2", "A3", "A4", "A5"]
        conv = None  # root-cause convergence: every operational agent (A1–A5) knows F_ROOT
        if all(self.known_at[a].get("F_ROOT") is not None for a in ops):
            conv = max(self.known_at[a]["F_ROOT"] for a in ops)
        suppressed = sorted({e["payload"]["wave"] for e in self.timeline if e["type"] == "inject" and e["payload"].get("suppressed")})
        claims_total = self.counters["claims_total"]
        onset = self.params["kpi"]["onset_min"]
        return {
            "time_to_awareness": tta,
            "awareness_convergence_min": conv,
            "suppressed_waves": suppressed,
            "copilot_rca_lead_min": (15 - self.known_at["A1"]["F_ROOT"]) if self.known_at["A1"].get("F_ROOT") is not None else None,
            "coordination_messages": len(self.messages),
            "messages_legal": sum(1 for m in self.messages if m["route"] in ("legal", "reform")),
            "messages_informal": sum(1 for m in self.messages if m["route"] == "informal"),
            "missing_channels": len(pairs_missing),
            "missing_channel_pairs": [f"{a}→{b}" for a, b in pairs_missing],
            "conflicting_actions": sum(1 for a in self.actions if a["flagged"]) + self.counters.get("lead_conflicts", 0),
            "blocked_actions": sum(1 for a in self.actions if not a["allowed"]),
            "would_block_actions_if_gate_on": sum(1 for v in self.verdicts if v["kind"] == "action" and v["failed_rule"] in ("G1", "G2")),
            "rerouted_messages": sum(1 for v in self.verdicts if v["kind"] == "message" and v["failed_rule"] == "G3"),
            "gaps_by_type": by_type,
            "gaps_total": len(gaps),
            "citation_coverage": round(self.counters["claims_supported"] / claims_total, 3) if claims_total else None,
            "claims_total": claims_total,
            "claims_supported": self.counters["claims_supported"],
            "unsupported_claims_caught": (self.counters["invalid_quotes"] + self.counters["redacted"]) if self.gate_on else 0,
            "unsupported_claims_passed": 0 if self.gate_on else (self.counters["invalid_quotes"] + self.counters["redacted"]),
            "invalid_quotes": self.counters["invalid_quotes"],
            "redacted_normative_claims": self.counters["redacted"],
            "iap_count": len(self.iaps),
            "service_restored_min": restored,
            "degraded_minutes": (restored - onset) if restored is not None else (self.sc.horizon - onset),
            "lead_claims": [{"agent": a, "t": tt} for a, tt in self.lead_claims],
            "rumour_rebuttal_min": self.rumour_rebutted_t,
            "adviser_questions": len(self.qa),
            "llm_calls": self.llm.stats["calls"] + (self.llm_adviser.stats["calls"] if self.llm_adviser is not self.llm else 0),
        }


def run_scenario(scenario: str, reform: str | None, llm, run_name: str, gate_on: bool = True, replay: bool = False,
                 kb: KB | None = None, llm_adviser=None) -> dict[str, Any]:
    sc = load_scenario(scenario)
    rf = load_reform(reform)
    kb = kb or KB(offline=replay, load_dense=not replay)
    run_dir = config.RUNS_DIR / run_name
    coord = Coordinator(sc, rf, kb, llm, run_dir, gate_on=gate_on, replay=replay, llm_adviser=llm_adviser)
    return coord.run()

"""The P node — Mandate & Citation Gate (Y.3172 "Policy" step).

Checks every proposed action, message and claim:
  G1  each cited chunk exists and the quote is a substring of it (normalised)
  G2  the action type is inside one of the agent's cited mandates
  G3  a legal channel exists to the message recipient (else delay/drop per scenario rule)
  G4  objective-conflict check against the declared objectives of the agents involved
  G5  no uncited normative claim ("must / shall / is required …") in free text

On failure the item is blocked (G4: flagged) and a gap candidate is emitted.
With ``enforce=False`` (the ablation) every verdict is still computed and
logged, but nothing is blocked — this measures what would have slipped through.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from majlis.agents.mandates import Registry
from majlis.kb.textnorm import quote_in

NORMATIVE = re.compile(
    r"\b(must|shall|is required to|are required to|is obliged to|are obliged to|is obligated to|are obligated to|"
    r"has a duty to|have a duty to|is mandatory|are mandatory|is prohibited|are prohibited|legally required)\b",
    re.I,
)
CITE_MARK = re.compile(r"\[(?:S|U|G|C)?\d+(?:\.\d+)?\]|\[[A-Z0-9][A-Z0-9\-]+::\d{4}\]")
MIN_QUOTE_CHARS = 20
# A cited source can only support a normative claim if the source itself is normative.
NORMATIVE_SRC = re.compile(
    r"\b(shall|must|required|requires|obliged|obligat\w*|prohibit\w*|mandatory|duty|not later than|no later than|"
    r"within (?:\d+|one|two|six|twenty|thirty|seventy)\b)", re.I)

# Gap type spawned when an external action type is blocked for lack of a mandate (G2).
G2_GAP_TYPE = {
    "claim_incident_lead": "unclear_responsibility",
    "public_rumour_rebuttal": "unclear_responsibility",
    "cross_border_log_transfer": "technology_gap",
    "investigate_cyber_incident": "unclear_responsibility",
    "issue_directive": "legislative_gap",
    "request_information": "coordination_problem",
    "notify_incident": "legislative_gap",
    "share_information": "coordination_problem",
}


@dataclass
class Check:
    rule: str
    ok: bool
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"rule": self.rule, "ok": self.ok, "detail": self.detail}


@dataclass
class Verdict:
    item_id: str
    kind: str  # action | message | claim | rule_ref
    allowed: bool
    enforced: bool
    checks: list[Check] = field(default_factory=list)
    failed_rule: str | None = None
    reason: str = ""
    gap_candidate: dict[str, Any] | None = None
    flagged: bool = False  # G4 conflict (not blocked)
    route: str = "legal"
    latency: int = 0
    channel_id: str | None = None
    redacted: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"item_id": self.item_id, "kind": self.kind, "allowed": self.allowed, "enforced": self.enforced,
                "failed_rule": self.failed_rule, "reason": self.reason, "flagged": self.flagged,
                "checks": [c.as_dict() for c in self.checks], "route": self.route, "latency": self.latency,
                "channel_id": self.channel_id, "redacted": self.redacted,
                "gap_candidate": self.gap_candidate}


class Gate:
    def __init__(self, registry: Registry, chunks_by_id: dict[str, dict[str, Any]], objectives: dict[str, list[str]],
                 params: dict[str, Any], enforce: bool = True, priority_rules: list[dict[str, Any]] | None = None):
        self.reg = registry
        self.chunks = chunks_by_id
        self.objectives = objectives
        self.params = params
        self.enforce = enforce
        self.priority_rules = priority_rules or []
        self.stats = {"checked": 0, "blocked": 0, "would_block": 0, "flagged": 0, "g1_fail": 0, "g2_fail": 0,
                      "g3_fail": 0, "g4_flag": 0, "g5_fail": 0, "claims_checked": 0, "claims_cited": 0}

    # -- G1 ----------------------------------------------------------------
    def check_quote(self, chunk_id: str, quote: str) -> Check:
        c = self.chunks.get(chunk_id)
        if c is None:
            return Check("G1", False, f"cited chunk {chunk_id!r} does not exist")
        if len((quote or "").strip()) < MIN_QUOTE_CHARS:
            return Check("G1", False, "quote too short to verify")
        if not quote_in(quote, c["text"]):
            return Check("G1", False, f"quote not found verbatim in {chunk_id}")
        return Check("G1", True, f"quote verified in {chunk_id}")

    # -- G5 ----------------------------------------------------------------
    def scan_text(self, text: str, lookup: dict[str, str] | None = None) -> tuple[str, list[str]]:
        """G5. Return (text with unsupported normative sentences redacted, redacted sentences).

        A sentence stating an obligation must cite a source; when ``lookup`` (citation id → cited text) is given,
        at least one cited text must itself be normative (shall / must / required / a deadline), otherwise the
        claim is treated as unsupported even though it carries a citation marker.
        """
        if not text:
            return text, []
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        kept, red = [], []
        for s in parts:
            if NORMATIVE.search(s):
                self.stats["claims_checked"] += 1
                ids = [m.strip("[]") for m in CITE_MARK.findall(s)]
                supported = bool(ids)
                if supported and lookup is not None:
                    supported = any(NORMATIVE_SRC.search(lookup.get(i, "")) for i in ids)
                if supported:
                    self.stats["claims_cited"] += 1
                    kept.append(s)
                else:
                    red.append(s)
                    kept.append("[redacted by P-node: unsupported normative claim]")
            else:
                kept.append(s)
        return " ".join(kept), red

    # -- actions -------------------------------------------------------------
    def check_action(self, item_id: str, agent: str, action: dict[str, Any], involved: list[str]) -> Verdict:
        self.stats["checked"] += 1
        checks: list[Check] = []
        atype = action["type"]
        v = Verdict(item_id=item_id, kind="action", allowed=True, enforced=self.enforce)
        internal = bool(action.get("internal"))
        mandate = None
        if not internal:
            mandate = self.reg.find_mandate(agent, atype)
            if mandate is None:
                checks.append(Check("G2", False, f"no cited mandate of {agent} covers action type '{atype}'"))
            else:
                checks.append(Check("G2", True, f"within {mandate.mandate_id}"))
                for cit in mandate.legal_basis:
                    checks.append(self.check_quote(cit.chunk_id, cit.quote))
        else:
            checks.append(Check("G2", True, "internal operational action (own network), no public power exercised"))
        # G4 objective conflicts
        harms = set(action.get("harms") or [])
        conflict_with = []
        for other in involved:
            if other == agent:
                continue
            for obj in self.objectives.get(other, []):
                if obj in harms and not self._prioritised(action):
                    conflict_with.append(f"{other}:{obj}")
        if conflict_with:
            checks.append(Check("G4", False, "conflicts with declared objectives " + ", ".join(sorted(set(conflict_with)))))
        else:
            checks.append(Check("G4", True, "no objective conflict"))
        v.checks = checks
        failed = [c for c in checks if not c.ok and c.rule != "G4"]
        if failed:
            rule = failed[0].rule
            v.failed_rule, v.reason = rule, failed[0].detail
            self.stats[f"{rule.lower()}_fail"] += 1
            self.stats["would_block"] += 1
            if self.enforce:
                v.allowed = False
                self.stats["blocked"] += 1
            v.gap_candidate = {"type": G2_GAP_TYPE.get(atype, "legislative_gap") if rule == "G2" else "legislative_gap",
                               "rule": rule, "agent": agent, "action_type": atype, "target": action.get("target"),
                               "reason": v.reason}
        if conflict_with:
            v.flagged = True
            self.stats["flagged"] += 1
            self.stats["g4_flag"] += 1
            v.failed_rule = v.failed_rule or "G4"
            v.reason = v.reason or checks[-1].detail
            if v.gap_candidate is None:
                v.gap_candidate = {"type": "conflicting_objectives", "rule": "G4", "agent": agent, "action_type": atype,
                                   "target": action.get("target"), "reason": checks[-1].detail}
        return v

    def _prioritised(self, action: dict[str, Any]) -> bool:
        return any(action["type"] in r.get("action_types", []) for r in self.priority_rules)

    # -- messages --------------------------------------------------------------
    def check_message(self, item_id: str, src: str, dst: str, content: str, mandate_ok: bool = True,
                      lookup: dict[str, str] | None = None) -> Verdict:
        self.stats["checked"] += 1
        v = Verdict(item_id=item_id, kind="message", allowed=True, enforced=self.enforce)
        ch = self.reg.channel(src, dst)
        if ch is None:
            v.checks.append(Check("G3", False, f"no legal channel {src}→{dst} in the cited corpus"))
            self.stats["g3_fail"] += 1
            self.stats["would_block"] += 1
            v.failed_rule = "G3"
            v.reason = f"No legal channel {src}→{dst} can be cited"
            policy = self.params.get("no_channel_policy", "delay")
            if self.enforce:
                self.stats["blocked"] += 1
                if policy == "drop":
                    v.allowed = False
                    v.route = "dropped"
                else:
                    v.route = "informal"
                    v.latency = int(self.params.get("informal_latency_min", 35))
            else:
                v.route = "unchecked"
                v.latency = int(self.params.get("default_channel_latency_min", 10))
            v.gap_candidate = {"type": "coordination_problem", "rule": "G3", "agent": src, "target": dst,
                               "action_type": "message", "reason": v.reason}
        else:
            v.checks.append(Check("G3", True, f"channel {ch.channel_id} ({ch.type})"))
            for cit in ch.legal_basis:
                v.checks.append(self.check_quote(cit.chunk_id, cit.quote))
            v.channel_id = ch.channel_id
            v.latency = ch.latency_min
            v.route = "legal" if ch.origin == "law" else "reform"
        clean, red = self.scan_text(content, lookup)
        if red:
            self.stats["g5_fail"] += len(red)
            v.checks.append(Check("G5", False, f"{len(red)} uncited normative claim(s)"))
            v.redacted = red
        else:
            v.checks.append(Check("G5", True, "no uncited normative claims"))
        return v

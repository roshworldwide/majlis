"""Agent runtime: one turn = observe → retrieve → reason (LLM or template) → Proposal.

The playbook (scenario SOPs) supplies the options deterministically; the LLM
writes the situation assessment, applicable rules (with quotes), rationale and
messages; the P-node gate then validates everything. The adviser (A7) answers
questions with UAE adherence + global examples, every quote gate-checked.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from majlis import config
from majlis.agents.schemas import AdviserOut, RecoOut, TurnOut
from majlis.kb.store import Hit
from majlis.kb.textnorm import sentences, tokens

SYSTEM_AGENT = (
    "You are {name}, a SIMULATED agent modelled on {modelled_on}, in a FICTIONAL tabletop exercise about an AI-caused "
    "telecom network incident. You do not represent or speak for any real institution. Be concise and factual. "
    "Only use the numbered sources you are given. Never invent laws, article numbers, deadlines or quotes. "
    "Reply with a single JSON object only."
)

SYSTEM_ADVISER = (
    "You are the Policy & Legal Adviser agent in a FICTIONAL simulation. You answer only from the numbered sources "
    "given (U = UAE sources, G = global examples). Never state that something is required, mandatory or due by a "
    "deadline unless a cited sentence itself says so. If the UAE sources do not answer the question, say so plainly. "
    "Never invent laws, articles or deadlines. Reply with a single JSON object only."
)


def best_sentence(text: str, query: str, min_len: int = 40, max_len: int = 320) -> str:
    """Pick the sentence of ``text`` with the highest token overlap with ``query`` (verbatim)."""
    q = set(tokens(query))
    best, score = "", -1.0
    for s in sentences(text):
        if len(s) < min_len:
            continue
        cand = s if len(s) <= max_len else s[:max_len].rsplit(" ", 1)[0]
        st = set(tokens(cand))
        sc = len(q & st) / (1 + 0.02 * len(st))
        if sc > score:
            best, score = cand, sc
    if not best:
        flat = " ".join(text.split())
        best = flat[:max_len].rsplit(" ", 1)[0] if len(flat) > max_len else flat
    return best


def excerpt(text: str, query: str, n_words: int = 90) -> str:
    """A verbatim window of the chunk centred on its best-matching sentence."""
    s = best_sentence(text, query, min_len=20, max_len=600)
    flat = " ".join(text.split())
    i = flat.find(" ".join(s.split()))
    if i < 0:
        words = flat.split()
        return " ".join(words[:n_words])
    words_before = flat[:i].split()
    start_words = words_before[-25:] if len(words_before) > 25 else words_before
    window = (" ".join(start_words) + " " + flat[i:]).split()
    return " ".join(window[:n_words])


def _src_block(hits: list[Hit], prefix: str, query: str) -> tuple[str, dict[str, Hit]]:
    lines, mapping = [], {}
    for i, h in enumerate(hits, 1):
        key = f"{prefix}{i}"
        mapping[key] = h
        m = h.meta
        loc = " ".join(x for x in [m.get("article") or "", f"p.{m.get('page')}" if m.get("page") else ""] if x)
        lines.append(f"[{key}] {m.get('title', h.doc_id)[:90]} — {loc}\n\"{excerpt(h.text, query)}\"")
    return "\n".join(lines), mapping


class AgentRuntime:
    def __init__(self, scenario, retriever, llm, registry, facts: dict[str, dict[str, str]], llm_adviser=None):
        self.sc = scenario
        self.retriever = retriever
        self.llm = llm
        self.llm_a = llm_adviser or llm  # A7 may run a larger model than A1–A6 (role-sized models)
        self.reg = registry
        self.facts = facts

    # ------------------------------------------------------------------ turns
    def turn(self, aid: str, t: int, wave: str, observations: list[str], beliefs: dict[str, float],
             options: list[dict[str, Any]], audit) -> dict[str, Any]:
        prof = self.sc.agents[aid]
        opt_text = "; ".join(self._opt_label(o) for o in options)
        query = f"{prof['name']} {prof['modelled_on']} " + " ".join(observations[-2:]) + " " + opt_text
        hits = self.retriever.search(query, k=4, collections=prof.get("collections") or None, agent=aid, t=t, audit=audit)
        src_text, mapping = _src_block(hits, "S", query)
        mandates = self.reg.mandates_for(aid)
        mand_text = "\n".join(f"- {m.mandate_id}: {m.title} (action types: {', '.join(m.action_types)})" for m in mandates) \
            or "- none citable in the corpus (any public-power action will be checked by the gate)"
        know = ", ".join(f"{f}={c:.2f}" for f, c in sorted(beliefs.items()) if c > 0) or "nothing yet"
        targets = sorted({o["target"] for o in options if o.get("target") in self.sc.agents})
        prompt = (
            f"Time: T+{t} min ({wave}). Fictional scenario: {self.sc.title}.\n"
            f"Your cited mandates:\n{mand_text}\n"
            f"New observations:\n" + "\n".join(f"- {o}" for o in observations[-4:]) + "\n"
            f"Your beliefs (fact=confidence): {know}\n"
            f"Sources (cite by id):\n{src_text}\n"
            f"Options the exercise playbook puts in front of you this turn:\n"
            + "\n".join(f"- O{i+1}: {self._opt_prompt(o)}" for i, o in enumerate(options)) + "\n"
            "Return JSON with keys: \"situation\" (1-2 sentences), \"applicable_rules\" (list of at most 2 objects "
            "{\"source\": \"S1\", \"quote\": \"<words copied exactly from that source>\", \"why\": \"...\"}), "
            "\"why\" (1-2 sentences on the options), \"messages\" (list of {\"to\": \"<agent id>\", \"content\": \"<short "
            f"message>\"}} for recipients {targets}), \"questions_to_adviser\" (0 or 1 short question). "
            "Do not state a legal obligation ('must', 'shall', 'required') unless you cite a source id in brackets, e.g. [S1]."
        )
        system = SYSTEM_AGENT.format(name=prof["name"], modelled_on=prof["modelled_on"])

        def fallback() -> dict[str, Any]:
            rules = []
            if hits:
                q = best_sentence(hits[0].text, query)
                rules.append({"source": "S1", "quote": q, "why": "closest provision retrieved for this turn"})
            msgs = [{"to": o["target"], "content": self._template_msg(aid, o)} for o in options if o.get("target") in self.sc.agents]
            return {"situation": f"T+{t}: " + " ".join(observations[-2:])[:400],
                    "applicable_rules": rules,
                    "why": f"Playbook options for the {prof['name']}: {opt_text}. Each item is submitted to the P-node gate.",
                    "messages": msgs, "questions_to_adviser": []}

        out, meta = self.llm.generate(system, prompt, TurnOut, fallback, tag=f"turn:{aid}:{wave}:{t}")
        audit.append("llm_call", {"agent": aid, "purpose": "turn", **meta}, sim_minute=t)
        rules = []
        for r in out.applicable_rules[:2]:
            h = mapping.get(r.source.strip().strip("[]"))
            rules.append({"source": r.source, "chunk_id": h.chunk_id if h else None, "doc_id": h.doc_id if h else None,
                          "quote": r.quote, "why": r.why})
        msgs = {m.to.strip(): m.content for m in out.messages if m.to}
        proposal = {
            "proposal_id": f"P-{aid}-{t:03d}",
            "agent": aid, "wave": wave, "t": t,
            "observations": observations[-4:],
            "beliefs": {f: round(c, 2) for f, c in beliefs.items() if c > 0},
            "reasoning_trace": {
                "situation": out.situation,
                "applicable_rules": rules,
                "options": [self._opt_label(o) for o in options],
                "chosen": [self._opt_label(o) for o in options],
                "why": out.why,
            },
            "retrieval": [h.cite() for h in hits],
            "messages_draft": msgs,
            "questions_to_adviser": out.questions_to_adviser[:1],
            "llm": meta,
            "_mapping": {k: v.chunk_id for k, v in mapping.items()},
            "_lookup": {k: v.text for k, v in mapping.items()},
        }
        return proposal

    def _opt_label(self, o: dict[str, Any]) -> str:
        tgt = o.get("target")
        facts = o.get("facts") or []
        return f"{o['type']}" + (f" → {tgt}" if tgt else "") + (f" [{', '.join(facts)}]" if facts else "")

    def _opt_prompt(self, o: dict[str, Any]) -> str:
        label = self._opt_label(o)
        tgt = o.get("target")
        if tgt in self.sc.agents:
            facts = "; ".join(self.facts[f]["label"] for f in (o.get("facts") or []) if f in self.facts)
            what = {"notify_incident": "inform", "share_information": "share with", "request_information": "ask",
                    "query_status": "ask", "issue_directive": "instruct", "examine_complaint": "ask",
                    "investigate_cyber_incident": "ask"}.get(o["type"], "message")
            return f"{label} — {what} {tgt} ({self.sc.agents[tgt]['name']})" + (f" about: {facts}" if facts else "")
        return label

    def _template_msg(self, aid: str, o: dict[str, Any]) -> str:
        labels = "; ".join(self.facts[f]["label"] for f in (o.get("facts") or []) if f in self.facts)
        verb = {"notify_incident": "Incident notice", "request_information": "Request for information",
                "share_information": "Information share", "issue_directive": "Directive",
                "investigate_cyber_incident": "Investigation request", "respond_information": "Response"}.get(o["type"], o["type"])
        return f"{verb} from {self.sc.agents[aid]['name']}" + (f": {labels}." if labels else ".")

    # ---------------------------------------------------------------- adviser
    def adviser(self, question: str, asked_by: str, t: int, wave: str, audit, k_uae: int = 2, k_glob: int = 3) -> dict[str, Any]:
        """Evidence-first adviser. The engine selects the evidence — the most relevant cited mandates/channels
        (kb_mandates), UAE provisions (kb_uae) and global clauses (kb_global_examples) — and copies the best-matching
        sentence of each verbatim. The LLM only composes the answer, citing [U#]/[G#]. A quote therefore cannot be
        paraphrased, and G5 still checks that any obligation stated in the answer cites a normative sentence."""
        mand = self.retriever.search(question, k=2, collections=["kb_mandates"], agent="A7", t=t, audit=audit)
        uae = self.retriever.search(question, k=k_uae + 1, collections=["kb_uae"], agent="A7", t=t, audit=audit)
        glob = self.retriever.search(question, k=k_glob, collections=["kb_global_examples"], agent="A7", t=t, audit=audit)
        u_hits: list[Hit] = []
        for h in mand + uae:
            if h.chunk_id not in {x.chunk_id for x in u_hits} and len(u_hits) < 4:
                u_hits.append(h)
        sel: dict[str, tuple[Hit, str]] = {}
        lines = []
        for prefix, hits in (("U", u_hits), ("G", glob)):
            for i, h in enumerate(hits, 1):
                src = h
                text = h.text
                if h.doc_id.startswith("MAJLIS-MANDATES"):  # quote the underlying statute, not the derived index
                    m = re.search(r'"([^"]{25,})"', text)
                    sent = m.group(1) if m else best_sentence(text, question)
                    src_ids = h.meta.get("source_chunks") or []
                    c = self.retriever.kb.get(src_ids[0]) if src_ids else None
                    if c is not None:
                        from majlis.kb.store import Hit as _H
                        src = _H(chunk_id=c["chunk_id"], doc_id=c["doc_id"], score=h.score, rank=h.rank, text=c["text"],
                                 meta={k: v for k, v in c.items() if k != "text"})
                else:
                    sent = best_sentence(text, question)
                sid = f"{prefix}{i}"
                sel[sid] = (src, sent)
                loc = " ".join(x for x in [src.meta.get("article") or "", f"p.{src.meta.get('page')}" if src.meta.get("page") else ""] if x)
                lines.append(f"[{sid}] {src.meta.get('title', src.doc_id)[:80]} — {loc}: \"{sent}\"")
        prompt = (
            f"Question from {asked_by} ({self.sc.agents.get(asked_by, {}).get('name', asked_by)}) at T+{t} ({wave}): {question}\n\n"
            "Evidence (U = UAE instruments, G = other jurisdictions):\n" + "\n".join(lines) + "\n\n"
            "Write JSON with exactly three keys: \"answer\": 3 to 4 plain sentences answering the question from the "
            "evidence, citing ids in brackets like [U1] or [G2]; say clearly if the UAE evidence does not answer the "
            "question. \"gap\": one sentence on any gap between the UAE evidence and the global examples, or \"\". "
            "\"confidence\": \"low\", \"med\" or \"high\"."
        )

        def fallback() -> dict[str, Any]:
            u = [k for k in sel if k.startswith("U")][:2]
            g = [k for k in sel if k.startswith("G")][:2]
            ans = ("Closest UAE provisions: " + "; ".join(f"[{k}] {sel[k][0].doc_id} {sel[k][0].meta.get('article') or ''}".strip() for k in u)
                   + ". Global examples: " + "; ".join(f"[{k}] {sel[k][0].doc_id} {sel[k][0].meta.get('article') or ''}".strip() for k in g) + ".")
            return {"answer": ans, "gap": "", "confidence": "low"}

        out, meta = self.llm_a.generate(SYSTEM_ADVISER, prompt, AdviserOut, fallback, tag=f"adviser:{asked_by}:{t}")
        audit.append("llm_call", {"agent": "A7", "purpose": "adviser", **meta}, sim_minute=t)
        answer = out.answer.strip()
        if answer.startswith("{") or len(answer) < 30:  # model returned a fragment instead of prose
            answer = fallback()["answer"]
            meta["source"] = (meta.get("source") or "") + " → template answer (malformed)"
        cited = set(re.findall(r"\[([UG]\d+)\]", answer))

        def pack(prefix):
            return [{"source": k, "chunk_id": h.chunk_id, "doc_id": h.doc_id, "quote": q,
                     "article": ", ".join(h.meta.get("articles") or []) or h.meta.get("article"),
                     "how": f"{h.meta.get('title', h.doc_id)[:70]} {h.meta.get('article') or ''}".strip(), "cited_in_answer": k in cited}
                    for k, (h, q) in sel.items() if k.startswith(prefix)]

        return {
            "qa_id": "QA-" + hashlib.sha256(f"{asked_by}{t}{question}".encode()).hexdigest()[:8],
            "asked_by": asked_by, "t": t, "wave": wave, "question": question,
            "answer": answer, "uae_basis": pack("U"), "global_examples": pack("G"),
            "gap": out.gap, "confidence": out.confidence, "llm": meta,
            "retrieval": {"uae": [h.cite() for h in u_hits], "global": [h.cite() for h in glob]},
            "_map": {k: v[0].chunk_id for k, v in sel.items()},
            "_sents": {k: v[1] for k, v in sel.items()},
        }

    # --------------------------------------------------------- gap recommendation
    def recommend(self, gap: dict[str, Any], examples: list[dict[str, Any]], audit, t: int) -> dict[str, Any]:
        ex_text = "\n".join(f"[G{i+1}] {e['doc_id']} {e.get('article','')}: \"{e['quote']}\" — {e.get('how','')}"
                            for i, e in enumerate(examples))
        prompt = (
            f"Domain: {gap['domain']}.\nGap type: {gap['type']}.\nGap: {gap['title']}. {gap['description']}\n"
            f"Global examples (verified quotes):\n{ex_text}\n\n"
            "Write a DOMAIN-LEVEL policy recommendation in 2-3 sentences that closes this gap for ANY jurisdiction. "
            "Do not name any country or institution; do not write document identifiers; describe the mechanism and cite "
            "the examples in brackets like [G1]. Return JSON {\"recommendation\": \"...\", \"rationale\": \"...\"}."
        )

        def fallback() -> dict[str, Any]:
            return {"recommendation": gap.get("recommendation_seed", ""), "rationale": "template (seed recommendation)"}

        out, meta = self.llm_a.generate(SYSTEM_ADVISER, prompt, RecoOut, fallback, tag=f"reco:{gap['key']}")
        audit.append("llm_call", {"agent": "A7", "purpose": "gap_recommendation", "gap": gap["key"], **meta}, sim_minute=t)
        return {"recommendation": out.recommendation or gap.get("recommendation_seed", ""), "rationale": out.rationale,
                "llm": meta}

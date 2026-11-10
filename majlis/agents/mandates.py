"""Institutional mandates and legal channels (countries/<cc>/mandates.yaml).

Rule: if a mandate cannot be cited, it does not load. Every ``legal_basis``
quote is checked (G1 at load time) against the canonical chunk store; entries
that fail are rejected and reported. The absence of a mandate or channel is
gap evidence, never something to paper over.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from majlis import config
from majlis.kb.textnorm import quote_in


@dataclass
class Citation:
    doc_id: str
    quote: str
    article: str = ""
    chunk_id: str = ""
    page: int | None = None
    url: str = ""
    title: str = ""
    valid: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"doc_id": self.doc_id, "chunk_id": self.chunk_id, "article": self.article, "page": self.page,
                "quote": self.quote, "url": self.url, "title": self.title}


@dataclass
class Mandate:
    mandate_id: str
    agent: str
    title: str
    action_types: list[str]
    legal_basis: list[Citation]
    note: str = ""


@dataclass
class Channel:
    channel_id: str
    src: str
    dst: str
    type: str
    latency_min: int
    legal_basis: list[Citation]
    origin: str = "law"  # law | reform


@dataclass
class Registry:
    country: str
    institutions: dict[str, dict[str, Any]]
    mandates: list[Mandate] = field(default_factory=list)
    channels: list[Channel] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)

    def mandates_for(self, agent: str) -> list[Mandate]:
        return [m for m in self.mandates if m.agent == agent]

    def mandate(self, mandate_id: str) -> Mandate | None:
        return next((m for m in self.mandates if m.mandate_id == mandate_id), None)

    def find_mandate(self, agent: str, action_type: str) -> Mandate | None:
        return next((m for m in self.mandates if m.agent == agent and action_type in m.action_types), None)

    def channel(self, src: str, dst: str) -> Channel | None:
        cands = [c for c in self.channels if c.src == src and c.dst == dst]
        return min(cands, key=lambda c: c.latency_min) if cands else None


def resolve_citation(raw: dict[str, Any], chunks_by_doc: dict[str, list[dict[str, Any]]]) -> Citation:
    cit = Citation(doc_id=raw["doc_id"], quote=raw["quote"], article=str(raw.get("article", "")))
    for c in chunks_by_doc.get(cit.doc_id, []):
        if quote_in(cit.quote, c["text"]):
            cit.chunk_id = c["chunk_id"]
            cit.page = c.get("page")
            cit.url = c.get("url", "")
            cit.title = c.get("title", "")
            cit.article = cit.article or c.get("article", "")
            cit.valid = True
            break
    return cit


def _group(chunks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by: dict[str, list[dict[str, Any]]] = {}
    for c in chunks:
        by.setdefault(c["doc_id"], []).append(c)
    return by


def load_registry(country: str, chunks: list[dict[str, Any]], path: Path | None = None) -> Registry:
    path = path or (config.COUNTRIES_DIR / country / "mandates.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    data = data or {}
    by_doc = _group(chunks)
    reg = Registry(country=country, institutions=data.get("institutions", {}))
    for m in data.get("mandates", []) or []:
        cits = [resolve_citation(c, by_doc) for c in m.get("legal_basis", [])]
        bad = [c for c in cits if not c.valid]
        if not cits or bad:
            reg.rejected.append({"kind": "mandate", "id": m.get("mandate_id"),
                                 "reason": "no legal_basis" if not cits else f"quote not found in {bad[0].doc_id}"})
            continue
        reg.mandates.append(Mandate(mandate_id=m["mandate_id"], agent=m["agent"], title=m.get("title", ""),
                                    action_types=list(m.get("action_types", [])), legal_basis=cits,
                                    note=m.get("note", "")))
    for ch in data.get("channels", []) or []:
        cits = [resolve_citation(c, by_doc) for c in ch.get("legal_basis", [])]
        bad = [c for c in cits if not c.valid]
        if not cits or bad:
            reg.rejected.append({"kind": "channel", "id": ch.get("channel_id"),
                                 "reason": "no legal_basis" if not cits else f"quote not found in {bad[0].doc_id}"})
            continue
        reg.channels.append(Channel(channel_id=ch["channel_id"], src=ch["from"], dst=ch["to"], type=ch.get("type", ""),
                                    latency_min=int(ch.get("latency_min", 10)), legal_basis=cits))
    return reg


def mandate_chunks(chunks: list[dict[str, Any]], country: str = "uae") -> list[dict[str, Any]]:
    """Derived kb_mandates chunks: one per validated mandate/channel."""
    path = config.COUNTRIES_DIR / country / "mandates.yaml"
    if not path.exists():
        return []
    reg = load_registry(country, chunks, path)
    out = []
    for m in reg.mandates:
        inst = reg.institutions.get(m.agent, {})
        basis = "\n".join(f"- {c.doc_id} {c.article} (p.{c.page}): \"{c.quote}\"" for c in m.legal_basis)
        text = (f"Mandate {m.mandate_id} — agent {m.agent} ({inst.get('role', '')}, modelled on {inst.get('modelled_on', '')}). "
                f"{m.title}. Permitted action types: {', '.join(m.action_types)}.\nLegal basis:\n{basis}")
        out.append(_derived(f"MAJLIS-MANDATES-{country.upper()}::{m.mandate_id}", text, m.mandate_id, m.legal_basis))
    for ch in reg.channels:
        basis = "\n".join(f"- {c.doc_id} {c.article} (p.{c.page}): \"{c.quote}\"" for c in ch.legal_basis)
        text = f"Channel {ch.channel_id}: {ch.src} → {ch.dst} ({ch.type}).\nLegal basis:\n{basis}"
        out.append(_derived(f"MAJLIS-MANDATES-{country.upper()}::{ch.channel_id}", text, ch.channel_id, ch.legal_basis))
    return out


def _derived(chunk_id: str, text: str, label: str, cits: list[Citation]) -> dict[str, Any]:
    return {
        "doc_id": chunk_id.split("::")[0], "title": "MAJLIS institutional mandates registry (derived, cited)",
        "issuer": "MAJLIS (derived from cited UAE sources)", "country": "UAE", "doc_type": "mandate",
        "document_category": "Mandates", "collection": "kb_mandates", "date": "2026-11-10",
        "url": cits[0].url if cits else "", "retrieved_at": "", "sha256": "",
        "license_note": "Derived index; quotes from cited sources", "chunk_id": chunk_id, "text": text,
        "page": 1, "page_end": 1, "section": "", "article": label, "articles": [label], "n_words": len(text.split()),
        "readiness_dims": ["d7", "d10"], "y3172_nodes": ["P"], "source_chunks": [c.chunk_id for c in cits],
    }

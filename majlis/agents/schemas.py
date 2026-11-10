"""Pydantic schemas: what the LLM must return, and what the engine records."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


def _strs(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v.strip() else []
    out = []
    for x in v:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            out.append(str(x.get("question") or x.get("text") or x.get("content") or next(iter(x.values()), "")))
        else:
            out.append(str(x))
    return [s for s in out if s.strip()]


class RuleRef(BaseModel):
    source: str = ""
    quote: str = ""
    why: str = ""

    @field_validator("source", "quote", "why", mode="before")
    @classmethod
    def _s(cls, v):
        return "" if v is None else str(v)


class MsgOut(BaseModel):
    to: str = ""
    content: str = ""

    @field_validator("to", "content", mode="before")
    @classmethod
    def _s(cls, v):
        return "" if v is None else str(v)


class TurnOut(BaseModel):
    """LLM output for one agent turn (structured, explicit rationale)."""

    situation: str = ""
    applicable_rules: list[RuleRef] = Field(default_factory=list)
    why: str = ""
    messages: list[MsgOut] = Field(default_factory=list)
    questions_to_adviser: list[str] = Field(default_factory=list)

    @field_validator("situation", "why", mode="before")
    @classmethod
    def _s(cls, v):
        if isinstance(v, (list, dict)):
            return " ".join(str(x) for x in (v if isinstance(v, list) else v.values()))
        return "" if v is None else str(v)

    @field_validator("questions_to_adviser", mode="before")
    @classmethod
    def _q(cls, v):
        return _strs(v)[:2]

    @field_validator("applicable_rules", "messages", mode="before")
    @classmethod
    def _l(cls, v):
        if v is None:
            return []
        if isinstance(v, dict):
            return [v]
        return [x for x in v if isinstance(x, dict)][:4]


class SourceQuote(BaseModel):
    source: str = ""
    quote: str = ""
    how_they_closed_it: str = ""

    @field_validator("source", "quote", "how_they_closed_it", mode="before")
    @classmethod
    def _s(cls, v):
        return "" if v is None else str(v)


class AdviserOut(BaseModel):
    answer: str = ""
    uae_basis: list[SourceQuote] = Field(default_factory=list)
    global_examples: list[SourceQuote] = Field(default_factory=list)
    gap: str = ""
    confidence: str = "low"

    @field_validator("answer", "gap", "confidence", mode="before")
    @classmethod
    def _s(cls, v):
        if isinstance(v, (list, dict)):
            return " ".join(str(x) for x in (v if isinstance(v, list) else v.values()))
        return "" if v is None else str(v)

    @field_validator("uae_basis", "global_examples", mode="before")
    @classmethod
    def _l(cls, v):
        if v is None:
            return []
        if isinstance(v, dict):
            return [v]
        return [x for x in v if isinstance(x, dict)][:3]


class RecoOut(BaseModel):
    recommendation: str = ""
    rationale: str = ""

    @field_validator("recommendation", "rationale", mode="before")
    @classmethod
    def _s(cls, v):
        if isinstance(v, (list, dict)):
            return " ".join(str(x) for x in (v if isinstance(v, list) else v.values()))
        return "" if v is None else str(v)

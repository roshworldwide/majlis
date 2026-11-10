"""Scenario + reform-pack loader (Y.3172 C node for scenario telemetry/injects)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from majlis import config


@dataclass
class Wave:
    id: str
    t: int
    visible_to: list[str]
    content: str
    reveals: dict[str, float]
    telemetry: dict[str, Any] = field(default_factory=dict)
    hidden_fact: str = ""
    condition: Any = None


@dataclass
class PlayRule:
    id: str
    agent: str
    action: dict[str, Any]
    knows: list[str] = field(default_factory=list)
    knows_any: list[str] = field(default_factory=list)
    not_knows: list[str] = field(default_factory=list)
    min_t: int = 0
    reform: str | None = None
    no_reform: str | None = None
    signal: list[str] = field(default_factory=list)
    min_conf: float | None = None


@dataclass
class Scenario:
    id: str
    title: str
    label: str
    domain: str
    country: str
    horizon: int
    params: dict[str, Any]
    facts: dict[str, str]
    agents: dict[str, dict[str, Any]]
    waves: list[Wave]
    playbook: list[PlayRule]
    adviser_questions: list[dict[str, Any]]
    expected: dict[str, Any]
    raw: dict[str, Any]


def load_scenario(name_or_path: str) -> Scenario:
    p = Path(name_or_path)
    if not p.exists():
        p = config.SCENARIOS_DIR / f"{name_or_path}.yaml"
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    waves = [Wave(id=w["id"], t=int(w["t"]), visible_to=list(w["visible_to"]), content=w["content"].strip(),
                  reveals={k: float(v) for k, v in (w.get("reveals") or {}).items()},
                  telemetry=w.get("telemetry") or {}, hidden_fact=w.get("hidden_fact", ""), condition=w.get("condition"))
             for w in d["waves"]]
    play = []
    for r in d.get("playbook", []):
        w = r.get("when", {}) or {}
        play.append(PlayRule(id=r["id"], agent=r["agent"], action=r["action"], knows=w.get("knows", []),
                             knows_any=w.get("knows_any", []), not_knows=w.get("not_knows", []),
                             min_t=int(w.get("min_t", 0)), reform=w.get("reform"), no_reform=w.get("no_reform"),
                             signal=w.get("signal", []), min_conf=w.get("min_conf")))
    return Scenario(id=d["scenario_id"], title=d["title"], label=d["label"], domain=d["domain"], country=d["country"],
                    horizon=int(d.get("horizon_min", 90)), params=d.get("params", {}), facts=d["facts"],
                    agents=d["agents"], waves=sorted(waves, key=lambda w: w.t), playbook=play,
                    adviser_questions=d.get("adviser_questions", []), expected=d.get("expected", {}), raw=d)


def load_reform(name_or_path: str | None) -> dict[str, Any] | None:
    if not name_or_path:
        return None
    p = Path(name_or_path)
    if not p.exists():
        p = config.SCENARIOS_DIR / "reforms" / f"{name_or_path}.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))

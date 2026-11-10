"""replay.json — the contract between the engine and the MAJLIS Experience (§8A.7).

The front end is a pure renderer of this file: scene state = f(t). The schema
is published as ``replay.schema.json`` (JSON Schema 2020-12) and mirrored in
``web/src/replay.schema.ts`` (zod).

Audit verification recipe (browser == CLI, byte-exact):
  for each line L of audit.jsonl (canonical JSON, keys sorted, no spaces):
    h      = JSON.parse(L).hash
    body   = L with the exact member  "hash":"<h>",  removed (it is never last)
    assert sha256(body) == h
    assert JSON.parse(L).prev_hash == previous h  (genesis = 64 zeros)
  root = last h ; N = number of lines
"""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path
from typing import Any

from majlis import config

EVENT_TYPES = ["inject", "message", "proposal", "gate_pass", "gate_block", "gate_flag", "belief", "gap",
               "adviser_qa", "kpi", "action"]
GAP_TYPES = ["unclear_responsibility", "standards_gap", "technology_gap", "legislative_gap", "coordination_problem",
             "conflicting_objectives"]
CLUSTERS = ["uae", "global", "itu", "other"]

_series = {"type": "array", "items": {"type": "array", "prefixItems": [{"type": "number"}, {"type": "number"}],
                                      "minItems": 2, "maxItems": 2}}

_run_part = {
    "type": "object",
    "required": ["run_id", "timeline", "kpis", "gaps"],
    "properties": {
        "run_id": {"type": "string"},
        "timeline": {"$ref": "#/$defs/timeline"},
        "kpis": {"$ref": "#/$defs/kpis"},
        "gaps": {"type": "array", "items": {"$ref": "#/$defs/gap"}},
        "audit": {"$ref": "#/$defs/audit"},
    },
}

REPLAY_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://github.com/roshworldwide/majlis/replay.schema.json",
    "title": "MAJLIS replay",
    "type": "object",
    "required": ["meta", "agents", "channels", "facts", "waves", "timeline", "kpis", "gaps", "citations",
                 "kb_points", "audit", "compare"],
    "$defs": {
        "event": {
            "type": "object",
            "required": ["t", "wave", "type", "agent", "payload"],
            "properties": {
                "seq": {"type": "integer"},
                "t": {"type": "number", "description": "simulation minute (T+0 = 22:30 fictional)"},
                "wave": {"type": "string"},
                "type": {"enum": EVENT_TYPES},
                "agent": {"type": ["string", "null"]},
                "payload": {"type": "object"},
            },
        },
        "timeline": {"type": "array", "items": {"$ref": "#/$defs/event"}},
        "kpis": {
            "type": "object",
            "required": ["cells_asleep_pct", "call_setup_success", "ambulance_delta_min"],
            "properties": {"cells_asleep_pct": _series, "call_setup_success": _series,
                           "emergency_call_success": _series, "ambulance_delta_min": _series},
        },
        "gap": {
            "type": "object",
            "required": ["gap_id", "type", "title", "global_examples", "readiness_ids", "y3172_nodes", "t"],
            "properties": {
                "gap_id": {"type": "string"},
                "type": {"enum": GAP_TYPES},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "domain": {"type": "string"},
                "trigger": {"type": "string"},
                "global_examples": {"type": "array", "items": {
                    "type": "object", "required": ["label", "cite_id"],
                    "properties": {"label": {"type": "string"}, "cite_id": {"type": "string"},
                                   "how": {"type": "string"}}}},
                "uae_evidence": {"type": "array", "items": {"type": "string"}},
                "absence_queries": {"type": "array", "items": {"type": "string"}},
                "readiness_ids": {"type": "array", "items": {"type": "string"}},
                "y3172_nodes": {"type": "array", "items": {"type": "string"}},
                "recommendation": {"type": "string"},
                "confidence": {"type": "string"},
                "t": {"type": "number"},
            },
        },
        "citation": {
            "type": "object",
            "required": ["doc_id", "title", "article", "page", "quote", "url", "verified"],
            "properties": {
                "doc_id": {"type": "string"}, "chunk_id": {"type": "string"}, "title": {"type": "string"},
                "issuer": {"type": "string"}, "article": {"type": "string"}, "page": {"type": ["integer", "null"]},
                "quote": {"type": "string"}, "url": {"type": "string"}, "verified": {"type": "boolean"},
                "cluster": {"enum": CLUSTERS}, "star_index": {"type": ["integer", "null"]},
            },
        },
        "audit": {"type": "object", "required": ["href", "root"],
                  "properties": {"href": {"type": "string"}, "root": {"type": "string"},
                                 "entries": {"type": "integer"}}},
    },
    "properties": {
        "meta": {
            "type": "object",
            "required": ["run_id", "scenario", "reform", "created_at", "llm", "audit_root", "disclaimer"],
            "properties": {
                "run_id": {"type": "string"}, "scenario": {"type": "string"}, "title": {"type": "string"},
                "reform": {"type": ["string", "null"]}, "created_at": {"type": "string"},
                "llm": {"type": "object", "required": ["provider", "model", "mode"],
                        "properties": {"provider": {"type": "string"}, "model": {"type": "string"},
                                       "mode": {"type": "string"}}},
                "audit_root": {"type": "string"}, "disclaimer": {"type": "string"},
                "label": {"type": "string"}, "clock_origin": {"type": "string"}, "horizon_min": {"type": "number"},
                "mock": {"type": "boolean"}, "quotable": {"type": "string"},
            },
        },
        "agents": {"type": "array", "items": {
            "type": "object", "required": ["id", "name", "name_ar", "role_type", "modelled_on", "color", "mandates"],
            "properties": {
                "id": {"type": "string"}, "name": {"type": "string"}, "name_ar": {"type": "string"},
                "role_type": {"type": "string"}, "modelled_on": {"type": "string"}, "color": {"type": "string"},
                "mandates": {"type": "array", "items": {
                    "type": "object", "required": ["id", "action_types", "citations"],
                    "properties": {"id": {"type": "string"}, "title": {"type": "string"},
                                   "action_types": {"type": "array", "items": {"type": "string"}},
                                   "citations": {"type": "array", "items": {"type": "string"}}}}},
            }}},
        "channels": {"type": "array", "items": {
            "type": "object", "required": ["from", "to", "legal", "citation"],
            "properties": {"from": {"type": "string"}, "to": {"type": "string"}, "legal": {"type": "boolean"},
                           "citation": {"type": ["string", "null"]}, "type": {"type": "string"},
                           "latency_min": {"type": "number"}, "origin": {"enum": ["law", "reform", "missing"]}}}},
        "facts": {"type": "array", "items": {
            "type": "object", "required": ["id", "label", "label_ar"],
            "properties": {"id": {"type": "string"}, "label": {"type": "string"}, "label_ar": {"type": "string"}}}},
        "waves": {"type": "array", "items": {
            "type": "object", "required": ["id", "t", "visible_to", "content"],
            "properties": {"id": {"type": "string"}, "t": {"type": "number"},
                           "visible_to": {"type": "array", "items": {"type": "string"}},
                           "content": {"type": "string"}, "hidden_fact": {"type": "string"}}}},
        "timeline": {"$ref": "#/$defs/timeline"},
        "kpis": {"$ref": "#/$defs/kpis"},
        "gaps": {"type": "array", "items": {"$ref": "#/$defs/gap"}},
        "citations": {"type": "object", "additionalProperties": {"$ref": "#/$defs/citation"}},
        "kb_points": {"type": "object", "required": ["href", "count", "clusters"],
                      "properties": {"href": {"type": "string"}, "count": {"type": "integer"},
                                     "clusters": {"type": "array", "items": {"enum": CLUSTERS}},
                                     "layout": {"type": "string"}}},
        "audit": {"$ref": "#/$defs/audit"},
        "compare": {
            "type": "object", "required": ["baseline_run", "reform_run", "metrics"],
            "properties": {
                "baseline_run": {"type": "string"}, "reform_run": {"type": ["string", "null"]},
                "metrics": {"type": "object"},
                "reform": _run_part,
            },
        },
        "adviser_presets": {"type": "array", "items": {"type": "object"}},
    },
}


def write_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(REPLAY_SCHEMA, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate(replay: dict[str, Any]) -> list[str]:
    import jsonschema

    v = jsonschema.Draft202012Validator(REPLAY_SCHEMA)
    return [f"{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in v.iter_errors(replay)][:50]


# ----------------------------------------------------------------------------
# KPI model (deterministic function of scenario parameters + restoration time)
# ----------------------------------------------------------------------------

def kpi_series(params: dict[str, Any], restored_at: float | None, horizon: int, step: int = 5) -> dict[str, list]:
    k = params["kpi"]
    onset, ramp = k["onset_min"], k["ramp_min"]
    out: dict[str, list] = {"cells_asleep_pct": [], "call_setup_success": [], "emergency_call_success": [],
                            "ambulance_delta_min": []}
    for t in range(-30, horizon + 1, step):
        if t < onset:
            sev = 0.0
        else:
            sev = min(1.0, (t - onset) / ramp)
        if restored_at is not None and t >= restored_at:
            sev = sev * math.exp(-(t - restored_at) / 4.0)  # recovery within ~10 min after restoration
        amb = k["ambulance_delta_peak_min"] * max(0.0, min(1.0, (t - 10) / 30.0)) if t >= 10 else 0.0
        if restored_at is not None and t >= restored_at:
            amb *= math.exp(-(t - restored_at) / 12.0)
        out["cells_asleep_pct"].append([t, round(k["cells_asleep_normal_pct"] + sev * (k["cells_asleep_peak_pct"] - k["cells_asleep_normal_pct"]), 1)])
        out["call_setup_success"].append([t, round(k["call_setup_success_normal_pct"] - sev * (k["call_setup_success_normal_pct"] - k["call_setup_success_floor_pct"]), 1)])
        out["emergency_call_success"].append([t, round(k["emergency_call_success_normal_pct"] - sev * (k["emergency_call_success_normal_pct"] - k["emergency_call_success_floor_pct"]), 1)])
        out["ambulance_delta_min"].append([t, round(amb * (1 if sev > 0 else 0.0) if t >= 10 else 0.0, 1)])
    return out


# ----------------------------------------------------------------------------
# kb_points.bin: Float32 xyz (N*3) followed by uint8 cluster codes (N)
# ----------------------------------------------------------------------------

def write_points(path: Path, xyz: list[tuple[float, float, float]], clusters: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        for x, y, z in xyz:
            fh.write(struct.pack("<fff", x, y, z))
        fh.write(bytes(clusters))


def mock_points(n: int = 6000, seed: int = 7) -> tuple[list[tuple[float, float, float]], list[int]]:
    import random

    rnd = random.Random(seed)
    centers = {0: (-1.2, 0.3, 0.0), 1: (1.1, 0.2, -0.4), 2: (0.0, -0.9, 0.8), 3: (0.1, 1.1, 0.9)}
    weights = [0.18, 0.22, 0.08, 0.52]
    xyz, cl = [], []
    for _ in range(n):
        c = rnd.choices([0, 1, 2, 3], weights)[0]
        cx, cy, cz = centers[c]
        xyz.append((cx + rnd.gauss(0, 0.35), cy + rnd.gauss(0, 0.35), cz + rnd.gauss(0, 0.35)))
        cl.append(c)
    return xyz, cl

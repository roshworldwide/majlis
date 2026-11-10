"""Metadata tagging (PP node): AI Readiness dimensions and Y.3172 nodes.

Keyword rules, deterministic and spot-checkable. Dimension IDs and names are
loaded from the reference dimensions.json (never retyped).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from majlis import config

# keyword stems per Readiness dimension id (1..13)
_DIM_KEYWORDS: dict[int, list[str]] = {
    1: ["dataset", "open data", "data sharing", "data marketplace", "model marketplace", "data exchange"],
    2: ["generative ai", "generative artificial intelligence", "synthetic", "deepfake", "genai", "large language model"],
    3: ["cross-domain", "cross-sector", "interoperab", "cross-border"],
    4: ["regional", "arabic", "local context", "localis", "localiz", "national priorities"],
    5: ["workflow", "automation", "automated", "integration of ai", "operations", "deployment"],
    6: ["human oversight", "human-in-the-loop", "human intervention", "explainab", "transparen", "human review"],
    7: ["strategy", "coordinat", "alignment", "national plan", "governance framework"],
    8: ["collaborat", "partnership", "cooperat", "stakeholder", "information sharing"],
    9: ["emergency", "public safety", "response time", "harm", "crisis", "disaster"],
    10: ["regulat", "legislation", "law", "policy", "sandbox", "compliance", "incident", "audit", "notif", "report"],
    11: ["inclusion", "inclusive", "accessib", "disabilit", "vulnerable", "gender"],
    12: ["priority", "priorities", "healthcare", "telecommunication", "energy sector"],
    13: ["network", "telecommunication", "infrastructure", "5g", "imt-2020", "energy", "data centre", "data center",
         "cloud", "connectivity", "availability", "outage", "resilien"],
}

_Y3172_KEYWORDS: dict[str, list[str]] = {
    "SRC": ["data source", "telemetry", "sensor", "measurement"],
    "C": ["collector", "data collection", "collect data"],
    "PP": ["pre-process", "preprocess", "data cleaning", "data preparation"],
    "M": ["machine learning model", "ml model", "training", "inference", "algorithm"],
    "P": ["policy", "policies", "rule", "constraint"],
    "D": ["distributor", "distribution", "deploy"],
    "SINK": ["sink", "actuat", "configuration change", "apply the output"],
    "MLFO": ["orchestrat", "mlfo", "intent"],
    "ML Sandbox": ["sandbox", "simulat", "testing environment", "validation", "pre-deployment"],
}


@lru_cache(maxsize=1)
def dimensions() -> dict:
    path = config.REF_DIMENSIONS if config.REF_DIMENSIONS.exists() else config.VENDORED_DIMENSIONS
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def metric_index() -> dict[str, dict]:
    out = {}
    for dim in dimensions()["dimensions"]:
        for m in dim["metrics"]:
            out[m["id"]] = {"dimension_id": dim["id"], "dimension": dim["name"], "short_name": dim["short_name"],
                            "name": m["name"], "description": m["description"]}
    return out


def metric_label(mid: str) -> str:
    m = metric_index().get(mid)
    return f"{mid} {m['name']}" if m else mid


def readiness_dims(text: str) -> list[str]:
    low = text.lower()
    hits = []
    for dim in dimensions()["dimensions"]:
        kws = _DIM_KEYWORDS.get(dim["id"], [])
        n = sum(low.count(k) for k in kws)
        if n >= 2:
            hits.append(f"d{dim['id']}")
    return hits


def y3172_nodes(text: str) -> list[str]:
    low = text.lower()
    return [node for node, kws in _Y3172_KEYWORDS.items() if any(re.search(re.escape(k), low) for k in kws)]

"""Central configuration for MAJLIS.

Every path is relative to the repository root so that a fresh clone works
without edits. Environment variables (prefix ``MAJLIS_``) override defaults.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CHROMA_DIR = DATA_DIR / "chroma"
EMB_CACHE_DIR = DATA_DIR / "emb_cache"
KB_DIR = ROOT / "kb"
EXPORT_DIR = KB_DIR / "export"
CHUNKS_PATH = EXPORT_DIR / "chunks.jsonl"
MANIFEST_PATH = EXPORT_DIR / "manifest.csv"
COUNTRIES_DIR = ROOT / "countries"
SCENARIOS_DIR = ROOT / "scenarios"
RUNS_DIR = ROOT / "runs"
RESULTS_DIR = ROOT / "results"
EVAL_DIR = ROOT / "eval"
LLM_CACHE_DIR = Path(os.environ.get("MAJLIS_LLM_CACHE", ROOT / "cache" / "llm"))
DOCS_DIR = ROOT / "docs"
REPORT_DIR = ROOT / "report"

# Reference repository (CrashingGuru/ITUAIReadiness, MIT). Its InputDocs are
# re-ingested into kb_main / kb_usecase and its dimensions.json is the single
# source of truth for AI Readiness dimension and metric IDs.
REF_DIR = Path(os.environ.get("MAJLIS_REF_DIR", ROOT.parent / "_ref" / "ITUAIReadiness"))
REF_SIM = REF_DIR / "simulation"
REF_INPUT_DOCS = REF_SIM / "server" / "knowledge" / "InputDocs"
REF_DIMENSIONS = REF_SIM / "data" / "framework" / "dimensions.json"
# A vendored copy (same file, MIT) so the repo works without the reference clone.
VENDORED_DIMENSIONS = ROOT / "majlis" / "kb" / "dimensions.json"

OLLAMA_BASE_URL = os.environ.get("MAJLIS_OLLAMA_BASE_URL", os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
if not OLLAMA_BASE_URL.startswith("http"):
    OLLAMA_BASE_URL = "http://" + OLLAMA_BASE_URL
LLM_PROVIDER = os.environ.get("MAJLIS_LLM_PROVIDER", "ollama")  # ollama | none
LLM_MODEL = os.environ.get("MAJLIS_LLM_MODEL", "qwen2.5:3b")
# The Policy & Legal Adviser (A7) does the heaviest legal synthesis, so it may run a larger model (role-sized models).
ADVISER_MODEL = os.environ.get("MAJLIS_ADVISER_MODEL", "qwen2.5:7b") or None
EMBED_MODEL = os.environ.get("MAJLIS_EMBED_MODEL", "nomic-embed-text")
LLM_SEED = int(os.environ.get("MAJLIS_LLM_SEED", "42"))

USER_AGENT = "Mozilla/5.0 (compatible; MAJLIS-collector/0.1; research)"

# Knowledge-base collections: the reference names are kept; MAJLIS adds four.
COLLECTIONS = {
    "kb_main": "Reference InputDocs (ITU AI Readiness strategies corpus)",
    "kb_framework": "ITU AI Readiness Framework dimensions.json",
    "kb_usecase": "ITU-T Y.3172 and AI for Good use cases",
    "kb_uae": "UAE national laws, strategies and sector instruments",
    "kb_global_examples": "Foreign and international instruments used as global policy examples",
    "kb_mandates": "Chunks backing countries/<cc>/mandates.yaml",
    "kb_decisions": "Run outputs (gaps, IAPs) written back for retrieval",
}

AS_OF = "10 Nov 2026"
NOT_FOUND = f"not found in the ingested public corpus (as of {AS_OF})"

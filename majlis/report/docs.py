"""Generated documentation (no hand-typed facts): KB datasheet, scenario sheet, Readiness mapping."""

from __future__ import annotations

import collections
import csv
import json
import re
from pathlib import Path
from typing import Any

from majlis import config
from majlis.kb.store import load_chunks
from majlis.kb.tags import dimensions, metric_index
from majlis.scenario.loader import load_reform, load_scenario

# Brief checklist ("make sure that the solution is mapped to ... documents provided by the country").
BRIEF_CATEGORIES = [
    ("Laws and regulations", ["UAE-TELECOM-LAW", "UAE-TDRA-LICENSING-REGS-2008", "UAE-TDRA-LICENSING-REGS-2023", "UAE-CYBERCRIME-2021", "UAE-HEALTH-ICT-2019", "UAE-NCEMA-CDA-2024"]),
    ("National AI, digital and cybersecurity strategies", ["UAE-AI-STRAT-2031", "UAE-AI-CHARTER-2024", "UAE-TDRA-IAR-2020"]),
    ("Data protection and privacy legislation", ["UAE-PDPL-2021"]),
    ("Institutional mandates and responsibilities", ["UAE-TELECOM-LAW", "UAE-NCEMA-CDA-2024", "UAE-PDPL-2021", "UAE-TDRA-IAR-2020"]),
    ("Sector regulation (telecom quality of service)", ["UAE-TDRA-QOS-POLICY-2019"]),
    ("Sector policy (health AI)", ["UAE-DOH-AI-POLICY-2018"]),
    ("Energy and infrastructure constraints", ["UAE-ENERGY-STRAT-2050", "UAE-TDRA-QOS-POLICY-2019"]),
    ("Economic and industrial characteristics", []),
    ("Labour-market conditions", []),
    ("Intellectual property regimes", []),
    ("Multilateral commitments and treaty obligations", []),
]

# Readiness metric → MAJLIS feature → evidence. Names/descriptions come from dimensions.json.
READINESS_MAP = [
    ("d1_m10", "PDPL mapping: personal-data gaps (retraining on location traces, cross-border logs)", "runs/golden/gaps.json (pdata_retraining, offshore_model_logs)"),
    ("d1_m13", "Open-source code (MIT) + open KB export (chunks, manifest, Chroma)", "LICENSE, kb/export/"),
    ("d2_m04", "Rumour scenario (false cyber-attack attribution) and rebuttal-mandate gap", "scenario W3; gap rumour_mandate"),
    ("d3_m01", "Cross-domain workflow: telecom → emergency → health → public trust in one run", "runs/golden/timeline.json"),
    ("d4_m02", "UAE national layer: kb_uae, mandates.yaml, Arabic labels; adding a country = adding a folder", "countries/uae/, countries/_template/"),
    ("d5_m01", "Automation level of network AI (ML energy-saving) under P-node control", "scenario W0; gate verdicts"),
    ("d6_m02", "Local language: bilingual EN/AR agent and fact labels in the Experience", "scenario YAML name_ar/label_ar; web/"),
    ("d6_m06", "Human supervision: every action passes the P node; facilitator console (majlis play)", "majlis/gate/, majlis/coord/play.py"),
    ("d7_m01", "Coordination level: messages only along cited legal channels; missing channels measured", "metrics.coordination_messages / missing_channels"),
    ("d8_m06", "Incident Action Plans produced per run", "runs/golden/iap.json (metrics.iap_count)"),
    ("d9_m08", "Action latency: time-to-awareness per agent and fact", "metrics.time_to_awareness"),
    ("d10_m01", "Policy sandbox: the simulator itself (ML Sandbox role)", "majlis run"),
    ("d10_m03", "Policy extrapolation: replay with the reform pack RF1–RF3", "runs/reform/, results/numbers.json deltas"),
    ("d10_m08", "Policy case briefs: typed gap register with global examples and recommendations", "runs/golden/gaps.json"),
    ("d10_m09", "Audit metrics: SHA-256 hash-chained audit log, gate ablation", "majlis verify; results/numbers.json ablation"),
    ("d11_m13", "Social inclusion impact: emergency access for the public during a mass event", "KPI emergency_call_success"),
    ("d13_m07", "Uptime: service restoration time and degraded minutes (scenario KPI model)", "metrics.service_restored_min"),
    ("d13_m06", "Energy sustainability vs availability conflict (G4) and safe-mode reform (RF2)", "gap energy_vs_availability"),
]

PERSPECTIVES = [
    ("Open data and open-source management", ["d1_m13"]),
    ("Generative AI content ecosystem", ["d2_m04"]),
    ("Contextualisation and regional focus", ["d4_m02", "d6_m02"]),
    ("AI integration in domains and cross-domain analysis", ["d3_m01", "d5_m01"]),
    ("Human interaction and supervision", ["d6_m06", "d8_m06"]),
    ("Policy / implementation opportunity identification", ["d10_m01", "d10_m03", "d10_m08"]),
    ("AI for social inclusion", ["d11_m13"]),
    ("Digital infrastructure and energy", ["d13_m07", "d13_m06"]),
]


def _skips(path: Path) -> str:
    txt = path.read_text(encoding="utf-8") if path.exists() else ""
    m = re.search(r"^# SKIPPED:.*", txt, re.M | re.S)
    if not m:
        return "_none logged_"
    return "\n".join(l[2:] if l.startswith("# ") else l.lstrip("#") for l in m.group(0).splitlines())


def write_datasheet() -> Path:
    rows = list(csv.DictReader((config.EXPORT_DIR / "manifest.csv").open(encoding="utf-8")))
    chunks = load_chunks()
    per_doc = collections.Counter(c["doc_id"] for c in chunks)
    ocr = collections.Counter(c["doc_id"] for c in chunks if c.get("ocr"))
    by_col = collections.Counter(c["collection"] for c in chunks)
    ev = json.loads((config.RESULTS_DIR / "kb_eval.json").read_text()) if (config.RESULTS_DIR / "kb_eval.json").exists() else None
    L = ["# MAJLIS knowledge base — datasheet", "",
         f"_Generated from `kb/export/manifest.csv` and `kb/export/chunks.jsonl` (as of {config.AS_OF}). Do not edit by hand._", "",
         "## Scope", "",
         "A vectorised, citable knowledge base for **AI-driven operation of critical telecom networks**, built with the ITU reference approach "
         "(CrashingGuru/ITUAIReadiness: extract → structure → ingest into ChromaDB with `document_category` tags) and extended with "
         "legal-structure-aware chunking, page/article metadata, SHA-256 provenance and three new collections.", "",
         "| Collection | Purpose | Chunks |", "|---|---|---|"]
    for col, purpose in config.COLLECTIONS.items():
        L.append(f"| `{col}` | {purpose} | {by_col.get(col, 0)} |")
    L += ["", f"Total chunks: **{len(chunks)}**. Chunks with OCR text (tesseract, scanned TDRA PDFs): **{sum(ocr.values())}**.", ""]
    for title, col in (("UAE national layer (`kb_uae`)", "kb_uae"), ("Global examples (`kb_global_examples`)", "kb_global_examples"),
                       ("ITU standards (`kb_usecase`, added)", "kb_usecase")):
        sel = [r for r in rows if r["collection"] == col and r["status"] != "reference"]
        if not sel:
            continue
        L += [f"## {title}", "", "| doc_id | title | issuer | date | chunks | SHA-256 | licence / terms | source |", "|---|---|---|---|---|---|---|---|"]
        for r in sel:
            src = f"[official]({r['url']})" + (" · [fetched copy]({})".format(r["fetch_url"]) if r.get("fetch_url") and r["fetch_url"] != r["url"] else "")
            L.append(f"| `{r['doc_id']}` | {r['title'][:90]} | {r['issuer'][:40]} | {r['date']} | {per_doc.get(r['doc_id'], 0)}"
                     f"{' (OCR)' if ocr.get(r['doc_id']) else ''} | `{r['sha256'][:12]}…` | {r['license_note'][:80]} | {src} |")
        L.append("")
    ref = [r for r in rows if r["status"] == "reference"]
    L += ["## Reference corpus (`kb_main`, `kb_usecase`)", "",
          f"All {len(ref)} InputDocs of the ITU reference repository are re-ingested unchanged (compatibility with the reference server). "
          "They are registered in the manifest with their GitHub path and SHA-256; they are not re-distributed by MAJLIS.", "",
          "## Coverage against the brief's checklist (UAE)", "", "| Category (brief wording) | Documents in the KB | Status |", "|---|---|---|"]
    have = {r["doc_id"] for r in rows if r.get("sha256")}
    for cat, docs in BRIEF_CATEGORIES:
        present = [d for d in docs if d in have]
        status = "covered" if present else f"**gap** — {config.NOT_FOUND}"
        L.append(f"| {cat} | {', '.join(f'`{d}`' for d in present) or '—'} | {status} |")
    L += ["", "## Documents sought but not ingested (logged by the collectors, never substituted)", "", "### UAE", "", "```",
          _skips(config.COUNTRIES_DIR / "uae" / "sources.yaml"), "```", "", "### Global", "", "```",
          _skips(config.COUNTRIES_DIR / "_global" / "sources.yaml"), "```", ""]
    if ev:
        L += ["## Retrieval quality", "", f"{ev['n_questions']} questions with gold document and article (`eval/kb_questions.jsonl`).", "",
              "| retriever | hit@1 | hit@3 | hit@5 | MRR |", "|---|---|---|---|---|"]
        for n, r in ev["retrievers"].items():
            L.append(f"| {n} | {r['hit@1']} | {r['hit@3']} | {r['hit@5']} | {r['mrr']} |")
        L += ["", "Caveat: the questions were written by the builder with knowledge of the corpus, so these are optimistic estimates.", ""]
    L += ["## Chunk record (`chunks.jsonl`)", "",
          "`chunk_id, doc_id, collection, text (verbatim), title, issuer, country, doc_type, document_category, date, url, retrieved_at, sha256, "
          "page, page_end, section, article, articles[], readiness_dims[], y3172_nodes[], license_note, n_words, ocr`", "",
          "## Quality controls", "",
          "- Legal texts are split at Article / Section / § / Annex boundaries; an article that fits in 600 words is never split.",
          "- Running headers, footers and page numbers are stripped for MAJLIS-collected PDFs so quotes are not broken by page furniture.",
          "- Every quote used by an agent, mandate, channel, gap or reform rule is verified verbatim against `chunks.jsonl` (gate rule G1).",
          "- OCR text is flagged `ocr: true`; quotes from OCR chunks should be re-checked against the page image.",
          "- Personal e-mail addresses of individuals that appear in third-party documents (e.g. use-case contact persons) are "
          "replaced by `[personal e-mail redacted]`; institutional addresses are kept.",
          "- 100% of cited quotes are re-checked against the original files with independent extractors "
          "(`scripts/spot_check_quotes.py` → `results/quote_spot_check.json`).", "",
          "## Update procedure (adding or refreshing documents / countries)", "",
          "1. Add a row to `countries/<cc>/sources.yaml` (official URL, honest-UA fetch URL, licence note).",
          "2. `majlis collect` → downloads, SHA-256, manifest. 3. `majlis ingest` → chunks, embeddings, ChromaDB.",
          "4. `majlis kb-eval` → regression check. 5. Re-validate `mandates.yaml` (rejected entries are reported at load).",
          "6. A new country = a new `countries/<cc>/` folder (copy `countries/_template/`).", "",
          "## Licences", "",
          "Raw documents are not committed. The export ships metadata, chunk text and URLs. EU texts: Commission Decision 2011/833/EU reuse; "
          "UK: Open Government Licence v3.0; US federal: public domain; ITU: free download, ITU copyright; UAE and other official "
          "documents: public access, redistribution terms not stated (metadata + chunks + URL only)."]
    text = "\n".join(L) + "\n"
    for p in (config.EXPORT_DIR / "kb_datasheet.md", config.DOCS_DIR / "kb_datasheet.md"):
        p.write_text(text, encoding="utf-8")
    return config.DOCS_DIR / "kb_datasheet.md"


def write_scenario_doc() -> Path:
    sc = load_scenario("uae_nye_cells")
    rf = load_reform("uae_reform_pack")
    L = [f"# Scenario — “{sc.title}”", "", f"**{sc.label}**", "", f"Domain: {sc.domain}. Clock origin: {sc.raw.get('clock_origin', '')}. Horizon: {sc.horizon} simulated minutes.", "",
         "## Agents", "", "| ID | Agent | Brief role | Modelled on |", "|---|---|---|---|"]
    for aid, a in sc.agents.items():
        L.append(f"| {aid} | {a['name']} ({a['name_ar']}) | {a['role_type']} | {a['modelled_on']} |")
    L += ["", "## Waves (sequenced, chunked, uneven visibility)", "", "| Wave | Sim time | Released to | Content | Fact | Condition |", "|---|---|---|---|---|---|"]
    for w in sc.waves:
        L.append(f"| {w.id} | T+{w.t} | {', '.join(w.visible_to)} | {w.content} | {w.hidden_fact or '—'} | {w.condition or '—'} |")
    L += ["", "Condition `degraded`: the inject is only released if service has not been restored by then (otherwise it is logged as suppressed).", "",
          "## Facts", ""] + [f"- `{k}` — {v['label']}" for k, v in sc.facts.items()]
    L += ["", "## Scenario parameters (not real-world values)", "", "```yaml", json.dumps(sc.params, indent=1), "```", "",
          "## Playbook (exercise SOPs; options are deterministic, the gate decides legality)", "", "| Rule | Agent | When | Action |", "|---|---|---|---|"]
    for r in sc.playbook:
        cond = ", ".join(f"{k}={v}" for k, v in (("knows", r.knows), ("knows_any", r.knows_any), ("not_knows", r.not_knows),
                                                   ("min_conf", r.min_conf), ("reform", r.reform), ("no_reform", r.no_reform)) if v)
        L.append(f"| {r.id} | {r.agent} | {cond} | `{r.action['type']}`{' → ' + r.action['target'] if r.action.get('target') else ''} |")
    L += ["", "## Adviser questions asked during the run", ""] + [f"- {q['id']} ({q['wave']}, as {q['as']}): {q['question']}" for q in sc.adviser_questions]
    L += ["", "## Expected outcomes (written before running)", ""]
    for k, v in sc.expected.items():
        L += [f"**{k}**", ""] + [f"- {x}" for x in v] + [""]
    L += ["## Reform pack (design proposal, not law)", ""]
    for r in rf["rules"]:
        L += [f"### {r['id']} — {r['title']}", "", r["summary"].strip(), "", f"_Design parameter:_ {r['design_parameter']}", "", "Global basis (verified quotes):", ""]
        L += [f"- {b['doc_id']} {b['article']}: “{b['quote']}”" for b in r["global_basis"]] + [""]
    p = config.DOCS_DIR / "scenario.md"
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


def write_readiness_doc() -> Path:
    mi = metric_index()
    L = ["# ITU AI Readiness Framework mapping", "", "_Dimension and metric names are loaded from the reference `dimensions.json` (not retyped)._", "",
         "## The brief's eight perspectives", "", "| Perspective (brief) | Metrics | MAJLIS feature |", "|---|---|---|"]
    feat = {m: f for m, f, _ in READINESS_MAP}
    for name, ids in PERSPECTIVES:
        labs = ", ".join("`%s` %s" % (i, mi[i]["name"]) for i in ids)
        L.append(f"| {name} | {labs} | {'; '.join(feat[i] for i in ids)} |")
    L += ["", "## All 13 dimensions", "", "| Dimension | Metric touched | MAJLIS feature | Evidence |", "|---|---|---|---|"]
    by_dim: dict[int, list] = collections.defaultdict(list)
    for m, f, e in READINESS_MAP:
        by_dim[mi[m]["dimension_id"]].append((m, f, e))
    for dim in dimensions()["dimensions"]:
        rows = by_dim.get(dim["id"], [])
        if not rows:
            L.append(f"| D{dim['id']} {dim['name']} | — | not exercised by this scenario | — |")
        for m, f, e in rows:
            L.append("| D%s %s | `%s` %s | %s | %s |" % (dim["id"], dim["name"], m, mi[m]["name"], f, e))
    p = config.DOCS_DIR / "readiness_mapping.md"
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p

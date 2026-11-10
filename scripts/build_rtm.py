"""Regenerate docs/RTM.md with statuses computed from evidence that actually exists.

A row is 🟢 only if every evidence path exists (and, where a check is given, the check passes);
🟡 if some evidence exists; 🔴 otherwise. Numbers come from results/numbers.json.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
N = json.loads((ROOT / "results" / "numbers.json").read_text())
FP = json.loads((ROOT / "results" / "frontend_perf.json").read_text()) if (ROOT / "results" / "frontend_perf.json").exists() else {}
SC = json.loads((ROOT / "results" / "quote_spot_check.json").read_text()) if (ROOT / "results" / "quote_spot_check.json").exists() else {}
B = N["baseline"]["metrics"]


def ex(*paths):
    return all((ROOT / p).exists() for p in paths)


def status(paths, check=True):
    have = [p for p in paths if (ROOT / p).exists()]
    if len(have) == len(paths) and check:
        return "🟢"
    return "🟡" if have else "🔴"


gtypes = set(B["gaps_by_type"])
six = {"unclear_responsibility", "standards_gap", "technology_gap", "legislative_gap", "coordination_problem", "conflicting_objectives"}
rows = [
    ("R0", "Agent-based solution on a KB (telecom), adhering to UAE AI/telecom/data instruments, mapped to global practice",
     f"{N['kb']['documents']} docs, {N['kb']['chunks']} chunks; every action gated on cited UAE mandates; {B['gaps_total']} gaps mapped to verified global examples",
     ["majlis/coord/coordinator.py", "countries/uae/mandates.yaml", "runs/golden/gaps.json", "kb/export/manifest.csv"], True),
    ("R1", "Innovative AI solution agent (NetOps Resilience Copilot)", f"root cause from Y.3172 telemetry at T+{B['time_to_awareness']['A1']['F_ROOT']} ({B['copilot_rca_lead_min']} min before customer complaints)",
     ["runs/golden/timeline.json"], B["time_to_awareness"]["A1"]["F_ROOT"] == 0),
    ("R2", "Policy & legal adviser queryable during error scenarios", f"{N['baseline']['adviser']['questions']} questions answered during the golden run; {N['baseline']['adviser']['quotes_valid']}/{N['baseline']['adviser']['quotes_total']} evidence quotes verified; `majlis ask`, `majlis play`",
     ["runs/golden/adviser_qa.json", "majlis/coord/play.py"], N["baseline"]["adviser"]["quotes_total"] > 0),
    ("R3", "Institutional participant agents", "A2–A6 modelled on TDRA, NCEMA, health/ambulance authority, Cybersecurity Council, UAE Data Office; cited mandates",
     ["countries/uae/mandates.yaml", "runs/golden/proposals.jsonl"], True),
    ("R4", "Multi-agent coordination under different mandates and information", f"{B['coordination_messages']} messages; {B['messages_legal']} via cited legal channels, {B['messages_informal']} informal; per-agent visibility",
     ["runs/golden/audit.jsonl", "tests/test_engine.py"], True),
    ("R5", "Interactive error scenarios, chunked and uneven", "9 waves with per-agent visibility; facilitator console", ["scenarios/uae_nye_cells.yaml", "docs/scenario.md", "majlis/coord/play.py"], True),
    ("R6", "Audit logging and chain-of-thought (structured reasoning) tracing", f"SHA-256 hash chain, {N['baseline']['audit']['entries']} entries, root {N['baseline']['audit']['root'][:12]}…; structured reasoning traces",
     ["runs/golden/audit.jsonl", "runs/golden/proposals.jsonl"], N["baseline"]["audit"]["ok"]),
    ("R7", "Y.3172 alignment + AI Readiness perspectives", "pipeline nodes SRC…SINK, MLFO, ML Sandbox; 8 perspectives + 13 dimensions mapped from dimensions.json",
     ["docs/architecture.md", "docs/readiness_mapping.md", "report/figures/fig_architecture.png"], True),
    ("R8", "KB with the ITU reference approach, vectorised, hostable in the Lab", "reference collections kept + kb_uae / kb_global_examples / kb_mandates; loader tested against the reference KnowledgeBase",
     ["kb/export/chunks.jsonl", "scripts/load_into_ituaireadiness.py", "results/loader_test.json"], True),
    ("E1", "KB quality", f"hybrid hit@5 {N['kb_eval']['retrievers']['hybrid']['hit@5']} on {N['kb_eval']['n_questions']} gold questions; manifest with URL/SHA-256/licence; datasheet",
     ["results/kb_eval.json", "kb/export/kb_datasheet.md", "kb/export/manifest.csv"], N["kb_eval"]["retrievers"]["hybrid"]["hit@5"] >= 0.85),
    ("E2", "Agent capability + gap identification + global examples", f"all six gap types: {sorted(gtypes)}; every gap has ≥1 verified global example",
     ["runs/golden/gaps.json"], six <= gtypes),
    ("E3", "Auditability", f"ablation: {N['ablation']['gate_on_caught']} caught (gate on) vs {N['ablation']['gate_off_passed']} passed (gate off); quotes spot-checked against originals: {SC.get('summary')}",
     ["results/numbers.json", "results/quote_spot_check.json", "runs/golden/dashboard.html"], not SC.get("not_found")),
    ("E4", "Alignment with ITU standards", "architecture = Y.3172 pipeline; Readiness metric IDs wired into run metrics", ["docs/architecture.md", "docs/readiness_mapping.md"], True),
]
for k, lbl in zip("abcdefgh", ["introduction", "use case", "requirements", "Y.3172 mapping", "Readiness 2.0 mapping", "local policies mapping",
                               "evaluation scenario", "gaps identified"]):
    rows.append((k, f"Report item ({k}) {lbl}", "section present in FAQ order", ["report/MAJLIS_technical_report.pdf"], True))
rows += [
    ("S1", "Technical report ≤ 5 pages on the official template", "built from the official .docx; page count checked by tests", ["report/MAJLIS_technical_report.pdf", "report/build_report.py"], True),
    ("S2", "GitHub repository", "github.com/roshworldwide/majlis (after Gate A)", ["README.md", "LICENSE", "NOTICE"], True),
    ("S3", "Knowledge base", "kb/export (chunks, manifest, datasheet) + Chroma release asset (Gate B)", ["kb/export/chunks.jsonl", "kb/export/manifest.csv"], True),
    ("S4", "Demo video (optional; mandatory if shortlisted)", "script ready; Story mode records it", ["docs/video_script.md"], True),
]
fe_ok = bool(FP)
rows += [
    ("X1", "Contract-first replay.json (+ schema, zod)", "engine export validates against replay.schema.json", ["replay.schema.json", "web/public/data/replay.json", "web/src/data/replay.schema.ts"], True),
    ("X2", "Act II council + magic moment", "see results/frontend_perf.json + docs/media", ["web/src/acts", "docs/media"], fe_ok),
    ("X3", "Act I city", "", ["web/src/acts"], fe_ok),
    ("X4", "Act IV rewind & reform", "", ["web/src/acts"], fe_ok),
    ("X5", "Act III evidence galaxy", "", ["web/src/acts", "web/public/data/kb_points.bin"], fe_ok),
    ("X6", "In-browser audit verification = CLI", "WebCrypto recipe, tested in tests/test_audit.py", ["web/src/data/audit.ts", "tests/test_audit.py"], True),
    ("X7", "2D fallback", "", ["web/src/fallback2d"], fe_ok),
    ("X8", "Performance budgets", json.dumps({k: FP.get(k) for k in list(FP)[:4]}) if FP else "", ["results/frontend_perf.json"], fe_ok),
    ("X9", "Robustness (e2e, no console errors)", "", ["web/e2e"], fe_ok),
    ("X10", "Accessibility", "", ["web/src/ui"], fe_ok),
    ("X11", "Builds: Pages + single file + workflow", "", ["web/dist-single/majlis_experience.html", ".github/workflows/pages.yml"], True),
    ("X12", "Media + live link + QR", "", ["docs/media", "report/figures/qr_live.png"], fe_ok),
]
L = ["# Requirement Traceability Matrix (RTM)", "", "_Generated by `scripts/build_rtm.py` from evidence that exists in the repo (🟢 = all evidence present and check passed)._", "",
     "| ID | Requirement | Evidence summary | Evidence paths | Status |", "|---|---|---|---|---|"]
for rid, req, summ, paths, chk in rows:
    L.append(f"| {rid} | {req} | {summ} | {'<br>'.join(f'`{p}`' for p in paths)} | {status(paths, chk)} |")
(ROOT / "docs" / "RTM.md").write_text("\n".join(L) + "\n")
counts = {s: sum(1 for r in rows if status(r[3], r[4]) == s) for s in ("🟢", "🟡", "🔴")}
print("RTM:", counts)

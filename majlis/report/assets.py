"""report-assets: results/numbers.json + figures. Nothing in the report or README is typed by hand.

numbers.json aggregates: KB composition, KB evaluation, the golden (baseline),
reform and no-gate ablation runs, determinism (replay root hashes), live-vs-replay
drift, gaps, adviser Q&A checks and gate statistics.
"""

from __future__ import annotations

import collections
import csv
import json
from pathlib import Path
from typing import Any

from majlis import config
from majlis.audit.chain import verify
from majlis.kb.store import load_chunks

INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
S1, S2 = "#2a78d6", "#eb6834"  # validated categorical slots 1-2 (dataviz reference palette)
LIVE_URL = "https://roshworldwide.github.io/majlis/"


def _run(name: str) -> dict[str, Any] | None:
    d = config.RUNS_DIR / name
    if not (d / "metrics.json").exists():
        return None
    out = {k: json.loads((d / f"{k}.json").read_text()) for k in ("metrics", "meta", "gaps", "adviser_qa", "gate")}
    ok, n, root, _ = verify(d / "audit.jsonl")
    out["audit"] = {"ok": ok, "entries": n, "root": root}
    return out


def _drift(a: str, b: str) -> dict[str, Any] | None:
    """Live-vs-replay drift: structural outcomes (who knew what when, blocks, gaps, restoration) vs LLM text."""
    da, db = config.RUNS_DIR / a, config.RUNS_DIR / b
    if not ((da / "timeline.json").exists() and (db / "timeline.json").exists()):
        return None
    ta, tb = json.loads((da / "timeline.json").read_text()), json.loads((db / "timeline.json").read_text())
    ma, mb = json.loads((da / "metrics.json").read_text()), json.loads((db / "metrics.json").read_text())
    ga, gb = json.loads((da / "gaps.json").read_text()), json.loads((db / "gaps.json").read_text())

    def struct(tl):
        keep = ("inject", "belief", "message", "gate_block", "gate_flag", "action", "kpi", "gap")
        out = collections.Counter()
        for e in tl:
            if e["type"] in keep:
                p = e["payload"]
                if e["type"] == "gate_block" and p.get("kind") == "claim":
                    continue  # quote/claim checks depend on LLM text
                out[(e["t"], e["type"], e["agent"], p.get("fact"), p.get("rule"), p.get("action_type") or p.get("type"),
                     p.get("to"), p.get("deliver_t"))] += 1
        return out

    sa, sb = struct(ta), struct(tb)
    keys = ["time_to_awareness", "blocked_actions", "rerouted_messages", "conflicting_actions", "gaps_by_type",
            "service_restored_min", "awareness_convergence_min", "missing_channel_pairs"]
    return {"structural_events_a": sum(sa.values()), "structural_events_b": sum(sb.values()),
            "structural_differences": sum(((sa - sb) + (sb - sa)).values()),
            "outcome_metrics_identical": all(ma.get(k) == mb.get(k) for k in keys),
            "gaps_identical": [g["key"] for g in ga] == [g["key"] for g in gb],
            "citation_coverage": [ma.get("citation_coverage"), mb.get("citation_coverage")],
            "invalid_quotes": [ma.get("invalid_quotes"), mb.get("invalid_quotes")],
            "note": "structural = facts, messages, blocks, actions, KPIs, gaps; LLM prose is expected to differ"}


def build_numbers() -> dict[str, Any]:
    chunks = load_chunks()
    manifest = list(csv.DictReader((config.EXPORT_DIR / "manifest.csv").open(encoding="utf-8")))
    docs_by_col = collections.Counter(r["collection"] for r in manifest if r.get("sha256"))
    chunks_by_col = collections.Counter(c["collection"] for c in chunks)
    n_ocr = sum(1 for c in chunks if c.get("ocr"))
    kb_eval = json.loads((config.RESULTS_DIR / "kb_eval.json").read_text()) if (config.RESULTS_DIR / "kb_eval.json").exists() else None
    runs = {n: _run(n) for n in ("golden", "reform", "nogate", "golden_replay2", "golden_replay3", "golden_live", "reform_live", "nogate_live")}
    g, r, ng = runs["golden"], runs["reform"], runs["nogate"]
    roots = {n: (runs[n]["audit"]["root"] if runs[n] else None) for n in ("golden", "golden_replay2", "golden_replay3")}
    nums: dict[str, Any] = {
        "as_of": config.AS_OF,
        "kb": {"documents": sum(docs_by_col.values()), "documents_by_collection": dict(docs_by_col),
               "uae_documents": docs_by_col.get("kb_uae", 0), "global_documents": docs_by_col.get("kb_global_examples", 0),
               "itu_documents": sum(1 for x in manifest if x.get("document_category") == "ITU_Standards" and x.get("sha256")),
               "reference_documents": sum(1 for x in manifest if x.get("status") == "reference"),
               "chunks": len(chunks), "chunks_by_collection": dict(chunks_by_col), "ocr_chunks": n_ocr,
               "mandates": sum(1 for c in chunks if c["collection"] == "kb_mandates")},
        "kb_eval": kb_eval and {k: v for k, v in kb_eval.items() if k != "per_question"},
        "determinism": {"replay_roots": roots, "identical": len({v for v in roots.values() if v}) == 1 and all(roots.values()),
                        "fresh_live_vs_golden": _drift("golden_fresh_live", "golden")},
    }
    for name, run in (("baseline", g), ("reform", r), ("nogate", ng)):
        if not run:
            continue
        m = run["metrics"]
        nums[name] = {"metrics": m, "audit": run["audit"], "llm": run["meta"]["llm"], "llm_stats": run["meta"]["llm_stats"],
                      "gate_stats": run["gate"]["stats"],
                      "gaps": [{"gap_id": x["gap_id"], "type": x["type"], "title": x["title"],
                                "examples": [e.get("label") for e in x["global_examples"]],
                                "confidence": x["confidence"]["level"]} for x in run["gaps"]],
                      "adviser": {"questions": len(run["adviser_qa"]),
                                  "quotes_total": sum(len(q["uae_basis"]) + len(q["global_examples"]) for q in run["adviser_qa"]),
                                  "quotes_valid": sum(1 for q in run["adviser_qa"] for p in ("uae_basis", "global_examples") for i in q[p] if i.get("valid"))}}
    if g and r:
        tb, tr = g["metrics"]["time_to_awareness"], r["metrics"]["time_to_awareness"]
        nums["deltas"] = {
            "A4_F_ROOT": [tb["A4"]["F_ROOT"], tr["A4"]["F_ROOT"]], "A3_F_ROOT": [tb["A3"]["F_ROOT"], tr["A3"]["F_ROOT"]],
            "A5_F_ROOT": [tb["A5"]["F_ROOT"], tr["A5"]["F_ROOT"]], "A2_F_ROOT": [tb["A2"]["F_ROOT"], tr["A2"]["F_ROOT"]],
            "root_cause_convergence_min": [g["metrics"]["awareness_convergence_min"], r["metrics"]["awareness_convergence_min"]],
            "service_restored_min": [g["metrics"]["service_restored_min"], r["metrics"]["service_restored_min"]],
            "degraded_minutes": [g["metrics"]["degraded_minutes"], r["metrics"]["degraded_minutes"]],
            "blocked_actions": [g["metrics"]["blocked_actions"], r["metrics"]["blocked_actions"]],
            "conflicting_actions": [g["metrics"]["conflicting_actions"], r["metrics"]["conflicting_actions"]],
            "missing_channels": [g["metrics"]["missing_channels"], r["metrics"]["missing_channels"]],
            "gaps_total": [g["metrics"]["gaps_total"], r["metrics"]["gaps_total"]],
        }
    if g and ng:
        nums["ablation"] = {"gate_on_caught": g["metrics"]["unsupported_claims_caught"],
                            "gate_off_passed": ng["metrics"]["unsupported_claims_passed"],
                            "gate_off_out_of_mandate_actions_executed": ng["metrics"]["would_block_actions_if_gate_on"],
                            "gate_on_blocked_actions": g["metrics"]["blocked_actions"],
                            "gate_off_lead_conflicts": ng["metrics"]["conflicting_actions"],
                            "gate_on_citation_coverage": g["metrics"]["citation_coverage"],
                            "gate_off_citation_coverage": ng["metrics"]["citation_coverage"]}
    if g and r:
        gb, gr = g["metrics"], r["metrics"]
        keys_b = {x["key"] for x in g["gaps"]}
        keys_r = {x["key"] for x in r["gaps"]}
        tb, tr = gb["time_to_awareness"], gr["time_to_awareness"]
        checks = [
            ("baseline", "A1 identifies the ML model as root cause before customer complaints (copilot RCA)", tb["A1"]["F_ROOT"] is not None and tb["A1"]["F_ROOT"] < 15),
            ("baseline", "A4 learns the root cause late or never: no legal operator-to-emergency-service channel",
             (tb["A4"]["F_ROOT"] is None or tb["A4"]["F_ROOT"] >= 30) and "A1→A4" in gb["missing_channel_pairs"]),
            ("baseline", "At least one action is blocked by the P node for lack of a citable mandate", gb["blocked_actions"] >= 1),
            ("baseline", "Energy-efficiency vs availability conflict is flagged", "energy_vs_availability" in keys_b),
            ("baseline", "Lead authority contested or unclear", "incident_lead" in keys_b),
            ("reform", "Flash notice (RF1) delivers the root cause to A2, A3, A4, A5 within minutes",
             all(tr[a]["F_ROOT"] is not None and tr[a]["F_ROOT"] <= 10 for a in ("A2", "A3", "A4", "A5"))),
            ("reform", "Mass-event safe-mode (RF2) restores service without waiting for the vendor",
             gr["service_restored_min"] is not None and gr["service_restored_min"] <= 10),
            ("reform", "Local rollback artefact (RF3) removes the offshore dependency", "offshore_model_logs" not in keys_r),
            ("reform", "Lead ambiguity remains (not addressed by RF1-RF3)", "incident_lead" in keys_r),
        ]
        nums["expected_vs_actual"] = {"held": sum(1 for *_, ok in checks if ok), "total": len(checks),
                                      "items": [{"run": run, "expected": e, "held": bool(ok)} for run, e, ok in checks]}
    fp = config.RESULTS_DIR / "frontend_perf.json"
    if fp.exists():
        nums["frontend"] = json.loads(fp.read_text())
    nums["live_url"] = LIVE_URL
    return nums


def _style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8, length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fig_awareness(nums: dict[str, Any], out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tb = nums["baseline"]["metrics"]["time_to_awareness"]
    tr = nums["reform"]["metrics"]["time_to_awareness"]
    rows = [("A2", "F_ROOT"), ("A3", "F_ROOT"), ("A4", "F_ROOT"), ("A5", "F_ROOT")]
    names = {"A1": "Operator copilot", "A2": "Telecom regulator", "A3": "Crisis authority", "A4": "Ambulance service", "A5": "Cyber authority"}
    labels = [f"{names[a]} learns the root cause" for a, f in rows]
    H = 90
    fig, ax = plt.subplots(figsize=(6.6, 2.0), dpi=220)
    fig.patch.set_facecolor(SURF)
    _style(ax)
    y = range(len(rows))
    for i, (a, f) in enumerate(rows):
        for off, val, col in ((-0.19, tb[a].get(f), S1), (0.19, tr[a].get(f), S2)):
            v = H if val is None else val
            ax.barh(i + off, max(v, 0.6), height=0.34, color=col, hatch="////" if val is None else None,
                    edgecolor=SURF if val is not None else col, linewidth=0.0 if val is not None else 0.6, fill=val is not None)
            ax.text(v + 1.2, i + off, "never" if val is None else f"T+{val}", va="center", fontsize=7, color=INK)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=8, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, H + 12)
    ax.set_xlabel("simulated minutes after T+0 (scenario parameters; not predictions)", fontsize=7.5, color=INK2)
    from matplotlib.patches import Patch

    ax.legend(handles=[Patch(color=S1, label="baseline (current corpus)"), Patch(color=S2, label="reform pack RF1–RF3")],
              loc="lower right", fontsize=7, frameon=False)
    ax.set_title("When each authority learns the root cause", fontsize=9, color=INK, loc="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(out, facecolor=SURF)
    plt.close(fig)


def fig_kpi(out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    kb = json.loads((config.RUNS_DIR / "golden" / "kpis.json").read_text())
    kr = json.loads((config.RUNS_DIR / "reform" / "kpis.json").read_text())
    fig, ax = plt.subplots(figsize=(3.3, 2.3), dpi=220)
    fig.patch.set_facecolor(SURF)
    _style(ax)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.grid(axis="x", visible=False)
    for series, col, lab in ((kb, S1, "baseline"), (kr, S2, "reform")):
        xs = [p[0] for p in series["emergency_call_success"]]
        ys = [p[1] for p in series["emergency_call_success"]]
        ax.plot(xs, ys, color=col, linewidth=2)
        ax.text(xs[-1] + 1, ys[-1], lab, fontsize=7, color=INK, va="center")
    ax.set_xlim(-30, 104)
    ax.set_ylabel("emergency-call success, %", fontsize=7.5, color=INK2)
    ax.set_xlabel("simulated minutes (illustrative KPI model)", fontsize=7.5, color=INK2)
    ax.set_title("Emergency access (scenario KPI)", fontsize=9, color=INK, loc="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(out, facecolor=SURF)
    plt.close(fig)


def fig_architecture(out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig, ax = plt.subplots(figsize=(6.6, 1.9), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 30)
    ax.axis("off")
    nodes = [("SRC", "UAE + global + ITU\nsources; scenario\ntelemetry & injects"), ("C", "collect.py\n(manifest, SHA-256)\nscenario loader"),
             ("PP", "legal-structure\nchunking, tags,\nBM25 + nomic"), ("M", "LLM agents\nA1–A7 (qwen2.5:3b)\n+ hybrid retrieval"),
             ("P", "Mandate &\nCitation Gate\nG1–G5"), ("D", "router: legal\nchannels only,\nlatency"),
             ("SINK", "gaps, IAPs,\naudit chain,\ndashboard")]
    w, gap, x0 = 12.2, 2.0, 1.0
    for i, (n, d) in enumerate(nodes):
        x = x0 + i * (w + gap)
        hot = n == "P"
        ax.add_patch(FancyBboxPatch((x, 8), w, 15, boxstyle="round,pad=0.25,rounding_size=1.2",
                                    facecolor="#fde8e1" if hot else "#eef4fc", edgecolor=S2 if hot else S1, linewidth=1.2))
        ax.text(x + w / 2, 20.2, n, ha="center", va="center", fontsize=9, fontweight="bold", color=INK)
        ax.text(x + w / 2, 13.6, d, ha="center", va="center", fontsize=5.6, color=INK)
        if i < len(nodes) - 1:
            ax.annotate("", xy=(x + w + gap - 0.2, 15.5), xytext=(x + w + 0.2, 15.5),
                        arrowprops=dict(arrowstyle="-|>", color=INK2, lw=0.8))
    ax.add_patch(FancyBboxPatch((1.0, 0.8), 47, 5.2, boxstyle="round,pad=0.2,rounding_size=1", facecolor="#f3f2ee", edgecolor=INK2, lw=0.8))
    ax.text(24.5, 3.4, "MLFO = Coordinator A8: waves, visibility, routing, termination", ha="center", va="center", fontsize=6, color=INK)
    ax.add_patch(FancyBboxPatch((51, 0.8), 48, 5.2, boxstyle="round,pad=0.2,rounding_size=1", facecolor="#f3f2ee", edgecolor=INK2, lw=0.8))
    ax.text(75, 3.4, "ML Sandbox = the simulator; reform replay = policy extrapolation (d10_m03)", ha="center", va="center", fontsize=6, color=INK)
    ax.text(1.0, 27.6, "MAJLIS as an ITU-T Y.3172 ML pipeline", fontsize=8.5, fontweight="bold", color=INK)
    fig.savefig(out, facecolor="white", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def qr(out: Path, url: str = LIVE_URL) -> None:
    import qrcode

    img = qrcode.make(url, box_size=8, border=2)
    img.save(out)


def build_assets() -> dict[str, Any]:
    fig_dir = config.REPORT_DIR / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    nums = build_numbers()
    (config.RESULTS_DIR / "numbers.json").write_text(json.dumps(nums, indent=1, ensure_ascii=False, default=str))
    made = []
    fig_architecture(fig_dir / "fig_architecture.png")
    made.append("fig_architecture.png")
    if nums.get("baseline") and nums.get("reform"):
        fig_awareness(nums, fig_dir / "fig_awareness.png")
        fig_kpi(fig_dir / "fig_kpi.png")
        made += ["fig_awareness.png", "fig_kpi.png"]
    qr(fig_dir / "qr_live.png")
    made.append("qr_live.png")
    return {"numbers": str(config.RESULTS_DIR / "numbers.json"), "figures": made}

"""MAJLIS command-line interface (typer + rich).

    majlis collect | ingest | kb-eval
    majlis run --scenario uae_nye_cells [--reform uae_reform_pack] [--llm ollama|none] [--replay] [--no-gate]
    majlis play | ask | verify | dashboard | report-assets | export-replay | web | all
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from majlis import config

app = typer.Typer(add_completion=False, help="MAJLIS — no mandate, no action. Mandate-gated multi-agent crisis council (FICTIONAL simulation).")
con = Console()


def _llm(llm: str, replay: bool, model: Optional[str] = None):
    from majlis.llm.adapter import LLM

    return LLM(provider=llm, model=model or config.LLM_MODEL, replay=replay)


@app.command()
def collect(force: bool = typer.Option(False, help="re-download even if cached")):
    """Y.3172 C node: download sources, record URL / retrieval date / SHA-256 / licence in kb/export/manifest.csv."""
    from majlis.kb.collect import collect as _collect

    rows = _collect(force=force)
    bad = [r for r in rows if str(r["status"]).startswith("failed")]
    con.print(f"[bold]{len(rows)}[/] documents in manifest · {len(bad)} failed (logged, never substituted)")


@app.command()
def ingest(no_embed: bool = typer.Option(False, help="skip embeddings (BM25 + TF-IDF/LSA only)")):
    """Y.3172 PP node: parse → legal-structure chunking → tags → chunks.jsonl → embeddings → ChromaDB."""
    from majlis.kb.ingest import run_ingest

    t0 = time.time()
    info = run_ingest(embed=not no_embed)
    con.print(f"[bold green]✓[/] {info['chunks']} chunks · dense: {info.get('dense')} · {time.time() - t0:.0f}s")
    if info.get("chroma"):
        con.print(f"ChromaDB collections: {info['chroma']}")
    for d, why in info["skipped"]:
        con.print(f"  [yellow]skipped[/] {d}: {why}")


@app.command("kb-eval")
def kb_eval(k: int = 5):
    """Evaluate retrieval (BM25 / dense / hybrid) on eval/kb_questions.jsonl → results/kb_eval.json."""
    from majlis.kb.evaluate import run_eval

    res = run_eval()
    t = Table(title=f"KB retrieval evaluation ({res['n_questions']} questions)")
    for col in ["retriever", "hit@1", "hit@3", "hit@5", "MRR"]:
        t.add_column(col)
    for name, r in res["retrievers"].items():
        t.add_row(name, f"{r['hit@1']:.3f}", f"{r['hit@3']:.3f}", f"{r['hit@5']:.3f}", f"{r['mrr']:.3f}")
    con.print(t)


@app.command()
def run(scenario: str = typer.Option("uae_nye_cells"), reform: Optional[str] = typer.Option(None),
        llm: str = typer.Option(config.LLM_PROVIDER, help="ollama | none"), model: Optional[str] = typer.Option(None),
        replay: bool = typer.Option(False, help="DEMO_MODE: read LLM + retrieval only from cache (offline, deterministic)"),
        no_gate: bool = typer.Option(False, help="ablation: compute gate verdicts but do not enforce them"),
        name: Optional[str] = typer.Option(None, help="run directory name under runs/"),
        adviser_model: Optional[str] = typer.Option(config.ADVISER_MODEL, help="model for the Policy & Legal Adviser (A7)")):
    """Run the scenario through the multi-agent council."""
    from majlis.coord.coordinator import run_scenario

    run_name = name or ("reform" if reform else "baseline") + ("_nogate" if no_gate else "")
    t0 = time.time()
    adv = _llm(llm, replay, adviser_model) if (adviser_model and llm != "none") else None
    out = run_scenario(scenario, reform, _llm(llm, replay, model), run_name, gate_on=not no_gate, replay=replay, llm_adviser=adv)
    m = out["metrics"]
    con.print(f"[bold]run[/] runs/{run_name} · {time.time() - t0:.0f}s · LLM {out['meta']['llm']} · "
              f"audit {out['meta']['audit_entries']} entries · root {out['meta']['audit_root'][:12]}…")
    con.print(f"gaps {m['gaps_total']} {m['gaps_by_type']} · blocked {m['blocked_actions']} · rerouted {m['rerouted_messages']} · "
              f"conflicts {m['conflicting_actions']} · restored T+{m['service_restored_min']} · coverage {m['citation_coverage']}")


@app.command()
def verify(run: str):
    """Recompute the SHA-256 hash chain of runs/<run>/audit.jsonl."""
    from majlis.audit.chain import verify as _verify

    p = Path(run)
    path = p if p.suffix == ".jsonl" else ((p if p.exists() else config.RUNS_DIR / run) / "audit.jsonl")
    ok, n, root, msg = _verify(path)
    if ok:
        con.print(f"[bold green]✓ {n} entries verified · root {root}[/]")
    else:
        con.print(f"[bold red]✗ chain broken after {n} entries: {msg}[/]")
        raise typer.Exit(1)


@app.command()
def ask(question: str, as_agent: str = typer.Option("A3", "--as"), at: str = typer.Option("W4", "--at"),
        llm: str = typer.Option(config.LLM_PROVIDER), replay: bool = typer.Option(False)):
    """Ask the Policy & Legal Adviser (A7) a question as any agent at any wave (logged to runs/ask/)."""
    from majlis.agents.mandates import load_registry
    from majlis.agents.runtime import AgentRuntime
    from majlis.audit.chain import AuditLog
    from majlis.coord.retriever import Retriever
    from majlis.gate.gate import Gate
    from majlis.kb.store import KB
    from majlis.scenario.loader import load_scenario

    sc = load_scenario("uae_nye_cells")
    kb = KB(offline=replay, load_dense=not replay)
    reg = load_registry(sc.country, kb.chunks)
    rt = AgentRuntime(sc, Retriever(kb, replay), _llm(llm, replay), reg, sc.facts,
                      llm_adviser=_llm(llm, replay, config.ADVISER_MODEL) if (config.ADVISER_MODEL and llm != "none") else None)
    audit = AuditLog(config.RUNS_DIR / "ask" / f"ask_{int(time.time())}.jsonl")
    t = next((w.t for w in sc.waves if w.id == at), 0)
    qa = rt.adviser(question, as_agent, t, at, audit)
    gate = Gate(reg, kb.by_id, {}, sc.params)
    con.print(f"[bold]{sc.agents[as_agent]['name']}[/] asks at {at}: {question}\n")
    con.print(qa["answer"] + "\n")
    for part in ("uae_basis", "global_examples"):
        for it in qa[part]:
            ok = gate.check_quote(it["chunk_id"] or "", it["quote"]).ok
            con.print(f"  {'[green]✓' if ok else '[red]✗'}[/] {it['source']} {it['doc_id']} — “{it['quote'][:160]}”")
    audit.append("adviser_qa", {k: v for k, v in qa.items() if k != "_map"})


@app.command()
def play(llm: str = typer.Option(config.LLM_PROVIDER), replay: bool = typer.Option(False)):
    """Interactive facilitator console: release waves, inject events, ask the adviser as any agent — all logged."""
    from majlis.coord.play import facilitator

    facilitator(_llm(llm, replay), replay)


@app.command()
def dashboard(run: str = typer.Argument("golden"), compare: Optional[str] = typer.Option(None), open_browser: bool = typer.Option(True, "--open/--no-open")):
    """Build the self-contained analyst dashboard (single offline HTML)."""
    from majlis.dashboard.build import build_dashboard

    path = build_dashboard(run, compare)
    con.print(f"[green]✓[/] {path}")
    if open_browser:
        import webbrowser

        webbrowser.open(path.resolve().as_uri())


@app.command("export-replay")
def export_replay(run: str = typer.Argument("golden"), compare: Optional[str] = typer.Option("reform"),
                  out: Path = typer.Option(config.ROOT / "web" / "public" / "data")):
    """Write replay.json, kb_points.bin and audit.jsonl for the MAJLIS Experience."""
    from majlis.report.export import export

    info = export(run, compare, out)
    con.print(f"[green]✓[/] replay → {out} · {info}")


@app.command("report-assets")
def report_assets():
    """Figures + results/numbers.json (every number in the report/README comes from here)."""
    from majlis.report.assets import build_assets

    info = build_assets()
    con.print(f"[green]✓[/] {info}")


@app.command()
def web(lite: bool = typer.Option(False)):
    """Build and serve the Experience locally, then open the browser."""
    import subprocess
    import webbrowser

    wd = config.ROOT / "web"
    subprocess.run(["npm", "run", "build"], cwd=wd, check=True)
    url = "http://localhost:4173/" + ("?lite=1" if lite else "")
    webbrowser.open(url)
    subprocess.run(["npx", "vite", "preview", "--port", "4173"], cwd=wd)


@app.command("all")
def all_(llm: str = typer.Option(config.LLM_PROVIDER), replay: bool = typer.Option(False)):
    """collect → ingest → kb-eval → baseline → reform → no-gate ablation → dashboards → figures → export-replay."""
    if not replay:
        collect(force=False)
        ingest(no_embed=False)
    kb_eval()
    for reform, gate, name in ((None, False, "golden"), ("uae_reform_pack", False, "reform"), (None, True, "nogate")):
        run(scenario="uae_nye_cells", reform=reform, llm=llm, model=None, replay=replay, no_gate=gate, name=name,
            adviser_model=config.ADVISER_MODEL)
    report_assets()
    dashboard(run="golden", compare="reform", open_browser=False)
    export_replay(run="golden", compare="reform", out=config.ROOT / "web" / "public" / "data")


if __name__ == "__main__":
    app()

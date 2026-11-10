"""majlis play — interactive facilitator console (all actions logged to the audit chain).

Commands:
  next                       release the next tick (wave or due messages) and let agents act
  until <minute>             advance to a simulation minute
  inject <A1,A4> <text>      inject a custom event to the named agents at the current time
  ask <A3> <question>        ask the Policy & Legal Adviser as any agent, at any time
  status                     who knows what (fog of crisis)
  end                        debrief, write the run directory, print the audit root
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from majlis import config
from majlis.coord.coordinator import Coordinator, ORDER
from majlis.kb.store import KB
from majlis.scenario.loader import load_scenario

con = Console()


def facilitator(llm, replay: bool = False, scenario: str = "uae_nye_cells") -> None:
    sc = load_scenario(scenario)
    kb = KB(offline=replay, load_dense=not replay)
    coord = Coordinator(sc, None, kb, llm, config.RUNS_DIR / "play", gate_on=True, replay=replay)
    coord.start()
    now = 0.0
    con.print(f"[bold]{sc.title}[/] — {sc.label}\n{__doc__}")
    while True:
        try:
            line = con.input("[bold cyan]facilitator>[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            line = "end"
        if not line:
            continue
        cmd, _, rest = line.partition(" ")
        if cmd == "next":
            t = coord.step()
            if t is None:
                con.print("no more events — type 'end'")
            else:
                now = t
                _tail(coord, t)
        elif cmd == "until":
            target = float(rest or now)
            while coord.queue and coord.queue[0][0] <= target:
                now = coord.step() or now
            _tail(coord, now)
        elif cmd == "inject":
            who, _, text = rest.partition(" ")
            coord.push(now, 1, "custom", {"to": [a.strip() for a in who.split(",") if a.strip()], "content": text})
            now = coord.step() or now
            _tail(coord, now)
        elif cmd == "ask":
            who, _, q = rest.partition(" ")
            coord._ask(q, who, now)
            qa = coord.qa[-1]
            con.print(f"[bold]A7 → {who}[/]: {qa['answer']}")
            for part in ("uae_basis", "global_examples"):
                for it in qa[part]:
                    con.print(f"  {'[green]✓' if it.get('valid') else '[red]✗'}[/] {it['doc_id']} “{it['quote'][:140]}”")
        elif cmd == "status":
            t = Table(title=f"Fog of crisis at T+{int(now)}")
            t.add_column("agent")
            for f in sc.facts:
                t.add_column(f)
            for a in ORDER:
                t.add_row(a, *[(f"T+{coord.known_at[a][f]}" if f in coord.known_at[a] else "·") for f in sc.facts])
            con.print(t)
        elif cmd == "end":
            coord._debrief()
            out = coord._finish()
            con.print(f"[green]✓[/] runs/play · audit {out['meta']['audit_entries']} entries · root {out['meta']['audit_root']}")
            return
        else:
            con.print(__doc__)


def _tail(coord: Coordinator, t: float) -> None:
    for e in coord.timeline[-12:]:
        if e["t"] == t and e["type"] in ("inject", "gate_block", "gate_flag", "message", "belief", "adviser_qa"):
            p = e["payload"]
            con.print(f"  T+{int(e['t']):>3} {e['type']:<10} {e['agent'] or '':<3} " +
                      str(p.get("reason") or p.get("content") or p.get("fact") or p.get("question") or "")[:110])

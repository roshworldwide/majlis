"""Visibility, determinism, mandates, gaps, replay schema."""
import json

import pytest

from majlis import config
from majlis.agents.mandates import load_registry
from majlis.coord.coordinator import run_scenario
from majlis.llm.adapter import LLM
from majlis.scenario.loader import load_scenario


@pytest.fixture(scope="module")
def tmpl_run():
    out = run_scenario("uae_nye_cells", None, LLM(provider="none"), "_scratch_test_a")
    return out, json.loads((config.RUNS_DIR / "_scratch_test_a" / "timeline.json").read_text())


def test_agent_never_receives_inject_outside_visibility(tmpl_run):
    _, tl = tmpl_run
    sc = load_scenario("uae_nye_cells")
    vis = {w.id: set(w.visible_to) for w in sc.waves}
    for e in tl:
        if e["type"] == "belief" and e["payload"]["source"] == "inject":
            wave_injects = [x for x in tl if x["type"] == "inject" and x["t"] == e["t"] and not x["payload"].get("suppressed")]
            assert any(e["agent"] in vis[x["payload"]["wave"]] for x in wave_injects), e


def test_facts_only_move_through_injects_messages_or_analysis(tmpl_run):
    _, tl = tmpl_run
    for e in tl:
        if e["type"] == "belief":
            assert e["payload"]["source"] in ("inject", "message", "analysis", "change_register (RF3)")
            if e["payload"]["source"] == "message":
                assert any(m["type"] == "message" and m["payload"]["msg_id"] == e["payload"]["via"]
                           and m["payload"]["to"] == e["agent"] for m in tl)


def test_template_runs_are_deterministic(tmpl_run):
    out_a, _ = tmpl_run
    out_b = run_scenario("uae_nye_cells", None, LLM(provider="none"), "_scratch_test_b")
    assert out_a["meta"]["audit_root"] == out_b["meta"]["audit_root"]


def test_golden_replays_identical():
    roots = []
    for n in ("golden", "golden_replay2", "golden_replay3"):
        p = config.RUNS_DIR / n / "meta.json"
        if not p.exists():
            pytest.skip("golden replays not generated yet (scripts/experiments.sh)")
        roots.append(json.loads(p.read_text())["audit_root"])
    assert len(set(roots)) == 1


def test_all_mandates_and_channels_cited(chunks):
    reg = load_registry("uae", chunks)
    assert not reg.rejected, reg.rejected
    assert all(c.valid for m in reg.mandates for c in m.legal_basis)


def test_six_gap_types_with_verified_examples():
    p = config.RUNS_DIR / "golden" / "gaps.json"
    if not p.exists():
        pytest.skip("golden run not generated yet")
    gaps = json.loads(p.read_text())
    types = {g["type"] for g in gaps}
    assert types >= {"unclear_responsibility", "standards_gap", "technology_gap", "legislative_gap",
                     "coordination_problem", "conflicting_objectives"}
    assert all(any(e.get("curated") for e in g["global_examples"]) for g in gaps)


def test_replay_json_validates():
    from majlis.report.replay import validate

    p = config.ROOT / "web" / "public" / "data" / "replay.json"
    assert not validate(json.loads(p.read_text()))

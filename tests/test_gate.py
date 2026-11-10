"""P-node gate: rejects a fabricated quote and an out-of-mandate action; checks channels and normative claims."""
from majlis.agents.mandates import load_registry
from majlis.gate.gate import Gate
from majlis.scenario.loader import load_scenario


def _gate(chunks, by_id, enforce=True):
    sc = load_scenario("uae_nye_cells")
    reg = load_registry("uae", chunks)
    return Gate(reg, by_id, {"A2": ["service_availability"], "A3": ["public_safety"]}, sc.params, enforce=enforce), reg


def test_rejects_fabricated_quote(chunks, by_id):
    gate, reg = _gate(chunks, by_id)
    real = reg.mandates[0].legal_basis[0]
    assert gate.check_quote(real.chunk_id, real.quote).ok
    fake = gate.check_quote(real.chunk_id, "Licensees shall notify the Authority of any AI incident within 24 hours")
    assert not fake.ok and "not found verbatim" in fake.detail
    assert not gate.check_quote("NO-SUCH-DOC::0001", real.quote).ok


def test_rejects_out_of_mandate_action(chunks, by_id):
    gate, _ = _gate(chunks, by_id)
    v = gate.check_action("T1", "A5", {"type": "public_rumour_rebuttal"}, ["A2"])
    assert not v.allowed and v.failed_rule == "G2" and v.gap_candidate["type"] == "unclear_responsibility"
    ok = gate.check_action("T2", "A2", {"type": "issue_directive", "target": "A1"}, ["A1"])
    assert ok.allowed and ok.failed_rule is None


def test_missing_channel_is_rerouted_and_logged(chunks, by_id):
    gate, _ = _gate(chunks, by_id)
    v = gate.check_message("M1", "A1", "A4", "Network fault may affect emergency calls.")
    assert v.failed_rule == "G3" and v.route == "informal" and v.gap_candidate["type"] == "coordination_problem"
    legal = gate.check_message("M2", "A2", "A1", "Please report.")
    assert legal.failed_rule is None and legal.route == "legal"


def test_uncited_normative_claim_redacted(chunks, by_id):
    gate, _ = _gate(chunks, by_id)
    clean, red = gate.scan_text("The operator must notify within 24 hours. Service is degraded.")
    assert red and "redacted" in clean
    clean2, red2 = gate.scan_text("The operator must notify the regulator [S1].")
    assert not red2


def test_objective_conflict_flagged_not_blocked(chunks, by_id):
    gate, _ = _gate(chunks, by_id)
    v = gate.check_action("T3", "A1", {"type": "keep_ml_energy_saving", "internal": True, "harms": ["service_availability"]}, ["A2"])
    assert v.allowed and v.flagged and v.gap_candidate["type"] == "conflicting_objectives"


def test_ablation_does_not_enforce(chunks, by_id):
    gate, _ = _gate(chunks, by_id, enforce=False)
    v = gate.check_action("T4", "A5", {"type": "public_rumour_rebuttal"}, [])
    assert v.allowed and v.failed_rule == "G2"


def test_normative_claim_must_cite_a_normative_source(chunks, by_id):
    gate, _ = _gate(chunks, by_id)
    lookup = {"U1.2": "Network administrators are experts in firewalls and routers.",
              "G1.1": "the entities concerned submit ... within 24 hours of becoming aware of the significant incident"}
    _, red = gate.scan_text("The operator is required to notify within 24 hours [U1.2].", lookup)
    assert red, "a citation to a non-normative sentence must not support an obligation"
    _, red2 = gate.scan_text("Entities are required to send an early warning within 24 hours [G1.1].", lookup)
    assert not red2

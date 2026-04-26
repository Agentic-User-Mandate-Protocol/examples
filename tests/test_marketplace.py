from aump.schemas import SchemaRegistry

from aump_examples.marketplace import run_marketplace_proof


def test_marketplace_proof_passes() -> None:
    proof = run_marketplace_proof()
    assert proof["passed"] is True
    assert proof["conformance"]["failed"] == 0


def test_marketplace_exercises_required_decisions() -> None:
    scenarios = run_marketplace_proof()["scenarios"]
    assert scenarios["accept_ping_pong"]["decision"] == "allowed"
    assert scenarios["over_budget_offer"]["decision"] == "denied"
    assert "price_above_budget" in scenarios["over_budget_offer"]["reason_codes"]
    assert scenarios["private_disclosure"]["decision"] == "denied"
    assert "disclosure_denied" in scenarios["private_disclosure"]["reason_codes"]
    assert scenarios["checkout_escalation"]["decision"] == "requires_escalation"


def test_marketplace_evidence_events_validate_schema() -> None:
    registry = SchemaRegistry.bundled()
    proof = run_marketplace_proof()
    assert proof["evidence"]
    for event in proof["evidence"]:
        assert registry.validate("evidence-event", event) == []

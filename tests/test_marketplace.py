from aump import AumpRuntime
from aump.bridges import AUMP_A2A_EXTENSION_URI
from aump.policy import parse_datetime
from aump.schemas import SchemaRegistry

from aump_examples.agents import BuyerAgent, SellerAgent
from aump_examples.jsonio import load_json
from aump_examples.marketplace import run_marketplace_proof
from aump_examples.paths import DATA_DIR


def test_marketplace_proof_passes() -> None:
    proof = run_marketplace_proof()
    assert proof["passed"] is True
    assert proof["conformance"]["failed"] == 0
    assert proof["scenarios"]["seller_reply"]["accepted"] is True
    assert proof["scenarios"]["seller_reply"]["a2a_validation"]["valid"] is True


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


def test_a2a_hash_tampering_is_rejected_before_seller_evidence() -> None:
    runtime, buyer, seller, listing = _marketplace_agents()
    offer = buyer.make_offer_message(listing)
    before_count = len(runtime.evidence.events)
    offer["a2a_message"]["message"]["metadata"][AUMP_A2A_EXTENSION_URI][
        "mandate_hash"
    ] = "sha256-" + ("0" * 64)

    result = seller.receive_offer(offer["a2a_message"], listing)

    assert result["accepted"] is False
    assert result["errors"] == ["A2A mandate hash mismatch"]
    assert len(runtime.evidence.events) == before_count


def test_a2a_full_mandate_leak_is_rejected_before_seller_evidence() -> None:
    runtime, buyer, seller, listing = _marketplace_agents()
    offer = buyer.make_offer_message(listing)
    before_count = len(runtime.evidence.events)
    offer["a2a_message"]["message"]["metadata"][AUMP_A2A_EXTENSION_URI][
        "mandate"
    ] = runtime.mandates[buyer.mandate_id]

    result = seller.receive_offer(offer["a2a_message"], listing)

    assert result["accepted"] is False
    assert result["errors"] == ["A2A message must not embed full private AUMP mandate"]
    assert len(runtime.evidence.events) == before_count


def _marketplace_agents() -> tuple[AumpRuntime, BuyerAgent, SellerAgent, dict]:
    mandates = {}
    for path in (DATA_DIR / "mandates").glob("*.json"):
        mandate = load_json(path)
        mandates[mandate["id"]] = mandate

    runtime = AumpRuntime(
        mandates=mandates,
        now=parse_datetime("2026-04-25T18:00:00Z"),
    )
    buyer = BuyerAgent(runtime=runtime, mandate_id="aump_mnd_market_buyer_001")
    seller = SellerAgent(runtime=runtime, mandate_id="aump_mnd_market_seller_001")
    listing = load_json(DATA_DIR / "listings" / "ping-pong-balls.json")
    return runtime, buyer, seller, listing

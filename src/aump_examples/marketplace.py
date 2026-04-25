"""Deterministic end-to-end AUMP marketplace proof."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aump import AumpRuntime, validate_bridge
from aump.policy import parse_datetime
from aump_conformance.runner import run_suite

from aump_examples.agents import BuyerAgent, SellerAgent
from aump_examples.jsonio import load_json
from aump_examples.paths import CONFORMANCE_FIXTURES, DATA_DIR


def run_marketplace_proof() -> dict[str, Any]:
    """Run a deterministic marketplace scenario backed by AUMP evaluation."""
    conformance_report = run_suite(CONFORMANCE_FIXTURES)
    mandates = _load_mandates()
    listings = {
        "ping_pong": load_json(DATA_DIR / "listings" / "ping-pong-balls.json"),
        "over_budget": load_json(DATA_DIR / "listings" / "over-budget-orbs.json"),
    }
    runtime = AumpRuntime(
        mandates=mandates,
        now=parse_datetime("2026-04-25T18:00:00Z"),
    )
    buyer = BuyerAgent(runtime=runtime, mandate_id="aump_mnd_market_buyer_001")
    seller = SellerAgent(runtime=runtime, mandate_id="aump_mnd_market_seller_001")

    offer = buyer.make_offer_message(listings["ping_pong"])
    offer_bridge_ok, offer_bridge_errors = validate_bridge(
        offer["a2a_message"],
        "a2a_message",
    )
    seller_reply = seller.receive_offer(offer["a2a_message"], listings["ping_pong"])
    seller_bridge_ok, seller_bridge_errors = validate_bridge(
        seller_reply,
        "a2a_message",
    )

    accepted = buyer.accept_listing(listings["ping_pong"])
    mcp_bridge_ok, mcp_bridge_errors = validate_bridge(
        accepted["mcp_tool_call"],
        "mcp_meta",
    )

    over_budget = buyer.accept_listing(listings["over_budget"])
    private_disclosure = buyer.attempt_private_disclosure(listings["ping_pong"])
    checkout_escalation = _run_checkout_escalation(runtime)

    proof = {
        "conformance": {
            "total": conformance_report.total,
            "passed": conformance_report.passed,
            "failed": conformance_report.failed,
        },
        "scenarios": {
            "offer_message": {
                "decision": offer["decision"]["decision"],
                "bridge_valid": offer_bridge_ok,
                "bridge_errors": offer_bridge_errors,
            },
            "seller_reply": {
                "bridge_valid": seller_bridge_ok,
                "bridge_errors": seller_bridge_errors,
            },
            "accept_ping_pong": {
                "decision": accepted["decision"]["decision"],
                "bridge_valid": mcp_bridge_ok,
                "bridge_errors": mcp_bridge_errors,
            },
            "over_budget_offer": {
                "decision": over_budget["decision"]["decision"],
                "reason_codes": over_budget["decision"]["reason_codes"],
            },
            "private_disclosure": {
                "decision": private_disclosure["decision"]["decision"],
                "reason_codes": private_disclosure["decision"]["reason_codes"],
            },
            "checkout_escalation": checkout_escalation,
        },
        "evidence": runtime.evidence.events,
    }
    proof["passed"] = _proof_passed(proof)
    return proof


def _load_mandates() -> dict[str, dict[str, Any]]:
    mandates: dict[str, dict[str, Any]] = {}
    for path in (DATA_DIR / "mandates").glob("*.json"):
        mandate = load_json(path)
        mandates[mandate["id"]] = mandate
    return mandates


def _run_checkout_escalation(runtime: AumpRuntime) -> dict[str, Any]:
    mandate_id = "aump_mnd_shop_001"
    action = {
        "type": "create_cart",
        "summary": "Create a UCP checkout cart for selected shoes.",
        "counterparty": "merchant_456",
        "amount": {
            "currency": "USD",
            "total_minor": 12900,
        },
        "downstream_refs": [
            {"protocol": "ucp", "id": "checkout_123"},
        ],
    }
    decision = runtime.evaluate_action(
        mandate_id,
        action,
        context={"conditions": ["checkout_ready"]},
    )
    ucp_payload = {
        "meta": {
            "ucp-agent": {
                "profile": "https://platform.example/profiles/shopping-agent.json",
            },
            "aump": {
                "mandate_id": mandate_id,
                "mandate_hash": runtime.resolve_mandate(mandate_id)["hash"],
                "version": "0.1.0",
            },
        },
        "checkout": {
            "id": "checkout_123",
            "status": "buyer_review_required",
        },
    }
    bridge_ok, bridge_errors = validate_bridge(ucp_payload, "ucp_reference")
    runtime.append_evidence(
        mandate_id,
        "checkout_escalation_evaluated",
        action["summary"],
        decision["decision"],
        {
            "checkout_id": "checkout_123",
            "reason_codes": decision["reason_codes"],
        },
    )
    return {
        "decision": decision["decision"],
        "reason_codes": decision["reason_codes"],
        "ucp_bridge_valid": bridge_ok,
        "ucp_bridge_errors": bridge_errors,
    }


def _proof_passed(proof: dict[str, Any]) -> bool:
    scenarios = proof["scenarios"]
    return all(
        [
            proof["conformance"]["failed"] == 0,
            scenarios["offer_message"]["decision"] == "allowed",
            scenarios["offer_message"]["bridge_valid"],
            scenarios["seller_reply"]["bridge_valid"],
            scenarios["accept_ping_pong"]["decision"] == "allowed",
            scenarios["accept_ping_pong"]["bridge_valid"],
            scenarios["over_budget_offer"]["decision"] == "denied",
            "price_above_budget" in scenarios["over_budget_offer"]["reason_codes"],
            scenarios["private_disclosure"]["decision"] == "denied",
            "disclosure_denied" in scenarios["private_disclosure"]["reason_codes"],
            scenarios["checkout_escalation"]["decision"] == "requires_escalation",
            scenarios["checkout_escalation"]["ucp_bridge_valid"],
            len(proof["evidence"]) >= 6,
        ]
    )


def write_transcript(path: Path) -> dict[str, Any]:
    """Run the proof and write a JSON transcript."""
    from aump_examples.jsonio import dump_json

    proof = run_marketplace_proof()
    path.write_text(dump_json(proof), encoding="utf-8")
    return proof

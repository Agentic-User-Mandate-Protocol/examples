"""Reference buyer and seller agents for a deterministic AUMP marketplace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aump import AumpRuntime, mandate_hash
from aump.bridges import AUMP_A2A_EXTENSION_URI


@dataclass
class BuyerAgent:
    """Buyer agent that evaluates every material action through AUMP."""

    runtime: AumpRuntime
    mandate_id: str

    def make_offer_message(self, listing: dict[str, Any]) -> dict[str, Any]:
        mandate = self.runtime.mandates[self.mandate_id]
        action = {
            "type": "make_offer",
            "summary": f"Offer on {listing['title']}.",
            "counterparty": listing["seller_id"],
            "amount": listing["price"],
            "downstream_refs": [
                {"protocol": "marketplace", "id": listing["id"]},
            ],
        }
        decision = self.runtime.evaluate_action(self.mandate_id, action)
        self.runtime.append_evidence(
            self.mandate_id,
            "offer_sent",
            action["summary"],
            decision["decision"],
            {"listing_id": listing["id"], "reason_codes": decision["reason_codes"]},
        )

        mandate_ref = {
            "mandate_id": self.mandate_id,
            "mandate_hash": mandate_hash(mandate),
            "version": mandate.get("aump", {}).get("version", "0.1.0"),
        }
        offer_text = (
            f"I can offer {listing['price']['total_minor'] / 100:.2f} "
            f"{listing['price']['currency']} for {listing['title']}."
        )
        return {
            "decision": decision,
            "a2a_message": {
                "headers": {
                    "A2A-Extensions": AUMP_A2A_EXTENSION_URI,
                },
                "message": {
                    "messageId": f"msg_offer_{listing['id']}",
                    "role": "user",
                    "parts": [{"text": offer_text}],
                    "extensions": [AUMP_A2A_EXTENSION_URI],
                    "metadata": {
                        AUMP_A2A_EXTENSION_URI: mandate_ref,
                    },
                },
            },
        }

    def accept_listing(self, listing: dict[str, Any]) -> dict[str, Any]:
        action = {
            "type": "accept_deal",
            "summary": f"Accept seller offer for {listing['title']}.",
            "counterparty": listing["seller_id"],
            "amount": listing["price"],
            "downstream_refs": [
                {"protocol": "marketplace", "id": listing["id"]},
            ],
        }
        tool_call = self.runtime.mcp_tool_call(
            tool_name="aump.evaluate_action",
            mandate_id=self.mandate_id,
            arguments={
                "mandate_ref": {"id": self.mandate_id},
                "proposed_action": action,
            },
        )
        decision = self.runtime.evaluate_action(self.mandate_id, action)
        event_type = (
            "deal_accepted" if decision["decision"] == "allowed" else "deal_denied"
        )
        self.runtime.append_evidence(
            self.mandate_id,
            event_type,
            action["summary"],
            decision["decision"],
            {
                "listing_id": listing["id"],
                "reason_codes": decision["reason_codes"],
                "mcp_call_id": tool_call["id"],
            },
        )
        return {"decision": decision, "mcp_tool_call": tool_call}

    def attempt_private_disclosure(self, listing: dict[str, Any]) -> dict[str, Any]:
        action = {
            "type": "make_offer",
            "summary": "Reveal buyer reservation price to seller.",
            "counterparty": listing["seller_id"],
            "disclosures": [
                {
                    "field": "negotiation.reservation_price_minor",
                    "content": "The buyer can pay up to 5 USD.",
                }
            ],
        }
        decision = self.runtime.evaluate_action(self.mandate_id, action)
        self.runtime.append_evidence(
            self.mandate_id,
            "disclosure_evaluated",
            action["summary"],
            decision["decision"],
            {"reason_codes": decision["reason_codes"]},
        )
        return {"decision": decision}


@dataclass
class SellerAgent:
    """Seller agent that receives A2A messages and records material offers."""

    runtime: AumpRuntime
    mandate_id: str

    def receive_offer(
        self,
        a2a_message: dict[str, Any],
        listing: dict[str, Any],
    ) -> dict:
        metadata = (
            a2a_message["message"]
            .get("metadata", {})
            .get(
                AUMP_A2A_EXTENSION_URI,
                {},
            )
        )
        self.runtime.append_evidence(
            self.mandate_id,
            "offer_received",
            f"Received offer for {listing['title']}.",
            "received",
            {
                "listing_id": listing["id"],
                "buyer_mandate_id": metadata.get("mandate_id"),
                "buyer_mandate_hash": metadata.get("mandate_hash"),
            },
        )
        seller_mandate = self.runtime.mandates[self.mandate_id]
        return {
            "headers": {
                "A2A-Extensions": AUMP_A2A_EXTENSION_URI,
            },
            "message": {
                "messageId": f"msg_reply_{listing['id']}",
                "role": "agent",
                "parts": [{"text": "Offer received. Ready to close if allowed."}],
                "extensions": [AUMP_A2A_EXTENSION_URI],
                "metadata": {
                    AUMP_A2A_EXTENSION_URI: {
                        "mandate_id": self.mandate_id,
                        "mandate_hash": mandate_hash(seller_mandate),
                        "version": seller_mandate.get("aump", {}).get(
                            "version",
                            "0.1.0",
                        ),
                    },
                },
            },
        }

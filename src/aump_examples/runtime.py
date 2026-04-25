"""Small AUMP-aware runtime used by the reference examples."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from typing import Any

from aump_conformance.bridges import AUMP_META_HASH, AUMP_META_ID
from aump_conformance.policy import evaluate_action, parse_datetime

DEFAULT_NOW = parse_datetime("2026-04-25T18:00:00Z")


def mandate_hash(mandate: dict[str, Any]) -> str:
    """Return a deterministic demo hash for a mandate."""
    import json

    encoded = json.dumps(mandate, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256-{sha256(encoded).hexdigest()}"


@dataclass
class EvidenceLog:
    """Append-only evidence log for material agent decisions."""

    events: list[dict[str, Any]] = field(default_factory=list)

    def append(
        self,
        *,
        mandate_id: str,
        event_type: str,
        summary: str,
        result: str,
        refs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "index": len(self.events) + 1,
            "mandate_id": mandate_id,
            "type": event_type,
            "summary": summary,
            "result": result,
            "refs": refs or {},
        }
        self.events.append(event)
        return event


@dataclass
class AumpRuntime:
    """Reference runtime that exposes MCP-shaped AUMP operations."""

    mandates: dict[str, dict[str, Any]]
    now: datetime = DEFAULT_NOW
    evidence: EvidenceLog = field(default_factory=EvidenceLog)

    def resolve_mandate(self, mandate_id: str) -> dict[str, Any]:
        if mandate_id not in self.mandates:
            raise KeyError(f"unknown mandate {mandate_id}")
        mandate = self.mandates[mandate_id]
        return {
            "id": mandate["id"],
            "hash": mandate_hash(mandate),
            "version": mandate["aump"]["version"],
            "public_summary": mandate.get("disclosure", {}).get("public_summary"),
        }

    def evaluate_action(
        self,
        mandate_id: str,
        action: dict[str, Any],
        *,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        mandate = self.mandates[mandate_id]
        return evaluate_action(mandate, action, now=self.now, context=context)

    def append_evidence(
        self,
        mandate_id: str,
        event_type: str,
        summary: str,
        result: str,
        refs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.evidence.append(
            mandate_id=mandate_id,
            event_type=event_type,
            summary=summary,
            result=result,
            refs=refs,
        )

    def mcp_tool_call(
        self,
        *,
        tool_name: str,
        mandate_id: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        mandate = self.mandates[mandate_id]
        return {
            "jsonrpc": "2.0",
            "id": f"call_{len(self.evidence.events) + 1}",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": {
                    "_meta": {
                        AUMP_META_ID: mandate_id,
                        AUMP_META_HASH: mandate_hash(mandate),
                    },
                    **arguments,
                },
            },
        }

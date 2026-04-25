"""CLI for AUMP reference examples."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aump_examples.jsonio import dump_json
from aump_examples.marketplace import run_marketplace_proof, write_transcript


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aump-examples",
        description="Run reference AUMP agentic examples.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    marketplace = subparsers.add_parser(
        "marketplace",
        help="Run the deterministic buyer/seller marketplace proof.",
    )
    marketplace.add_argument("--json", action="store_true", help="Emit JSON.")
    marketplace.add_argument("--output", help="Write transcript JSON to path.")

    args = parser.parse_args(argv)
    if args.command == "marketplace":
        if args.output:
            proof = write_transcript(Path(args.output))
        else:
            proof = run_marketplace_proof()

        if args.json:
            sys.stdout.write(dump_json(proof))
        else:
            sys.stdout.write(_render_summary(proof))
        return 0 if proof["passed"] else 1

    parser.error(f"unknown command {args.command}")
    return 2


def _render_summary(proof: dict) -> str:
    scenarios = proof["scenarios"]
    conformance = proof["conformance"]
    lines = [
        "AUMP marketplace proof",
        f"conformance: {conformance['passed']}/{conformance['total']} passed",
        f"offer message: {scenarios['offer_message']['decision']}",
        f"accept ping pong balls: {scenarios['accept_ping_pong']['decision']}",
        f"over-budget offer: {scenarios['over_budget_offer']['decision']}",
        f"private disclosure: {scenarios['private_disclosure']['decision']}",
        f"checkout handoff: {scenarios['checkout_escalation']['decision']}",
        f"evidence events: {len(proof['evidence'])}",
        f"proof: {'passed' if proof['passed'] else 'failed'}",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())

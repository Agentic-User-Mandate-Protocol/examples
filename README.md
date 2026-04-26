# AUMP Examples

Reference examples for the Agentic User Mandate Protocol.

This repo proves the next layer above conformance: a runnable buyer/seller
agentic marketplace flow that uses AUMP to evaluate actions before messages,
offers, commitments, disclosures, and checkout handoffs.

## What This Proves

The marketplace example runs these deterministic scenarios:

- A buyer agent offers 3 USD for 19 ping pong balls under a delegated mandate.
- The offer is sent as an A2A-shaped message with mandate metadata.
- A seller agent receives the A2A message and records evidence.
- The buyer accepts the deal only after an MCP-shaped `aump.evaluate_action`
  call returns `allowed`.
- A 7 USD offer is denied by the mandate budget.
- A protected reservation-price disclosure is denied.
- A UCP checkout-ready handoff returns `requires_escalation`.
- Evidence is appended for material steps.

The flow imports the sibling `aump-conformance` package and runs the canonical
conformance suite first. If the contract fails, the marketplace proof fails.

## Workspace Requirement

This repo expects the org repos to be cloned as siblings:

```text
projects/
  conformance/
  examples/
```

## Run

```bash
uv sync
uv run aump-examples marketplace
```

Expected summary:

```text
AUMP marketplace proof
conformance: 29/29 passed
offer message: allowed
accept ping pong balls: allowed
over-budget offer: denied
private disclosure: denied
checkout handoff: requires_escalation
evidence events: 6
proof: passed
```

Write the full transcript:

```bash
uv run aump-examples marketplace --json --output transcript.json
```

## Test

```bash
uv run ruff check .
uv run pytest
```

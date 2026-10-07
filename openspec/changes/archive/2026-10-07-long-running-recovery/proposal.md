# Proposal

## Why

Change `prompt-template` (archived 2026-10-07) made the run-control layer explicit
but documentary: the state/signal taxonomy, retry budget and propagation rule
exist as template and spec text, yet nothing executes them. The known failure
modes of a long run remain open: contaminated continuation (the next unit
builds on a parked, broken base), death-spiral retries on one failing
verification, and spin — iterations whose tool calls all "succeed" while
producing zero durable progress. This change turns the documented vocabulary
into executed behavior of the team contracts.

## What Changes

- `agents/planner.md` — each decomposed task ends with an explicit
  machine-readable `Depends on: <ids | ->` marker (the planner owns dependency
  semantics; scheduling may not invent dependencies).
- `agents/orchestrator.md` — Recovery clauses in the Run Brief block (briefed
  runs only): retries = min(brief, contract default 3); security failures 0 —
  escalate; on exhaustion classify continuation (independent next → continue,
  only dependents remain → BLOCKED, systemic → escalate); `PARK(X)` propagates
  BLOCKED to `Depends on: X` tasks while the independent frontier continues;
  empty frontier → run-level BLOCKED in the handoff; on resume, disposition
  comments are reconciled with the ledger.
- `agents/orchestrator.md` — always-on No-progress guard: every iteration must
  leave a durable trace (task / evidence / implementation / decision / blocker
  state); 2 consecutive trace-less iterations → change strategy or park.
- `examples/RUN-BRIEF.md` §10 — explicit defaults (retries 3, no-progress
  threshold 2, security 0).
- `docs/design-decisions.md` #16; new runbook `docs/recovery-experiment.md`
  with the two experimental criteria (forced failure, context loss).
- Contract line cap for the orchestrator: 105 → 115 (SPEC.md + validate.py).

### Non-goals (change C `run-observability`)

RUN-SUMMARY contract, BLOCKERS.md convention, dashboard alignment, mechanical
template validation.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `run-briefs`: adds requirements for executed recovery — Recovery policy
  execution, Dependency propagation, No-progress detection, Disposition
  refresh on resume.

## Impact

- Files: `agents/planner.md` (1 sentence replaced, line count unchanged),
  `agents/orchestrator.md` (+~10 lines, new cap 115), `SPEC.md` (cap line),
  `scripts/validate.py` (LIMITS), `examples/RUN-BRIEF.md` (§10 defaults),
  `docs/design-decisions.md`, `docs/recovery-experiment.md` (new).
- Compatibility: without a brief, observable behavior changes only by the
  planner's marker format and the always-on no-progress guard; the disposition
  machinery (retries, parking, propagation) is active in briefed runs only.
- Verification: the runbook's forced-failure walkthrough maps each contract
  clause; live-run evidence lands with the first real briefed run.

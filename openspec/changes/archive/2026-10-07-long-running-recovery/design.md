# Design

## Context

Change `prompt-template` shipped the run-brief layer: template, opt-in command
hooks, the orchestrator's conditional Run Brief block (HOW-only overlay,
immutability, rehydration, dispositions-as-comments) and the state/signal
taxonomy in the template appendix. All of it is contract text; nothing
executes transitions. The orchestrator contract is at its 105-line cap; the
planner expresses dependencies as free text; retry discipline exists only as
template slots. See proposal.md — Why.

User-locked decisions for this change (2026-10-07): extend the `run-briefs`
capability (no new capability); raise the orchestrator cap to 115; the
disposition machinery is active in briefed runs only; the no-progress guard
is always active.

## Goals / Non-Goals

**Goals:**

- Executed recovery: retry budget, exhaustion classification, dependency
  propagation, run-level BLOCKED — as contract clauses the orchestrator
  follows during real runs.
- Machine-greppable dependency markers from the planner.
- An always-on spin guard that works with or without a brief.
- A runbook that turns the two experimental criteria into checkable evidence.

**Non-Goals:**

- RUN-SUMMARY, BLOCKERS.md, dashboard, template validation — change C.
- New roles, code, plugins. Automated tests for agent behavior (it is contract
  text; the runbook carries the verification).

## Decisions

### D1. Recovery lives as clauses of the Run Brief block (briefed runs only)

The orchestrator's existing conditional block gains Recovery and Propagation
bullets. Unbriefed runs keep their current semantics — that preserves
`prompt-template`'s compatibility criterion ("no brief — no behavior
change") for everything except the two deliberately global additions below.

### D2. Retry budget = min(brief, 3); security = 0

Scalar merge per the monotonic rules: the strictest of applicable values
wins, so a brief can lower but never raise the contract default. Security
failures never retry — escalation is cheap, a repeated insecure attempt is
not.

### D3. Classification on exhaustion (contaminated-continuation fix)

The E1 rule "3 failures → commit WIP → next ticket" ignored the dependency
graph. Replacement: classify the remainder — independent next unit →
continue; only dependents → BLOCKED; systemic → escalate. The next unit never
builds on a parked, broken base.

### D4. `Depends on:` markers are planner output, one line, greppable

Format: `Depends on: <ids | ->`. The planner owns dependency semantics; the
orchestrator schedules but never invents dependencies. A missing marker is an
assumption in DECISIONS.md plus a sequential-safe (treat as dependent)
fallback — conservative by default.

### D5. No-progress guard is global (locked decision)

Two lines in the always-active Main Directive: every iteration leaves a
durable trace (task / evidence / implementation / decision / blocker); two
trace-less iterations → rotate strategy or park. Applies to every run: spin
is a failure mode with or without a brief, and the guard changes no
artifacts — only stops wasted iterations.

### D6. Orchestrator cap 105 → 115 (locked decision, Ask-first boundary)

Additions: ~8 lines of Recovery/Propagation clauses + 2 lines of no-progress
directive ≈ 114 total, one line of headroom under 115. SPEC.md and
`scripts/validate.py` LIMITS move together (kept consistent by the same
change; the 90/96 drift from before `prompt-template` must not recur).

### D7. Verification is a runbook, not an automated test

`docs/recovery-experiment.md` carries the two experimental criteria with
evidence checklists: (1) forced failure — brief with retries 1 over a chain
A(-) → B(A) → C(-), induce a verification failure in A, expect A PARKED, B
BLOCKED, C continues, run-level BLOCKED recorded when C finishes; (2) context
loss — execute a unit, force compaction, resume, verify the six rehydration
checkpoints. Agent behavior cannot be unit-tested; the runbook is executed on
the first real briefed run and its evidence row is the criterion.

## Risks / Trade-offs

- [Over-eager parking starves a run] → Mitigation: classification rule
  (independent frontier continues) + human reviews the ledger/handoff;
  runbook criterion (2) checks exactly this.
- [Planner omits markers on complex graphs] → Mitigation: D4 fallback
  (DECISIONS entry, treat as dependent) — safe but slower; marker presence is
  greppable in review.
- [Contract at 114/115 leaves no room for C] → Accepted: C's additions land
  in commands/docs, not the orchestrator; if that changes, the cap decision
  is revisited in C's design.
- [Marker format drift] → Mitigation: one canonical example in planner
  contract + runbook; no schema machinery until a second consumer exists.

## Migration Plan

Additive contract clauses + docs. Unbriefed runs: only the planner marker
format and the global no-progress directive appear. Rollback = revert this
change's file edits; no state to migrate.

# Proposal

## Why

An empirically proven overnight run (the E1 brief, 197 lines built on `/team-change`)
demonstrated that long-running unattended runs become reliable when the operator supplies
a fourth artifact class — a **run brief**: scope fences, reading budgets, gates, retry
budgets, evidence tables, and a designed morning handoff. That layer is absent from the
shipped product: `/team` carries only a one-line autonomy clause, and every new overnight
run would have to re-invent the structure from private experience. Generalize the proven
structure into an optional, reusable template so any project gets E1-grade run control by
dropping one file into the repo root.

## What Changes

- **New `examples/RUN-BRIEF.md`** — the generalized run-brief template: 12 sections
  (envelope, mission reference, decision authority, scope map, source precedence,
  context budget, gates, execution policy, unit contract, recovery, handoff,
  termination), an immutable-categories header (the brief governs HOW, never WHAT),
  monotonic merge semantics, unit/run state and signal taxonomy, and an
  immutability/versioning block.
- **`/team` and `/team-change` recognize an optional `RUN-BRIEF.md`** in the project
  root: present → its sections act as an execution-policy overlay constraining the run;
  absent → current behavior, byte-for-byte. The brief is read-only during the run.
- **Orchestrator contract gains a conditional run-controls block** (~10 lines): the brief
  may narrow execution but never grant capabilities or redefine acceptance; after
  compaction, rehydrate from the brief's rehydration set; dispositions are recorded as
  tasks.md comments (`PARKED != DONE`), never as checkbox states.
- **Docs**: design decision #14 (run brief = fourth layer; distributed run state stays
  distributed) and #15 (monotonic run control) in `docs/design-decisions.md`; a "Run
  briefs" section in README.
- No new roles, no code, no dependencies, no permission changes.

### Non-goals (queued follow-up changes)

- `long-running-recovery` (change B): behavioral recovery machinery — disposition
  transitions, dependency propagation with explicit `Depends on:` markers in planner
  output, retry parameterization, no-progress guard, context-loss test.
- `run-observability` (change C): RUN-SUMMARY contract, BLOCKERS.md convention,
  dashboard alignment, mechanical template validation (deferred entirely).

## Capabilities

### New Capabilities

- `run-briefs`: how an optional run brief constrains an autonomous team run —
  recognition by commands, monotonic authority model, immutability during the run,
  compaction rehydration, and disposition recording.

### Modified Capabilities

(none — `plugin-integrations` is unaffected)

## Impact

- Files: `examples/RUN-BRIEF.md` (new), `commands/team.md` (+3 lines),
  `commands/team-change.md` (+2 lines), `agents/orchestrator.md` (+~10 lines against
  the SPEC.md ≤90-line contract cap — resolution decided in design.md),
  `docs/design-decisions.md`, `README.md`.
- Compatibility: fully backward — no `RUN-BRIEF.md`, no behavior change. Existing
  installs and headless flows unaffected.
- Verification: brief absent → `/team` semantics unchanged; brief present → declared
  HOW-constraints honored; `scripts/validate.py` and CI stay green.

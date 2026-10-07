# Proposal

## Why

Changes `prompt-template` (A) and `long-running-recovery` (B) both reference
run artifacts that do not exist yet: "blocker or decision ledger entry",
"run-level BLOCKED in the handoff", "recorded in the handoff". After an
interrupted or overnight briefed run, the human still assembles state by hand
from git, DECISIONS.md and the dashboard. This change ships the missing human
interface: the authoritative blocker ledger, the end-of-run RUN-SUMMARY
contract, the run-state source-of-truth rule, the twice-deferred mechanical
template check, and a committed sandbox proving ground that produces test
data without touching real work tasks.

## What Changes

- **RUN-SUMMARY contract** (briefed runs, written last): run-level terminal
  state (SUCCESS/BLOCKED/ESCALATED/EXHAUSTED/ABORT); criterion table
  (MET/PARKED + evidence path); branches with `git log --oneline main..<branch>`
  for human review/push; rolled-up DECISIONS.md and BLOCKERS.md items, one
  human action each; negative confirmations; brief path + revision. Location:
  the brief's §11 slot, default `RUN-SUMMARY.md` in the repo root.
- **BLOCKERS.md convention** — the authoritative disposition ledger (unit |
  criterion | why | what unblocks); DECISIONS.md stays for resolved
  ambiguities; contract references to "the ledger" resolve to BLOCKERS.md.
- **Run-state source of truth**: BLOCKERS.md (authoritative) > tasks.md
  disposition comments (observability pointers) > RUN-SUMMARY (derived
  snapshot); divergence resolves to the ledger, comments corrected on
  reconciliation.
- **Finish hooks** in `/team` and `/team-change` (+2 lines each): on finish
  of a briefed run write the summary; the orchestrator contract is NOT
  touched (114/115 — precedent B-D6).
- **validate.py**: mechanical check that `examples/RUN-BRIEF.md` contains the
  canonical section headings.
- **Sandbox proving ground**: `scripts/setup-sandbox.sh` builds a disposable
  briefed project (TASK.md + minimal brief with retries 1 + hand-written
  `seeded-failure` change: A `Depends on: -` with `make check-a` = exit 1,
  B `Depends on: A`, C `Depends on: -`) + runbook §3 with three drills.
- Docs: design decision #17, README paragraph, runbook recording update.

### Non-goals

Dashboard disposition panel (deferred — zero new parsing surface; named
follow-up); orchestrator contract edits; preset files; YAML manifests.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `run-briefs`: adds requirements — Run summary artifact, Blocker ledger,
  Run-state source of truth, Template mechanical validation.

## Impact

- Files: `commands/team.md` (+2), `commands/team-change.md` (+2),
  `examples/RUN-BRIEF.md` (§11 concretized), `scripts/validate.py` (+1 check),
  `scripts/setup-sandbox.sh` (new), `docs/recovery-experiment.md` (recording
  line + §3), `docs/design-decisions.md` (#17), `README.md`.
- Compatibility: unbriefed runs unchanged (no summary, no ledger — DECISIONS.md
  flow as today). Zero orchestrator lines.
- Verification: RUN-SUMMARY structure walkthrough against the spec content
  list; sandbox setup smoke; drills 1–2 executed on the sandbox produce the
  first real evidence rows for the B runbook and criterion C.

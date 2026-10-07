# Spec Delta

## ADDED Requirements

### Requirement: Run summary artifact

A briefed run SHALL end by writing a run summary at the path named by the
brief's handoff section (default `RUN-SUMMARY.md` in the repo root), written
last, containing: the run-level terminal state (SUCCESS, BLOCKED, ESCALATED,
EXHAUSTED or ABORT); a criterion table (MET/PARKED with evidence paths); the
branches created with `git log --oneline main..<branch>` for human review and
push; rolled-up DECISIONS.md and BLOCKERS.md items with one human action each;
negative confirmations (e.g. nothing pushed, no PR opened); and the brief's
path with its revision.

#### Scenario: Completed run with a parked unit

- **WHEN** a briefed run finishes with one unit PARKED and others MET
- **THEN** RUN-SUMMARY.md reports terminal state BLOCKED-or-SUCCESS per the remaining work, the criterion table marks the parked unit PARKED with its evidence path, and no parked unit is reported as done

#### Scenario: Negative confirmations present

- **WHEN** the summary is written at the end of a local-only briefed run
- **THEN** it explicitly confirms that nothing was pushed and no pull request was opened

### Requirement: Blocker ledger

In a briefed run, every parked, blocked or escalated unit SHALL get an entry
in `BLOCKERS.md` — the authoritative disposition ledger with the schema
unit | criterion | why | what unblocks. DECISIONS.md remains the ledger for
resolved ambiguities. References to "the ledger" in team contracts resolve to
BLOCKERS.md.

#### Scenario: Parked unit lands in the ledger

- **WHEN** a unit is parked after exhausting its retry budget
- **THEN** BLOCKERS.md gains a row (unit, criterion, why, what unblocks) and the unit's tasks.md comment points at that row

#### Scenario: Resume reads the ledger

- **WHEN** a briefed run is resumed against an existing change
- **THEN** disposition reconciliation reads BLOCKERS.md as the authoritative record

### Requirement: Run-state source of truth

Run-state precedence SHALL be: BLOCKERS.md (authoritative) > tasks.md
disposition comments (observability pointers only) > RUN-SUMMARY (derived
snapshot). On divergence, the ledger wins and the comment is corrected at the
next reconciliation.

#### Scenario: Comment diverges from ledger

- **WHEN** a tasks.md disposition comment contradicts a BLOCKERS.md entry
- **THEN** the BLOCKERS.md entry governs behavior and the comment is refreshed from it on resume

### Requirement: Template mechanical validation

The repo's validation script SHALL check that `examples/RUN-BRIEF.md` contains
the canonical section headings (immutable-categories header, merge rules, run
identification, the 12 numbered sections, the taxonomy appendix); a missing
heading SHALL fail validation with a non-zero exit.

#### Scenario: Template edit drops a section

- **WHEN** a heading from the canonical set is removed from examples/RUN-BRIEF.md
- **THEN** `python3 scripts/validate.py` exits non-zero naming the missing heading

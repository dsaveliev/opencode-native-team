# Spec Delta

## Purpose

Defines how an optional, operator-authored run brief (`RUN-BRIEF.md`) constrains an
autonomous team run: recognition, authority model, immutability, compaction
rehydration, and disposition recording — without altering default team behavior when
no brief is present.

## ADDED Requirements

### Requirement: Run brief recognition

The `/team` and `/team-change` commands SHALL detect a `RUN-BRIEF.md` file in the
project root before starting work. When absent, the run SHALL proceed with existing
semantics unchanged. When present, the brief SHALL be read before the first mutation
and its sections SHALL act as an execution-policy overlay for the entire run.

#### Scenario: No brief present

- **WHEN** `/team` is invoked in a project whose root contains no `RUN-BRIEF.md`
- **THEN** the run behaves identically to a project without run-brief support, with no extra questions, gates, or artifacts required

#### Scenario: Brief present

- **WHEN** `/team-change <change>` is invoked in a project whose root contains `RUN-BRIEF.md`
- **THEN** the run reads the brief before the first write, and the brief's execution-policy sections constrain delegation, verification, and commits for the whole run

### Requirement: Execution policy only (WHAT/HOW separation)

The run brief SHALL govern only HOW work is executed (order, budgets, scope fences,
gates, side-effect policy, checkpoints). It SHALL NOT redefine product requirements,
acceptance-criteria semantics, OpenSpec capability meaning, or task dependency
direction. A brief that attempts to redefine acceptance or completion meaning SHALL
have that attempt ignored, and the conflict SHALL be recorded as a run decision.

#### Scenario: Brief attempts to strengthen an acceptance criterion

- **WHEN** the brief contains a completion rule that adds or raises an acceptance criterion not present in TASK.md or the change artifacts
- **THEN** the criterion is evaluated from TASK.md/OpenSpec artifacts as-is, the brief's rule is treated at most as an additional verification gate, and the discrepancy is recorded in DECISIONS.md

#### Scenario: Brief restricts git operations

- **WHEN** the brief forbids pushing and the change workflow would otherwise allow a local merge
- **THEN** the run keeps all work on local branches and records the restriction in the run's handoff

### Requirement: Monotonic authority merge

An effective run policy SHALL be computed by narrowing, never widening: capabilities
as the intersection of runtime permissions, project policy, agent-role permissions,
and the brief's scope; numeric budgets as the minimum across applicable levels;
side-effect permissions denied if any layer denies. The brief MUST NOT grant a
capability any layer denies; grant attempts SHALL be no-ops.

#### Scenario: Brief attempts to grant push

- **WHEN** the brief contains `git: allow push` while agent permissions deny `git push*`
- **THEN** push remains denied for every role, and the brief's grant line has no effect on behavior

#### Scenario: Budget intersection

- **WHEN** the orchestrator's default retry budget is 3 and the brief sets retries to 1
- **THEN** the effective retry budget for the run is 1

#### Scenario: Budget cannot be raised by the brief

- **WHEN** the brief sets retries to 5 while the project's contract caps attempts at 3
- **THEN** the effective retry budget remains 3 and the attempt is recorded in DECISIONS.md

### Requirement: Brief immutability during the run

The executing team SHALL treat `RUN-BRIEF.md` as read-only for the duration of a run:
loaded before the first mutation, never edited by any team role, with its file
revision (git SHA or equivalent) recorded in run outputs. A brief modified after run
start SHALL define a new run rather than continue the active one.

#### Scenario: Agent weakens policy after failed verification

- **WHEN** verification fails and the agent considers editing the brief's verification section to relax it
- **THEN** the edit is prohibited by the run-brief contract, the failure is preserved as evidence, and the unit proceeds to the disposition defined by the recovery policy

#### Scenario: Reproducibility

- **WHEN** a run completes and its handoff artifact lists run inputs
- **THEN** the handoff includes the brief's path and revision identifier

### Requirement: Compaction rehydration

After any context compaction, the run SHALL restore its operating state from the
brief's rehydration set — current unit, acceptance criteria re-read verbatim from
their canonical source, active branch, and open blockers — without re-reading whole
documents or relying on the compaction summary for requirements text.

#### Scenario: Compact mid-run, then continue

- **WHEN** a compaction occurs between two units of a briefed run
- **THEN** the next unit begins with the current unit identifier, verbatim acceptance criteria, branch name, and blocker state restored from the rehydration set, and no acceptance-criterion text is taken from the compaction summary

### Requirement: Disposition recording

Execution dispositions (PARKED, BLOCKED, ESCALATED) SHALL be recorded as tasks.md
comments pointing at a blocker or decision ledger entry, and never as OpenSpec
checkbox states. `PARKED` SHALL NOT be treated as completion: a criterion without
executed evidence is never MET.

#### Scenario: Unit parked after exhausted attempts

- **WHEN** a unit exhausts its retry budget without green verification
- **THEN** its task line remains an unchecked `[ ]`, a comment under it records the disposition with a pointer to the blocker ledger, and the final handoff reports it as PARKED, not DONE

### Requirement: Generalized template availability

The project SHALL ship a run-brief template (`examples/RUN-BRIEF.md`) containing the
canonical section set — envelope, mission reference, decision authority, scope map,
source precedence, context budget, gates, execution policy, unit contract, recovery,
handoff, termination — plus the immutable-categories header, monotonic merge rules,
and the unit/run state and signal taxonomy.

#### Scenario: Operator starts a new overnight run

- **WHEN** a user copies `examples/RUN-BRIEF.md` into a project root and fills in the bracketed slots
- **THEN** the resulting `RUN-BRIEF.md` is recognized by `/team` and `/team-change` and requires no other installation step

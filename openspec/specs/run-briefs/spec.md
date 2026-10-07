# run-briefs Specification

## Purpose

Defines how an optional, operator-authored run brief (`RUN-BRIEF.md`) constrains an
autonomous team run: recognition, authority model, immutability, compaction
rehydration, and disposition recording — without altering default team behavior when
no brief is present.

## Requirements

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

### Requirement: Recovery policy execution

In a briefed run, the team SHALL apply the brief's retry budget clamped by the
contract default — effective attempts = min(brief value, 3) per failing
verification — and SHALL give security-relevant verification failures zero
retries with immediate escalation. After budget exhaustion on a unit, the run
SHALL classify continuation: an independent next unit exists → park the failed
unit and continue; only dependent units remain → they become BLOCKED;
systemic or toolchain failure → escalate (the brief's gates decide abort).

#### Scenario: Independent continuation after exhaustion

- **WHEN** unit X exhausts its retry budget and an independent unit Y is pending
- **THEN** X is PARKED (disposition comment + ledger entry) and Y proceeds

#### Scenario: Security failure escalates without retries

- **WHEN** a verification failure is security-relevant
- **THEN** no retry is attempted; the unit escalates immediately

#### Scenario: Systemic failure does not park units one by one

- **WHEN** the failing verification is toolchain-wide (e.g. baseline commands broken mid-run)
- **THEN** the run escalates or aborts per the brief's gates instead of burning retry budgets unit by unit

### Requirement: Dependency propagation

The planner SHALL end every decomposed task with an explicit
`Depends on: <ids | ->` marker. Scheduling SHALL NOT invent dependencies. On
PARK(X), every task marked `Depends on: X` SHALL transition to BLOCKED
(disposition comment + ledger); the independent frontier continues; an empty
frontier SHALL leave the run at run-level BLOCKED, recorded in the handoff. A
task without a marker SHALL be recorded in DECISIONS.md and treated as
dependent (sequential-safe fallback).

#### Scenario: Park mid-chain

- **WHEN** A1 parks while A3 and A4 carry `Depends on: A1` and no independent work remains
- **THEN** A3 and A4 become BLOCKED and the run ends at run-level BLOCKED in the handoff

#### Scenario: Independent sibling proceeds

- **WHEN** A1 parks while A2 carries `Depends on: -`
- **THEN** A2 proceeds

#### Scenario: Missing marker falls back safely

- **WHEN** a task reaches scheduling without a `Depends on:` marker
- **THEN** the orchestrator records the gap in DECISIONS.md and treats the task as dependent

### Requirement: No-progress detection

Every implementation or recovery iteration SHALL leave at least one durable
trace — task state, verified evidence, implementation state, a decision, or a
blocker entry. After 2 consecutive iterations with no durable trace, the run
SHALL treat this as a NO_PROGRESS signal: the next attempt must rotate
strategy (alternate implementation, different decomposition, stronger
verification), and park the unit if that attempt also leaves no trace. This
requirement applies to briefed and unbriefed runs alike.

#### Scenario: Repeated identical failure loop

- **WHEN** two consecutive iterations reproduce the same failing verification with no new durable state
- **THEN** the next iteration changes strategy or parks the unit; an unchanged repeat is a contract violation

### Requirement: Disposition refresh on resume

On resuming a run against an existing change (for example via
`/team-change`), the orchestrator SHALL reconcile the disposition comments in
tasks.md with the authoritative ledger before starting new work, so a human
reviewing tasks.md sees the latest run state.

#### Scenario: Resume after interruption

- **WHEN** a change with parked or blocked disposition comments is resumed
- **THEN** the comments are reconciled with the ledger entries before new work begins

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

### Requirement: Brief generation tooling

The project SHALL ship a deterministic generator (`scripts/gen-run-brief.py`,
python3 stdlib only) that produces a `RUN-BRIEF.md` from interactive answers
or non-interactive flags. The canonical template (`examples/RUN-BRIEF.md`)
is the generator's single structural source: canonical prose blocks are
copied verbatim from it, never embedded or paraphrased by the generator. A
thin command wrapper (`/team-brief`) collects answers and invokes the
generator with flags; it does not author brief text.

#### Scenario: Quick mode produces a valid minimal brief

- **WHEN** the generator runs in quick mode with six answers (name, mode, mission, scope rows, retries, fence)
- **THEN** the output contains the minimal valid section set (1, 2, 3, 4 and 12, plus 10 when retries differs from the default) with the answers substituted and canonical wording intact

#### Scenario: Non-interactive runs are reproducible

- **WHEN** the generator runs twice with identical flags
- **THEN** the two outputs are byte-identical

#### Scenario: Canonical blocks are verbatim

- **WHEN** a generated full brief is compared section-by-section with the template
- **THEN** every kept section's non-slot prose matches the template exactly

### Requirement: Run log export at run end

The run lifecycle SHALL end with a markdown run log exported from the same
data the dashboard collects. `/team-change` runs write the log to
`openspec/changes/<change>/RUN-LOG.md`; `/team` runs write it to
`tmp/run-logs/<date>-<slug>/RUN-LOG.md`. The log SHALL include the run
window, per-wave session summary with durations, per-task timings, tool
errors, permission denials, commits, and token totals. The export SHALL be
generated by a dedicated mode of the dashboard generator (`--export`) so
the dashboard and the log can never disagree about what happened.

#### Scenario: Change run finishes

- **WHEN** a `/team-change` run completes its final gates
- **THEN** `openspec/changes/<change>/RUN-LOG.md` exists and contains the
  wave table, task timings, error and denial lists, commits, and token
  totals for the run window

#### Scenario: Ad-hoc run finishes

- **WHEN** a `/team` run completes
- **THEN** a run log exists under `tmp/run-logs/` for that run

#### Scenario: Denials are visible after the run

- **WHEN** a team agent was blocked by a permission rule during the run
- **THEN** the run log lists that denial with its command and agent

### Requirement: Retro recommendations in the run log

After the run log export, the orchestrator SHALL append a recommendations
section to the same run log: friction observed during the run (slow tasks,
retries, permission denials, repeated tool errors) translated into concrete,
actionable improvement suggestions for the team framework. The section is
model-authored from run data, not a canned template.

#### Scenario: Permission friction produces a suggestion

- **WHEN** the run log shows repeated permission denials for one tool
- **THEN** the recommendations section names the tool and proposes the
  permission change that would unblock it

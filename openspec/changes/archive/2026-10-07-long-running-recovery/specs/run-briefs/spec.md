# Spec Delta

## ADDED Requirements

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

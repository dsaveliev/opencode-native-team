# Design

## Context

The team today has three artifact layers — agent contracts (who), OpenSpec (process),
TASK.md (what) — and partial, implicit run control scattered across `/team-change`
(branch discipline), the orchestrator (timeouts, waves), and one autonomy line in
`/team`. The E1 overnight brief proved a fourth layer: an operator-authored run brief
that makes unattended runs reliable. This change makes that layer explicit, optional,
and reusable. See proposal.md — Why.

Constraints that shape the design: the project's philosophy is contracts, not code
(no plugins, no TypeScript, no rules engines); SPEC.md caps the orchestrator contract;
everything must stay backward-compatible (no brief → no behavior change).

## Goals / Non-Goals

**Goals:**

- One file (`RUN-BRIEF.md`) in a project root upgrades a run to E1-grade control —
  no installer step, no new roles, no code.
- The four architectural invariants survive as contract text: monotonic authority,
  brief immutability, WHAT/HOW separation, disposition-vs-completion separation.
- A vocabulary (unit states / run states / signals) fixed now, so follow-up changes
  implement against it instead of inventing terms.

**Non-Goals:**

- Behavioral recovery machinery — disposition transitions, dependency propagation,
  retry parameterization, no-progress enforcement, context-loss test → change B
  (`long-running-recovery`).
- Observability artifacts — RUN-SUMMARY contract, BLOCKERS.md convention, dashboard
  alignment, mechanical template validation → change C (`run-observability`).
- Multi-repo scope maps, YAML manifests, a `/team-run` launcher — reconsider after
  B/C evidence.

## Decisions

### D1. Monotonic authority model (core invariant)

Effective policy is computed by narrowing only:

```
capabilities = runtime permissions ∩ project policy ∩ role permissions ∩ brief scope
budgets      = min(across applicable levels)
side effects = any layer DENY -> DENY
```

The brief MAY constrain execution; it MUST NOT grant capabilities or weaken any
deny. Precedence exists per domain, not as one ladder: WHAT is owned by
user > TASK/OpenSpec (the brief never enters this domain); HOW is owned by
user > brief > contracts > defaults, bounded above by the intersection above.

*Why not a precedence chain:* a chain lets a higher-ranked source (the brief) widen
what a lower layer denies. Intersection cannot. *Why text, not a rules engine:*
opencode already enforces the outer layers mechanically (frontmatter denies beat
top-level allows — probed); the brief's content varies per run, so its narrowing is
enforced by contract text in the orchestrator. Acceptable because the brief is
trusted operator input, not agent output. Grant attempts in a brief are no-ops
(spec: "Monotonic authority merge").

### D2. Brief immutability + versioning

The brief is read-only for the run's duration, loaded before the first mutation;
run outputs record its revision (git SHA). A mid-run edit defines a new run. This
closes the self-weakening loop (failed verification → relax policy → retry) — the
meta-level anti-Goodhart guard that pairs with the existing criterion-integrity
clauses.

### D3. State/signal taxonomy (fixed vocabulary, enforced in change B)

```
Unit states:  READY IN_PROGRESS DONE PARKED BLOCKED ESCALATED
Run states:   RUNNING SUCCESS BLOCKED ESCALATED ABORTED EXHAUSTED
Signals:      NO_PROGRESS VERIFY_FAILURE RETRY_EXHAUSTED BASELINE_FAILURE
              SCOPE_VIOLATION
```

Signals trigger transitions; states are destinations. `PARKED` = intentionally not
advancing this run (reason recorded: retry_exhausted / insufficient_evidence /
human_decision / budget / scope_change — free text, not a closed enum). This change
documents the taxonomy in the template; change B implements transitions against it.

### D4. Dispositions never touch checkbox semantics

`PARKED/BLOCKED/ESCALATED` are recorded as HTML comments under the task line,
pointing at a ledger entry — the same mechanism as the existing observability
comments (`<!-- HH:MM → role task -->`). OpenSpec keeps `[x]/[ ]` completion
semantics clean; `PARKED != DONE`. The authoritative record lives in the ledger
(DECISIONS.md until change C formalizes BLOCKERS.md); tasks.md comments are
observability pointers only.

### D5. File convention + two-line command hooks

Detection is a file convention: `RUN-BRIEF.md` in the project root. `/team` and
`/team-change` each gain 2–3 lines: if present, read first; execution-policy
overlay; read-only during run. No flags, no config keys, no third launcher. The
E1-faithful property: a brief is self-contained and survives compaction as a file.

### D6. Merge semantics of the overlay

Scalars → strictest of applicable values; lists of restrictions → intersection;
omitted section → project default; safety fields → cannot be weakened (clamped by
D1). The brief is a partial policy overlay, never a replacement contract.

### D7. Rehydration set (compaction defense)

After any compaction the run restores: current unit, acceptance criteria re-read
verbatim from their canonical source (never from the compaction summary), active
branch, open blockers. Optional: design sections named in the brief. Implemented as
one orchestrator line + template section — no compaction hooks/plugins.

### D8. Orchestrator line budget

SPEC.md caps the orchestrator at ≤90 lines; it is already 93. The run-controls
block adds ~10 after trimming ~4 redundant lines (net ≈99). Decision: raise the
SPEC.md cap for the orchestrator to ≤105 and record why in design-decisions.md
(#14/#15) — dual-layer wiring plus run-controls is the deliberate new ceiling.
This touches the project's "Ask first" boundary (modifying agent contracts /
SPEC), so it is flagged for owner review with these artifacts.

## Risks / Trade-offs

- [Template bloat — operators copy a 200-line brief for a 20-minute task]
  → Mitigation: template marks required core (header, scope, stop conditions) vs
  optional sections; minimal valid brief is ~15 lines.
- [Brief narrowing is contract-enforced, not mechanical, for varying content]
  → Mitigation: hard boundaries (push, main, external dirs) remain mechanically
  enforced by permissions; change B's experimental criteria measure brief
  compliance end-to-end.
- [A documents taxonomy but B enforces it — interim drift]
  → Mitigation: acceptable — A is additive; without a brief nothing changes, and
  the vocabulary is already fixed for B.
- [RUN-BRIEF vs TASK.md precedence confusion in the field]
  → Mitigation: immutable-categories header at the top of every brief, plus the
  README section stating "the brief governs HOW, TASK/OpenSpec govern WHAT".

## Migration Plan

Additive and opt-in: ship template + hooks + docs. No existing install changes
behavior until a user drops `RUN-BRIEF.md` into a project. Rollback = revert the
seven file edits in this change; no state to migrate.

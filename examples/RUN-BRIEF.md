# Run Brief: <run name>

<!--
Copy to the repo root as RUN-BRIEF.md and fill the <slots>. Delete optional
sections you do not need — an omitted section falls back to project defaults.
The minimal valid brief is the header (Immutable Categories, Merge Rules,
Run Identification) + sections 1, 2, 3, 4, 12. This file is READ-ONLY during
the run. Reference instantiation: the E1 overnight brief (see README).
-->

## Immutable Categories

This brief governs HOW the run executes.

- It MAY: constrain execution order; narrow scope, budgets, concurrency and
  reading; add gates and verification; forbid side effects; define
  checkpoint and handoff policy.
- It MUST NOT: grant a capability any layer denies; weaken runtime, project
  or role permissions; redefine product requirements, acceptance-criteria
  semantics or OpenSpec capability meaning; change task dependency direction
  (the planner owns dependencies — this brief may only constrain the
  concurrency of their execution).
- Any attempt at the forbidden is a no-op and is recorded in DECISIONS.md.

## Merge Rules

- Scalars (retries, concurrency, time budgets): strictest of applicable values.
- Lists of restrictions (paths, commands, sections): intersection.
- Omitted section: the project default applies.
- Safety fields are never weakened — clamped by the rules above.

## Run Identification

- Loaded before the first write; read-only for the whole run.
- Run outputs must record this file's path and revision (git SHA).
- Dispositions (parked/blocked/escalated) live in BLOCKERS.md — the
  authoritative ledger; a briefed run ends by writing RUN-SUMMARY.md (§11).
- Any edit after run start defines a NEW run, not a continuation.

## 1. Envelope [required]

- Mode: <unattended | attended>
- Autonomy: never wait for a human when a safe autonomous state transition
  exists; on ambiguity — record the assumption (with supporting source) and
  continue. A stalled run is a failed run; partial documented progress is
  the goal.
- Locality: <local-only | remote policy>

## 2. Mission Reference [required]

- Objective source: <TASK.md | openspec change <id>> — it owns WHAT and the
  completion semantics. Never duplicate acceptance criteria here.
- Additional verification gates are allowed (stronger proof); changing the
  meaning of completion is not.

## 3. Decision Authority [required]

- AUTONOMOUS (execute): <implementation details, non-product assumptions, ...>
- AUTONOMOUS + RECORD (execute, log to ledger): <reorder independent tasks, ...>
- HUMAN-REQUIRED (analyze + recommend + park): <breaking API decisions,
  new infrastructure, ...>
- PROHIBITED (do not attempt): <list>

## 4. Scope Map [required]

| Resource                | Access               | Notes              |
|-------------------------|----------------------|--------------------|
| <code repo / dir>       | write                | <branch policy>    |
| <task input>            | read, section <X> only |                  |
| <documentation>         | read-only, <dirs>    |                    |
| <run logs dir>          | write                | <outside repos>    |

- Forbidden: <paths/files never to touch or read>
- Side effects: <none | allowed list>; external writes: <none | list>

## 5. Source Precedence [optional]

- WHAT domain: user > TASK/OpenSpec artifacts (this brief never enters it).
- HOW domain: user > this brief > agent contracts > project defaults.

## 6. Context Budget [optional]

- Reading budget: <source -> exact sections; never a whole file when a
  section suffices; always-read list; ignore rules>
- Rehydration set (restore after any compaction): current unit; acceptance
  criteria VERBATIM from <canonical source>; active branch; open blockers.
  Optional additions: <design sections, ...>


## 7. Gates [optional]

- Baseline gate: <enabled | off>; base_ref: <origin/main | current tree>;
  commands: <make format-check && make lint && make test>;
  on_failure: <abort — write ABORT note and stop | ...>
- In resume mode the gate must not mutate working state.
- Phase gates: <list, or none>

## 8. Execution Policy [optional]

- Dependencies: each task carries `Depends on: <ids | ->` markers (the
  planner owns them); scheduling may not invent dependencies.
- Concurrency: <sequential | bounded(N)>
- Phases:
  | # | Deliverable          | Branch        | Compact after |
  |---|----------------------|---------------|---------------|
  | 1 | <artifacts only>     | <branch>      | yes           |
  | 2 | <implement units>    | <per unit>    | per unit      |

## 9. Unit Contract [optional]

Per unit: branch <pattern> -> re-inject the unit's acceptance criteria
VERBATIM from the canonical source (compaction loses them) -> implement ->
verify by execution -> evidence row (`criterion | MET/PARKED | proof path`)
-> commit <prefix rule>. No criterion is MET without executed evidence.

## 10. Recovery [optional]

- Retries: <N> attempts per failing verification — default 3; effective value
  = min of brief and contract cap. Security failures: 0 — escalate
  immediately.
- No-progress: after <2> consecutive iterations with no durable trace
  (default 2) — rotate strategy, then park.
- On exhaustion classify: independent next unit -> continue; dependent
  units -> BLOCKED; systemic/toolchain -> escalate or abort.
- Anti-Goodhart: when verification fails, do NOT weaken criteria, shrink
  corpora, reinterpret failures as success, or widen scope; preserve the
  failure evidence and park if needed.
- Repository drift is information, not authorization: log every divergence
  from plan assumptions as an assumption — it is not a licence to change
  scope.

## 11. Handoff [recommended]

RUN-SUMMARY.md (or the path named here; written last): run-level terminal
state (SUCCESS/BLOCKED/ESCALATED/EXHAUSTED/ABORT); criterion table
(MET/PARKED | evidence path); branches with `git log --oneline
main..<branch>`; rolled-up DECISIONS.md and BLOCKERS.md items, one human
action each; negative confirmations (<nothing pushed; no PR opened>); brief
path + revision. Ledger: BLOCKERS.md — unit | criterion | why | what
unblocks — authoritative; tasks.md comments are pointers only.

## 12. Termination [required]

- Stop conditions: SUCCESS (all required criteria MET with evidence) |
  BLOCKED (no safe autonomous transition remains) | ESCALATED |
  BUDGET (<time/token limit>) | ABORT (<gate failed>).
- Scope fence: do not start <next epic / checkpoint / ...> under any
  circumstances.

## Appendix: State and Signal Taxonomy

- Unit states: READY IN_PROGRESS DONE PARKED BLOCKED ESCALATED
- Run states: RUNNING SUCCESS BLOCKED ESCALATED ABORTED EXHAUSTED
- Signals trigger transitions (they are not states): NO_PROGRESS
  VERIFY_FAILURE RETRY_EXHAUSTED BASELINE_FAILURE SCOPE_VIOLATION
- PARKED = intentionally not advancing in this run. Reason (free text):
  retry_exhausted | insufficient_evidence | human_decision | budget |
  scope_change. PARKED != DONE. Dispositions are recorded as tasks.md
  comments pointing at the ledger entry — never as checkbox states.

## Minimal Valid Brief (example)

Copy, strip the comments, fill in — roughly 15 lines is a complete brief:

```markdown
# RUN-BRIEF.md (minimal)
<!-- ledger: BLOCKERS.md · finish: RUN-SUMMARY.md (see full template §11) -->

## 1. Envelope
- Mode: unattended. Never wait for a human when a safe autonomous state
  transition exists; record assumptions and continue.

## 2. Mission Reference
- Objective source: TASK.md (owns WHAT and completion semantics).

## 3. Decision Authority
- AUTONOMOUS: implementation details. HUMAN-REQUIRED: schema changes.

## 4. Scope Map
| Resource | Access |
| ./       | write, branch feat/* only |
| docs/    | read |
- Side effects: none. No push, no PR.

## 12. Termination
- Stop: SUCCESS (all TASK.md criteria MET with evidence) | BLOCKED | ABORT.
- Scope fence: nothing beyond TASK.md.
```

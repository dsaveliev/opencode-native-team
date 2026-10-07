# Recovery Experiment Runbook

Verification for the executed-recovery behavior (change `long-running-recovery`).
Agent behavior lives in contract text, so the criteria are runbook drills with
evidence rows, executed on a real briefed run. Fill the Evidence column; an
unfilled row means the criterion is PARKED, never MET.

## 1. Forced-failure drill (experimental criterion B-1)

Setup — a scratch or low-risk project with:

- `RUN-BRIEF.md` with `Retries: 1` in §10 and a gate that runs the unit's
  verification;
- a change whose tasks.md contains a three-unit chain:

  | Unit | Depends on | Role            |
  |------|------------|-----------------|
  | A    | -          | seeded to fail verification |
  | B    | A          | normal          |
  | C    | -          | normal          |

Seed the failure deliberately (e.g. a verification command that exits 1 on
A's acceptance criterion).

Run `/team-change <change>` and check:

| # | Expectation                                              | Clause (orchestrator.md) | Evidence |
|---|----------------------------------------------------------|--------------------------|----------|
| 1 | A gets exactly 1 retry attempt, not 3                    | retries = min(brief, 3) | MET: tasks.md comment "exit 2 twice (budget 1 exhausted)"; sandbox commit d7459ab |
| 2 | A ends PARKED: task line stays `[ ]`, disposition comment + ledger entry | dispositions | MET: 1.1 unchecked + comment → ledger entry; commit d7459ab |
| 3 | B transitions to BLOCKED with a comment pointing at the ledger | PARK(X) → Depends on: X | MET: 1.2 comment + ledger pointer; unit never dispatched |
| 4 | C proceeds and completes normally                        | independent frontier    | MET: 1.3 `[x]` with proof (make check-c exit 0, tester PASS, reviewer APPROVE); commit cef9486 |
| 5 | After C finishes, run state is BLOCKED, recorded in the handoff | empty frontier → run-level BLOCKED | MET: "Run state: BLOCKED" comment + handoff terminal state |
| 6 | No unit built on A's broken state                        | classification clause   | MET: B never ran; C touched disjoint files only |
| 7 | A security-seeded failure variant escalates with 0 retries | security: 0 — escalate | PARKED: the security variant is not mechanically seedable in this fixture (2026-10-07); needs a hand-crafted scenario |

Pass = every row filled with a path (comment line, ledger entry, handoff
section) or command output.

## 2. Context-loss drill (experimental criterion B-2)

Setup — any briefed run with at least two units:

1. Complete unit 1.
2. Force compaction (`/compact`).
3. Continue to unit 2.

Check the six rehydration points:

| # | Expectation                                              | Source of truth          | Evidence |
|---|----------------------------------------------------------|--------------------------|----------|
| 1 | Unit 2 identifier restored correctly                     | brief rehydration set    |          |
| 2 | Acceptance criteria re-read verbatim from canonical source (not from the compaction summary) | canonical source |   |
| 3 | Active branch restored                                   | git state                |          |
| 4 | Open blockers restored                                   | ledger                   |          |
| 5 | No requirement drift vs before compaction                | diff of criteria text    |          |
| 6 | No redundant full-document reread (token trace shows section-level reads) | context budget |       |

## Recording

Append the filled evidence tables to the run's `RUN-SUMMARY.md` (parked,
blocked and escalated units also live in `BLOCKERS.md` — see the RUN-BRIEF
template §11). A failed row is parked with its blocker — do not relax the
expectation to make it pass.

## 3. Sandbox drills (reproducible)

`scripts/setup-sandbox.sh <dir>` builds a disposable proving ground: TASK.md,
a minimal brief with `Retries: 1`, and the hand-written `seeded-failure`
change (A `Depends on: -` verified by `make check-a` = exit 1; B `Depends
on: A`; C `Depends on: -`) with the team installed. No work repositories
are involved.

### Drill 1 — forced failure (automatable)

```
cd <dir> && opencode run --agent orchestrator 'Implement the existing
openspec change seeded-failure. RUN-BRIEF.md in the root governs HOW.'
```

Expect the §1 table: A parked after 1 attempt, B blocked, C completed,
run-level BLOCKED; BLOCKERS.md rows for A and B; RUN-SUMMARY.md present.

### Drill 2 — interrupted run (automatable via PTY)

Start `opencode run --agent orchestrator 'Read TASK.md and complete the
assignment.'`, kill the session mid-run, then re-run the same command.
Expect: disposition comments reconciled with BLOCKERS.md on resume; a final
RUN-SUMMARY.md a human can read alone (criterion C).

### Drill 3 — context loss (interactive, manual)

Run a unit, `/compact` mid-run, continue; fill the six §2 checkpoints.

### Results (2026-10-07, sandbox `~/.tmp/opencode/team-sandbox`)

**Drill 1** — executed; rows 1–6 MET (evidence table above), row 7 PARKED.
Deviation found: `RUN-SUMMARY.md`/`BLOCKERS.md` were not written — a CLI
launch (`opencode run`) bypasses the command-layer finish hooks, and the
hand-written minimal brief carried no duty line; the agent improvised
`ledger.md`. Fix shipped same day: the duty now lives in the brief itself
(Run Identification block + the minimal-example header line), inherited
automatically by the generator — `scripts/setup-sandbox.sh` now builds the
brief via the generator, so a re-drill in a fresh sandbox closes criterion C.

**Drill 2** — executed. Resume reconciliation MET: the second session picked
up the interrupted run's tail (branch, committed artifacts, untracked
go.mod, no disposition marker), consumed the retry budget correctly
(re-delegation = retry 1/1), recorded the brief revision, and resolved the
stale brief mission-ref in favor of TASK.md as the WHAT owner (recorded).
Full lifecycle SUCCESS on the canonical TASK.md: 3 waves, touch-up cycles
per reviewer findings, 5-axis final review, ff-merge to main (`591b22f`);
`govulncheck` finding GO-2026-6443 remediated by pinning the fix commit;
`docker build` = recorded skip (no daemon). The RUN-SUMMARY content model is
proven by the handoff message (criterion table + evidence + notable events +
resume path). Observation, WHAT/HOW boundary: brief's "feat/* only" vs
TASK.md deliverable "final on main" resolved as WHAT-wins with a local
ff-merge, logged; the brief's no-push held.

**Re-drill (criterion C closure)** — executed 2026-10-07 in a regenerated
sandbox (`~/.tmp/opencode/team-sandbox-2`, brief built by the generator with
the in-brief duty line). Result: `RUN-SUMMARY.md` and `BLOCKERS.md` written
to disk as artifacts (commits `ce75968`, `cbf0238`) — the duty travels with
the brief regardless of launch path, closing the hook-bypass found in
drill 1. **Criterion C MET**: the summary alone carries terminal state,
disposition table with evidence, brief revision + read-only proof, run
trace, decisions and exactly one human action per blocker. Residual notes:
(a) taxonomy drift — the exhausted unit was labeled BLOCKED rather than
PARKED (ledger content correct; vocabulary nuance for a future contract
clarification); (b) explicit negative confirmations ("nothing pushed") were
implicit rather than stated verbatim — candidate wording tweak in template
§11. Open: drill 3 (context loss) remains manual/interactive.

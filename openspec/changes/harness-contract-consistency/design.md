# Design

## Context

See proposal.md - Why. Six defects confirmed line-by-line during
planning; none reproduced beyond static reading, all are
mechanism-follows-document fixes. This change repairs the contract
surface itself: documentation vs enforcement, installer vs resolved
templates, fixture vs real schema, generator vs operator intent, test
wiring vs CI.

## Goals / Non-Goals

**Goals:**
- SPEC numbers, validator numbers, and enforcement are one value.
- Installing the framework installs everything its scripts resolve.
- Fixtures exercise the real schema; a mismatch fails loudly.
- Operator-specified brief scope is preserved verbatim.
- Every behavioral test runs in validate.py and CI; spec drift is a CI
  failure via a pinned openspec job.

**Non-Goals:**
- Making adoption/dashboard data reporting honest about partial reads
  (roadmap: evidence/data-honesty change).
- Worktree/process isolation, run identity, receipts.

## Decisions

### D1: SPEC limits derived, not restated

SPEC.md carries the exact numbers from `validate.py` LIMITS, phrased so a
regex can extract them (`orchestrator <= N lines`, `reviewer <= N`,
`tester <= N`, `subagents <= N`). New validator step parses those
numbers and compares to LIMITS — drift fails the build. One direction of
truth (the code), mirrored in docs, checked mechanically.

### D2: Template ships with its generator

`install.sh` copies `examples/RUN-BRIEF.md` into `${TARGET}/examples/`
(both modes), because `gen-run-brief.py` resolves
`<script dir>/../examples/RUN-BRIEF.md`. `commands/team-brief.md`
resolves the generator with the same precedence as the dashboard script
(project `.opencode/scripts/`, then global). Validator asserts the
resolved template exists in-repo, so a future move breaks CI, not a
user's run.

### D3: Fixture schema equals real schema

The adoption fixture's CREATE TABLE mirrors every column
`load_sessions` selects (including `title`), and its window checks assert
the exact inserted row count. A swallowed schema error then yields a
loud count mismatch instead of a green "non-empty".

### D4: Operator scope is data, not a template

`scope_lines` emits the operator's access verbatim for every row,
including `./=` (the canonical write string stays only the no-rows
default via marker replacement). `test-gen-run-brief.py` gains a
`./=read` regression case.

### D5: Wire everything into CI

`validate.py` step [7] additionally runs `test-gen-run-brief.py`. CI
gains a second step: `npm i -g openspec@1.14.0 && openspec validate
--specs` (pin = the locally verified CLI; bump is a deliberate change).
Pinned because an unpinned CLI can fail PRs on unrelated release churn.

### D6: Amartifact honesty

`dashboard-session-control/proposal.md` Impact is corrected to name the
launcher/serve changes the pivot actually made (it currently claims none
change). Done before that change is archived.

## Archive-order precondition

```
1. openspec archive dashboard-session-control   (creates "Verified process stop")
2. openspec archive dashboard-control-hardening (modifies it + localhost serve)
3. openspec archive harness-contract-consistency (this change; deps on 1+2 deltas)
```
Reverse order fails spec sync: this change's MODIFIED blocks reference
requirements the earlier deltas create.

## Risks / Trade-offs

- The SPEC regex couples docs to a phrasing; a reworded SPEC line fails
  the build (by design — fix the number, not the check).
- The openspec pin blocks on CLI regressions until bumped; bumping is a
  one-line PR, acceptable versus unpinned flakiness.
- Fixture count assertions make the adoption test stricter — any future
  column drift fails immediately (intended).

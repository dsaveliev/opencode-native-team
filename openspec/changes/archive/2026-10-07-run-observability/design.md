# Design

## Context

A shipped the run-brief layer; B shipped executed recovery. Both reference
artifacts that do not exist: the disposition ledger and the end-of-run
handoff. The orchestrator contract is at 114/115 lines (its cap), the
dashboard parses tasks.md checkboxes but not comments, and the B runbook's
evidence tables are empty until a real briefed run happens. User-locked
decisions (2026-10-07): C before D; dashboard panel deferred; sandbox setup
committed to the repo.

## Goals / Non-Goals

**Goals:**

- Close B's dangling references: BLOCKERS.md and RUN-SUMMARY exist as
  contracts the commands instruct and the runbook verifies.
- One source-of-truth ladder for run state; no three-way divergence.
- Mechanical guard against template drift (validate.py).
- Reproducible test data without work tasks: a committed sandbox script.

**Non-Goals:**

- Dashboard disposition panel (deferred with a named follow-up).
- Orchestrator contract edits (cap; precedent B-D6 — the duty lives in
  commands and the brief).
- Preset files, YAML manifests (D-territory or later).

## Decisions

### D1. The duty lives in commands, not the orchestrator

`/team` and `/team-change` each gain a two-line finish hook ("on finish of a
briefed run: write the summary per §11; ledger = BLOCKERS.md"). The
orchestrator's existing Run Brief block already says "record its revision in
run outputs" and "dispositions … pointing at the ledger" — the commands now
name what the ledger and the summary concretely are.

### D2. Briefed runs only (locked precedent from B)

Unbriefed runs keep today's flow: DECISIONS.md, no summary, no ledger. The
compatibility criterion of A/B stays intact.

### D3. RUN-SUMMARY at repo root, committed by the team lead

Not `tmp/` (gitignored — the morning artifact must be durable and reviewable
in git), not outside the repo (project boundary: artifacts stay inside).
Location is overridable via the brief's §11 slot.

### D4. BLOCKERS.md schema: a 4-column markdown table

`unit | criterion | why | what unblocks` — free text, lazily created on the
first entry. No tooling reads it mechanically in this change (dashboard
deferred); it is written for humans and for the resume reconciliation.

### D5. Source-of-truth ladder + reconciliation hook

BLOCKERS.md > tasks.md comments > RUN-SUMMARY. B's resume clause already
reconciles comments with "the ledger"; this change defines that term.

### D6. validate.py: canonical-heading check, single list

One constant list of canonical headings; loop + report missing. The check is
self-verifying: the current template passes (proof = green run); a temporary
deletion proves the failure path during the task.

### D7. Sandbox as committed infrastructure

`scripts/setup-sandbox.sh <dir>`: git-init a disposable repo, copy
`examples/TASK.md`, write a minimal filled RUN-BRIEF (retries 1), scaffold the
`seeded-failure` change via the openspec CLI (A `Depends on: -` verified by
`make check-a` which exits 1; B `Depends on: A`; C `Depends on: -`), install
the team via `install.sh`, initial commit. Runbook §3 documents three drills:
forced-failure (automatable headless), interrupted-run (kill + resume,
automatable via PTY), context-loss (interactive `/compact` — manual). The
sandbox serves B-runbook evidence, criterion C, and later D's generator
smoke test.

## Risks / Trade-offs

- [Summary staleness if the run dies mid-flight] → Mitigation: summary is
  written last; if absent, BLOCKERS.md + git remain the truth; the interrupted
  drill checks exactly this.
- [Ledger/comment divergence in practice] → Mitigation: ladder + resume
  reconciliation (B clause) + drill 2 verifies.
- [Setup script bit-rots against install.sh changes] → Mitigation: drill §3
  re-run is cheap (script is idempotent, target dir disposable); CI does not
  depend on it.

## Migration Plan

Additive: hooks, docs, scripts. Unbriefed installs unchanged. Rollback =
revert this change's edits.

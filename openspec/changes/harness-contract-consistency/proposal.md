# Proposal

## Why

A five-axis audit of the repo found contract-consistency defects: the
documented contract limits drift from the enforced ones, the installer
ships a generator without the template it resolves, the adoption fixture
silently tests an empty result, the brief generator silently widens an
operator's requested access, and the run-brief behavioral test is wired
into neither the validator nor CI. The dashboard-session-control
proposal still denies the launcher semantics its own implementation
changed. Each defect makes a written rule disagree with the mechanism
that enforces it — the exact failure class this harness exists to remove.

## What Changes

- SPEC.md contract limits match `validate.py` LIMITS verbatim; a new
  validator step parses the SPEC line and fails on any future drift
  (rule becomes mechanism).
- `install.sh` ships `examples/RUN-BRIEF.md` next to the generator that
  resolves it; `commands/team-brief.md` resolves the generator like the
  dashboard (project-local, then global); validator asserts the template
  the generator resolves exists.
- Adoption fixture schema gains the `title` column; its window checks
  assert an exact row count, so a schema mismatch fails loudly instead
  of "non-empty" passing on a swallowed error.
- `gen-run-brief.py` scope rows keep the operator's access verbatim
  (`--scope ./=read` stays read); a regression case pins it.
- `scripts/test-gen-run-brief.py` joins the validator suite; CI gains a
  pinned-version openspec job (`openspec validate --specs`) so spec drift
  fails at PR time.
- dashboard-session-control proposal Impact corrected to describe the
  launcher pivot actually shipped.
- Archive-order precondition (session-control -> hardening -> this
  change) recorded in design.md and pinned by a task.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `plugin-integrations`: installed artifacts and template resolution
  become consistent and mechanically checked.

## Impact

- Files: `SPEC.md`, `scripts/validate.py`, `install.sh`,
  `commands/team-brief.md`, `scripts/gen-run-brief.py`,
  `scripts/test-dashboard-adoption.py`, `scripts/test-gen-run-brief.py`,
  `.github/workflows/ci.yml`,
  `openspec/changes/dashboard-session-control/proposal.md`.
- No runtime behavior of the team loop changes; this change makes the
  written contract and its enforcement agree.
- Not in scope: data honesty (PARTIAL/UNAVAILABLE), evidence truncation,
  run identity, receipts — roadmap changes that follow this one.

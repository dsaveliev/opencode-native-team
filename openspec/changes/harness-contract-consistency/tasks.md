# Tasks

## 1. Contract surface repairs

- [x] 1.1 A: SPEC.md limits rewritten to the validated values
  (orchestrator 140, reviewer 60, tester 55, subagents 40) in
  regex-extractable form; validate.py gains a step parsing them and
  comparing to LIMITS — mismatch = FAIL. Verify: `python3
  scripts/validate.py` green; deliberately editing the SPEC number fails
  the new step (revert after).
- [x] 1.2 B: install.sh copies examples/RUN-BRIEF.md to
  ${TARGET}/examples/RUN-BRIEF.md in both modes; validate.py asserts
  gen-run-brief.py's DEFAULT_TEMPLATE resolves inside the repo. Verify:
  `./install.sh --global && test -f
  ~/.config/opencode/examples/RUN-BRIEF.md`; validate green.
- [x] 1.3 B: commands/team-brief.md resolves the generator project-first
  (`.opencode/scripts/gen-run-brief.py`), global fallback
  (`~/.config/opencode/scripts/…`); skips with a message when absent.
  Verify: `rg 'gen-run-brief' commands/team-brief.md` shows both paths.
- [x] 1.4 C: adoption fixture CREATE TABLE gains title TEXT (full
  column parity with load_sessions); window checks assert the exact
  inserted row count. Verify: `python3 scripts/test-dashboard-adoption.py`
  green; dropping the column again fails the count check (revert after).
- [x] 1.5 D: scope_lines keeps operator access verbatim for ./= rows;
  test-gen-run-brief.py gains a `--scope ./=read` -> "read" case (not
  "write"). Verify: `python3 scripts/test-gen-run-brief.py` green.
- [x] 1.6 E: validate.py [7] also runs scripts/test-gen-run-brief.py.
  Verify: validate green; temporarily renaming the test fails [7]
  (revert after).
- [x] 1.7 E: CI gains `npm i -g openspec@1.14.0 && openspec validate
  --specs`. Verify: `.github/workflows/ci.yml` shows the step; local
  `openspec validate --specs` green.
- [x] 1.8 F: dashboard-session-control proposal.md Impact corrected —
  launcher/serve pivot named explicitly (no "no launcher/window changes"
  claim). Verify: `openspec validate dashboard-session-control` green;
  `rg 'launcher' .../proposal.md` shows the corrected bullet.
- [x] 1.9 Precondition: archive order (session-control -> hardening ->
  this change) noted in design.md (done) and re-verified at archive time.
  Verify: `rg 'Archive-order' openspec/changes/harness-contract-consistency/design.md`.

## 2. Bugs found along the way

- [x] 2.1 Process bug found while proving the 1.4 guard: a `git checkout
  --` used to revert a deliberate drift deleted the uncommitted fixture
  edits in the same file (edits restored, double-verified). Fix/lesson:
  prove guards with in-memory reverts (temp copy), never git checkout on a
  dirty file. Verify: adoption test PASSED again after restore; guard
  mechanism proven directly (0 sessions without the title column).

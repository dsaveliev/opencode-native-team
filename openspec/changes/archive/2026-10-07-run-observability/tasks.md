# Tasks

## 1. Command finish hooks

- [x] 1.1 `commands/team.md`: after the run-brief paragraph add the finish
      hook (+2 lines) — on finish of a briefed run write the summary per the
      brief's §11; the dispositions ledger is BLOCKERS.md. Verify: diff adds
      ≤ 2 lines, dashboard pre-flight untouched.
- [x] 1.2 `commands/team-change.md`: same finish hook (+2 lines). Verify:
      diff adds ≤ 2 lines.
      Proof: git diff --numstat = `2 0 commands/team.md` (hook names RUN-SUMMARY per §11 + BLOCKERS.md).
      Proof: git diff --numstat = `2 0 commands/team-change.md`.

## 2. Template and validation

- [x] 2.1 `examples/RUN-BRIEF.md` §11: concretize to the RUN-SUMMARY contract
      (terminal state, criterion table, branch logs, rolled-up ledgers, one
      action each, negative confirmations, brief path+revision; ledger =
      BLOCKERS.md with its schema). Verify: §11 names RUN-SUMMARY.md and
      BLOCKERS.md with the 4-column schema.
- [x] 2.2 `scripts/validate.py`: canonical-heading check for
      examples/RUN-BRIEF.md (header blocks, 12 numbered sections, taxonomy
      appendix). Verify: green run on the current template; temporary removal
      of one heading fails with the heading named, then restored.
      Proof: §11 names RUN-SUMMARY.md with all 7 content items + BLOCKERS.md 4-column schema; validate [6b] green.
      Proof: green run ALL CHECKS PASSED; negative path verified — deleting the §7 heading line -> "FAIL examples/RUN-BRIEF.md: canonical heading missing: ## 7." + VALIDATION FAILED; heading restored, 22 ## headings, green again.

## 3. Sandbox proving ground

- [x] 3.1 `scripts/setup-sandbox.sh`: disposable repo with TASK.md, minimal
      filled brief (retries 1), seeded-failure change (A/- with make check-a
      exit 1; B/A; C/-), team installed via install.sh, initial commit.
      Verify: script runs clean end-to-end into a scratch dir; openspec
      validate seeded-failure passes there.
      Proof: `scripts/setup-sandbox.sh ~/.tmp/opencode/team-sandbox` -> "sandbox ready ... (change valid)"; 5 agents + 2 commands installed; initial commit 9867b86.

## 4. Documentation

- [x] 4.1 `docs/design-decisions.md` #17 (run observability artifacts: summary,
      ledger, source-of-truth ladder, mechanical check, sandbox) in the
      existing format. Verify: format matches; 1–16 untouched.
- [x] 4.2 `docs/recovery-experiment.md`: recording section now points at
      RUN-SUMMARY.md + BLOCKERS.md; add §3 Sandbox drills (forced-failure,
      interrupted, context-loss) with expectations per drill. Verify: both
      edits present.
- [x] 4.3 `README.md`: extend the run-briefs section with 2–3 lines (summary,
      ledger, sandbox script). Verify: ≤ 4 added lines, links resolve.
      Proof: `## 17. Run observability artifacts` after #16; Decision/Rejected/Rationale; 1-16 untouched.
      Proof: Recording -> RUN-SUMMARY.md + BLOCKERS.md; §3 Sandbox drills with 3 drills (drill 1 automatable command included).
      Proof: README +3 lines naming RUN-SUMMARY.md, BLOCKERS.md, setup-sandbox.sh; recovery-experiment.md §3 link.

## 5. Integration checks

- [x] 5.1 `python3 scripts/validate.py`. Verify: ALL CHECKS PASSED, exit 0.
- [x] 5.2 RUN-SUMMARY structure walkthrough: map each content item of spec
      requirement "Run summary artifact" to the §11 text and the finish
      hooks. Record as `[x]` proof.
- [x] 5.3 `openspec validate run-observability --strict`. Verify: exit 0.

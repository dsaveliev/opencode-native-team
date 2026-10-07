# Tasks

## 1. Planner dependency markers

- [x] 1.1 `agents/planner.md`: replace the free-text dependency sentence with
      the explicit marker convention — each task ends with
      `Depends on: <ids | ->` (machine-readable; never prose). Verify: the
      contract contains the marker format; `wc -l agents/planner.md` ≤ 40;
      `python3 scripts/validate.py` step [1]-[3] green.
      Proof: planner.md:33 carries the marker format line; `wc -l` = 38 ≤ 40
      (net +1 line); validate.py green — see 5.1.

## 2. Orchestrator recovery

- [x] 2.1 `agents/orchestrator.md`: add Recovery/Propagation/Resume clauses to
      the Run Brief block (~8 lines): retries = min(brief, 3); security 0 —
      escalate; on exhaustion classify (independent next → continue; only
      dependents → BLOCKED; systemic → escalate); PARK(X) → `Depends on: X`
      tasks BLOCKED; empty frontier → run-level BLOCKED; missing marker →
      DECISIONS entry, treat as dependent; resume reconciles disposition
      comments with the ledger. Verify: block contains all seven clauses;
      `wc -l agents/orchestrator.md` ≤ 115.
      Proof: all seven clauses grep-confirmed (orchestrator.md:36-42:
      min(brief, 3); security 0; independent next unit; Depends on: X;
      empty frontier; Missing marker; reconcile disposition);
      `wc -l` = 114 ≤ 115.
- [x] 2.2 `agents/orchestrator.md`: always-on No-progress directive in Main
      Directive (+2 lines): every iteration leaves a durable trace; 2
      trace-less iterations → rotate strategy or park. Verify: directive
      present outside the Run Brief block (unconditional).
      Proof: orchestrator.md:86-87 (Main Directive section, ~45 lines below
      the Run Brief block — unconditional).
- [x] 2.3 Raise the orchestrator cap 105 → 115: SPEC.md cap line with updated
      rationale; `scripts/validate.py` LIMITS in the same edit. Verify:
      SPEC.md diff touches only the cap lines; validate step [3] green.
      Proof: SPEC.md cap lines now read "orchestrator ≤ 115 lines (dual-layer
      wiring + run-brief overlay with executed recovery)"; validate.py
      LIMITS = {"orchestrator": 115, "reviewer": 46} — same-edit consistency
      (no 90/96-style drift); step [3] green in 5.1.

## 3. Template defaults

- [x] 3.1 `examples/RUN-BRIEF.md` §10: make defaults explicit — retries
      default 3 (effective = min of brief and contract), no-progress
      threshold default 2, security failures 0. Verify: section contains all
      three defaults.
      Proof: §10 now carries "default 3; effective value = min of brief and
      contract cap", "default 2" (no-progress), "Security failures: 0".

## 4. Documentation

- [x] 4.1 `docs/design-decisions.md`: add #16 (executed recovery: min-retry,
      exhaustion classification, propagation, global no-progress guard) in
      the existing format. Verify: entry follows the Decision / Rejected
      alternatives / Rationale shape; 1–15 untouched.
      Proof: `## 16. Executed recovery (change long-running-recovery)` after
      #15; full Decision / Rejected alternatives / Rationale structure;
      entries 1–15 unmodified.
- [x] 4.2 Create `docs/recovery-experiment.md`: runbook with two criteria —
      (1) forced failure: setup (brief retries 1, chain A(-)→B(A)→C(-)),
      steps, expected dispositions, evidence table; (2) context loss:
      compact drill with the six rehydration checkpoints. Verify: file
      exists with both checklists.
      Proof: file written — section 1 (7-row forced-failure table incl.
      security variant, clause references to orchestrator.md), section 2
      (6 rehydration checkpoints), recording rules (PARKED never MET).

## 5. Integration checks

- [x] 5.1 `python3 scripts/validate.py`. Verify: ALL CHECKS PASSED, exit 0.
      Proof: "ALL CHECKS PASSED", exit 0 (incl. step [3] line limits at the
      new 115 cap with the 114-line orchestrator).

- [x] 5.2 Forced-failure textual walkthrough per runbook section 1: map each
      contract clause to the expected disposition in the A/B/C chain;
      record the mapping as the `[x]` proof. (Live-run evidence lands with
      the first real briefed run — runbook stays the checklist.)
      Proof: all 7 runbook rows map 1:1 to the Recovery clauses verified in
      2.1 — row 1 `min(brief,3)` → A gets 1 attempt (brief retries 1);
      row 2 dispositions-comment + ledger → A stays `[ ]` PARKED; row 3
      `PARK(X) → Depends on: X` → B BLOCKED; row 4 independent frontier →
      C proceeds; row 5 empty frontier → run-level BLOCKED in handoff;
      row 6 classification → nothing builds on A; row 7 `security: 0` →
      0-retry escalate variant. Live evidence deferred per design D7.

- [x] 5.3 `openspec validate long-running-recovery --strict`. Verify: exit 0.
      Proof: "Change 'long-running-recovery' is valid", exit 0.

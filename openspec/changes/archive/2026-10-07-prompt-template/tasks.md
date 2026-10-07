# Tasks

## 1. Template — `examples/RUN-BRIEF.md`

- [x] 1.1 Write the template: immutable-categories header (MAY constrain /
      MUST NOT grant or redefine acceptance), monotonic merge rules (intersect capabilities,
      min budgets, any-DENY), immutability/versioning block (read-only during run,
      revision recorded), and the 12 canonical sections — Envelope, Mission
      Reference, Decision Authority, Scope Map, Source Precedence, Context Budget
      (incl. rehydration set), Gates, Execution Policy, Unit Contract, Recovery,
      Handoff, Termination — each with bracketed slots and required/optional marker.
      Verify: `rg -c '^## ' examples/RUN-BRIEF.md` reports 12 canonical sections
      plus header sub-blocks; a human reads the whole file in under 5 minutes.
      Proof: rg -c '^## ' = 22 = 3 header sub-blocks + 12 canonical + Appendix +
      Minimal-brief section + 5 headings inside the fenced example; exit 0.
- [x] 1.2 Add the unit/run state and signal taxonomy block (design D3) and a
      minimal-valid-brief example (~15 lines: header + scope + stop conditions) at
      the bottom. Verify: the minimal example contains no optional sections and
      `bash -n`-style eyeball confirms every slot in it is fillable without the
      optional ones.
      Proof: `## Appendix: State and Signal Taxonomy` present (unit/run states,
      signals, PARKED semantics); fenced `## Minimal Valid Brief (example)` uses
      only sections 1/2/3/4/12 (all required-core), zero optional sections.

## 2. Command hooks

- [x] 2.1 `commands/team.md`: after the TASK.md-precedence block add the opt-in
      lines — if `RUN-BRIEF.md` exists in the repo root, read it first; its
      sections are an execution-policy overlay (HOW only; may narrow, never
      grant); read-only during the run. Verify: diff adds ≤ 4 lines; existing
      dashboard pre-flight and TASK.md semantics untouched.
      Proof: `git diff --numstat` = `4 0 commands/team.md` (additions only,
      dashboard pre-flight and TASK.md block byte-identical).
- [x] 2.2 `commands/team-change.md`: same overlay lines with the resume nuance —
      hydrate change state first, then apply the brief overlay. Verify: diff adds
      ≤ 3 lines; the "implement existing change" mode text unchanged otherwise.
      Proof: `git diff --numstat` = `3 0 commands/team-change.md` (additions
      only, placed after the Mode line; all other mode text unchanged).

## 3. Orchestrator contract

- [x] 3.1 Add the conditional run-controls block (~10 lines) to
      `agents/orchestrator.md`: if `RUN-BRIEF.md` exists it constrains HOW only
      (monotonic; grant attempts are no-ops); after any compaction, rehydrate from
      the brief's set (current unit, AC verbatim from canonical source, branch,
      blockers); dispositions are tasks.md comments, `PARKED != DONE`; record the
      brief's revision in run outputs. Verify: block ≤ 12 lines and contains all
      five clauses.
      Proof: `## Run Brief` section = 12 lines incl. blanks; clauses present:
      HOW-only+no-ops (bullet 1), read-before-first-write + revision recording
      (bullet 2), rehydration set (bullet 3), dispositions + PARKED != DONE
      (bullet 4).
- [x] 3.2 Trim redundant orchestrator lines (~4: overlap between Resources /
      Prohibited bullets) and update the SPEC.md contract cap for the orchestrator
      from ≤ 90 to ≤ 105 with a one-line rationale. Verify: `wc -l
      agents/orchestrator.md` ≤ 105; SPEC.md diff touches only the cap line.
      Proof: `wc -l agents/orchestrator.md` = 105; SPEC.md diff = the two cap
      lines only (90→105 + rationale). Note: `scripts/validate.py` LIMITS
      raised 96→105 in step — mechanical enforcement of the same SPEC cap;
      without it 5.1 would fail (SPEC said 90, validator already allowed 96 —
      pre-existing drift, now consistent).

## 4. Documentation

- [x] 4.1 `docs/design-decisions.md`: add decision #14 (run brief as the fourth
      artifact layer; distributed run state stays distributed — standardize the
      protocol, not the storage) and #15 (monotonic run control — the brief may
      narrow, never grant; immutable during the run), each in the existing
      Decision / Rejected alternatives / Rationale format. Verify: entries follow
      the format of the existing 13 and renumber nothing.
      Proof: `## 14. Run brief as a fourth artifact layer` and `## 15. Monotonic
      run control` appended after #13; both carry Decision / Rejected
      alternatives / Rationale; entries 1–13 untouched.
- [x] 4.2 `README.md`: add a "Run briefs (long-running runs)" section near the
      `/team-change` usage — what a brief is, the HOW-only rule, the drop-in usage
      (copy template, fill slots), and the queued follow-ups (recovery,
      observability). Verify: markdown links to `examples/RUN-BRIEF.md` resolve;
      section ≤ 20 lines.
      Proof: section at README line 101, `awk`-measured 17 lines; `test -f
      examples/RUN-BRIEF.md` OK.

## 5. Integration checks

- [x] 5.1 Run `python3 scripts/validate.py` and the repo's other CI-side checks
      (`bash scripts/check-model-routing.sh` where applicable). Verify: exit 0.
      Proof: `python3 scripts/validate.py` → ALL CHECKS PASSED, exit 0 (after
      moving the temporary Russian review copies out of the repo tree —
      validate.py's Cyrillic check scans tmp/ despite .gitignore; copies now at
      `~/.tmp/opencode/prompt-template-ru/`). `check-model-routing.sh` not
      applicable: requires a `<run-dir>` from a live team run; usage error, not
      a repo-state failure.
- [x] 5.2 Experimental criterion A walkthrough, evidence recorded: (a) brief
      absent — confirm `/team` and `/team-change` texts change only by the opt-in
      lines, no mandatory interaction added; (b) brief present — in a scratch
      project, drop a filled minimal brief and confirm the command text directs
      reading it as an overlay before work. Verify: both outcomes noted with
      evidence in the task line (`[x]` proof).
      Proof: (a) `git diff --numstat` = `4 0 commands/team.md`, `3 0
      commands/team-change.md`, both additions strictly conditional
      (`if RUN-BRIEF.md exists`, 1 occurrence each); dashboard pre-flight and
      TASK.md precedence byte-identical. (b) scratch project
      `~/.tmp/opencode/runbrief-scratch/` holds a filled minimal brief;
      directive chain present: team.md:30, team-change.md:23 (read/apply before
      work), orchestrator.md:25 (conditional overlay block).
- [x] 5.3 `openspec validate prompt-template --strict`. Verify: exit 0.
      Proof: "Change 'prompt-template' is valid", exit 0.

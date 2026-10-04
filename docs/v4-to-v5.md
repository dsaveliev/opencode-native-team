# v4 → v5: What Changed and Why

Based on four controlled experiments (barebone, +skills, +openspec, combined).

## v1 (barebone) — The Baseline

- 5 agents, ~20 lines each, no external layers
- Result: 15/15 judge (15-check battery of that era; the v5 judge has 18 checks), 53.9% weighted coverage (main untested), 43 min, 344k input
- Gap: no enforcement — skills available but never invoked

## v2 (+skills) — Closing the Enforcement Gap

- Added: mandatory `skill` tool invocations per phase
- Result: 71.9% coverage (+18pp), main 16.3%, 39 min (faster than v1!), +22% input
- Insight: discipline didn't slow things down — it sped them up by reducing rework

## v3 (+openspec) — Closing the Audit Gap

- Added: change-cycle (proposal/design/tasks → validate → [x] → status)
- Result: 69.5% coverage (+16pp), 44 min, best commit traceability (18 task-labeled commits)
- Gap: main still untested — process doesn't force testability

## v4 (combined) — Both Layers Together

- Added: artifact hierarchy (openspec = single plan), evidence-based [x], fail-loud
- Result: **91.5% coverage** (+38pp!), 2 security bugs caught, 81 min, 521k input
- Problems discovered:
  1. Main still 0% — "main testable" directive lost during contract composition
  2. Shutdown test block took 28 min (25% of total) — evidence format provoked
     exhaustive test matrices
  3. Tester dispatch rejected by environment (external_directory) — 3 min lost + retry

## v5 — Fixes All Known Issues

| Change | Fixes | Expected Impact |
|---|---|---|
| "Main testable" in base contract (not skill appendix) | v4 main 0% | main > 70% |
| Skill mapping table (deterministic dispatch) | v2-v4 ad-hoc selection | reproducibility ±10% |
| Edge cases in task acceptance criteria | overflow bug latent 28 min | defects caught in red phase |
| Per-task light review (2 axes) | single final review = late discovery | fix latency < 5 min |
| Parallel read-only delegation (reviewer ∥ tester) | sequential review-then-test | −8-10 min |
| Test task timeout (5 min) | v4 shutdown block 28 min | −10-15 min |
| Artifacts inside repo only | external_directory rejection | 0 retries |
| Distilled briefs for subagents | each re-reads TASK.md | −10-15% input |
| Model routing (planner/tester on fast) | all on main model | −15-20% input |
| Task reference in commit messages | v4 lost traceability | readable git history |
| Delegation markers in tasks.md | parent silence 15+ min confused monitoring | observability |
| openspec validate after every commit | drift detected only at end | drift < 1 min |

## Projected v5 Metrics

| Metric | v1 | v4 | v5 target |
|---|---|---|---|
| Judge | 15/15 | 15/15 | 15/15 |

  (15-check battery; the v5 judge has 18 checks — compare by category, not raw score)
| Coverage (weighted) | 53.9% | 91.5% | > 93% |
| Main (cmd) | 0% | 0% | > 70% |
| Time | 43 min | 81 min | ≤ 55 min |
| Input tokens | 344k | 521k | ≤ 450k |
| Sessions | 8 | 13 | ≤ 10 |
| Security bugs caught | — | 2 | ≥ 2 |
| Reproducibility | ±25% | — | ±10% |

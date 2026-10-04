# Design Decisions

Thirteen decisions made in the design of the native-team pattern, each with
rationale and rejected alternatives. Derived from empirical data across four
controlled experiments.

## 1. One primary + four subagents (not peer-to-peer, not nested)

**Decision:** Strict two-level hierarchy. The orchestrator is the single context hub.

**Rejected alternatives:**
- All agents primary — no single state holder, conflicting contexts.
- Nested subagents (coder calls tester) — responsibility quickly blurs.

**Rationale:** The orchestrator is the only agent that sees the full transcript,
so cause-effect relationships ("review feedback → fix → commit") never get lost.

## 2. permission.task deny-by-default

**Decision:** `"*": "deny"` + explicit allow for exactly 4 roles.

**Rationale:** Structural protection against spontaneous delegation to external
agents. Predictability over flexibility.

## 3. Planner and reviewer are read-only

**Decision:** Both roles deny `edit` permission.

**Rationale:** Separation of "think" and "do". An analyst who can edit files
becomes an implementer, and planning merges with execution. A reviewer who can't
write is forced to formulate findings as text — which becomes an artifact for
the coder to act on.

## 4. Reviewer temperature = 0.1

**Decision:** Only role with an explicitly pinned temperature.

**Rationale:** Review is maximally deterministic (criteria matching). Creativity
is harmful here. Other roles keep defaults (coder needs solution variety).

## 5. Git commit authority stays with the orchestrator

**Decision:** coder/tester never commit; only the team lead does.

**Rationale:** "Atomic commit = one meaningful step" requires visibility of the
entire step, and a subagent only sees its own delegation.

## 6. Planner returns text, doesn't write PLAN.md

**Decision:** Subagent without write access returns the plan; orchestrator
materializes and commits it.

**Rationale:** Single author of file artifacts — uniform style in git history.

## 7. English contracts (v5)

**Decision:** v5 contracts are in English for the public repository.

**Rationale:** Broader applicability. The original experiments used Russian
contracts; the pattern is language-agnostic.

## 8. No model pinning in v1 (experiment), routing in v5 (production)

**Decision:** v1 fixed all roles on the same model to isolate the pattern variable.
v5 routes: planner/tester on fast model, coder/reviewer on main model.

**Rationale:** Experiment needed controlled variables. Production optimizes cost.

## 9. No inter-session memory — deliberately

**Decision:** v1 is a pure pipeline. State lives in git (commits) and artifacts
(DECISIONS.md), not in hidden stores.

**Rationale:** Full reproducibility and git history = execution journal. The gap
is closed by layers (openspec artifacts as external memory), not by the pattern.

## 10. Contracts ~20 lines each (v1) to ~60 lines (v5)

**Decision:** Each agent has one responsibility, described concisely.

**Rationale:** Long prompts dilute priorities; short contracts + hard permissions
work better. v5 doubled orchestrator length (dual-layer wiring) — that's the
deliberate ceiling; beyond it, mechanics move to layers.

## 11. Fail-loud contracts (from v4)

**Decision:** "If skill/CLI unavailable — log to DECISIONS.md, continue on known
principles; do not stay silent."

**Rationale:** In headless mode, silent failures mean indefinite hangs.
Empirical: v4's tester dispatch was rejected by the environment; the orchestrator
logged it, retried, and succeeded — the failure was visible, the pipeline survived.

## 12. No plugin mechanism

**Decision:** Native is not an opencode plugin. No TypeScript, hooks, or npm.

**Rationale:** The entire mechanism must be git-versioned, human-readable in a
minute, and editable without rebuilding. The trade is "mechanics → discipline",
which the experiments justified economically (344k input vs 5.6M for the most
mechanized participant).

## 13. Skill mapping table (v5 addition)

**Decision:** A deterministic dispatch table (which skill at which openspec stage)
embedded in the orchestrator contract.

**Rationale:** In v2–v4, skill selection was ad-hoc — the same task produced
different skill sets. A mapping table removes this variance completely, the
cheapest remaining reproducibility lever.

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

**Decision:** `"*": "deny"` + explicit allow for exactly 4 roles. All subagents
also carry `task: { "*": "deny" }` to prevent nested delegation.

**Rationale:** Structural protection against spontaneous delegation. In opencode,
most permissions default to `allow` — without explicit denies, any subagent can
spawn sub-subagents.

**Note:** `external_directory: { "*": "deny" }` converts the environment's
auto-reject (headless mode) into a deterministic, immediate denial. This doesn't
change the outcome (the v4 tester was auto-rejected either way) but makes the
failure mode predictable and debuggable. The actual v4 fix is the contract
text: "all artifacts inside the repo, temp files in ./tmp/".

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

## 14. Run brief as a fourth artifact layer

**Decision:** An optional, operator-authored `RUN-BRIEF.md` in the project root
(upgraded from `examples/RUN-BRIEF.md`) constrains how a run executes: scope
fences, budgets, gates, recovery policy, handoff. Run state stays distributed —
`tasks.md` = intended work, git = execution history, ledgers = decisions and
blockers, the summary = run-level state. We standardize the protocol, not the
storage: no unified `run-state.md`.

**Rejected alternatives:**
- A single `run-state.md` — one file, muddled semantics; each artifact owning
  one semantic survived compaction and human review better in the E1 run.
- Expanding TASK.md with run-control sections — mixes WHAT and HOW; TASK.md
  stays fully about what to build.

**Rationale:** The E1 overnight run proved the layer empirically (197-line
brief over `/team-change`, zero operator interventions). Opt-in file
convention keeps default behavior byte-identical when no brief is present.

## 15. Monotonic run control

**Decision:** The brief may narrow execution, never widen it: capabilities are
the intersection of runtime permissions, project policy, role permissions and
the brief's scope; numeric budgets take the minimum across levels; a side
effect denied by any layer is denied. The brief is read-only during the run
(loaded before the first write, revision recorded); editing it mid-run starts
a new run. It never enters the WHAT domain — requirements, acceptance
semantics and dependency direction belong to TASK/OpenSpec and the planner.

**Rejected alternatives:**
- A precedence ladder (user > brief > contracts > defaults) — a higher-ranked
  source could widen what a lower layer denies; intersection cannot.
- A rules engine enforcing brief content — content varies per run; the outer
  layers are already enforced mechanically by opencode permissions, and the
  brief is trusted operator input, not agent output.

**Rationale:** Matches opencode's own permission semantics (frontmatter denies
beat top-level allows). Closes the self-weakening loop — an agent that failed
verification cannot relax its own policy and retry.

## 16. Executed recovery (change long-running-recovery)

**Decision:** Briefed runs execute the brief's recovery policy as contract
clauses: effective retries = min(brief, 3); security-relevant failures get 0
retries and escalate; exhaustion is classified (independent next unit →
continue, only dependents → BLOCKED, systemic → escalate) instead of blindly
moving on; PARK(X) propagates BLOCKED to every `Depends on: X` task while the
independent frontier continues, and an empty frontier leaves the run at
run-level BLOCKED. The planner emits machine-readable `Depends on:` markers.
A global, always-on no-progress guard requires every iteration to leave a
durable trace (task / evidence / implementation / decision / blocker state);
two trace-less iterations force a strategy rotation or a park.

**Rejected alternatives:**
- Recovery machinery in all runs — breaks the no-brief compatibility
  criterion of the run-briefs spec; only the no-progress guard is global.
- A dedicated recovery subagent — no new roles; recovery is orchestration,
  not implementation.
- Automated tests for the recovery behavior — it lives in contract text; the
  runbook (`docs/recovery-experiment.md`) carries the verification on a real
  run instead.

**Rationale:** The two empirically observed failure modes of long runs —
contaminated continuation (next unit on a broken base) and death-spiral
retries — are closed by classification + propagation; spin without progress
is closed by the durable-trace guard. `min`-merge keeps the monotonic run
control of decision #15 intact.

## 17. Run observability artifacts (change run-observability)

**Decision:** Briefed runs end with `RUN-SUMMARY.md` (terminal state, criterion
table with evidence paths, branch logs for human push review, rolled-up
ledger items with one human action each, negative confirmations, brief path +
revision; written last, committed by the team lead). Parked, blocked and
escalated units live in `BLOCKERS.md` — the authoritative disposition ledger
(unit | criterion | why | what unblocks); DECISIONS.md stays for resolved
ambiguities. Run-state precedence: BLOCKERS.md > tasks.md disposition comments
> RUN-SUMMARY (derived snapshot). `validate.py` mechanically checks the
template's canonical headings; `scripts/setup-sandbox.sh` builds a disposable
proving ground for the recovery/observability drills.

**Rejected alternatives:**
- A unified `run-state.md` — already rejected in #14; each artifact keeps one
  semantic.
- A dashboard disposition panel — deferred: zero new parsing surface now;
  dispositions are visible in comments, ledger and summary; named follow-up
  when a live need appears.
- Orchestrator contract lines for the summary duty — cap 114/115 (B-D6);
  the duty lives in the two command finish-hooks.

**Rationale:** B's contracts already reference "the ledger" and "the
handoff"; this change defines both. The precedence ladder prevents three-way
divergence between comments, ledger and summary; the mechanical check guards
the template that the future generator (change run-brief-interactive) will
read as its single source of truth.

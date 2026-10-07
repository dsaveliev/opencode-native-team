# Execution Plugins: context-mode + Ponytail

How the two recommended OpenCode plugins relate to native-team. Both are
external npm plugins — nothing is vendored, forked or reimplemented here.
Change: `integrate-context-mode-ponytail`.

## Architecture

```text
OpenSpec            process: intent, change artifacts, lifecycle
    ↓
native-team         who does what: orchestrator → planner → coder → tester → reviewer
    ↓
OpenCode            runtime: agents, permissions, plugin hooks
    ├── context-mode       = context / data plane
    └── @dietrichgebert/ponytail = implementation discipline
```

- **context-mode** owns the context budget: sandboxed code execution
  (`ctx_execute*`, `ctx_batch_execute`), FTS5/BM25 retrieval (`ctx_search`,
  `ctx_index`), web ingestion (`ctx_fetch_and_index`), session continuity
  across compaction. Raw bytes stay out of the model's window; only derived
  answers enter it.
- **Ponytail** owns implementation discipline: the YAGNI/reuse/stdlib ladder,
  deletion over addition, minimal diffs. Prompt-level policy only.
- **native-team** keeps roles, delegation order, permissions and the OpenSpec
  lifecycle. Neither plugin gets orchestration responsibilities; OpenSpec
  stays the authoritative process layer.

Upstream docs: [context-mode](https://github.com/mksglu/context-mode) ·
[Ponytail](https://github.com/DietrichGebert/ponytail) (this file does not
duplicate them).

## Installation

`install.sh` (project mode) adds both entries to `.opencode/opencode.json`
idempotently — existing fields, model routing, permissions, unrelated plugins
and unknown fields are preserved; no duplicates on repeated installs. The
example config ships with the entries pre-declared. The project entry is the
canonical, portable declaration; plugins already active through an external
registration (global config, OpenCode's package manager) load once — the
project entry does not duplicate them.

```bash
./install.sh /path/to/project              # adds the plugin entries
NATIVE_TEAM_PLUGINS=none ./install.sh ...  # opt out (skips/removes them)
```

Requirements: Node >= 22.5 for context-mode; python3 for the installer merge
(same prerequisite as `scripts/validate.py`).

Pinned/verified against: `context-mode@1.0.169`, `@dietrichgebert/ponytail@4.13.0`.
If a `ctx_*` tool name ever changes upstream, `scripts/validate.py` step [3b]
fails on our side — update the matrix and the pinned versions together.
Known upgrade note: a config with BOTH `plugin: ["context-mode"]` AND
`mcp["context-mode"]` registers zero `ctx_*` tools — the installer warns and
skips; run `context-mode upgrade` to clean the legacy MCP entry.

## Why no AGENTS.md is copied

The context-mode OpenCode plugin injects its routing block into the system
prompt itself (`experimental.chat.system.transform`) and enforces routing
programmatically via `tool.execute.before/after` hooks. Copying the upstream
`configs/opencode/AGENTS.md` would duplicate that payload in every prompt and
risk touching your file — so the installer never creates or modifies
AGENTS.md/CLAUDE.md. Model awareness comes from the plugin; you keep your own
instruction files untouched.

## Permission matrix (role × ctx tool)

Agent contracts deny the tools a role must not reach — enforced by
`scripts/validate.py` step [3b], present regardless of whether the plugins
are installed (denying absent tools is a no-op).

| ctx tool (permission key = short internal name) | orchestrator | planner | coder | tester | reviewer |
|---|---|---|---|---|---|
| ctx_execute / ctx_execute_file / ctx_batch_execute | allow | **deny** | allow | allow | **deny** |
| ctx_fetch_and_index | allow | **deny** | allow | allow | **deny** |
| ctx_index | allow | **deny** | allow | allow | **deny** |
| ctx_search / ctx_stats / ctx_doctor / ctx_insight | allow | allow | allow | allow | allow |
| ctx_upgrade / ctx_purge | **deny** | **deny** | **deny** | **deny** | **deny** |

Rationale: `ctx_execute`/`ctx_batch_execute` can run host shell
(`language: "shell"`) and `ctx_fetch_and_index` does network fetch — for the
read-only roles (`bash: "*": "deny"`, `webfetch: deny`) they would be a
privilege-escalation channel, so planner/reviewer keep retrieval only
(`ctx_search`, `ctx_stats`). `ctx_upgrade` (runs installs) and `ctx_purge`
(destructive knowledge-base wipe) are admin operations — denied for every
team role, the user runs them personally. Coder/tester/orchestrator already
hold broad bash; the sandbox tools then *reduce* their context cost without
granting a new capability class.

Probed on opencode 1.18.34 (see the change's design.md D10): permission keys
for plugin tools must use the **short internal names** above — the prefixed
MCP-listing form (`context-mode_ctx_execute`) matches nothing and fails
open; with short keys the denies are enforced on the subagent `task` path
(planner `ctx_execute` blocked, `ctx_search` allowed). Note also:
`opencode run --agent <subagent>` silently falls back to the default agent —
subagents are only reachable through the orchestrator's task tool, which is
the intended team topology.

Usage policy (deterministic, not a blanket rule): context-mode for large
files, bulk grep/analysis, big test outputs and logs, MCP/web research,
retrieval in long sessions; plain Read/Edit/Bash for small files, point
edits, short checks. Program the analysis, not the context.

## Precedence

1. User requirements
2. Security / correctness constraints
3. OpenSpec artifacts (proposal/design/tasks)
4. native-team role contracts
5. Project-specific skills
6. Ponytail minimalism policy

Ponytail never cancels a security requirement, contract-mandated tests or
validation, an accepted OpenSpec design decision, scope, or role
permissions. If an accepted spec says "add this abstraction", minimalism is
not a reason to delete it. Every agent contract carries this rule; Ponytail's
own mode switching (`/ponytail lite|full|ultra|off`) stays upstream and
session-wide — native-team adds no per-agent mode manager.

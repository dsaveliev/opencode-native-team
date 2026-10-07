# Design

## Context

See proposal.md - Why. Permission evaluation for a bash command passes two
gates: the agent's bash ruleset and `external_directory` for paths outside
the worktree. Team contracts already allow bash broadly (coder/tester:
`"*": "allow"` + git-mutation denies) but deny external directories
wholesale - and toolchains live outside by definition. The session DB shows
the exact denial ("a rule which prevents you...") on `go mod tidy` from a
coder subagent. The orchestrator contract has no bash ruleset at all, so
its commits ride on the user's global `ask` policy and fail silently under
`--auto`. Run data (waves, errors, denials, timings) already exists in the
session DB and is already assembled by `collect_data()` for the dashboard.

## Goals / Non-Goals

**Goals:**
- Team agents can build and fetch dependencies without permission walls;
  everything else outside the project stays denied.
- The orchestrator's own commit flow works headless (`--auto`).
- Every run leaves a human-readable, analyzable run log with a retro
  section, generated from the same code path as the dashboard.

**Non-Goals:**
- Changing the user's global config silently: global-config edits are
  explicit, additive, consent-gated operator actions (tasks 4.x), not
  shipped behavior.
- Sandbox/isolation redesign (no sandbox-exec profiles); this is a
  permission-policy fix only.
- Control plane for the dashboard; reviewer's strict bash rules stay as
  they are beyond cache access.

## Decisions

### D1: Cache allowlist instead of blanket external deny

`external_directory` in coder/tester/reviewer/orchestrator contracts
becomes a map: allow the toolchain surface
(`~/go/pkg/mod/**`, `~/go/bin/**`, `~/Library/Caches/go-build/**`,
`~/.cache/go-build/**`, `~/.npm/**`, `~/.cargo/**`, `~/.rustup/**`,
`~/.cache/pip/**`), deny `"*"` last... broad rules first, narrow allows
last - deny `"*"` first, cache allows after (last match wins in opencode).
Executables under `/opt/homebrew` and `/usr/local/go` are not listed:
execution is not a file-access permission event in practice; if a real run
proves otherwise, the retro loop surfaces it and the list grows by one line.

### D2: Orchestrator bash ruleset mirrors coder's

Allow `"*"`, deny destructive/remote git (`push`, `reset`, `revert`,
`rebase`, `stash`, `am`, `cherry-pick`, `checkout -- `, `clean`) plus the
same deny for task spawning already present. Orchestrator keeps `git add` /
`git commit` (its contract role: "the team lead commits"). No
project-edit restrictions change.

### D3: Denial detection by error text

Permission denials surface in the session DB as bash tool parts with
`state.status == "error"` and an error string containing "rule which
prevents". `load_parts` gains a third output (denial entries: time, agent,
command excerpt) alongside texts and errored-tool entries. Text-match is
deliberately lazy: it is the exact string opencode emits; a schema change
there will fail loudly in tests, not silently miscount.

### D4: Export mode reuses collect_data

`gen-team-dashboard.py --export <dir>` runs the same window adoption +
collection as the HTML render, then emits markdown instead: header
(project, window, changes), wave table (per subagent session: role, span,
duration, title), task table (top-level timings + estimates), tool errors,
denials, commits, token totals. One data path - the log and the dashboard
cannot disagree. Written by the orchestrator's final step to the change
dir (`/team-change`) or `tmp/run-logs/<date>-<slug>/` (`/team`).

### D5: Retro is model-authored, data-scaffolded

The orchestrator appends the recommendations section itself after reading
the exported log sections - no new tooling. The scaffold guarantees the
inputs (denials table, slow tasks, retries) are present; the model turns
them into concrete suggestions. This is the feedback loop for future
permission/prompt tuning.

### D6: Operator actions are consent-gated tasks, not code

Global-config edits (bash allowlist entries for module managers, cache
allowlist in `external_directory`), `install.sh --global` re-run, and the
opencode restart live in tasks as explicit steps with verification, applied
only when the user says so. The repo ships the contracts and the example;
it never edits the user's config at install time.

## Risks / Trade-offs

- The cache allowlist is per-OS (darwin/linux GOCACHE paths both listed);
  Windows paths are absent until someone runs a team there.
- Allowing `~/.cargo/**` / `~/.rustup/**` is broader than a pure cache
  (build scripts execute from there) - accepted for a single-user dev
  machine; the deny-star still blocks arbitrary projects.
- Denial-by-text-match (D3) breaks if opencode rewords the message; caught
  by tests, fixed by one string.
- Retro quality depends on the model; the scaffold keeps it useful even
  when the prose is bland (the data tables carry the signal).

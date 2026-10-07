# Proposal

## Why

Live runs exposed a permissions landmine and a memory hole. The team agent
contracts deny all external-directory access (`external_directory: deny`),
which blocks language toolchains by construction: `go mod tidy` / `go get`
touch `~/go/pkg/mod` and the Go build cache outside the project, so a coder
subagent is denied with "a rule which prevents you from using this specific
tool call" (proven from the session DB, team-sandbox run). The orchestrator
contract ships no bash ruleset at all, so its own `git commit` depends on
the user's global `ask` policy and silently fails under `--auto`. And when a
run ends, everything it did lives only in the global session DB: there is no
per-run artifact to analyze afterwards, and no feedback loop that turns run
friction (denials, retries, slow tasks) into framework improvements.

## What Changes

- Agent contracts (`agents/coder.md`, `tester.md`, `reviewer.md`,
  `orchestrator.md`): replace blanket `external_directory: deny` with a
  toolchain-cache allowlist (Go module/build caches and binaries, npm,
  cargo, rustup, pip caches) plus `*`: deny for everything else; give the
  orchestrator an explicit bash ruleset (allow by default, deny destructive
  git: push/reset/revert/rebase/stash/am/cherry-pick/checkout -- /clean).
- `examples/opencode.json.example`: same external-directory allowlist so
  project-mode installs work out of the box.
- Run log export: `gen-team-dashboard.py --export <dir>` renders
  `RUN-LOG.md` from the same data the dashboard collects (waves, task
  timings, tool errors, permission denials, commits, tokens); `/team-change`
  final step writes it to `openspec/changes/<change>/RUN-LOG.md`, `/team`
  to `tmp/run-logs/<date>-<slug>/RUN-LOG.md`.
- Retro step (final, model-driven): the orchestrator appends a
  recommendations section to the run log (slow tasks, retries, denials ->
  concrete framework improvement suggestions).
- Operator-side (outside the repo, applied at install time with the user's
  consent): extend the user's global `~/.config/opencode/opencode.json`
  bash allowlist with module managers (`go mod*`, `go get*`,
  `npm install*`, `npm ci*`, `pip install -r*`, `pip3 install -r*`) and the
  same cache allowlist in its `external_directory`; re-run
  `install.sh --global`; restart opencode.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `plugin-integrations`: agent contracts gain toolchain-cache access and an
  orchestrator bash ruleset; the example project config mirrors the cache
  allowlist.
- `run-briefs`: the run lifecycle gains a mandatory final export step
  (RUN-LOG.md) and a retro recommendations section.

## Impact

- Files: `agents/*.md` (frontmatter only), `examples/opencode.json.example`,
  `scripts/gen-team-dashboard.py` (export mode), `commands/team.md`,
  `commands/team-change.md` (final step), `scripts/test-dashboard.py`
  (export smoke), `scripts/validate.py` (contract frontmatter sanity),
  `README.md`.
- Behavior: team agents can build/fetch dependencies; orchestrator can
  commit under `--auto`; runs leave a markdown run log. No dashboard or
  serve behavior changes.
- Not in repo: the user's global config edits and the reinstall/restart are
  one-time operator actions listed in tasks and README, applied only with
  explicit user consent.

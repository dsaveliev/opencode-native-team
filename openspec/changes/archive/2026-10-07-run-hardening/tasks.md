# Tasks

## 1. Agent contracts (permissions)

- [x] 1.1 Replace `external_directory: deny` with the toolchain-cache
  allowlist (D1) in `agents/coder.md`, `agents/tester.md`,
  `agents/reviewer.md`, `agents/orchestrator.md`. Verify: frontmatter parses
  as YAML; `rg 'external_directory' agents/` shows the map in all four; no
  blanket deny remains.
- [x] 1.2 Add the orchestrator bash ruleset (D2: allow `*`, deny
  push/reset/revert/rebase/stash/am/cherry-pick/`checkout -- `/clean) to
  `agents/orchestrator.md`. Verify: block present; deny list matches the
  coder's minus add/commit.
- [x] 1.3 Mirror the cache allowlist in `examples/opencode.json.example`
  `external_directory`. Verify: JSON parses; allowlist entries identical to
  contracts.

## 2. Run log export

- [x] 2.1 Denial collection (D3): extend `load_parts` in
  `scripts/gen-team-dashboard.py` to also return permission-denial entries
  (bash error parts matching "rule which prevents": time, agent, command
  excerpt). Verify: unit check against a fixture part payload in
  `test-dashboard.py`.
- [x] 2.2 Export mode (D4): `--export <dir>` renders `RUN-LOG.md` from
  `collect_data` (header, wave table, task timings, tool errors, denials,
  commits, tokens). Verify: run on this repo; file contains all sections;
  dashboard HTML output unchanged.
- [x] 2.3 Final step in `commands/team.md` and `commands/team-change.md`:
  after final gates, run the export to the change dir (`/team-change`) or
  `tmp/run-logs/<date>-<slug>/` (`/team`), then write the retro section
  (D5). Verify: `rg 'RUN-LOG' commands/` in both; step wording references
  the export command verbatim.

## 3. Tests and validation

- [x] 3.1 Extend `scripts/test-dashboard.py`: export smoke on the fixture
  (markdown sections present), denial-parse unit check. Verify:
  `python3 scripts/test-dashboard.py` passes.
- [x] 3.2 Extend `scripts/validate.py`: contract frontmatter sanity - all
  four agent files parse as YAML, contain `external_directory` maps (not
  blanket deny), orchestrator has a bash block; example JSON parses with
  the allowlist. Verify: `python3 scripts/validate.py` -> ALL CHECKS
  PASSED.
- [x] 3.3 README: permissions section (cache allowlist rationale, module
  commands that now work, `--auto` commit flow) + run log/retro section.
  Verify: `rg` finds both sections; doc paths check stays green.

## 4. Operator actions (consent-gated, outside the repo)

- [x] 4.1 With user consent: extend `~/.config/opencode/opencode.json` -
  bash allowlist += `go mod*`, `go get*`, `npm install*`, `npm ci*`,
  `pip install -r*`, `pip3 install -r*`; `external_directory` += cache
  allowlist. Verify: `opencode` starts cleanly after restart; config
  diff shows additive changes only.
- [x] 4.2 Re-run `./install.sh --global` to refresh agent contracts; user
  restarts opencode. Verify: `diff agents/coder.md
  ~/.config/opencode/agents/coder.md` empty; a scratch `go mod tidy` via a
  coder subagent runs without denial.

# Tasks

## 1. Permission matrix in agent contracts

- [x] 1.1 Add `ctx_*` deny keys to frontmatter per design D2 (short internal
  tool names — probed, see D10): planner and reviewer deny `ctx_execute`,
  `ctx_execute_file`, `ctx_batch_execute`, `ctx_fetch_and_index`,
  `ctx_index`, `ctx_upgrade`, `ctx_purge`; coder, tester, orchestrator deny
  `ctx_upgrade` + `ctx_purge`; add the one-line
  precedence rule (design D6) to all five contracts; bump
  `validate.py` `LIMITS["reviewer"]` to 46. Verify: `python3
  scripts/validate.py` passes with the edits in place.
- [x] 1.2 Add a `validate.py` step enforcing the matrix in both directions:
  every required deny present per role, and no sandbox-tool denies added to
  coder/tester/orchestrator (protects token-saving goal from over-hardening).
  Verify: validate.py green; then in a scratch copy of `agents/planner.md`
  remove one deny and confirm the step fails naming planner + the key
  (restore afterwards).

## 2. Installer: idempotent plugin-entry merge

- [x] 2.1 Create `scripts/integrate-plugins.py` (python3 stdlib `json` only):
  `add` mode appends missing entries to the `plugin` array preserving all
  fields/order; `remove` mode (env `NATIVE_TEAM_PLUGINS=none`) strips the two
  known entries and drops an empty `plugin` key; malformed JSON → non-zero
  exit, file untouched; `mcp["context-mode"]` conflict → loud warning, skip
  the context-mode entry, still add ponytail (spec: Idempotent config merge,
  Installer opt-out). Verify: manual runs against tmpdir fixtures for each
  mode print the expected outcomes.
- [x] 2.2 Create `scripts/test-integrate-plugins.py` (assert-based tmpdir
  fixtures, `test-dashboard.py` style) covering: absent config, existing
  config with model routing + unknown fields + unrelated plugins,
  already-present entries, repeated install, remove-mode both directions,
  malformed JSON untouched + non-zero, legacy `mcp.context-mode` path; wire
  it into `validate.py` step [7]. Verify: `python3
  scripts/test-integrate-plugins.py` exits 0; validate.py green.
- [x] 2.3 Extend `install.sh` (project mode only, after the example-config
  block) to invoke the merge script honoring `NATIVE_TEAM_PLUGINS`; global
  mode unchanged. Verify: `bash -n install.sh`; fresh tmpdir project install
  → config carries both entries with model routing intact; second install →
  no duplicates; `NATIVE_TEAM_PLUGINS=none` install → no entries.

## 3. Example config and documentation

- [x] 3.1 Add `"plugin": ["context-mode", "@dietrichgebert/ponytail"]` to
  `examples/opencode.json.example` (additive — models, permissions, bash maps
  byte-identical); extend `validate.py` step [5]: plugin array contains
  exactly the two entries and no `mcp` block references context-mode. Verify:
  validate.py green.
- [x] 3.2 Write `docs/integrations.md`: architecture split diagram (OpenSpec →
  native-team → OpenCode → context-mode = context/data plane, Ponytail =
  implementation discipline), responsibility lists, the D2 permission matrix,
  precedence ladder (user requirements > security/correctness > OpenSpec
  artifacts > role contract > project skills > Ponytail), installer opt-out,
  pinned upstream versions (context-mode@1.0.169, @dietrichgebert/ponytail@
  4.13.0) with upgrade notes, why no AGENTS.md is copied, upstream links
  (no doc duplication). Verify: doc renders; claims match design.md.
- [x] 3.3 Update `README.md` (short "Execution plugins" section linking
  docs/integrations.md, python3 prerequisite note, opt-out mention) and
  `SPEC.md` project-structure lines for the two new scripts + new doc. Verify:
  `python3 scripts/validate.py` doc-reality step green (all newly referenced
  paths exist).

## 4. Integration verification

- [x] 4.1 Live two-plugin smoke test (requires Node >= 22.5 and both plugins
  in the plugin cache; if unavailable, leave unchecked with the reason —
  do not claim untested behavior): in a tmpdir fixture project with the
  installed config, verify via the orchestrator `task` path (the only real
  route to subagents — `--agent <subagent>` falls back to the default
  agent, probed): `ctx stats` responds; Ponytail injection active; planner
  `ctx_execute` blocked before execution while planner `ctx_search`
  responds and planner bash stays rule-rejected (existing model intact);
  coder `ctx_execute` succeeds; both plugins register exactly once,
  including when a plugin is already active via an external registration
  (spec: Coexistence with external plugin registration). Probes F1/F1b/F3/F4
  in design.md D10 are the recorded evidence; final sweep re-runs the
  planner-exec denial with the short-name matrix in place.
- [x] 4.2 Final regression sweep: `python3 scripts/validate.py` → ALL CHECKS
  PASSED; `openspec validate integrate-context-mode-ponytail`; review the
  full diff — no files under `vendor/`, no new repo dependencies, no changes
  to model routing, delegation order, commands, dashboard or global-install
  behavior (spec: Upstream isolation; proposal Non-goals).

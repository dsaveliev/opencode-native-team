# Proposal

## Why

Team runs lose a large share of their context window to raw tool output (build
logs, large greps, MCP responses) and to over-built implementations, yet both
problems already have mature external OpenCode plugins: `context-mode`
(context/data plane: sandboxed analysis, FTS5 retrieval, session continuity)
and `@dietrichgebert/ponytail` (implementation discipline: YAGNI ladder,
minimal diffs). native-team should recommend both natively — without vendoring
their source, without a second orchestration engine, and without weakening the
role permission model (a sandbox tool is shell-on-host for a `bash: "*": "deny"`
role, so unrestrained access would be a privilege-escalation channel).

## What Changes

- Recommend both plugins via the official OpenCode `plugin` mechanism:
  `"plugin": ["context-mode", "@dietrichgebert/ponytail"]` in
  `examples/opencode.json.example` (additive; models, permissions and routing
  untouched). The project entries are the canonical, portable declaration:
  they must coexist with externally registered (global config /
  package-manager) plugin activations without duplicate tool or command
  registration; opt-out leaves external registrations untouched.
- Extend `install.sh` (project mode) with an idempotent, non-destructive JSON
  merge (Python stdlib, no new dependencies) that adds the two plugin entries
  to an existing `.opencode/opencode.json`: no overwrites, no lost fields, no
  duplicates, unknown fields and unrelated plugins preserved; opt-out via
  `NATIVE_TEAM_PLUGINS=none`; loud warning on the upstream
  `plugin`+`mcp.context-mode` conflict instead of silently adding a broken state.
- Add a `ROLE x ctx-tool` permission matrix to the agent contracts
  (frontmatter): read-only roles (planner, reviewer) keep retrieval-only access
  (`ctx_search`, `ctx_stats`); exec/network/index tools denied; destructive
  meta tools (`ctx_upgrade`, `ctx_purge`) denied for every team role; coder,
  tester and orchestrator keep the sandbox tools their trust level already
  grants. Enforced mechanically by `scripts/validate.py`.
- One precedence line per contract: OpenSpec artifacts, role contracts and
  security rules always override minimalism policies (Ponytail cannot cancel
  tests, validation or scope).
- No `AGENTS.md` copying: the context-mode plugin already injects its routing
  block programmatically (`experimental.chat.system.transform`); copying the
  upstream file would duplicate payload (prompt inflation) and risk clobbering
  a user file.
- Docs: new `docs/integrations.md` (architecture split, permission matrix,
  precedence, opt-out, upstream links) + a short README section.
- Tests: fixture-driven installer-merge test (`scripts/test-integrate-plugins.py`,
  wired into `validate.py`), static permission-matrix regression in
  `validate.py`, example-config regression, and a live two-plugin smoke test
  task (executed at apply time).

Non-goals: no vendoring/forking of upstream source, no new framework/task
manager/state store, no changes to OpenSpec lifecycle, delegation order,
`DECISIONS.md` semantics, model routing, or the global-install mode (config
stays per-project), no per-agent Ponytail mode manager (upstream persistence
is global/session-wide and stays as-is).

## Capabilities

### New Capabilities

- `plugin-integrations`: how native-team recommends, installs and constrains
  external OpenCode plugins — recommended plugin set, idempotent config merge
  behavior, role-based plugin-tool permission matrix, discipline-policy
  precedence, and routing usage policy for context-heavy work.

### Modified Capabilities

(none — the project has no existing specs)

## Impact

- `install.sh` (+merge step, project mode only), new
  `scripts/integrate-plugins.py` + `scripts/test-integrate-plugins.py`.
- `agents/*.md`: frontmatter permission additions (5 contracts), one
  precedence line each; `scripts/validate.py`: contract line-limit bump for
  reviewer (security matrix), new matrix + example-config checks, wiring the
  new fixture test.
- `examples/opencode.json.example`: `plugin` array added (additive).
- `docs/integrations.md` (new), `README.md` (short section), `SPEC.md`
  (structure listing).
- Runtime effect only when the user has Node >= 22.5 and the plugins installed;
  without them the config entries are inert and the frontmatter denies are
  no-ops for absent tools.

# Design

## Context

Repo state (verified): 5 agent contracts with frontmatter permission maps
(`agents/*.md`), `install.sh` copies agents/skills/commands/dashboard and the
example config only when absent, `scripts/validate.py` enforces contract
shapes mechanically, `openspec/specs/` is empty, `vendor/` pins only
agent-skills. Upstream state (verified against installed packages
`context-mode@1.0.169`, `@dietrichgebert/ponytail@4.13.0`):

- context-mode ships a native OpenCode adapter
  (`build/adapters/opencode/plugin.js`, `package.json` `main`), registered by
  `"plugin": ["context-mode"]`; it registers 11 `ctx_*` tools in-process and
  hooks `tool.execute.before/after`, `chat.message`,
  `experimental.session.compacting`, `experimental.chat.system.transform`.
  The transform hook injects the routing block + resume snapshots into the
  system prompt itself; upstream calls the `configs/opencode/AGENTS.md` copy
  *optional* for OpenCode.
- ponytail ships `.opencode/plugins/ponytail.mjs` (V1 `server()` + V2
  `id`/`setup`), registered the same way; it registers `/ponytail*` commands
  and its skills dir, and injects its ruleset into every chat's system prompt
  (context hook appends; V1 transform appends to the last system part). Mode
  persists in one global file `~/.config/opencode/.ponytail-active`
  (session-wide, not per-agent).
- Security-critical fact: planner/reviewer frontmatter already carries
  `bash: {"*": "deny"}` and `webfetch: deny`. `ctx_execute` /
  `ctx_execute_file` / `ctx_batch_execute` can run host shell
  (`language: "shell"`), `ctx_fetch_and_index` does network fetch — all three
  would bypass those denials if left default-allowed for read-only roles.

## Goals / Non-Goals

**Goals:**

- Both plugins as external npm plugins via one config surface (`plugin`
  array), merged idempotently by the installer.
- A role-based permission matrix for `ctx_*` tools, enforced in contracts and
  by `validate.py`, so context-mode cannot be a privilege-escalation channel.
- Documented precedence (contracts/OpenSpec/security over minimalism) with
  upstream Ponytail semantics untouched.
- Fixture tests for the merge + static regression for the matrix; live
  two-plugin smoke test at apply time.

**Non-Goals:** (beyond proposal Non-goals)

- No per-tool routing prompt engineering in native-team docs beyond pointing
  at plugin-injected routing (no duplicate policy text).
- No changes to reviewer/tester bash maps, model routing, dashboard,
  team-skills sync, or global-install layout.

## Decisions

### D1 — Integration surface: `plugin` array only

Both packages are registered exactly as upstream documents for OpenCode:
top-level `"plugin": ["context-mode", "@dietrichgebert/ponytail"]`. No
`mcpServers` entry (upstream: plugin + `mcp.context-mode` together register
zero `ctx_*` tools), no vendored copies, no repo dependencies — the entries
resolve from the user's plugin cache at runtime.
*Alternatives rejected:* vendoring source (maintenance + license drift);
`mcpServers` stdio child (redundant process, conflicts with plugin path).

### D2 — Permission matrix lives in agent frontmatter (contract layer)

The `ctx_*` denies go into `agents/*.md` frontmatter, not only the example
config. Rationale: the example config is optional and user-editable —
security boundaries must not depend on an optional file; frontmatter denies
are enforced ahead of top-level allows (the repo's probed precedence, see
validate.py C-2 comment) and are inert no-ops when plugins are absent.
This follows the existing complete-map/superset philosophy: contracts carry
the boundary, config only ever widens for project-specific commands.
*Alternative rejected:* matrix only in `opencode.json.example` — a user with
a hand-rolled config would silently get escalated planners/reviewers.

Exact keys (enumerated, no glob patterns — deterministic, mechanically
checkable): permission keys use the **short internal tool names**
(`ctx_execute`, not the MCP-listing form `context-mode_ctx_execute`) —
probed at apply time (D10, probes F1 vs F1b); the prefixed form does not
match anything and silently fails open.

| Tool (permission key = short internal name) | orchestrator | planner | coder | tester | reviewer |
|---|---|---|---|---|---|
| ctx_execute / ctx_execute_file / ctx_batch_execute | default | **deny** | default | default | **deny** |
| ctx_fetch_and_index | default | **deny** | default | default | **deny** |
| ctx_index | default | **deny** | default | default | **deny** |
| ctx_search / ctx_stats / ctx_doctor / ctx_insight | default | default | default | default | default |
| ctx_upgrade / ctx_purge | **deny** | **deny** | **deny** | **deny** | **deny** |

- Read-only roles keep retrieval + diagnostics only; exec/network/index are
  denied exactly like their `bash`/`webfetch` denials (sandbox = shell on
  host; fetch = network; index = store write).
- `ctx_upgrade` (runs installs) and `ctx_purge` (destructive KB wipe) are
  denied for every team role — admin actions belong to the user, matching
  "coder/tester can't commit/push" and the no-`~/.anything`-writes boundary.
- Coder/tester/orchestrator keep sandbox tools: they already hold broad
  bash; the plugin then *reduces* their context cost (bulk analysis moves
  out of the window) without granting any new capability class.
- `ctx_doctor` (read-only diagnostics) and `ctx_insight` (opens dashboard
  URL) stay default: benign, and denying them in the primary agent would
  block the interactive user's own `ctx doctor` request in `/team` sessions.

### D3 — Contract edits are additive and mechanically bounded

Per contract: the deny keys above (+1 precedence line, see D6). This grows
reviewer past its 40-line limit and orchestrator past its 90-line limit →
`validate.py` `LIMITS["reviewer"] = 46`, `LIMITS["orchestrator"] = 96`
(security matrix justifies a bounded bump; planner/coder/tester stay at 40).
`validate.py` gains a step that fails on any missing required deny key and
on matrix drift in either direction (a deny accidentally added to
coder/tester for sandbox tools is also flagged — protects the token-saving
goal from well-meaning hardening).

### D4 — Installer merge: stdlib Python script, fail-loud, opt-out switch

New `scripts/integrate-plugins.py` (python3, `json` only — precedent:
`validate.py`; no jq/node dependency assumptions in `install.sh`). Called in
project mode after the existing example-config step; global mode untouched
(config stays per-project).

- Default (`add`): parse JSON → ensure `plugin` list contains both entries
  (append missing, never reorder/dedup user entries) → write back with
  `indent=2` + trailing newline. All unknown fields survive by construction
  (dict round-trip).
- `NATIVE_TEAM_PLUGINS=none` (`remove` mode): strip the two known entries
  (and an empty `plugin` key), preserve everything else; runs on fresh
  installs too (example is copied, then stripped).
- Invalid JSON → exit non-zero with path + parse error; file untouched
  (installer `set -e` aborts — fail-loud philosophy).
- Conflict guard: if `mcp["context-mode"]` exists and the plugin entry does
  not, print the upstream warning, skip adding `context-mode` (adding it
  would produce the zero-tools state), still add ponytail, tell the user to
  run `context-mode upgrade` and re-install.
*Alternatives rejected:* bash/sed JSON surgery (fragile, forbidden by task);
jq (not a guaranteed prerequisite); Node script (install.sh currently needs
no runtime).

### D5 — No AGENTS.md copying

Upstream's OpenCode adapter already injects the routing block via
`experimental.chat.system.transform`, and hooks enforce routing
programmatically regardless. Copying `configs/opencode/AGENTS.md` would
double the payload (prompt inflation) and risk touching user files.
Installer and docs must not create/append AGENTS.md; `docs/integrations.md`
links upstream docs instead of duplicating them.

### D6 — Ponytail: config entry + one precedence line + docs, nothing else

Mode persistence is upstream-global (`~/.config/opencode/.ponytail-active`)
and applies to every chat including subagent sessions; we keep that semantic
(no second mode manager, no per-agent forks). The only native-team addition
is one line per contract, e.g. under Prohibited/Team Contracts:
"Layers above — user requirements, security, OpenSpec artifacts, this
contract — always override minimalism policies (e.g. Ponytail); never delete
contract-mandated tests or validation as 'overengineering'." That line is
the citable authority when Ponytail's ruleset conflicts with a contract.

### D7 — Two-plugin interaction (analyzed, verified by smoke test)

- Both register via the same `plugin` array; duplicate registration is
  impossible because the merge is dedup-by-name and OpenCode resolves each
  package once.
- System prompt: both *append* (ponytail pushes a text part / appends to the
  last part; context-mode's transform injects its block) — neither rewrites
  parts it does not own, so order-independent composition; worst case is
  bounded additive payload (~4.5 KB routing block + ~3 KB ruleset per
  session), far below the context cost of one unrouted 50 KB tool dump.
- Hook namespaces are disjoint: context-mode owns `tool.execute.*`,
  `chat.message`, compaction; ponytail owns command execution + its context
  append. No shared state.
- Compaction/resume: context-mode hooks `experimental.session.compacting`
  (snapshots); ponytail re-injects every turn, so both survive compaction.
- Subagents: plugin tools and injections are session-pipeline-level, so
  subagent chats see them; their per-agent frontmatter denies (D2) gate the
  dangerous subset — this is exactly what the smoke test must prove
  (planner denied `ctx_execute`, coder allowed, both plugins' markers
  present, team agents still start).

### D8 — Tests

- `scripts/test-integrate-plugins.py`: tmpdir fixtures, assert-based,
  covering: absent config, existing config with model routing + unknown
  fields + unrelated plugins, already-present entries (no dup), repeated
  install, `remove` mode both directions, malformed JSON (untouched,
  non-zero), legacy `mcp.context-mode` conflict path. Wired into
  `validate.py` step [7] next to `test-dashboard.py`.
- `validate.py` new step: frontmatter matrix (D2 table) + example config
  (`plugin` array exactly the two entries; reviewer superset and model
  routing checks already exist).
- Live smoke test (apply-time task, not CI): `opencode run` in a fixture
  project with both plugins — `ctx stats` responds, `/ponytail` command
  listed, planner `ctx_execute` denied by permission, coder `ctx_execute`
  works, `openspec validate` + `validate.py` green.

### D9 — Coexistence with external plugin registration

Verified on the reference machine: both plugins can be active with no
`plugin` array in either the global or the project config — OpenCode's
package manager registers them from its own cache. Therefore the merge
script manages only the project config (external registration sources
cannot be enumerated reliably) and must not try to modify them. A project
entry for an already-active package is expected to resolve to a single
load (OpenCode resolves packages by name); this must be proven in the
smoke test, not assumed. Failure mode (double registration observed) →
document `NATIVE_TEAM_PLUGINS=none` as the path for externally managed
setups; the project config stays clean and portable either way.

### D10 — Probed runtime behavior (apply-time evidence, opencode 1.18.34)

Event-level probes via the only real path to subagents — the orchestrator's
`task` tool (`opencode run --agent <subagent>` silently falls back to the
default agent; subagents are unreachable directly):

- F3: planner `bash echo` → **rule-rejected** by the frontmatter bash map —
  the repo's existing permission model IS enforced on 1.18.34 via the task
  path (C-2 holds).
- F1: planner `ctx_execute` with prefixed frontmatter key
  (`context-mode_ctx_execute: deny`) → **executed** — plugin-tool permission
  keys do not match the prefixed MCP-listing name.
- F1b: same probe after switching the key to the short internal name
  (`ctx_execute: deny`) → **blocked** before execution. Short names are the
  correct key form; adopted in D2.
- F4: planner `ctx_search` (not denied) → completed — the matrix is
  per-tool, retrieval stays available.
- Probe-methodology trap recorded for the future: model-claimed replies are
  not proof (a model can print "hi" without calling a tool); only
  `--format json` `tool_use` events or an orchestrator-relayed raw error
  are. An earlier false conclusion ("denies not enforced at all") came from
  probing subagents via `--agent`, which never actually ran them.

A runtime guard shim (a local plugin hooking `tool.execute.before`) was
prototyped and **rejected**: native enforcement with short keys is proven,
so the shim would duplicate the permission layer — more surface, zero
added guarantee.

## Risks / Trade-offs

- [Permission key spelling `context-mode_ctx_*` drifts upstream] → matrix is
  a pinned contract against the current 11-tool set; validate.py fails on
  our side, docs/integrations.md notes the pinned versions and the upgrade
  path.
- [Glob-less enumeration adds 7 frontmatter lines to read-only contracts] →
  bounded by LIMITS bump (reviewer 46) and validate.py; the payoff is
  deterministic enforcement — accepted.
- [Installer now requires python3] → already required by validate.py in CI;
  README prerequisite line updated.
- [Both plugins inject per-subagent-session payload] → bounded static text,
  one copy each per session; the alternative (no plugins) costs whole tool
  dumps — net win; measured in smoke test via `ctx stats`.
- [User's existing broken `plugin`+`mcp` combo] → conflict guard warns and
  does not make it worse; upstream `context-mode upgrade` is the documented
  fix.
- [Smoke test shows double registration for externally active plugins] →
  documented fallback (D9): `NATIVE_TEAM_PLUGINS=none` for externally
  managed setups; upstream dedup-by-name is expected but verified, not
  assumed.
- [Ponytail deletes "overengineering" that a spec requires] → precedence
  line (D6) + reviewer contract already gates; smoke test includes the
  contracts-still-load check.

## Migration Plan

Additive change; no data or config migration. Rollback: revert commits (the
merge script never rewrites fields it did not add; `NATIVE_TEAM_PLUGINS=none`
removes the entries for users who keep the rest).

## Open Questions

- None blocking. (Whether OpenCode ever supports `context-mode_*` glob keys
  is irrelevant by D2's enumeration decision; subagent-level injection is a
  verification item in the smoke test, not a design unknown.)

# plugin-integrations Specification

## Purpose

Defines how opencode-native-team recommends, installs and constrains external
OpenCode execution plugins (context data plane + implementation discipline)
without vendoring upstream source or weakening role permissions.

## Requirements

### Requirement: Recommended plugin set

The project's example OpenCode configuration SHALL declare
`context-mode` and `@dietrichgebert/ponytail` in the top-level `plugin`
array, additively: existing model routing, agent permissions, test-command
allows and all other example fields SHALL remain unchanged. The declared
entries SHALL be the only reference to the plugins in the config — no
`mcp.context-mode` entry SHALL be introduced (the plugin path registers
tools natively; the combination registers zero `ctx_*` tools upstream).

#### Scenario: Example config carries both plugins additively

- **WHEN** the example config is inspected
- **THEN** its `plugin` array contains exactly `context-mode` and
  `@dietrichgebert/ponytail`, the GLM model routing for all five agents is
  byte-identical to the pre-change example, and no `mcp` block references
  context-mode

#### Scenario: Plugins absent at runtime

- **WHEN** a target project runs OpenCode without the two plugins installed
- **THEN** the `plugin` config entries are inert and every native-team agent
  contract behaves exactly as before this change

### Requirement: Idempotent config merge on install

In project-scoped installs, the installer SHALL merge the two plugin entries
into an existing `.opencode/opencode.json` via a structured JSON round-trip
(stdlib parsing, no regex/sed JSON edits), and the merge MUST be idempotent
and non-destructive: existing fields (including unknown ones), nested
objects, arrays, unrelated plugin entries, model routing and permissions
SHALL be preserved; no duplicate entries SHALL be created on repeated runs.
When the config file does not exist, the installer SHALL keep its current
behavior of copying the example config (which already carries the entries).
Global installs (`--global`) SHALL NOT touch any config. A malformed JSON
config SHALL abort the merge loudly without modifying the file.

#### Scenario: Existing config gains entries, nothing else changes

- **WHEN** the installer runs on a project whose config contains model
  routing, an unrelated plugin, and an unknown top-level field
- **THEN** after the merge the `plugin` array contains the unrelated plugin
  plus both recommended entries, and every pre-existing field (including the
  unknown one) is present with its original value

#### Scenario: Repeated install creates no duplicates

- **WHEN** the installer runs twice on the same project
- **THEN** the second run reports both entries already present and the
  `plugin` array still lists each recommended plugin exactly once

#### Scenario: Malformed config fails loud and untouched

- **WHEN** the target config contains invalid JSON
- **THEN** the installer exits non-zero with a clear message and leaves the
  file byte-identical

#### Scenario: Legacy MCP conflict is warned, not silently broken

- **WHEN** the target config already has `mcp.context-mode` and lacks the
  `context-mode` plugin entry
- **THEN** the installer prints the upstream conflict warning (plugin +
  mcp together register zero `ctx_*` tools), skips adding the `context-mode`
  entry, directs the user to run `context-mode upgrade`, and still adds the
  `@dietrichgebert/ponytail` entry

### Requirement: Installer opt-out

A user SHALL be able to exclude the recommended plugin entries from install
time without modifying native-team core files, via a single documented
installer-level switch (`NATIVE_TEAM_PLUGINS=none`): with the switch set, an
absent config is created without the plugin entries and an existing config
has them removed if present; all other install behavior is unchanged.

#### Scenario: Opt-out on fresh install

- **WHEN** the installer runs with the opt-out switch set on a project
  without a config
- **THEN** the created config contains no `context-mode` or ponytail entry
  and is otherwise the standard example config

#### Scenario: Opt-out removes previously recommended entries

- **WHEN** the installer runs with the opt-out switch set on a project whose
  config already carries both recommended entries
- **THEN** both entries are removed, unrelated plugins and every other field
  are preserved

### Requirement: Coexistence with external plugin registration

The recommended plugin entries SHALL coexist with plugins already active
through registration sources outside the project config (global config,
OpenCode's own plugin/package manager): adding a project-level `plugin`
entry for an already-active package MUST NOT produce duplicate tool or
command registration, and the installer MUST NOT attempt to remove or
modify external registrations. Documentation SHALL state that the project
entry is the canonical, portable declaration and that
`NATIVE_TEAM_PLUGINS=none` leaves external registrations untouched.

#### Scenario: Externally active plugin gains a project entry

- **WHEN** the installer adds the project `plugin` entries while one or both
  plugins are already active via an external registration
- **THEN** each plugin loads exactly once — every `ctx_*` tool and ponytail
  command appears a single time — verified in the integration smoke test

#### Scenario: Opt-out does not touch external registrations

- **WHEN** the installer runs with `NATIVE_TEAM_PLUGINS=none` while a plugin
  remains active externally
- **THEN** only the project entries are absent; the external registration
  and its behavior are unchanged

### Requirement: Plugin-tool permission matrix

Agent contracts SHALL constrain context-mode tools by role so the plugin
set cannot become a privilege-escalation channel: read-only roles (planner,
reviewer) MUST be denied `ctx_execute`, `ctx_execute_file`,
`ctx_batch_execute`, `ctx_fetch_and_index` and `ctx_index` (sandbox
execution, network fetch and store writes bypass their `bash`/`webfetch`
denials), while retrieval (`ctx_search`, `ctx_stats`) stays available;
`ctx_upgrade` and `ctx_purge` MUST be denied for all five team roles
(admin/destructive operations are the user's, not the team's). Permission
keys MUST use the short internal tool names — the prefixed
`context-mode_*` form does not match and fails open (probed). Coder, tester
and orchestrator keep the sandbox and retrieval tools consistent with their
existing trust level. The matrix SHALL be enforced by the repo's mechanical
validation, and the constraints MUST hold in agent frontmatter regardless
of whether plugins are installed (denying absent tools is a no-op).

#### Scenario: Read-only role cannot reach host shell via sandbox

- **WHEN** planner or reviewer attempts any of the exec/network/index
  context-mode tools in a session where the plugin is active
- **THEN** the call is blocked before execution, while `ctx_search` and
  `ctx_stats` still respond for the same role

#### Scenario: Trusted roles keep analysis power

- **WHEN** coder or tester uses `ctx_execute` or `ctx_batch_execute` for
  bulk test-output analysis, or orchestrator uses them for research
- **THEN** the calls are permitted and their bash git-write denies are
  unchanged

#### Scenario: Regression check catches matrix drift

- **WHEN** repo validation runs after an edit removes any required deny from
  any agent contract
- **THEN** validation fails naming the agent and the missing deny

### Requirement: Discipline-policy precedence

Every agent contract SHALL state that user requirements, security and
correctness constraints, OpenSpec artifacts and the role contract itself
always override implementation-minimalism policies (Ponytail): minimalism
MUST NOT cancel required validation, tests mandated by a contract, accepted
OpenSpec architecture decisions, scope, or role permissions. Ponytail's
upstream mode persistence (global, session-wide) SHALL be preserved as-is —
native-team MUST NOT introduce its own per-agent mode manager or a fork of
the ruleset.

#### Scenario: Minimalism does not delete contract-mandated tests

- **WHEN** a run with Ponytail active produces a diff where a
  contract-mandated test or validation was removed as "overengineering"
- **THEN** the reviewer flags it as a violation and the precedence rule in
  the contracts is the cited authority

#### Scenario: Mode switching stays upstream

- **WHEN** a user switches Ponytail intensity (`/ponytail lite|full|ultra|off`)
- **THEN** native-team adds no second mode state; upstream persistence
  applies to the whole session unchanged

### Requirement: Routing without AGENTS.md copying

Model awareness of context-mode routing SHALL come from the plugin's own
programmatic system-prompt injection; the installer and docs MUST NOT copy
upstream `AGENTS.md` (or append routing blocks to a user's instruction
files) — that would duplicate the injected payload and risk clobbering user
content. Installation documentation SHALL state that hooks enforce routing
even without any AGENTS.md changes.

#### Scenario: Installer never touches instruction files

- **WHEN** the installer runs on a project that has an `AGENTS.md`
- **THEN** the file is not created, modified or appended to, and routing
  still works because the plugin injects its routing block at runtime

### Requirement: Upstream isolation

native-team SHALL integrate both plugins as external npm plugins only: no
upstream source files vendored into the repo, no runtime dependencies added
to the project for integration purposes, and no second orchestration, task,
state or permission framework introduced. OpenSpec remains the authoritative
process layer; context-mode is positioned as context/data plane and Ponytail
as implementation-discipline policy.

#### Scenario: Repo gains no upstream code

- **WHEN** the change is implemented
- **THEN** `vendor/` contains no context-mode or ponytail files, no
  package.json dependency on either package exists in the repo, and the
  integration surface is config, contracts, docs and installer logic only

### Requirement: Toolchain cache access for team agents

Team agent contracts (coder, tester, reviewer, orchestrator) SHALL allow
subagent access to language toolchain caches and package directories
outside the project (Go module cache, Go build cache on macOS and Linux,
`~/go/bin`, npm cache, cargo registry, rustup toolchains, pip cache) while
denying every other external directory. A standard dependency operation
(`go mod tidy`, `go get`, `npm install`, `cargo fetch`) run by a team agent
SHALL NOT be blocked by external-directory permissions.

#### Scenario: Coder adds a dependency mid-run

- **WHEN** the coder subagent runs `go mod tidy` and the Go module cache
  lives at `~/go/pkg/mod`
- **THEN** the command executes without an external-directory permission
  denial

#### Scenario: Foreign project directory stays denied

- **WHEN** a team agent attempts a file access into another user project
  directory not covered by the toolchain allowlist
- **THEN** the access is denied

### Requirement: Orchestrator bash ruleset

The orchestrator contract SHALL carry an explicit bash permission ruleset:
allow by default, deny destructive and remote git operations (push, reset,
revert, rebase, stash, am, cherry-pick, `checkout --`, clean). The
orchestrator's own commit flow (`git add`, `git commit`) SHALL work under a
headless `--auto` run without interactive permission approval.

#### Scenario: Orchestrator commits a wave under auto

- **WHEN** a run is launched with `--auto` and the orchestrator commits a
  finished wave (`git add` + `git commit`)
- **THEN** the commands execute without a permission ask or denial

#### Scenario: Push stays denied

- **WHEN** the orchestrator attempts `git push`
- **THEN** the command is denied by its contract ruleset

### Requirement: Example project config mirrors toolchain access

The shipped example project configuration
(`examples/opencode.json.example`) SHALL include the same toolchain-cache
external-directory allowlist, so a project-mode install can build and fetch
dependencies before any manual permission tuning.

#### Scenario: Fresh project install runs module commands

- **WHEN** a project is set up from the example config and a team agent
  runs `npm install`
- **THEN** the npm cache access does not trigger an external-directory
  denial

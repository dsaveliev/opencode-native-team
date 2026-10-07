# Spec Delta

## ADDED Requirements

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

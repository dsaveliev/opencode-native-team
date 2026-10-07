# Spec Delta

## Purpose

Live, zero-touch observation of a native-team run: a localhost web dashboard
that adopts any in-flight run, updates itself without manual reload, and can
be launched at any moment without interfering with the running session.

## ADDED Requirements

### Requirement: Localhost serve delivery

The dashboard SHALL be served by an HTTP server bound to 127.0.0.1 only, at a
port resolved from configuration. The server SHALL respond on `GET /` with
the dashboard page and on `GET /state` with the current dashboard data as
JSON. The server SHALL regenerate page data on demand at most once per
configured refresh interval.

#### Scenario: Opening the dashboard

- **WHEN** the server is running and a user opens `http://127.0.0.1:<port>/`
- **THEN** the dashboard page renders with data for its project directory

#### Scenario: Network isolation

- **WHEN** a client attempts to connect to the dashboard port from another
  machine
- **THEN** the connection is refused, because the server binds 127.0.0.1 only

### Requirement: Fixed port with explicit conflict failure

The port SHALL be a fixed value from the configuration chain, not
auto-allocated. If the port is already occupied, startup SHALL fail with a
message naming the occupying PID and command line; the server SHALL NOT
silently pick another port.

#### Scenario: Port already in use

- **WHEN** serve starts and the configured port is occupied by another
  process
- **THEN** startup exits non-zero and prints the occupying PID and its
  command line

### Requirement: Live page without manual reload

The dashboard page SHALL poll `/state` at the configured refresh interval
and update its content in place. A full browser reload SHALL NOT be required
to see current run state.

#### Scenario: Run progresses while page is open

- **WHEN** the page is open and a new agent session or commit appears in the
  observed run
- **THEN** within two refresh intervals the page shows it without any manual
  reload

### Requirement: In-flight run window adoption

When dashboard startup finds zero sessions for the project inside its
observation window, it SHALL roll the window start back to the earliest
recently-active session of that directory, so a run already in flight is
adopted. This applies to both fresh start and resume.

#### Scenario: Dashboard started after the run

- **WHEN** an orchestrator session for the project started before the
  dashboard was launched, and the current window contains no sessions
- **THEN** the window start moves to that session's creation time and the
  dashboard renders the in-flight run

### Requirement: Out-of-band launcher

A `team-dash` command SHALL locate runs without arguments: it queries the
session database for the most recently updated session per project directory
and picks the freshest. When more than one project has a recently-active
run, it SHALL present an interactive choice. It SHALL NOT send messages to,
or otherwise interact with, any running opencode session.

#### Scenario: One active run, no arguments

- **WHEN** `team-dash` is invoked with no arguments and exactly one project
  has a recently-active run
- **THEN** the dashboard for that project starts (or is reused), adopts the
  run window, and the browser opens per configuration

#### Scenario: Mid-run launch leaves the run untouched

- **WHEN** `team-dash` is invoked while an orchestrator session is working
- **THEN** the orchestrator session's conversation and progress are not
  affected

### Requirement: Configuration resolution chain

Dashboard configuration SHALL resolve per key as project-local
`.opencode/team-dashboard.json` over installation-wide
`~/.config/opencode/team-dashboard.json` over built-in defaults. Keys SHALL
include `mode`, `open_browser`, `refresh`, and `port`. Unknown keys SHALL be
ignored.

#### Scenario: Project overrides installation default

- **WHEN** the installation config sets `refresh: 5` and the project config
  sets `refresh: 2`
- **THEN** the dashboard for that project refreshes every 2 seconds while
  other projects use 5

### Requirement: Run-integrated auto-start

`/team` and `/team-change` pre-flight SHALL start serve-mode before the run
begins when resolved mode is `always` — including runs launched with
`--auto`. Mode `ask` SHALL ask exactly once per run in an interactive
session and skip silently when the question cannot be asked (headless,
`--auto`). Mode `never` SHALL not start anything.

#### Scenario: Auto run with mode always

- **WHEN** a run starts under `--auto` and resolved mode is `always`
- **THEN** the dashboard server is running before the orchestrator begins
  work, with a window covering the run start

#### Scenario: Ask mode in a headless run

- **WHEN** a run starts headless and resolved mode is `ask`
- **THEN** no question is asked and no dashboard starts

### Requirement: Read-only observation guarantee

The dashboard subsystem SHALL observe runs strictly read-only: the session
database SHALL be opened in read-only mode, and no component of the
subsystem (server, generator, launcher) SHALL write into the observed
project's working tree, git state, or sessions.

#### Scenario: Observation during a run

- **WHEN** the dashboard renders a live run
- **THEN** `git status` of the observed project shows no changes caused by
  the dashboard, and the session database is opened read-only

### Requirement: Final artifact after stop

On stop, the server SHALL leave a static snapshot of the last rendered page
at `tmp/team-dashboard.html` in the project directory, and SHALL terminate
its process.

#### Scenario: Stop preserves the snapshot

- **WHEN** `stop` is issued after a completed run
- **THEN** the server process exits and `tmp/team-dashboard.html` contains
  the final dashboard

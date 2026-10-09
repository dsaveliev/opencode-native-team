# Spec Delta

## MODIFIED Requirements

### Requirement: Out-of-band launcher

A `team-dash` command SHALL locate runs without arguments — it picks the
most recently active project directory and starts (or reuses) THE single
dashboard. With a directory argument it SHALL re-point the running
dashboard to that project. It SHALL NOT present an interactive choice in
the CLI: project selection happens in the dashboard UI. It SHALL NOT send
messages to, or otherwise interact with, any running opencode session. When
the dashboard is already serving another project, serve SHALL re-point it
to the requested directory instead of failing; a port held by a
non-dashboard process still fails loudly naming the holder.

#### Scenario: One active run, no arguments

- **WHEN** `team-dash` is invoked with no arguments and no dashboard is
  running
- **THEN** the dashboard for the freshest active project starts (or is
  reused), adopts the run window, and the browser opens per configuration

#### Scenario: Dashboard already serving another project

- **WHEN** a dashboard is running for project A and `team-dash` names
  project B
- **THEN** the dashboard observation is re-pointed to B and the browser
  opens; no second server is started and no port conflict is reported

#### Scenario: Mid-run launch leaves the run untouched

- **WHEN** `team-dash` is invoked while an orchestrator session is working
- **THEN** the orchestrator session's conversation and progress are not
  affected

### Requirement: Localhost serve delivery

The dashboard SHALL be served by an HTTP server bound to 127.0.0.1 only, at
a port resolved from configuration. The server SHALL respond on `GET /`
with the dashboard page and on `GET /state` with the current dashboard data
as JSON. The server SHALL regenerate page data on demand at most once per
configured refresh interval. The server MAY expose control endpoints that
act on verified opencode processes; all other non-GET requests SHALL be
rejected.

#### Scenario: Opening the dashboard

- **WHEN** the server is running and a user opens `http://127.0.0.1:<port>/`
- **THEN** the dashboard page renders with data for its project directory

#### Scenario: Network isolation

- **WHEN** a client attempts to connect to the dashboard port from another
  machine
- **THEN** the connection is refused, because the server binds 127.0.0.1 only

#### Scenario: Unknown POST target

- **WHEN** a client POSTs to any path other than the defined control
  endpoint
- **THEN** the request is rejected with an error status

### Requirement: Read-only observation guarantee

The dashboard subsystem SHALL observe runs strictly read-only: the session
database SHALL be opened in read-only mode, and no component of the
subsystem (server, generator, launcher) SHALL write into the observed
project's working tree, git state, or sessions. The single exception is the
control plane: a dedicated endpoint MAY deliver a stop signal to a verified
opencode process; it SHALL NOT write to the session database, the observed
project's tree, or any file of the target process.

#### Scenario: Observation during a run

- **WHEN** the dashboard renders a live run
- **THEN** `git status` of the observed project shows no changes caused by
  the dashboard, and the session database is opened read-only

#### Scenario: Control plane writes nothing but the signal

- **WHEN** a stop request is executed successfully
- **THEN** no file or database row is modified by the dashboard; only the
  process signal is delivered

## ADDED Requirements

### Requirement: Sessions and instances panel

The page SHALL show a sessions panel listing every running opencode
process with its pid, project directory, CPU time and command, together
with the sessions it hosts (title, agent, state, tokens) as derived from
the session database by directory and recent activity. Processes hosting
the observed project's sessions SHALL be visually distinguished. The panel
SHALL update on the regular refresh cycle.

#### Scenario: Several instances running

- **WHEN** two opencode processes run in different projects and the
  dashboard is open in one of them
- **THEN** the panel lists both, marking the observed project's process

#### Scenario: Instance stops elsewhere

- **WHEN** a listed opencode process exits
- **THEN** within two refresh intervals the panel no longer shows it

### Requirement: Verified process stop

The page SHALL offer a stop control per listed opencode process, guarded by
an explicit confirmation that names the consequence (all sessions of that
process end). A stop request SHALL be accepted only when the target pid is
alive, is an opencode process (verified against its command line at
execution time), and is not the dashboard's own process; the endpoint SHALL
require a JSON content type. Any other target SHALL be refused with an
error and no signal delivered.

#### Scenario: Stopping a stray run

- **WHEN** the user confirms stopping a listed opencode process hosting a
  runaway run
- **THEN** the process receives SIGTERM and the UI reports the outcome,
  including a warning if the process is still alive shortly after

#### Scenario: Forged target refused

- **WHEN** a stop request names a pid that is not an opencode process, or
  sends a non-JSON body
- **THEN** the request is rejected, no signal is sent, and the response
  names the reason

### Requirement: UI observation switching

The sessions panel SHALL offer a switching control per listed project:
activating it re-points the dashboard's read-only observation to that
project directory and refreshes the page. Switching SHALL NOT start a
second server, SHALL NOT write anything to the target project, and SHALL
validate the target directory. With several browser tabs open on the one
dashboard, the most recent switch wins for all of them.

#### Scenario: Switching from the panel

- **WHEN** the user activates the view control of another project's row
- **THEN** the page reloads showing that project's data on the same port

#### Scenario: Invalid target refused

- **WHEN** a switch request names a nonexistent directory
- **THEN** it is refused with a reason and the dashboard keeps observing
  the current project

# Spec Delta

## MODIFIED Requirements

### Requirement: Localhost serve delivery

The dashboard SHALL be served by an HTTP server bound to 127.0.0.1 only, at
a port resolved from configuration. The server SHALL respond on `GET /`
with the dashboard page and on `GET /state` with the current dashboard data
as JSON. The server SHALL regenerate page data on demand at most once per
configured refresh interval. The server MAY expose control endpoints that
act on verified opencode processes; all other non-GET requests SHALL be
rejected. Control endpoints SHALL accept requests only from a localhost
Host (`127.0.0.1:<port>` or `localhost:<port>`). Any model-authored or
session text embedded into page scripts SHALL be escaped for script
context so it cannot terminate a script element.

#### Scenario: Opening the dashboard

- **WHEN** the server is running and a user opens `http://127.0.0.1:<port>/`
- **THEN** the dashboard page renders with data for its project directory

#### Scenario: Network isolation

- **WHEN** a client attempts to connect to the dashboard port from another
  machine
- **THEN** the connection is refused, because the server binds 127.0.0.1 only

#### Scenario: Foreign Host refused

- **WHEN** a control request arrives with a non-localhost Host header
- **THEN** the request is refused before any body is read

#### Scenario: Session text cannot break out of the script island

- **WHEN** a work-log entry's text contains `</script>`
- **THEN** the rendered page still has exactly one script element end and
  the entry appears as plain text in the work log

### Requirement: Verified process stop

The page SHALL offer a stop control per listed opencode process, guarded by
an explicit confirmation that names the consequence (all sessions of that
process end). A stop request SHALL be accepted only when the target pid is
alive, IS an opencode process by executable identity — verified at
execution time against the live process table, not against the command-line
string — and is not the dashboard's own process; the endpoint SHALL require
a JSON content type. Any other target SHALL be refused with an error and no
signal delivered.

#### Scenario: Stopping a stray run

- **WHEN** the user confirms stopping a listed opencode process hosting a
  runaway run
- **THEN** the process receives SIGTERM and the UI reports the outcome,
  including a warning if the process is still alive shortly after

#### Scenario: Renamed binary refused

- **WHEN** a stop request names a pid whose executable identity is not
  opencode, even though its command line contains the word "opencode"
- **THEN** the request is refused, no signal is sent, and the response
  names the reason

#### Scenario: Forged target refused

- **WHEN** a stop request sends a non-JSON body, or a pid-shaped value
  that is not an integer
- **THEN** the request is rejected and the response names the reason

### Requirement: Single-owner server lifecycle

The dashboard server is a machine-wide singleton; its lifecycle state
(owner pid, currently observed project) SHALL be tracked in ONE
machine-level record per port, not in per-project files. `serve` for a
project already observed SHALL reuse the server; `serve` for a different
project SHALL re-point the running server; `stop` from any project
directory SHALL stop the singleton. `status` SHALL report the observed
project and the server liveness.

#### Scenario: Switch back and forth

- **WHEN** the dashboard is serving project A, is re-pointed to B, and
  then `serve A` runs again
- **THEN** the server is re-pointed back to A, and no second server starts

#### Scenario: Stop from any directory

- **WHEN** the dashboard serves project B and `stop` runs from project A's
  directory
- **THEN** the singleton is stopped and its owner record is removed

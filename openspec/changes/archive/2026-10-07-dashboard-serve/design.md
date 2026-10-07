# Design

## Context

The dashboard today is a regeneration loop (`team-dashboard.sh start` spawns
`while :; do gen-team-dashboard.py; sleep N; done`) writing
`tmp/team-dashboard.html`, opened as `file://`. The generator
(`gen-team-dashboard.py`, ~600 lines) already reads its sources purely
read-only: `~/.local/share/opencode/opencode.db` via sqlite `mode=ro`,
`git log`, openspec tasks. See proposal.md — Why for the UX defects this
change removes.

## Goals / Non-Goals

Goals: zero-touch monitoring; correct observation window regardless of
launch timing; launch channels that can never interfere with a running
session; a delivery layer that later admits control (POST) without redesign.

Non-Goals: control from the browser; SSE/WebSocket push; multi-run history;
remote access or authentication; per-agent drill-down beyond current panels.

## Decisions

### D1. Delivery: stdlib `http.server` on 127.0.0.1, fixed port (default 4731)

`scripts/dashboard_server.py` (~80 lines): `ThreadingHTTPServer` bound to
`127.0.0.1`, handler answers `GET /` (HTML) and `GET /state` (JSON). Render
happens on demand, memoized per refresh interval (mtime/TTL cache). The page
keeps its current markup plus a ~10-line poller: `fetch('/state')` every
`refresh` seconds, repaint. Alternatives: `file://` + `<meta refresh>`
(rejected: dead end for control/push, full-page flicker); WebSocket/SSE
(rejected now: polling at 2–5 s is indistinguishable for observation and
costs zero extra moving parts). POST is not routed; the handler's method
dispatch is the designated extension point for the future control layer.

### D2. Generator split: pure render module + thin CLI

`gen-team-dashboard.py` keeps all data loading and HTML rendering; the page
assembly moves into `render_html(data)` and a new `state_json(data)` returns
the same data dict serialized. The CLI wrapper continues to write
`tmp/team-dashboard.html` (used for the final snapshot). The server imports
the module; the loop is retired from the primary path but `once` remains for
debugging. Alternative: a separate renderer for the server (rejected:
two sources of truth for panels).

### D3. Window adoption inside the server, not the shell script

On every render pass, if the window (state `start_ms`) yields zero sessions
for the directory, the server queries the earliest session of that directory
with `time_updated >= now - 12h` and lowers `start_ms` to its `time_created`,
persisting the correction to `tmp/team-dashboard-state.json`. Placing the
rule in the render path means every launch channel (auto-start, `team-dash`,
manual `serve`) gets adoption for free; the shell script's `--resume` state
semantics stay as-is. 12 h "recently-active" horizon covers overnight runs
without adopting stale history.

### D4. Launcher `team-dash`: one SQL query, zero session contact

`bin/team-dash` (installed to `~/.config/opencode/bin/`, already on PATH in
the reference setup): opens the session DB read-only, `SELECT directory,
MAX(time_updated) ... WHERE time_updated >= now-12h GROUP BY directory`;
freshest wins; multiple candidates → numbered prompt on stderr, read choice;
then `exec team-dashboard.sh serve <dir>`. It never touches opencode
sessions, so it is safe at any point of a run. Alternative: `/team-watch`
slash command (rejected: a prompt into the running session interrupts the
orchestrator; exploration 2026-10-07).

### D5. Config chain: project > installation > defaults

Resolution per key: `.opencode/team-dashboard.json` in the project, then
`~/.config/opencode/team-dashboard.json`, then built-ins
(`mode: ask`, `open_browser: true`, `refresh: 5`, `port: 4731`). Project
installs via `install.sh` keep writing only the project file;
`--global` install additionally writes the installation file if absent.
Port conflicts: pre-bind check via `lsof -i :<port>`; on occupation, exit
non-zero printing PID + command line. No auto-allocation (predictability
over convenience; the knob exists in config).

### D6. Pre-flight switch and `--auto` fix

`/team` and `/team-change` pre-flight text changes from "start the loop" to
"start serve"; semantics: `always` → start unconditionally (this closes the
`--auto` silent skip: no question is needed), `ask` → one question tool call
in interactive sessions, skipped when questions can't be asked, `never` →
nothing. Default mode stays `ask` globally (conservative for existing
installs); the user sets `always` per installation — config, not code.

## Risks / Trade-offs

- [Port conflict across concurrent projects] → one server per port; second
  project fails loudly with PID; run on another port via that project's
  config. Documented in README.
- [Server left running after TUI closes] → pidfile + `status`/`stop` verbs;
  auto-start stops the server at run finish (pre-flight start implies stop at
  RUN-SUMMARY), `team-dash`-started servers persist until stopped.
- [Polling shows "stopped" state after server death] → poller catches fetch
  failure and paints a "server stopped — snapshot at tmp/" banner instead of
  silent staleness.
- [sqlite read under WAL while session writes] → already proven read-only
  concurrent access in the current loop; unchanged.
- [`team-dash` picks a wrong-but-fresh session (non-team opencode usage)] →
  candidates list shows directory + last update; user can always pass a path
  explicitly as an optional argument.

## Migration Plan

1. Ship server + launcher + config chain; `team-dashboard.sh` gains `serve`,
  `start`/`stop`/`status` map onto it (`start` = `serve` + browser open).
2. `install.sh --global` installs `bin/team-dash` and
  `scripts/dashboard_server.py`; existing global installs re-run
  `./install.sh --global` to pick them up.
3. Rollback: revert the commit; the old loop mode remains available via
  `once`/manual loop and the generator CLI is unchanged in behavior.

## Open Questions

None — port default (4731), adoption horizon (12 h), and default mode
(`ask` with user opt-in to `always`) were settled during exploration on
2026-10-07.

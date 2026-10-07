# Proposal

## Why

The first live run (qc-fop-service, 2026-10-07) exposed four UX defects in run
monitoring: a `--auto` run silently skips the ask-once dashboard offer; manual
launch requires knowing the script path and passing the project path as an
argument; `start` issued mid-run resets the observation window to "now",
rendering an in-flight run invisible (empty dashboard); and the served page is
static — the browser shows stale data until manually reloaded. Monitoring must
be zero-touch and must never interfere with a running session.

## What Changes

- **Serve-mode delivery**: the dashboard is served over HTTP on `127.0.0.1`
  at a fixed port from config (default 4731); the page polls `/state` and
  live-updates without reload. The file-regeneration loop is retired from the
  primary path.
- **Window adoption**: on start or resume, if the observation window contains
  zero sessions for the project, the window rolls back to the earliest
  recently-active session of that directory — an in-flight run is always
  adopted, regardless of when monitoring started.
- **Out-of-band launcher** `team-dash`: a no-arguments global command that
  finds the most recently updated active run across projects (interactive
  choice when several), adopts its window, and opens the browser. It never
  communicates with the running session, so it can be used at any moment
  without interrupting the orchestrator.
- **Per-installation config**: `~/.config/opencode/team-dashboard.json`
  (mode, open_browser, refresh, port) as installation-wide defaults; a
  project-local `.opencode/team-dashboard.json` overrides per key; lookup
  order project > global > built-in defaults.
- **Run-integrated auto-start**: `/team` and `/team-change` pre-flight
  switches from the regeneration loop to serve-mode; default mode for
  interactive TUI runs becomes `always`; `always` starts the dashboard even
  under `--auto` (closing the silent-skip defect); `ask` keeps the single
  pre-flight question; `never` stays off.
- **Control layer reserved, not built**: the server exposes GET only
  (`/`, `/state`); POST is deliberately absent but the layering must not
  preclude adding it later.

## Capabilities

### New Capabilities
- `run-dashboard`: live observation of a native-team run — delivery (localhost
  serve on a fixed port), observation-window adoption, launch channels
  (run-integrated auto-start and the out-of-band `team-dash` launcher),
  configuration resolution, and read-only guarantees toward the run.

### Modified Capabilities
- `run-briefs`: no requirement changes. The `/team` and `/team-change`
  pre-flight text is updated to reference serve-mode, but the pre-flight
  behavior contract (ask once, respect mode, headless skip) already exists in
  the commands; only its mechanism description changes.

## Out of Scope

- Browser-side control of the run (stop, nudge, message agents) — reserved as
  a future extension point, not implemented.
- SSE/WebSocket push (polling suffices), multi-run history UI, remote
  (non-localhost) access, authentication.

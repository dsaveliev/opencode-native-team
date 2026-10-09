# Proposal

## Why

The dashboard observes runs but cannot act on them. With several opencode
instances running concurrently (live at the time of writing: three TUIs
across qc-fop-service, qc-item-first and this repo), answering "which
sessions are alive and who hosts them" means shell archaeology, and stopping
a runaway run means hunting pids by hand. The control plane was reserved
(`POST` -> 405 "reserved for future control layer") — this change turns it
on for one narrow, verifiable action: stopping a hosting opencode process.

## What Changes

- New "Sessions & instances" panel on the dashboard: every running opencode
  process (pid, project directory from cwd, CPU time, command) with the
  sessions it hosts (from the session DB, matched by directory and recent
  activity): title, agent, state, tokens; entries of the observed project
  are visually primary.
- Stop control: a Stop button per process row behind an explicit
  confirmation; it calls `POST /control/stop {pid}` on the dashboard
  server, which SIGTERMs the pid only after verifying the target is an
  opencode process — never an arbitrary pid, never the dashboard's own
  process. The UI reports the outcome inline.
- Single-dashboard pivot: project selection moves from the CLI to the UI.
  `team-dash` drops its interactive picker (no arguments = freshest run;
  an argument re-points the running dashboard via
  `POST /control/switch {dir}`); the sessions panel gains a View button
  per project that re-points observation on the same fixed port. One
  dashboard per machine; no per-project ports, no port conflicts between
  projects.
- Endpoint hardening: JSON content-type required (blocks HTML-form
  cross-site posts), localhost/same-origin enforcement kept, observation
  pipeline (DB access, generation) stays read-only.
- Bug fixes discovered during the work, recorded as tasks with proofs.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `run-dashboard`: the read-only observation guarantee is scoped (data
  sources stay read-only; the control plane is one verified SIGTERM
  endpoint); serve delivery gains the control endpoint; a new requirement
  covers the sessions panel.

## Impact

- Files: `scripts/dashboard_server.py` (POST route + validation),
  `scripts/gen-team-dashboard.py` (process discovery, panel render, page
  JS), `scripts/test-dashboard.py`, `scripts/validate.py`, `README.md`.
- Behavioral: the dashboard page gains an actionable panel; `POST` is no
- Behavioral: the dashboard page gains an actionable panel; `POST` is no
  longer blanket-405. The launcher is part of this change (single-dashboard
  pivot): `team-dash` drops its interactive picker, `serve` re-points a
  running dashboard instead of conflicting between projects, and ownership
  of the machine-wide server moves from per-project pidfiles to one
  machine-level record (see design.md D6/D7). Config keys, port semantics
  and window adoption are unchanged.
- Risk accepted: SIGTERM to an opencode process ends all sessions hosted
  by that process — the confirmation dialog states this explicitly.

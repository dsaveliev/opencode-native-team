# Design

## Context

See proposal.md - Why. Recon (2026-10-07, live machine): opencode TUI
processes host their sessions in-process and listen on no TCP port, so no
HTTP API exists to address a session inside a TUI; the CLI offers only
destructive `session delete`. Three opencode processes were live, each with
a distinct cwd (`lsof -p <pid>` cwd -> project directory), and the session
DB keys sessions by the same directory. Consequence: the controllable unit
is the host process, and a session-to-process mapping is derivable from
(cwd, recent activity). The dashboard server already binds 127.0.0.1 and
serves GET / and GET /state; POST is blanket-405 today.

## Goals / Non-Goals

**Goals:**
- See every live opencode instance and its sessions on the dashboard.
- Stop an instance through the UI, with verification that the target is an
  opencode process, and a confirmation that states the blast radius.
- Keep the observation pipeline byte-for-byte read-only.
- One dashboard per machine: project selection lives in the UI, the CLI
  never asks questions.

**Non-Goals:**
- Addressing or stopping an individual session inside a TUI (impossible
  without an upstream API; revisit if opencode exposes one).
- Remote control: the endpoint stays on 127.0.0.1 like everything else.
- Multiple simultaneous observation targets (one view at a time; last
  switch wins across tabs — documented in the panel caption).

## Decisions

### D1: Process discovery via ps/lsof, sessions via DB

`opencode_processes()` (in the generator, cached per generation): `ps -eo
pid,etime,time,command` filtered by an anchored opencode match
`(^|/)opencode(\s|$)`; cwd via `lsof -p`; sessions matched from the
already-collected window sessions plus a fresh per-directory recent-session
query. Cost: one ps + one lsof per generation (already throttled by the
refresh TTL) — acceptable for a status page.

### D2: Control unit = verified opencode process, stop = SIGTERM

Sessions are not individually addressable (D1 recon); the stop unit is the
pid. SIGTERM (not SIGKILL): opencode persists session state on graceful
shutdown. The server re-verifies at execution time: pid alive, command
matches the anchored opencode pattern (checked against the live `ps`
command line, not the panel data — stale panel data must never authorize a
kill), pid != server's own pid. Post-signal: if still alive after ~2s,
respond with a warning (UI shows it); no escalation to SIGKILL (manual
decision, not an automatic one).

### D3: Endpoint shape and request hardening

`POST /control/stop` with body `{"pid": <int>}`:
- `Content-Type: application/json` required -> HTML `<form>` cannot send
  it, killing the cross-site form CSRF class without any token machinery.
- Host header must be `127.0.0.1:<port>` (redundant with binding, cheap).
- Responses: 200 {ok, alive_after}, 400 bad shape/content-type, 403 not an
  opencode process / self / not found, each with a one-line reason.
- All other non-GET stay 405.

### D4: Panel UX

One panel "Sessions & instances" after Agents: a table — pid, project
(basename of cwd, `this project` badge when it equals the observed dir),
CPU time, command (truncated), hosted sessions (agent badge + title +
state), Stop button per row. Confirmation via native `confirm()` naming
pid + project + "all its sessions end". Result inline: transient banner
(ok / warned / refused + reason). The panel rides the existing repaint
cycle; `state_sig` gains the process count so instance changes repaint.

### D5: Spec evolution wording

"Read-only observation guarantee" is scoped: data sources stay read-only;
the sole write-like action is signal delivery by the verified endpoint
(which itself writes nothing). "Localhost serve delivery" gains "control
endpoints MAY exist; everything else non-GET is rejected".

### D6: Single dashboard, re-pointable target (CLI-pivot)

One dashboard server per machine on the fixed port. `POST /control/switch
{"dir": ...}` re-points observation: validate the directory exists, swap
the in-memory target under the generation lock, drop the cached generation
(the next request renders the new project; per-project window state files
already exist). Nothing is written to the target project. The sessions
panel carries a View button per project row; several open tabs share the
one target — the most recent switch wins for all of them (stated in the
panel caption). This removes the per-project port conflict class entirely:
serving project B while A's dashboard runs is a switch, not an error.

### D7: team-dash without a dialog

`team-dash [dir]`: with an argument — exec `team-dashboard.sh serve <dir>`;
without — pick the freshest recently-active directory (12h horizon,
existing-dead dirs filtered) and exec the same. `serve` itself grows the
single-dashboard semantics: pidfile reuse for the same project, else probe
`/state` — a live dashboard of another project is switched (`switch_to` +
`wait_ours` verifies the new project name answers), a foreign port holder
still fails loudly. The CLI picker and its numbered dialog are deleted.

## Risks / Trade-offs

- cwd-based session mapping misattributes sessions when two instances share
  a directory (e.g. two TUIs in one repo): the panel shows both processes
  with the same session list — the list is "sessions of this directory",
  which stays true; blast radius is stated per process anyway.
- SIGTERM ends every session of the process, including an interactive one
  the user forgot about — mitigated by the explicit confirmation text, not
  by technology.
- Anchored command match could miss exotic opencode launches (symlinks with
  other names) — those simply don't get a working Stop (fail-closed).

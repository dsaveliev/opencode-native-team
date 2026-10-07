# Tasks

## 1. Generator refactor (render module)

- [x] 1.1 Extract page assembly in `scripts/gen-team-dashboard.py` into
  `render_html(data) -> str` and add `state_json(data) -> dict` returning the
  same aggregated data as JSON; keep the CLI behavior (writes
  `tmp/team-dashboard.html`) unchanged. Verify:
  `python3 scripts/gen-team-dashboard.py <dir>` output byte-identical to
  before refactor (diff the generated HTML in a scratch dir).
- [x] 1.2 Add the `/state` poller to the page: ~10 lines fetching
  `/state` every configured `refresh` seconds and repainting; on fetch
  failure show a "server stopped — snapshot at tmp/team-dashboard.html"
  banner instead of stale content. Verify: open served page, kill server,
  banner appears within one interval.

## 2. Serve mode (`scripts/dashboard_server.py` + `team-dashboard.sh`)

- [x] 2.1 Create `scripts/dashboard_server.py`: stdlib
  `ThreadingHTTPServer` on 127.0.0.1, routes `GET /` (HTML, TTL-cached per
  refresh interval) and `GET /state` (JSON), imports the generator module;
  unknown paths → 404; POST → 405 with a "reserved for future control"
  message. Verify: `curl -s localhost:4731/state | python3 -m json.tool`
  returns the data dict; `curl -X POST localhost:4731/x` → 405.
- [x] 2.2 Port resolution + conflict failure: read `port` through the
  config chain (D5); pre-bind check `lsof -i :<port>`; on occupation exit
  non-zero printing occupying PID and command line. Verify: start one
  server, start a second → error names the first server's PID.
- [x] 2.3 Window adoption in the render path (D3): if zero sessions for the
  directory inside the window, lower `start_ms` to the earliest session with
  `time_updated >= now-12h`, persist to
  `tmp/team-dashboard-state.json`. Verify: with a session DB fixture whose
  session predates `start_ms` by minutes, serve renders that session;
  `scripts/test-dashboard-adoption.py` asserts the correction.
- [x] 2.4 `team-dashboard.sh`: add `serve` verb (spawn server, pidfile at
  `tmp/team-dashboard-server.pid`, browser open per config); `start` becomes
  an alias of `serve`; `stop` kills the server and writes the final
  `tmp/team-dashboard.html` snapshot via generator `once`; `status` reports
  server + port. Verify: start → curl OK → stop → process gone, snapshot
  file exists.

## 3. Launcher `team-dash`

- [x] 3.1 Create `bin/team-dash`: no-arg resolution via read-only session DB
  query (freshest `MAX(time_updated)` per directory within 12 h); multiple
  candidates → numbered stderr prompt + read choice; optional explicit path
  argument bypasses detection; then `exec team-dashboard.sh serve <dir>`.
  Verify: with the live qc-fop-service run, `team-dash` selects that project
  and the served page shows the orchestrator session.

## 4. Config chain

- [x] 4.1 Config resolution `project > ~/.config/opencode > defaults` for
  keys `mode`, `open_browser`, `refresh`, `port`; unknown keys ignored.
  Update `examples/team-dashboard.json` with the full key set and comments.
  Verify: unit check in `scripts/test-dashboard-adoption.py` — global
  `refresh: 5` + project `refresh: 2` resolves to 2.

## 5. Run-integrated auto-start

- [x] 5.1 Update `commands/team.md` and `commands/team-change.md` pre-flight:
  start serve before the run when resolved mode is `always` (including
  `--auto` runs — no question needed); `ask` keeps the single question in
  interactive sessions and skips silently when questions can't be asked;
  `never` off. Stop at run finish when the team started the server.
  Verify: run `/team` in the sandbox with mode `always` under a TUI —
  server up before orchestrator work; RUN-SUMMARY step stops it.

## 6. Install, docs, validation

- [x] 6.1 `install.sh`: copy `scripts/dashboard_server.py` to scripts dir
  and `bin/team-dash` to `~/.config/opencode/bin/` (global) or
  `.opencode/bin/` (project); write installation-level
  `~/.config/opencode/team-dashboard.json` defaults only if absent.
  Verify: fresh `./install.sh --global` in a scratch HOME → files present,
  `team-dash --help` runs.
- [x] 6.2 README: replace the loop description with serve UX — auto-start
  modes, `team-dash`, config chain, fixed port + conflict behavior, final
  snapshot. Verify: `python3 scripts/validate.py` passes (doc paths real).
- [x] 6.3 `scripts/validate.py`: extend the dashboard config check to
  accept the new keys (`port`) in `examples/team-dashboard.json`; keep
  bash -n green. Verify: `python3 scripts/validate.py` → ALL CHECKS PASSED.

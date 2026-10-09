# Tasks

## 1. Data layer

- [x] 1.1 `opencode_processes()` in gen-team-dashboard.py: ps scan with the
  anchored opencode match, lsof cwd per pid, etime/cputime/command; map
  window sessions (and a fresh recent-session query per cwd directory) to
  each process; export via collect_data. Verify: unit check on synthetic ps
  output in test-dashboard.py (match `/opt/homebrew/bin/opencode --auto`;
  reject `opencode-fake`, `myopencode`, `opencode.py`).
- [x] 1.2 Sessions panel data: per-process row (pid, project basename,
  is_this_project, cpu, cmd excerpt, sessions list with agent/state/tokens)
  rendered into the page and included in the repaint signature (process
  count joins state_sig). Verify: fixture render contains the panel and
  rows; sig changes when the process list changes (unit).

## 2. Control plane

- [x] 2.1 `POST /control/stop` in dashboard_server.py per design D2/D3:
  JSON content-type required, pid shape check, live re-verification
  (anchored opencode match, not self), SIGTERM, alive-after-2s warning,
  typed error responses with reasons; all other non-GET stays 405. Verify:
  curl battery — non-JSON body 400; unknown pid 403; non-opencode pid 403
  (a spawned `sleep`); a fake `opencode` argv0 process 403; happy path on a
  real short-lived `opencode run` child exits it.
- [x] 2.2 Page JS: Stop button per row -> confirm(pid, project, "all its
  sessions end") -> fetch POST -> inline result banner (ok / warned /
  refused + reason); button disabled while pending; expansion keys keep
  working for the new panel. Verify: `node --check` on the embedded
  script; manual click-through documented in the run log.

## 3. Tests, validation, docs

- [x] 3.1 test-dashboard.py: panel render assertions (fixture), ps-match
  unit checks (1.1), server battery scripted from the existing serve test
  (start fixture server on the hermetic port, run the 2.1 curl cases,
  stop). Verify: `python3 scripts/test-dashboard.py` passes end-to-end.
- [x] 3.2 validate.py: no new structural checks needed beyond green
  suites; keep bash -n / ast.parse coverage for the touched files. Verify:
  `python3 scripts/validate.py` -> ALL CHECKS PASSED.
- [x] 3.3 README: Sessions & instances panel + stop semantics + safety
  rails (verified opencode-only, confirmation, no SIGKILL escalation).
  Verify: `rg 'Sessions & instances' README.md`; doc paths check green.

## 4. Bugs found along the way

- [x] 4.1 `opencode_processes()` parsed `ps` with `split(None, 4)` and
  matched the regex against the command REMAINDER only (`--auto`), so zero
  processes were ever found (caught by the first live render: 0 stop
  buttons with 3 instances running). Fix: `split(None, 3)` — full command
  in one field. Verify: `python3 scripts/gen-team-dashboard.py .` ->
  exit 0, panel lists the 3 live opencode pids (77622/52483/93720).
- [x] 4.2 `alive_after` lied via zombies: `kill -0` succeeds on an
  unreaped child, so a successfully SIGTERMed target still reported
  alive_after=true when its parent had not reaped it (reproduced through
  the serve-wrapper battery). Fix: liveness = `ps -o stat=` non-empty and
  not starting with Z. Verify: `python3 scripts/test-dashboard.py` ->
  "verified opencode stop 200" ok (alive_after false, exit -15).

## 5. Single-dashboard pivot (CLI without dialogs)

- [x] 5.1 `POST /control/switch {"dir": ...}` in dashboard_server.py (D6):
  directory validation, target swap under the generation lock, cached
  generation dropped; same JSON content-type hardening as stop. Verify:
  battery — switch 200, bad dir 403, bad body 400 (test-dashboard.py).
- [x] 5.2 View button per project row (generator panel) + page JS: POST
  switch -> reload; failures via the inline banner. Verify: render contains
  `viewbtn` rows; `node --check` on the embedded script.
- [x] 5.3 `bin/team-dash` rewritten without the interactive picker (D7):
  argument = serve that dir; no argument = freshest active dir; dead
  directories filtered. `team-dashboard.sh serve` re-points a running
  dashboard instead of conflicting (probe /state -> switch -> wait_ours);
  a foreign port holder still fails loudly. Verify: serve B on a taken
  dashboard port now reports "re-pointed" and /state shows project B
  (test-dashboard.py); `bash -n` both scripts.
- [x] 5.4 Artifacts: proposal bullet, design D6/D7, spec delta — MODIFIED
  "Out-of-band launcher" (no CLI dialog, re-point semantics), ADDED "UI
  observation switching". Verify: `openspec validate
  dashboard-session-control` -> valid.

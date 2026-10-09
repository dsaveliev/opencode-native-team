# Tasks

## 1. Control-plane fixes

- [x] 1.1 G1: `js_json()` helper in gen-team-dashboard.py; use it for the
  embedded `LOGSEED` constant (design D1). Verify: unit check —
  `js_json({"x": "</script><img onerror>"})` contains no literal
  `</script>` and parses back to the original object; rendered page
  contains no literal `</script>` inside the seed.
- [x] 1.2 G2: Host allowlist in do_POST for both control endpoints (D2),
  before body read; 403 on foreign Host. Verify: battery — POST with
  `Host: evil.example` on /control/stop and /control/switch -> 403.
- [x] 1.3 G3: identity by executable identity (D3): `ps comm` basename
  `opencode`/`opencode-cli`, aliveness re-checked at signal time. Verify:
  battery — symlinked `/bin/sleep` as `opencode` -> 403 (fixture inverts);
  real **copy** of `/bin/sleep` named `opencode` -> 200 and process dead;
  unknown pid -> 403; non-opencode pid -> 403.
- [x] 1.4 G4: machine-level owner record (D4) in team-dashboard.sh;
  per-project pidfiles removed; serve switches A -> B -> A; stop from any
  dir; stale record recovery. Verify: `bash -n`; battery — after
  re-point to fi2, `serve fx1` again -> "re-pointed" and /state project
  back to fi1; `stop fi2` stops the server (fixture dir independent).

## 2. Docs and tests

- [x] 2.1 test-dashboard.py: rewrite the owner/serve half of the battery
  for D4 semantics (no per-project pidfile assertions), add Host-rejection
  and poisoned-text cases (1.1/1.2). Verify: `python3
  scripts/test-dashboard.py` passes end-to-end.
- [x] 2.2 README: control-plane section — Host enforcement, executable
  identity, machine-level owner record, script-context escaping. Verify:
  `rg` finds the updated section; validate [9] stays green.
- [x] 2.3 `./install.sh --global` refresh; live smoke — dashboard up,
  Sessions panel renders, foreign-Host POST refused. Verify: install
  diff-clean; battery green.

## 3. Bugs found along the way

- [x] 3.1 serve adoption gap: a running dashboard left by the old
  per-project-pidfile scheme had no owner record, so serve tried to start a
  second server instead of re-pointing (live smoke: "port serves ANOTHER
  project's dashboard" against a pre-hardening server). Fix: probe_ours
  adopted the server and wrote the owner record from the port holder pid.
  Verify: `bash scripts/team-dashboard.sh serve .` -> "re-pointed ...
  (pid ...)"; status shows the observed project.
- [x] 3.2 macOS identity facts measured during 1.3: comm = exec path
  (symlinks preserved, so a symlink named opencode passes comm checks),
  lsof txt resolves the real binary (/bin/sleep) -> the refused fixture,
  and copies of signed binaries are killed by AMFI -> positive fixture
  compiles a real binary instead. Verified by the inverted battery
  (symlink 403, compiled opencode 200).
- [x] 3.3 openspec refused the first delta draft: a MODIFIED requirement
  must carry ALL scenarios of the current spec ("Network isolation" was
  dropped). Fix: scenario restored; `openspec validate` clean with the
  archive-order constraint recorded in design.md.

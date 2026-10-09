# Design

## Context

See proposal.md - Why. The control plane (dashboard-session-control,
committed 129adb3) introduced four concrete defects found by a five-axis
audit of the working tree. All four are confirmed in code; the identity
weakness is proven by this repo's own test fixture (a `/bin/sleep`
symlink named `opencode` receives SIGTERM and the test asserts 200). The
server is a machine-wide singleton on a fixed port, but the launcher still
tracks it with per-project pidfiles, which produces the A -> B lifecycle
bugs. Scope of this change closes exactly these four defects; the
data-honesty and evidence-truncation gaps belong to the next changes.

**Archive order constraint:** this delta MODIFIES the "Verified process
stop" requirement that the still-unarchived dashboard-session-control
delta creates. Archive dashboard-session-control first, then this change.

## Goals / Non-Goals

**Goals:**
- Model text can never escape its script context on the control page.
- Control endpoints refuse non-localhost Hosts before reading bodies.
- Signal delivery is gated on executable identity, not command-line text.
- One owner record for the singleton; serve/stop behave directory-agnostic.

**Non-Goals:**
- Reworking how processes are discovered for the panel (cmdline regex for
  display stays — it lists real TUIs correctly).
- Data honesty (PARTIAL/UNAVAILABLE), evidence truncation, run identity,
  receipts — separate changes in the roadmap.

## Decisions

### D1: Script-context escaping via one helper

All JSON embedded into the page's script context goes through
`js_json(obj) = json.dumps(obj).replace("<", "\\u003c")`. Valid JS escape,
parses to `<` at runtime, and the literal `</script` sequence can never
appear in the HTML source. Covers `LOGSEED` (session text — the actual
sink) and future embedded payloads. Rendering-side `html.escape` remains
for HTML contexts (they are separate sinks). Verification: fixture unit
check on the helper + `node --check` on the rendered page's script with a
poisoned work-log text (the fixture part pipeline is unit-checked via the
helper; page-level poisoning is exercised through the adoption test's
synthetic parts where practical).

### D2: Host allowlist on control endpoints

In `do_POST`, before reading the body: reject unless
`Host` is `127.0.0.1:<port>` or `localhost:<port>` with 403
`{"error": "non-localhost host"}`. JSON content-type check stays after
it (both must pass). GET endpoints unchanged (read-only page).

### D3: Executable identity, not command line

`stop_opencode` verifies the target's **resolved executable**: `ps comm`
gives the exec path (symlinks preserved); the `lsof` txt entry (first
non-dyld) is the resolved binary. Identity = basename matches
`opencode`/`opencode-cli`. Consequences measured on macOS:

- `/bin/sleep` symlinked as `opencode` resolves to `sleep` → refused (the
  fixture inverts: 403 expected).
- `bash -c 'exec -a opencode-fake sleep'` → `/bin/bash` → refused.
- a genuine executable compiled as `opencode` → accepted. Note: macOS AMFI
  kills copies of *signed* binaries, so the positive fixture compiles a
  real binary instead of copying one.

The check→signal TOCTOU (pid reuse) is accepted at desktop scale,
mitigated by re-checking aliveness at signal time; recorded for the
durability roadmap.

### D4: One machine-level owner record

`~/.local/state/team-dashboard-<port>.json` (`{pid, dir}`) written by
`serve`, removed by `stop`. `serve`: read record -> if pid alive and is a
dashboard_server process: current dir equals target -> "already running";
else probe_ours + switch + wait_ours -> "re-pointed". Stale record -> rm
and start fresh. `stop` (any directory): kill from the record -> final
snapshot for the record's dir (the observed project) plus the passed
directory's snapshot? One snapshot for the observed project is the useful
one — snapshot the record's dir, report it. Per-project pidfiles and
`tmp/team-dashboard.pid` are removed; `once`/`status` semantics unchanged
(status reads the record).

## Risks / Trade-offs

- `comm` check refuses exotic launches (e.g. `node opencode.js`) that the
  cmdline regex accepted — fail-closed, which is the intended direction;
  genuine opencode binaries are comm-named.
- The check->signal TOCTOU remains (pid could be reused between check and
  kill); accepted at desktop scale, recorded for the durability roadmap.
- Machine-level state adds a new global directory (`~/.local/state`),
  created with restrictive default umask; no secrets stored.

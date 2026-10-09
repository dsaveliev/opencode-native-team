# Proposal

## Why

The control plane shipped in dashboard-session-control has four confirmed
defects that weaken the safety claims of the feature:

1. **Script-context injection sink.** Session text is embedded into an
   inline `<script>` via raw `json.dumps`; a message containing
   `</script>` ends the JS island early and turns model-authored text into
   HTML/JS on the page that hosts the stop/switch controls.
2. **Missing Host enforcement.** The design required a localhost Host
   check on control endpoints; the handler never checks it. Same-origin
   policy blocks reads cross-origin, but the check is the cheap
   defence-in-depth that the design promised and reviewers expect.
3. **Process identity by name only.** Verification matches the command
   line text, so `/bin/sleep` symlinked as `opencode` passes — proven by
   our own positive test fixture. The signal may be delivered to a process
   that is not opencode.
4. **Per-project pidfiles against a singleton server.** The machine-wide
   dashboard is tracked by per-project pidfiles: after switching A -> B,
   `serve A` reports "already running" without switching back, and
   `stop` from B cannot stop the shared server.

## What Changes

- Embedded JSON constants (work-log seed, and any future script-context
  payloads) are escaped for script context (`<` -> `\u003c`), so model
  text can never terminate the script island; covered by a fixture unit
  check and by `node --check` on the rendered page.
- Control endpoints enforce `Host in {127.0.0.1:<port>, localhost:<port>}`;
  foreign Host requests are refused before any body is read.
- Stop verification identifies the target by its live executable identity
  (`ps comm`, basename `opencode`/`opencode-cli`) plus aliveness, not by
  the command-line string: renamed binaries (symlinks) are refused. The
  happy-path fixture uses a real copy of a binary named `opencode`.
- One machine-level owner record (`~/.local/state/team-dashboard-<port>`
  with pid + current project) replaces per-project pidfiles: `serve`
  switches back to A from B, `stop` works from any directory, stale
  records are recovered.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `run-dashboard`: verified-process stop gains executable-identity
  verification; localhost serve delivery gains Host enforcement and
  script-context escaping; the singleton lifecycle becomes a
  single-owner-record requirement.

## Impact

- Files: `scripts/dashboard_server.py` (Host check, identity), 
  `scripts/gen-team-dashboard.py` (escaping helper),
  `scripts/team-dashboard.sh` (machine-level owner record),
  `scripts/test-dashboard.py` (flipped fixtures + new cases),
  `README.md` (control-plane safety section).
- Behavior: renamed non-opencode binaries are refused (the old symlink
  fixture inverts); serve/stop lifecycle is project-agnostic.
- Not in scope (next changes): partial/unavailable data honesty,
  evidence truncation (`LIMIT 300`), run identity, receipts.

---
description: Run the native-team dev cycle (plan → code → test → review → commit)
agent: orchestrator
---

Pre-flight — live dashboard (config chain: project `.opencode/team-dashboard.json`
over `~/.config/opencode/team-dashboard.json` over defaults; keys: mode,
refresh, open_browser, port):
- mode "never" -> skip silently. mode "always" -> start now — unconditionally,
  including `--auto` runs (no question is needed).
- mode "ask" (or chain absent) -> ALWAYS attempt the question tool exactly once:
  "Create live dashboard for this run?". Do NOT decide yourself whether a user
  is present — if the tool is unavailable or errors, THAT is the headless
  signal: skip silently and continue. Never skip the attempt by judging the
  session "probably headless".
- Resolve the dashboard script once: `.opencode/scripts/team-dashboard.sh`
  in the project, else `~/.config/opencode/scripts/team-dashboard.sh`
  (global install); if neither exists, skip the dashboard silently.
- Start BEFORE any run work: `bash <resolved script> serve "$(pwd)"` —
  serves `http://127.0.0.1:<port>/` (fixed port from config) and adopts an
  in-flight window automatically.
- On finish — success or failure: `bash <resolved script> stop "$(pwd)"`
  (stops the server; the final snapshot stays at tmp/team-dashboard.html).

Run log (final step, before the dashboard stop):
- Resolve GEN the same way as the dashboard script's directory:
  `.opencode/scripts/gen-team-dashboard.py` in the project, else
  `~/.config/opencode/scripts/gen-team-dashboard.py`; if neither exists,
  skip silently.
- Export the log:
  `mkdir -p tmp/run-logs/$(date +%F)-team && python3 "$GEN" --export "$(pwd)" > tmp/run-logs/$(date +%F)-team/RUN-LOG.md`
- Then APPEND a `## Recommendations` section to that RUN-LOG.md yourself:
  friction observed this run (slow tasks, retries, permission denials,
  repeated tool errors) translated into concrete, actionable improvement
  suggestions for the team framework (prompts, permissions, wave sizing).

Assignment:

$ARGUMENTS

If TASK.md exists in the repo root, read it first — it takes precedence and is
the assignment. Follow your contract: openspec change lifecycle, skill mapping
table, delegation order coder → tester → reviewer, commits with task
references. Do not ask questions: resolve ambiguities yourself and record each
one in DECISIONS.md (question — decision — rationale). All artifacts stay
inside the repo; temp files in ./tmp/.

Run brief: if RUN-BRIEF.md exists in the repo root, read it before starting;
its sections are an execution-policy overlay (HOW only: may narrow execution,
never grant or redefine acceptance); read-only for the whole run.
On finish of a briefed run: write the run summary per the brief's §11
(RUN-SUMMARY.md); the dispositions ledger is BLOCKERS.md.

---
description: Run the native-team dev cycle (plan → code → test → review → commit)
agent: orchestrator
---

Pre-flight — live dashboard (config: `.opencode/team-dashboard.json`, default mode "ask"):
- mode "never" -> skip silently. mode "always" -> start now.
- mode "ask" (or file absent) -> ALWAYS attempt the question tool exactly once:
  "Create live dashboard for this run?". Do NOT decide yourself whether a user
  is present — if the tool is unavailable or errors, THAT is the headless
  signal: skip silently and continue. Never skip the attempt by judging the
  session "probably headless".
- Resolve the dashboard script once: `.opencode/scripts/team-dashboard.sh`
  in the project, else `~/.config/opencode/scripts/team-dashboard.sh`
  (global install); if neither exists, skip the dashboard silently.
- Start: `bash <resolved script> start "$(pwd)"`
- On finish — success or failure: `bash <resolved script> stop "$(pwd)"`

Assignment:

$ARGUMENTS

If TASK.md exists in the repo root, read it first — it takes precedence and is
the assignment. Follow your contract: openspec change lifecycle, skill mapping
table, delegation order coder → tester → reviewer, commits with task
references. Do not ask questions: resolve ambiguities yourself and record each
one in DECISIONS.md (question — decision — rationale). All artifacts stay
inside the repo; temp files in ./tmp/.

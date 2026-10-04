---
description: Run the native-team dev cycle (plan → code → test → review → commit)
agent: orchestrator
---

Pre-flight — live dashboard (config: `.opencode/team-dashboard.json`, default mode "ask"):
- mode "never" -> skip silently. mode "always" -> start now.
- mode "ask" (or file absent) -> if a user is present in this session, ask ONCE
  via the question tool: "Create live dashboard for this run?"; headless run
  (no user) -> skip silently.
- Start: `bash .opencode/scripts/team-dashboard.sh start "$(pwd)"`
- On finish — success or failure: `bash .opencode/scripts/team-dashboard.sh stop "$(pwd)"`

Assignment:

$ARGUMENTS

If TASK.md exists in the repo root, read it first — it takes precedence and is
the assignment. Follow your contract: openspec change lifecycle, skill mapping
table, delegation order coder → tester → reviewer, commits with task
references. Do not ask questions: resolve ambiguities yourself and record each
one in DECISIONS.md (question — decision — rationale). All artifacts stay
inside the repo; temp files in ./tmp/.

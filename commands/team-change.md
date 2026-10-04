---
description: Implement an existing openspec change (artifacts already written)
agent: orchestrator
---

Pre-flight — live dashboard (config: `.opencode/team-dashboard.json`, default mode "ask"):
- mode "never" -> skip silently. mode "always" -> start now.
- mode "ask" (or file absent) -> if a user is present in this session, ask ONCE
  via the question tool: "Create live dashboard for this run?"; headless run
  (no user) -> skip silently.
- Start: `bash .opencode/scripts/team-dashboard.sh start "$(pwd)"`
- On finish — success or failure: `bash .opencode/scripts/team-dashboard.sh stop "$(pwd)"`

Implement the existing openspec change: $1

Mode: implementation-only (the change artifacts already exist).

- Read openspec/changes/$1/proposal.md, design.md and tasks.md first.
- Do NOT create a new change; do NOT rewrite proposal/design (marking tasks
  [x] with proofs and adding observability comments is allowed).
- Verify the change with `openspec validate $1` before implementing; if
  validation fails, report and stop.
- Work on branch `feat/$1` created from the current default branch; do not
  touch main. Merge/PR is the owner's action, not yours.
- Then follow your contract from the implementation stage: skill mapping,
  waves, delegation coder → tester → reviewer, evidence-based [x], commits
  with task references (`feat: ... (change $1, task N.M)`).

If the change directory does not exist, list available changes and stop.

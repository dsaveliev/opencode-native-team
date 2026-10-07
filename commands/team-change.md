---
description: Implement an existing openspec change (artifacts already written)
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

Implement the existing openspec change: $1

Mode: implementation-only (the change artifacts already exist).

Run brief: if RUN-BRIEF.md exists in the repo root, apply it after hydrating
the change state — a read-only execution-policy overlay (HOW only).
On finish of a briefed run: write the summary per the brief's §11; ledger —
BLOCKERS.md (schema in the RUN-BRIEF template §11).

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

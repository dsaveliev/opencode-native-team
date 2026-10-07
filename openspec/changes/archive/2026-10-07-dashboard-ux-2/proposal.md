# Proposal

## Why

The first live wave-based run (qc-fop-service, `/team-change`) exposed a wrong
mental model in the dashboard stage indicator and a set of presentation
defects: the stepper derives stage from the most recently active subagent
role, so each new wave flips it backward (review -> code) and destroys trust
in it; agents and activity lanes sort alphabetically instead of by first
activity; expanded rows collapse on every repaint; the work log loses older
entries on reload; tool errors are counted but not shown.

## What Changes

- Stage indicator: derive the macro run stage from task progress (no
  backward jumps), and show the instantaneous activity ("now: coder, wave
  3") as a separate secondary label.
- Ordering: agents table and activity chart lanes ordered by the agent's
  first activity in the run window, not by name.
- Task tree: softer palette and tree guides; top-level tasks collapse into
  expandable rows (subtasks inside); the task currently being worked on is
  highlighted; each top-level task shows elapsed time and, once at least one
  top-level task has completed, a projected "≈" estimate for the remaining
  ones plus a run-total projection (median of completed task durations; no
  changes to tasks.md schema).
- Summary tiles become clickable anchors to the tasks/commits/agents panels.
- Repaints preserve the user's expanded rows (keyed re-open after repaint).
- Work log: client-side buffer (localStorage) accumulates entries across
  page reloads; no new server-side writes to the observed project.
- Tool Errors panel: a side-by-side neighbor of Work Log (like Tasks |
  Commits) listing recent errored tool calls (tool, agent, time, input
  head) with a total count.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `run-dashboard`: stage semantics, ordering, task-tree presentation,
  repaint behavior, work-log persistence, and a tool-errors panel change or
  extend existing requirements of the capability.

## Impact

- Files: `scripts/gen-team-dashboard.py` (data + render), page JS (poller),
  `scripts/test-dashboard.py` (fixture assertions), `scripts/validate.py`
  (checks), `README.md` (UX notes). `scripts/dashboard_server.py`,
  `bin/team-dash`, `scripts/team-dashboard.sh`, config chain and port
  behavior are untouched.
- No breaking changes: page structure and endpoints stay the same; the
  read-only observation guarantee is strengthened (work-log history moves
  to the client, no server-side log accumulation).

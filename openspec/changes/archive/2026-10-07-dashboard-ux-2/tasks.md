# Tasks

## 1. Data layer (gen-team-dashboard.py)

- [x] 1.1 Stage model: replace role-derived stage with task-progress macro
  stage (D1: plan/code/review/done mapping) plus `now` activity label
  (freshest subagent role, 10-min horizon) and wave counter (coder sessions
  after first reviewer session); emit both through `state_json`. Verify:
  unit check with fixture sessions/tasks (reviewer done -> coder wave B
  starts -> macro stage does not regress; label shows coder + wave 2).
- [x] 1.2 Agent ordering: build agent first-activity map (`min(created)` per
  agent in window) and use it for the agents table and activity chart lanes
  (D2). Verify: fixture render lists agents in first-activity order, not
  alphabetical.
- [x] 1.3 Tool error entries: extend `load_parts` to emit the last ~30
  errored tool calls (tool, session, time, first ~120 chars of
  `state.input`) next to the existing counts (D5). Verify: unit check
  against fixture DB parts with `status: error`.
- [x] 1.4 Task timing + projection: compute per-top-level-task elapsed and,
  once one top-level task is complete, median-based "~" projections for
  remaining tasks and the run total (D6: wave-span durations from subagent
  titles, whole-run fallback). Verify: unit check - one completed task of
  30m yields "~" estimates for the others; no estimates before first
  completion.

## 2. Render layer (HTML)

- [x] 2.1 Task tree restructure: top-level tasks as `<details>` rows
  (summary = checkbox, title, elapsed, optional "~eta"; subtasks inside),
  active-task highlight from the active subagent title's task ids (D7).
  Verify: fixture render contains per-task `<details>`, a highlighted row
  when the fixture's active session title names a task.
- [x] 2.2 Task tree styling: muted palette, thin indentation guides, softer
  counters and headers (D7, CSS only). Verify: visual check of fixture
  render; no structural markup changes beyond classes/styles.
- [x] 2.3 Work Log | Tool Errors panels: render as side-by-side neighbors
  (like Tasks | Commits), errors panel shows entries from 1.3 plus the
  total count (D5). Verify: fixture render contains both panels on one
  row; error entry shows tool, agent, time, excerpt.
- [x] 2.4 Summary tile anchors: tasks/commits/spawns tiles link to
  `#panel-tasks` / `#panel-commits` / `#panel-agents`; panels get the ids
  (D8). Verify: fixture render has anchor-wrapped tiles and matching panel
  ids.
- [x] 2.5 Stepper + label markup: macro-stage stepper from 1.1 plus the
  secondary "now: <role>, wave N" label next to it. Verify: fixture render
  shows both; stepper state matches the macro stage.

## 3. Page JS (poller)

- [x] 3.1 Expansion preservation: before repaint, snapshot open
  `<details>` keys (work log: agent+ts; commits: sha; tasks: change+title);
  re-open matching details after repaint; drop keys whose entries vanished
  (D3). Verify: manual - expand a row, wait for a signature change, row
  stays open; `node --check` on the embedded script.
- [x] 3.2 Work log client buffer: localStorage keyed by directory-hash +
  window start (D4); merge `/state` log entries newest-wins, cap 500, drop
  on window change; render merged history. Verify: manual - reload page
  mid-run, older entries survive; changing window start clears the buffer.

## 4. Tests, validation, docs

- [x] 4.1 Extend `scripts/test-dashboard.py` fixture and assertions:
  macro-stage value, agent order, task `<details>` + highlight, ETA "~"
  markers, both panels present, tile anchors. Verify: `python3
  scripts/test-dashboard.py` passes end-to-end.
- [x] 4.2 Extend `scripts/validate.py`: keep existing checks green with the
  new assertions from 4.1 wired in (fixture test already runs there); no
  new file checks needed. Verify: `python3 scripts/validate.py` -> ALL
  CHECKS PASSED.
- [x] 4.3 README: update the dashboard section (stage semantics, panels,
  expansion/reload behavior, ETA meaning). Verify: docs mention all new
  behaviors; `rg` finds each feature named.

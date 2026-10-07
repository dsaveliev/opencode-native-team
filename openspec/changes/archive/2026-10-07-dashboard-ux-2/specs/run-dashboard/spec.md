# Spec Delta

## MODIFIED Requirements

### Requirement: Live page without manual reload

The dashboard page SHALL poll `/state` at the configured refresh interval
and update its content in place. A full browser reload SHALL NOT be required
to see current run state. An in-place update SHALL preserve the expansion
state of collapsible page elements the user has opened: after an update,
elements the user expanded SHALL remain expanded, and elements the user
collapsed SHALL remain collapsed. Elements whose underlying entry no longer
exists after an update SHALL be removed.

#### Scenario: Run progresses while page is open

- **WHEN** the page is open and a new agent session or commit appears in the
  observed run
- **THEN** within two refresh intervals the page shows it without any manual
  reload

#### Scenario: Expanded row survives a repaint

- **WHEN** the user expands a collapsible row (work log entry, commit, or
  task) and new data arrives that changes the page
- **THEN** that row is still rendered expanded after the update, without the
  user re-opening it

## ADDED Requirements

### Requirement: Run stage derived from task progress

The macro run stage shown on the page SHALL be derived from run task
progress and run lifecycle state, and SHALL NOT move backward while the run
continues. A separate secondary label SHALL show the instantaneous current
activity (role of the most recently active subagent) and, when the run
executes in waves, the wave count. The instantaneous activity MAY change in
any direction; it is the macro stage that SHALL be monotonic.

#### Scenario: New coding wave after a review wave

- **WHEN** a reviewer session finishes for wave N and a coder session for
  wave N+1 becomes active while unchecked tasks remain
- **THEN** the macro stage stays at or beyond its previous value (it does
  not jump back) and the secondary label shows the coder and wave N+1

#### Scenario: Final review with all tasks done

- **WHEN** every task in the run is checked and a reviewer session is
  active
- **THEN** the macro stage shows review

### Requirement: Agents ordered by first activity

The agents panel and the activity chart lanes SHALL order agents by the time
of their first activity inside the run window, not by name or identifier.

#### Scenario: Late-joining agent appears last

- **WHEN** an agent type first appears in the run after other agents are
  already listed
- **THEN** it is placed below the previously active agents in both the
  agents panel and the activity chart

### Requirement: Collapsible task tree with active highlight

Top-level tasks in the tasks panel SHALL be collapsible: a top-level task
row SHALL be expandable to reveal its subtasks, with subtasks hidden until
expanded. The task (or tasks) referenced by the currently active subagent
session SHALL be visually highlighted while that session is active.

#### Scenario: Expanding a top-level task

- **WHEN** the user clicks a collapsed top-level task
- **THEN** its subtasks become visible; clicking again hides them

#### Scenario: Active task highlight

- **WHEN** the active subagent session's title references task 2.1
- **THEN** task 2.1 is visually distinct from non-active tasks

### Requirement: Per-task elapsed and projection

Each top-level task SHALL display its elapsed time. Once at least one
top-level task in the run has completed, remaining top-level tasks and the
run total SHALL additionally display a projected duration estimate derived
from the durations of completed top-level tasks, clearly marked as an
estimate. Before any top-level task has completed, no estimate SHALL be
shown. Task sources SHALL NOT be modified to carry estimates.

#### Scenario: Projection after first completion

- **WHEN** one top-level task has completed in 30 minutes and two remain
- **THEN** each remaining top-level task and the run total show a visible
  estimate marked as approximate

### Requirement: Summary tiles link to panels

The summary tiles for tasks, commits, and subagent spawns SHALL navigate to
the corresponding panels (tasks, commits, agents) when activated.

#### Scenario: Activating the tasks tile

- **WHEN** the user clicks the tasks-done summary tile
- **THEN** the tasks panel is brought into view

### Requirement: Work log history across reloads

The work log SHALL retain entries across full page reloads within the same
run window by accumulating them in client-side storage; the dashboard
subsystem SHALL NOT write any additional files to the observed project for
this purpose. Accumulated entries SHALL be merged with entries from the
current server response, and SHALL be discarded when the run window
changes.

#### Scenario: Reload during a run

- **WHEN** the user reloads the page while a run is in flight and older
  entries have already rotated out of the current server response
- **THEN** those older entries are still visible from the client-side
  accumulation

### Requirement: Tool errors panel

The page SHALL show a tool errors panel adjacent to the work log, listing
recent errored tool calls with their tool name, agent, time, and a short
excerpt of the failing call input, plus the total error count for the run
window.

#### Scenario: Tool fails during a run

- **WHEN** a tool call in the observed run finishes with an error
- **THEN** within two refresh intervals the tool errors panel shows its
  tool name, agent, time, and input excerpt, and the total count includes it

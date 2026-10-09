# Run log — opencode-native-team

- window: 06:36 – 11:33  (elapsed 100h57m)
- tasks: 95/95 · commits: 44 · tokens in/out: 5904k/558k

## Waves / sessions
| role | span | dur | title |
|---|---|---|---|
| build | 06:36–06:36 | 0m09s | Completing TASK.md assignment |
| build | 21:01–21:06 | 4m35s | Установка opencode-native-team без команд /team |
| build | 09:27–10:38 | 1h10m | Интеграция context-mode и Ponytail в opencode-native-team |
| build | 15:14–11:33 | 20h18m | Long-running agent prompt research |
| plan | 20:55–20:56 | 0m36s | Team dashboard run stage & UI fixes |

## Task timings
### dashboard-session-control
- [x] 1.1 `opencode_processes()` in gen-team-dashboard.py: ps scan with the (100h57m)
- [x] 1.2 Sessions panel data: per-process row (pid, project basename, (100h57m)
- [x] 2.1 `POST /control/stop` in dashboard_server.py per design D2/D3: (100h57m)
- [x] 2.2 Page JS: Stop button per row -> confirm(pid, project, "all its (100h57m)
- [x] 3.1 test-dashboard.py: panel render assertions (fixture), ps-match (100h57m)
- [x] 3.2 validate.py: no new structural checks needed beyond green (100h57m)
- [x] 3.3 README: Sessions & instances panel + stop semantics + safety (100h57m)
- [x] 4.1 `opencode_processes()` parsed `ps` with `split(None, 4)` and (100h57m)
- [x] 4.2 `alive_after` lied via zombies: `kill -0` succeeds on an (100h57m)
### archive: 2026-10-07-dashboard-serve
- [x] 1.1 Extract page assembly in `scripts/gen-team-dashboard.py` into (100h57m)
- [x] 1.2 Add the `/state` poller to the page: ~10 lines fetching (100h57m)
- [x] 2.1 Create `scripts/dashboard_server.py`: stdlib (100h57m)
- [x] 2.2 Port resolution + conflict failure: read `port` through the (100h57m)
- [x] 2.3 Window adoption in the render path (D3): if zero sessions for the (100h57m)
- [x] 2.4 `team-dashboard.sh`: add `serve` verb (spawn server, pidfile at (100h57m)
- [x] 3.1 Create `bin/team-dash`: no-arg resolution via read-only session DB (100h57m)
- [x] 4.1 Config resolution `project > ~/.config/opencode > defaults` for (100h57m)
- [x] 5.1 Update `commands/team.md` and `commands/team-change.md` pre-flight: (100h57m)
- [x] 6.1 `install.sh`: copy `scripts/dashboard_server.py` to scripts dir (100h57m)
- [x] 6.2 README: replace the loop description with serve UX — auto-start (100h57m)
- [x] 6.3 `scripts/validate.py`: extend the dashboard config check to (100h57m)
### archive: 2026-10-07-dashboard-ux-2
- [x] 1.1 Stage model: replace role-derived stage with task-progress macro (100h57m)
- [x] 1.2 Agent ordering: build agent first-activity map (`min(created)` per (100h57m)
- [x] 1.3 Tool error entries: extend `load_parts` to emit the last ~30 (100h57m)
- [x] 1.4 Task timing + projection: compute per-top-level-task elapsed and, (100h57m)
- [x] 2.1 Task tree restructure: top-level tasks as `<details>` rows (100h57m)
- [x] 2.2 Task tree styling: muted palette, thin indentation guides, softer (100h57m)
- [x] 2.3 Work Log | Tool Errors panels: render as side-by-side neighbors (100h57m)
- [x] 2.4 Summary tile anchors: tasks/commits/spawns tiles link to (100h57m)
- [x] 2.5 Stepper + label markup: macro-stage stepper from 1.1 plus the (100h57m)
- [x] 3.1 Expansion preservation: before repaint, snapshot open (100h57m)
- [x] 3.2 Work log client buffer: localStorage keyed by directory-hash + (100h57m)
- [x] 4.1 Extend `scripts/test-dashboard.py` fixture and assertions: (100h57m)
- [x] 4.2 Extend `scripts/validate.py`: keep existing checks green with the (100h57m)
- [x] 4.3 README: update the dashboard section (stage semantics, panels, (100h57m)
### archive: 2026-10-07-integrate-context-mode-ponytail
- [x] 1.1 Add `ctx_*` deny keys to frontmatter per design D2 (short internal (100h57m)
- [x] 1.2 Add a `validate.py` step enforcing the matrix in both directions: (100h57m)
- [x] 2.1 Create `scripts/integrate-plugins.py` (python3 stdlib `json` only): (100h57m)
- [x] 2.2 Create `scripts/test-integrate-plugins.py` (assert-based tmpdir (100h57m)
- [x] 2.3 Extend `install.sh` (project mode only, after the example-config (100h57m)
- [x] 3.1 Add `"plugin": ["context-mode", "@dietrichgebert/ponytail"]` to (100h57m)
- [x] 3.2 Write `docs/integrations.md`: architecture split diagram (OpenSpec → (100h57m)
- [x] 3.3 Update `README.md` (short "Execution plugins" section linking (100h57m)
- [x] 4.1 Live two-plugin smoke test (requires Node >= 22.5 and both plugins (100h57m)
- [x] 4.2 Final regression sweep: `python3 scripts/validate.py` → ALL CHECKS (100h57m)
### archive: 2026-10-07-long-running-recovery
- [x] 1.1 `agents/planner.md`: replace the free-text dependency sentence with (100h57m)
- [x] 2.1 `agents/orchestrator.md`: add Recovery/Propagation/Resume clauses to (100h57m)
- [x] 2.2 `agents/orchestrator.md`: always-on No-progress directive in Main (100h57m)
- [x] 2.3 Raise the orchestrator cap 105 → 115: SPEC.md cap line with updated (100h57m)
- [x] 3.1 `examples/RUN-BRIEF.md` §10: make defaults explicit — retries (100h57m)
- [x] 4.1 `docs/design-decisions.md`: add #16 (executed recovery: min-retry, (100h57m)
- [x] 4.2 Create `docs/recovery-experiment.md`: runbook with two criteria — (100h57m)
- [x] 5.1 `python3 scripts/validate.py`. Verify: ALL CHECKS PASSED, exit 0. (100h57m)
- [x] 5.2 Forced-failure textual walkthrough per runbook section 1: map each (100h57m)
- [x] 5.3 `openspec validate long-running-recovery --strict`. Verify: exit 0. (100h57m)
### archive: 2026-10-07-prompt-template
- [x] 1.1 Write the template: immutable-categories header (MAY constrain / (100h57m)
- [x] 1.2 Add the unit/run state and signal taxonomy block (design D3) and a (100h57m)
- [x] 2.1 `commands/team.md`: after the TASK.md-precedence block add the opt-in (100h57m)
- [x] 2.2 `commands/team-change.md`: same overlay lines with the resume nuance — (100h57m)
- [x] 3.1 Add the conditional run-controls block (~10 lines) to (100h57m)
- [x] 3.2 Trim redundant orchestrator lines (~4: overlap between Resources / (100h57m)
- [x] 4.1 `docs/design-decisions.md`: add decision #14 (run brief as the fourth (100h57m)
- [x] 4.2 `README.md`: add a "Run briefs (long-running runs)" section near the (100h57m)
- [x] 5.1 Run `python3 scripts/validate.py` and the repo's other CI-side checks (100h57m)
- [x] 5.2 Experimental criterion A walkthrough, evidence recorded: (a) brief (100h57m)
- [x] 5.3 `openspec validate prompt-template --strict`. Verify: exit 0. (100h57m)
### archive: 2026-10-07-run-brief-interactive
- [x] 1.1 `scripts/gen-run-brief.py`: template loading and section split; (100h57m)
- [x] 1.2 Full mode (`--full`) and `--non-interactive` flags (name, mode, (100h57m)
- [x] 2.1 `scripts/test-gen-run-brief.py`: three fixture tests (quick shape; (100h57m)
- [x] 3.1 `commands/team-brief.md` (≤ 8 lines): collect answers via the (100h57m)
- [x] 3.2 `install.sh`: copy `gen-run-brief.py` into `.opencode/scripts/` (100h57m)
- [x] 4.1 README: one-two lines in the run-briefs section (generator + (100h57m)
- [x] 4.2 Integration: `python3 scripts/validate.py` green; self-test green; (100h57m)
### archive: 2026-10-07-run-hardening
- [x] 1.1 Replace `external_directory: deny` with the toolchain-cache (100h57m)
- [x] 1.2 Add the orchestrator bash ruleset (D2: allow `*`, deny (100h57m)
- [x] 1.3 Mirror the cache allowlist in `examples/opencode.json.example` (100h57m)
- [x] 2.1 Denial collection (D3): extend `load_parts` in (100h57m)
- [x] 2.2 Export mode (D4): `--export <dir>` renders `RUN-LOG.md` from (100h57m)
- [x] 2.3 Final step in `commands/team.md` and `commands/team-change.md`: (100h57m)
- [x] 3.1 Extend `scripts/test-dashboard.py`: export smoke on the fixture (100h57m)
- [x] 3.2 Extend `scripts/validate.py`: contract frontmatter sanity - all (100h57m)
- [x] 3.3 README: permissions section (cache allowlist rationale, module (100h57m)
- [x] 4.1 With user consent: extend `~/.config/opencode/opencode.json` - (100h57m)
- [x] 4.2 Re-run `./install.sh --global` to refresh agent contracts; user (100h57m)
### archive: 2026-10-07-run-observability
- [x] 1.1 `commands/team.md`: after the run-brief paragraph add the finish (100h57m)
- [x] 1.2 `commands/team-change.md`: same finish hook (+2 lines). Verify: (100h57m)
- [x] 2.1 `examples/RUN-BRIEF.md` §11: concretize to the RUN-SUMMARY contract (100h57m)
- [x] 2.2 `scripts/validate.py`: canonical-heading check for (100h57m)
- [x] 3.1 `scripts/setup-sandbox.sh`: disposable repo with TASK.md, minimal (100h57m)
- [x] 4.1 `docs/design-decisions.md` #17 (run observability artifacts: summary, (100h57m)
- [x] 4.2 `docs/recovery-experiment.md`: recording section now points at (100h57m)
- [x] 4.3 `README.md`: extend the run-briefs section with 2–3 lines (summary, (100h57m)
- [x] 5.1 `python3 scripts/validate.py`. Verify: ALL CHECKS PASSED, exit 0. (100h57m)
- [x] 5.2 RUN-SUMMARY structure walkthrough: map each content item of spec (100h57m)
- [x] 5.3 `openspec validate run-observability --strict`. Verify: exit 0. (100h57m)

## Tool errors
- 05:58 build `edit` — {"filePath": "/Users/dmitrii.savelyev/Sync/Repo/opencode-native-team/scripts/dashboard_server.py", "
- 23:47 build `edit` — {"filePath": "/Users/dmitrii.savelyev/Sync/Repo/opencode-native-team/scripts/team-dashboard.sh", "ne

## Permission denials
- none

## Commits
- `17a4783` run-hardening: toolchain cache permissions, run logs + retro
- `7f1a441` dashboard-ux-2: progress-based stage, task tree, panels, refresh-safe UX
- `078c967` dashboard-serve: localhost serve mode, team-dash launcher, window adoption
- `de5aaf4` chore: gitignore local tooling (.opencode/) and python bytecode (__pycache__)
- `052ce2b` cleanup: remove Russian-language originals (v1-v4 task + review-v5.1.1-6), repo is English-only
- `a1e1364` run-briefs: run-brief control layer + generator + sandbox drills (changes prompt-template, long-running-recovery, run-observability, run-brief-interactive)
- `705c5ea` openspec: change integrate-context-mode-ponytail (archived) + main spec plugin-integrations
- `edc4a7b` config+docs: recommended plugin entries + execution-plugins doc
- `1d847b5` installer: idempotent plugin-entry merge for .opencode/opencode.json
- `6311952` agents+validate: context-mode ctx_* permission matrix + minimalism precedence
- `689872b` install: --global put dashboard scripts into ~/.config/opencode/.opencode/scripts (nested .opencode inside the global config) — DASH_DIR now follows the global layout (~/.config/opencode/scripts); /team and /team-change resolve the dashboard script project-local first, then fall back to the global copy, skipping silently when neither exists; README de-drifted
- `dd606bd` commands: same ask-mode fix in /team-change (attempt the question tool; its failure is the headless signal)
- `907b528` commands: dashboard ask-mode must ATTEMPT the question tool and let its failure signal headless — agents misjudge 'user present' and skip silently in interactive sessions (live case)
- `a5a111d` v5.1.7: round-8 — LOC counted in Python (kills shell injection via filenames AND the wc total double-count, proven by fixture probes), coverage opt-in (default 0, failure cached 5x ttl, go/go.mod gates, declared in example+README), pause cancels pending reload, guarded storage helpers, per-feed scroll restore, .tx flex-shrink, escaped error string, subagent-recency stage detection, 'spawned' header, undated archives excluded; README/SPEC de-drifted; tester contract gains language-agnostic structural invariants (entrypoint-glue test, injected clock, leak check)
- `ea521ff` dashboard: real hover popups (data-tip + positioned div) for commit diamonds and session bars — native SVG <title> tooltips are unreliable and the hover transform broke hit-testing
- `de978e0` dashboard: replace cumulative commit chart with swimlane activity timeline — wall-clock axis anchored at run start (stable tick labels, no shifting), per-agent session bars (who/when/duration), commit diamonds with full-message tooltips; Tasks+Commits panels share a row between Agents and Work log
- `1c627b3` dashboard: cards equal-width filling one row, click-to-expand work log and commit messages (full text, CSS ellipsis), commit nodes enlarge on hover with full-message tooltip, run-stage label on stepper
- `d4faf73` dashboard round-2 fixes: quote SVG classes (unquoted + self-closing slash made class='grid/' — path and grid invisible, root cause of the blank chart), refresh button back (pause kept), cards in one row, agent column 150px, right-aligned time column, task tree with wave headers + bullet-depth indentation
- `881e022` dashboard: explicit svg width/height (Safari collapsed height:auto svg to zero — chart rendered blank), LOC card (tracked code files), test-coverage card (go test -cover, TTL-cached, coverage_ttl config; placeholder when off/no Go); fixture checks for all three
- `492608f` dashboard: revert cards to row; stack Agents/Tasks/Work log/Commits panels full-width one per row; fix commit timeline (path duplicated point 0 and dropped the last, circles one step above the line)
- `b6846c7` Revert "dashboard: cards stacked full-width, one per row (value + label baseline)"
- `09b732d` dashboard: cards stacked full-width, one per row (value + label baseline)
- `e69cea7` fix dashboard: stage detection crashed on timestamps instead of texts (loop died silently, HTML frozen — 'all idle' was staleness, not inactivity)
- `73bb270` dashboard: activity threshold 90s -> 180s (long tool calls / test runs marked agents idle while working)
- `899dd4b` v5.1.6: round-7 dashboard blockers — start resets window (--resume for mid-run), archive-date run window, cfgget booleans, tasks panel rebuilt (waves/todo-first), safe path quoting (positional args), config-driven JS timer + pause/scroll-restore, atomic write, subagent spawns via parent_id, stage stepper, badges, now-marker, title state, dark theme, responsive; behavioral fixture test (14 checks) wired into validator; G-1 rounds journal enforced; install keeps tmp/ out of git
- `678fbf3` dashboard: filter sessions by run start (previous runs in same dir polluted tokens/agents/log), preserve state file on restart (mid-run dashboard restart no longer shifts the window), drop dead run_start
- `84dd11a` fix dashboard: commits panel sliced the joined HTML to 40 chars (messages truncated) — slice the entry list to 40 instead
- `e4714ea` dashboard UI: role-colored work log and agent names (orchestrator/coder/tester/reviewer), bolder header with spacing under subtitle, manual refresh button
- `b9bea14` live dashboard: gen-team-dashboard.py (agents/tasks/log/commits/tokens/ETA, archived-changes aware, SOH-separated git format) + team-dashboard.sh (start/stop/once/status loop manager) + ask-mode config example + preambles in /team and /team-change + install to .opencode/scripts + validator (syntax+schema) + README; full start/refresh/stop cycle smoke-tested
- `119292b` stack skills: per-project .opencode/team-skills.json (name/source/stages) + scripts/sync-skills.sh (install/verify/--update with sha256 skills.lock), orchestrator loads stage extensions, example config, validator schema check, README section
- `6e434d9` work-flow adaptation: /team-change <id> command (implementation-only mode, feat-branch, no main), orchestrator existing-change clause, install copies all commands, validator covers both commands, README section for existing openspec projects
- `5143227` ci: fetch-depth 0 (step 9 resolves review SHAs against full history; shallow clones previously failed CI with 4 false mismatches) + shallow-aware validator with a clear fix message
- `e007a9b` v5.1.5: round-6 — superset guard (JSON reviewer map must contain every frontmatter rule, not just the catch-all), R-5 check inverted per probed semantics (top-level allows required for headless, shipped in example), Round 4 table + six-round header in reviews.md, Commit/Коммит in subject regex
- `fe27924` docs: autonomous-run permission note (headless needs top-level allow; frontmatter denies take precedence — probed)
- `66ac926` v5.1.4: round-5 — complete-map permission rule (probed: partial JSON bash map is defeated by frontmatter catch-all; live run caught reviewer go test denials), artifact committed (docs/artifacts/), mislabeled round-2 file deleted + honest traceability, validator per-step ok-guards + doc-reality step (paths exist, review subject SHAs resolve/unique), judge A4 default-LIMIT check (19 checks)
- `761aaa6` add /team command (opencode commands/, installed by install.sh), --global install mode, CI badge + Usage section in README, validator step for command frontmatter
- `88fa38e` v5.1.3: round-4 fixes — validator catches Cyrillic (not just CJK) + permission PRESENCE invariants (negative-tested), judge phase A verifies default 2s window behaviorally (A3) + PORT honored, MANIFEST upstream pins restored (agent-skills@1401c8b), review round 2 reconstructed into docs/, M-8 became check-model-routing.sh + saved artifact, judge count reconciled to 18 across docs
- `0600d42` v5.1.2: round-3 blockers — scalar edit/external_directory (path globs don't cross /), duplicate YAML key, strict full-hash MANIFEST over all 12 vendored files, judge ./... + statement-weighted cmd coverage + deterministic WINDOW_SECONDS=10 phase B, README fixes (npm install, anonymized n=1 results, security table matches code), scripts/validate.py + CI, docs/reviews.md; remove tools/ (SPEC violation)
- `82fd3f7` tools: dashboard-gen.py with v5 arm
- `ecb8051` fix: webfetch and external_directory as string 'deny', not glob object
- `ffd7efb` v5.1.1: fix all review blockers — judge B5/B6 window consistency, weighted coverage via cover-func, real sha256 verification, reviewer test permissions in example config, no global permission override, expanded git+separator denies, contract limit raised to 90, TASK.md translated, README rewritten for publication
- `266708d` v5.1: security hardening (task/external_dir/webfetch deny, bash separator guards), judge score+exit-code+weighted-coverage, tester contradiction fixed, reviewer-after-tester, language-agnostic via opencode.json
- `9af1fd7` v5: English contracts, docs, vendor with MANIFEST + 10 skill hashes
- `41ccb64` init: v5 structure — SPEC, agents (5 contracts v5), install, examples, docs placeholders
## Recommendations

- cwd-based process->session mapping: two TUIs in one directory show the same
  session list on both rows — acceptable (the list is "sessions of this
  directory"), but a future `session_inbox`-based mapping would be exact if
  opencode ever exposes per-session host metadata.
- The 2 s `alive_after` wait blocks a request thread per stop; fine at this
  scale, switch to an async re-check if stops become frequent.
- Found-and-fixed en route (see tasks 4.1-4.2): ps field-splitting hid all
  processes; zombie children lied about liveness. Both prove the value of
  the scripted control battery — keep it in test-dashboard.py.
- `opencode session delete` (CLI) remains the only per-session tool and is
  destructive; if opencode ships a session-abort API, add per-session Stop
  next to the process-level one.

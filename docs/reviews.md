# Review Rounds

Eight external review rounds shaped v5 → v5.1.6. Original reviews were
received in Russian. Round 1 lives in git history only
(`git show 266708d:docs/audit-v5.md`). Rounds 3+ are committed as
`docs/review-v5.1.*.md`. The round-2 original (`review-v5.1.md`, of commit
`266708d`, findings R-1..R-11) was never committed and is not reproduced
verbatim here — only its English summary table below. English summaries
with resolutions:

## Round 1 — initial audit (of v5)

| Finding | Resolution (v5.1, `266708d`) |
|---|---|
| No structural protection vs nested delegation | `task: deny` for subagents |
| No external-directory guard | `external_directory` deny added |
| Reviewer verdict without running tests | reviewer-after-tester ordering + test commands |
| Global bash allow undermines per-agent denies | per-agent permissions only |
| Unweighted "coverage" metric | statement-weighted via `go tool cover` |

## Round 2 — review of v5.1

| Finding | Resolution (v5.1.1, `ffd7efb`, `ecb8051`) |
|---|---|
| R-1 judge B5 flaky (window vs sleep) | two-phase judge: defaults + WINDOW_SECONDS=10 |
| R-2 fake "weighted coverage" | `go tool cover -func` total + profile-parsed cmd aggregate |
| R-3 placebo hash verification | real sha256 vs MANIFEST, abort on mismatch |
| R-4 reviewer cannot run tests | test/build allows in example config |
| R-5 global bash allow | removed; agent-scoped only |
| R-9 orchestrator over line limit | SPEC limit raised to 90 (dual-layer wiring) |
| Others (docs, translation, README) | applied |

## Round 3 — review of v5.1.1

| Finding | Resolution |
|---|---|
| N-1 duplicate YAML key in coder.md | removed; `scripts/validate.py` now rejects duplicates (strict loader) |
| N-2 path-glob `*` does not cross `/`: `edit`/`external_directory` object forms were root-only | scalar forms: `edit: deny`, `external_directory: deny` |
| N-3 prefix hash comparison | strict full-length equality + missing/extra file detection |
| M-1 judge hardcoded `./cmd/... ./internal/...` | `./...` |
| M-2 cmd coverage was per-function mean | statement-weighted, parsed from the profile |
| M-3 B2-B4 timing flakiness | phase B runs with WINDOW_SECONDS=10 (env override is contract) |
| M-4 README `brew install openspec` vs npm package | npm command |
| M-5 n=1 results attributed to named third parties | anonymized + "data on request" |
| M-6 Security Model overstated protections | table matches code; every vendored file hashed |
| M-7 redundant deny patterns; newline uncaught | `*||*`/`*>>*` removed, newline pattern added |
| M-8 `.opencode/opencode.json` read-path unverified | `scripts/check-model-routing.sh` + committed pilot artifact `docs/artifacts/native-v5-models-routing.txt` |
| tools/dashboard-gen.py violated SPEC (external writes) | removed from repo |
| C1 no CI | `.github/workflows/ci.yml` runs `scripts/validate.py` |

## Round 4 — review of v5.1.2

| Finding | Resolution |
|---|---|
| V-1 validator checked CJK but not Cyrillic (the actual failure class) | step [8]: Cyrillic U+0400-04FF added; whitelist narrowed |
| V-2 deny FORMS checked, PRESENCE not | presence invariants (task-deny, edit/webfetch deny, git denies, allow-list, mode, temperature) — negative-tested |
| V-3 judge count 17 vs "15/15" in four doc places | reconciled to 18 (now 19 after A4) + comparability notes in historical tables |
| J-1 documented 2s window untested behaviorally | judge A3: sleep 3 → count must be 1 |
| J-2 Phase A ignored PORT | passed |
| D-1 upstream pins lost from MANIFEST | pins restored (agent-skills@1401c8b), validator requires 40-hex SHA |
| V-4 validator silently skipped YAML checks without PyYAML | hard requirement, exit 1 |
| D-3 round 2 absent from history | attempted reconstruction (turned out mislabeled — fixed in round 5) |

## Round 5 — review of v5.1.3

| Finding | Resolution |
|---|---|
| T-1 artifact promised in reviews.md but absent | artifact committed: `docs/artifacts/native-v5-models-routing.txt`; validator step [10] now checks doc paths against disk |
| T-2 "reconstructed round 2" was actually round 3 text | mislabeled file deleted; traceability statement made honest; round-2 original still absent (summary only) |
| T-3 ok printed after FAIL (substring guards) | per-step error counting; ok only when the step added zero errors |
| M-8 second half: permission merge unverified | verified empirically — and it was broken: reviewer `go test` denied in the live run (frontmatter catch-all defeats JSON allow). Fix: complete-map rule (probed twice), fixed `examples/opencode.json.example`, README note |
| default LIMIT untested | judge A4: `Incr(n=5) -> count=5`, then `Incr(n=1) -> RESOURCE_EXHAUSTED` at defaults (two calls, no timing pressure) |
| dead code in validate.py | strict loader via subclass, no global mutation |
## Round 6 — review of v5.1.4 (commits 761aaa6..fe27924)

| Finding | Resolution |
|---|---|
| C-1 complete-map guarded by a single key | superset check: every frontmatter rule must be present in the JSON override |
| C-2 R-5 check guarded a refuted hypothesis | inverted: top-level allows required (headless primary mode), shipped in example |
| C-3 reviewer map duplicated, drift unguarded | closed by the superset check |
| C-5 Russian-only subject keyword in the regex | Commit (EN) + Cyrillic equivalent, ignore-case |

## Round 7 — review of v5.1.5 (`docs/review-v5.1.5.md`)

| Finding | Resolution |
|---|---|
| D-1 start no longer resets the window (678fbf3 regression) | start = new run by default; `--resume` for mid-run restarts |
| D-2 archived changes leaked into the run window | archive date parsed from dir name; only same-day-or-later count |
| D-3 open_browser True vs "true" | cfgget lowercases values |
| D-4 Tasks panel dead branch | panel rebuilt: waves as sections, todo emphasized, done dimmed |
| D-5 project path interpolated into bash -c / python -c | positional args; nothing interpolated |
| D-6 refresh config ignored by the page | generator reads config; JS timer instead of meta refresh |
| D-7 non-atomic HTML write | tmp + os.replace |
| D-8 no behavioral tests in repo | `scripts/test-dashboard.py` fixture (14 checks), wired into validate.py |
| moderate (pid reuse, tmp gitignore, parts LIMIT, fmt_k) | pid+cmdline check; install.sh appends tmp/ to .gitignore; LIMIT 300; decimal k |
| UX (pause/scroll, stepper, badges, now marker, title, %, dark, responsive) | all implemented |
| G-1 round 6 section missing while its fixes shipped | sections added; validator now enforces one section per review file |

## Round 8 — review of v5.1.6 (`docs/review-v5.1.6.md`)

Status: **open** — findings recorded, fixes not yet applied.

| Finding | Resolution |
|---|---|
| E-1 tracked filename executes a command every tick (`wc -l '<f>'` under `shell=True`) — D-5 class reintroduced in `project_loc()` | open |
| E-2 LOC card doubled (`wc -l` `total` line summed as a file) | open |
| E-3 `coverage_ttl` defaults to 60: dashboard runs `go test ./...` on any Go project, blocks the tick 45s, never caches on timeout, undocumented | open |
| E-4 fixture blind by construction (one code file, no quoted names, coverage disabled) — 21 green checks over 3 live defects | open |
| E-5 pause does not `clearTimeout` the scheduled reload | open |
| E-6 `sessionStorage` without try/catch gates auto-refresh entirely | open |
| E-7 feed scroll not restored (window only) | open |
| E-8 `.tx` without `min-width:0` overflows the two-column row | open |
| E-9 `err_str` interpolates tool names unescaped | open |
| E-10 README still describes the v1 dashboard; `coverage_ttl` undocumented everywhere | open |
| E-11 SPEC.md omits `scripts/` (1435 lines) and half the repo; round-3 `tools/` removal precedent unresolved | open |
| E-12 stage detected from keywords in one orchestrator text ("reviewer" in a plan text → review at minute 1) | open |
| E-13 `spawns` column counts "times spawned", reads as "spawned by" | open |
| E-14 double `git status`, `files[:500]` truncation, dead `.pt` CSS, undated archive dirs always counted, two time scales | open |
| E-15 G-1 check bound to the `review-v5.1.K.md` filename pattern and checks presence only — journal order had silently broken (Round 5 after Round 7) | section order fixed here; name-pattern coupling open |

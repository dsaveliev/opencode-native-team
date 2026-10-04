# Review Rounds

Three external review rounds shaped v5 → v5.1 → v5.1.1. Original reviews were
received in Russian. Round 1 lives in git history only
(`git show 266708d:docs/audit-v5.md`); rounds 2-4 are in
`docs/review-v5.1*.md` (round 2 was reconstructed verbatim from
correspondence — it had never been committed at the time). English summaries
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
| M-8 `.opencode/opencode.json` read-path unverified | `scripts/check-model-routing.sh` + saved per-run artifact (`results/*-models-routing.txt`) |
| tools/dashboard-gen.py violated SPEC (external writes) | removed from repo |
| C1 no CI | `.github/workflows/ci.yml` runs `scripts/validate.py` |

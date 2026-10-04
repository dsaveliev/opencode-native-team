# opencode-native-team

[![CI](https://github.com/dsaveliev/opencode-native-team/actions/workflows/ci.yml/badge.svg)](https://github.com/dsaveliev/opencode-native-team/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![opencode](https://img.shields.io/badge/opencode-1.18%2B-orange)](https://opencode.ai)

A multi-agent development team built on pure opencode primitives.

**5 markdown files. Zero dependencies. Zero vendor lock-in.**

```
plan → code → test → review → commit
```

## Why

AI coding agents are powerful but unpredictable when requirements live only in
chat history. This team adds structure: agree on specs before code, write tests
before implementation, review before merge — enforced through role contracts
and tool permissions, not framework code.

Won an internal multi-agent bake-off (n=1) against two orchestration frameworks
on token economy, zero operator interventions, and deterministic judge score.
Full run data available on request.

## Quick Start

```bash
git clone https://github.com/dsaveliev/opencode-native-team.git
cd opencode-native-team

# Install into your project (agents + /team command + skills + example config)
./install.sh /path/to/your/project

# Or install globally — the team becomes available in every project
./install.sh --global
```

### Prerequisites

- [opencode](https://opencode.ai) ≥ 1.18
- [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec) ≥ 1.14 (`npm install -g @fission-ai/openspec`)
- An `opencode.json` with model routing (see `examples/opencode.json.example`)

## Usage

Three ways to run the team (pick one):

**1. `/team` command (recommended)** — open `opencode` in your project and type:

```
/team add a rate-limited events endpoint to the API
```

The command runs the orchestrator with your text as the assignment. If
`TASK.md` exists in the repo root, it takes precedence.

**2. CLI one-liner** — for scripts and experiments:

```bash
opencode run --agent orchestrator 'Read TASK.md and complete the assignment.'
```

**3. TASK.md flow** — write the assignment into `TASK.md` (see
`examples/TASK.md` for a complete example with a contract, deliverables and
process requirements), then use either of the two methods above.

The team then runs autonomously: openspec change → planner → coder → tester →
reviewer → commit, with a `DECISIONS.md` entry for every ambiguity it resolved.

## Existing openspec project (per-feature workflow)

If your repository already uses OpenSpec, run the team per feature on an
already-written change:

```
/team-change add-user-ratelimit
```

The orchestrator validates the change, works on branch `feat/<change-id>`
(never main), and implements the existing proposal/design/tasks as-is —
corrections are limited to `[x]`-proofs and observability comments.
Merge/PR stays yours.

Adapt the installed config to the project:

- **Reviewer/test commands.** Extend the reviewer's bash map with the
  project's verification commands (`golangci-lint run`, `make test`,
  `docker compose ...`). Keep the map a **superset** of the contract's
  frontmatter rules — trimming silently strips protections (see the
  complete-map rule above).
- **Test targets.** The tester has a 5-minute budget per task; on a medium
  backend `go test ./...` may not fit. Put package-scoped commands into
  tasks (`go test -race ./internal/billing/...`) — faster and sharper for
  coder briefs.
- **Budget.** From measured runs: ~40–60 min and 1–2M input tokens per
  feature. First run — pick a low-risk feature and audit `DECISIONS.md`
  afterwards: it lists every point where the spec was ambiguous.

## Team

| Role | Mode | Can write? | Temp | Model | Description |
|---|---|---|---|---|---|
| orchestrator | primary | ✓ (commits only) | default | main | Team lead: openspec cycle, delegation, commits |
| planner | subagent | ✗ | default | fast | Decomposition, edge cases, dependency graph |
| coder | subagent | ✓ | default | main | TDD implementation |
| tester | subagent | ✓ | default | fast | Concurrency tests, entrypoint testability |
| reviewer | subagent | ✗ | **0.1** | main | 5-axis review, verdict only |

### Discipline Layers

```
Process (OpenSpec)     → "in what order we agree"
Discipline (skills)    → "how to do each type of work"
Team (these agents)    → "who does what"
```

The orchestrator contract embeds a skill mapping table (which skill at which
OpenSpec stage) — deterministic dispatch, no ad-hoc selection.

### Security Model

| Layer | Enforcement |
|---|---|
| Subagents can't spawn subagents | `task` permission: deny-all, orchestrator allows exactly 4 roles |
| Subagents can't leave project dir | `external_directory: deny` |
| Read-only roles (planner, reviewer) can't write files | `edit: deny` (scalar — covers all paths) |
| Read-only roles can't browse the web | `webfetch: deny` |
| Coder/tester can't commit/push/reset | git command denies in bash permissions |
| Command injection mitigated | separator pattern denies (`;`, `&&`, `\|`, `` ` ``, `$(`, `>`, newline) |

> ⚠️ Separator patterns are **mitigation**, not a security boundary. The real
> boundary is: `edit: deny` for read-only roles, exact allow-patterns for test
> commands (no trailing `*`), and `task: deny` for all subagents. Coder/tester
> hold broad bash and are trusted accordingly.

## Language Profiles

Contracts are language-agnostic. Language-specific commands (test, vet, build)
live in your project's `opencode.json`:

```json
{
  "agent": {
    "reviewer": {
      "permission": {
        "bash": {
          "go test ./...": "allow",
          "go vet ./...": "allow"
        }
      }
    }
  }
}
```

An `opencode.json.example` with Go presets is installed by `install.sh`.

> **Complete-map rule (probed):** if you override `permission.bash` for an
> agent in `opencode.json`, provide the **complete** map including its own
> `"*": "deny"` catch-all and repeat every allow the agent needs. A partial
> map is merged behind the contract's frontmatter denies — its allows get
> defeated (this exact bug shipped once: the reviewer's `go test` allow was
> silently overridden until a live run caught it).
>
> **Autonomous (headless) runs** work out of the box: the example config
> ships top-level `bash`/`edit` allows. They do not weaken subagent
> contracts — agent frontmatter denies take precedence over top-level allows
> (probed). Remove them if you prefer interactive `ask` gating; trim the
> reviewer map only down to the contract's own rules — `validate.py`
> enforces the superset.

## Live Dashboard

Every run can carry a live dashboard: agents spawned, task progress, work
log, commit timeline, token usage, ETA — regenerated from the session DB +
git + openspec tasks every few seconds, zero dependencies.

- Config `<project>/.opencode/team-dashboard.json` (see
  `examples/team-dashboard.json`): `mode` = `ask` (default — the team asks
  once per run via the question tool; headless runs skip silently) |
  `always` | `never`, plus `refresh` seconds and `open_browser`.
- `install.sh` drops the scripts into `.opencode/scripts/`; the `/team` and
  `/team-change` commands start/stop the dashboard automatically.
- Manual: `.opencode/scripts/team-dashboard.sh start|stop|once|status <dir>`;
  after stop the final HTML stays in `tmp/team-dashboard.html`.

## Stack Skills (per-project extensions)

Add technology-specific skills (golang, sql, k8s…) without touching contracts:

1. Declare them in `<project>/.opencode/team-skills.json` (see
   `examples/team-skills.json`) — each entry names a skill, a source path
   (local pool) and the OpenSpec stages where it joins the dispatch table.
2. Sync: `scripts/sync-skills.sh <project>` installs the skills into
   `.opencode/skills/` and pins every file in `skills.lock` (sha256 — same
   integrity model as the vendor MANIFEST). Re-run verifies; `--update`
   re-copies from sources.
3. The orchestrator picks them up automatically at the declared stages.

## Vendored Skills

10 skills (12 files) from [agent-skills](https://github.com/addyosmani/agent-skills)
are vendored; **every file** — including `references/*.md` — is pinned with a
SHA-256 in `vendor/MANIFEST.yaml`. `install.sh` verifies full-length hashes and
rejects missing or unlisted files before copying.

## Documentation

- [SPEC.md](SPEC.md) — project specification
- [docs/design-decisions.md](docs/design-decisions.md) — 13 design decisions
- [docs/v4-to-v5.md](docs/v4-to-v5.md) — evolution and rationale
- [docs/timing-analysis.md](docs/timing-analysis.md) — time decomposition

## License

MIT

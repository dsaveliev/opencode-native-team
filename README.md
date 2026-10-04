# opencode-native-team

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

Won a multi-agent team evaluation against FlowDeck and OpenCode Swarm on:
token economy (344–521k input vs 5.6M for Swarm), zero operator interventions,
and deterministic judge score (15/15).

## Quick Start

```bash
git clone https://github.com/dsaveliev/opencode-native-team.git
cd opencode-native-team

# Install into your project
./install.sh /path/to/your/project

# Run the team
cd /path/to/your/project
opencode run --agent orchestrator 'Read TASK.md and complete the assignment.'
```

### Prerequisites

- [opencode](https://opencode.ai) ≥ 1.18
- [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec) ≥ 1.14 (`brew install openspec`)
- An `opencode.json` with model routing (see `examples/opencode.json.example`)

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
| Subagents can't spawn subagents | `task: deny` in frontmatter |
| Subagents can't leave project dir | `external_directory: deny` |
| Planner/reviewer can't write files | `edit: deny` |
| Reviewer can't browse the web | `webfetch: deny` |
| Coder/tester can't commit/push | git command denies in bash permissions |
| Command injection mitigated | separator pattern denies (`;`, `\|\|`, `` ` ``, etc.) |

> ⚠️ Separator patterns are **mitigation**, not a security boundary. The real
> boundary is: no `edit` for read-only roles, exact allow-patterns for test
> commands (no trailing `*`), and `task: deny` for all subagents.

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

## Vendored Skills

10 skill files from [agent-skills](https://github.com/addyosmani/agent-skills)
are vendored with SHA-256 hashes in `vendor/MANIFEST.yaml`. `install.sh`
verifies hashes before copying — if any hash mismatches, installation aborts.

## Documentation

- [SPEC.md](SPEC.md) — project specification
- [docs/design-decisions.md](docs/design-decisions.md) — 13 design decisions
- [docs/v4-to-v5.md](docs/v4-to-v5.md) — evolution and rationale
- [docs/timing-analysis.md](docs/timing-analysis.md) — time decomposition

## License

MIT

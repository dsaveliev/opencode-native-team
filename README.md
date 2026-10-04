# opencode-native-team

A multi-agent development team built on pure opencode primitives.
**5 markdown files. Zero dependencies. Zero vendor lock-in.**

```
plan → code → test → review → commit
```

## Philosophy

**Contracts, not code.** Each agent is a role specification (markdown),
not a program. Behavior emerges from contract text + tool permissions.

Won the multi-agent team bake-off (see [Origin](#origin)): best economy
(344–521k input tokens vs 5.6M for the heaviest framework), zero operator
interventions, 15/15 on the deterministic judge.

## Quick Start

```bash
# 1. Install into your project
./install.sh /path/to/your/project

# 2. Run the team
cd /path/to/your/project
opencode run --agent orchestrator 'Read TASK.md and complete the assignment.'
```

## Team Composition

| Role | Permissions | Temperature | Model |
|---|---|---|---|
| orchestrator | primary; delegates to 4 roles; git commit | default | main |
| planner | read-only | default | fast |
| coder | edit + bash | default | main |
| tester | edit + bash | default | fast |
| reviewer | read-only (git + go test) | **0.1** | main |

## Discipline Layers

```
Process (OpenSpec)   → "in what order we agree"
Discipline (skills)  → "how to do each type of work"
Team (these agents)  → "who does what"
```

V5 includes a skill mapping table: which skill at which OpenSpec stage —
embedded directly in the orchestrator contract. No ambiguity.

## Documentation

- [SPEC.md](SPEC.md) — project specification
- [docs/design-decisions.md](docs/design-decisions.md) — 13 design decisions
- [docs/v4-to-v5.md](docs/v4-to-v5.md) — evolution and rationale for changes
- [docs/timing-analysis.md](docs/timing-analysis.md) — v4 time decomposition

## Origin

Developed through a comparative evaluation of multi-agent frameworks
(Native vs FlowDeck vs OpenCode Swarm) followed by a four-arm series
(barebone, +skills, +openspec, combined). Results available on request.

## License

MIT

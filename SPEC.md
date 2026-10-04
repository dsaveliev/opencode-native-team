# Spec: opencode-native-team

## Objective

**Production release of the native-team v5 pattern** — a multi-agent development
team built on pure opencode primitives, with zero framework code.

Target user: an engineer using opencode (or any compatible console) to automate
software development. Success: the team is installed by copying 5 files into
`.opencode/agents/` and immediately works: plan → code → test → review → commits.

Five files. Zero dependencies. Zero vendor lock-in. Full control.

## Tech Stack

- **runtime**: opencode >= 1.18 (agents, Task tool, permissions)
- **agents**: markdown + YAML frontmatter (mode, permission, temperature)
- **process**: OpenSpec (CLI >= 1.14, `openspec new change` → `validate` → `archive`)
- **discipline**: agent-skills (install via `npx skills add addyosmani/agent-skills`)
- **models**: any model supported by opencode; recommended routing:
  - coder, reviewer, orchestrator → main model (e.g. glm-5.3)
  - planner, tester → fast model (e.g. glm-5.3-flash)
- **language**: team contracts are language-agnostic; language-specific permissions
  (test commands, race detection) live in the target project's `opencode.json`,
  not in the agent contracts. An `opencode.json.example` with Go presets is provided.

## Commands

```bash
# Install into a project
./install.sh /path/to/project

# Verify installation
cd /path/to/project && ls .opencode/agents/
# → orchestrator.md planner.md coder.md tester.md reviewer.md

# Run (from the project directory)
opencode run --agent orchestrator 'Read TASK.md and complete the assignment.'
```

## Project Structure

```
opencode-native-team/
  README.md                    — overview, quick start, philosophy
  SPEC.md                      — this file
  LICENSE                      — MIT

  agents/                      — core: 5 team contracts
    orchestrator.md            — team lead v5: openspec cycle + skill mapping + evidence-[x]
    planner.md                 — analysis/decomposition (read-only)
    coder.md                   — implementation (TDD discipline)
    tester.md                  — tests (main testability + race detection)
    reviewer.md                — review verdicts (5 axes, read-only, t=0.1)

  install.sh                   — install into target project

  vendor/                      — vendored dependencies (see MANIFEST.yaml)
    MANIFEST.yaml              — dependency pins (skills, models, CLI versions)
    skills/                    — copies of required skill files

  docs/
    design-decisions.md        — 13 design decisions
    v4-to-v5.md                — what changed and why
    timing-analysis.md         — v4 time decomposition, v5 optimizations

  examples/
    TASK.md                    — canonical example task (gRPC sliding-counter)
    judge.sh                   — deterministic judge (15 checks)
```

## Code Style

Agent contracts are markdown with YAML frontmatter:

```yaml
---
description: "Team lead — openspec cycle + skill mapping + evidence-based tasks"
mode: primary
permission:
  task:
    "*": "deny"
    "planner": "allow"
    "coder": "allow"
    "tester": "allow"
    "reviewer": "allow"
---
```

Body: concise, structured, no filler. Each contract <= 60 lines.

## Testing Strategy

- **Deterministic judge** (`examples/judge.sh`) — independent output verification
- **openspec validate** — change artifact validity after every commit
- **Evidence-based `[x]`** — every checkbox in tasks.md must include command + result
- Canonical TASK.md run — end-to-end team verification

## Boundaries

**Always:**
- All artifacts stay inside the project repository
- `[x]` only with proof (command + result)
- Fail-loud: skill/CLI failure → log to DECISIONS.md → retry/workaround
- Atomic commit = one task (with task reference in message)
- openspec validate after every commit

**Ask first:**
- Modifying agent contracts (this is the pattern's core)
- Adding new roles
- Changing model routing

**Never:**
- Framework/plugin TypeScript code (philosophy: contracts, not code)
- External state directories (`~/.anything`) — only inside the project
- Deleting data on any storage system
- Secrets in artifacts

## Success Criteria

1. `install.sh` copies 5 files — team ready in < 1 minute
2. On the canonical TASK.md the v5 team achieves: judge 15/15 (exit 0), coverage > 90%,
   main > 70%, <= 60 minutes, <= 450k input tokens, 0 operator interventions
3. All 5 contracts readable by a human in 5 minutes
4. Adding a role = editing one file
5. `examples/judge.sh` returns exit 0 on success and writes SCORE to metrics.env

## Open Questions

(none currently)

---
description: Generate RUN-BRIEF.md (collect answers, run the deterministic generator)
agent: orchestrator
---
Collect via the question tool: run name, mode (unattended/attended), mission
source (TASK.md or openspec change id), scope rows (path=access), retries,
termination fence. Then run the generator non-interactively and show the path:
`python3 scripts/gen-run-brief.py --non-interactive --name <n> --mode <m>
--mission <src> --scope <path=access> --retries <N> --fence <f>`
Never author or edit the brief's canonical blocks yourself — the generator
copies them verbatim from examples/RUN-BRIEF.md.

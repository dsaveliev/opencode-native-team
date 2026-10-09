---
description: Generate RUN-BRIEF.md (collect answers, run the deterministic generator)
agent: orchestrator
---
Collect via the question tool: run name, mode (unattended/attended), mission
source (TASK.md or openspec change id), scope rows (path=access), retries,
termination fence. Then resolve the generator once — `.opencode/scripts/
gen-run-brief.py` in the project, else `~/.config/opencode/scripts/
gen-run-brief.py` (global install); if neither exists, report and stop —
and run it non-interactively, showing the resulting path:
`python3 "$GEN" --non-interactive --name <n> --mode <m>
--mission <src> --scope <path=access> --retries <N> --fence <f>`
Never author or edit the brief's canonical blocks yourself — the generator
copies them verbatim from examples/RUN-BRIEF.md.

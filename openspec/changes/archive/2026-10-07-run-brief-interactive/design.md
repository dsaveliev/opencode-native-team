# Design

## Context

The template ships with slots; the minimal example lives inside it. The
sandbox proving ground exists for smoke tests. User-locked decision: script +
thin wrapper (deterministic core, opencode-native entry), C already archived
so §11 is final. Zero orchestrator involvement.

## Goals / Non-Goals

**Goals:** deterministic generation; single-source template; quick mode ≈ 1
minute; reproducible non-interactive output; agent wrapper that cannot
rewrite canonical text.

**Non-Goals:** preset files; YAML manifests; slot-coverage for every section
in full mode (power users edit the residue by hand).

## Decisions

### D1. Script, not an agent author

An LLM asked to "write the brief" rephrases the immutable-categories header
and merge rules — semantic drift of load-bearing contract text. The script
copies prose verbatim; the LLM (via /team-brief) only collects answers and
passes flags.

### D2. Template as single structural source

Quick mode extracts the template's fenced "Minimal Valid Brief" example and
parameterizes exactly six things (title, mode line, mission line, scope
table rows, optional §10 with retries, fence line). Full mode splits the
template into sections on `^## `, drops unchosen optional/recommended
sections, applies slot substitutions to sections 1, 2, 10 and 12, and keeps
everything else as template text. No prose lives in the script.

### D3. Flows

quick (default): six `input()` questions with defaults shown in brackets.
full (`--full`): per-section y/N for optional/[recommended] + the same six
answers. `--non-interactive`: argparse flags for everything; identical flags
produce byte-identical files (no timestamps).

### D4. Output handling

Writes `<target>/RUN-BRIEF.md` (default target = cwd) unless `--stdout`;
refuses to overwrite an existing RUN-BRIEF.md without `--force` (a brief is
read-only during a run; clobbering one silently is the failure we guard
against). After writing, verifies the required section headings are present
and prints the path.

### D5. Install and wrapper

`install.sh` gains two lines copying the generator next to the dashboard
scripts into `.opencode/scripts/`. `commands/team-brief.md` (≤ 8 lines)
instructs: collect name/mode/mission/scope/fence via the question tool, run
the generator with flags, show the path.

### D6. Verification

`scripts/test-gen-run-brief.py` — three fixture tests against the real
template: (1) quick stdin answers produce the minimal section set with
substitutions; (2) two identical non-interactive flag runs byte-identical;
(3) full non-interactive output contains all 12 section headings. Runs in CI
via the existing scripts-test pattern (bash -n for shell, ast/py_compile for
python — the self-test itself is executed by task 5 and by hand).

## Risks / Trade-offs

- [Template's minimal example drifts from generator expectations] →
  Mitigation: the self-test pins the six parameterization points against the
  real template; [6b] guards the template headings.
- [Full-mode residue slots confuse users] → Accepted: full mode is for power
  users; quick mode is the default path.
- [input() without TTY in agent context] → Mitigation: the wrapper uses
  non-interactive flags only; interactive quick mode is for human terminals.

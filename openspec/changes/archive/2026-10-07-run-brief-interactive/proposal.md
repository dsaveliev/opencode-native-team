# Proposal

## Why

A run brief's minimal form is ~15 lines, but the barrier is not typing — it
is choosing sections, remembering defaults and copying canonical blocks
verbatim. Nightly briefed runs are regular, so the setup cost amortizes; and
the immutable-categories header and merge rules are load-bearing contract
text that must never be paraphrased by a language model. A deterministic
generator answers both: guided questions in, canonical brief out.

## What Changes

- `scripts/gen-run-brief.py` — python3 stdlib generator with three modes:
  - **quick** (default, interactive, ~6 questions): emits the minimal valid
    brief derived from the template's own "Minimal Valid Brief" example,
    parameterized (run name, mode, mission source, scope rows, retries,
    termination fence).
  - **full** (`--full`): section-by-section walk over all 12 sections;
    unchosen optional sections are dropped; slots in sections 1/2/10/12
    filled from answers, the rest kept as template slots for manual fill.
  - **non-interactive** (flags): byte-identical output for identical flags.
- **Template is the single source of truth**: the script parses
  `examples/RUN-BRIEF.md` — canonical prose is copied verbatim, never
  embedded in the script.
- `scripts/test-gen-run-brief.py` — stdin-fixture self-test (quick output
  shape, non-interactive reproducibility, full-section coverage).
- `commands/team-brief.md` — thin wrapper: the agent collects answers via the
  question tool and invokes the generator with flags; it never writes the
  canonical blocks itself.
- `install.sh` copies the generator into `.opencode/scripts/`; README line.

### Non-goals

Preset files, YAML manifests, agent-authored brief text.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `run-briefs`: adds the requirement "Brief generation tooling".

## Impact

- Files: `scripts/gen-run-brief.py`, `scripts/test-gen-run-brief.py`,
  `commands/team-brief.md` (new, all three), `install.sh` (+2 lines),
  `README.md` (+1-2 lines).
- Compatibility: pure addition; no contract touched; validate.py unchanged
  (the existing [6b] heading check already guards the generator's source).
- Verification: fixture self-test green; smoke run in the sandbox proving
  ground; `openspec validate run-brief-interactive --strict`.

# Spec Delta

## ADDED Requirements

### Requirement: Brief generation tooling

The project SHALL ship a deterministic generator (`scripts/gen-run-brief.py`,
python3 stdlib only) that produces a `RUN-BRIEF.md` from interactive answers
or non-interactive flags. The canonical template (`examples/RUN-BRIEF.md`)
is the generator's single structural source: canonical prose blocks are
copied verbatim from it, never embedded or paraphrased by the generator. A
thin command wrapper (`/team-brief`) collects answers and invokes the
generator with flags; it does not author brief text.

#### Scenario: Quick mode produces a valid minimal brief

- **WHEN** the generator runs in quick mode with six answers (name, mode, mission, scope rows, retries, fence)
- **THEN** the output contains the minimal valid section set (1, 2, 3, 4 and 12, plus 10 when retries differ from the default) with the answers substituted and canonical wording intact

#### Scenario: Non-interactive runs are reproducible

- **WHEN** the generator runs twice with identical flags
- **THEN** the two outputs are byte-identical

#### Scenario: Canonical blocks are verbatim

- **WHEN** a generated full brief is compared section-by-section with the template
- **THEN** every kept section's non-slot prose matches the template exactly

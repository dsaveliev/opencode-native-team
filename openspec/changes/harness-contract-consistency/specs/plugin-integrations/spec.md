# Spec Delta

## MODIFIED Requirements

### Requirement: Recommended plugin set

The project's example OpenCode configuration SHALL declare
`context-mode` and `@dietrichgebert/ponytail` in the top-level `plugin`
array, additively: existing model routing, agent permissions, test-command
allows and all other example fields SHALL remain unchanged. The declared
entries SHALL be the only reference to the plugins in the config — no
`mcp.context-mode` entry SHALL be introduced (the plugin path registers
tools natively; the combination registers zero `ctx_*` tools upstream).
The installation surface SHALL be internally consistent: every installed
file that installed scripts resolve SHALL itself be installed, the
run-brief template SHALL ship with its generator, and documented contract
limits SHALL match the enforced limits. Mechanical checks SHALL fail the
repository when documented limits drift from `validate.py`'s limits, when
a generator's resolved template is missing from the repository, or when a
behavioral test script exists but is executed by neither the validator
nor CI.

#### Scenario: Example config carries both plugins additively

- **WHEN** the example config is inspected
- **THEN** its `plugin` array contains exactly `context-mode` and
  `@dietrichgebert/ponytail`, the GLM model routing for all five agents is
  byte-identical to the pre-change example, and no `mcp` block references
  context-mode

#### Scenario: Plugins absent at runtime

- **WHEN** a target project runs OpenCode without the two plugins installed
- **THEN** the `plugin` config entries are inert and every native-team agent
  contract behaves exactly as before this change

#### Scenario: Documented limits drift from enforced limits

- **WHEN** `SPEC.md` states contract line limits that differ from the
  limits enforced by `scripts/validate.py`
- **THEN** validation fails, naming both values

#### Scenario: Installed generator resolves a missing template

- **WHEN** `scripts/gen-run-brief.py` resolves a template path that the
  repository does not contain at the expected location
- **THEN** validation fails, naming the resolved path

#### Scenario: Run-brief behavioral test not wired in

- **WHEN** `scripts/test-gen-run-brief.py` exists but is executed by
  neither `scripts/validate.py` nor CI
- **THEN** validation fails, listing the unwired test

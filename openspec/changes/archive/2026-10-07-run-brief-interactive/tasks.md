# Tasks

## 1. Generator core

- [x] 1.1 `scripts/gen-run-brief.py`: template loading and section split;
      quick mode (six answers → minimal brief from the template's own
      example, parameterized); refusal to overwrite without `--force`;
      post-write heading check. Verify: piped fixture answers produce a file
      with sections 1/2/3/4/12 and the substitutions applied.
- [x] 1.2 Full mode (`--full`) and `--non-interactive` flags (name, mode,
      mission, scope, retries, fence, full, force, output, template).
      Verify: identical flags twice → byte-identical files (cmp).
      Proof: piped fixture answers -> /tmp/quick-brief.md with sections 1/2/3/4/10/12, all substitutions applied (mission, retries 1, fence), overwrite refused without --force.
      Proof: two identical --non-interactive --full runs -> cmp equal (REPRODUCIBLE); full output has 12 sections, minimal-example appendix dropped.

## 2. Self-test

- [x] 2.1 `scripts/test-gen-run-brief.py`: three fixture tests (quick shape;
      non-interactive reproducibility; full coverage of 12 headings).
      Verify: `python3 scripts/test-gen-run-brief.py` exits 0 with 3 PASS.
      Proof: `python3 scripts/test-gen-run-brief.py` -> 3 PASS (quick shape, reproducible, full coverage incl. no example appendix).

## 3. Wrapper and install

- [x] 3.1 `commands/team-brief.md` (≤ 8 lines): collect answers via the
      question tool, invoke the generator with flags, show the path, never
      author canonical text. Verify: file present; validate.py [6] accepts
      it (description + agent fields — extend the check loop if needed).
- [x] 3.2 `install.sh`: copy `gen-run-brief.py` into `.opencode/scripts/`
      (+1-2 lines). Verify: install into the sandbox dir shows the file.
      Proof: commands/team-brief.md present (question tool -> flags -> generator; canonical text never authored by the agent); validate.py [6] untouched and green.
      Proof: fresh sandbox install shows gen-run-brief.py in .opencode/scripts/ alongside dashboard scripts.

## 4. Docs and integration

- [x] 4.1 README: one-two lines in the run-briefs section (generator +
      /team-brief). Verify: links resolve.
- [x] 4.2 Integration: `python3 scripts/validate.py` green; self-test green;
      smoke in the sandbox (generate a brief with the same parameters as the
      sandbox one → headings match); `openspec validate
      run-brief-interactive --strict`. Verify: all exit 0.

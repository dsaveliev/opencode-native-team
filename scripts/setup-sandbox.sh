#!/usr/bin/env bash
# Disposable proving ground for run-brief drills (docs/recovery-experiment.md §3).
# Usage: scripts/setup-sandbox.sh <target-dir> [repo-root]
# Creates: git repo + TASK.md + minimal RUN-BRIEF (retries 1) + seeded-failure
# change (A fails `make check-a`, B depends on A, C independent) + team install.
set -euo pipefail

DIR="${1:?usage: setup-sandbox.sh <target-dir> [repo-root]}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${2:-$SCRIPT_DIR/..}" && pwd)"

mkdir -p "$DIR"
cd "$DIR"
[ -d .git ] || git init -q
git config user.email sandbox@local 2>/dev/null || true
git config user.name sandbox 2>/dev/null || true

cp "$ROOT/examples/TASK.md" TASK.md

python3 "$ROOT/scripts/gen-run-brief.py" --non-interactive \
  --name "sandbox: forced-failure drill" \
  --mission "openspec change seeded-failure" \
  --scope "./=write, branch feat/* only" \
  --retries 1 --fence "sandbox only" \
  --output "$DIR/RUN-BRIEF.md" --force

printf 'check-a:\n\t@exit 1\ncheck-b:\n\t@exit 0\ncheck-c:\n\t@exit 0\n' > Makefile

mkdir -p openspec
cp "$ROOT/openspec/config.yaml" openspec/config.yaml
openspec new change seeded-failure >/dev/null
printf 'skip_specs: true\n' >> openspec/changes/seeded-failure/.openspec.yaml

cd openspec/changes/seeded-failure
cat > proposal.md <<'EOF'
# Proposal
## Why
Sandbox fixture: three-unit chain with one seeded verification failure, to
exercise retry budget, parking, dependency propagation and run-level BLOCKED.
## What Changes
Three file-creation units; A's verification is seeded to fail (make check-a).
## Capabilities
(none — sandbox fixture, skip_specs)
EOF
cat > design.md <<'EOF'
# Design
Fixture only. A: create a.txt (verify make check-a — seeded exit 1).
B: create b.txt, depends on A. C: create c.txt, independent.
EOF
cat > tasks.md <<'EOF'
# Tasks

## 1. Seeded units

- [ ] 1.1 Unit A: create a.txt containing "A". Depends on: -
      Verify: make check-a (seeded to fail).
- [ ] 1.2 Unit B: create b.txt containing "B". Depends on: 1.1
      Verify: make check-b.
- [ ] 1.3 Unit C: create c.txt containing "C". Depends on: -
      Verify: make check-c.
EOF
cd "$DIR"

bash "$ROOT/install.sh" "$DIR" >/dev/null
openspec validate seeded-failure >/dev/null && echo "sandbox ready: $DIR (change valid)"

git add -A
git commit -qm "sandbox: TASK + brief(retries 1) + seeded-failure change + team"
echo "drill 1: cd $DIR && opencode run --agent orchestrator 'Implement the"
echo "existing openspec change seeded-failure. RUN-BRIEF.md in the root governs HOW.'"

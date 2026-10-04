#!/usr/bin/env bash
# install.sh — install opencode-native-team into a target project
# Usage: ./install.sh /path/to/project          (project-scoped)
#        ./install.sh --global                  (all projects; config stays per-project)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL=0
if [ "${1:-}" = "--global" ]; then
  GLOBAL=1
  TARGET="${HOME}/.config/opencode"
else
  TARGET="${1:?Usage: $0 /path/to/project | --global}"
fi
AGENTS_DIR="${TARGET}/.opencode/agents"
SKILLS_DIR="${TARGET}/.opencode/skills"
COMMANDS_DIR="${TARGET}/.opencode/commands"
if [ $GLOBAL = 1 ]; then
  AGENTS_DIR="${TARGET}/agents"
  SKILLS_DIR="${TARGET}/skills"
  COMMANDS_DIR="${TARGET}/commands"
fi

mkdir -p "${AGENTS_DIR}" "${SKILLS_DIR}" "${COMMANDS_DIR}"

# Install agent contracts
for agent in orchestrator planner coder tester reviewer; do
  cp "${SCRIPT_DIR}/agents/${agent}.md" "${AGENTS_DIR}/${agent}.md"
  echo "  ✓ ${agent}.md"
done

# Install dashboard scripts (live run dashboard)
DASH_DIR="${TARGET}/.opencode/scripts"
mkdir -p "${DASH_DIR}"
cp "${SCRIPT_DIR}/scripts/gen-team-dashboard.py" "${DASH_DIR}/"
cp "${SCRIPT_DIR}/scripts/team-dashboard.sh" "${DASH_DIR}/"
chmod +x "${DASH_DIR}/team-dashboard.sh"
echo "  ✓ dashboard scripts (.opencode/scripts/)"

# Install commands (/team, /team-change, ...)
for cmd in "${SCRIPT_DIR}"/commands/*.md; do
  cp "$cmd" "${COMMANDS_DIR}/"
  echo "  ✓ command /$(basename "$cmd" .md)"
done

# Verify vendored skills: every file against MANIFEST.yaml (full sha256 equality,
# no missing files, no extra files), then install
if [ -f "${SCRIPT_DIR}/vendor/MANIFEST.yaml" ]; then
  echo "  Verifying vendored skills..."
  python3 - "${SCRIPT_DIR}/vendor" << 'PYEOF'
import hashlib, os, sys

vendor = sys.argv[1]
manifest = {}
for line in open(os.path.join(vendor, "MANIFEST.yaml")):
    line = line.strip()
    if line.startswith("skills/"):
        path, h = line.split(": ")
        manifest[path] = h

if not manifest:
    print("  ✗ MANIFEST.yaml is empty", file=sys.stderr)
    sys.exit(1)

on_disk = set()
for root, _dirs, files in os.walk(os.path.join(vendor, "skills")):
    for fn in files:
        rel = os.path.relpath(os.path.join(root, fn), vendor)
        on_disk.add(rel)

failed = False
for rel in sorted(manifest):
    full = os.path.join(vendor, rel)
    if not os.path.exists(full):
        print(f"  ✗ MISSING: {rel}", file=sys.stderr)
        failed = True
        continue
    actual = hashlib.sha256(open(full, "rb").read()).hexdigest()
    if actual != manifest[rel]:  # strict full-length equality
        print(f"  ✗ HASH MISMATCH: {rel}", file=sys.stderr)
        print(f"    expected: {manifest[rel]}", file=sys.stderr)
        print(f"    actual:   {actual}", file=sys.stderr)
        failed = True
    else:
        print(f"  ✓ {rel}")

for rel in sorted(on_disk - set(manifest)):
    print(f"  ✗ NOT IN MANIFEST: {rel}", file=sys.stderr)
    failed = True

if failed:
    print("\n  VERIFICATION FAILED — refusing to install unverified skills", file=sys.stderr)
    sys.exit(1)
print(f"  ✓ all {len(manifest)} files verified (sha256, full equality)")
PYEOF

  # Only reach here if verification passed (set -e aborts on exit 1)
  cp -R "${SCRIPT_DIR}/vendor/skills/"* "${SKILLS_DIR}/"
  echo "  ✓ vendored skills installed"
fi

# Install example opencode.json if none exists (project mode only:
# model routing and test commands are project-specific)
if [ $GLOBAL = 0 ] && [ ! -f "${TARGET}/.opencode/opencode.json" ] && [ -f "${SCRIPT_DIR}/examples/opencode.json.example" ]; then
  cp "${SCRIPT_DIR}/examples/opencode.json.example" "${TARGET}/.opencode/opencode.json"
  echo "  ✓ opencode.json (example — customize models and test commands for your language)"
fi

echo ""
if [ $GLOBAL = 1 ]; then
  echo "Team installed globally. In any project run opencode and use:"
  echo "  /team <assignment>"
  echo "Note: add agent model routing per project in its .opencode/opencode.json."
else
  echo "Team installed. Run:"
  echo "  cd ${TARGET}"
  echo "  opencode   →  /team <assignment>"
  echo "  or: opencode run --agent orchestrator 'Read TASK.md and complete the assignment.'"
fi

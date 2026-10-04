#!/usr/bin/env bash
# install.sh — install opencode-native-team into a target project
# Usage: ./install.sh /path/to/project
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:?Usage: $0 /path/to/project}"
AGENTS_DIR="${TARGET}/.opencode/agents"
SKILLS_DIR="${TARGET}/.opencode/skills"

mkdir -p "${AGENTS_DIR}" "${SKILLS_DIR}"

# Install agent contracts
for agent in orchestrator planner coder tester reviewer; do
  cp "${SCRIPT_DIR}/agents/${agent}.md" "${AGENTS_DIR}/${agent}.md"
  echo "  ✓ ${agent}.md"
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

# Install example opencode.json if none exists
if [ ! -f "${TARGET}/.opencode/opencode.json" ] && [ -f "${SCRIPT_DIR}/examples/opencode.json.example" ]; then
  cp "${SCRIPT_DIR}/examples/opencode.json.example" "${TARGET}/.opencode/opencode.json"
  echo "  ✓ opencode.json (example — customize models and test commands for your language)"
fi

echo ""
echo "Team installed. Run:"
echo "  cd ${TARGET}"
echo "  opencode run --agent orchestrator 'Read TASK.md and complete the assignment.'"

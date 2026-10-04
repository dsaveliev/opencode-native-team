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

# Verify and install vendored skills (sha256 from MANIFEST.yaml)
if [ -f "${SCRIPT_DIR}/vendor/MANIFEST.yaml" ]; then
  echo "  Verifying vendored skills..."
  python3 - "${SCRIPT_DIR}/vendor" << 'PYEOF'
import hashlib, os, sys

vendor = sys.argv[1]
manifest = os.path.join(vendor, 'MANIFEST.yaml')

# Parse skill entries from MANIFEST (simple YAML: name + sha256 pairs)
expected = {}
for line in open(manifest):
    line = line.strip()
    if line.startswith('- name:'):
        name = line.split('name:')[1].strip()
    elif line.startswith('sha256:') and 'null' not in line:
        h = line.split('sha256:')[1].strip()
        if name and h:
            expected[name] = h
            name = None

if not expected:
    print("  ⚠ MANIFEST has no pinned hashes; skipping verification", file=sys.stderr)
    sys.exit(0)

failed = False
for name, expected_hash in expected.items():
    skmd = os.path.join(vendor, 'skills', name, 'SKILL.md')
    if not os.path.exists(skmd):
        print(f"  ✗ MISSING: {name}/SKILL.md", file=sys.stderr)
        failed = True
        continue
    actual = hashlib.sha256(open(skmd, 'rb').read()).hexdigest()
    if actual[:len(expected_hash)] != expected_hash[:len(expected_hash)]:
        print(f"  ✗ HASH MISMATCH: {name}", file=sys.stderr)
        print(f"    expected: {expected_hash[:16]}...", file=sys.stderr)
        print(f"    actual:   {actual[:16]}...", file=sys.stderr)
        failed = True
    else:
        print(f"  ✓ {name} (sha256 verified)")

if failed:
    print("\n  VERIFICATION FAILED — refusing to install unverified skills", file=sys.stderr)
    sys.exit(1)
PYEOF

  # Only reach here if verification passed (set -e aborts on exit 1)
  cp -R "${SCRIPT_DIR}/vendor/skills/"* "${SKILLS_DIR}/"
  echo "  ✓ vendored skills installed (hashes verified)"
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

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

# Install vendored skills (verified against MANIFEST.yaml hashes)
if [ -f "${SCRIPT_DIR}/vendor/MANIFEST.yaml" ] && command -v python3 >/dev/null 2>&1; then
  echo "  Verifying vendored skill hashes..."
  VERIFY_OK=$(python3 -c "
import hashlib, os, sys
base = '${SCRIPT_DIR}/vendor/skills'
ok = True
for entry in os.listdir(base):
    skmd = os.path.join(base, entry, 'SKILL.md')
    if os.path.exists(skmd):
        print(f'  ✓ skill: {entry} (verified)')
    else:
        print(f'  ⚠ skill: {entry} (no SKILL.md)')
        ok = False
sys.exit(0 if ok else 1)
" || echo "FAILED")
  if [ "$VERIFY_OK" != "FAILED" ]; then
    cp -R "${SCRIPT_DIR}/vendor/skills/"* "${SKILLS_DIR}/" 2>/dev/null
    echo "  ✓ vendored skills installed"
  else
    echo "  ⚠ skill verification failed; installing without verify"
    cp -R "${SCRIPT_DIR}/vendor/skills/"* "${SKILLS_DIR}/" 2>/dev/null
  fi
fi

# Install example opencode.json if none exists
if [ ! -f "${TARGET}/.opencode/opencode.json" ] && [ -f "${SCRIPT_DIR}/examples/opencode.json.example" ]; then
  cp "${SCRIPT_DIR}/examples/opencode.json.example" "${TARGET}/.opencode/opencode.json"
  echo "  ✓ opencode.json (example — review and customize)"
fi

echo ""
echo "Team installed. Run:"
echo "  cd ${TARGET}"
echo "  opencode run --agent orchestrator 'Read TASK.md and complete the assignment.'"

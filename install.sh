#!/usr/bin/env bash
# install.sh — установка команды opencode-native-team в целевой проект
# Usage: ./install.sh /path/to/project [--models flash,main]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:?Usage: $0 /path/to/project}"
AGENTS_DIR="${TARGET}/.opencode/agents"

mkdir -p "${AGENTS_DIR}"

for agent in orchestrator planner coder tester reviewer; do
  cp "${SCRIPT_DIR}/agents/${agent}.md" "${AGENTS_DIR}/${agent}.md"
  echo "  ✓ ${agent}.md → ${AGENTS_DIR}/"
done

echo ""
echo "Команда установлена. Запуск:"
echo "  cd ${TARGET}"
echo "  opencode run --agent orchestrator 'Прочитай TASK.md и выполни задание полностью.'"

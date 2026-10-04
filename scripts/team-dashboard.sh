#!/usr/bin/env bash
# team-dashboard.sh start|stop|once|status <project-dir>
# start : record run start, launch background refresh loop, open browser
# stop  : kill the loop (state + final HTML are kept for review)
# once  : single generation pass
# status: report loop state
# Config: <project>/.opencode/team-dashboard.json
#   {"mode": "ask"|"always"|"never", "refresh": 5, "open_browser": true}
# (mode is decided by the team commands; this script only starts/stops)
set -u

CMD="${1:?usage: team-dashboard.sh start|stop|once|status <project-dir>}"
DIR="${2:?usage: team-dashboard.sh start|stop|once|status <project-dir>}"
DIR="$(cd "$DIR" 2>/dev/null && pwd)" || { echo "no such dir: $2"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEN="$SCRIPT_DIR/gen-team-dashboard.py"
TMP="$DIR/tmp"
PIDFILE="$TMP/team-dashboard.pid"
STATE="$TMP/team-dashboard-state.json"

mkdir -p "$TMP"

cfgget() {
  python3 - "$DIR/.opencode/team-dashboard.json" "$1" "$2" << 'PYEOF'
import json, os, sys
cfg, key, default = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    print(json.load(open(cfg)).get(key, default))
except Exception:
    print(default)
PYEOF
}

REFRESH="$(cfgget refresh 5)"
OPEN_URL="$(cfgget open_browser true)"

running() {
  [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

open_browser() {
  [ "$OPEN_URL" = "true" ] || return 0
  command -v open >/dev/null 2>&1 && open "$TMP/team-dashboard.html" && return 0
  command -v xdg-open >/dev/null 2>&1 && xdg-open "$TMP/team-dashboard.html"
}

case "$CMD" in
  once)
    exec python3 "$GEN" "$DIR"
    ;;
  start)
    if running; then
      echo "dashboard already running (pid $(cat "$PIDFILE"))"
      exit 0
    fi
    if [ ! -f "$STATE" ]; then
      python3 -c "import json, time; json.dump({'start_ms': int(time.time()*1000)}, open('$STATE', 'w'))"
    fi
    nohup bash -c "while :; do python3 '$GEN' '$DIR' >/dev/null 2>&1 || true; sleep $REFRESH; done" \
      >/dev/null 2>&1 &
    echo $! > "$PIDFILE"
    python3 "$GEN" "$DIR" >/dev/null 2>&1 || true
    open_browser
    echo "dashboard: $TMP/team-dashboard.html (refresh ${REFRESH}s, pid $(cat "$PIDFILE"))"
    ;;
  stop)
    if running; then
      kill "$(cat "$PIDFILE")" 2>/dev/null
      rm -f "$PIDFILE"
      python3 "$GEN" "$DIR" >/dev/null 2>&1 || true
      echo "dashboard stopped; final view kept at $TMP/team-dashboard.html"
    else
      echo "dashboard not running"
    fi
    ;;
  status)
    if running; then
      echo "running (pid $(cat "$PIDFILE"), refresh ${REFRESH}s)"
    else
      echo "not running"
    fi
    ;;
  *)
    echo "unknown command: $CMD" >&2
    exit 1
    ;;
esac

#!/usr/bin/env bash
# team-dashboard.sh start|stop|once|status <project-dir> [--resume]
# start : begin a NEW run window (resets state) and launch the refresh loop
#         --resume : keep the existing state (mid-run dashboard restart)
# stop  : kill the loop (state + final HTML are kept for review)
# once  : single generation pass
# status: report loop state
# Config: <project>/.opencode/team-dashboard.json
#   {"mode": "ask"|"always"|"never", "refresh": 5, "open_browser": true}
set -u

CMD="${1:?usage: team-dashboard.sh start|stop|once|status <project-dir> [--resume]}"
DIR="${2:?usage: team-dashboard.sh start|stop|once|status <project-dir> [--resume]}"
RESUME="${3:-}"
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
    print(str(json.load(open(cfg)).get(key, default)).lower())
except Exception:
    print(str(default).lower())
PYEOF
}

REFRESH="$(cfgget refresh 5)"
REFRESH="${REFRESH%%.*}"
[ "$REFRESH" -ge 2 ] 2>/dev/null || REFRESH=5
OPEN_URL="$(cfgget open_browser true)"

running() {
  # pid alive AND it is our loop (never kill a recycled pid)
  [ -f "$PIDFILE" ] || return 1
  local pid
  pid="$(cat "$PIDFILE")"
  kill -0 "$pid" 2>/dev/null || return 1
  ps -p "$pid" -o command= 2>/dev/null | grep -q "gen-team-dashboard" || return 1
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
    if [ "$RESUME" != "--resume" ] || [ ! -f "$STATE" ]; then
      python3 - "$STATE" << 'PYEOF'
import json, sys, time
json.dump({"start_ms": int(time.time() * 1000)}, open(sys.argv[1], "w"))
PYEOF
    fi
    # loop args passed positionally: no project path is interpolated into
    # the script body (apostrophes / ';' in paths are safe)
    nohup bash -c 'while :; do python3 "$1" "$2" >/dev/null 2>&1 || true; sleep "$3"; done' \
      dash-loop "$GEN" "$DIR" "$REFRESH" >/dev/null 2>&1 &
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

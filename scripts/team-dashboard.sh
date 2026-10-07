#!/usr/bin/env bash
# team-dashboard.sh serve|stop|once|status <project-dir> [--resume]
# serve : start the localhost web dashboard (alias: start). Fixed port from
#         config; window adoption is automatic (an in-flight run is always
#         picked up, so --resume is accepted but unnecessary).
# stop  : kill the server; the final snapshot stays at tmp/team-dashboard.html
# once  : single file generation (debug / file mode)
# status: server state + URL
# Config per key: <project>/.opencode/team-dashboard.json over
#   ~/.config/opencode/team-dashboard.json (mode, refresh, open_browser, port)
set -u

CMD="${1:?usage: team-dashboard.sh serve|stop|once|status <project-dir> [--resume]}"
[ "$CMD" = "start" ] && CMD="serve"
DIR="${2:?usage: team-dashboard.sh serve|stop|once|status <project-dir> [--resume]}"
DIR="$(cd "$DIR" 2>/dev/null && pwd)" || { echo "no such dir: $2"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEN="$SCRIPT_DIR/gen-team-dashboard.py"
SRV="$SCRIPT_DIR/dashboard_server.py"
TMP="$DIR/tmp"
PIDFILE="$TMP/team-dashboard.pid"
LOG="$TMP/team-dashboard-server.log"

mkdir -p "$TMP"

cfgget() {
  python3 "$GEN" --cfg "$1" "$DIR"
}

PORT="$(cfgget port)"
URL="http://127.0.0.1:${PORT}/"

running() {
  # pid alive AND it is our server (never kill a recycled pid)
  [ -f "$PIDFILE" ] || return 1
  local pid
  pid="$(cat "$PIDFILE")"
  kill -0 "$pid" 2>/dev/null || return 1
  ps -p "$pid" -o command= 2>/dev/null | grep -q "dashboard_server" || return 1
}

open_browser() {
  [ "$(cfgget open_browser | tr 'A-Z' 'a-z')" = "true" ] || return 0
  command -v open >/dev/null 2>&1 && open "$URL" && return 0
  command -v xdg-open >/dev/null 2>&1 && xdg-open "$URL"
}

wait_port() {
  # up to ~6s for the server to answer (or die with a conflict message)
  python3 - "$PORT" << 'PYEOF'
import socket, sys, time
port = int(sys.argv[1])
deadline = time.time() + 6
while time.time() < deadline:
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=0.5)
        s.close()
        sys.exit(0)
    except OSError:
        time.sleep(0.25)
sys.exit(1)
PYEOF
}

case "$CMD" in
  once)
    exec python3 "$GEN" "$DIR"
    ;;
  serve)
    if running; then
      echo "dashboard already running (pid $(cat "$PIDFILE")): $URL"
      open_browser
      exit 0
    fi
    nohup python3 "$SRV" "$DIR" >"$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    if wait_port; then
      echo "dashboard: $URL (pid $(cat "$PIDFILE"))"
    else
      echo "dashboard failed to start; log tail:" >&2
      tail -5 "$LOG" >&2
      rm -f "$PIDFILE"
      exit 1
    fi
    ;;
  stop)
    if running; then
      pid="$(cat "$PIDFILE")"
      kill "$pid" 2>/dev/null || true
      echo "dashboard server stopped (pid $pid)"
    fi
    rm -f "$PIDFILE"
    # final snapshot of the last render for after-the-fact review
    python3 "$GEN" "$DIR" >/dev/null 2>&1 || true
    echo "final snapshot: $TMP/team-dashboard.html"
    ;;
  status)
    if running; then
      echo "running: $URL (pid $(cat "$PIDFILE"))"
    else
      echo "stopped; snapshot (if any): $TMP/team-dashboard.html"
    fi
    ;;
  *)
    echo "usage: team-dashboard.sh serve|stop|once|status <project-dir> [--resume]" >&2
    exit 1
    ;;
esac

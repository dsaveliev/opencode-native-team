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

wait_ours() {
  # 0 = OUR dashboard answers /state with this project's name;
  # 3 = the port serves ANOTHER project's dashboard (holder's message is
  #     in the log we just captured); 1 = timeout or our server died
  python3 - "$PORT" "$(basename "$DIR")" << 'PYEOF'
import http.client, json, sys, time
port, want = int(sys.argv[1]), sys.argv[2]
deadline = time.time() + 6
while time.time() < deadline:
    try:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=0.5)
        c.request("GET", "/state")
        d = json.loads(c.getresponse().read())
        c.close()
        sys.exit(0 if d.get("project") == want else 3)
    except Exception:
        time.sleep(0.25)
sys.exit(1)
PYEOF
}

probe_ours() {
  # true when a dashboard server (ours) answers on the port
  python3 - "$PORT" << 'PYEOF'
import json, sys, urllib.request
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/state", timeout=1.5) as r:
        sys.exit(0 if "sig" in json.loads(r.read()) else 1)
except Exception:
    sys.exit(1)
PYEOF
}

switch_to() {
  # re-point the running dashboard to a directory (D6 single-dashboard)
  python3 - "$PORT" "$1" << 'PYEOF'
import json, sys, urllib.request
req = urllib.request.Request(
    f"http://127.0.0.1:{sys.argv[1]}/control/switch",
    data=json.dumps({"dir": sys.argv[2]}).encode(), method="POST",
    headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=8) as r:
        sys.exit(0 if json.loads(r.read()).get("ok") else 1)
except Exception:
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
    # single-dashboard philosophy (D6): a dashboard already serving another
    # project is re-pointed here instead of failing on the port
    if probe_ours; then
      if switch_to "$DIR" && wait_ours; then
        echo "dashboard re-pointed: $URL (project $(basename "$DIR"))"
        open_browser
        exit 0
      fi
      echo "dashboard: failed to re-point the running dashboard to $DIR" >&2
      exit 1
    fi
    nohup python3 "$SRV" "$DIR" >"$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    wait_ours; rc=$?
    if [ "$rc" -eq 0 ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "dashboard: $URL (pid $(cat "$PIDFILE"), project $(basename "$DIR"))"
    elif [ "$rc" -eq 3 ]; then
      echo "dashboard failed: port $PORT serves ANOTHER project's dashboard:" >&2
      # our server names the holder pid on exit; give its log a moment
      i=0
      while [ $i -lt 8 ] && ! grep -q "already in use" "$LOG" 2>/dev/null; do
        sleep 0.5
        i=$((i + 1))
      done
      if grep -q "already in use" "$LOG" 2>/dev/null; then
        tail -2 "$LOG" >&2
      elif command -v lsof >/dev/null 2>&1; then
        lsof -nP -i :"$PORT" | tail -n +2 >&2
      fi
      echo "stop it first (team-dashboard.sh stop <that-dir>), or set 'port' in $DIR/.opencode/team-dashboard.json" >&2
      rm -f "$PIDFILE"
      exit 1
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

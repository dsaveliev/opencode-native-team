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
LOG="$TMP/team-dashboard-server.log"
# dashboard-control-hardening D4: ONE machine-level owner record for the
# singleton server (pid + currently observed project) — per-project pidfiles
# could not express A -> B -> A, and `stop` from another dir missed the server
STATE_DIR="${HOME}/.local/state/opencode-team"

mkdir -p "$TMP" "$STATE_DIR"

cfgget() {
  python3 "$GEN" --cfg "$1" "$DIR"
}

PORT="$(cfgget port)"
URL="http://127.0.0.1:${PORT}/"
OWNER="${STATE_DIR}/team-dashboard-${PORT}.json"

owner_field() {  # pid | dir from the owner record, "" if absent
  [ -f "$OWNER" ] || return 0
  python3 - "$OWNER" "$1" << 'PYEOF'
import json, sys
try:
    print(json.load(open(sys.argv[1])).get(sys.argv[2], ""))
except Exception:
    print("")
PYEOF
}

write_owner() {  # pid dir
  python3 - "$OWNER" "$1" "$2" << 'PYEOF'
import json, sys, os
os.makedirs(os.path.dirname(sys.argv[1]), exist_ok=True)
json.dump({"pid": int(sys.argv[2]), "dir": sys.argv[3]}, open(sys.argv[1], "w"))
PYEOF
}

owner_alive() {  # record pid alive AND it is our server (never kill a recycled pid)
  local p
  p="$(owner_field pid)"
  [ -n "$p" ] || return 1
  kill -0 "$p" 2>/dev/null || return 1
  ps -p "$p" -o command= 2>/dev/null | grep -q "dashboard_server" || return 1
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
    if owner_alive && [ "$(owner_field dir)" = "$DIR" ]; then
      echo "dashboard already running (pid $(owner_field pid), project $(basename "$DIR")): $URL"
      open_browser
      exit 0
    fi
    # singleton: switch back (A -> B -> A), or ADOPT a running dashboard
    # left by an older per-project-pidfile scheme (no readable owner record)
    if probe_ours; then
      if switch_to "$DIR" && wait_ours; then
        OPID="$(owner_field pid)"
        if [ -z "$OPID" ] && command -v lsof >/dev/null 2>&1; then
          OPID="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | tail -n +2 | awk '{print $2}' | head -1)"
        fi
        [ -n "$OPID" ] && write_owner "$OPID" "$DIR"
        echo "dashboard re-pointed: $URL (pid $OPID, project $(basename "$DIR"))"
        open_browser
        exit 0
      fi
      echo "dashboard: failed to re-point the running dashboard to $DIR" >&2
      exit 1
    fi
    rm -f "$OWNER"  # stale record
    nohup python3 "$SRV" "$DIR" >"$LOG" 2>&1 &
    write_owner $! "$DIR"
    wait_ours; rc=$?
    if [ "$rc" -eq 0 ] && kill -0 "$(owner_field pid)" 2>/dev/null; then
      echo "dashboard: $URL (pid $(owner_field pid), project $(basename "$DIR"))"
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
      rm -f "$OWNER"
      exit 1
    else
      echo "dashboard failed to start; log tail:" >&2
      tail -5 "$LOG" >&2
      rm -f "$OWNER"
      exit 1
    fi
    ;;
  stop)
    if owner_alive; then
      kill "$(owner_field pid)" 2>/dev/null || true
      echo "dashboard server stopped (pid $(owner_field pid))"
    fi
    OD="$(owner_field dir)"
    rm -f "$OWNER"
    # final snapshot of the observed project's last render for after-the-fact review
    SNAP="${OD:-$DIR}"
    python3 "$GEN" "$SNAP" >/dev/null 2>&1 || true
    echo "final snapshot: $SNAP/tmp/team-dashboard.html"
    ;;
  status)
    if owner_alive; then
      echo "running: $URL (pid $(owner_field pid), project $(basename "$(owner_field dir)"))"
    else
      echo "stopped; snapshot (if any): $TMP/team-dashboard.html"
    fi
    ;;
  *)
    echo "usage: team-dashboard.sh serve|stop|once|status <project-dir> [--resume]" >&2
    exit 1
    ;;
esac

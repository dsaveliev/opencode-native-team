#!/usr/bin/env python3
"""dashboard_server.py <project-dir> — serve the team dashboard (localhost).

Routes:
  GET /                dashboard page (rendered on demand, memoized per refresh)
  GET /state           dashboard data as JSON + change signature for the poller
  POST /control/stop   {"pid": <int>} — SIGTERM to a verified opencode process
                       (dashboard-session-control D2/D3: JSON content-type
                       required, live re-verification, never arbitrary pids)
  POST /control/switch {"dir": <path>} — re-point observation to another
                       project directory (D6 single-dashboard pivot: one
                       server per machine, selection happens in the UI)
  any other request    404/405

Binds 127.0.0.1 only (network isolation is a spec requirement). FIXED port
from the config chain (default 4731): if occupied, exits non-zero naming the
occupying PID and command line — never silently re-allocates. Window
adoption happens inside the render path (gen-team-dashboard.adopt_window):
a run already in flight is always picked up, however the server started.
"""

import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "gen_team_dashboard", os.path.join(HERE, "gen-team-dashboard.py")
)
gtm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gtm)

DIR = os.path.abspath(sys.argv[1])
PORT = int(gtm.cfg_chain(DIR, "port", 4731))
REFRESH = max(2, int(gtm.cfg_chain(DIR, "refresh", 5) or 5))
OPEN = str(gtm.cfg_chain(DIR, "open_browser", True)).lower() != "false"

_lock = threading.Lock()
_gen = {"ts": 0.0, "data": None, "html": None}


def generation():
    """One cached (data, html) generation; TTL = refresh seconds.

    / and /state always answer from the SAME generation, so a poller-triggered
    reload shows exactly what /state advertised (no torn view)."""
    with _lock:
        now = time.time()
        if _gen["data"] is None or now - _gen["ts"] >= REFRESH:
            _gen["data"] = gtm.collect_data(DIR)
            _gen["html"] = gtm.render_html(DIR, _gen["data"])
            _gen["ts"] = now
        return _gen["data"], _gen["html"]


# dashboard-control-hardening D3: executable identity, not command line —
# a renamed/symlinked binary (e.g. /bin/sleep as "opencode") must fail
IDENTITY_RE = re.compile(r"^opencode(-cli)?$")


def switch_target(new_dir):
    """Re-point observation to another project directory (D6).

    Read-only for the target: nothing is written anywhere; the in-memory
    target changes and the next generation renders the new project."""
    global DIR
    d = os.path.abspath(new_dir)
    if not os.path.isdir(d):
        return f"no such directory: {new_dir}"
    with _lock:
        DIR = d
        _gen["data"] = None
        _gen["html"] = None
        _gen["ts"] = 0.0
    return None


def _exec_identity(pid):
    """(comm, resolved executable) for a pid.

    comm is the path used at exec (symlinks preserved); the lsof txt entry
    (first non-dyld) is the RESOLVED binary — a symlink named "opencode"
    pointing at /bin/sleep therefore resolves to "sleep"."""
    r = subprocess.run(
        ["ps", "-p", str(pid), "-o", "comm="], capture_output=True, text=True
    )
    comm = r.stdout.strip()
    txt = ""
    r2 = subprocess.run(["lsof", "-p", str(pid)], capture_output=True, text=True)
    for ln in r2.stdout.splitlines():
        f = ln.split()
        if len(f) > 3 and f[3] == "txt" and "dyld" not in f[-1]:
            txt = f[-1]
            break
    return comm, txt


def stop_opencode(pid):
    """SIGTERM a pid only if its RESOLVED executable is opencode (D3).

    Re-verified against the live process table at execution time — stale
    panel data must never authorize a signal. Returns an error string or None."""
    if pid <= 1:
        return "invalid pid"
    if pid == os.getpid():
        return "refusing to stop the dashboard server itself"
    comm, txt = _exec_identity(pid)
    if not comm:
        return f"pid {pid} not found"
    # resolved binary must BE opencode (comm is only the lsof-less fallback);
    # a symlink named "opencode" -> /bin/sleep resolves to "sleep"
    ident = os.path.basename(txt or comm)
    if not IDENTITY_RE.match(ident):
        return f"pid {pid} is not an opencode process ({ident})"
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return None  # exited between the check and the signal — done
    except PermissionError:
        return "permission denied"
    return None


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            _, page = generation()
            self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/state":
            data, _ = generation()
            body = json.dumps(gtm.state_json(data)).encode("utf-8")
            self._send(200, body, "application/json")
        else:
            self._send(404, b"not found\n", "text/plain")

    def do_POST(self):
        if self.path not in ("/control/stop", "/control/switch"):
            self._send(405, b"POST reserved for the control plane\n", "text/plain")
            return
        # D2 (dashboard-control-hardening): localhost Host only, before the
        # body is read — same-origin blocks cross-page reads, this is the
        # promised defence in depth for the local control surface
        host = (self.headers.get("Host") or "").strip()
        if host not in (f"127.0.0.1:{PORT}", f"localhost:{PORT}"):
            self._send(
                403,
                json.dumps({"error": "non-localhost host"}).encode(),
                "application/json",
            )
            return
        # D3: JSON content-type is required — an HTML <form> cannot send it,
        # which closes the cross-site form CSRF class without tokens
        ctype = self.headers.get("Content-Type", "").split(";")[0].strip()
        if ctype != "application/json":
            self._send(
                400,
                json.dumps({"error": "Content-Type must be application/json"}).encode(),
                "application/json",
            )
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            self._send(
                400,
                json.dumps({"error": "body must be JSON"}).encode(),
                "application/json",
            )
            return
        if self.path == "/control/switch":
            if not isinstance(body.get("dir"), str) or not body["dir"].strip():
                self._send(
                    400,
                    json.dumps({"error": 'body must be {"dir": "<path>"}'}).encode(),
                    "application/json",
                )
                return
            err = switch_target(body["dir"])
            if err:
                self._send(403, json.dumps({"error": err}).encode(), "application/json")
                return
            self._send(
                200,
                json.dumps({"ok": True, "project": os.path.basename(DIR)}).encode(),
                "application/json",
            )
            return
        try:
            pid = int(body["pid"])
        except Exception:
            self._send(
                400,
                json.dumps({"error": 'body must be {"pid": <int>}'}).encode(),
                "application/json",
            )
            return
        err = stop_opencode(pid)
        if err:
            self._send(403, json.dumps({"error": err}).encode(), "application/json")
            return
        time.sleep(2.0)  # per-request thread; gives SIGTERM a moment to land
        # kill -0 succeeds on zombies too (unreaped children of other
        # processes), so liveness = listed AND not in zombie state
        r = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True
        )
        st_ = r.stdout.strip()
        alive = bool(st_) and not st_.startswith("Z")
        self._send(
            200,
            json.dumps({"ok": True, "pid": pid, "alive_after": alive}).encode(),
            "application/json",
        )

    def log_message(self, format, *args):
        pass  # keep the server log quiet (tmp/team-dashboard-server.log)


def port_holder():
    """(pid, cmdline) of the process listening on PORT, or None."""
    try:
        r = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{PORT}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
        )
        lines = [ln for ln in r.stdout.strip().splitlines()[1:] if ln.strip()]
        if not lines:
            return None
        pid = lines[0].split()[1]
        cmd = subprocess.run(
            ["ps", "-p", pid, "-o", "command="], capture_output=True, text=True
        ).stdout.strip()
        return pid, cmd
    except Exception:
        return None


def main():
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        holder = port_holder()
        if holder:
            print(
                f"dashboard: port {PORT} already in use by pid {holder[0]}: "
                f"{holder[1]}",
                file=sys.stderr,
            )
        else:
            print(
                f"dashboard: port {PORT} already in use (holder unknown)",
                file=sys.stderr,
            )
        return 1
    print(
        f"dashboard: http://127.0.0.1:{PORT}/ ({os.path.basename(DIR)}), "
        f"refresh {REFRESH}s",
        flush=True,
    )
    if OPEN:
        threading.Timer(
            0.5, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}/")
        ).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

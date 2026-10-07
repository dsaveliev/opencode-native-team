#!/usr/bin/env python3
"""dashboard_server.py <project-dir> — serve the team dashboard (localhost).

Routes (change dashboard-serve, design D1):
  GET /       dashboard page (rendered on demand, memoized per refresh)
  GET /state  dashboard data as JSON + change signature for the poller
  POST        405 — reserved for the future control layer (not built)

Binds 127.0.0.1 only (network isolation is a spec requirement). FIXED port
from the config chain (default 4731): if occupied, exits non-zero naming the
occupying PID and command line — never silently re-allocates. Window
adoption happens inside the render path (gen-team-dashboard.adopt_window):
a run already in flight is always picked up, however the server started.
"""

import importlib.util
import json
import os
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
        # future control layer (design D1 extension point) — nothing yet
        self._send(405, b"POST reserved for the future control layer\n", "text/plain")

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

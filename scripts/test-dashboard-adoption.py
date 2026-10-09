#!/usr/bin/env python3
"""test-dashboard-adoption.py — unit checks for dashboard-serve internals:
window adoption (design D3) and the config chain (design D5).

Pure tmpdir + fixture sqlite DB (module DB path is patched); never touches
the real session database. Mirrors scripts/test-dashboard.py conventions.
"""

import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "gtm", os.path.join(HERE, "gen-team-dashboard.py")
)
gtm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gtm)

fails = []


def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        fails.append(name)


tmp = tempfile.mkdtemp(prefix="dash-adopt-")
try:
    # fixture session DB: one in-flight orchestrator session for the project
    # (created 1h ago, updated 30s ago)
    db = os.path.join(tmp, "fake.db")
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE session (id TEXT, agent TEXT, model TEXT, directory TEXT, "
        "time_created INTEGER, time_updated INTEGER, parent_id TEXT, "
        "tokens_input INTEGER, tokens_output INTEGER, tokens_reasoning INTEGER, "
        "title TEXT)"
    )
    proj = os.path.join(tmp, "proj")
    os.makedirs(proj)
    now = int(time.time() * 1000)
    con.execute(
        "INSERT INTO session VALUES ('s1','orchestrator','{}',?,?,?,NULL,1,1,1,'')",
        (proj, now - 3600_000, now - 30_000),
    )
    con.commit()
    con.close()
    gtm.DB = db  # module-level: every helper reads it per call

    # 1. window starts AFTER the run (the live qc-fop defect) -> adopted
    sp = gtm.state_path(proj)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    json.dump({"start_ms": now + 60_000}, open(sp, "w"))
    start, have = gtm.adopt_window(proj, now)
    check("in-flight run adopted", have and start == now - 3600_000)
    check("adopted window persisted", json.load(open(sp))["start_ms"] == now - 3600_000)

    # 2. non-empty declared window is kept verbatim (no re-adoption churn)
    json.dump({"start_ms": now - 7200_000}, open(sp, "w"))
    sess2 = gtm.load_sessions(proj, now - 7200_000)
    start2, have2 = gtm.adopt_window(proj, now)
    check("declared window kept when non-empty", have2 and start2 == now - 7200_000)
    # schema parity: load_sessions selects `title`; a fixture drift fails the
    # count loudly instead of passing "non-empty" on a swallowed SQL error
    check("fixture schema parity (1 session readable)", len(sess2) == 1)

    # 3. nothing adoptable (no active sessions in 12h) -> window kept
    con = sqlite3.connect(db)
    con.execute("UPDATE session SET time_updated = ?", (now - 13 * 3600_000,))
    con.commit()
    con.close()
    json.dump({"start_ms": now - 1000_000}, open(sp, "w"))
    start3, have3 = gtm.adopt_window(proj, now)
    check(
        "stale window kept when nothing adoptable", have3 and start3 == now - 1000_000
    )

    # 4. config chain: project over global (installation) over default
    gcfg = os.path.join(tmp, "global.json")
    json.dump({"refresh": 5, "port": 9999}, open(gcfg, "w"))
    gtm.GLOBAL_CFG = gcfg
    os.makedirs(os.path.join(proj, ".opencode"))
    json.dump(
        {"refresh": 2},
        open(os.path.join(proj, ".opencode", "team-dashboard.json"), "w"),
    )
    check("project overrides global", gtm.cfg_chain(proj, "refresh", 5) == 2)
    check("global fills missing key", gtm.cfg_chain(proj, "port", 4731) == 9999)
    check("default when both absent", gtm.cfg_chain(proj, "mode", "ask") == "ask")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print(f"ADOPTION TEST FAILED: {len(fails)}")
    sys.exit(1)
print("ADOPTION TEST PASSED")

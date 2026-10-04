#!/usr/bin/env python3
"""test-dashboard.py — behavioral smoke test for the team dashboard.

Builds a fixture project (git + openspec tasks + config), runs the real
generator, and asserts on the produced HTML. Catches the defect classes
from review round 7: run-window leakage (D-1/D-2), config-driven refresh
(D-6), tasks panel rendering (D-4), crash-free generation.
"""

import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "scripts", "gen-team-dashboard.py")

fails = []


def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        fails.append(name)


fx = tempfile.mkdtemp(prefix="dash-fixture-")
try:
    os.makedirs(os.path.join(fx, ".opencode"))
    os.makedirs(os.path.join(fx, "openspec", "changes", "alpha"))
    os.makedirs(os.path.join(fx, "openspec", "changes", "archive", "2026-01-01-old"))

    # git with two commits
    def git(*a):
        subprocess.run(["git", *a], cwd=fx, capture_output=True, check=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    open(os.path.join(fx, "f.txt"), "w").write("1")
    git("add", "-A")
    git("commit", "-qm", "first")
    open(os.path.join(fx, "f.txt"), "w").write("2")
    git("add", "-A")
    git("commit", "-qm", "second")

    # active change: 2 done / 2 todo
    open(os.path.join(fx, "openspec", "changes", "alpha", "tasks.md"), "w").write(
        "# Tasks\n\n## Wave 1\n\n- [x] 1. scaffold done thing\n"
        "- [x] 2. proto done thing\n\n## Wave 2\n\n"
        "- [ ] 3. engine todo thing\n  - [ ] 3.1 nested sub thing\n"
        "- [ ] 4. server todo thing\n"
    )
    # archived change from an OLD date: 40 done — must NOT leak into the window
    open(
        os.path.join(
            fx, "openspec", "changes", "archive", "2026-01-01-old", "tasks.md"
        ),
        "w",
    ).write(
        "# Tasks\n\n" + "".join(f"- [x] {i}. old archived task\n" for i in range(40))
    )

    # config: refresh 15, no browser, coverage off (no Go in CI)
    open(os.path.join(fx, ".opencode", "team-dashboard.json"), "w").write(
        '{"mode": "always", "refresh": 15, "open_browser": false, "coverage_ttl": 0}'
    )

    # code file so the LOC card has something to count
    os.makedirs(os.path.join(fx, "cmd"), exist_ok=True)
    open(os.path.join(fx, "cmd", "main.go"), "w").write(
        "package main\n\nfunc main() { println(1) }\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=fx, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "loc fixture"], cwd=fx, capture_output=True, check=True
    )

    # run window state: started now (this is "this run")
    state = os.path.join(fx, "tmp", "team-dashboard-state.json")
    os.makedirs(os.path.dirname(state), exist_ok=True)
    import json

    json.dump({"start_ms": int(time.time() * 1000)}, open(state, "w"))

    r = subprocess.run([sys.executable, GEN, fx], capture_output=True, text=True)
    check("generator exit 0", r.returncode == 0)
    page = open(os.path.join(fx, "tmp", "team-dashboard.html"), encoding="utf-8").read()

    # D-2: archived (old) change must not leak: 2/5, not 42/45
    check("tasks card 2/5", ">2/5<" in page)
    check("old archive excluded (no 42/45)", ">42/45<" not in page)
    check("no old archived task titles", "old archived task" not in page)
    # D-4: task titles render (done dimmed, todo present)
    check("todo task rendered", "engine todo thing" in page)
    check("done task rendered", "scaffold done thing" in page)
    check("wave header rendered", "Wave 1" in page)
    # D-6: refresh from config drives the page timer, not the hardcoded 5
    check("refresh from config (15s)", "R = 15 * 1000" in page and "(15s)" in page)
    check("no stale 5s timer", "R = 5 * 1000" not in page and 'content="5"' not in page)
    # commits within window: both fixture commits are at window start
    check("commits rendered", "first" in page and "second" in page)
    # stepper present
    check(
        "stage stepper", re.search(r'class="step cur">plan|class="step cur">code', page)
    )
    # LOC counts tracked code (4 lines of Go), coverage renders a placeholder
    check("LOC card counts code", ">3<" in page and "loc (tracked)" in page)
    check("coverage placeholder", "&mdash;</div><div class=l>test coverage %" in page)
    # svg has explicit width/height (Safari renders height:auto-only svg at 0)
    check(
        "timeline svg has width/height attrs",
        re.search(r'<svg width="860" height="120"', page) is not None,
    )
    check(
        "nested task indented",
        "padding-left:24px" in page and "nested sub thing" in page,
    )
    check(
        "svg classes quoted",
        'class="line"/>' in page
        and 'class="grid"/>' in page
        and "class=line/>" not in page,
    )
    # atomic write: no leftover tmp
    check(
        "no .tmp leftover",
        not os.path.exists(os.path.join(fx, "tmp", "team-dashboard.html.tmp")),
    )

    # archive view (no state): old archive IS counted
    os.remove(state)
    r2 = subprocess.run([sys.executable, GEN, fx], capture_output=True, text=True)
    page2 = open(
        os.path.join(fx, "tmp", "team-dashboard.html"), encoding="utf-8"
    ).read()
    check("archive view counts old change", ">42/45<" in page2)
    check("archive view exit 0", r2.returncode == 0)
finally:
    shutil.rmtree(fx, ignore_errors=True)

print()
if fails:
    print(f"DASHBOARD TEST FAILED: {len(fails)}")
    sys.exit(1)
print("DASHBOARD TEST PASSED")

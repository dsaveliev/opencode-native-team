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

    # code files: main + second (forces the old wc "total" double-count bug)
    # + a filename with a quote (E-1 shell-injection probe)
    os.makedirs(os.path.join(fx, "cmd"), exist_ok=True)
    open(os.path.join(fx, "cmd", "main.go"), "w").write(
        "package main\n\nfunc main() { println(1) }\n"
    )
    open(os.path.join(fx, "two.go"), "w").write("package main\n\nvar X = 1\n")
    open(os.path.join(fx, "it's.go"), "w").write("package main\n")
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
    # E-2: exact LOC — main.go(3) + two.go(3) + it's.go(1) = 7; doubled=14
    # and loose ">3<" (matches 113) must both fail this check
    check(
        "LOC card exact (7, not doubled)",
        re.search(r"<div class=v>7</div><div class=l>loc \(tracked\)</div>", page)
        is not None,
    )
    check(
        "quote filename no injection",
        not os.path.exists(os.path.join(fx, "INJECTED_PROOF")),
    )
    check("coverage placeholder", "&mdash;</div><div class=l>test coverage %" in page)
    # svg has explicit width/height (Safari renders height:auto-only svg at 0)
    check(
        "activity svg has width/height attrs",
        re.search(r'<svg width="860" height="\d+"', page) is not None,
    )
    check(
        "nested task indented",
        "padding-left:24px" in page and "nested sub thing" in page,
    )
    check(
        "svg classes quoted",
        'class="grid"/>' in page
        and 'class="dia"' in page
        and 'class="axis"' in page
        and "class=line/>" not in page,
    )
    check("activity lanes present", page.count('class="lat"') >= 1)
    check(
        "hover popups via data-tip",
        'data-tip="' in page
        and "<title>" not in re.search(r"<svg.*?</svg>", page, re.S).group(0),
    )
    check("tasks+commits share a row", "class=row2" in page)
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

    # run-hardening: --export renders a complete markdown run log
    r3 = subprocess.run(
        [sys.executable, GEN, "--export", fx], capture_output=True, text=True
    )
    check("export exit 0", r3.returncode == 0)
    for section in (
        "# Run log",
        "## Waves / sessions",
        "## Task timings",
        "## Tool errors",
        "## Permission denials",
        "## Commits",
    ):
        check(f"export section: {section}", section in r3.stdout)
    check("export has task titles", "engine todo thing" in r3.stdout)

    # --- dashboard-ux-2: stage model, task tree, panels, anchors ---
    # macro stage from task progress: 2/5 done -> code (never role-derived)
    check("macro stage=code from progress", 'class="step cur">code' in page)
    check("now-label present (quiet, no sessions)", ">now: quiet<" in page)
    # collapsible top-level tasks with stable keys
    check("task <details> rendered", 'details class="tk"' in page)
    check("task data-k keys", 'data-k="alpha:1"' in page and 'data-k="alpha:3"' in page)
    check("subtask inside details", "nested sub thing" in page)
    # ETA projection: top-level 1,2 done -> est on remaining (min 1m)
    check("tmeta est present", 'class="tmeta est">~' in page)
    # tool errors panel beside work log, both with ids
    check(
        "tool errors panel",
        'id="panel-errors"' in page and ">Tool errors (0)</h2>" in page,
    )
    check("work log panel id", 'id="panel-log"' in page)
    # summary tiles anchor to panels
    check(
        "tile anchors",
        'href="#panel-tasks"' in page
        and 'href="#panel-commits"' in page
        and 'href="#panel-agents"' in page,
    )
    # expandable rows carry stable keys (expansion preservation, D3)
    check("log rows keyed", 'data-k="cmt:' in page)
    check("expansion JS present", "applyKeys" in page and "dash-open" in page)
    check("log buffer JS present", "LOGSEED" in page and "dash-log:" in page)

    # --- dashboard-ux-2 unit phase: pure stage/wave/span functions ---
    import importlib.util

    spec = importlib.util.spec_from_file_location("gtm", GEN)
    gtm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gtm)
    now = 1_000_000_000_000

    def sess(agent, created, updated, title=""):
        return {"agent": agent, "created": created, "updated": updated, "title": title}

    # wave regression: reviewer done 1 min ago, coder wave B active, 2/5 tasks
    wave_sessions = [
        sess("orchestrator", now - 3600_000, now - 60_000),
        sess("reviewer", now - 3000_000, now - 120_000, "Review wave A"),
        sess("coder", now - 900_000, now - 30_000, "Wave B: task 2.1"),
    ]
    check(
        "stage stays code across wave flip (was: review)",
        gtm.compute_stage(wave_sessions, 2, 5, now) == "code",
    )
    check(
        "all done + active -> review",
        gtm.compute_stage(wave_sessions, 5, 5, now) == "review",
    )
    check(
        "all done + quiet -> done",
        gtm.compute_stage(wave_sessions, 5, 5, now + 3600_000) == "done",
    )
    check("nothing done -> plan", gtm.compute_stage(wave_sessions, 0, 5, now) == "plan")
    role, wave = gtm.now_activity(wave_sessions, now)
    check("now activity = coder, wave 2", role == "coder" and wave == 2)
    # task durations from wave-title references + median projection
    span_sessions = [
        sess("coder", now - 1800_000, now - 900_000, "Wave A: task 1.1"),
        sess("tester", now - 900_000, now - 600_000, "Test wave A task 1.1"),
        sess("coder", now - 500_000, now - 100_000, "Wave B: task 1.2"),
    ]
    changes = [
        ("c", [("t", True, 0, "1.1 first thing"), ("t", False, 0, "1.2 second thing")])
    ]
    meta, med = gtm.task_spans(span_sessions, changes, now)
    check(
        "done task duration from wave span",
        meta["1.1"]["dur"] == 1_200_000,
    )
    check("pending task gets est = median", meta["1.2"]["est"] == 1_200_000)
    check("active task flagged", meta["1.2"]["act"] is True)
    check("median value", med == 1_200_000)
    # denial detection (run-hardening D3): exact opencode error wording
    denial_state = {
        "status": "error",
        "error": "The user has specified a rule which prevents you from "
        "using this specific tool call. Here are some of the relevant rules",
        "input": {"command": "go mod tidy && go test ./..."},
    }
    check(
        "denial detected with command",
        gtm.denial_of(denial_state) == "go mod tidy && go test ./...",
    )
    check(
        "plain error is not a denial",
        gtm.denial_of({"status": "error", "error": "exit status 1"}) is None,
    )
finally:
    shutil.rmtree(fx, ignore_errors=True)

print()
if fails:
    print(f"DASHBOARD TEST FAILED: {len(fails)}")
    sys.exit(1)
print("DASHBOARD TEST PASSED")

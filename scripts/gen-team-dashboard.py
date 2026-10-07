#!/usr/bin/env python3
"""gen-team-dashboard.py <project-dir> — one generation pass (v3).

Writes <project>/tmp/team-dashboard.html atomically from:
  - opencode session DB (agents, tokens, activity, work log, tool errors,
    subagent spawns via parent_id)
  - git log (commit timeline with a "now" marker, dirty files)
  - openspec tasks (run-window aware: archived changes count only if
    archived on/after the run start date)
  - team-dashboard.json (project .opencode/ over ~/.config/opencode/,
    over built-in defaults): mode, refresh, open_browser, port

Importable module (scripts/dashboard_server.py imports it):
  cfg_chain(dir, key, default)   config resolution project > global > default
  adopt_window(dir, now_ms)      in-flight run window adoption (D3)
  collect_data(dir) -> dict      all panels' data
  render_html(dir, data) -> str  full page (CLI and server share it)
  state_json(data) -> dict       GET /state payload + change signature

Exit 0 even on partial data (the loop must keep running). Zero deps, no CDN.
"""

import datetime
import glob
import html
import json
import os
import re
import sqlite3
import shutil
import subprocess
import sys
import time

DB = os.path.expanduser("~/.local/share/opencode/opencode.db")
GLOBAL_CFG = os.path.expanduser("~/.config/opencode/team-dashboard.json")
ACTIVE_HORIZON_MS = 12 * 3600 * 1000  # adoption: "recently active" window

AGENT_COLORS = {
    "orchestrator": "#7c6bb0",
    "coder": "#3f8f5f",
    "tester": "#b45309",
    "reviewer": "#b91c1c",
}
BADGES = {"orchestrator": "ORC", "coder": "COD", "tester": "TST", "reviewer": "REV"}


def agent_color(a):
    return AGENT_COLORS.get(a, "#66707c")


def agent_badge(a):
    b = BADGES.get(a)
    return (
        f'<span class=badge style="border-color:{agent_color(a)}">{b}</span>'
        if b
        else ""
    )


def sh(cmd, dir_):
    try:
        return subprocess.run(
            cmd, shell=True, cwd=dir_, capture_output=True, text=True
        ).stdout
    except Exception:
        return ""


def cfg_chain(dir_, key, default):
    """Per-key resolution: project .opencode/team-dashboard.json over the
    installation-wide ~/.config/opencode/team-dashboard.json over default.
    Unknown keys in either file are simply never looked up."""
    for p in (os.path.join(dir_, ".opencode", "team-dashboard.json"), GLOBAL_CFG):
        try:
            m = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(m, dict) and key in m:
            return m[key]
    return default


def state_path(dir_):
    return os.path.join(dir_, "tmp", "team-dashboard-state.json")


def fmt_ms(ms):
    m, s = divmod(int(ms / 1000), 60)
    return f"{m}m{s:02d}s" if m < 60 else f"{m // 60}h{m % 60:02d}m"


def fmt_k(n):
    n = n or 0
    if n >= 10000:
        return f"{round(n / 1000)}k"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def load_sessions(dir_, start_ms=None):
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        q = (
            "SELECT id, agent, model, time_created, time_updated, parent_id, "
            "tokens_input, tokens_output, tokens_reasoning "
            "FROM session WHERE directory = ?"
        )
        args = [dir_]
        if start_ms:
            q += " AND time_created >= ?"
            args.append(start_ms - 60_000)
        rows = con.execute(q, args).fetchall()
        con.close()
    except Exception:
        return []
    out = []
    for r in rows:
        try:
            model = json.loads(r[2]).get("id", "?")
        except Exception:
            model = "?"
        out.append(
            {
                "id": r[0],
                "agent": r[1],
                "model": model,
                "created": r[3],
                "updated": r[4],
                "parent": r[5],
                "tin": r[6] or 0,
                "tout": (r[7] or 0) + (r[8] or 0),
            }
        )
    return out


def load_parts(session_ids, sessions):
    """Recent text parts (work log) and errored tool parts (names)."""
    if not session_ids:
        return [], {}
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        q = (
            "SELECT p.session_id, p.time_updated, p.data FROM part p "
            "WHERE p.session_id IN (%s) ORDER BY p.time_updated DESC LIMIT 300"
            % ",".join("?" * len(session_ids))
        )
        rows = con.execute(q, session_ids).fetchall()
        con.close()
    except Exception:
        return [], {}
    texts, err_tools = [], {}
    for sid, t, data in rows:
        try:
            d = json.loads(data)
        except Exception:
            continue
        if d.get("type") == "text":
            txt = (d.get("text") or "").strip()
            if len(txt) > 40:
                agent = next((s["agent"] for s in sessions if s["id"] == sid), "?")
                texts.append((t, agent, txt))
        st = d.get("state") or {}
        if isinstance(st, dict) and st.get("status") == "error":
            tool = d.get("tool", "?")
            err_tools[tool] = err_tools.get(tool, 0) + 1
    texts.sort(key=lambda x: -x[0])
    return texts[:40], err_tools


def load_tasks(dir_, start_ms=None):
    """Checkbox tasks within the run window.

    Active changes always count. Archived changes count only when their
    archive date (dir name prefix) is on/after the run start date; without
    a run state (archive view) everything counts."""

    def entries(path):
        """Items: ("h", title) sections and ("t", done, depth, title) tasks;
        depth derived from bullet indentation."""
        out = []
        for raw in open(path, encoding="utf-8", errors="ignore"):
            if re.match(r"^## ", raw):
                out.append(("h", raw.lstrip("# ").strip()[:60]))
            m = re.match(r"(\s*)- \[([ x])]\s*(\d*\.?\s*.+)", raw)
            if m:
                depth = min(len(m.group(1)) // 2, 4)
                out.append(("t", m.group(2) == "x", depth, m.group(3).strip()[:90]))
        return out

    start_date = None
    if start_ms:
        start_date = datetime.datetime.fromtimestamp(start_ms / 1000).date()

    changes = []
    for path in sorted(
        glob.glob(os.path.join(dir_, "openspec", "changes", "*", "tasks.md"))
    ):
        name = os.path.basename(os.path.dirname(path))
        changes.append((name, entries(path)))
    for path in sorted(
        glob.glob(os.path.join(dir_, "openspec", "changes", "archive", "*", "tasks.md"))
    ):
        name = os.path.basename(os.path.dirname(path))
        dm = re.match(r"(\d{4}-\d{2}-\d{2})-", name)
        if start_date:
            # undated or pre-run archives belong to other runs' history
            if not dm or datetime.date.fromisoformat(dm.group(1)) < start_date:
                continue
        changes.append(("archive: " + name, entries(path)))

    done = sum(1 for _, es in changes for it in es if it[0] == "t" and it[1])
    total = sum(1 for _, es in changes for it in es if it[0] == "t")
    return done, total, changes


def load_commits(dir_, start_ms, have_state):
    # %x01 = SOH separator: immune to spaces/pipes in messages
    out = sh("git log --reverse --format=%at%x01%s", dir_)
    pts, msgs = [], []
    for line in out.split("\n"):
        if "\x01" not in line:
            continue
        ts, msg = line.split("\x01", 1)
        t = int(ts) * 1000
        if have_state and t < start_ms - 60_000:
            continue
        pts.append(max(0.0, (t - start_ms) / 60000))
        msgs.append(msg)
    return pts, msgs


def activity_chart(sessions, commits_t, commits_m, start_ms, now_ms):
    """Swimlane activity timeline.

    X axis: wall clock anchored at the run start — ticks sit at start + k*step
    with a stable step, so labels never shift as time passes; new ones only
    append to the right. The right edge is ~now, so no now-marker is needed.
    Lanes: commits (diamonds, full-message tooltips) on top, then one lane
    per agent with a bar per session (created..updated).
    """
    agents_present = []
    for a in ["orchestrator", "planner", "coder", "tester", "reviewer"]:
        if any(s["agent"] == a for s in sessions):
            agents_present.append(a)
    for a in sorted({s["agent"] for s in sessions} - set(agents_present)):
        agents_present.append(a)

    width = 860
    left, right = 118, 16
    lane_h = 28
    top_axis = 22
    height = top_axis + (len(agents_present) + 1) * lane_h + 10

    elapsed = max((now_ms - start_ms) / 60000, 1.0)
    if elapsed <= 10:
        step = 2
    elif elapsed <= 30:
        step = 5
    elif elapsed <= 90:
        step = 10
    else:
        step = 30
    xmax = max(-(-elapsed // step) * step, step * 2)  # ceil, min two steps

    def x(v):
        return left + v / xmax * (width - left - right)

    def hhmm(ms):
        return datetime.datetime.fromtimestamp(ms / 1000).strftime("%H:%M")

    s = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto">'
    ]
    # stable ticks: k*step from run start, wall-clock labels
    tick_every = 1 if xmax / step <= 8 else 2
    for k in range(0, int(xmax) + 1, step):
        gx = x(k)
        s.append(
            f'<line x1="{gx:.0f}" y1="{top_axis - 6}" x2="{gx:.0f}" '
            f'y2="{height - 8}" class="grid"/>'
        )
        if k % (step * tick_every) == 0:
            label = hhmm(start_ms + k * 60000)
            s.append(
                f'<text x="{gx:.0f}" y="12" text-anchor="middle" '
                f'class="axt">{label}</text>'
            )

    def lane_label(y, text, color):
        s.append(
            f'<text x="8" y="{y + 13:.0f}" class="lat" '
            f'style="fill:{color}">{html.escape(text)}</text>'
        )

    # commits lane (top)
    cy = top_axis + lane_h * 0 + lane_h / 2
    s.append(
        f'<line x1="{left}" y1="{cy:.0f}" x2="{width - right}" y2="{cy:.0f}" class="axis"/>'
    )
    lane_label(cy, "commits", "var(--acc)")
    for i, (p, m) in enumerate(zip(commits_t, commits_m)):
        if p > xmax:
            continue
        dx = x(p)
        tip = html.escape(f"#{i + 1} {hhmm(start_ms + p * 60000)} — {m}")
        s.append(
            f'<path d="M {dx:.0f} {cy - 5:.0f} L {dx + 5:.0f} {cy:.0f} '
            f'L {dx:.0f} {cy + 5:.0f} L {dx - 5:.0f} {cy:.0f} Z" '
            f'class="dia" data-tip="{tip}"></path>'
        )

    # agent lanes: one bar per session
    for li, a in enumerate(agents_present, 1):
        ly = top_axis + li * lane_h
        mid = ly + lane_h / 2
        s.append(
            f'<line x1="{left}" y1="{mid:.0f}" x2="{width - right}" y2="{mid:.0f}" class="axis"/>'
        )
        lane_label(mid, f"{a} {BADGES.get(a, '')}".strip(), agent_color(a))
        for ses in sessions:
            if ses["agent"] != a:
                continue
            x1 = x(max((ses["created"] - start_ms) / 60000, 0))
            x2 = max(x1 + 3, x(min((ses["updated"] - start_ms) / 60000, xmax)))
            dur = fmt_ms(max(ses["updated"] - ses["created"], 0))
            tip = html.escape(
                f"{a} {hhmm(ses['created'])}–{hhmm(ses['updated'])} ({dur})"
            )
            s.append(
                f'<rect x="{x1:.0f}" y="{mid - 4:.0f}" width="{x2 - x1:.0f}" '
                f'height="8" rx="4" fill="{agent_color(a)}" fill-opacity="0.75" '
                f'data-tip="{tip}"></rect>'
            )
    s.append("</svg>")
    return "".join(s)


CODE_EXT = re.compile(r"\.(go|py|ts|tsx|js|jsx|rs|java|rb|php|c|cc|cpp|h|hpp|sh)$")


def project_loc(dir_):
    """Lines of code over tracked files (code extensions only).
    Counted in Python: no shell, no quoting, no wc total-line double-count."""
    files = [
        f
        for f in sh("git ls-files", dir_).split("\n")
        if f and CODE_EXT.search(f) and not f.startswith("vendor/")
    ]
    total = 0
    for f in files:
        try:
            with open(os.path.join(dir_, f), encoding="utf-8", errors="ignore") as fh:
                total += len(fh.read().splitlines())
        except OSError:
            continue
    return total


def test_coverage(dir_):
    """Mean per-package go test coverage. OPT-IN: coverage_ttl (seconds,
    default 0 = off — running tests from a dashboard tick is heavy and can
    race the tester agent). Failures are cached too, so a broken run does
    not retry every tick."""
    ttl = int(cfg_chain(dir_, "coverage_ttl", 0) or 0)
    if ttl <= 0:
        return None
    now_ms = time.time() * 1000
    cov_cache = os.path.join(dir_, "tmp", "team-dashboard-coverage.json")
    try:
        c = json.load(open(cov_cache, encoding="utf-8"))
        if now_ms - c["ts"] < (c.get("ttl", ttl)) * 1000:
            return c.get("pct")
    except Exception:
        pass
    if not os.path.exists(os.path.join(dir_, "go.mod")):
        return None
    if not shutil.which("go"):
        return None
    try:
        import subprocess as sp

        r = sp.run(
            ["go", "test", "-count=1", "-cover", "./..."],
            cwd=dir_,
            capture_output=True,
            text=True,
            timeout=45,
        )
        pcts = [float(m) for m in re.findall(r"coverage:\s+(\d+(?:\.\d+)?)%", r.stdout)]
        pct = round(sum(pcts) / len(pcts), 1) if pcts else None
        # cache success with the configured ttl, failure with 5x ttl
        cache_ttl = ttl if pct is not None else ttl * 5
        json.dump(
            {"pct": pct, "ts": int(now_ms), "ttl": cache_ttl},
            open(cov_cache, "w", encoding="utf-8"),
        )
        return pct
    except Exception:
        return None


def adopt_window(dir_, now_ms=None):
    """In-flight run window adoption (dashboard-serve D3).

    Returns (start_ms, have_state). When the state window yields zero
    sessions for the directory, roll the window back to the earliest
    session still updated within ACTIVE_HORIZON_MS and persist it — a run
    already in flight is always adopted, however monitoring started.
    Nothing adoptable: keep the declared window (empty dashboard is honest
    "nothing running"). No state file: archive view (all sessions)."""
    now_ms = now_ms if now_ms is not None else time.time() * 1000
    sp = state_path(dir_)
    start, have = None, os.path.exists(sp)
    if have:
        try:
            start = json.load(open(sp, encoding="utf-8"))["start_ms"]
        except Exception:
            start = None
    if start is not None:
        if load_sessions(dir_, start):
            return start, True
        earliest = None
        try:
            con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
            row = con.execute(
                "SELECT MIN(time_created) FROM session "
                "WHERE directory = ? AND time_updated >= ?",
                (dir_, now_ms - ACTIVE_HORIZON_MS),
            ).fetchone()
            con.close()
            earliest = row[0] if row else None
        except Exception:
            earliest = None
        if earliest is not None and earliest < start - 60_000:
            start = earliest
            os.makedirs(os.path.dirname(sp), exist_ok=True)
            json.dump({"start_ms": start}, open(sp, "w", encoding="utf-8"))
        return start, True
    _all = load_sessions(dir_)
    return min((s["created"] for s in _all), default=now_ms), False


def collect_data(dir_):
    now_ms = time.time() * 1000
    refresh = max(2, int(cfg_chain(dir_, "refresh", 5) or 5))
    start, have_state = adopt_window(dir_, now_ms)
    if have_state:
        sessions = load_sessions(dir_, start)
    else:
        sessions = load_sessions(dir_)
    texts, err_tools = load_parts([s["id"] for s in sessions], sessions)
    done, total, task_changes = load_tasks(dir_, start if have_state else None)
    commits_t, commits_m = load_commits(dir_, start, have_state)
    elapsed = max(now_ms - start, 0)
    porcelain = sh("git status --porcelain", dir_).strip()
    dirty = porcelain.count("\n") + (1 if porcelain else 0)

    agents = {}
    for s in sessions:
        a = agents.setdefault(
            s["agent"],
            {"n": 0, "spawns": 0, "tin": 0, "tout": 0, "model": s["model"], "last": 0},
        )
        a["n"] += 1
        if s["parent"]:
            a["spawns"] += 1
        a["tin"] += s["tin"]
        a["tout"] += s["tout"]
        a["last"] = max(a["last"], s["updated"])

    proj_loc = project_loc(dir_)
    coverage = test_coverage(dir_)
    spawns = sum(d["spawns"] for a, d in agents.items() if a != "orchestrator")
    tin = sum(s["tin"] for s in sessions)
    tout = sum(s["tout"] for s in sessions)
    last_act = max((s["updated"] for s in sessions), default=now_ms)
    active = now_ms - last_act < 180_000
    nerr = sum(err_tools.values())

    # stage stepper: last orchestrator text → keywords; fallback: last active agent
    stages = ["plan", "code", "test", "review", "done"]
    stage = None
    # primary signal: the most recently active SUBAGENT role (last 10 minutes) —
    # keyword scanning of one orchestrator text misfires on phrases like
    # "first coder, then reviewer"
    role2stage = {
        "planner": "plan",
        "coder": "code",
        "tester": "test",
        "reviewer": "review",
    }
    recent_sub = [
        (d["last"], a)
        for a, d in agents.items()
        if a in role2stage and now_ms - d["last"] < 600_000
    ]
    if recent_sub:
        stage = role2stage[max(recent_sub)[1]]
    orch_texts = [x for _t, a, x in texts if a == "orchestrator"]
    last_txt = orch_texts[0].lower() if orch_texts else ""
    for kw, st in [
        ("archive|final gates|closing", "done"),
    ]:
        if stage is None and re.search(kw, last_txt):
            stage = st
            break
    if stage is None:
        by_agent = {a: d["last"] for a, d in agents.items()}
        last_agent = max(by_agent, key=by_agent.get) if by_agent else None
        stage = role2stage.get(last_agent, "plan")
    stage_idx = stages.index(stage)
    steps = []
    for i, n in enumerate(stages):
        cls = "step"
        if i < stage_idx:
            cls += " done"
        if i == stage_idx:
            cls += " cur"
        steps.append(f'<span class="{cls}">{n}</span>')
        if i < len(stages) - 1:
            steps.append("<span class=sep></span>")
    stepper = "".join(steps)

    eta = "no ETA yet"
    if done:
        rate = (elapsed / 60000) / done
        eta = f"~{round(rate * (total - done))} min left"

    err_str = (
        ", ".join(
            f"{html.escape(str(t))}&times;{n}" for t, n in sorted(err_tools.items())
        )
        or "none"
    )

    cards = f"""
<div class=card><div class=v>{done}/{total}</div><div class=l>tasks done</div></div>
<div class=card><div class=v>{len(commits_t)}</div><div class=l>commits</div></div>
<div class=card><div class=v>{fmt_k(tin)}</div><div class=l>tokens in</div></div>
<div class=card><div class=v>{fmt_k(tout)}</div><div class=l>tokens out</div></div>
<div class=card><div class=v>{spawns}</div><div class=l>subagent spawns</div></div>
<div class=card><div class=v>{fmt_k(proj_loc)}</div><div class=l>loc (tracked)</div></div>
<div class=card><div class=v>{coverage if coverage is not None else "&mdash;"}</div><div class=l>test coverage %</div></div>
<div class=card><div class=v>{nerr}</div><div class=l>tool errors</div></div>
<div class=card><div class=v>{fmt_ms(elapsed)}</div><div class=l>elapsed &middot; {html.escape(eta)}</div></div>
"""

    agent_rows = "".join(
        f'<tr><td><b style="color:{agent_color(a)}">{html.escape(a)}</b> {agent_badge(a)}</td>'
        f"<td class=num>{d['n']}</td><td class=num>{d['spawns']}</td>"
        f"<td>{html.escape(d['model'])}</td><td class=num>{fmt_k(d['tin'])}</td>"
        f"<td class=num>{fmt_k(d['tout'])}</td>"
        f"<td class=num>{fmt_ms(max(now_ms - d['last'], 0))} ago</td>"
        f"<td>{'<span class=live>active</span>' if now_ms - d['last'] < 180_000 else 'idle'}</td></tr>"
        for a, d in sorted(agents.items())
    )

    pct = round(100 * done / total) if total else 0
    task_html = ""
    for name, es in task_changes:
        d_n = sum(1 for it in es if it[0] == "t" and it[1])
        t_n = sum(1 for it in es if it[0] == "t")
        task_html += f"<div class=tch>{html.escape(name)} — {d_n}/{t_n}</div>"
        for it in es:
            if it[0] == "h":
                task_html += f"<div class=tw>{html.escape(it[1])}</div>"
                continue
            _, d, depth, title = it
            cls = "tdone" if d else "ttodo"
            mark = "&#10003;" if d else "&#9744;"
            task_html += (
                f'<div class="{cls}" style="padding-left:{6 + depth * 18}px">'
                f"{mark} {html.escape(title)}</div>"
            )
        task_html += "<div style='height:6px'></div>"

    log_html = "".join(
        f"<div class=ev><span class=t>{datetime.datetime.fromtimestamp(t / 1000).strftime('%H:%M:%S')}</span>"
        f'<span class="ag" style="color:{agent_color(a)}">{html.escape(a)}{agent_badge(a)}</span>'
        f"<span class=tx onclick=\"this.classList.toggle('exp')\">{html.escape(x)}</span></div>"
        for t, a, x in texts
    )

    commit_entries = [
        f"<div class=ev><span class=t>+{p:.0f}m</span>"
        f"<span class=tx onclick=\"this.classList.toggle('exp')\">{html.escape(m)}</span></div>"
        for p, m in zip(reversed(commits_t), reversed(commits_m))
    ]
    commits_list = "".join(commit_entries[:40]) or "<div class=muted>none yet</div>"

    return {
        "dir": dir_,
        "now_ms": now_ms,
        "refresh": refresh,
        "start": start,
        "have_state": have_state,
        "sessions": sessions,
        "done": done,
        "total": total,
        "commits_t": commits_t,
        "commits_m": commits_m,
        "elapsed": elapsed,
        "dirty": dirty,
        "agents": agents,
        "proj_loc": proj_loc,
        "coverage": coverage,
        "spawns": spawns,
        "tin": tin,
        "tout": tout,
        "last_act": last_act,
        "active": active,
        "nerr": nerr,
        "stage": stage,
        "stepper": stepper,
        "eta": eta,
        "err_str": err_str,
        "cards": cards,
        "agent_rows": agent_rows,
        "pct": pct,
        "task_html": task_html,
        "log_html": log_html,
        "commits_list": commits_list,
    }


def state_sig(d):
    """Cheap change signature: poller compares this before reloading."""
    return (
        f"{len(d['sessions'])}:{d['done']}/{d['total']}:"
        f"{len(d['commits_t'])}:{int(d['last_act'])}"
    )


def state_json(d):
    """GET /state payload — the poller's data view of the dashboard."""
    return {
        "generated_ms": int(time.time() * 1000),
        "project": os.path.basename(d["dir"]),
        "active": d["active"],
        "stage": d["stage"],
        "sessions": len(d["sessions"]),
        "tasks_done": d["done"],
        "tasks_total": d["total"],
        "commits": len(d["commits_t"]),
        "run_start_ms": d["start"],
        "sig": state_sig(d),
    }


def render_html(dir_, d):
    DONE, TOTAL = d["done"], d["total"]
    SESSIONS, COMMITS_T = d["sessions"], d["commits_t"]
    START, NOW, REFRESH = d["start"], d["now_ms"], d["refresh"]
    DIRTY, last_act, err_str = d["dirty"], d["last_act"], d["err_str"]
    cards, stepper, pct = d["cards"], d["stepper"], d["pct"]
    agent_rows = d["agent_rows"]
    task_html, log_html, commits_list = d["task_html"], d["log_html"], d["commits_list"]
    active = d["active"]
    state_html = "&#9679; live" if active else "&#9675; idle"
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{state_html} {DONE}/{TOTAL} — team dashboard — {html.escape(os.path.basename(dir_))}</title>
<style>
 :root{{--bg:#f4f5f7;--fg:#1a1d21;--panel:#fff;--border:#dde1e6;--grid:#eef0f2;--muted:#66707c;--acc:#3f8f5f}}
 @media (prefers-color-scheme: dark){{:root{{--bg:#16181c;--fg:#e6e8eb;--panel:#1e2126;--border:#33373d;--grid:#2a2e34;--muted:#9aa4af;--acc:#4caf76}}}}
 body{{font-family:-apple-system,'IBM Plex Sans',system-ui,sans-serif;background:var(--bg);color:var(--fg);margin:0;padding:18px;font-size:14px}}
 .head{{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}}
 h1{{font-size:21px;font-weight:800;margin:0;letter-spacing:-.01em}}
 .muted{{color:var(--muted);font-size:12px}}
 button{{font-family:inherit;font-size:12px;padding:4px 14px;border:1px solid var(--border);border-radius:5px;background:var(--panel);color:var(--fg);cursor:pointer}}
 button:hover{{border-color:var(--acc);color:var(--acc)}} button:active{{transform:translateY(1px)}}
 .meta{{font-family:ui-monospace,monospace;font-size:11px;color:var(--muted);margin:5px 0 14px}}
 .cards{{display:flex;gap:8px;flex-wrap:nowrap;overflow-x:auto;margin-bottom:10px}}
 .card{{flex:1 1 0;min-width:0;background:var(--panel);border:1px solid var(--border);border-radius:6px;padding:8px 12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
 .card .v{{font-size:20px;font-weight:600;font-variant-numeric:tabular-nums}}
 .card .l{{font-size:11px;color:var(--muted);margin-top:2px}}
 .bar{{height:10px;background:var(--grid);border-radius:5px;overflow:hidden;margin:4px 0 12px;display:flex;align-items:center;gap:10px}}
 .bar>div{{height:100%;background:var(--acc);width:{pct}%}}
 .barlab{{font-size:11px;color:var(--muted);white-space:nowrap}}
 .stepper{{display:flex;align-items:center;gap:6px;margin:0 0 14px;flex-wrap:wrap}}
 .step{{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:3px 10px;border-radius:11px;border:1px solid var(--border);color:var(--muted)}}
 .step.cur{{background:var(--acc);border-color:var(--acc);color:#fff}}
 .step.done{{color:var(--acc);border-color:var(--acc)}}
 .sep{{width:14px;height:1px;background:var(--border)}}
 .panel{{background:var(--panel);border:1px solid var(--border);border-radius:6px;padding:10px 12px;margin-bottom:14px;overflow:auto}}
 h2{{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:2px 0 8px}}
 table{{border-collapse:collapse;width:100%}} td,th{{padding:4px 8px;border-bottom:1px solid var(--grid);text-align:left;font-size:12.5px}}
 td.num{{font-family:ui-monospace,monospace;font-variant-numeric:tabular-nums;white-space:nowrap}}
 .live{{color:var(--acc);font-weight:600}}
 .feed{{max-height:300px;overflow-y:auto;font-family:ui-monospace,monospace;font-size:11.5px}}
 .ev{{padding:3px 0;border-bottom:1px solid var(--grid);display:flex;gap:8px;align-items:baseline}}
 .ev .t{{color:var(--muted);white-space:nowrap;min-width:56px;display:inline-block;text-align:right}} .ev .ag{{font-weight:600;min-width:150px;white-space:nowrap}}
 .badge{{font-family:ui-monospace,monospace;font-size:9px;font-weight:700;border:1px solid;border-radius:3px;padding:0 3px;margin-left:4px;vertical-align:1px}}
 .tx{{min-width:0;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer}}
 .tx.exp{{white-space:normal;max-width:none}}
 .pt:hover{{transform:scale(1.6);transform-box:fill-box;transform-origin:center}}
 .row2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}}
 .tch{{font-family:ui-monospace,monospace;color:var(--muted);font-size:11.5px;margin-top:4px}}
 .tw{{font-weight:700;font-size:12px;margin:7px 0 2px;text-transform:uppercase;letter-spacing:.04em;color:var(--fg)}}
 .ttodo{{padding:1px 0 1px 6px;font-size:12.5px;font-weight:600}}
 .tdone{{padding:1px 0 1px 6px;font-size:12.5px;color:var(--muted)}}
 .grid{{stroke:var(--grid)}} .axt{{font-size:10px;fill:var(--muted);font-family:ui-monospace,monospace}}
 .lat{{font-size:11px;font-weight:600;font-family:ui-monospace,monospace}}
 .axis{{stroke:var(--grid);stroke-width:1}} .dia{{fill:var(--acc)}}
 .dia:hover{{fill:#b45309}}
 #tip{{position:absolute;display:none;max-width:360px;background:var(--fg);color:var(--bg);
  padding:6px 10px;border-radius:6px;font-family:ui-monospace,monospace;font-size:11px;
  z-index:9;pointer-events:none;white-space:normal;line-height:1.45;box-shadow:0 2px 8px rgba(0,0,0,.25)}}
</style></head><body>
<div class=head><h1>team dashboard — {html.escape(os.path.basename(dir_))}
 <span class="{("live" if active else "muted")}">{state_html}</span></h1>
<div style="display:flex;gap:8px">
 <button onclick="location.reload()">refresh</button>
 <button id=pause onclick="togglePause()">pause</button>
</div></div>
<div class=meta>project: <code>{html.escape(dir_)}</code> &middot; run start {datetime.datetime.fromtimestamp(START / 1000).strftime("%H:%M:%S")}
 &middot; refreshed {datetime.datetime.now().strftime("%H:%M:%S")} ({REFRESH}s) &middot; dirty files: {DIRTY}
 &middot; last activity {fmt_ms(max(NOW - last_act, 0))} ago &middot; tool errors: {err_str}</div>
<div class=cards>{cards}</div>
<div class=bar><div></div><span class=barlab>{pct}%</span></div>
<div class=stepper><span class=muted style="margin-right:8px">run stage:</span>{stepper}</div>
<div class=panel><h2>Activity — sessions &amp; commits (wall clock)</h2>{activity_chart(SESSIONS, COMMITS_T, d["commits_m"], START, NOW)}</div>
<div class=panel><h2>Agents</h2><table><tr><th>agent</th><th>sessions</th><th>spawned</th><th>model</th><th>in</th><th>out</th><th>last</th><th>state</th></tr>{agent_rows}</table></div>
<div class=row2>
 <div class=panel><h2>Tasks ({DONE}/{TOTAL})</h2>{task_html or "<div class=muted>no openspec tasks found</div>"}</div>
 <div class=panel><h2>Commits</h2><div class=feed>{commits_list}</div></div>
</div>
<div class=panel><h2>Work log</h2><div class=feed>{log_html or "<div class=muted>waiting for output…</div>"}</div></div>
<div id=tip></div>
<div class=meta>generated by scripts/gen-team-dashboard.py &middot; data: opencode session db + git + openspec tasks &middot; no external deps</div>
<script>
const R = {REFRESH} * 1000;
const tip = document.getElementById('tip');
document.addEventListener('mouseover', e => {{
  const t = e.target.closest && e.target.closest('[data-tip]');
  if (t) {{ tip.textContent = t.getAttribute('data-tip'); tip.style.display = 'block'; }}
}});
document.addEventListener('mousemove', e => {{
  if (tip.style.display === 'block') {{
    tip.style.left = Math.min(e.pageX + 14, window.innerWidth - 380) + 'px';
    tip.style.top = (e.pageY + 14) + 'px';
  }}
}});
document.addEventListener('mouseout', e => {{
  if (e.target.closest && e.target.closest('[data-tip]')) tip.style.display = 'none';
}});
// storage guarded: a single SecurityError (cookies blocked etc.) must not
// silently kill auto-refresh — third "quietly looks alive" bug of this class
const sGet = k => {{ try {{ return sessionStorage.getItem(k); }} catch (e) {{ return null; }} }};
const sSet = (k, v) => {{ try {{ sessionStorage.setItem(k, v); }} catch (e) {{}} }};
const sDel = k => {{ try {{ sessionStorage.removeItem(k); }} catch (e) {{}} }};
let tmr = null;
const SIG = {json.dumps(state_sig(d))};
// live page (design dashboard-serve D1): poll /state, repaint only when the
// data signature changed; on fetch failure show a stopped-banner instead of
// quietly looking alive. file:// keeps the legacy reload (file mode: `once`).
async function poll() {{
  try {{
    const r = await fetch('/state');
    if (!r.ok) throw 0;
    const s = await r.json();
    const b = document.getElementById('srvdead');
    if (b) b.remove();
    if (s.sig !== SIG) location.reload();
  }} catch (e) {{
    if (!document.getElementById('srvdead')) {{
      const b = document.createElement('div');
      b.id = 'srvdead';
      b.style.cssText = 'position:fixed;top:0;left:0;right:0;padding:6px;' +
        'background:#b91c1c;color:#fff;font:600 12px ui-monospace,monospace;' +
        'text-align:center;z-index:99';
      b.textContent = 'dashboard server stopped — final snapshot: tmp/team-dashboard.html';
      document.body.appendChild(b);
    }}
  }}
}}
if (location.protocol === 'file:') {{
  if (sGet('dash-pause') !== '1') tmr = setTimeout(() => location.reload(), R);
}} else if (sGet('dash-pause') !== '1') {{
  tmr = setInterval(poll, R);
}}
addEventListener('scroll', () => sSet('dash-y', String(scrollY)), {{passive: true}});
// per-feed scroll: each .feed remembers its own position by index
document.querySelectorAll('.feed').forEach((f, i) => {{
  f.addEventListener('scroll', () => sSet('dash-f' + i, String(f.scrollTop)), {{passive: true}});
  f.scrollTop = +sGet('dash-f' + i) || 0;
}});
scrollTo(0, +sGet('dash-y') || 0);
function togglePause() {{
  const p = sGet('dash-pause') === '1';
  if (p) {{ sDel('dash-pause'); location.reload(); }}
  else {{ sSet('dash-pause', '1');
         if (tmr) {{ clearInterval(tmr); tmr = null; }}  // cancel the pending poll/reload
         document.getElementById('pause').textContent = 'resume'; }}
}}
if (sGet('dash-pause') === '1') {{
  document.getElementById('pause').textContent = 'resume';
}}
</script>
</body></html>"""
    return page


def main(argv):
    if len(argv) >= 4 and argv[1] == "--cfg":
        # shell helper: print one resolved config key for a project dir
        defaults = {"mode": "ask", "open_browser": True, "refresh": 5, "port": 4731}
        key, dir_ = argv[2], os.path.abspath(argv[3])
        print(cfg_chain(dir_, key, defaults.get(key)))
        return 0
    dir_ = os.path.abspath(argv[1])
    d = collect_data(dir_)
    out = os.path.join(dir_, "tmp", "team-dashboard.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    page = render_html(dir_, d)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(page)
    os.replace(tmp, out)  # atomic: readers never see a half-written file
    print(
        f"{datetime.datetime.now().strftime('%H:%M:%S')}: {out} ({len(page)} b, "
        f"{len(d['sessions'])} sessions, {d['done']}/{d['total']} tasks, "
        f"{len(d['commits_t'])} commits)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

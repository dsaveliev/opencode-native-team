#!/usr/bin/env python3
"""gen-team-dashboard.py <project-dir> — one generation pass.

Writes <project>/tmp/team-dashboard.html from:
  - opencode session DB (agents, tokens, activity, work log, errors)
  - git log (commit timeline, dirty files)
  - openspec/changes/*/tasks.md (task progress, ETA estimate)

Run start time: tmp/team-dashboard-state.json (written by team-dashboard.sh),
fallback = earliest session for this directory. Zero dependencies, no CDN.
"""

import datetime
import glob
import html
import json
import os
import re
import sqlite3
import subprocess
import sys

DIR = os.path.abspath(sys.argv[1])
DB = os.path.expanduser("~/.local/share/opencode/opencode.db")
OUT = os.path.join(DIR, "tmp", "team-dashboard.html")
STATE = os.path.join(DIR, "tmp", "team-dashboard-state.json")
NOW = datetime.datetime.now().timestamp() * 1000


def sh(cmd):
    try:
        return subprocess.run(
            cmd, shell=True, cwd=DIR, capture_output=True, text=True
        ).stdout
    except Exception:
        return ""


def fmt_ms(ms):
    m, s = divmod(int(ms / 1000), 60)
    return f"{m}m{s:02d}s" if m < 60 else f"{m // 60}h{m % 60:02d}m"


def fmt_k(n):
    n = n or 0
    return f"{round(n / 1000)}k" if n >= 1000 else str(n)


def run_start(sessions):
    try:
        return json.load(open(STATE))["start_ms"]
    except Exception:
        if sessions:
            return min(s["created"] for s in sessions)
        return NOW


def load_sessions():
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT id, agent, model, time_created, time_updated, "
            "tokens_input, tokens_output, tokens_reasoning "
            "FROM session WHERE directory = ?",
            (DIR,),
        ).fetchall()
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
                "tin": r[5] or 0,
                "tout": (r[6] or 0) + (r[7] or 0),
            }
        )
    return out


def load_parts(session_ids):
    """Text parts (work log) and errored tool parts (diagnostics)."""
    if not session_ids:
        return [], 0
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        q = (
            "SELECT p.session_id, p.time_updated, p.data FROM part p "
            "WHERE p.session_id IN (%s)" % ",".join("?" * len(session_ids))
        )
        rows = con.execute(q, session_ids).fetchall()
        con.close()
    except Exception:
        return [], 0
    texts, errors = [], []
    for sid, t, data in rows:
        try:
            d = json.loads(data)
        except Exception:
            continue
        if d.get("type") == "text":
            txt = (d.get("text") or "").strip()
            if len(txt) > 40:
                agent = next((s["agent"] for s in SESSIONS if s["id"] == sid), "?")
                texts.append((t, agent, txt))
        st = d.get("state") or {}
        if isinstance(st, dict) and st.get("status") == "error":
            errors.append((t, d.get("tool", "?")))
    texts.sort(key=lambda x: -x[0])
    return texts[:40], len(errors)


def load_tasks():
    """Checkbox tasks across all changes; returns (done, total, lines)."""
    done = total = 0
    lines = []
    paths = sorted(glob.glob(os.path.join(DIR, "openspec", "changes", "*", "tasks.md")))
    # openspec archive moves changes to archive/<date>-<id>/ (one level)
    paths += sorted(
        glob.glob(os.path.join(DIR, "openspec", "changes", "archive", "*", "tasks.md"))
    )
    for path in paths:
        change = os.path.basename(os.path.dirname(path))
        cd = ct = 0
        cur = None
        for raw in open(path, encoding="utf-8", errors="ignore"):
            m = re.match(r"\s*- \[([ x])]\s*(.*)", raw)
            if m:
                ct += 1
                if m.group(1) == "x":
                    cd += 1
                    cur = (True, m.group(2)[:90])
            elif raw.startswith("#"):
                lines.append(("h", raw.lstrip("# ").strip()))
            elif re.match(r"^## ", raw) and cur:
                lines.append(("t", cur[1]))
        done, total = done + cd, total + ct
        lines.insert(0, ("c", f"{change}: {cd}/{ct}"))
    return done, total, lines


def load_commits(start_ms, have_state):
    # %x01 = SOH separator: immune to spaces/pipes in messages
    out = sh("git log --reverse --format=%at%x01%s")
    pts, msgs = [], []
    for line in out.split("\n"):
        if "\x01" not in line:
            continue
        ts, msg = line.split("\x01", 1)
        t = int(ts) * 1000
        # without a state file we are viewing a finished/foreign run:
        # keep all commits; with state, only this run's commits
        if have_state and t < start_ms - 60_000:
            continue
        pts.append(max(0.0, (t - start_ms) / 60000))
        msgs.append(msg[:80])
    return pts, msgs


def sparkline(pts, msgs, width=860, height=110):
    if not pts:
        return "<div class=muted>no commits yet</div>"
    xmax = max(pts[-1] + 5, 10)
    ymax = max(len(pts), 5) * 1.15
    x = lambda v: 38 + v / xmax * (width - 50)
    y = lambda v: height - 22 - v / ymax * (height - 36)
    s = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    for g in range(0, len(pts) + 1, max(1, len(pts) // 5)):
        s.append(
            f'<line x1="38" y1="{y(g):.0f}" x2="{width - 12}" y2="{y(g):.0f}" stroke="#eef0f2"/>'
        )
        s.append(
            f'<text x="32" y="{y(g) + 4:.0f}" text-anchor="end" font-size="10" fill="#667">{g}</text>'
        )
    step = max(5, round(xmax / 10))
    for m in range(0, int(xmax) + 1, step):
        s.append(
            f'<line x1="{x(m):.0f}" y1="14" x2="{x(m):.0f}" y2="{height - 22}" stroke="#eef0f2"/>'
        )
        s.append(
            f'<text x="{x(m):.0f}" y="{height - 6}" text-anchor="middle" font-size="10" fill="#667">{m}m</text>'
        )
    path = f"M {x(pts[0]):.0f} {y(1):.0f}" + "".join(
        f" L {x(p):.0f} {y(i + 2):.0f}" for i, p in enumerate(pts)
    )
    s.append(f'<path d="{path}" fill="none" stroke="#3f8f5f" stroke-width="2"/>')
    for i, p in enumerate(pts):
        tip = html.escape(f"#{i + 1} @ {p:.0f}m: {msgs[i] if i < len(msgs) else ''}")
        s.append(
            f'<circle cx="{x(p):.0f}" cy="{y(i + 2):.0f}" r="4" fill="#3f8f5f">'
            f"<title>{tip}</title></circle>"
        )
    s.append("</svg>")
    return "".join(s)


AGENT_COLORS = {
    "orchestrator": "#7c6bb0",
    "coder": "#3f8f5f",
    "tester": "#b45309",
    "reviewer": "#b91c1c",
}


def agent_color(a):
    return AGENT_COLORS.get(a, "#66707c")


SESSIONS = load_sessions()
START = run_start(SESSIONS)
TEXTS, NERR = load_parts([s["id"] for s in SESSIONS])
DONE, TOTAL, TASK_LINES = load_tasks()
HAVE_STATE = os.path.exists(STATE)
COMMITS_T, COMMITS_M = load_commits(START, HAVE_STATE)
ELAPSED = max(NOW - START, 0)
DIRTY = (
    len(sh("git status --porcelain").strip().split("\n"))
    if sh("git status --porcelain").strip()
    else 0
)

agents = {}
for s in SESSIONS:
    a = agents.setdefault(
        s["agent"],
        {
            "n": 0,
            "tin": 0,
            "tout": 0,
            "model": s["model"],
            "last": 0,
            "created": s["created"],
        },
    )
    a["n"] += 1
    a["tin"] += s["tin"]
    a["tout"] += s["tout"]
    a["last"] = max(a["last"], s["updated"])
    a["created"] = min(a["created"], s["created"])

# ETA: mean minutes per completed task so far
eta = "n/a (no tasks closed yet)"
if DONE:
    rate = (ELAPSED / 60000) / DONE
    eta = f"~{round(rate * (TOTAL - DONE))} min ({TOTAL - DONE} left, {round(rate, 1)} min/task)"

tin = sum(s["tin"] for s in SESSIONS)
tout = sum(s["tout"] for s in SESSIONS)
last_act = max((s["updated"] for s in SESSIONS), default=NOW)
active = NOW - last_act < 90_000

cards = f"""
<div class=card><div class=v>{DONE}/{TOTAL}</div><div class=l>tasks done</div></div>
<div class=card><div class=v>{len(COMMITS_T)}</div><div class=l>commits</div></div>
<div class=card><div class=v>{fmt_k(tin)}</div><div class=l>tokens in</div></div>
<div class=card><div class=v>{fmt_k(tout)}</div><div class=l>tokens out</div></div>
<div class=card><div class=v>{len(agents)}</div><div class=l>agents</div></div>
<div class=card><div class=v>{NERR}</div><div class=l>tool errors</div></div>
<div class=card><div class=v>{fmt_ms(ELAPSED)}</div><div class=l>elapsed &middot; ETA {html.escape(eta)}</div></div>
"""

agent_rows = "".join(
    f'<tr><td><b style="color:{agent_color(a)}">{html.escape(a)}</b></td><td class=num>{d["n"]}</td>'
    f"<td>{html.escape(d['model'])}</td><td class=num>{fmt_k(d['tin'])}</td>"
    f"<td class=num>{fmt_k(d['tout'])}</td>"
    f"<td class=num>{fmt_ms(max(NOW - d['last'], 0))} ago</td>"
    f"<td>{'<span class=live>active</span>' if NOW - d['last'] < 90_000 else 'idle'}</td></tr>"
    for a, d in sorted(agents.items())
)

task_html = ""
for kind, text in TASK_LINES[:60]:
    if kind == "h":
        task_html += f"<div class=th>{html.escape(text)}</div>"
    elif kind == "t":
        task_html += f"<div class=tdone>&#10003; {html.escape(text)}</div>"
    elif kind == "c":
        task_html += f"<div class=tch>{html.escape(text)}</div>"

log_html = "".join(
    f"<div class=ev><span class=t>{datetime.datetime.fromtimestamp(t / 1000).strftime('%H:%M:%S')}</span>"
    f'<span class="ag" style="color:{agent_color(a)}">{html.escape(a)}</span> {html.escape(x[:150])}</div>'
    for t, a, x in TEXTS
)

commits_list = (
    "".join(
        f"<div class=ev><span class=t>+{p:.0f}m</span> {html.escape(m)}</div>"
        for p, m in zip(reversed(COMMITS_T), reversed(COMMITS_M))
    )[:40]
    or "<div class=muted>none yet</div>"
)

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<title>team dashboard — {html.escape(os.path.basename(DIR))}</title>
<style>
 body{{font-family:-apple-system,'IBM Plex Sans',system-ui,sans-serif;background:#f4f5f7;color:#1a1d21;margin:0;padding:18px;font-size:14px}}
 .head{{display:flex;justify-content:space-between;align-items:center;gap:12px}}
 h1{{font-size:21px;font-weight:800;margin:0;letter-spacing:-.01em}}
 .muted{{color:#66707c;font-size:12px}}
 button{{font-family:inherit;font-size:12px;padding:4px 14px;border:1px solid #dde1e6;
  border-radius:5px;background:#fff;color:#1a1d21;cursor:pointer}}
 button:hover{{border-color:#3f8f5f;color:#3f8f5f}} button:active{{transform:translateY(1px)}}
 .meta{{font-family:ui-monospace,monospace;font-size:11px;color:#66707c;margin:5px 0 16px}}
 .cards{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}}
 .card{{background:#fff;border:1px solid #dde1e6;border-radius:6px;padding:10px 14px;min-width:110px}}
 .card .v{{font-size:20px;font-weight:600;font-variant-numeric:tabular-nums}}
 .card .l{{font-size:11px;color:#66707c;margin-top:2px}}
 .cols{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
 .panel{{background:#fff;border:1px solid #dde1e6;border-radius:6px;padding:10px 12px;margin-bottom:14px;overflow:auto}}
 h2{{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:#66707c;margin:2px 0 8px}}
 table{{border-collapse:collapse;width:100%}} td,th{{padding:4px 8px;border-bottom:1px solid #eef0f2;text-align:left;font-size:12.5px}}
 td.num{{font-family:ui-monospace,monospace;font-variant-numeric:tabular-nums;white-space:nowrap}}
 .live{{color:#3f8f5f;font-weight:600}}
 .feed{{max-height:300px;overflow-y:auto;font-family:ui-monospace,monospace;font-size:11.5px}}
 .ev{{padding:3px 0;border-bottom:1px solid #f0f2f4;display:flex;gap:8px;align-items:baseline}}
 .ev .t{{color:#66707c;white-space:nowrap}} .ev .ag{{font-weight:600;min-width:86px}}
 .th{{font-weight:600;margin:8px 0 3px}} .tdone{{color:#3f8f5f;padding:1px 0 1px 14px;font-size:12.5px}}
 .tch{{font-family:ui-monospace,monospace;color:#66707c;font-size:11.5px;margin-top:4px}}
 .bar{{height:10px;background:#eef0f2;border-radius:5px;overflow:hidden;margin:6px 0 10px}}
 .bar>div{{height:100%;background:#3f8f5f}}
</style></head><body>
<div class=head><h1>team dashboard — {html.escape(os.path.basename(DIR))}
 {"<span class=live>● live</span>" if active else "<span class=muted>○ idle</span>"}</h1>
<button onclick="location.reload()">refresh</button></div>
<div class=meta>project: <code>{html.escape(DIR)}</code> &middot; run start {datetime.datetime.fromtimestamp(START / 1000).strftime("%H:%M:%S")}
 &middot; refreshed {datetime.datetime.now().strftime("%H:%M:%S")} (5s) &middot; dirty files: {DIRTY}
 &middot; last activity {fmt_ms(max(NOW - last_act, 0))} ago</div>
<div class=cards>{cards}</div>
<div class=bar><div style="width:{round(100 * DONE / TOTAL) if TOTAL else 0}%"></div></div>
<div class=panel><h2>Commit timeline</h2>{sparkline(COMMITS_T, COMMITS_M)}</div>
<div class=cols>
 <div class=panel><h2>Agents</h2><table><tr><th>agent</th><th>sessions</th><th>model</th><th>in</th><th>out</th><th>last</th><th>state</th></tr>{agent_rows}</table></div>
 <div class=panel><h2>Tasks ({DONE}/{TOTAL})</h2>{task_html or "<div class=muted>no openspec tasks found</div>"}</div>
 <div class=panel><h2>Work log</h2><div class=feed>{log_html or "<div class=muted>waiting for output…</div>"}</div></div>
 <div class=panel><h2>Commits</h2><div class=feed>{commits_list}</div></div>
</div>
<div class=meta>generated by scripts/gen-team-dashboard.py &middot; data: opencode session db + git + openspec tasks &middot; no external deps</div>
</body></html>"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(page)
print(
    f"{datetime.datetime.now().strftime('%H:%M:%S')}: {OUT} ({len(page)} b, "
    f"{len(SESSIONS)} sessions, {DONE}/{TOTAL} tasks, {len(COMMITS_T)} commits)"
)

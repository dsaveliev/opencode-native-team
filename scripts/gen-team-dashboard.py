#!/usr/bin/env python3
"""gen-team-dashboard.py <project-dir> — one generation pass (v2).

Writes <project>/tmp/team-dashboard.html atomically from:
  - opencode session DB (agents, tokens, activity, work log, tool errors,
    subagent spawns via parent_id)
  - git log (commit timeline with a "now" marker, dirty files)
  - openspec tasks (run-window aware: archived changes count only if
    archived on/after the run start date)
  - .opencode/team-dashboard.json (refresh seconds)

Exit 0 even on partial data (the loop must keep running). Zero deps, no CDN.
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
import time

DIR = os.path.abspath(sys.argv[1])
DB = os.path.expanduser("~/.local/share/opencode/opencode.db")
CFG = os.path.join(DIR, ".opencode", "team-dashboard.json")
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


def cfg_get(key, default):
    try:
        return json.load(open(CFG, encoding="utf-8")).get(key, default)
    except Exception:
        return default


REFRESH = max(2, int(cfg_get("refresh", 5) or 5))


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


def load_sessions(start_ms=None):
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        q = (
            "SELECT id, agent, model, time_created, time_updated, parent_id, "
            "tokens_input, tokens_output, tokens_reasoning "
            "FROM session WHERE directory = ?"
        )
        args = [DIR]
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


def load_parts(session_ids):
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
                agent = next((s["agent"] for s in SESSIONS if s["id"] == sid), "?")
                texts.append((t, agent, txt))
        st = d.get("state") or {}
        if isinstance(st, dict) and st.get("status") == "error":
            tool = d.get("tool", "?")
            err_tools[tool] = err_tools.get(tool, 0) + 1
    texts.sort(key=lambda x: -x[0])
    return texts[:40], err_tools


def load_tasks(start_ms=None):
    """Checkbox tasks within the run window.

    Active changes always count. Archived changes count only when their
    archive date (dir name prefix) is on/after the run start date; without
    a run state (archive view) everything counts."""

    def entries(path):
        """Items: ("h", title) sections and ("t", done, depth, title) tasks;
        depth derived from bullet indentation."""
        out = []
        section = ""
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
        glob.glob(os.path.join(DIR, "openspec", "changes", "*", "tasks.md"))
    ):
        name = os.path.basename(os.path.dirname(path))
        changes.append((name, entries(path)))
    for path in sorted(
        glob.glob(os.path.join(DIR, "openspec", "changes", "archive", "*", "tasks.md"))
    ):
        name = os.path.basename(os.path.dirname(path))
        dm = re.match(r"(\d{4}-\d{2}-\d{2})-", name)
        if start_date and dm and datetime.date.fromisoformat(dm.group(1)) < start_date:
            continue  # archived before this run — another run's history
        changes.append(("archive: " + name, entries(path)))

    done = sum(1 for _, es in changes
               for it in es if it[0] == "t" and it[1])
    total = sum(1 for _, es in changes for it in es if it[0] == "t")
    return done, total, changes


def load_commits(start_ms, have_state):
    # %x01 = SOH separator: immune to spaces/pipes in messages
    out = sh("git log --reverse --format=%at%x01%s")
    pts, msgs = [], []
    for line in out.split("\n"):
        if "\x01" not in line:
            continue
        ts, msg = line.split("\x01", 1)
        t = int(ts) * 1000
        if have_state and t < start_ms - 60_000:
            continue
        pts.append(max(0.0, (t - start_ms) / 60000))
        msgs.append(msg[:80])
    return pts, msgs


def sparkline(pts, msgs, now_min):
    if not pts:
        return "<div class=muted>no commits yet</div>"
    width, height = 860, 120
    xmax = max(pts[-1], now_min) + 5
    ymax = max(len(pts), 5) * 1.15

    def x(v):
        return 38 + v / xmax * (width - 50)

    def y(v):
        return height - 24 - v / ymax * (height - 38)

    s = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto">'
    ]
    for g in range(0, len(pts) + 1, max(1, len(pts) // 5)):
        s.append(
            f'<line x1="38" y1="{y(g):.0f}" x2="{width - 12}" y2="{y(g):.0f}" class="grid"/>'
        )
        s.append(
            f'<text x="32" y="{y(g) + 4:.0f}" text-anchor="end" class="axt">{g}</text>'
        )
    step = max(5, round(xmax / 10))
    for m in range(0, int(xmax) + 1, step):
        s.append(
            f'<line x1="{x(m):.0f}" y1="14" x2="{x(m):.0f}" y2="{height - 24}" class="grid"/>'
        )
        s.append(
            f'<text x="{x(m):.0f}" y="{height - 8}" text-anchor="middle" class="axt">{m}m</text>'
        )
    path = f"M {x(pts[0]):.0f} {y(1):.0f}" + "".join(
        f" L {x(p):.0f} {y(i + 1):.0f}" for i, p in enumerate(pts[1:], 1)
    )
    s.append(f'<path d="{path}" fill="none" class="line"/>')
    for i, p in enumerate(pts):
        tip = html.escape(f"#{i + 1} @ {p:.0f}m: {msgs[i] if i < len(msgs) else ''}")
        s.append(
            f'<circle cx="{x(p):.0f}" cy="{y(i + 1):.0f}" r="4" class="pt"><title>{tip}</title></circle>'
        )
    if now_min is not None and 0 <= now_min <= xmax:
        nx = x(now_min)
        s.append(
            f'<line x1="{nx:.0f}" y1="10" x2="{nx:.0f}" y2="{height - 24}" class="now"/>'
        )
        s.append(
            f'<text x="{nx:.0f}" y="10" text-anchor="middle" class="nowt">now</text>'
        )
    s.append("</svg>")
    return "".join(s)


CODE_EXT = re.compile(r"\.(go|py|ts|tsx|js|jsx|rs|java|rb|php|c|cc|cpp|h|hpp|sh)$")


def project_loc():
    """Lines of code over tracked files (code extensions only)."""
    files = [
        f
        for f in sh("git ls-files").split("\n")
        if f and CODE_EXT.search(f) and not f.startswith("vendor/")
    ]
    if not files:
        return 0
    out = sh("wc -l " + " ".join(f"'{f}'" for f in files[:500]))
    total = 0
    for line in out.split("\n"):
        m = re.match(r"\s*(\d+)", line)
        if m:
            total += int(m.group(1))
    return total


COV_CACHE = os.path.join(DIR, "tmp", "team-dashboard-coverage.json")


def test_coverage():
    """Mean per-package go test coverage, cached with a TTL (tests are too
    heavy for every tick). 'n/a' when Go is absent or the TTL is 0."""
    ttl = int(cfg_get("coverage_ttl", 60) or 0)
    if ttl <= 0:
        return None
    try:
        c = json.load(open(COV_CACHE, encoding="utf-8"))
        if time.time() * 1000 - c["ts"] < ttl * 1000:
            return c["pct"]
    except Exception:
        pass
    if not os.path.exists(os.path.join(DIR, "go.mod")):
        return None
    try:
        import subprocess as sp

        r = sp.run(
            ["go", "test", "-count=1", "-cover", "./..."],
            cwd=DIR,
            capture_output=True,
            text=True,
            timeout=45,
        )
        pcts = [float(m) for m in re.findall(r"coverage:\s+(\d+(?:\.\d+)?)%", r.stdout)]
        pct = round(sum(pcts) / len(pcts), 1) if pcts else None
        if pct is not None:
            json.dump(
                {"pct": pct, "ts": int(time.time() * 1000)},
                open(COV_CACHE, "w", encoding="utf-8"),
            )
        return pct
    except Exception:
        return None


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


# ---- data assembly ----
HAVE_STATE = os.path.exists(STATE)
START = None
if HAVE_STATE:
    try:
        START = json.load(open(STATE))["start_ms"]
    except Exception:
        START = None
if START is None:
    _all = load_sessions()
    START = min((s["created"] for s in _all), default=NOW)
    SESSIONS = _all
else:
    SESSIONS = load_sessions(START)
TEXTS, ERR_TOOLS = load_parts([s["id"] for s in SESSIONS])
DONE, TOTAL, TASK_CHANGES = load_tasks(START if HAVE_STATE else None)
COMMITS_T, COMMITS_M = load_commits(START, HAVE_STATE)
ELAPSED = max(NOW - START, 0)
DIRTY = sh("git status --porcelain").strip().count("\n") + (
    1 if sh("git status --porcelain").strip() else 0
)
NOW_MIN = (NOW - START) / 60000

agents = {}
for s in SESSIONS:
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

PROJ_LOC = project_loc()
COVERAGE = test_coverage()
SPAWNS = sum(d["spawns"] for a, d in agents.items() if a != "orchestrator")
tin = sum(s["tin"] for s in SESSIONS)
tout = sum(s["tout"] for s in SESSIONS)
last_act = max((s["updated"] for s in SESSIONS), default=NOW)
active = NOW - last_act < 180_000
NERR = sum(ERR_TOOLS.values())

# stage stepper: last orchestrator text → keywords; fallback: last active agent
STAGES = ["plan", "code", "test", "review", "done"]
stage = None
orch_texts = [x for _t, a, x in TEXTS if a == "orchestrator"]
last_txt = orch_texts[0].lower() if orch_texts else ""
for kw, st in [
    ("archive|final gates|closing", "done"),
    ("reviewer|review", "review"),
    ("tester|tests green", "test"),
    ("coder|implement|delegating", "code"),
    ("openspec|proposal|design|doubt|planning|decomposition", "plan"),
]:
    if re.search(kw, last_txt):
        stage = st
        break
if stage is None:
    by_agent = {a: d["last"] for a, d in agents.items()}
    last_agent = max(by_agent, key=by_agent.get) if by_agent else None
    stage = {
        "planner": "plan",
        "coder": "code",
        "tester": "test",
        "reviewer": "review",
    }.get(last_agent, "plan")
stage_idx = STAGES.index(stage)
steps = []
for i, n in enumerate(STAGES):
    cls = "step"
    if i < stage_idx:
        cls += " done"
    if i == stage_idx:
        cls += " cur"
    steps.append(f'<span class="{cls}">{n}</span>')
    if i < len(STAGES) - 1:
        steps.append("<span class=sep></span>")
stepper = "".join(steps)

eta = "no ETA yet"
if DONE:
    rate = (ELAPSED / 60000) / DONE
    eta = f"~{round(rate * (TOTAL - DONE))} min left"

err_str = ", ".join(f"{t}&times;{n}" for t, n in sorted(ERR_TOOLS.items())) or "none"

cards = f"""
<div class=card><div class=v>{DONE}/{TOTAL}</div><div class=l>tasks done</div></div>
<div class=card><div class=v>{len(COMMITS_T)}</div><div class=l>commits</div></div>
<div class=card><div class=v>{fmt_k(tin)}</div><div class=l>tokens in</div></div>
<div class=card><div class=v>{fmt_k(tout)}</div><div class=l>tokens out</div></div>
<div class=card><div class=v>{SPAWNS}</div><div class=l>subagent spawns</div></div>
<div class=card><div class=v>{fmt_k(PROJ_LOC)}</div><div class=l>loc (tracked)</div></div>
<div class=card><div class=v>{COVERAGE if COVERAGE is not None else "&mdash;"}</div><div class=l>test coverage %</div></div>
<div class=card><div class=v>{NERR}</div><div class=l>tool errors</div></div>
<div class=card><div class=v>{fmt_ms(ELAPSED)}</div><div class=l>elapsed &middot; {html.escape(eta)}</div></div>
"""

agent_rows = "".join(
    f'<tr><td><b style="color:{agent_color(a)}">{html.escape(a)}</b> {agent_badge(a)}</td>'
    f"<td class=num>{d['n']}</td><td class=num>{d['spawns']}</td>"
    f"<td>{html.escape(d['model'])}</td><td class=num>{fmt_k(d['tin'])}</td>"
    f"<td class=num>{fmt_k(d['tout'])}</td>"
    f"<td class=num>{fmt_ms(max(NOW - d['last'], 0))} ago</td>"
    f"<td>{'<span class=live>active</span>' if NOW - d['last'] < 180_000 else 'idle'}</td></tr>"
    for a, d in sorted(agents.items())
)

pct = round(100 * DONE / TOTAL) if TOTAL else 0
task_html = ""
for name, es in TASK_CHANGES:
    d_n = sum(1 for it in es if it[0] == "t" and it[1])
    t_n = sum(1 for it in es if it[0] == "t")
    task_html += f"<div class=tch>{html.escape(name)} — {d_n}/{t_n}</div>"
    for it in es:
        if it[0] == "h":
            task_html += f'<div class=tw>{html.escape(it[1])}</div>'
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
    f" {html.escape(x[:150])}</div>"
    for t, a, x in TEXTS
)

commit_entries = [
    f"<div class=ev><span class=t>+{p:.0f}m</span> {html.escape(m)}</div>"
    for p, m in zip(reversed(COMMITS_T), reversed(COMMITS_M))
]
commits_list = "".join(commit_entries[:40]) or "<div class=muted>none yet</div>"

state_html = "&#9679; live" if active else "&#9675; idle"
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{state_html} {DONE}/{TOTAL} — team dashboard — {html.escape(os.path.basename(DIR))}</title>
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
 .card{{flex:0 0 auto;background:var(--panel);border:1px solid var(--border);border-radius:6px;padding:8px 12px;white-space:nowrap}}
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
 .cols{{display:grid;grid-template-columns:1fr;gap:14px}}
 .panel{{background:var(--panel);border:1px solid var(--border);border-radius:6px;padding:10px 12px;margin-bottom:14px;overflow:auto}}
 h2{{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:2px 0 8px}}
 table{{border-collapse:collapse;width:100%}} td,th{{padding:4px 8px;border-bottom:1px solid var(--grid);text-align:left;font-size:12.5px}}
 td.num{{font-family:ui-monospace,monospace;font-variant-numeric:tabular-nums;white-space:nowrap}}
 .live{{color:var(--acc);font-weight:600}}
 .feed{{max-height:300px;overflow-y:auto;font-family:ui-monospace,monospace;font-size:11.5px}}
 .ev{{padding:3px 0;border-bottom:1px solid var(--grid);display:flex;gap:8px;align-items:baseline}}
 .ev .t{{color:var(--muted);white-space:nowrap;min-width:56px;display:inline-block;text-align:right}} .ev .ag{{font-weight:600;min-width:150px;white-space:nowrap}}
 .badge{{font-family:ui-monospace,monospace;font-size:9px;font-weight:700;border:1px solid;border-radius:3px;padding:0 3px;margin-left:4px;vertical-align:1px}}
 .tch{{font-family:ui-monospace,monospace;color:var(--muted);font-size:11.5px;margin-top:4px}}
 .tw{{font-weight:700;font-size:12px;margin:7px 0 2px;text-transform:uppercase;letter-spacing:.04em;color:var(--fg)}}
 .ttodo{{padding:1px 0 1px 6px;font-size:12.5px;font-weight:600}}
 .tdone{{padding:1px 0 1px 6px;font-size:12.5px;color:var(--muted)}}
 .grid{{stroke:var(--grid)}} .axt{{font-size:10px;fill:var(--muted);font-family:ui-monospace,monospace}}
 .line{{stroke:var(--acc);stroke-width:2;fill:none}} .pt{{fill:var(--acc)}}
 .now{{stroke:#b45309;stroke-width:1.5;stroke-dasharray:4,3}} .nowt{{font-size:10px;fill:#b45309;font-family:ui-monospace,monospace}}
</style></head><body>
<div class=head><h1>team dashboard — {html.escape(os.path.basename(DIR))}
 <span class="{("live" if active else "muted")}">{state_html}</span></h1>
<div style="display:flex;gap:8px">
 <button onclick="location.reload()">refresh</button>
 <button id=pause onclick="togglePause()">pause</button>
</div></div>
<div class=meta>project: <code>{html.escape(DIR)}</code> &middot; run start {datetime.datetime.fromtimestamp(START / 1000).strftime("%H:%M:%S")}
 &middot; refreshed {datetime.datetime.now().strftime("%H:%M:%S")} ({REFRESH}s) &middot; dirty files: {DIRTY}
 &middot; last activity {fmt_ms(max(NOW - last_act, 0))} ago &middot; tool errors: {err_str}</div>
<div class=cards>{cards}</div>
<div class=bar><div></div><span class=barlab>{pct}%</span></div>
<div class=stepper>{stepper}</div>
<div class=panel><h2>Commit timeline</h2>{sparkline(COMMITS_T, COMMITS_M, NOW_MIN)}</div>
<div class=cols>
 <div class=panel><h2>Agents</h2><table><tr><th>agent</th><th>sessions</th><th>spawns</th><th>model</th><th>in</th><th>out</th><th>last</th><th>state</th></tr>{agent_rows}</table></div>
 <div class=panel><h2>Tasks ({DONE}/{TOTAL})</h2>{task_html or "<div class=muted>no openspec tasks found</div>"}</div>
 <div class=panel><h2>Work log</h2><div class=feed>{log_html or "<div class=muted>waiting for output…</div>"}</div></div>
 <div class=panel><h2>Commits</h2><div class=feed>{commits_list}</div></div>
</div>
<div class=meta>generated by scripts/gen-team-dashboard.py &middot; data: opencode session db + git + openspec tasks &middot; no external deps</div>
<script>
const R = {REFRESH} * 1000;
if (sessionStorage.getItem('dash-pause') !== '1') {{
  setTimeout(() => location.reload(), R);
}}
addEventListener('scroll', () => sessionStorage.setItem('dash-y', scrollY), {{passive: true}});
scrollTo(0, +sessionStorage.getItem('dash-y') || 0);
function togglePause() {{
  const p = sessionStorage.getItem('dash-pause') === '1';
  if (p) {{ sessionStorage.removeItem('dash-pause'); location.reload(); }}
  else {{ sessionStorage.setItem('dash-pause', '1');
         const b = document.getElementById('pause'); b.textContent = 'resume'; }}
}}
if (sessionStorage.getItem('dash-pause') === '1') {{
  document.getElementById('pause').textContent = 'resume';
}}
</script>
</body></html>"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
tmp = OUT + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(page)
os.replace(tmp, OUT)  # atomic: readers never see a half-written file
print(
    f"{datetime.datetime.now().strftime('%H:%M:%S')}: {OUT} ({len(page)} b, "
    f"{len(SESSIONS)} sessions, {DONE}/{TOTAL} tasks, {len(COMMITS_T)} commits)"
)

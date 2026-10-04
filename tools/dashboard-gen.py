#!/usr/bin/env python3
"""dashboard-gen.py — живая панель native×4: таблица, лента событий, график гонки.
Каждый тик: диф транскриптов -> события (state), git-таймлайны, sqlite-токены."""

import subprocess, re, html, os, json, datetime, glob

R = os.path.expanduser("~/.tmp/opencode/bakeoff")
L = os.path.join(R, "dashboard.html")
STATE = os.path.join(R, "dashboard-state.json")
ARMS = [
    ("native", "barebone (v1)", "#9aa4b2"),
    ("native-skills", "skills", "#c2a3a3"),
    ("native-openspec", "openspec", "#7c6bb0"),
    ("native-combined", "combined v4", "#b45309"),
]
MAX_EVENTS = 250


def sh(cmd, cwd=None):
    try:
        return subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd or R
        ).stdout.strip()
    except Exception:
        return ""


def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {"offsets": {}, "events": []}


def save_state(s):
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False)


def meaningful(line):
    l = line.strip()
    if not l or len(l) < 4:
        return None
    if re.match(r"^(\[opencode|WALL_SECONDS|</|$|\(|dup\b)", l):
        return None
    if re.match(r"^(\→|⚙|•|✓|✗|\$|\*\*|#|—|-{2,})", l):
        return l[:160]
    if re.search(
        r"(Skill|Делег|Задач|Task|Фаза|коммит|Commit|чендж|change|план|PLAN|вердикт|review|Judge|EXIT|заверш)",
        l,
        re.I,
    ):
        return l[:160]
    return None


def harvest_events(state):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    ev = state.get("events", [])
    offs = state.get("offsets", {})
    for name, _, _ in ARMS:
        if name == "native":
            continue
        tr = os.path.join(R, "results", f"{name}-live.txt")
        if not os.path.exists(tr):
            continue
        raw = open(tr, "rb").read()
        off = offs.get(name, max(0, len(raw) - 4000))  # первый тик: сеем хвост
        offs[name] = len(raw)
        if off > len(raw):
            off = 0
        chunk = raw[off:].decode("utf-8", "ignore")
        txt = re.sub(r"\x1b\[[0-9;]*m", "", chunk)
        fresh = [m for m in (meaningful(l) for l in txt.split("\n")) if m]
        for f in fresh[-6:]:
            ev.append({"t": now, "arm": name, "text": f})
    state["events"] = ev[-MAX_EVENTS:]
    state["offsets"] = offs


def commits_timeline(name):
    d = os.path.join(R, "runs", name)
    out = sh("git log --reverse --date=iso-strict", d)
    ts, msgs, subj = [], [], []
    for l in out.split("\n"):
        if l.startswith("Date:"):
            ts.append(
                datetime.datetime.fromisoformat(
                    l.replace("Date:", "").strip().replace("Z", "+00:00")
                ).timestamp()
            )
        if l.startswith("    "):
            subj.append(l.strip())
    if not ts:
        return [], None
    t0 = ts[0]
    pts = [
        {
            "m": round((t - t0) / 60, 1),
            "msg": (subj[i] if i < len(subj) else "")[:70],
            "task": bool(re.search(r"task|задач", subj[i], re.I))
            if i < len(subj)
            else False,
        }
        for i, t in enumerate(ts)
    ]
    return pts, t0


def arm_data(name):
    d = {"dir": os.path.join(R, "runs", name)}
    d["alive"] = sh(f"pgrep -f 'run-fw.sh {name}' | head -1") != ""
    log = os.path.join(R, "status", f"{name}.log")
    elapsed = "—"
    if os.path.exists(log):
        tail = (
            open(log, encoding="utf-8", errors="ignore").read().strip().split("\n")[-1]
        )
        m = re.search(r"\](\d+m\d+s)", tail)
        if m:
            elapsed = m.group(1)
    d["elapsed"] = elapsed
    res = os.path.join(R, "results", f"{name}.result")
    if not d["alive"] and os.path.exists(res):
        last = open(res).read().strip().split("\n")[-1]
        mm = re.search(r"WALL_SECONDS=(\d+) EXIT=(\d+)", last)
        if mm:
            d["elapsed"] = f"финиш: {int(mm.group(1)) // 60} мин (exit {mm.group(2)})"
    d["commits"] = sh("git rev-list --count HEAD", d["dir"]) or "0"
    d["last_commit"] = sh("git log -1 --format=%s", d["dir"])[:70]
    d["dirty"] = sh("git status --porcelain | wc -l | tr -d ' '", d["dir"]) or "0"
    d["tasks"] = "—"
    tg = glob.glob(os.path.join(d["dir"], "openspec", "changes", "*", "tasks.md"))
    if tg:
        t = open(tg[0], encoding="utf-8", errors="ignore").read()
        done = len(re.findall(r"- \[[xX]\]", t))
        todo = len(re.findall(r"- \[ \]", t))
        d["tasks"] = f"{done}/{done + todo}"
    tr = os.path.join(R, "results", f"{name}-live.txt")
    txt = (
        open(tr, encoding="utf-8", errors="ignore").read() if os.path.exists(tr) else ""
    )
    txt = re.sub(r"\x1b\[[0-9;]*m", "", txt)
    lines = [l.strip() for l in txt.split("\n") if l.strip()]
    d["lastline"] = lines[-1][:130] if lines else ""
    d["skills"] = len(re.findall(r"→ Skill", txt))
    jr = os.path.join(R, "results", name, "judge-report.md")
    if os.path.exists(jr):
        j = open(jr, encoding="utf-8", errors="ignore").read()
        d["judge"] = (
            f"{len(re.findall(r'- PASS:', j))}P/{len(re.findall(r'- FAIL:', j))}F"
        )
    else:
        d["judge"] = "—"
    return d


def tokens(name):
    try:
        import sqlite3

        db = os.path.expanduser("~/.local/share/opencode/opencode.db")
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        exact = os.path.join(R, "runs", name)
        s, ti, to_, tr = con.execute(
            "SELECT count(*), sum(tokens_input), sum(tokens_output), sum(tokens_reasoning) "
            "FROM session WHERE directory = ?",
            (exact,),
        ).fetchone()
        con.close()
        return (
            f"{s or 0} сесс<br>{round((ti or 0) / 1000)}k in · "
            f"{round(((to_ or 0) + (tr or 0)) / 1000)}k out"
        )
    except Exception:
        return "—"


def go_loc(name):
    d = os.path.join(R, "runs", name)

    def cnt(pattern):
        out = sh(
            f"find . -name '{pattern}' -not -path './vendor/*' | xargs wc -l 2>/dev/null | tail -1",
            d,
        )
        m = re.search(r"(\d+)", out or "")
        return int(m.group(1)) if m else 0

    total = cnt("*.go")
    tests = cnt("*_test.go")
    share = f" · {round(tests / total * 100)}% тесты" if total else ""
    return f"{total:,}".replace(",", " ") + share if total else "—"


state = load_state()
harvest_events(state)
save_state(state)

meta = {}
for name, title, color in ARMS:
    meta[name] = {"title": title, "color": color, **arm_data(name)}
    meta[name]["tokens"] = tokens(name)
    meta[name]["loc"] = go_loc(name)
    pts, _ = commits_timeline(name)
    meta[name]["commits_tl"] = pts

page_data = {"arms": meta, "events": state["events"][-60:]}
pd_json = json.dumps(page_data, ensure_ascii=False).replace("</", "<\\/")

now = datetime.datetime.now().strftime("%H:%M:%S")
page = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<title>Native×4 — живая панель</title>
<style>
 body{{font-family:-apple-system,'IBM Plex Sans',system-ui,sans-serif;background:#f4f5f7;color:#1a1d21;margin:0;padding:20px;font-size:14px}}
 h1{{font-size:20px;margin:0 0 4px}} h2{{font-size:15px;margin:22px 0 8px}}
 .bar{{display:flex;align-items:center;gap:12px;margin-bottom:14px}}
 .meta{{font-family:ui-monospace,monospace;font-size:11px;color:#66707c}}
 button{{font-family:inherit;font-size:12px;padding:4px 12px;border:1px solid #dde1e6;border-radius:4px;background:#fff;color:#1a1d21;cursor:pointer}}
 button:hover{{border-color:#b45309;color:#b45309}} button:active{{transform:translateY(1px)}}
 .chip{{display:inline-flex;align-items:center;gap:6px;font-size:12px;padding:3px 10px;border:1px solid #dde1e6;border-radius:12px;background:#fff;cursor:pointer;margin-right:6px;user-select:none}}
 .chip.off{{opacity:.35}} .dot{{width:9px;height:9px;border-radius:50%;display:inline-block}}
 table{{border-collapse:collapse;width:100%;background:#fff;border:1px solid #dde1e6}}
 th{{text-align:left;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#66707c;border-bottom:2px solid #1a1d21;padding:8px 10px}}
 td{{border-bottom:1px solid #eef0f2;padding:6px 10px;vertical-align:top}}
 td.num{{font-family:ui-monospace,monospace;font-variant-numeric:tabular-nums;white-space:nowrap}}
 td.last{{font-family:ui-monospace,monospace;font-size:11px;color:#66707c;padding:2px 10px 8px 14px;word-break:break-all}}
 .muted{{color:#66707c;font-size:12px}}
 #chart{{background:#fff;border:1px solid #dde1e6;padding:10px;margin-bottom:6px}}
 .feed{{background:#fff;border:1px solid #dde1e6;max-height:420px;overflow-y:auto;font-family:ui-monospace,monospace;font-size:11.5px}}
 .ev{{padding:4px 10px;border-bottom:1px solid #f0f2f4;display:flex;gap:8px;align-items:baseline}}
 .ev .t{{color:#66707c;white-space:nowrap}}
 .legend{{margin-top:8px;font-size:12px;color:#66707c}}
</style></head><body>
<h1>Native×5: barebone · skills · openspec · v4 · v5</h1>
<div class="bar">
  <button onclick="location.reload()">Обновить сейчас</button>
  <span class="meta">обновлено {now} · авто-refresh 5 с · git+sqlite живые</span>
</div>

<h2>Гонка к результату: накопленные коммиты от старта (точки — коммиты, кружки — task-коммиты)</h2>
<div id="chips"></div>
<div id="chart"></div>
<div class="legend">Наведи на точку — сообщение коммита и минута. Клик по чипу — скрыть/показать рукав.
Пунктирная серая — v1 barebone (эталон: 17 коммитов за 43 мин).</div>

<h2>Сводка</h2>
<table>
<tr><th>Рукав</th><th>коммиты</th><th>грязных</th><th>tasks [x]</th><th>скиллов</th><th>LOC (тесты)</th><th>токены</th><th>последний коммит</th><th>судья</th></tr>
<tr id="rows"></tr>
</table>

<h2>Лента событий (последние 60, новые сверху) <span id="fchips" style="margin-left:10px"></span></h2>
<div class="feed" id="feed"></div>

<script id="pd" type="application/json">{pd_json}</script>
<script>
const PD = JSON.parse(document.getElementById('pd').textContent);
const ARM_ORDER = ['native','native-skills','native-openspec','native-combined'];
// состояние в hash — переживает авто-refresh: #f=<feedFilter>&h=<скрытые через запятую>
const readHash = () => {{
  const h = new URLSearchParams(location.hash.slice(1));
  return {{ f: h.get('f') || 'all', h: new Set((h.get('h') || '').split(',').filter(Boolean)) }};
}};
const writeHash = () => history.replaceState(null, '', '#f=' + feedFilter + '&h=' + [...hidden].join(','));
let {{ f: hf, h: hh }} = readHash();
const hidden = hh;
let feedFilter = hf;

// ---- таблица ----
const rows = ARM_ORDER.map(n => {{
  const a = PD.arms[n];
  const st = a.alive ? '🔄' : (String(a.elapsed).includes('финиш') ? '✅' : '⏸');
  return `<tr><td style="border-left:4px solid ${{a.color}};padding:6px 10px;"><b>${{a.title}}</b><br><span class="muted">${{st}} ${{a.elapsed}}</span></td>
  <td class="num">${{a.commits}}</td><td class="num">${{a.dirty}}</td><td class="num">${{a.tasks}}</td>
  <td class="num">${{a.skills}}</td><td class="num">${{a.loc}}</td><td class="num" style="white-space:normal;min-width:110px;">${{a.tokens}}</td><td>${{a.last_commit}}</td><td><b>${{a.judge}}</b></td></tr>
  <tr><td colspan="8" class="last">↳ ${{a.lastline}}</td></tr>`;
}}).join('');
document.getElementById('rows').outerHTML = rows;

// ---- лента с фильтрами по рукавам (feedFilter инициализирован из hash выше) ----
const renderFeed = () => {{
  const list = PD.events.slice().reverse()
    .filter(e => feedFilter === 'all' || e.arm === feedFilter);
  document.getElementById('feed').innerHTML = list.map(e => {{
    const c = (PD.arms[e.arm] || {{}}).color || '#667';
    return `<div class="ev"><span class="t">${{e.t}}</span><span class="dot" style="background:${{c}}"></span><span>${{e.text.replace(/</g,'&lt;')}}</span></div>`;
  }}).join('') || '<div class="ev muted">нет событий по фильтру…</div>';
}};
const FEED_ARMS = ARM_ORDER.filter(n => n !== 'native');
document.getElementById('fchips').innerHTML =
  `<span class="chip" data-f="all"><b>Все</b></span>` +
  FEED_ARMS.map(n => `<span class="chip" data-f="${{n}}"><span class="dot" style="background:${{PD.arms[n].color}}"></span>${{PD.arms[n].title}} <span class="muted">${{PD.events.filter(e => e.arm === n).length}}</span></span>`).join('');
const setActiveChips = () => document.querySelectorAll('[data-f]').forEach(ch =>
  ch.classList.toggle('off', ch.dataset.f !== feedFilter));
document.querySelectorAll('[data-f]').forEach(ch => ch.addEventListener('click', () => {{
  feedFilter = ch.dataset.f; setActiveChips(); renderFeed(); writeHash();
}}));
setActiveChips();
renderFeed();

// ---- график гонки ----
function renderChart() {{
  const W = 900, H = 300, X0 = 46, X1 = W - 16, Y0 = 24, Y1 = H - 34;
  let xMax = 45, yMax = 17;
  for (const n of ARM_ORDER) {{
    const a = PD.arms[n];
    const tl = a.commits_tl || [];
    if (!hidden.has(n) && tl.length) {{
      xMax = Math.max(xMax, tl[tl.length-1].m + 5);
      yMax = Math.max(yMax, tl.length);
    }}
  }}
  yMax = Math.ceil(yMax * 1.1);
  const x = v => X0 + v / xMax * (X1 - X0), y = v => Y1 - v / yMax * (Y1 - Y0);
  let s = `<svg width="${{W}}" height="${{H}}" viewBox="0 0 ${{W}} ${{H}}" xmlns="http://www.w3.org/2000/svg">`;
  for (let g = 0; g <= yMax; g += Math.max(1, Math.round(yMax / 6))) {{
    s += `<line x1="${{X0}}" y1="${{y(g)}}" x2="${{X1}}" y2="${{y(g)}}.0" stroke="#eef0f2"/>`;
    s += `<text x="${{X0-6}}" y="${{y(g)+4}}" text-anchor="end" font-size="10" fill="#66707c" font-family="monospace">${{g}}</text>`;
  }}
  for (let m = 0; m <= xMax; m += Math.max(5, Math.round(xMax / 8))) {{
    s += `<line x1="${{x(m)}}" y1="${{Y0}}" x2="${{x(m)}}" y2="${{Y1}}" stroke="#eef0f2"/>`;
    s += `<text x="${{x(m)}}" y="${{H-12}}" text-anchor="middle" font-size="10" fill="#66707c" font-family="monospace">${{m}}м</text>`;
  }}
  s += `<text x="${{X0}}" y="${{14}}" font-size="10" fill="#66707c" font-family="monospace">коммиты ↑ · минуты от старта →</text>`;
  for (const n of ARM_ORDER) {{
    if (hidden.has(n)) continue;
    const a = PD.arms[n], tl = a.commits_tl || [];
    if (tl.length < 1) continue;
    const dash = n === 'native' ? ' stroke-dasharray="5,4"' : '';
    let path = `M ${{x(0)}} ${{y(1)}}`;
    tl.forEach((p, i) => {{ path += ` L ${{x(p.m)}} ${{y(i+1)}}`; }});
    s += `<path d="${{path}}" fill="none" stroke="${{a.color}}" stroke-width="2"${{dash}}/>`;
    tl.forEach((p, i) => {{
      const tip = `${{a.title}} · ${{p.m}} мин · коммит #${{i+1}}: ${{p.msg}}`;
      if (p.task) s += `<circle cx="${{x(p.m)}}" cy="${{y(i+1)}}" r="5.5" fill="#fff" stroke="${{a.color}}" stroke-width="2"><title>${{tip}}</title></circle>`;
      else s += `<circle cx="${{x(p.m)}}" cy="${{y(i+1)}}" r="4" fill="${{a.color}}"><title>${{tip}}</title></circle>`;
    }});
    const lastP = tl[tl.length-1];
    s += `<text x="${{x(lastP.m)+7}}" y="${{y(tl.length)-4}}" font-size="11" fill="${{a.color}}" font-weight="600">${{a.title}}</text>`;
  }}
  s += '</svg>';
  document.getElementById('chart').innerHTML = s;
}}
document.getElementById('chips').innerHTML = ARM_ORDER.map(n => {{
  const a = PD.arms[n];
  return `<span class="chip${{hidden.has(n) ? ' off' : ''}}" data-arm="${{n}}"><span class="dot" style="background:${{a.color}}"></span>${{a.title}}</span>`;
}}).join('');
document.querySelectorAll('.chip').forEach(ch => ch.addEventListener('click', () => {{
  const n = ch.dataset.arm;
  hidden.has(n) ? hidden.delete(n) : hidden.add(n);
  ch.classList.toggle('off');
  writeHash();
  renderChart();
}}));
renderChart();
</script>
</body></html>"""

open(L, "w", encoding="utf-8").write(page)
print(
    f"{now}: панель обновлена ({len(page)} б, событий в ленте: {len(state['events'])})"
)

#!/usr/bin/env bash
# check-model-routing.sh <run-dir> — verify that .opencode/opencode.json model
# routing actually applies: session models in the opencode DB must match the
# configured routing. Exit 0 = match, 2 = mismatch, 1 = no data.
set -u
D="${1:?usage: $0 <run-dir>}"
python3 - "$D" << 'PYEOF'
import json, os, sqlite3, sys

d = os.path.abspath(sys.argv[1])
cfg_path = os.path.join(d, ".opencode", "opencode.json")
if not os.path.exists(cfg_path):
    print(f"no .opencode/opencode.json in {d}")
    sys.exit(1)
cfg = json.load(open(cfg_path, encoding="utf-8"))
routing = {k: (v or {}).get("model", "")
           for k, v in (cfg.get("agent") or {}).items()}

db = os.path.expanduser("~/.local/share/opencode/opencode.db")
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
rows = con.execute(
    "SELECT agent, model FROM session WHERE directory = ?", (d,)).fetchall()
con.close()
if not rows:
    print(f"no sessions recorded for {d}")
    sys.exit(1)

def model_id(m):
    try:
        return json.loads(m).get("id", "?")
    except (ValueError, TypeError):
        return "?"

seen = {}
for agent, model in rows:
    seen.setdefault(agent, set()).add(model_id(model))

ok = True
print(f"{'agent':14s} {'session models':28s} configured")
for agent, mids in sorted(seen.items()):
    exp = routing.get(agent, "")
    if exp:
        # config uses provider/model, session DB stores bare model id
        match = all(m == exp.split("/")[-1] for m in mids)
        verdict = "OK" if match else "MISMATCH"
        if not match:
            ok = False
    else:
        verdict = "(unrouted)"
    print(f"{agent:14s} {','.join(sorted(mids)):28s} {exp or '-':40s} {verdict}")
sys.exit(0 if ok else 2)
PYEOF

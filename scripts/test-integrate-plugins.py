#!/usr/bin/env python3
"""test-integrate-plugins.py — behavioral fixtures for integrate-plugins.py.

Covers the merge contract (change integrate-context-mode-ponytail, spec:
Idempotent config merge / Installer opt-out): absent config, existing config
with model routing + unknown fields + unrelated plugins, already-present
entries, repeated install, remove-mode both directions, malformed JSON
(untouched + non-zero), non-array 'plugin', legacy mcp['context-mode']
conflict, bad NATIVE_TEAM_PLUGINS value.
"""

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "integrate-plugins.py")
CM = "context-mode"
PT = "@dietrichgebert/ponytail"

fails = []


def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        fails.append(name)


def run(proj, env_mode=None):
    env = dict(os.environ)
    if env_mode is None:
        env.pop("NATIVE_TEAM_PLUGINS", None)
    else:
        env["NATIVE_TEAM_PLUGINS"] = env_mode
    return subprocess.run(
        [sys.executable, SCRIPT, proj], capture_output=True, text=True, env=env
    )


def write_cfg(proj, cfg):
    with open(os.path.join(proj, ".opencode", "opencode.json"), "w") as f:
        json.dump(cfg, f, indent=2)


def read_cfg(proj):
    with open(os.path.join(proj, ".opencode", "opencode.json")) as f:
        return json.load(f)


fx = tempfile.mkdtemp(prefix="plugins-fixture-")
try:
    # 1. absent config -> no-op, exit 0, no file created
    p1 = os.path.join(fx, "no-config")
    os.makedirs(os.path.join(p1, ".opencode"))
    r = run(p1)
    check("absent config: exit 0", r.returncode == 0)
    check(
        "absent config: no file created",
        not os.path.exists(os.path.join(p1, ".opencode", "opencode.json")),
    )

    # 2. existing config: model routing + unknown fields + unrelated plugins
    p2 = os.path.join(fx, "existing")
    os.makedirs(os.path.join(p2, ".opencode"))
    write_cfg(
        p2,
        {
            "$schema": "https://opencode.ai/config.json",
            "future_field": {"deep": [1, {"x": None}]},
            "plugin": ["some-other-plugin"],
            "mcp": {"my-server": {"command": "x"}},
            "agent": {
                "planner": {"model": "fast-model"},
                "reviewer": {
                    "permission": {"bash": {"*": "deny", "go test ./...": "allow"}}
                },
            },
        },
    )
    r = run(p2)
    check("existing config: exit 0", r.returncode == 0)
    c = read_cfg(p2)
    check(
        "existing config: entries appended after user entries",
        c["plugin"] == ["some-other-plugin", CM, PT],
    )
    check(
        "existing config: unknown field preserved",
        c["future_field"] == {"deep": [1, {"x": None}]},
    )
    check("existing config: mcp preserved", c["mcp"] == {"my-server": {"command": "x"}})
    check(
        "existing config: model routing preserved",
        c["agent"]["planner"]["model"] == "fast-model",
    )
    check(
        "existing config: reviewer bash map preserved",
        c["agent"]["reviewer"]["permission"]["bash"]["go test ./..."] == "allow",
    )

    # 3. repeated install -> no duplicates
    r = run(p2)
    check("repeat install: exit 0", r.returncode == 0)
    c = read_cfg(p2)
    check(
        "repeat install: no duplicates",
        c["plugin"].count(CM) == 1 and c["plugin"].count(PT) == 1,
    )

    # 4. already fully present -> no-op
    r = run(p2)
    check("already present: reports no changes", "no changes" in r.stdout)

    # 5. remove mode: strips recommended, keeps unrelated
    r = run(p2, "none")
    check("remove mode: exit 0", r.returncode == 0)
    c = read_cfg(p2)
    check(
        "remove mode: only unrelated plugin left", c["plugin"] == ["some-other-plugin"]
    )

    # 6. remove mode: emptied array -> key dropped
    write_cfg(p2, {"plugin": [CM, PT], "keep": 1})
    r = run(p2, "none")
    c = read_cfg(p2)
    check("remove mode: empty plugin key dropped", "plugin" not in c and c["keep"] == 1)

    # 7. remove mode on config without plugin array -> no-op
    write_cfg(p2, {"keep": 2})
    r = run(p2, "none")
    check(
        "remove mode without array: exit 0 no-op",
        r.returncode == 0 and read_cfg(p2) == {"keep": 2},
    )

    # 8. malformed JSON -> exit 1, file untouched
    bad = os.path.join(p2, ".opencode", "opencode.json")
    with open(bad, "w") as f:
        f.write('{ "plugin": [ truncated')
    before = open(bad).read()
    r = run(p2)
    check("malformed: exit 1", r.returncode == 1)
    check("malformed: file untouched", open(bad).read() == before)

    # 9. non-array plugin -> exit 1, file untouched
    write_cfg(p2, {"plugin": "context-mode"})
    r = run(p2)
    check("non-array plugin: exit 1", r.returncode == 1)
    check(
        "non-array plugin: file untouched", read_cfg(p2) == {"plugin": "context-mode"}
    )

    # 10. legacy mcp['context-mode'] -> warn + skip context-mode, add ponytail
    write_cfg(p2, {"plugin": ["x"], "mcp": {CM: {"command": CM}, "other": {}}})
    r = run(p2)
    check("legacy mcp: exit 0", r.returncode == 0)
    check("legacy mcp: warning printed", "context-mode upgrade" in r.stdout)
    c = read_cfg(p2)
    check("legacy mcp: context-mode entry skipped", c["plugin"] == ["x", PT])
    check("legacy mcp: mcp block intact", CM in c["mcp"] and "other" in c["mcp"])

    # 11. legacy mcp already has plugin entry too -> treated as present (no dup)
    write_cfg(p2, {"plugin": [CM, PT], "mcp": {CM: {}}})
    r = run(p2)
    c = read_cfg(p2)
    check("legacy mcp + entry present: no duplicate added", c["plugin"] == [CM, PT])

    # 12. bad env value -> exit 2
    r = run(p2, "banana")
    check("bad env value: exit 2", r.returncode == 2)

    # 13. fresh install flow: example copied then stripped by opt-out
    write_cfg(p2, {"plugin": [CM, PT, "other"], "agent": {"planner": {"model": "m"}}})
    r = run(p2, "none")
    c = read_cfg(p2)
    check(
        "opt-out fresh: recommended gone, rest kept",
        c["plugin"] == ["other"] and c["agent"]["planner"]["model"] == "m",
    )
finally:
    import shutil

    shutil.rmtree(fx, ignore_errors=True)

print()
if fails:
    print(f"INTEGRATE-PLUGINS TESTS FAILED: {len(fails)}")
    sys.exit(1)
print("ALL INTEGRATE-PLUGINS TESTS PASSED")

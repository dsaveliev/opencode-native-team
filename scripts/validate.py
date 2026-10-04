#!/usr/bin/env python3
"""validate.py — mechanical checks for the opencode-native-team repo.

Catches the error classes found in review rounds 1-4:
duplicate YAML keys, permission shape drift AND missing permissions,
contract line-limit violations, MANIFEST hash mismatches and lost upstream
pins, example-config regressions, shell syntax errors, Cyrillic/CJK
artifacts outside the allowed Russian files.
"""

import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = ["orchestrator", "planner", "tester", "reviewer", "coder"]
LIMITS = {"orchestrator": 90}  # subagents default to 40
CYRILLIC = re.compile(r"[\u0400-\u04ff\u0500-\u052f]")
CJK = re.compile(
    r"[\u2e80-\u2eff\u3000-\u30ff\u3400-\u4dbf\u4e00-\u9fff"
    r"\uac00-\ud7af\uf900-\ufaff\ufe30-\ufe4f\uff00-\uffef"
    r"\U00020000-\U0003ffff]"
)
# Files that are intentionally Russian ( originals / baseline task)
RU_ALLOWED = ["examples/TASK.ru.md", "docs/review-*.md", "docs/audit-*.md"]
errors = []


def err(msg):
    errors.append(msg)
    print(f"  FAIL {msg}")


def ok(msg):
    print(f"  ok   {msg}")


def ru_allowed(path):
    return any(fnmatch.fnmatch(path, pat) for pat in RU_ALLOWED)


def load_yaml_strict():
    try:
        import yaml
    except ImportError:
        err("PyYAML is required (pip install pyyaml) — YAML checks cannot run")
        return None
    try:

        class StrictLoader(yaml.SafeLoader):
            pass

        def no_dupes(loader, node, deep=False):
            mapping = {}
            for k_node, v_node in node.value:
                key = loader.construct_object(k_node, deep=deep)
                if key in mapping:
                    raise yaml.constructor.ConstructorError(
                        None, None, f"duplicate key {key!r}", k_node.start_mark
                    )
                mapping[key] = loader.construct_object(v_node, deep=deep)
            return mapping

        StrictLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_dupes
        )
        return yaml
    except Exception as e:  # pragma: no cover
        err(f"PyYAML loader setup failed: {e}")
        return None


def parse_frontmatter(text, where, yaml_mod):
    parts = text.split("\n---\n", 1)
    if not text.startswith("---") or len(parts) != 2:
        err(f"{where}: frontmatter delimiters broken")
        return None
    try:
        return yaml_mod.load(parts[0][4:], Loader=StrictLoader_global)
    except yaml_mod.YAMLError as e:
        err(f"{where}: YAML parse error: {e}")
        return None


StrictLoader_global = None


def main():
    global StrictLoader_global
    os.chdir(ROOT)

    print("[1] PyYAML availability (hard requirement)")
    yaml_mod = load_yaml_strict()
    if yaml_mod is None:
        print(f"\nVALIDATION FAILED: {len(errors)} error(s)")
        return 1
    StrictLoader_global = yaml_mod.SafeLoader

    # re-bind strict constructor on the global loader
    def _no_dupes(loader, node, deep=False):
        mapping = {}
        for k_node, v_node in node.value:
            key = loader.construct_object(k_node, deep=deep)
            if key in mapping:
                raise yaml_mod.constructor.ConstructorError(
                    None, None, f"duplicate key {key!r}", k_node.start_mark
                )
            mapping[key] = loader.construct_object(v_node, deep=deep)
        return mapping

    StrictLoader_global.add_constructor(
        yaml_mod.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dupes
    )
    ok("PyYAML present, strict loader ready")

    print("[2] agent frontmatter: strict YAML, no duplicate keys")
    fm = {}
    for a in AGENTS:
        text = open(f"agents/{a}.md", encoding="utf-8").read()
        data = parse_frontmatter(text, f"agents/{a}.md", yaml_mod)
        if data is not None:
            fm[a] = data
    if len(fm) == len(AGENTS):
        ok("all 5 frontmatters parse, zero duplicates")
    else:
        return finish()

    print("[3] permission invariants: shapes AND presence")
    for a in ("planner", "coder", "tester", "reviewer"):
        where = f"agents/{a}.md"
        perm = fm[a].get("permission", {})
        if perm.get("task") != {"*": "deny"}:
            err(f"{where}: permission.task must be {{'*': 'deny'}}")
        if perm.get("external_directory") != "deny":
            err(f"{where}: permission.external_directory must be scalar 'deny'")
        for tool in ("edit", "external_directory", "webfetch"):
            if tool in perm and not isinstance(perm[tool], str):
                err(
                    f"{where}: permission.{tool} must be scalar, got {type(perm[tool]).__name__}"
                )
        if fm[a].get("mode") != "subagent":
            err(f"{where}: mode must be 'subagent'")
    for a in ("planner", "reviewer"):
        where = f"agents/{a}.md"
        perm = fm[a].get("permission", {})
        if perm.get("edit") != "deny":
            err(f"{where}: read-only role must have edit: deny")
        if perm.get("webfetch") != "deny":
            err(f"{where}: read-only role must have webfetch: deny")
    for a in ("coder", "tester"):
        b = fm[a].get("permission", {}).get("bash", {})
        for pat in ("git commit*", "git push*", "git reset*", "git checkout -- *"):
            if b.get(pat) != "deny":
                err(f"agents/{a}.md: bash deny missing for '{pat}'")
    o = fm["orchestrator"].get("permission", {})
    task_perm = dict(o.get("task", {}))
    star = task_perm.pop("*", None)
    if star != "deny":
        err("agents/orchestrator.md: permission.task['*'] must be 'deny'")
    if set(task_perm) != {"planner", "coder", "tester", "reviewer"}:
        err(
            f"agents/orchestrator.md: task allow-list must be exactly the 4 roles, got {sorted(task_perm)}"
        )
    if set(task_perm.values()) != {"allow"}:
        err("agents/orchestrator.md: task allow-list values must all be 'allow'")
    if o.get("external_directory") != "deny":
        err(
            "agents/orchestrator.md: permission.external_directory must be scalar 'deny'"
        )
    if fm["orchestrator"].get("mode") != "primary":
        err("agents/orchestrator.md: mode must be 'primary'")
    if str(fm["reviewer"].get("temperature")) != "0.1":
        err("agents/reviewer.md: temperature must be 0.1")
    if not errors or not any(
        "[3]" in e
        or "permission" in e
        or "mode" in e
        or "bash deny" in e
        or "task" in e
        for e in errors
    ):
        ok("shapes and presence verified for all 5 contracts")

    print("[4] contract line limits (SPEC.md)")
    for a in AGENTS:
        n = sum(1 for _ in open(f"agents/{a}.md", encoding="utf-8"))
        limit = LIMITS.get(a, 40)
        if n > limit:
            err(f"agents/{a}.md: {n} lines > limit {limit}")
        else:
            ok(f"agents/{a}.md: {n}/{limit} lines")

    print("[5] MANIFEST.yaml: upstream pins, full sha256, no extra/missing")
    manifest = {}
    has_pin = False
    for line in open("vendor/MANIFEST.yaml", encoding="utf-8"):
        line = line.strip()
        if "agent-skills" in line and "@" in line and re.search(r"[0-9a-f]{40}", line):
            has_pin = True
        if line.startswith("skills/"):
            p, h = line.split(": ")
            manifest[p] = h
    if not has_pin:
        err(
            "MANIFEST.yaml: agent-skills upstream revision pin missing (D-1 regression)"
        )
    on_disk = set()
    for root, _dirs, files in os.walk("vendor/skills"):
        for fn in files:
            on_disk.add(os.path.relpath(os.path.join(root, fn), "vendor"))
    for p, h in sorted(manifest.items()):
        full = os.path.join("vendor", p)
        if not os.path.exists(full):
            err(f"MANIFEST lists missing file: {p}")
            continue
        if hashlib.sha256(open(full, "rb").read()).hexdigest() != h:
            err(f"hash mismatch: {p}")
    extra = on_disk - set(manifest)
    if extra:
        err(f"files on disk not in MANIFEST: {sorted(extra)}")
    if not any("MANIFEST" in e for e in errors):
        ok(f"pin present, {len(manifest)} hashes verified, {len(extra)} extra")

    print("[6] examples/opencode.json.example")
    try:
        cfg = json.load(open("examples/opencode.json.example", encoding="utf-8"))
    except json.JSONDecodeError as e:
        err(f"opencode.json.example: invalid JSON: {e}")
        cfg = {}
    if cfg.get("permission", {}).get("bash", {}).get("*") == "allow":
        err("opencode.json.example: global bash wildcard allow (R-5 regression)")
    rev = cfg.get("agent", {}).get("reviewer", {}).get("permission", {}).get("bash", {})
    if not any("test" in k for k in rev):
        err(
            "opencode.json.example: reviewer has no test command allow (R-4 regression)"
        )
    if "model" not in cfg.get("agent", {}).get("planner", {}):
        err("opencode.json.example: planner model routing missing")
    if not any("MANIFEST" in e or "json.example" in e for e in errors):
        ok("example config: no global allow, reviewer tests, model routing present")

    print("[7] shell scripts: syntax")
    for sh in ("install.sh", "examples/judge.sh", "scripts/check-model-routing.sh"):
        r = subprocess.run(["bash", "-n", sh], capture_output=True, text=True)
        if r.returncode != 0:
            err(f"{sh}: {r.stderr.strip()}")
        else:
            ok(f"{sh}")

    print("[8] Cyrillic / CJK outside allowed Russian files")
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
        for fn in files:
            p = os.path.relpath(os.path.join(root, fn))
            if ru_allowed(p) or not fn.endswith(
                (".md", ".py", ".sh", ".yaml", ".yml", ".json", ".example")
            ):
                continue
            text = open(p, encoding="utf-8", errors="ignore").read()
            if CYRILLIC.search(text):
                err(f"{p}: Cyrillic found (allowed only in {RU_ALLOWED})")
            if CJK.search(text):
                err(f"{p}: CJK found")
    ok("script artifact scan done")

    return finish()


def finish():
    print()
    if errors:
        print(f"VALIDATION FAILED: {len(errors)} error(s)")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

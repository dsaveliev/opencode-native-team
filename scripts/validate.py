#!/usr/bin/env python3
"""validate.py — mechanical checks for the opencode-native-team repo.

Catches the error classes found in review rounds 1-3:
duplicate YAML keys, permission shape drift (edit/external_directory/webfetch
must be scalars), contract line-limit violations, MANIFEST hash mismatches,
example-config regressions, shell syntax errors, CJK artifacts.
"""

import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = ["orchestrator", "planner", "coder", "tester", "reviewer"]
LIMITS = {"orchestrator": 90}  # subagents default to 40
CJK = re.compile(
    r"[\u2e80-\u2eff\u3000-\u30ff\u3400-\u4dbf\u4e00-\u9fff"
    r"\uac00-\ud7af\uf900-\ufaff\ufe30-\ufe4f\uff00-\uffef"
    r"\U00020000-\U0003ffff]"
)
errors = []


def err(msg):
    errors.append(msg)
    print(f"  FAIL {msg}")


def ok(msg):
    print(f"  ok   {msg}")


def parse_frontmatter_strict(text, where):
    """Parse frontmatter YAML detecting duplicate keys at every level."""
    try:
        import yaml
    except ImportError:
        print("  skip PyYAML not installed")
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
        return yaml.load(text, Loader=StrictLoader)
    except yaml.YAMLError as e:
        err(f"{where}: YAML parse error: {e}")
        return None


def main():
    os.chdir(ROOT)

    print("[1] agent frontmatter: strict YAML, no duplicate keys")
    fm = {}
    for a in AGENTS:
        text = open(f"agents/{a}.md", encoding="utf-8").read()
        parts = text.split("\n---\n", 1)
        if not text.startswith("---") or len(parts) != 2:
            err(f"agents/{a}.md: frontmatter delimiters broken")
            continue
        data = parse_frontmatter_strict(parts[0][4:], f"agents/{a}.md")
        if data is not None:
            fm[a] = data
            ok(f"agents/{a}.md")
    if len(fm) == len(AGENTS):
        ok("all 5 frontmatters parse, zero duplicates")

    print("[2] permission shapes: edit/external_directory/webfetch are scalars")
    for a, data in fm.items():
        perm = data.get("permission", {})
        for tool in ("edit", "external_directory", "webfetch"):
            if tool in perm and not isinstance(perm[tool], str):
                err(
                    f"agents/{a}.md: permission.{tool} must be scalar, got {type(perm[tool]).__name__}"
                )
    ok("shape check done")

    print("[3] contract line limits (SPEC.md)")
    for a in AGENTS:
        n = sum(1 for _ in open(f"agents/{a}.md", encoding="utf-8"))
        limit = LIMITS.get(a, 40)
        if n > limit:
            err(f"agents/{a}.md: {n} lines > limit {limit}")
        else:
            ok(f"agents/{a}.md: {n}/{limit} lines")

    print("[4] MANIFEST.yaml: full sha256 equality, no extra/missing files")
    manifest = {}
    for line in open("vendor/MANIFEST.yaml", encoding="utf-8"):
        line = line.strip()
        if line.startswith("skills/"):
            p, h = line.split(": ")
            manifest[p] = h
    on_disk = set()
    for root, _dirs, files in os.walk("vendor/skills"):
        for fn in files:
            on_disk.add(os.path.relpath(os.path.join(root, fn), "vendor"))
    for p, h in sorted(manifest.items()):
        full = os.path.join("vendor", p)
        if not os.path.exists(full):
            err(f"MANIFEST lists missing file: {p}")
            continue
        actual = hashlib.sha256(open(full, "rb").read()).hexdigest()
        if actual != h:
            err(f"hash mismatch: {p}")
    extra = on_disk - set(manifest)
    if extra:
        err(f"files on disk not in MANIFEST: {sorted(extra)}")
    if not errors or all("MANIFEST" not in e and "hash" not in e for e in errors):
        ok(f"{len(manifest)} files verified, {len(extra)} extra")

    print("[5] examples/opencode.json.example")
    try:
        cfg = json.load(open("examples/opencode.json.example", encoding="utf-8"))
    except json.JSONDecodeError as e:
        err(f"opencode.json.example: invalid JSON: {e}")
        cfg = {}
    top_bash = cfg.get("permission", {}).get("bash", {})
    if "*" in top_bash and top_bash.get("*") == "allow":
        err("opencode.json.example: global bash wildcard allow (R-5 regression)")
    rev = cfg.get("agent", {}).get("reviewer", {}).get("permission", {}).get("bash", {})
    if not any("test" in k for k in rev):
        err(
            "opencode.json.example: reviewer has no test command allow (R-4 regression)"
        )
    if "model" not in cfg.get("agent", {}).get("planner", {}):
        err("opencode.json.example: planner model routing missing")
    if not (errors and any("json.example" in e for e in errors)):
        ok("example config: no global allow, reviewer tests, model routing present")

    print("[6] shell scripts: syntax")
    for sh in ("install.sh", "examples/judge.sh"):
        r = subprocess.run(["bash", "-n", sh], capture_output=True, text=True)
        if r.returncode != 0:
            err(f"{sh}: {r.stderr.strip()}")
        else:
            ok(f"{sh}")

    print("[7] CJK / script artifacts")
    allowed_ru = {"examples/TASK.ru.md"}
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
        for fn in files:
            p = os.path.relpath(os.path.join(root, fn))
            if p in allowed_ru or not fn.endswith(
                (".md", ".py", ".sh", ".yaml", ".yml", ".json", ".example")
            ):
                continue
            text = open(p, encoding="utf-8", errors="ignore").read()
            if CJK.search(text):
                err(f"{p}: CJK characters found")
    ok("CJK scan done")

    print()
    if errors:
        print(f"VALIDATION FAILED: {len(errors)} error(s)")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

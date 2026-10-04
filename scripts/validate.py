#!/usr/bin/env python3
"""validate.py — mechanical checks for the opencode-native-team repo.

Error classes caught (from review rounds 1-5):
duplicate YAML keys, permission shape drift AND missing permissions,
contract line-limit violations, MANIFEST hash mismatches and lost upstream
pins, example-config regressions (including the complete-map rule),
shell syntax errors, Cyrillic/CJK artifacts outside allowed Russian files,
documentation reality: paths named in README/reviews must exist on disk,
review files must reference real and mutually unique commits.
"""

import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    print("FAIL PyYAML is required (pip install pyyaml) — cannot validate")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = ["orchestrator", "planner", "tester", "reviewer", "coder"]
LIMITS = {"orchestrator": 90}  # subagents default to 40
CYRILLIC = re.compile(r"[\u0400-\u04ff\u0500-\u052f]")
CJK = re.compile(
    r"[\u2e80-\u2eff\u3000-\u30ff\u3400-\u4dbf\u4e00-\u9fff"
    r"\uac00-\ud7af\uf900-\ufaff\ufe30-\ufe4f\uff00-\uffef"
    r"\U00020000-\U0003ffff]"
)
RU_ALLOWED = ["examples/TASK.ru.md", "docs/review-*.md", "docs/audit-*.md"]
# paths that docs may name; anything matching must exist on disk.
# Only repo-tree dirs; bare filenames and .opencode/* are target-project files.
DOC_PATH = re.compile(
    r"`((?:docs|agents|examples|scripts|commands|vendor|artifacts|results|"
    r"\.github|openspec)/[A-Za-z0-9_./-]+|install\.sh)`"
)
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
errors = []


def err(msg):
    errors.append(msg)
    print(f"  FAIL {msg}")


class Step:
    """ok() prints only if the step added zero errors since its start."""

    def __init__(self, title):
        print(title)
        self._before = len(errors)

    def ok(self, msg):
        if len(errors) == self._before:
            print(f"  ok   {msg}")


class StrictLoader(yaml.SafeLoader):
    pass


def _no_dupes(loader, node, deep=False):
    mapping = {}
    for k_node, v_node in node.value:
        key = loader.construct_object(k_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r}", k_node.start_mark
            )
        mapping[key] = loader.construct_object(v_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dupes)


def parse_frontmatter(text, where):
    parts = text.split("\n---\n", 1)
    if not text.startswith("---") or len(parts) != 2:
        err(f"{where}: frontmatter delimiters broken")
        return None
    try:
        return yaml.load(parts[0][4:], Loader=StrictLoader)
    except yaml.YAMLError as e:
        err(f"{where}: YAML parse error: {e}")
        return None


def ru_allowed(path):
    return any(fnmatch.fnmatch(path, pat) for pat in RU_ALLOWED)


def git_shas():
    """Short SHAs of full history; on a shallow clone the caller reports
    a clear fix instead of per-file false failures."""
    shallow = (
        subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == "true"
    )
    if shallow:
        err(
            "shallow clone: review subject commits cannot resolve — "
            "run 'git fetch --unshallow' (CI: actions/checkout fetch-depth: 0)"
        )
        return None
    out = subprocess.run(
        ["git", "log", "--format=%h"], cwd=ROOT, capture_output=True, text=True
    ).stdout.split()
    return set(out)


def main():
    os.chdir(ROOT)

    s = Step("[1] agent frontmatter: strict YAML, no duplicate keys")
    fm = {}
    for a in AGENTS:
        data = parse_frontmatter(
            open(f"agents/{a}.md", encoding="utf-8").read(), f"agents/{a}.md"
        )
        if data is not None:
            fm[a] = data
    if len(fm) == len(AGENTS):
        s.ok("all 5 frontmatters parse, zero duplicates")

    s = Step("[2] permission invariants: shapes AND presence")
    for a in ("planner", "coder", "tester", "reviewer"):
        where = f"agents/{a}.md"
        perm = fm.get(a, {}).get("permission", {})
        if perm.get("task") != {"*": "deny"}:
            err(f"{where}: permission.task must be {{'*': 'deny'}}")
        if perm.get("external_directory") != "deny":
            err(f"{where}: permission.external_directory must be scalar 'deny'")
        for tool in ("edit", "external_directory", "webfetch"):
            if tool in perm and not isinstance(perm[tool], str):
                err(
                    f"{where}: permission.{tool} must be scalar, got {type(perm[tool]).__name__}"
                )
        if fm.get(a, {}).get("mode") != "subagent":
            err(f"{where}: mode must be 'subagent'")
    for a in ("planner", "reviewer"):
        perm = fm.get(a, {}).get("permission", {})
        if perm.get("edit") != "deny":
            err(f"agents/{a}.md: read-only role must have edit: deny")
        if perm.get("webfetch") != "deny":
            err(f"agents/{a}.md: read-only role must have webfetch: deny")
    for a in ("coder", "tester"):
        b = fm.get(a, {}).get("permission", {}).get("bash", {})
        for pat in ("git commit*", "git push*", "git reset*", "git checkout -- *"):
            if b.get(pat) != "deny":
                err(f"agents/{a}.md: bash deny missing for '{pat}'")
    o = fm.get("orchestrator", {}).get("permission", {})
    task_perm = dict(o.get("task", {}))
    if task_perm.pop("*", None) != "deny":
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
    if fm.get("orchestrator", {}).get("mode") != "primary":
        err("agents/orchestrator.md: mode must be 'primary'")
    if str(fm.get("reviewer", {}).get("temperature")) != "0.1":
        err("agents/reviewer.md: temperature must be 0.1")
    s.ok("shapes and presence verified for all 5 contracts")

    s = Step("[3] contract line limits (SPEC.md)")
    for a in AGENTS:
        n = sum(1 for _ in open(f"agents/{a}.md", encoding="utf-8"))
        limit = LIMITS.get(a, 40)
        if n > limit:
            err(f"agents/{a}.md: {n} lines > limit {limit}")
    s.ok("line limits hold")

    s = Step("[4] MANIFEST.yaml: upstream pins, full sha256, no extra/missing")
    manifest = {}
    has_pin = False
    for line in open("vendor/MANIFEST.yaml", encoding="utf-8"):
        line = line.strip()
        if "agent-skills" in line and re.search(r"[0-9a-f]{40}", line):
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
    s.ok(f"pin present, {len(manifest)} hashes verified, {len(extra)} extra")

    s = Step("[5] examples/opencode.json.example")
    try:
        cfg = json.load(open("examples/opencode.json.example", encoding="utf-8"))
    except json.JSONDecodeError as e:
        err(f"opencode.json.example: invalid JSON: {e}")
        cfg = {}
    # C-2 (probed, supersedes R-5): headless/autonomous is the primary mode;
    # top-level allows are REQUIRED for it and do NOT weaken subagent
    # contracts (frontmatter denies take precedence over top-level allows)
    top = cfg.get("permission", {})
    if top.get("bash", {}).get("*") != "allow":
        err(
            "opencode.json.example: top-level bash allow missing — headless "
            "runs auto-reject every command (probed)"
        )
    if top.get("edit", {}).get("*") != "allow":
        err(
            "opencode.json.example: top-level edit allow missing — headless "
            "runs cannot write files"
        )
    rev = cfg.get("agent", {}).get("reviewer", {}).get("permission", {}).get("bash", {})
    if not any("test" in k for k in rev):
        err(
            "opencode.json.example: reviewer has no test command allow (R-4 regression)"
        )
    # C-1: the JSON override must be a SUPERSET of the reviewer frontmatter
    # bash map — a trimmed map silently strips git-read allows and separator
    # denies (presence of "*" alone does not express "complete")
    fm_rev_bash = fm.get("reviewer", {}).get("permission", {}).get("bash", {})
    if isinstance(fm_rev_bash, dict):
        for pat, action in fm_rev_bash.items():
            if rev.get(pat) != action:
                err(
                    "opencode.json.example: reviewer bash map must be a "
                    f"superset of the contract — missing {pat!r}: {action!r}"
                )
    if "model" not in cfg.get("agent", {}).get("planner", {}):
        err("opencode.json.example: planner model routing missing")
    s.ok("example config: headless allows, reviewer superset map, model routing")

    s = Step("[6] commands/")
    for cf in ("commands/team.md", "commands/team-change.md"):
        ctext = open(cf, encoding="utf-8").read()
        cdata = parse_frontmatter(ctext, cf)
        if cdata is not None:
            if not cdata.get("description"):
                err(f"{cf}: description missing")
            if cdata.get("agent") != "orchestrator":
                err(f"{cf}: agent must be 'orchestrator'")
            if "$ARGUMENTS" not in ctext and "$1" not in ctext:
                err(f"{cf}: $ARGUMENTS/$1 placeholder missing")
    s.ok("commands /team and /team-change valid")

    s = Step("[7] shell scripts: syntax + skills config schema")
    ts = json.load(open("examples/team-skills.json", encoding="utf-8"))
    for ent in ts.get("skills", []):
        if not ent.get("name") or not ent.get("source"):
            err("examples/team-skills.json: entry missing name/source")
        for st in ent.get("stages", []):
            if st not in ("proposal", "design", "tasks", "apply", "verify"):
                err(f"examples/team-skills.json: invalid stage {st!r}")
    import ast
    ast.parse(open("scripts/gen-team-dashboard.py", encoding="utf-8").read())
    dash = json.load(open("examples/team-dashboard.json", encoding="utf-8"))
    if dash.get("mode") not in ("ask", "always", "never"):
        err("examples/team-dashboard.json: mode must be ask|always|never")
    if not isinstance(dash.get("refresh", 5), int) or dash.get("refresh", 5) < 2:
        err("examples/team-dashboard.json: refresh must be int >= 2")
    r = subprocess.run([sys.executable, "scripts/test-dashboard.py"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        err("dashboard behavioral test failed:\n" + r.stdout[-800:])
    for sh in ("install.sh", "examples/judge.sh", "scripts/check-model-routing.sh",
               "scripts/sync-skills.sh", "scripts/team-dashboard.sh"):
        r = subprocess.run(["bash", "-n", sh], capture_output=True, text=True)
        if r.returncode != 0:
            err(f"{sh}: {r.stderr.strip()}")
    s.ok("bash -n clean")

    s = Step("[8] Cyrillic / CJK outside allowed Russian files")
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
    s.ok("no script artifacts")

    s = Step("[9] documentation reality: paths exist, review SHAs resolve & unique")
    for doc in ("README.md", "docs/reviews.md"):
        text = open(doc, encoding="utf-8").read()
        for m in DOC_PATH.finditer(text):
            path = m.group(1)
            if not os.path.exists(path):
                err(f"{doc}: names missing path '{path}'")
    if not os.path.exists("docs/artifacts/native-v5-models-routing.txt"):
        err("docs/reviews.md: promised artifact docs/artifacts/... missing")
    shas = git_shas()
    if shas is None:
        s.ok("skipped: see shallow-clone error above")
        print()
        print(f"VALIDATION FAILED: {len(errors)} error(s)")
        return 1
    # subject commit = the first SHA on the "Kommit(y) ..." header line
    # (\u041a\u043a = Cyrillic K/k — kept escaped to keep this file ASCII);
    # SHAs merely quoted inside the body may repeat across reviews
    subj_re = re.compile(
        "(?:[\u041a\u043a]\u043e\u043c\u043c\u0438\u0442(?:\u044b)?|Commit)\\s+`?([0-9a-f]{7,40})",
        re.IGNORECASE,
    )
    seen = {}
    for rf in sorted(fnmatch.filter(os.listdir("docs"), "review-*.md")):
        text = open(f"docs/{rf}", encoding="utf-8").read()
        m = subj_re.search(text[:400])
        if not m:
            err(
                f"docs/{rf}: no subject commit line ('Kommit <sha>' in Cyrillic) in header"
            )
            continue
        subj = m.group(1)
        if subj not in shas:
            err(f"docs/{rf}: subject commit {subj} not in git log")
        elif subj in seen:
            err(
                f"docs/{rf}: subject {subj} already reviewed by "
                f"docs/{seen[subj]} — each review must cover a distinct commit"
            )
        else:
            seen[subj] = rf
    # G-1: every review file must have its section in docs/reviews.md
    # (review-v5.1.K.md documents round K+2)
    journal = open("docs/reviews.md", encoding="utf-8").read()
    have_rounds = {int(m) for m in re.findall(r"## Round (\d+)", journal)}
    for rf in sorted(fnmatch.filter(os.listdir("docs"), "review-*.md")):
        m = re.match(r"review-v5\.1\.(\d+)\.md", rf)
        if m and int(m.group(1)) + 2 not in have_rounds:
            err(f"docs/{rf}: no 'Round {int(m.group(1)) + 2}' section in docs/reviews.md")
    s.ok("doc paths on disk, review subject commits resolve and are unique, journal complete")

    print()
    if errors:
        print(f"VALIDATION FAILED: {len(errors)} error(s)")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

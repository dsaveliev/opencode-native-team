#!/usr/bin/env bash
# sync-skills.sh <project-dir> [--update]
# Installs stack skills declared in <project>/.opencode/team-skills.json into
# <project>/.opencode/skills/ and pins them in skills.lock (sha256 per file —
# same integrity philosophy as vendor/MANIFEST.yaml).
#   default : verify installed skills against the lock, install missing ones
#   --update: re-copy from sources and refresh the lock
# Exit 0 = synced/verified, 1 = config/source errors, 2 = lock mismatch.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:?usage: $0 /path/to/project [--update]}"
UPDATE="${2:-}"
CFG="${TARGET}/.opencode/team-skills.json"
SKILLS_DIR="${TARGET}/.opencode/skills"
LOCK="${SKILLS_DIR}/skills.lock"

[ -f "$CFG" ] || { echo "no .opencode/team-skills.json in ${TARGET} — nothing to sync"; exit 0; }
mkdir -p "$SKILLS_DIR"

python3 - "$CFG" "$SKILLS_DIR" "$LOCK" "$UPDATE" << 'PYEOF'
import hashlib, json, os, shutil, sys

cfg_path, skills_dir, lock_path, update = sys.argv[1:5]
update = update == "--update"

try:
    cfg = json.load(open(cfg_path, encoding="utf-8"))
except json.JSONDecodeError as e:
    print(f"FAIL {cfg_path}: invalid JSON: {e}", file=sys.stderr)
    sys.exit(1)

VALID_STAGES = {"proposal", "design", "tasks", "apply", "verify"}
entries = cfg.get("skills", [])
lock = {}
if os.path.exists(lock_path):
    for line in open(lock_path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            p, h = line.split(": ")
            lock[p] = h

def digest(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

def skill_files(skill_dir):
    out = []
    for root, _dirs, files in os.walk(skill_dir):
        for fn in files:
            out.append(os.path.relpath(os.path.join(root, fn), skill_dir))
    return sorted(out)

failed = False
new_lock = {}
for ent in entries:
    name, source, stages = ent.get("name"), ent.get("source", ""), ent.get("stages", [])
    if not name:
        print("FAIL entry without 'name'", file=sys.stderr)
        failed = True
        continue
    bad = [s for s in stages if s not in VALID_STAGES]
    if bad:
        print(f"FAIL {name}: invalid stages {bad} (valid: {sorted(VALID_STAGES)})", file=sys.stderr)
        failed = True
        continue
    src = os.path.expanduser(source)
    dst = os.path.join(skills_dir, name)
    installed = os.path.isdir(dst) and os.path.exists(os.path.join(dst, "SKILL.md"))
    if not os.path.isdir(src) or not os.path.exists(os.path.join(src, "SKILL.md")):
        if installed and not update:
            print(f"  = {name}: source missing, keeping installed copy")
            for rel in skill_files(dst):
                new_lock[f"{name}/{rel}"] = digest(os.path.join(dst, rel))
            continue
        print(f"FAIL {name}: source {source} missing or has no SKILL.md", file=sys.stderr)
        failed = True
        continue
    if update or not installed:
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"  + {name}: installed from {source} (stages: {','.join(stages) or 'none'})")
    # verify (or record) hashes
    for rel in skill_files(dst if os.path.isdir(dst) else src):
        full = os.path.join(dst if os.path.isdir(dst) else src, rel)
        h = digest(full)
        rel_key = f"{name}/{rel}"
        new_lock[rel_key] = h
        if not update and rel_key in lock and lock[rel_key] != h:
            print(f"FAIL hash mismatch: {rel_key}", file=sys.stderr)
            print(f"  expected {lock[rel_key]}", file=sys.stderr)
            print(f"  actual   {h}", file=sys.stderr)
            failed = True

# detect installed-but-undeclared skills only in strict mode? keep permissive.

if failed:
    sys.exit(1)

with open(lock_path, "w", encoding="utf-8") as f:
    f.write("# synced by sync-skills.sh; sha256 per file (verify on re-run)\n")
    for k in sorted(new_lock):
        f.write(f"{k}: {new_lock[k]}\n")
print(f"  lock: {len(new_lock)} file hashes -> {os.path.basename(lock_path)}")
PYEOF

echo "done"

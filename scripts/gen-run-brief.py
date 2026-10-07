#!/usr/bin/env python3
"""Deterministic RUN-BRIEF.md generator. Template = single structural source.

Modes: quick (interactive, ~6 answers, minimal brief), full (--full, all
sections), non-interactive (--non-interactive with flags, byte-reproducible).
Canonical prose is copied verbatim from examples/RUN-BRIEF.md; only slots
listed in SUBST_* are parameterized. Drift between template and script
expectations is a hard error, not silent output corruption.
"""

import argparse
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(SCRIPT_DIR, "..", "examples", "RUN-BRIEF.md")

MINIMAL_MARKERS = {
    "title": "# RUN-BRIEF.md (minimal)",
    "mode": "- Mode: unattended.",
    "mission": "- Objective source: TASK.md (owns WHAT and completion semantics).",
    "scope_row": "| ./       | write, branch feat/* only |",
    "scope_row2": "| docs/    | read |",
    "fence": "- Scope fence: nothing beyond TASK.md.",
    "term": "## 12. Termination",
}

REQUIRED_MINIMAL = [
    "## 1. Envelope",
    "## 2. Mission Reference",
    "## 3. Decision Authority",
    "## 4. Scope Map",
    "## 12. Termination",
]
REQUIRED_FULL = [f"## {i}." for i in range(1, 13)]


def load_template(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def minimal_block(tpl):
    m = re.search(
        r"## Minimal Valid Brief \(example\)\n.*?```markdown\n(.*?)```", tpl, re.S
    )
    if not m:
        sys.exit("template drift: fenced minimal example not found")
    return m.group(1)


def ask(prompt, default):
    ans = input(f"{prompt} [{default}]: ").strip()
    return ans or default


def collect_interactive(full):
    name = ask("Run name", "nightly")
    mode = ask("Mode (unattended/attended)", "unattended")
    mission = ask("Mission source (TASK.md or openspec change <id>)", "TASK.md")
    rows, row = (
        [],
        ask("Scope row 'path=access' (empty to stop)", "./=write, branch feat/* only"),
    )
    while row:
        rows.append(row)
        row = ask("Scope row 'path=access' (empty to stop)", "")
    retries = ask("Retries (0..)", "3")
    fence = ask("Termination scope fence", "nothing beyond the mission source")
    keep = {}
    if full:
        for i in range(5, 12):
            if i in (5, 6, 7, 8, 9, 10):
                keep[i] = ask(f"Keep section {i}", "n").lower().startswith("y")
        keep[11] = ask("Keep section 11 (Handoff)", "y").lower().startswith("y")
    return dict(
        name=name,
        mode=mode,
        mission=mission,
        rows=rows,
        retries=int(retries),
        fence=fence,
        keep=keep,
        locality="local-only",
    )


def scope_lines(rows):
    lines = [
        MINIMAL_MARKERS["scope_row"] if r.startswith("./=") else f"| {p:<8} | {a} |"
        for r in rows
        for p, a in [r.split("=", 1)]
    ]
    return "\n".join(lines)


def build_minimal(a):
    block = minimal_block(load_template(a["template"]))
    for key, val in (
        ("title", f"# RUN-BRIEF.md ({a['name']})"),
        ("mode", f"- Mode: {a['mode']}."),
        (
            "mission",
            f"- Objective source: {a['mission']} (owns WHAT and completion semantics).",
        ),
        ("fence", f"- Scope fence: {a['fence']}."),
    ):
        if MINIMAL_MARKERS[key] not in block:
            sys.exit(f"template drift: marker {key!r} missing in minimal example")
        block = block.replace(MINIMAL_MARKERS[key], val)
    if a["rows"]:
        block = block.replace(
            MINIMAL_MARKERS["scope_row"] + "\n" + MINIMAL_MARKERS["scope_row2"],
            scope_lines(a["rows"]),
        )
    if a["retries"] != 3:
        block = block.replace(
            MINIMAL_MARKERS["term"],
            f"## 10. Recovery\n- Retries: {a['retries']}.\n\n"
            + MINIMAL_MARKERS["term"],
        )
    return block


def build_full(a):
    tpl = load_template(a["template"])
    tpl = tpl.replace("# Run Brief: <run name>", f"# Run Brief: {a['name']}")
    parts = re.split(r"(?m)^(?=## )", tpl)
    out = []
    for part in parts:
        m = re.match(r"## (\d+)\.", part)
        if not m:
            if part.startswith("## Minimal Valid Brief"):
                continue  # the example appendix is template documentation, not brief content
            out.append(part)
            continue
        i = int(m.group(1))
        if i in a["keep"] and not a["keep"][i]:
            continue
        if i == 1:
            part = part.replace(
                "- Mode: <unattended | attended>", f"- Mode: {a['mode']}"
            )
            part = part.replace(
                "- Locality: <local-only | remote policy>",
                f"- Locality: {a['locality']}",
            )
        elif i == 2:
            part = part.replace("<TASK.md | openspec change <id>>", a["mission"])
        elif i == 10:
            part = part.replace("<N>", str(a["retries"]))
        elif i == 12:
            part = part.replace("<next epic / checkpoint / ...>", a["fence"])
        out.append(part)
    text = "".join(out)
    return re.sub(r"\n{3,}", "\n\n", text)


def verify(text, full):
    need = REQUIRED_FULL if full else REQUIRED_MINIMAL
    missing = [
        h for h in need if not re.search(rf"^{re.escape(h)}(\s\S|\s*$)", text, re.M)
    ]
    if missing:
        sys.exit(f"internal error: generated brief missing {missing}")


def main():
    ap = argparse.ArgumentParser(description="Deterministic RUN-BRIEF.md generator")
    ap.add_argument("--non-interactive", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--name", default="nightly")
    ap.add_argument("--mode", default="unattended")
    ap.add_argument("--locality", default="local-only")
    ap.add_argument("--mission", default="TASK.md")
    ap.add_argument(
        "--scope", action="append", default=[], help="path=access, repeatable"
    )
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--fence", default="nothing beyond the mission source")
    ap.add_argument("--output", default="RUN-BRIEF.md")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE)
    ap.add_argument("--stdout", action="store_true")
    a = vars(ap.parse_args())

    if a["non_interactive"]:
        a["rows"] = a["scope"]
        a["keep"] = {i: True for i in range(5, 12)}  # keep all in scripted full mode
    else:
        a.update(collect_interactive(a["full"]))

    text = build_full(a) if a["full"] else build_minimal(a)
    verify(text, a["full"])
    if a["stdout"]:
        print(text, end="")
        return
    if os.path.exists(a["output"]) and not a["force"]:
        sys.exit(
            f"{a['output']} exists; a brief is read-only during a run — "
            "pass --force to replace it deliberately"
        )
    with open(a["output"], "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {a['output']}")


if __name__ == "__main__":
    main()

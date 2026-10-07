#!/usr/bin/env python3
"""integrate-plugins.py — add/remove recommended OpenCode plugin entries in a
project's .opencode/opencode.json (change integrate-context-mode-ponytail).

Modes, selected by env NATIVE_TEAM_PLUGINS (default: add):
  add   append missing recommended entries to the "plugin" array —
        idempotent, never duplicates, never touches other fields
  none  strip the recommended entries; drop "plugin" if left empty

Malformed JSON or a non-object/non-array shape -> exit 1, file untouched.
If a legacy mcp["context-mode"] registration exists, warns and skips the
context-mode entry (plugin + mcp together register zero ctx_* tools
upstream); the user is directed to `context-mode upgrade`.
"""

import json
import os
import sys

RECOMMENDED = ["context-mode", "@dietrichgebert/ponytail"]


def main():
    if len(sys.argv) != 2:
        print("usage: integrate-plugins.py <project-dir>", file=sys.stderr)
        return 2
    cfg_path = os.path.join(sys.argv[1], ".opencode", "opencode.json")
    mode = os.environ.get("NATIVE_TEAM_PLUGINS", "add").strip().lower() or "add"
    if mode not in ("add", "none"):
        print(
            f"integrate-plugins: unknown NATIVE_TEAM_PLUGINS={mode!r}"
            " (use 'add' or 'none')",
            file=sys.stderr,
        )
        return 2
    remove = mode == "none"

    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        print(f"integrate-plugins: {cfg_path} not found — nothing to merge")
        return 0
    except json.JSONDecodeError as e:
        print(
            f"integrate-plugins: {cfg_path} is not valid JSON ({e}) —"
            " file left untouched",
            file=sys.stderr,
        )
        return 1
    if not isinstance(cfg, dict):
        print(
            f"integrate-plugins: {cfg_path} top level must be an object —"
            " file left untouched",
            file=sys.stderr,
        )
        return 1

    original = cfg.get("plugin")
    if original is not None and not isinstance(original, list):
        print(
            "integrate-plugins: 'plugin' must be an array — file left untouched",
            file=sys.stderr,
        )
        return 1

    if remove:
        if original is None:
            print("integrate-plugins: nothing to remove — no 'plugin' array")
            return 0
        kept = [p for p in original if p not in RECOMMENDED]
        if not kept:
            del cfg["plugin"]
        elif len(kept) == len(original):
            print("integrate-plugins: already in desired state — no changes")
            return 0
        else:
            cfg["plugin"] = kept
        action = "removed recommended plugin entries"
    else:
        plugins = list(original) if original is not None else []
        legacy_mcp = isinstance(cfg.get("mcp"), dict) and "context-mode" in cfg["mcp"]
        added = []
        for name in RECOMMENDED:
            if name in plugins:
                continue
            if name == "context-mode" and legacy_mcp:
                print(
                    "integrate-plugins: WARNING mcp['context-mode'] present —"
                    " plugin + mcp together register ZERO ctx_* tools."
                    " Run 'context-mode upgrade', then re-run install."
                    " Skipping the context-mode plugin entry."
                )
                continue
            plugins.append(name)
            added.append(name)
        if not added:
            print("integrate-plugins: already in desired state — no changes")
            return 0
        cfg["plugin"] = plugins
        action = f"added plugin entries: {', '.join(added)}"

    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"integrate-plugins: {action}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Self-test for gen-run-brief.py against the real template (3 fixtures)."""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "gen-run-brief.py")


def run(args, stdin=None):
    return subprocess.run(
        [sys.executable, GEN] + args, capture_output=True, text=True, input=stdin
    )


def t_quick_shape():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "RUN-BRIEF.md")
        r = run(
            ["--output", out],
            stdin="nightly\nunattended\nopenspec change c1\n"
            "./=write, branch feat/* only\n\n1\nsandbox only\n",
        )
        assert r.returncode == 0, r.stderr
        t = open(out).read()
        assert "# RUN-BRIEF.md (nightly)" in t
        assert "openspec change c1" in t
        assert "## 10. Recovery\n- Retries: 1." in t
        assert "- Scope fence: sandbox only." in t
        for h in ("## 1.", "## 2.", "## 3.", "## 4.", "## 12."):
            assert f"\n{h} " in t or t.startswith(f"# {h}") or f"\n{h}\n" in t, h
    print("PASS quick shape")


def t_reproducible():
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.md"), os.path.join(d, "b.md")
        for out in (a, b):
            r = run(
                [
                    "--non-interactive",
                    "--name",
                    "t",
                    "--retries",
                    "2",
                    "--full",
                    "--mission",
                    "TASK.md",
                    "--fence",
                    "x",
                    "--output",
                    out,
                ]
            )
            assert r.returncode == 0, r.stderr
        assert open(a, "rb").read() == open(b, "rb").read()
    print("PASS non-interactive reproducible")


def t_full_coverage():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "RUN-BRIEF.md")
        r = run(["--non-interactive", "--full", "--output", out])
        assert r.returncode == 0, r.stderr
        t = open(out).read()
        import re

        for i in range(1, 13):
            assert re.search(rf"^## {i}\. ", t, re.M), f"section {i} missing"
        assert "## Minimal Valid Brief" not in t
    print("PASS full coverage")


def t_scope_verbatim():
    # regression (harness-contract-consistency D4): operator access is data.
    # A './=read' request must stay read — the old code emitted the
    # canonical write row, silently widening the restriction.
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "RUN-BRIEF.md")
        r = run(
            [
                "--non-interactive",
                "--output",
                out,
                "--name",
                "scoped",
                "--mode",
                "unattended",
                "--mission",
                "TASK.md",
                "--scope",
                "./=read",
                "--retries",
                "3",
                "--fence",
                "nothing",
            ]
        )
        assert r.returncode == 0, r.stderr
        t = open(out).read()
        assert "| ./       | read |" in t, "operator read scope not preserved"
        assert "| ./       | write, branch feat/* only |" not in t, (
            "canonical write row leaked into an operator-specified scope"
        )
    print("PASS scope verbatim")


if __name__ == "__main__":
    t_quick_shape()
    t_reproducible()
    t_full_coverage()
    t_scope_verbatim()
    print("4 PASS")

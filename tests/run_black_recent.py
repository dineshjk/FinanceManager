# -*- coding: utf-8 -*-
# tests/run_black_recent.py
#!/usr/bin/env python3
"""Run Black on recently modified Python files in the StockMan package.

Usage:
  python run_black_recent.py [--minutes MIN] [--line-length N] [--apply]

By default the script prints the files it would touch and runs Black in
check+diff mode. Pass --apply to reformat files in-place.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from typing import List


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def find_recent_py_files(root: str, minutes: int) -> List[str]:
    """Return list of Python files under ``root`` modified in the
    last ``minutes``.

    The function walks the directory tree rooted at ``root`` and collects
    absolute paths for files ending with ``.py`` whose modification time is
    at or after the computed cutoff. Files that cannot be stat'ed are silently
    ignored.
    """

    cutoff = time.time() - minutes * 60
    files: List[str] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                if os.path.getmtime(p) >= cutoff:
                    files.append(p)
            except OSError:
                # ignore files we can't stat
                pass
    return files


def run_black(files: List[str], line_length: int, apply: bool) -> int:
    """Invoke Black on ``files`` with the given ``line_length``.

    If ``apply`` is False Black is executed in check+diff mode. The function
    returns Black's exit code so callers can propagate or inspect it.
    """

    if not files:
        print("No recently saved Python files found.")
        return 0

    cmd = [sys.executable, "-m", "black", "--line-length", str(line_length)]
    if not apply:
        cmd += ["--check", "--diff"]
    cmd += files

    print("Running:", " ".join(cmd))
    # use check=False so we can return Black's exit code to the caller
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def main(argv: List[str] | None = None) -> int:
    """Command-line entry point: parse args, locate recent files and run Black.

    Returns the exit code from Black, or 0 if no recent files were found.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--minutes",
        "-m",
        type=int,
        default=10,
        help="Lookback window in minutes",
    )
    parser.add_argument(
        "--line-length",
        "-l",
        type=int,
        default=79,
        help="Black line length",
    )
    parser.add_argument(
        "--apply",
        "-a",
        action="store_true",
        help="Apply formatting (default: check+diff)",
    )
    args = parser.parse_args(argv)

    files = find_recent_py_files(ROOT, args.minutes)
    if not files:
        print(f"No Python files modified in the last {args.minutes} minutes.")
        return 0

    print("Files to format:")
    for f in files:
        print(" -", f)

    rc = run_black(files, args.line_length, args.apply)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Context-aware wrapper around extract_from_worktree.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def fail(message: str) -> None:
    raise SystemExit(f"extract_operator error: {message}")


def load_context(path: str) -> dict:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        fail(f"context file not found: {p}")
    return json.loads(p.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract one repaired worktree into the PR branch")
    parser.add_argument("--context", required=True)
    parser.add_argument("--op", required=True, help="normalized operator name")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ctx = load_context(args.context)
    repo = Path(ctx["repo_dir"]).resolve()
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "extract_from_worktree.py"),
        args.op,
        "--repo-dir",
        str(repo),
    ]
    if args.dry_run:
        cmd.append("--dry-run")
    res = subprocess.run(cmd, cwd=repo, text=True)
    raise SystemExit(res.returncode)


if __name__ == "__main__":
    main()

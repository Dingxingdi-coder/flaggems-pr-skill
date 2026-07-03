#!/usr/bin/env python3
"""Context-aware wrapper around extract_from_worktree.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from op_naming import resolve_op  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"extract_operator error: {message}")


def load_context(path: str) -> dict:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        fail(f"context file not found: {p}")
    return json.loads(p.read_text())


def stage_dict(stage_text: str) -> dict[str, str]:
    parts = stage_text.split()
    if len(parts) != 2:
        fail(f"expected_stage must look like 'alpha 5.1', got {stage_text!r}")
    return {parts[0]: parts[1]}


def normalize_stage(repo: Path, op: str, expected_stage: str) -> None:
    yaml_path = repo / "conf" / "operators.yaml"
    data = yaml.safe_load(yaml_path.read_text())
    target = resolve_op(op).op_id
    changed = False
    for entry in data.get("ops", []):
        if entry.get("id") == target or str(entry.get("id", "")).startswith(f"{target}_"):
            if entry.get("stages") != [stage_dict(expected_stage)]:
                entry["stages"] = [stage_dict(expected_stage)]
                changed = True
    if changed:
        yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"normalized operators.yaml stage to {expected_stage}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract one repaired worktree into the PR branch")
    parser.add_argument("--context", required=True)
    parser.add_argument("--op", required=True, help="normalized operator name")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ctx = load_context(args.context)
    repo = Path(ctx["repo_dir"]).expanduser().resolve()
    if not repo.is_dir():
        fail(f"repo_dir not found: {repo}")
    if not Path(ctx["worktree_root"]).expanduser().is_dir():
        fail(f"worktree_root not found: {ctx['worktree_root']}")

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
    if res.returncode != 0:
        raise SystemExit(res.returncode)
    if not args.dry_run:
        normalize_stage(repo, args.op, ctx.get("expected_stage", "alpha 5.1"))


if __name__ == "__main__":
    main()

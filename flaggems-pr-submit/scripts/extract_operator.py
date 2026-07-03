#!/usr/bin/env python3
"""Context-aware wrapper around extract_from_worktree.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

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


def stage_line(stage_text: str) -> str:
    parts = stage_text.split()
    if len(parts) != 2:
        fail(f"expected_stage must look like 'alpha 5.1', got {stage_text!r}")
    return f"      - {parts[0]}: '{parts[1]}'\n"


def normalize_stage(repo: Path, op: str, expected_stage: str) -> None:
    """Patch only the target operator's stages block and preserve yaml formatting."""
    yaml_path = repo / "conf" / "operators.yaml"
    lines = yaml_path.read_text(encoding="utf-8").splitlines(keepends=True)
    target = resolve_op(op).op_id
    expected = stage_line(expected_stage)
    out: list[str] = []
    i = 0
    changed = False
    in_target = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if line.startswith("  - id: "):
            entry_id = stripped.split(":", 1)[1].strip()
            in_target = entry_id == target or entry_id.startswith(f"{target}_")
        if in_target and line.startswith("    stages:"):
            out.append(line)
            i += 1
            old_block: list[str] = []
            while i < len(lines) and lines[i].startswith("      - "):
                old_block.append(lines[i])
                i += 1
            if old_block != [expected]:
                out.append(expected)
                changed = True
            else:
                out.extend(old_block)
            continue
        out.append(line)
        i += 1

    if changed:
        yaml_path.write_text("".join(out), encoding="utf-8")
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

    cmd = [sys.executable, str(SCRIPT_DIR / "extract_from_worktree.py"), args.op, "--repo-dir", str(repo)]
    if args.dry_run:
        cmd.append("--dry-run")
    res = subprocess.run(cmd, cwd=repo, text=True)
    if res.returncode != 0:
        raise SystemExit(res.returncode)
    if not args.dry_run:
        normalize_stage(repo, args.op, ctx.get("expected_stage", "alpha 5.1"))


if __name__ == "__main__":
    main()
